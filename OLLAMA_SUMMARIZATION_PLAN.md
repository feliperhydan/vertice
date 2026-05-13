# Plano de Acao: Resumo de Artigos com Ollama

Este documento descreve um plano de implementacao para adicionar ao Vértice uma camada de enriquecimento de artigos e geracao de resumos com Ollama.

## Status atual

- [x] Schema inicial de `article_content`
- [x] Schema inicial de `article_summary`
- [x] `article_page_fetcher.py`
- [x] `article_content_extractor.py`
- [x] `ollama_client.py`
- [x] `article_summarizer.py`
- [x] `article_enrichment_service.py`
- [x] `article_analysis_service.py`
- [x] Acao no frontend para enriquecer artigos
- [x] Acao no frontend para gerar resumos com Ollama
- [ ] `article_scores`
- [ ] Scores de relevancia, novidade e impacto
- [ ] Reprocessamento com multiplos tipos de resumo
- [ ] Filtros e visualizacoes dedicadas para enrichment/summarization

## Objetivo

Melhorar a qualidade do entendimento dos artigos coletados via RSS, indo alem do resumo curto que normalmente vem no feed.

A proposta e:

1. usar o RSS apenas para descoberta e coleta inicial;
2. buscar a pagina do artigo original;
3. extrair o melhor conteudo publico disponivel;
4. gerar resumos estruturados com Ollama;
5. salvar esses resultados no banco para consulta posterior.

## Problema atual

Hoje o sistema salva principalmente:

- `summary`: geralmente vindo de `description`, `summary` ou `abstract` do feed;
- `content`: quando o feed oferece algo como `content:encoded`.

Isso nem sempre e suficiente porque:

- muitos feeds trazem apenas um teaser;
- o conteudo pode vir truncado;
- o texto pode ser promocional ou superficial;
- nem sempre ha contexto suficiente para um bom ranking posterior.

## Estrategia recomendada

Separar o problema em 3 etapas:

1. `ingestion`
2. `enrichment`
3. `summarization`

### 1. Ingestion

Responsabilidade:

- descobrir novos artigos via RSS;
- salvar metadados basicos no banco.

Dados principais:

- titulo
- link
- guid
- autores
- data
- resumo do feed
- conteudo do feed, quando existir

### 2. Enrichment

Responsabilidade:

- acessar a URL do artigo;
- extrair o melhor conteudo publico disponivel da pagina.

Prioridade de extracao:

1. abstract da pagina
2. meta tags como `citation_abstract`
3. `description`, `og:description` e `twitter:description`
4. JSON-LD com `description`
5. highlights
6. primeiros paragrafos do corpo principal

Objetivo:

- montar um texto-base melhor para alimentar o Ollama.

### 3. Summarization

Responsabilidade:

- gerar resumos derivados a partir do melhor texto extraido;
- salvar os resultados no banco.

Tipos de resumo sugeridos:

- resumo curto
- resumo tecnico
- pontos-chave
- classificacao tematica
- score de relevancia

## Mudancas sugeridas no banco de dados

Nao e recomendado sobrescrever diretamente o `summary` original do feed.

O ideal e guardar:

- o texto original vindo da fonte
- o texto enriquecido extraido da pagina
- o resumo gerado pela IA

### Opcao A: novas colunas na tabela `articles`

Campos sugeridos:

- `source_summary`
- `source_content`
- `enriched_text`
- `abstract_text`
- `enrichment_strategy`
- `generated_summary`
- `summary_model`
- `summary_generated_at`

Vantagem:

- implementacao mais simples no curto prazo.

Desvantagem:

- tabela `articles` cresce muito em responsabilidade.

### Opcao B: novas tabelas

Opcao recomendada.

#### `article_content`

Campos sugeridos:

- `id`
- `article_id`
- `source_url`
- `raw_html`
- `extracted_text`
- `abstract_text`
- `meta_description`
- `jsonld_description`
- `extraction_strategy`
- `fetched_at`

#### `article_summary`

Campos sugeridos:

- `id`
- `article_id`
- `summary_type`
- `summary_text`
- `model_name`
- `input_source`
- `prompt_version`
- `generated_at`

#### `article_scores`

Campos sugeridos:

- `id`
- `article_id`
- `model_name`
- `relevance_score`
- `novelty_score`
- `credibility_score`
- `impact_score`
- `reasoning`
- `generated_at`

Vantagem:

- mais escalavel;
- separa melhor as responsabilidades;
- facilita reprocessar artigos com novos modelos.

## Arquitetura sugerida no codigo

### Novos modulos

#### `src/vertice/services/article_page_fetcher.py`

Responsabilidade:

- buscar a pagina do artigo;
- lidar com HTML, redirecionamentos e fallback por navegador quando necessario.

