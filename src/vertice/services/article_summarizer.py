from dataclasses import dataclass


@dataclass(frozen=True)
class SummaryResult:
    summary_text: str
    input_source: str
    prompt_version: str


class ArticleSummarizer:
    PROMPT_VERSION = "v1-short-summary"

    def __init__(self, ollama_client, max_chars: int) -> None:
        self.ollama_client = ollama_client
        self.max_chars = max_chars

    def summarize(
        self,
        title: str,
        source_summary: str | None,
        source_content: str | None,
        abstract_text: str | None,
        extracted_text: str | None,
        meta_description: str | None,
        jsonld_description: str | None,
        context: dict | None = None,
    ) -> SummaryResult:
        input_text, input_source = self._select_input_text(
            source_summary=source_summary,
            source_content=source_content,
            abstract_text=abstract_text,
            extracted_text=extracted_text,
            meta_description=meta_description,
            jsonld_description=jsonld_description,
        )

        prompt = self._build_prompt(title=title, text=input_text)
        summary = self.ollama_client.generate(
            prompt,
            context={
                **(context or {}),
                "input_source": input_source,
                "input_chars": len(input_text),
                "prompt_version": self.PROMPT_VERSION,
            },
        )
        return SummaryResult(
            summary_text=summary,
            input_source=input_source,
            prompt_version=self.PROMPT_VERSION,
        )

    def _select_input_text(
        self,
        source_summary: str | None,
        source_content: str | None,
        abstract_text: str | None,
        extracted_text: str | None,
        meta_description: str | None,
        jsonld_description: str | None,
    ) -> tuple[str, str]:
        candidates = [
            ("abstract_text", abstract_text),
            ("extracted_text", extracted_text),
            ("source_content", source_content),
            ("source_summary", source_summary),
            ("jsonld_description", jsonld_description),
            ("meta_description", meta_description),
        ]

        for source_name, value in candidates:
            if value and value.strip():
                return value.strip()[: self.max_chars], source_name

        raise ValueError("Nao ha texto suficiente para gerar resumo com o Ollama.")

    def _build_prompt(self, title: str, text: str) -> str:
        return (
            "Voce esta resumindo um artigo cientifico ou tecnico.\n"
            "Gere um resumo claro em portugues do Brasil, em um unico paragrafo curto, "
            "explicando do que o artigo trata, qual problema aborda e o principal foco do texto.\n"
            "Nao invente informacoes ausentes.\n\n"
            f"Titulo: {title}\n\n"
            f"Texto base:\n{text}\n"
        )
