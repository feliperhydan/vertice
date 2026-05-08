from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urljoin

import requests


@dataclass(frozen=True)
class FetchResult:
    requested_url: str
    normalized_url: str
    final_url: str
    content: str
    content_type: str
    status_code: int


class AlternateFeedParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.feed_url: str | None = None

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag.lower() != "link" or self.feed_url is not None:
            return

        attributes = {key.lower(): value for key, value in attrs}
        rel = (attributes.get("rel") or "").lower()
        href = attributes.get("href")
        content_type = (attributes.get("type") or "").lower()

        if "alternate" not in rel:
            return

        if not href:
            return

        if "rss" in content_type or "atom" in content_type or "xml" in content_type:
            self.feed_url = href


class RSSFetcher:
    def __init__(self, timeout_seconds: int = 20) -> None:
        self.timeout_seconds = timeout_seconds
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/136.0.0.0 Safari/537.36"
            ),
            "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, text/html;q=0.9, */*;q=0.8",
        }

    def fetch(self, url: str) -> FetchResult:
        normalized_url = self._normalize_url(url)
        response = requests.get(
            normalized_url,
            timeout=self.timeout_seconds,
            headers=self.headers,
            allow_redirects=True,
        )
        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "")
        content = response.text

        if self._looks_like_html(content_type, content):
            discovered_feed_url = self._discover_feed_url(
                base_url=response.url,
                html_content=content,
            )
            if discovered_feed_url and discovered_feed_url != response.url:
                discovered_response = requests.get(
                    discovered_feed_url,
                    timeout=self.timeout_seconds,
                    headers=self.headers,
                    allow_redirects=True,
                )
                discovered_response.raise_for_status()
                return FetchResult(
                    requested_url=url,
                    normalized_url=normalized_url,
                    final_url=discovered_response.url,
                    content=discovered_response.text,
                    content_type=discovered_response.headers.get("Content-Type", ""),
                    status_code=discovered_response.status_code,
                )

        return FetchResult(
            requested_url=url,
            normalized_url=normalized_url,
            final_url=response.url,
            content=content,
            content_type=content_type,
            status_code=response.status_code,
        )

    def inspect(self, url: str) -> FetchResult:
        normalized_url = self._normalize_url(url)
        response = requests.get(
            normalized_url,
            timeout=self.timeout_seconds,
            headers=self.headers,
            allow_redirects=True,
        )
        return FetchResult(
            requested_url=url,
            normalized_url=normalized_url,
            final_url=response.url,
            content=response.text,
            content_type=response.headers.get("Content-Type", ""),
            status_code=response.status_code,
        )

    def _normalize_url(self, url: str) -> str:
        if url.startswith("http://feeds.nature.com/") and url.endswith("/rss/current"):
            parts = url.rstrip("/").split("/")
            journal_slug = parts[-3]
            return f"https://www.nature.com/{journal_slug}.rss"

        if url.startswith("http://rss.sciencedirect.com/"):
            return "https://" + url[len("http://") :]

        return url

    def _looks_like_html(self, content_type: str, content: str) -> bool:
        lowered_content_type = content_type.lower()
        if "text/html" in lowered_content_type:
            return True

        content_start = content.lstrip()[:200].lower()
        return (
            content_start.startswith("<!doctype html")
            or content_start.startswith("<html")
        )

    def _discover_feed_url(self, base_url: str, html_content: str) -> str | None:
        parser = AlternateFeedParser()
        parser.feed(html_content)
        if not parser.feed_url:
            return None

        return urljoin(base_url, parser.feed_url)
