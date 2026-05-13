SOURCES_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    url TEXT NOT NULL UNIQUE,
    category TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


ARTICLES_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    link TEXT NOT NULL,
    guid TEXT NOT NULL,
    summary TEXT,
    author TEXT,
    published_at TEXT,
    raw_published TEXT,
    content TEXT,
    language TEXT,
    scraped_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(guid),
    FOREIGN KEY (source_id) REFERENCES sources(id)
);
"""


ARTICLE_CONTENT_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS article_content (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id INTEGER NOT NULL UNIQUE,
    source_url TEXT NOT NULL,
    raw_html TEXT,
    extracted_text TEXT,
    abstract_text TEXT,
    meta_description TEXT,
    jsonld_description TEXT,
    extraction_strategy TEXT,
    fetched_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE CASCADE
);
"""


ARTICLE_SUMMARY_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS article_summary (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id INTEGER NOT NULL,
    summary_type TEXT NOT NULL,
    summary_text TEXT NOT NULL,
    model_name TEXT,
    input_source TEXT,
    prompt_version TEXT,
    generated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE CASCADE
);
"""
