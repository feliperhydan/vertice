from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class RSSSource:
    name: str
    url: str
    category: Optional[str] = None


@dataclass(frozen=True)
class Article:
    source_id: int
    title: str
    link: str
    guid: str
    summary: Optional[str] = None
    author: Optional[str] = None
    published_at: Optional[str] = None
    raw_published: Optional[str] = None
    content: Optional[str] = None
    language: Optional[str] = None
