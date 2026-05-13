from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppSettings:
    database_path: Path = Path("data/vertice.db")
    rss_sources_path: Path = Path("data/rss_sources.json")
    logs_dir: Path = Path("logs")
    app_log_path: Path = Path("logs/vertice.log")
    operation_error_log_path: Path = Path("logs/operation_errors.jsonl")
    request_timeout_seconds: int = 20
    web_host: str = "127.0.0.1"
    web_port: int = 5000
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "ministral-3:3b"
    ollama_timeout_seconds: int = 120
    summary_max_chars: int = 12000
