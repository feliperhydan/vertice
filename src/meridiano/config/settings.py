from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppSettings:
    database_path: Path = Path("data/meridiano.db")
    rss_sources_path: Path = Path("data/rss_sources.json")
    request_timeout_seconds: int = 20
    web_host: str = "127.0.0.1"
    web_port: int = 5000
