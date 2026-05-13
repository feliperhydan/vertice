import logging
from dataclasses import dataclass
from time import perf_counter

from ..db.repository import ArticleContentRecord


@dataclass(frozen=True)
class BatchProcessSummary:
    processed: int
    skipped: int
    errors: int


class ArticleEnrichmentService:
    def __init__(self, repository, page_fetcher, content_extractor, error_logger=None) -> None:
        self.repository = repository
        self.page_fetcher = page_fetcher
        self.content_extractor = content_extractor
        self.error_logger = error_logger
        self.logger = logging.getLogger(__name__)

    def enrich_pending_articles(self, limit: int = 25) -> BatchProcessSummary:
        batch_started_at = perf_counter()
        processed = 0
        skipped = 0
        errors = 0
        pending_articles = self.repository.list_articles_for_enrichment(limit=limit)

        self.logger.info(
            "[ENRICH] starting batch | limit=%s | total_candidates=%s",
            limit,
            len(pending_articles),
        )

        for article in pending_articles:
            if not article.link.strip():
                skipped += 1
                self.logger.warning(
                    "[ENRICH] article=%s | title=%r | status=skipped | reason=missing_link",
                    article.id,
                    article.title,
                )
                continue

            article_started_at = perf_counter()
            try:
                self.logger.info(
                    "[ENRICH] article=%s | title=%r | step=fetch_page | url=%s",
                    article.id,
                    article.title,
                    article.link,
                )
                final_url, html_content, content_type = self.page_fetcher.fetch_page(article.link)

                self.logger.info(
                    "[ENRICH] article=%s | title=%r | step=extract_content | final_url=%s | content_type=%s",
                    article.id,
                    article.title,
                    final_url,
                    content_type or "unknown",
                )
                extracted = self.content_extractor.extract(html_content)

                self.logger.info(
                    "[ENRICH] article=%s | title=%r | step=save_content | strategy=%s | abstract=%s | extracted_text=%s",
                    article.id,
                    article.title,
                    extracted.extraction_strategy,
                    bool(extracted.abstract_text),
                    bool(extracted.extracted_text),
                )
                self.repository.upsert_article_content(
                    ArticleContentRecord(
                        article_id=article.id,
                        source_url=final_url,
                        raw_html=extracted.raw_html,
                        extracted_text=extracted.extracted_text,
                        abstract_text=extracted.abstract_text,
                        meta_description=extracted.meta_description,
                        jsonld_description=extracted.jsonld_description,
                        extraction_strategy=extracted.extraction_strategy,
                    )
                )
                processed += 1
                elapsed_seconds = perf_counter() - article_started_at
                self.logger.info(
                    "[ENRICH] article=%s | title=%r | status=success | processed=%s | skipped=%s | errors=%s | elapsed=%.2fs",
                    article.id,
                    article.title,
                    processed,
                    skipped,
                    errors,
                    elapsed_seconds,
                )
            except Exception as exc:
                errors += 1
                elapsed_seconds = perf_counter() - article_started_at
                if self.error_logger is not None:
                    self.error_logger.log_error(
                        operation="article_enrichment",
                        stage="enrich_article",
                        error=exc,
                        context={
                            "article_id": article.id,
                            "title": article.title,
                            "article_url": article.link,
                            "elapsed_seconds": round(elapsed_seconds, 2),
                        },
                    )
                self.logger.exception(
                    "[ENRICH] article=%s | title=%r | status=error | elapsed=%.2fs | message=%s",
                    article.id,
                    article.title,
                    elapsed_seconds,
                    exc,
                )

        batch_elapsed_seconds = perf_counter() - batch_started_at
        self.logger.info(
            "[ENRICH] batch finished | processed=%s | skipped=%s | errors=%s | elapsed=%.2fs",
            processed,
            skipped,
            errors,
            batch_elapsed_seconds,
        )
        return BatchProcessSummary(
            processed=processed,
            skipped=skipped,
            errors=errors,
        )
