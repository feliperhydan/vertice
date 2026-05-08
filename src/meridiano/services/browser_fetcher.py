from dataclasses import dataclass


@dataclass(frozen=True)
class BrowserFetchResult:
    final_url: str
    content: str
    content_type: str
    status_code: int


class PlaywrightUnavailableError(RuntimeError):
    """Raised when Playwright is not installed or cannot be used."""


class BrowserFetcher:
    def fetch(self, url: str, timeout_seconds: int) -> BrowserFetchResult:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise PlaywrightUnavailableError(
                "Playwright nao esta instalado no ambiente atual."
            ) from exc

        timeout_ms = timeout_seconds * 1000
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            response = page.goto(url, wait_until="networkidle", timeout=timeout_ms)
            content = page.content()
            final_url = page.url
            status_code = response.status if response is not None else 200
            content_type = ""
            if response is not None:
                content_type = response.headers.get("content-type", "")
            browser.close()

        return BrowserFetchResult(
            final_url=final_url,
            content=content,
            content_type=content_type,
            status_code=status_code,
        )
