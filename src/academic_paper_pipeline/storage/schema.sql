PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    query TEXT NOT NULL,
    max_results INTEGER NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT NOT NULL,
    records_requested INTEGER DEFAULT 0,
    records_collected INTEGER DEFAULT 0,
    records_failed INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS papers (
    paper_id TEXT PRIMARY KEY,
    doi TEXT,
    title TEXT NOT NULL,
    abstract TEXT,
    publication_year INTEGER,
    publication_date TEXT,
    venue TEXT,
    cited_by_count INTEGER DEFAULT 0,
    source_api TEXT NOT NULL,
    source_url TEXT,
    open_access_pdf_url TEXT,
    ingested_at TEXT NOT NULL,
    raw_record_id TEXT
);

CREATE TABLE IF NOT EXISTS authors (
    author_id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS paper_authors (
    paper_id TEXT NOT NULL,
    author_id TEXT NOT NULL,
    author_position INTEGER,
    PRIMARY KEY (paper_id, author_id),
    FOREIGN KEY (paper_id) REFERENCES papers(paper_id) ON DELETE CASCADE,
    FOREIGN KEY (author_id) REFERENCES authors(author_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS topics (
    topic_id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    score REAL
);

CREATE TABLE IF NOT EXISTS paper_topics (
    paper_id TEXT NOT NULL,
    topic_id TEXT NOT NULL,
    score REAL,
    PRIMARY KEY (paper_id, topic_id),
    FOREIGN KEY (paper_id) REFERENCES papers(paper_id) ON DELETE CASCADE,
    FOREIGN KEY (topic_id) REFERENCES topics(topic_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS raw_records (
    raw_record_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    source TEXT NOT NULL,
    source_record_id TEXT,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES pipeline_runs(run_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS pipeline_events (
    event_id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    message TEXT NOT NULL,
    metadata_json TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES pipeline_runs(run_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS errors (
    error_id TEXT PRIMARY KEY,
    run_id TEXT,
    source TEXT,
    error_type TEXT NOT NULL,
    error_message TEXT NOT NULL,
    record_id TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES pipeline_runs(run_id) ON DELETE SET NULL
);
