# Vértice

Vértice e uma base para um aplicativo em Python focado em:

1. coletar noticias e artigos cientificos por meio de feeds RSS;
2. normalizar e armazenar esses dados em banco de dados local;
3. preparar o terreno para uma etapa posterior de analise com inteligencia artificial local via Ollama;
4. rankear artigos segundo criterios definidos pelo projeto.

Neste primeiro estagio, o projeto entrega a fundacao de coleta e persistencia:

- lista configuravel de links RSS dentro do codigo;
- persistencia editavel dessas fontes em arquivo local;
- leitura de multiplos feeds;
- extracao de metadados principais de cada item;
- armazenamento em SQLite;
- interface web para operar o sistema;
- estrutura modular para facilitar a futura integracao com IA local.

## Objetivo do projeto

A proposta do Vértice e funcionar como um pipeline local para descoberta e organizacao de conteudo. Em vez de depender apenas de leitura manual de varios sites e revistas, o sistema centraliza os itens publicados em feeds RSS e salva tudo em um banco local. Depois, uma camada de IA podera ler os registros coletados e classifica-los por relevancia, qualidade metodologica, atualidade, potencial de impacto ou qualquer outra heuristica definida pelo usuario.

## Escopo implementado agora

O que ja esta pronto nesta versao:

- cadastro de fontes RSS por meio de uma lista Python;
- persistencia das fontes em `data/rss_sources.json`;
- coleta de feeds RSS 2.0, Atom e RSS/RDF 1.0;
- parsing de itens para um formato interno padronizado;
- deduplicacao por `guid` ou `link`;
- armazenamento em banco SQLite;
- enriquecimento de artigos a partir da pagina original;
- resumo curto com Ollama a partir do melhor texto disponivel;
- relatorio individual por feed RSS ao fim do processamento de cada fonte;
- CLI simples para executar a coleta;
- frontend browser-based para executar e administrar o app;
- aba de operacoes para observar scraping, enrichment, resumos e erros;
- validador inteligente de feeds com deteccao de URLs obsoletas, bloqueadas ou redirecionadas;
- logging em terminal e em arquivo para facilitar diagnostico.

O que fica preparado para a proxima etapa:

- ranking e scores mais avancados com Ollama;
- enriquecimento com extracao ainda mais especifica por provedor;
- filtros mais avancados por dominio, topico, idioma ou fonte;
- agendamento recorrente da coleta.

## Estrutura do projeto

```text
Vértice/
├── README.md
├── OLLAMA_SUMMARIZATION_PLAN.md
├── requirements.txt
├── main.py
├── run_web.py
├── data/
│   └── .gitkeep
└── src/
    └── vertice/
        ├── __init__.py
        ├── bootstrap.py
        ├── config/
        │   ├── __init__.py
        │   ├── rss_sources.py
        │   └── settings.py
        ├── db/
        │   ├── __init__.py
        │   ├── connection.py
        │   ├── models.py
        │   └── repository.py
        ├── logging_config.py
        ├── models/
        │   ├── __init__.py
        │   └── article.py
        ├── services/
        │   ├── __init__.py
        │   ├── article_analysis_service.py
        │   ├── article_content_extractor.py
        │   ├── article_enrichment_service.py
        │   ├── article_page_fetcher.py
        │   ├── article_summarizer.py
        │   ├── browser_fetcher.py
        │   ├── feed_validator.py
        │   ├── html_article_extractor.py
        │   ├── ingestion_service.py
        │   ├── ollama_client.py
        │   ├── rss_fetcher.py
        │   ├── rss_parser.py
        │   └── source_reader.py
        ├── utils/
        │   ├── __init__.py
        │   └── dates.py
        └── web/
            ├── __init__.py
            ├── app.py
            ├── static/
            │   └── styles.css
            └── templates/
                └── dashboard.html
```

## Como o fluxo funciona

