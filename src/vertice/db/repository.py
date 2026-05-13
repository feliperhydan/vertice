import sqlite3
from dataclasses import dataclass
from typing import Optional

from ..models.article import Article, RSSSource


@dataclass(frozen=True)
class PersistResult:
    inserted: bool
    article_id: Optional[int] = None


@dataclass(frozen=True)
class ArticleListItem:
    id: int
    source_name: str
    source_category: Optional[str]
    title: str
    link: str
    author: Optional[str]
    published_at: Optional[str]
    summary: Optional[str]
    generated_summary: Optional[str]
    enrichment_strategy: Optional[str]
    summary_model: Optional[str]
    scraped_at: str


@dataclass(frozen=True)
class ArticleForProcessing:
    id: int
    source_id: int
    title: str
    link: str
    summary: Optional[str]
    content: Optional[str]


@dataclass(frozen=True)
class ArticleContentRecord:
    article_id: int
    source_url: str
    raw_html: Optional[str]
    extracted_text: Optional[str]
    abstract_text: Optional[str]
    meta_description: Optional[str]
    jsonld_description: Optional[str]
    extraction_strategy: Optional[str]


@dataclass(frozen=True)
class ArticleSummaryRecord:
    article_id: int
    summary_type: str
    summary_text: str
    model_name: Optional[str]
    input_source: Optional[str]
    prompt_version: Optional[str]


@dataclass(frozen=True)
class SourceStats:
    source_id: Optional[int]
    source_name: str
    source_url: str
    category: Optional[str]
    article_count: int
    last_published_at: Optional[str]
    last_scraped_at: Optional[str]


@dataclass(frozen=True)
class ProcessingCounts:
    total_articles: int
    total_sources: int
    enriched_articles: int
    summarized_articles: int
    pending_enrichment: int
    pending_summary: int


