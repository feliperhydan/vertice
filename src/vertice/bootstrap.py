from .config.rss_sources import load_rss_sources
from .config.settings import AppSettings
from .db.connection import DatabaseManager
from .db.repository import ArticleRepository
from .services.article_analysis_service import ArticleAnalysisService
from .services.article_content_extractor import ArticleContentExtractor
from .services.article_enrichment_service import ArticleEnrichmentService
from .services.article_page_fetcher import ArticlePageFetcher
from .services.article_summarizer import ArticleSummarizer
from .services.html_article_extractor import HTMLArticleExtractor
from .services.feed_validator import FeedValidator
from .services.ingestion_service import IngestionService
from .services.ollama_client import OllamaClient
from .services.operation_error_logger import OperationErrorLogger
from .services.operation_stats_service import OperationStatsService
from .services.rss_fetcher import RSSFetcher
from .services.rss_parser import RSSParser
from .services.source_reader import SourceReader


def build_runtime() -> dict:
    settings = AppSettings()
    operation_error_logger = OperationErrorLogger(settings.operation_error_log_path)
    database_manager = DatabaseManager(settings.database_path)
    repository = ArticleRepository(database_manager)
    fetcher = RSSFetcher(timeout_seconds=settings.request_timeout_seconds)
    parser = RSSParser()
    html_extractor = HTMLArticleExtractor()
    article_page_fetcher = ArticlePageFetcher(fetcher=fetcher)
    article_content_extractor = ArticleContentExtractor()
    source_reader = SourceReader(
        fetcher=fetcher,
        parser=parser,
        html_extractor=html_extractor,
    )
    ollama_client = OllamaClient(
        base_url=settings.ollama_base_url,
        model=settings.ollama_model,
        timeout_seconds=settings.ollama_timeout_seconds,
        error_logger=operation_error_logger,
    )
    article_summarizer = ArticleSummarizer(
        ollama_client=ollama_client,
        max_chars=settings.summary_max_chars,
    )
    rss_sources = load_rss_sources(settings.rss_sources_path)
    ingestion_service = IngestionService(
        sources=rss_sources,
        repository=repository,
        source_reader=source_reader,
    )
    article_enrichment_service = ArticleEnrichmentService(
        repository=repository,
        page_fetcher=article_page_fetcher,
        content_extractor=article_content_extractor,
        error_logger=operation_error_logger,
    )
    article_analysis_service = ArticleAnalysisService(
        repository=repository,
        summarizer=article_summarizer,
        ollama_model=settings.ollama_model,
        error_logger=operation_error_logger,
    )
    feed_validator = FeedValidator(
        fetcher=fetcher,
        parser=parser,
        source_reader=source_reader,
    )
    operation_stats_service = OperationStatsService(
        repository=repository,
        app_log_path=settings.app_log_path,
        operation_error_log_path=settings.operation_error_log_path,
    )
    return {
        "settings": settings,
        "repository": repository,
        "ingestion_service": ingestion_service,
        "article_enrichment_service": article_enrichment_service,
        "article_analysis_service": article_analysis_service,
        "feed_validator": feed_validator,
        "operation_stats_service": operation_stats_service,
        "source_reader": source_reader,
        "rss_sources": rss_sources,
    }