#### `src/vertice/services/article_content_extractor.py`

Responsabilidade:

- extrair abstract, meta tags, JSON-LD e blocos relevantes da pagina.

#### `src/vertice/services/ollama_client.py`

Responsabilidade:

- encapsular chamadas locais para o Ollama.

#### `src/vertice/services/article_summarizer.py`

Responsabilidade:

- decidir qual texto usar como entrada;
- enviar prompt ao Ollama;
- retornar resumos estruturados.

#### `src/vertice/services/article_enrichment_service.py`

Responsabilidade:

- coordenar busca da pagina e extracao do texto;
- salvar conteudo enriquecido.

#### `src/vertice/services/article_analysis_service.py`

Responsabilidade:

- coordenar resumo e ranking com IA;
- salvar saidas no banco.

## Fluxo proposto

### Fluxo 1: enriquecimento

1. selecionar artigos novos ainda nao enriquecidos
2. buscar a URL original do artigo
3. extrair abstract e texto relevante
4. salvar em `article_content`

### Fluxo 2: resumo com Ollama

1. selecionar artigos enriquecidos ainda nao resumidos
2. escolher o melhor texto de entrada
3. enviar ao Ollama
4. salvar saida em `article_summary`

### Fluxo 3: ranking com Ollama

1. selecionar artigos resumidos
2. pedir notas por criterios definidos
3. salvar em `article_scores`

## Prioridade de texto para resumir

Ordem sugerida:

1. `abstract_text`
2. `extracted_text`
3. `source_content`
4. `source_summary`
5. titulo apenas, como ultimo fallback

## Estrategia de prompts

Nao usar um unico prompt para tudo.

Sugestao:

- um prompt para noticia
- um prompt para artigo cientifico
- um prompt para revisao ou editorial

### Exemplo de saidas desejadas

#### Resumo curto

- 2 a 3 frases
- linguagem clara
- foco no tema central

#### Resumo tecnico

- 1 paragrafo mais detalhado
- mencionar metodo, objeto de estudo e principal resultado

#### Pontos-chave

- 3 a 5 bullets

#### Ranking

- relevancia
- novidade
- potencial de impacto
- confiabilidade aparente

## Integracao com Ollama

### Requisitos

- Ollama instalado localmente
- modelo baixado, por exemplo:
  - `ministral-3:3b`
  - `mistral`
  - outro modelo compativel com o seu ambiente

### Configuracoes futuras sugeridas

Adicionar em `settings.py`:

- `ollama_base_url`
- `ollama_model`
- `ollama_timeout_seconds`
- `summary_max_chars`

## Etapas recomendadas de implementacao

### Fase 1

- [x] criar schema para `article_content`
- [x] implementar fetch da pagina do artigo
- [x] implementar extracao de abstract e meta descriptions

### Fase 2

- [x] criar `ollama_client.py`
- [x] criar `article_summarizer.py`
- [x] gerar resumo curto
- [x] salvar em `article_summary`

### Fase 3

- [ ] adicionar resumo tecnico e pontos-chave
- [ ] adicionar scores de relevancia e novidade
- [ ] salvar em `article_scores`

### Fase 4

- [x] mostrar os resumos no frontend
- [x] permitir disparar analise por lote
- [ ] permitir reprocessar artigos com outro modelo

## Ajustes no frontend

Paginas ou secoes futuras sugeridas:

- lista de artigos com resumo gerado
- botao para enriquecer artigos
- botao para gerar resumos com Ollama
- status de processamento por artigo
- filtros por:
  - resumido ou nao
  - enriquecido ou nao
  - score de relevancia

## Riscos e limitacoes

### Qualidade do texto fonte

- alguns sites mostram apenas abstract;
- alguns mostram trechos curtos;
- alguns exigem login ou paywall.

### Bloqueios anti-bot

- nem toda pagina sera acessivel por `requests`;
- algumas podem exigir navegador automatizado.

### Custo computacional local

- resumir muitos artigos pode demorar;
- dependendo do modelo, o uso de memoria pode ser alto.

### Qualidade dos resumos

- modelos locais variam muito em precisao;
- sera importante testar prompts e modelos diferentes.

## Recomendacao final

A melhor ordem pratica para o projeto e:

1. enriquecer os artigos buscando a pagina original;
2. extrair o melhor texto publico disponivel;
3. salvar esse conteudo em estrutura separada no banco;
4. so entao integrar o Ollama para resumo e ranking;
5. por fim, expor esses resultados no frontend.

## Proximo passo recomendado

Implementar primeiro a Fase 1:

- schema de `article_content`
- fetch da pagina do artigo
- extracao de abstract e metadados ricos

Depois disso, a integracao com Ollama fica muito mais forte e util.
