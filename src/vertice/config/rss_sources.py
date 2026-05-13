import json
from pathlib import Path


DEFAULT_RSS_SOURCES = [
    {
        "name": "Nature",
        "url": "https://www.nature.com/nature.rss",
        "category": "ciencia",
    },
    {
        "name": "BBC News",
        "url": "http://feeds.bbci.co.uk/news/rss.xml",
        "category": "noticias",
    },
]


def load_rss_sources(file_path: Path) -> list[dict[str, str]]:
    if not file_path.exists():
        save_rss_sources(file_path, DEFAULT_RSS_SOURCES)
        return list(DEFAULT_RSS_SOURCES)

    with file_path.open("r", encoding="utf-8") as file:
        loaded_sources = json.load(file)

    normalized_sources: list[dict[str, str]] = []
    for source in loaded_sources:
        normalized_sources.append(
            {
                "name": str(source.get("name", "")).strip(),
                "url": str(source.get("url", "")).strip(),
                "category": str(source.get("category", "")).strip(),
            }
        )
    return normalized_sources


def save_rss_sources(file_path: Path, sources: list[dict[str, str]]) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("w", encoding="utf-8") as file:
        json.dump(sources, file, indent=2, ensure_ascii=False)