class ArticleRepository:
    def __init__(self, database_manager) -> None:
        self.database_manager = database_manager

    def upsert_source(self, source: RSSSource) -> int:
        with self.database_manager.connect() as connection:
            existing = connection.execute(
                "SELECT id FROM sources WHERE url = ?",
                (source.url,),
            ).fetchone()
            if existing:
                connection.execute(
                    """
                    UPDATE sources
                    SET name = ?, category = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (source.name, source.category, existing["id"]),
                )
                return int(existing["id"])

            cursor = connection.execute(
                """
                INSERT INTO sources (name, url, category)
                VALUES (?, ?, ?)
                """,
                (source.name, source.url, source.category),
            )
            return int(cursor.lastrowid)

    def insert_article(self, article: Article) -> PersistResult:
        try:
            with self.database_manager.connect() as connection:
                cursor = connection.execute(
                    """
                    INSERT INTO articles (
                        source_id,
                        title,
                        link,
                        guid,
                        summary,
                        author,
                        published_at,
                        raw_published,
                        content,
                        language
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        article.source_id,
                        article.title,
                        article.link,
                        article.guid,
                        article.summary,
                        article.author,
                        article.published_at,
                        article.raw_published,
                        article.content,
                        article.language,
                    ),
                )
                return PersistResult(inserted=True, article_id=int(cursor.lastrowid))
        except sqlite3.IntegrityError:
            return PersistResult(inserted=False, article_id=None)

    def list_articles(self, limit: int = 200) -> list[ArticleListItem]:
        with self.database_manager.connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    articles.id,
                    sources.name AS source_name,
                    sources.category AS source_category,
                    articles.title,
                    articles.link,
                    articles.author,
                    articles.published_at,
                    articles.summary,
                    article_content.extraction_strategy AS enrichment_strategy,
                    latest_summary.summary_text AS generated_summary,
                    latest_summary.model_name AS summary_model,
                    articles.scraped_at
                FROM articles
                INNER JOIN sources ON sources.id = articles.source_id
                LEFT JOIN article_content ON article_content.article_id = articles.id
                LEFT JOIN (
                    SELECT s1.article_id, s1.summary_text, s1.model_name
                    FROM article_summary s1
                    INNER JOIN (
                        SELECT article_id, MAX(id) AS max_id
                        FROM article_summary
                        WHERE summary_type = 'short'
                        GROUP BY article_id
                    ) s2 ON s1.id = s2.max_id
                ) latest_summary ON latest_summary.article_id = articles.id
                ORDER BY
                    COALESCE(articles.published_at, articles.scraped_at) DESC,
                    articles.id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return [
            ArticleListItem(
                id=int(row["id"]),
                source_name=str(row["source_name"]),
                source_category=row["source_category"],
                title=str(row["title"]),
                link=str(row["link"]),
                author=row["author"],
                published_at=row["published_at"],
                summary=row["summary"],
                generated_summary=row["generated_summary"],
                enrichment_strategy=row["enrichment_strategy"],
                summary_model=row["summary_model"],
                scraped_at=str(row["scraped_at"]),
            )
            for row in rows
        ]

    def list_articles_for_enrichment(self, limit: int = 50) -> list[ArticleForProcessing]:
        with self.database_manager.connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    articles.id,
                    articles.source_id,
                    articles.title,
                    articles.link,
                    articles.summary,
                    articles.content
                FROM articles
                LEFT JOIN article_content ON article_content.article_id = articles.id
                WHERE article_content.article_id IS NULL
                ORDER BY articles.id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return [
            ArticleForProcessing(
                id=int(row["id"]),
                source_id=int(row["source_id"]),
                title=str(row["title"]),
                link=str(row["link"]),
                summary=row["summary"],
                content=row["content"],
            )
            for row in rows
        ]

    def list_articles_for_summary(self, limit: int = 50) -> list[ArticleForProcessing]:
        with self.database_manager.connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    articles.id,
                    articles.source_id,
                    articles.title,
                    articles.link,
                    articles.summary,
                    articles.content
                FROM articles
                LEFT JOIN article_summary
                    ON article_summary.article_id = articles.id
                    AND article_summary.summary_type = 'short'
                WHERE article_summary.id IS NULL
                ORDER BY articles.id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return [
            ArticleForProcessing(
                id=int(row["id"]),
                source_id=int(row["source_id"]),
                title=str(row["title"]),
                link=str(row["link"]),
                summary=row["summary"],
                content=row["content"],
            )
            for row in rows
        ]

    def get_article_content(self, article_id: int) -> Optional[ArticleContentRecord]:
        with self.database_manager.connect() as connection:
            row = connection.execute(
                """
                SELECT
                    article_id,
                    source_url,
                    raw_html,
                    extracted_text,
                    abstract_text,
                    meta_description,
                    jsonld_description,
                    extraction_strategy
                FROM article_content
                WHERE article_id = ?
                """,
                (article_id,),
            ).fetchone()

        if row is None:
            return None

        return ArticleContentRecord(
            article_id=int(row["article_id"]),
            source_url=str(row["source_url"]),
            raw_html=row["raw_html"],
            extracted_text=row["extracted_text"],
            abstract_text=row["abstract_text"],
            meta_description=row["meta_description"],
            jsonld_description=row["jsonld_description"],
            extraction_strategy=row["extraction_strategy"],
        )

    def upsert_article_content(self, record: ArticleContentRecord) -> None:
        with self.database_manager.connect() as connection:
            connection.execute(
                """
                INSERT INTO article_content (
                    article_id,
                    source_url,
                    raw_html,
                    extracted_text,
                    abstract_text,
                    meta_description,
                    jsonld_description,
                    extraction_strategy
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(article_id) DO UPDATE SET
                    source_url = excluded.source_url,
                    raw_html = excluded.raw_html,
                    extracted_text = excluded.extracted_text,
                    abstract_text = excluded.abstract_text,
                    meta_description = excluded.meta_description,
                    jsonld_description = excluded.jsonld_description,
                    extraction_strategy = excluded.extraction_strategy,
                    fetched_at = CURRENT_TIMESTAMP
                """,
                (
                    record.article_id,
                    record.source_url,
                    record.raw_html,
                    record.extracted_text,
                    record.abstract_text,
                    record.meta_description,
                    record.jsonld_description,
                    record.extraction_strategy,
                ),
            )

    def insert_article_summary(self, record: ArticleSummaryRecord) -> None:
        with self.database_manager.connect() as connection:
            connection.execute(
                """
                INSERT INTO article_summary (
                    article_id,
                    summary_type,
                    summary_text,
                    model_name,
                    input_source,
                    prompt_version
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    record.article_id,
                    record.summary_type,
                    record.summary_text,
                    record.model_name,
                    record.input_source,
                    record.prompt_version,
                ),
            )

    def list_source_stats(self) -> list[SourceStats]:
        with self.database_manager.connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    sources.id AS source_id,
                    sources.name AS source_name,
                    sources.url AS source_url,
                    sources.category AS category,
                    COUNT(articles.id) AS article_count,
                    MAX(articles.published_at) AS last_published_at,
                    MAX(articles.scraped_at) AS last_scraped_at
                FROM sources
                LEFT JOIN articles ON articles.source_id = sources.id
                GROUP BY sources.id, sources.name, sources.url, sources.category
                ORDER BY article_count DESC, sources.name ASC
                """
            ).fetchall()

        return [
            SourceStats(
                source_id=int(row["source_id"]) if row["source_id"] is not None else None,
                source_name=str(row["source_name"]),
                source_url=str(row["source_url"]),
                category=row["category"],
                article_count=int(row["article_count"]),
                last_published_at=row["last_published_at"],
                last_scraped_at=row["last_scraped_at"],
            )
            for row in rows
        ]

    def get_dashboard_counts(self) -> dict[str, int]:
        with self.database_manager.connect() as connection:
            articles_count = connection.execute(
                "SELECT COUNT(*) AS total FROM articles"
            ).fetchone()
            sources_count = connection.execute(
                "SELECT COUNT(*) AS total FROM sources"
            ).fetchone()
        return {
            "articles": int(articles_count["total"]),
            "sources": int(sources_count["total"]),
        }

    def get_processing_counts(self) -> ProcessingCounts:
        with self.database_manager.connect() as connection:
            row = connection.execute(
                """
                SELECT
                    (SELECT COUNT(*) FROM articles) AS total_articles,
                    (SELECT COUNT(*) FROM sources) AS total_sources,
                    (SELECT COUNT(*) FROM article_content) AS enriched_articles,
                    (
                        SELECT COUNT(DISTINCT article_id)
                        FROM article_summary
                        WHERE summary_type = 'short'
                    ) AS summarized_articles,
                    (
                        SELECT COUNT(*)
                        FROM articles
                        LEFT JOIN article_content ON article_content.article_id = articles.id
                        WHERE article_content.article_id IS NULL
                    ) AS pending_enrichment,
                    (
                        SELECT COUNT(*)
                        FROM articles
                        LEFT JOIN article_summary
                            ON article_summary.article_id = articles.id
                            AND article_summary.summary_type = 'short'
                        WHERE article_summary.id IS NULL
                    ) AS pending_summary
                """
            ).fetchone()

        return ProcessingCounts(
            total_articles=int(row["total_articles"]),
            total_sources=int(row["total_sources"]),
            enriched_articles=int(row["enriched_articles"]),
            summarized_articles=int(row["summarized_articles"]),
            pending_enrichment=int(row["pending_enrichment"]),
            pending_summary=int(row["pending_summary"]),
        )

    def clear_articles(self) -> None:
        with self.database_manager.connect() as connection:
            connection.execute("DELETE FROM articles")

    def clear_all_data(self) -> None:
        with self.database_manager.connect() as connection:
            connection.execute("DELETE FROM articles")
            connection.execute("DELETE FROM sources")
