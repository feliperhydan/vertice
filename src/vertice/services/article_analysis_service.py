import logging
from time import perf_counter

from .article_enrichment_service import BatchProcessSummary
from .ollama_client import OllamaConfigurationError
from ..db.repository import ArticleSummaryRecord


class ArticleAnalysisService:
    def __init__(self, repository, summarizer, ollama_model: str, error_logger=None) -> None:
        self.repository = repository
        self.summarizer = summarizer
        self.ollama_model = ollama_model
        self.error_logger = error_logger
        self.logger = logging.getLogger(__name__)

    def summarize_pending_articles(self, limit: int = 25) -> BatchProcessSummary:
        batch_started_at = perf_counter()
        processed = 0
        skipped = 0
        errors = 0
        pending_articles = self.repository.list_articles_for_summary(limit=limit)

        self.logger.info(
            "[SUMMARY] starting batch | limit=%s | total_candidates=%s | model=%s",
            limit,
            len(pending_articles),
            self.ollama_model,
        )

        for article in pending_articles:
            content_record = self.repository.get_article_content(article.id)
            if content_record is None:
                skipped += 1
                self.logger.warning(
                    "[SUMMARY] article=%s | title=%r | status=skipped | reason=missing_enriched_content",
                    article.id,
                    article.title,
                )
                continue

            article_started_at = perf_counter()
            try:
                self.logger.info(
                    "[SUMMARY] article=%s | title=%r | step=select_input | abstract=%s | extracted_text=%s | source_content=%s | source_summary=%s",
                    article.id,
                    article.title,
                    bool(content_record.abstract_text),
                    bool(content_record.extracted_text),
                    bool(article.content),
                    bool(article.summary),
                )
                summary = self.summarizer.summarize(
                    title=article.title,
                    source_summary=article.summary,
                    source_content=article.content,
                    abstract_text=content_record.abstract_text,
                    extracted_text=content_record.extracted_text,
                    meta_description=content_record.meta_description,
                    jsonld_description=content_record.jsonld_description,
                    context={
                        "article_id": article.id,
                        "title": article.title,
                        "article_url": article.link,
                        "model": self.ollama_model,
                    },
                )
                self.logger.info(
                    "[SUMMARY] article=%s | title=%r | step=save_summary | input_source=%s | chars=%s",
                    article.id,
                    article.title,
                    summary.input_source,
                    len(summary.summary_text),
                )
                self.repository.insert_article_summary(
                    ArticleSummaryRecord(
                        article_id=article.id,
                        summary_type="short",
                        summary_text=summary.summary_text,
                        model_name=self.ollama_model,
                        input_source=summary.input_source,
                        prompt_version=summary.prompt_version,
                    )
                )
                processed += 1
                elapsed_seconds = perf_counter() - article_started_at
                self.logger.info(
                    "[SUMMARY] article=%s | title=%r | status=success | processed=%s | skipped=%s | errors=%s | elapsed=%.2fs",
                    article.id,
                    article.title,
                    processed,
                    skipped,
                    errors,
                    elapsed_seconds,
                )
            except OllamaConfigurationError as exc:
                errors += 1
                elapsed_seconds = perf_counter() - article_started_at
                if self.error_logger is not None:
                    self.error_logger.log_error(
                        operation="article_summary",
                        stage="summarize_article_configuration",
                        error=exc,
                        context={
                            "article_id": article.id,
                            "title": article.title,
                            "article_url": article.link,
                            "model": self.ollama_model,
                            "elapsed_seconds": round(elapsed_seconds, 2),
                        },
                    )
                self.logger.exception(
                    "[SUMMARY] article=%s | title=%r | status=error | kind=configuration | elapsed=%.2fs | message=%s",
                    article.id,
                    article.title,
                    elapsed_seconds,
                    exc,
                )
                self.logger.error(
                    "[SUMMARY] aborting batch early | reason=ollama_configuration_error | processed=%s | skipped=%s | errors=%s",
                    processed,
                    skipped,
                    errors,
                )
                break
            except Exception as exc:
                errors += 1
                elapsed_seconds = perf_counter() - article_started_at
                if self.error_logger is not None:
                    self.error_logger.log_error(
                        operation="article_summary",
                        stage="summarize_article",
                        error=exc,
                        context={
                            "article_id": article.id,
                            "title": article.title,
                            "article_url": article.link,
                            "model": self.ollama_model,
                            "has_abstract_text": bool(content_record.abstract_text),
                            "has_extracted_text": bool(content_record.extracted_text),
                            "has_source_content": bool(article.content),
                            "has_source_summary": bool(article.summary),
                            "elapsed_seconds": round(elapsed_seconds, 2),
                        },
                    )
                self.logger.exception(
                    "[SUMMARY] article=%s | title=%r | status=error | elapsed=%.2fs | message=%s",
                    article.id,
                    article.title,
                    elapsed_seconds,
                    exc,
                )

        batch_elapsed_seconds = perf_counter() - batch_started_at
        self.logger.info(
            "[SUMMARY] batch finished | processed=%s | skipped=%s | errors=%s | model=%s | elapsed=%.2fs",
            processed,
            skipped,
            errors,
            self.ollama_model,
            batch_elapsed_seconds,
        )
        return BatchProcessSummary(
            processed=processed,
            skipped=skipped,
            errors=errors,
        )
