from .config.rss_sources import load_rss_sources
from .config.settings import AppSettings
from .db.connection import DatabaseManager
from .db.repository import ArticleRepository
from .services.html_article_extractor import HTMLArticleExtractor
from .services.feed_validator import FeedValidator
from .services.ingestion_service import IngestionService
from .services.rss_fetcher import RSSFetcher
from .services.rss_parser import RSSParser
from .services.source_reader import SourceReader


def build_runtime() -> dict:
    settings = AppSettings()
    database_manager = DatabaseManager(settings.database_path)
    repository = ArticleRepository(database_manager)
    fetcher = RSSFetcher(timeout_seconds=settings.request_timeout_seconds)
    parser = RSSParser()
    html_extractor = HTMLArticleExtractor()
    source_reader = SourceReader(
        fetcher=fetcher,
        parser=parser,
        html_extractor=html_extractor,
    )
    rss_sources = load_rss_sources(settings.rss_sources_path)
    ingestion_service = IngestionService(
        sources=rss_sources,
        repository=repository,
        source_reader=source_reader,
    )
    feed_validator = FeedValidator(
        fetcher=fetcher,
        parser=parser,
        source_reader=source_reader,
    )
    return {
        "settings": settings,
        "repository": repository,
        "ingestion_service": ingestion_service,
        "feed_validator": feed_validator,
        "source_reader": source_reader,
        "rss_sources": rss_sources,
    }
