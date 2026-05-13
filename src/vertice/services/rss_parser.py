import hashlib
import xml.etree.ElementTree as ET
from typing import Iterable, Optional

from ..models.article import Article
from ..utils.dates import normalize_datetime


class RSSParser:
    ATOM_NAMESPACE = "http://www.w3.org/2005/Atom"

    def parse(self, xml_content: str, source_id: int) -> list[Article]:
        root = ET.fromstring(xml_content.strip())

        if self._looks_like_html_document(root):
            raise ValueError("The fetched document is HTML, not a valid XML feed.")

        if self._is_atom_feed(root):
            return list(self._parse_atom(root, source_id))

        if self._is_rdf_feed(root):
            return list(self._parse_rdf(root, source_id))

        return list(self._parse_rss(root, source_id))

    def _parse_rss(self, root: ET.Element, source_id: int) -> Iterable[Article]:
        channel = self._find_first_child(root, ["channel"])
        if channel is None:
            items = self._find_children(root, "item")
            feed_language = None
        else:
            items = self._find_children(channel, "item")
            feed_language = self._find_text(channel, ["language"])

        return [
            article
            for article in (
                self._build_xml_article(item, source_id, feed_language=feed_language)
                for item in items
            )
            if article is not None
        ]

    def _parse_rdf(self, root: ET.Element, source_id: int) -> Iterable[Article]:
        items = self._find_children(root, "item")
        feed_language = self._find_text(root, ["language"])
        return [
            article
            for article in (
                self._build_xml_article(item, source_id, feed_language=feed_language)
                for item in items
            )
            if article is not None
        ]

    def _parse_atom(self, root: ET.Element, source_id: int) -> Iterable[Article]:
        feed_language = (
            root.attrib.get("{http://www.w3.org/XML/1998/namespace}lang")
            or root.attrib.get("lang")
        )
        entries = self._find_children(root, "entry")
        return [
            article
            for article in (
                self._build_atom_article(entry, source_id, feed_language=feed_language)
                for entry in entries
            )
            if article is not None
        ]

    def _build_xml_article(
        self,
        item: ET.Element,
        source_id: int,
        feed_language: Optional[str] = None,
    ) -> Optional[Article]:
        title = self._find_text(item, ["title"]) or "Untitled"
        link = self._extract_link(item)
        summary = self._find_text(item, ["description", "summary", "abstract"])
        author = self._find_text(item, ["author", "creator"])
        raw_published = self._find_text(
            item,
            ["pubDate", "date", "published", "updated", "issued", "created"],
        )
        language = self._find_text(item, ["language"]) or feed_language
        content = self._extract_content(item)
        guid = self._build_guid(
            source_id=source_id,
            guid=self._find_text(item, ["guid", "id", "identifier"]),
            link=link,
            title=title,
            raw_published=raw_published,
        )

        if not title.strip() and not link.strip():
            return None

        return Article(
            source_id=source_id,
            title=title.strip() or "Untitled",
            link=link.strip(),
            guid=guid.strip(),
            summary=self._clean_optional(summary),
            author=self._clean_optional(author),
            published_at=normalize_datetime(raw_published),
            raw_published=self._clean_optional(raw_published),
            content=self._clean_optional(content),
            language=self._clean_optional(language),
        )

    def _build_atom_article(
        self,
        entry: ET.Element,
        source_id: int,
        feed_language: Optional[str] = None,
    ) -> Optional[Article]:
        title = self._find_text(entry, ["title"]) or "Untitled"
        link = self._extract_link(entry)
        summary = self._find_text(entry, ["summary", "subtitle"])
        content = self._find_text(entry, ["content"]) or summary
        author = self._extract_atom_author(entry)
        raw_published = self._find_text(entry, ["published", "updated", "created"])
        language = (
            entry.attrib.get("{http://www.w3.org/XML/1998/namespace}lang")
            or entry.attrib.get("lang")
            or feed_language
        )
        guid = self._build_guid(
            source_id=source_id,
            guid=self._find_text(entry, ["id", "identifier"]),
            link=link,
            title=title,
            raw_published=raw_published,
        )

        if not title.strip() and not link.strip():
            return None

        return Article(
            source_id=source_id,
            title=title.strip() or "Untitled",
            link=link.strip(),
            guid=guid.strip(),
            summary=self._clean_optional(summary),
            author=self._clean_optional(author),
            published_at=normalize_datetime(raw_published),
            raw_published=self._clean_optional(raw_published),
            content=self._clean_optional(content),
            language=self._clean_optional(language),
        )

    def _is_atom_feed(self, root: ET.Element) -> bool:
        return self._local_name(root.tag) == "feed"

    def _is_rdf_feed(self, root: ET.Element) -> bool:
        local_name = self._local_name(root.tag).lower()
        return local_name == "rdf"

    def _looks_like_html_document(self, root: ET.Element) -> bool:
        return self._local_name(root.tag).lower() == "html"

    def _extract_atom_author(self, entry: ET.Element) -> Optional[str]:
        author_element = self._find_first_child(entry, ["author"])
        if author_element is None:
            return self._find_text(entry, ["creator", "author"])

        name = self._find_text(author_element, ["name"])
        if name:
            return name
        return self._joined_text(author_element)

    def _extract_link(self, item: ET.Element) -> str:
        local_name = self._local_name(item.tag)
        if local_name == "entry":
            return self._extract_atom_link(item) or ""

        link_text = self._find_text(item, ["link"])
        if link_text:
            return link_text

        first_link_element = self._find_first_child(item, ["link"])
        if first_link_element is not None:
            href = first_link_element.attrib.get("href")
            if href:
                return href

        about = item.attrib.get("{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about")
        if about:
            return about

        return ""

    def _extract_atom_link(self, entry: ET.Element) -> Optional[str]:
        links = self._find_children(entry, "link")
        for link in links:
            href = link.attrib.get("href")
            rel = link.attrib.get("rel", "alternate")
            if href and rel == "alternate":
                return href

        for link in links:
            href = link.attrib.get("href")
            if href:
                return href

        fallback_text = self._find_text(entry, ["link"])
        return fallback_text

    def _extract_content(self, item: ET.Element) -> Optional[str]:
        content = self._find_text(
            item,
            [
                "encoded",
                "content",
                "description",
                "summary",
                "abstract",
            ],
        )
        if content:
            return content

        media_description = self._find_nested_text(item, ["group", "content"], ["description"])
        return media_description

    def _find_nested_text(
        self,
        item: ET.Element,
        parent_candidates: list[str],
        child_candidates: list[str],
    ) -> Optional[str]:
        for child in item:
            if self._local_name(child.tag) not in parent_candidates:
                continue

            nested_text = self._find_text(child, child_candidates)
            if nested_text:
                return nested_text

        return None

    def _find_text(self, item: ET.Element, candidate_names: list[str]) -> Optional[str]:
        normalized_candidates = {name.lower() for name in candidate_names}
        for child in item.iter():
            if child is item:
                continue

            if self._local_name(child.tag).lower() not in normalized_candidates:
                continue

            text = self._joined_text(child)
            if text:
                return text

        return None

    def _find_first_child(
        self,
        item: ET.Element,
        candidate_names: list[str],
    ) -> Optional[ET.Element]:
        normalized_candidates = {name.lower() for name in candidate_names}
        for child in item:
            if self._local_name(child.tag).lower() in normalized_candidates:
                return child
        return None

    def _find_children(self, item: ET.Element, candidate_name: str) -> list[ET.Element]:
        normalized_name = candidate_name.lower()
        return [
            child
            for child in item
            if self._local_name(child.tag).lower() == normalized_name
        ]

    def _build_guid(
        self,
        source_id: int,
        guid: Optional[str],
        link: str,
        title: str,
        raw_published: Optional[str],
    ) -> str:
        cleaned_guid = self._clean_optional(guid)
        if cleaned_guid:
            return cleaned_guid

        if link.strip():
            return link.strip()

        digest_input = f"{source_id}|{title.strip()}|{raw_published or ''}"
        return hashlib.sha256(digest_input.encode("utf-8")).hexdigest()

    def _joined_text(self, element: Optional[ET.Element]) -> Optional[str]:
        if element is None:
            return None

        text = "".join(element.itertext()).strip()
        return text or None

    def _local_name(self, tag: str) -> str:
        if "}" in tag:
            return tag.rsplit("}", 1)[-1]
        return tag

    def _clean_optional(self, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None

        cleaned = value.strip()
        return cleaned or None
