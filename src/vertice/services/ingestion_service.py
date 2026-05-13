import logging
from dataclasses import dataclass

from ..models.article import RSSSource


@dataclass(frozen=True)
class SourceIngestionSummary:
    source_name: str
    source_url: str
    fetched_items: int
    new_articles: int
    skipped_duplicates: int
    strategy: str | None = None
    error: str | None = None


@dataclass(frozen=True)
class IngestionSummary:
    new_articles: int
    skipped_duplicates: int
    errors: int
    sources: list[SourceIngestionSummary]


class IngestionService:
    def __init__(self, sources, repository, source_reader) -> None:
        self.sources = sources
        self.repository = repository
        self.source_reader = source_reader
        self.logger = logging.getLogger(__name__)

    def run(self) -> IngestionSummary:
        new_articles = 0
        skipped_duplicates = 0
        errors = 0
        source_summaries: list[SourceIngestionSummary] = []

        for source_data in self.sources:
            source = RSSSource(**source_data)
            self.logger.info(
                "Processing source | name=%s | url=%s",
                source.name,
                source.url,
            )

            try:
                source_id = self.repository.upsert_source(source)
                read_result = self.source_reader.read(source.url, source_id=source_id)
                articles = read_result.articles
                if not articles:
                    message = (
                        "No articles were found in the source. "
                        f"final_url={read_result.final_url} "
                        f"content_type={read_result.content_type or 'unknown'}"
                    )
                    raise ValueError(message)
            except Exception as exc:
                errors += 1
                source_summary = SourceIngestionSummary(
                    source_name=source.name,
                    source_url=source.url,
                    fetched_items=0,
                    new_articles=0,
                    skipped_duplicates=0,
                    strategy=None,
                    error=str(exc),
                )
                source_summaries.append(source_summary)
                self.logger.exception(
                    "Failed to process source %s: %s",
                    source.url,
                    exc,
                )
                self.logger.info(
                    "RSS report | name=%s | fetched_items=%s | new_articles=%s | duplicates=%s | status=error | message=%s",
                    source_summary.source_name,
                    source_summary.fetched_items,
                    source_summary.new_articles,
                    source_summary.skipped_duplicates,
                    source_summary.error,
                )
                continue

            source_new_articles = 0
            source_skipped_duplicates = 0
            for article in articles:
                result = self.repository.insert_article(article)
                if result.inserted:
                    new_articles += 1
                    source_new_articles += 1
                else:
                    skipped_duplicates += 1
                    source_skipped_duplicates += 1

            source_summary = SourceIngestionSummary(
                source_name=source.name,
                source_url=source.url,
                fetched_items=len(articles),
                new_articles=source_new_articles,
                skipped_duplicates=source_skipped_duplicates,
                strategy=read_result.strategy,
                error=None,
            )
            source_summaries.append(source_summary)
            self.logger.info(
                "RSS report | name=%s | fetched_items=%s | new_articles=%s | duplicates=%s | strategy=%s | status=success",
                source_summary.source_name,
                source_summary.fetched_items,
                source_summary.new_articles,
                source_summary.skipped_duplicates,
                source_summary.strategy,
            )

        self.logger.info(
            "[SCRAPE] batch finished | new_articles=%s | duplicates=%s | errors=%s | sources=%s",
            new_articles,
            skipped_duplicates,
            errors,
            len(source_summaries),
        )
        return IngestionSummary(
            new_articles=new_articles,
            skipped_duplicates=skipped_duplicates,
            errors=errors,
            sources=source_summaries,
        )
