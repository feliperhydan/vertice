import requests

from .browser_fetcher import BrowserFetcher, PlaywrightUnavailableError


class ArticlePageFetcher:
    def __init__(self, fetcher) -> None:
        self.fetcher = fetcher
        self.browser_fetcher = BrowserFetcher()

    def fetch_page(self, url: str) -> tuple[str, str, str]:
        try:
            inspection = self.fetcher.inspect(url)
            return inspection.final_url, inspection.content, inspection.content_type
        except requests.RequestException:
            browser_result = self._try_browser(url)
            if browser_result is None:
                raise
            return browser_result.final_url, browser_result.content, browser_result.content_type

    def _try_browser(self, url: str):
        try:
            return self.browser_fetcher.fetch(
                url=url,
                timeout_seconds=self.fetcher.timeout_seconds,
            )
        except (PlaywrightUnavailableError, Exception):
            return None
