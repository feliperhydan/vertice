import json
import re
from dataclasses import dataclass
from html.parser import HTMLParser


@dataclass(frozen=True)
class ExtractedArticleContent:
    raw_html: str
    extracted_text: str | None
    abstract_text: str | None
    meta_description: str | None
    jsonld_description: str | None
    extraction_strategy: str


class ArticleHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.meta_description: str | None = None
        self.abstract_candidates: list[str] = []
        self.paragraphs: list[str] = []
        self.jsonld_blocks: list[str] = []

        self._current_tag: str | None = None
        self._current_text_parts: list[str] = []
        self._current_script_type: str | None = None

    def handle_starttag(self, tag: str, attrs) -> None:
        attributes = {key.lower(): value for key, value in attrs}

        if tag.lower() == "meta":
            name = (attributes.get("name") or attributes.get("property") or "").lower()
            content = attributes.get("content")
            if content and name in {
                "description",
                "og:description",
                "twitter:description",
                "citation_abstract",
            }:
                if name == "citation_abstract":
                    self.abstract_candidates.append(content.strip())
                elif self.meta_description is None:
                    self.meta_description = content.strip()

        if tag.lower() in {"p", "div", "section"}:
            self._current_tag = tag.lower()
            self._current_text_parts = []

        if tag.lower() == "script":
            self._current_script_type = (attributes.get("type") or "").lower()
            self._current_text_parts = []

    def handle_data(self, data: str) -> None:
        if self._current_tag is not None or self._current_script_type is not None:
            self._current_text_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        tag_lower = tag.lower()

        if self._current_tag == tag_lower:
            text = " ".join(part.strip() for part in self._current_text_parts).strip()
            normalized = " ".join(text.split())
            if len(normalized) >= 80:
                lowered = normalized.lower()
                if "abstract" in lowered and len(normalized) <= 1600:
                    self.abstract_candidates.append(normalized)
                self.paragraphs.append(normalized)
            self._current_tag = None
            self._current_text_parts = []

        if tag_lower == "script" and self._current_script_type == "application/ld+json":
            text = "".join(self._current_text_parts).strip()
            if text:
                self.jsonld_blocks.append(text)
            self._current_script_type = None
            self._current_text_parts = []


class ArticleContentExtractor:
    def extract(self, html_content: str) -> ExtractedArticleContent:
        parser = ArticleHTMLParser()
        parser.feed(html_content)

        jsonld_description = self._extract_jsonld_description(parser.jsonld_blocks)
        abstract_text = self._choose_abstract(parser.abstract_candidates)
        extracted_text = self._choose_extracted_text(parser.paragraphs, abstract_text)
        strategy = self._choose_strategy(abstract_text, parser.meta_description, extracted_text)

        return ExtractedArticleContent(
            raw_html=html_content,
            extracted_text=extracted_text,
            abstract_text=abstract_text,
            meta_description=parser.meta_description,
            jsonld_description=jsonld_description,
            extraction_strategy=strategy,
        )

    def _extract_jsonld_description(self, blocks: list[str]) -> str | None:
        for block in blocks:
            try:
                data = json.loads(block)
            except json.JSONDecodeError:
                continue

            description = self._find_description(data)
            if description:
                return description
        return None

    def _find_description(self, value) -> str | None:
        if isinstance(value, dict):
            description = value.get("description")
            if isinstance(description, str) and description.strip():
                return description.strip()
            for nested in value.values():
                found = self._find_description(nested)
                if found:
                    return found
        elif isinstance(value, list):
            for item in value:
                found = self._find_description(item)
                if found:
                    return found
        return None

    def _choose_abstract(self, candidates: list[str]) -> str | None:
        for candidate in candidates:
            cleaned = re.sub(r"\s+", " ", candidate).strip()
            if len(cleaned) >= 60:
                return cleaned
        return None

    def _choose_extracted_text(self, paragraphs: list[str], abstract_text: str | None) -> str | None:
        chosen: list[str] = []
        for paragraph in paragraphs:
            if abstract_text and paragraph == abstract_text:
                continue
            chosen.append(paragraph)
            if len(chosen) >= 4:
                break

        if not chosen:
            return None

        return "\n\n".join(chosen)

    def _choose_strategy(
        self,
        abstract_text: str | None,
        meta_description: str | None,
        extracted_text: str | None,
    ) -> str:
        if abstract_text:
            return "page_abstract"
        if meta_description:
            return "meta_description"
        if extracted_text:
            return "html_paragraphs"
        return "unknown"