1. O projeto possui fontes padrao em `src/vertice/config/rss_sources.py`.
2. Na primeira execucao, essas fontes sao copiadas para `data/rss_sources.json`.
3. O frontend passa a ler e editar esse arquivo persistido.
4. O comando de scraping percorre todas as URLs configuradas.
5. O sistema baixa o XML do feed.
6. Cada item e convertido para um modelo interno `Article`.
7. O banco registra a fonte RSS e insere os artigos ainda nao existentes.
8. O sistema pode enriquecer o artigo acessando a pagina original.
9. O sistema pode gerar um resumo curto via Ollama.
10. Itens repetidos sao ignorados com base em uma chave unica.

## Logs e diagnostico

Quando uma operacao falha, o Vértice passa a salvar logs persistentes em disco, o que ajuda bastante a corrigir erros de scraping, enrichment e principalmente de resumo com Ollama.

Arquivos gerados:

- `logs/vertice.log`: log geral da aplicacao com eventos e erros exibidos tambem no terminal.
- `logs/operation_errors.jsonl`: log estruturado de erros, com um JSON por linha.

Cada registro em `logs/operation_errors.jsonl` inclui:

- `timestamp`
- `operation`
- `stage`
- `exception_type`
- `error_message`
- `context`
- `traceback`

Nos erros de resumo com Ollama, o `context` pode trazer dados como:

- `article_id`
- `title`
- `article_url`
- `model`
- `input_source`
- `prompt_chars`
- `prompt_preview`

Isso torna mais facil descobrir rapidamente se a falha veio de timeout, modelo indisponivel, API do Ollama fora do ar, falta de texto suficiente ou resposta invalida.

## Banco de dados

Foi escolhido SQLite para a primeira versao porque:

- e simples de usar;
- nao exige servidor separado;
- funciona muito bem para prototipos e apps locais;
- facilita testes e iteracoes rapidas.

### Tabelas

#### `sources`

Armazena as fontes RSS cadastradas.

Campos principais:

- `id`
- `name`
- `url`
- `category`
- `created_at`
- `updated_at`

#### `articles`

Armazena os itens coletados dos feeds.

Campos principais:

- `id`
- `source_id`
- `title`
- `link`
- `guid`
- `summary`
- `author`
- `published_at`
- `raw_published`
- `content`
- `language`
- `scraped_at`

#### `article_content`

Armazena o conteudo enriquecido extraido da pagina do artigo.

Campos principais:

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

Armazena resumos gerados a partir do conteudo enriquecido.

Campos principais:

- `article_id`
- `summary_type`
- `summary_text`
- `model_name`
- `input_source`
- `prompt_version`
- `generated_at`

### Regra de duplicidade

Cada artigo recebe uma chave unica baseada em:

- `guid`, quando disponivel;
- caso contrario, `link`.

Isso evita que o mesmo item seja salvo varias vezes em coletas subsequentes.

## Como executar

### 1. Criar ambiente virtual

#### Linux / macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
```

#### Windows PowerShell

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
```

#### Windows CMD

```cmd
py -m venv .venv
.venv\Scripts\activate.bat
```

### 2. Instalar dependencias

#### Linux / macOS

```bash
pip install -r requirements.txt
```

#### Windows PowerShell / CMD

```powershell
py -m pip install -r requirements.txt
```

### 3. Editar os feeds RSS

Voce pode editar os feeds de duas formas.

#### Pela interface web

Depois de iniciar o painel, use as secoes de gerenciamento para:

- adicionar RSS;
- editar nome, URL e categoria;
- remover fontes existentes.

#### Pelo arquivo persistido

Abra o arquivo:

- `data/rss_sources.json`

E adicione suas fontes no formato:

```json
[
    {
        "name": "Nature",
        "url": "https://www.nature.com/nature.rss",
        "category": "ciencia"
    },
    {
        "name": "BBC News",
        "url": "http://feeds.bbci.co.uk/news/rss.xml",
        "category": "noticias"
    }
]
```

### 4. Rodar a ingestao

#### Linux / macOS

```bash
python3 main.py
```

#### Windows PowerShell / CMD

```powershell
py main.py
```

### 5. Rodar a interface web

#### Linux / macOS

```bash
python3 run_web.py
```

