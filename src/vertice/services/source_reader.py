from dataclasses import dataclass

import requests

from .browser_fetcher import BrowserFetcher, PlaywrightUnavailableError


@dataclass(frozen=True)
class SourceReadResult:
    articles: list
    strategy: str
    final_url: str
    content_type: str
    message: str


class SourceReader:
    def __init__(self, fetcher, parser, html_extractor) -> None:
        self.fetcher = fetcher
        self.parser = parser
        self.html_extractor = html_extractor
        self.browser_fetcher = BrowserFetcher()

    def read(self, url: str, source_id: int) -> SourceReadResult:
        try:
            fetch_result = self.fetcher.fetch(url)
        except requests.RequestException as exc:
            browser_result = self._try_browser(url, source_id)
            if browser_result is not None:
                return browser_result
            raise ValueError(f"Falha ao buscar a fonte: {exc}") from exc

        if not self.fetcher._looks_like_html(fetch_result.content_type, fetch_result.content):
            articles = self.parser.parse(fetch_result.content, source_id=source_id)
            return SourceReadResult(
                articles=articles,
                strategy="xml_feed",
                final_url=fetch_result.final_url,
                content_type=fetch_result.content_type,
                message="Feed XML processado com sucesso.",
            )

        html_result = self.html_extractor.extract(
            html_content=fetch_result.content,
            source_id=source_id,
            base_url=fetch_result.final_url,
        )
        if html_result.articles:
            return SourceReadResult(
                articles=html_result.articles,
                strategy="html_page",
                final_url=fetch_result.final_url,
                content_type=fetch_result.content_type,
                message=html_result.message,
            )

        browser_result = self._try_browser(url, source_id)
        if browser_result is not None:
            return browser_result

        raise ValueError(
            "Nao foi possivel extrair artigos nem via feed XML nem via HTML heuristico."
        )

    def diagnose(self, url: str) -> SourceReadResult | None:
        browser_result = self._try_browser(url, source_id=1)
        return browser_result

    def _try_browser(self, url: str, source_id: int) -> SourceReadResult | None:
        try:
            browser_result = self.browser_fetcher.fetch(
                url=url,
                timeout_seconds=self.fetcher.timeout_seconds,
            )
        except PlaywrightUnavailableError:
            return None
        except Exception:
            return None

        if not self.fetcher._looks_like_html(browser_result.content_type, browser_result.content):
            articles = self.parser.parse(browser_result.content, source_id=source_id)
            return SourceReadResult(
                articles=articles,
                strategy="browser_xml_feed",
                final_url=browser_result.final_url,
                content_type=browser_result.content_type,
                message="Feed obtido com sucesso por navegador automatizado.",
            )

        html_result = self.html_extractor.extract(
            html_content=browser_result.content,
            source_id=source_id,
            base_url=browser_result.final_url,
        )
        if html_result.articles:
            return SourceReadResult(
                articles=html_result.articles,
                strategy="browser_html_page",
                final_url=browser_result.final_url,
                content_type=browser_result.content_type,
                message="Artigos extraidos da pagina HTML usando navegador automatizado.",
            )

        return None
