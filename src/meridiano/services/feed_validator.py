from dataclasses import dataclass
from typing import Optional

import requests

from ..models.article import RSSSource


@dataclass(frozen=True)
class FeedValidationResult:
    source_name: str
    source_url: str
    status: str
    message: str
    normalized_url: str
    final_url: str
    content_type: str
    http_status: Optional[int]
    article_count: int = 0
    suggested_url: Optional[str] = None
    confidence: str = "low"


class FeedValidator:
    def __init__(self, fetcher, parser, source_reader) -> None:
        self.fetcher = fetcher
        self.parser = parser
        self.source_reader = source_reader

    def validate_sources(self, sources: list[dict[str, str]]) -> list[FeedValidationResult]:
        return [self.validate_source(RSSSource(**source)) for source in sources]

    def validate_source(self, source: RSSSource) -> FeedValidationResult:
        try:
            inspection = self.fetcher.inspect(source.url)
        except requests.RequestException as exc:
            return FeedValidationResult(
                source_name=source.name,
                source_url=source.url,
                status="network_error",
                message=f"Falha de rede ao tentar acessar o feed: {exc}",
                normalized_url=source.url,
                final_url=source.url,
                content_type="",
                http_status=None,
            )

        suggested_url = self._choose_suggested_url(inspection)
        content_type = inspection.content_type or "unknown"

        if inspection.status_code in (401, 403):
            browser_diagnosis = self.source_reader.diagnose(source.url)
            if browser_diagnosis and browser_diagnosis.articles:
                return FeedValidationResult(
                    source_name=source.name,
                    source_url=source.url,
                    status="requires_browser",
                    message="O servidor bloqueia requisicoes simples, mas a leitura funciona via navegador automatizado.",
                    normalized_url=inspection.normalized_url,
                    final_url=browser_diagnosis.final_url,
                    content_type=browser_diagnosis.content_type or content_type,
                    http_status=inspection.status_code,
                    article_count=len(browser_diagnosis.articles),
                    suggested_url=suggested_url if suggested_url != source.url else None,
                    confidence=self._confidence_from_suggestion(source.url, suggested_url),
                )

            return FeedValidationResult(
                source_name=source.name,
                source_url=source.url,
                status="blocked",
                message="O servidor bloqueou a requisicao automatica para este feed.",
                normalized_url=inspection.normalized_url,
                final_url=inspection.final_url,
                content_type=content_type,
                http_status=inspection.status_code,
                suggested_url=suggested_url if suggested_url != source.url else None,
                confidence=self._confidence_from_suggestion(source.url, suggested_url),
            )

        if inspection.status_code in (404, 410):
            return FeedValidationResult(
                source_name=source.name,
                source_url=source.url,
                status="obsolete",
                message="A URL parece obsoleta ou removida pelo provedor.",
                normalized_url=inspection.normalized_url,
                final_url=inspection.final_url,
                content_type=content_type,
                http_status=inspection.status_code,
                suggested_url=suggested_url if suggested_url != source.url else None,
                confidence=self._confidence_from_suggestion(source.url, suggested_url),
            )

        if inspection.status_code >= 400:
            return FeedValidationResult(
                source_name=source.name,
                source_url=source.url,
                status="http_error",
                message=f"O servidor retornou erro HTTP {inspection.status_code}.",
                normalized_url=inspection.normalized_url,
                final_url=inspection.final_url,
                content_type=content_type,
                http_status=inspection.status_code,
                suggested_url=suggested_url if suggested_url != source.url else None,
                confidence=self._confidence_from_suggestion(source.url, suggested_url),
            )

        if self.fetcher._looks_like_html(inspection.content_type, inspection.content):
            discovered_url = self.fetcher._discover_feed_url(inspection.final_url, inspection.content)
            if discovered_url:
                return FeedValidationResult(
                    source_name=source.name,
                    source_url=source.url,
                    status="candidate_replacement_found",
                    message="A URL atual retorna HTML, mas um feed alternativo foi encontrado na pagina.",
                    normalized_url=inspection.normalized_url,
                    final_url=inspection.final_url,
                    content_type=content_type,
                    http_status=inspection.status_code,
                    suggested_url=discovered_url,
                    confidence="medium",
                )

            try:
                html_read_result = self.source_reader.read(source.url, source_id=1)
                if html_read_result.articles:
                    return FeedValidationResult(
                        source_name=source.name,
                        source_url=source.url,
                        status="html_scrape_ok",
                        message=html_read_result.message,
                        normalized_url=inspection.normalized_url,
                        final_url=html_read_result.final_url,
                        content_type=html_read_result.content_type,
                        http_status=inspection.status_code,
                        article_count=len(html_read_result.articles),
                        suggested_url=suggested_url if suggested_url != source.url else None,
                        confidence=self._confidence_from_suggestion(source.url, suggested_url),
                    )
            except Exception:
                pass

            return FeedValidationResult(
                source_name=source.name,
                source_url=source.url,
                status="html_instead_of_feed",
                message="A URL retorna uma pagina HTML em vez de um feed XML.",
                normalized_url=inspection.normalized_url,
                final_url=inspection.final_url,
                content_type=content_type,
                http_status=inspection.status_code,
                suggested_url=suggested_url if suggested_url != source.url else None,
                confidence=self._confidence_from_suggestion(source.url, suggested_url),
            )

        try:
            parsed_articles = self.parser.parse(inspection.content, source_id=1)
        except Exception as exc:
            return FeedValidationResult(
                source_name=source.name,
                source_url=source.url,
                status="invalid_feed",
                message=f"O conteudo nao foi reconhecido como feed valido: {exc}",
                normalized_url=inspection.normalized_url,
                final_url=inspection.final_url,
                content_type=content_type,
                http_status=inspection.status_code,
                suggested_url=suggested_url if suggested_url != source.url else None,
                confidence=self._confidence_from_suggestion(source.url, suggested_url),
            )

        if not parsed_articles:
            return FeedValidationResult(
                source_name=source.name,
                source_url=source.url,
                status="empty_feed",
                message="O feed foi lido, mas nenhum artigo foi identificado.",
                normalized_url=inspection.normalized_url,
                final_url=inspection.final_url,
                content_type=content_type,
                http_status=inspection.status_code,
                suggested_url=suggested_url if suggested_url != source.url else None,
                confidence=self._confidence_from_suggestion(source.url, suggested_url),
            )

        if suggested_url and suggested_url != source.url:
            return FeedValidationResult(
                source_name=source.name,
                source_url=source.url,
                status="redirected",
                message="O feed funciona, mas existe uma URL melhor ou mais atual para substituicao.",
                normalized_url=inspection.normalized_url,
                final_url=inspection.final_url,
                content_type=content_type,
                http_status=inspection.status_code,
                article_count=len(parsed_articles),
                suggested_url=suggested_url,
                confidence=self._confidence_from_suggestion(source.url, suggested_url),
            )

        return FeedValidationResult(
            source_name=source.name,
            source_url=source.url,
            status="ok",
            message="Feed valido e funcionando normalmente.",
            normalized_url=inspection.normalized_url,
            final_url=inspection.final_url,
            content_type=content_type,
            http_status=inspection.status_code,
            article_count=len(parsed_articles),
            suggested_url=None,
            confidence="high",
        )

    def _choose_suggested_url(self, inspection) -> Optional[str]:
        if inspection.final_url and inspection.final_url != inspection.requested_url:
            return inspection.final_url

        if inspection.normalized_url and inspection.normalized_url != inspection.requested_url:
            return inspection.normalized_url

        return None

    def _confidence_from_suggestion(self, original_url: str, suggested_url: Optional[str]) -> str:
        if not suggested_url or suggested_url == original_url:
            return "low"

        if suggested_url.endswith(".rss") or suggested_url.endswith(".xml") or "rss" in suggested_url.lower():
            return "high"

        return "medium"