#### Windows PowerShell / CMD

```powershell
py run_web.py
```

Depois abra:

- `http://127.0.0.1:5000`

### 6. Conferir o banco

Por padrao, o banco sera criado em:

- `data/vertice.db`

## Funcionalidades da interface web

O painel web permite operar o projeto inteiro por navegador.

Ele foi organizado em paginas separadas com navegacao superior:

- `Inicio`
- `Artigos`
- `Estatisticas`
- `RSS`
- `Banco`

### 1. Executar o scraping

- botao para iniciar a coleta;
- relatorio visual por RSS ao final de cada execucao;
- exibicao de novos artigos, duplicados e erros por fonte.

### 2. Visualizar os artigos coletados

- cards com os ultimos artigos armazenados;
- fonte, categoria, resumo e data;
- exibicao de estrategia de enriquecimento quando disponivel;
- exibicao do resumo gerado por Ollama quando disponivel;
- link direto para abrir o conteudo original.

### 2.1. Enriquecer artigos

- botao na pagina de artigos para buscar a pagina original dos artigos pendentes;
- extracao de abstract, meta description, JSON-LD e paragrafos principais;
- persistencia desse conteudo em `article_content`.

### 2.2. Gerar resumos com Ollama

- botao na pagina de artigos para resumir artigos enriquecidos;
- selecao automatica da melhor fonte de texto;
- persistencia do resumo em `article_summary`.

### 3. Visualizar as estatisticas por RSS

- quantidade de artigos por fonte;
- ultima publicacao registrada;
- ultima coleta conhecida daquela fonte.

### 4. Editar os RSS

- criar, atualizar e remover fontes pela propria interface;
- persistencia automatica em `data/rss_sources.json`.

### 4.1. Validar feeds e sugerir substituicoes

- executar validacao automatica de todos os RSS cadastrados;
- classificar fontes como `ok`, `redirected`, `blocked`, `obsolete`, `html_instead_of_feed` e outras categorias de diagnostico;
- sugerir uma URL de substituicao quando houver forte indicio de feed mais atual ou funcional;
- aplicar a sugestao diretamente pela interface.

### 5. Apagar dados do banco de dados

- apagar apenas os artigos;
- apagar artigos e fontes salvas no SQLite.

Observacao importante:

- limpar o banco nao remove automaticamente o arquivo `data/rss_sources.json`;
- isso preserva a configuracao das fontes para novas coletas.

## Exemplo de uso esperado

Voce preenche a lista de RSS no codigo com fontes como:

- jornais;
- blogs tecnicos;
- revistas cientificas;
- periodicos academicos;
- repositrios institucionais com feeds.

Ao executar o sistema, ele:

- registra cada fonte no banco;
- baixa os feeds;
- salva os itens encontrados;
- mostra um relatorio logo apos cada RSS ser processado;
- ignora duplicados em execucoes futuras.

### Exemplo de relatorio por RSS

Durante a execucao, cada fonte passa a emitir um resumo proprio, por exemplo:

```text
RSS report | name=Nature | fetched_items=25 | new_articles=12 | duplicates=13 | status=success
RSS report | name=BBC News | fetched_items=40 | new_articles=40 | duplicates=0 | status=success
```

Se houver falha em uma fonte:

```text
RSS report | name=Minha Fonte | fetched_items=0 | new_articles=0 | duplicates=0 | status=error | message=...
```

## Futuro: camada de IA local com Ollama

O projeto ja possui a base inicial de integracao com Ollama para gerar resumos curtos. A proxima evolucao natural e ampliar isso para scores, analise tematica e rankings mais sofisticados.

Exemplos de analises futuras:

- gerar resumo tecnico do artigo;
- atribuir nota de relevancia de 0 a 10;
- detectar topicos principais;
- estimar nivel de confiabilidade;
- identificar se o texto e mais util para pesquisa academica, acompanhamento de mercado ou atualizacao geral.

### Exemplo de pipeline futuro

