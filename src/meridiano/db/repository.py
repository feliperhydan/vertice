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
    scraped_at: str


@dataclass(frozen=True)
class SourceStats:
    source_id: Optional[int]
    source_name: str
    source_url: str
    category: Optional[str]
    article_count: int
    last_published_at: Optional[str]
    last_scraped_at: Optional[str]


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
                    articles.scraped_at
                FROM articles
                INNER JOIN sources ON sources.id = articles.source_id
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
                scraped_at=str(row["scraped_at"]),
            )
            for row in rows
        ]

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

    def clear_articles(self) -> None:
        with self.database_manager.connect() as connection:
            connection.execute("DELETE FROM articles")

    def clear_all_data(self) -> None:
        with self.database_manager.connect() as connection:
            connection.execute("DELETE FROM articles")
            connection.execute("DELETE FROM sources")
