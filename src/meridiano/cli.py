import logging

from .config.rss_sources import load_rss_sources
from .config.settings import AppSettings
from .db.connection import DatabaseManager
from .db.repository import ArticleRepository
from .logging_config import configure_logging
from .services.ingestion_service import IngestionService
from .services.rss_fetcher import RSSFetcher
from .services.rss_parser import RSSParser


def main() -> None:
    configure_logging()
    logger = logging.getLogger(__name__)

    settings = AppSettings()
    rss_sources = load_rss_sources(settings.rss_sources_path)
    database_manager = DatabaseManager(settings.database_path)
    repository = ArticleRepository(database_manager)
    fetcher = RSSFetcher(timeout_seconds=settings.request_timeout_seconds)
    parser = RSSParser()
    ingestion_service = IngestionService(
        sources=rss_sources,
        repository=repository,
        fetcher=fetcher,
        parser=parser,
    )

    logger.info("Starting Meridiano RSS ingestion")
    ingestion_summary = ingestion_service.run()
    logger.info(
        "Ingestion completed | new_articles=%s | skipped_duplicates=%s | errors=%s",
        ingestion_summary.new_articles,
        ingestion_summary.skipped_duplicates,
        ingestion_summary.errors,
    )