1. coletar artigos via RSS;
2. salvar no SQLite;
3. enriquecer com conteudo da pagina original;
4. gerar resumo curto com Ollama;
5. futuramente gerar scores e justificativas.

### Possivel extensao de schema

No futuro, pode ser criada uma tabela `article_analysis` com campos como:

- `article_id`
- `model_name`
- `relevance_score`
- `novelty_score`
- `credibility_score`
- `summary_ai`
- `reasoning`
- `analyzed_at`

## Decisoes de arquitetura

### Separacao por responsabilidades

- `config/`: configuracoes e fontes RSS;
- `models/`: modelos de dominio do app;
- `services/`: regras de negocio, fetch e parse dos feeds;
- `db/`: conexao, schema e operacoes de persistencia;
- `utils/`: helpers pequenos e reutilizaveis.

### Por que modularizar agora

Mesmo sendo um prototipo, o projeto ja nasce com divisao clara para evitar que a futura integracao com IA vire um unico arquivo grande e dificil de manter.

## Dependencias

As dependencias foram mantidas enxutas:

- `requests` para baixar feeds com simplicidade e robustez.
- `Flask` para a interface web browser-based.

Todo o parsing XML e a persistencia usam bibliotecas da propria biblioteca padrao do Python.

Dependencia opcional para fontes mais protegidas:

- `playwright`, caso voce queira habilitar o modo de navegador automatizado para feeds bloqueados ou paginas que exigem renderizacao mais realista.

### Integracao com Ollama

O projeto agora possui um cliente dedicado para Ollama e um fluxo de resumo curto baseado em:

- `abstract_text`
- `extracted_text`
- `content` do feed
- `summary` do feed
- `jsonld_description`
- `meta_description`

Configuracoes disponiveis em `src/vertice/config/settings.py`:

- `ollama_base_url`
- `ollama_model` (padrao atual: `ministral-3:3b`)
- `ollama_timeout_seconds`
- `summary_max_chars`

Se quiser usar `playwright` no Windows:

```powershell
py -m pip install playwright
py -m playwright install
```

### Compatibilidade de feeds

O parser foi adaptado para tolerar o maximo possivel de variacoes comuns de feeds, incluindo:

- RSS 2.0 tradicional com `channel/item`
- Atom com `feed/entry`
- RSS 1.0 / RDF
- campos com namespaces como `dc:creator`, `dc:date` e `content:encoded`
- variacoes comuns de datas como RFC 822, ISO 8601 e timestamps com milissegundos

### Leitura hibrida de fontes

O Vértice agora usa uma estrategia em camadas:

1. tenta ler como feed XML normal;
2. se receber HTML, tenta descobrir um feed alternativo na pagina;
3. se ainda assim nao houver feed, tenta extrair artigos da propria pagina HTML com heuristicas genericas;
4. opcionalmente, se `playwright` estiver instalado, tenta repetir a leitura via navegador automatizado.

Isso ajuda em fontes que:

- mudaram de URL;
- entregam pagina HTML em vez de XML;
- expõem a lista de artigos na pagina do journal;
- bloqueiam requisicoes simples mas funcionam melhor com navegador real.

## Melhorias sugeridas para as proximas iteracoes

- adicionar testes automatizados;
- permitir carregar fontes RSS por arquivo `.json` ou `.yaml`;
- criar agendamento com `cron` ou `APScheduler`;
- baixar o conteudo completo da pagina alem do feed;
- adicionar tabela de analise com Ollama;
- criar API com FastAPI para consultar os dados;
- criar filtros e ranking mais avancados na interface web.

## Resumo

O Vértice ja entrega a espinha dorsal do sistema:

- entrada configuravel de feeds RSS;
- coleta automatizada;
- persistencia local confiavel;
- enriquecimento de artigos a partir da pagina original;
- resumo curto com Ollama;
- painel web para operar o fluxo sem usar so o terminal;
- arquitetura pronta para evoluir com IA local.

Se voce quiser, a proxima etapa pode ser a integracao com Ollama para:

- resumir os artigos;
- classificar relevancia;
- gerar ranking automatico;
- marcar os melhores candidatos para leitura.
