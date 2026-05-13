from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

from ..models.article import Article


@dataclass(frozen=True)
class HTMLExtractionResult:
    articles: list[Article]
    message: str


@dataclass
class AnchorCandidate:
    href: str
    text: str
    score: int


class GenericHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._current_anchor_href: str | None = None
        self._current_anchor_text_parts: list[str] = []
        self.anchors: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag.lower() != "a":
            return

        attributes = {key.lower(): value for key, value in attrs}
        href = attributes.get("href")
        if href:
            self._current_anchor_href = href
            self._current_anchor_text_parts = []

    def handle_data(self, data: str) -> None:
        if self._current_anchor_href is not None:
            self._current_anchor_text_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() != "a" or self._current_anchor_href is None:
            return

        text = " ".join(part.strip() for part in self._current_anchor_text_parts).strip()
        self.anchors.append((self._current_anchor_href, text))
        self._current_anchor_href = None
        self._current_anchor_text_parts = []


class HTMLArticleExtractor:
    def extract(
        self,
        html_content: str,
        source_id: int,
        base_url: str,
    ) -> HTMLExtractionResult:
        parser = GenericHTMLParser()
        parser.feed(html_content)
        candidates = self._score_candidates(parser.anchors, base_url)
        articles = self._build_articles(candidates, source_id)

        if not articles:
            return HTMLExtractionResult(
                articles=[],
                message="Nenhum artigo convincente foi identificado no HTML.",
            )

        return HTMLExtractionResult(
            articles=articles,
            message="Artigos extraidos de uma pagina HTML usando heuristicas genericas.",
        )

    def _score_candidates(
        self,
        anchors: list[tuple[str, str]],
        base_url: str,
    ) -> list[AnchorCandidate]:
        scored: list[AnchorCandidate] = []
        seen: set[str] = set()

        for href, text in anchors:
            cleaned_text = " ".join(text.split()).strip()
            if not href or len(cleaned_text) < 20:
                continue

            absolute_href = urljoin(base_url, href)
            cache_key = f"{absolute_href}|{cleaned_text}"
            if cache_key in seen:
                continue
            seen.add(cache_key)

            score = self._score_link(absolute_href, cleaned_text, base_url)
            if score < 3:
                continue

            scored.append(
                AnchorCandidate(
                    href=absolute_href,
                    text=cleaned_text,
                    score=score,
                )
            )

        scored.sort(key=lambda item: item.score, reverse=True)
        return scored[:50]

    def _score_link(self, href: str, text: str, base_url: str) -> int:
        score = 0
        lowered_href = href.lower()
        lowered_text = text.lower()
        base_host = urlparse(base_url).netloc
        href_host = urlparse(href).netloc

        if href_host == base_host:
            score += 1

        if "doi.org" in lowered_href:
            score += 5
        if "/article/" in lowered_href:
            score += 5
        if "/articles/" in lowered_href:
            score += 4
        if "/science/article/" in lowered_href:
            score += 5
        if "/abs/" in lowered_href or "/full/" in lowered_href:
            score += 2
        if any(char.isdigit() for char in lowered_href):
            score += 1

        if 35 <= len(text) <= 280:
            score += 2
        if any(keyword in lowered_text for keyword in ["editorial board", "submit", "sign in", "about", "issue", "journal home"]):
            score -= 5
        if lowered_text.count("...") > 0:
            score -= 2

        return score

    def _build_articles(
        self,
        candidates: list[AnchorCandidate],
        source_id: int,
    ) -> list[Article]:
        articles: list[Article] = []
        used_links: set[str] = set()

        for candidate in candidates:
            if candidate.href in used_links:
                continue
            used_links.add(candidate.href)

            articles.append(
                Article(
                    source_id=source_id,
                    title=candidate.text,
                    link=candidate.href,
                    guid=candidate.href,
                    summary="Extraido de pagina HTML; feed XML nao estava disponivel.",
                    author=None,
                    published_at=None,
                    raw_published=None,
                    content=None,
                    language=None,
                )
            )

        return articles
