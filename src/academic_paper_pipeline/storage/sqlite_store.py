import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from academic_paper_pipeline.config import get_settings


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


class SQLiteStore:
    def __init__(self, db_path: str | Path = "academic_papers.db") -> None:
        self.db_path = Path(db_path)
        self.schema_path = Path(__file__).with_name("schema.sql")

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def initialize(self) -> None:
        with self.connect() as conn:
            conn.executescript(self.schema_path.read_text())

    def create_run(self, source: str, query: str, max_results: int) -> str:
        run_id = new_id("run")
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO pipeline_runs (
                    run_id, source, query, max_results, started_at, status, records_requested
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (run_id, source, query, max_results, utc_now(), "running", max_results),
            )
        return run_id

    def finish_run(
        self,
        run_id: str,
        status: str,
        records_collected: int,
        records_failed: int = 0,
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE pipeline_runs
                SET finished_at = ?, status = ?, records_collected = ?, records_failed = ?
                WHERE run_id = ?
                """,
                (utc_now(), status, records_collected, records_failed, run_id),
            )

    def log_event(
        self, run_id: str, event_type: str, message: str, metadata: dict | None = None
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO pipeline_events (
                    event_id, run_id, event_type, message, metadata_json, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    new_id("event"),
                    run_id,
                    event_type,
                    message,
                    json.dumps(metadata or {}, ensure_ascii=False),
                    utc_now(),
                ),
            )

    def log_error(
        self,
        error_type: str,
        error_message: str,
        run_id: str | None = None,
        source: str | None = None,
        record_id: str | None = None,
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO errors (
                    error_id, run_id, source, error_type, error_message, record_id, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (new_id("error"), run_id, source, error_type, error_message, record_id, utc_now()),
            )

    def insert_raw_record(
        self,
        run_id: str,
        source: str,
        source_record_id: str | None,
        payload: dict[str, Any],
    ) -> str:
        raw_record_id = new_id("raw")
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO raw_records (
                    raw_record_id, run_id, source, source_record_id, payload_json, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    raw_record_id,
                    run_id,
                    source,
                    source_record_id,
                    json.dumps(payload, ensure_ascii=False),
                    utc_now(),
                ),
            )
        return raw_record_id

    def upsert_paper(self, paper: dict[str, Any]) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO papers (
                    paper_id, doi, title, abstract, publication_year, publication_date,
                    venue, cited_by_count, source_api, source_url, open_access_pdf_url,
                    ingested_at, raw_record_id)
                VALUES(
                    :paper_id, :doi, :title, :abstract, :publication_year, :publication_date,
                    :venue, :cited_by_count, :source_api, :source_url, :open_access_pdf_url,
                    :ingested_at, :raw_record_id
                )
                ON CONFLICT(paper_id) DO UPDATE SET
                    doi = excluded.doi,
                    title = excluded.title,
                    abstract = excluded.abstract,
                    publication_year = excluded.publication_year,
                    publication_date = excluded.publication_date,
                    venue = excluded.venue,
                    cited_by_count = excluded.cited_by_count,
                    source_api = excluded.source_api,
                    source_url = excluded.source_url,
                    open_access_pdf_url = excluded.open_access_pdf_url,
                    ingested_at = excluded.ingested_at,
                    raw_record_id = excluded.raw_record_id
                """,
                paper,
            )

    def upsert_author(self, author_id: str, display_name: str) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO authors (author_id, display_name)
                VALUES (?, ?)
                ON CONFLICT(author_id) DO UPDATE SET display_name = excluded.display_name
                """,
                (author_id, display_name),
            )

    def link_paper_author(self, paper_id: str, author_id: str, position: int) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO paper_authors (paper_id, author_id, author_position)
                VALUES (?, ?, ?)
                """,
                (paper_id, author_id, position),
            )

    def upsert_topic(self, topic_id: str, display_name: str, score: float | None) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO topics (topic_id, display_name, score)
                VALUES (?, ?, ?)
                ON CONFLICT(topic_id) DO UPDATE SET
                    display_name = excluded.display_name,
                    score = excluded.score
                """,
                (topic_id, display_name, score),
            )

    def link_paper_topics(self, paper_id: str, topic_id: str, score: float | None) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO paper_topics (paper_id, topic_id, score)
                VALUES (?, ?, ?)
                """,
                (paper_id, topic_id, score),
            )

    def export_papers_csv(self) -> Path:
        import pandas as pd

        settings = get_settings()
        output_path = settings.outputs_dir / "papers.csv"
        with self.connect() as conn:
            df = pd.read_sql_query(
                """
                SELECT
                    paper_id, doi, title, abstract, publication_year, publication_date,
                    venue, cited_by_count, source_api, source_url, open_access_pdf_url, ingested_at
                FROM papers
                ORDER BY cited_by_count DESC, publication_year DESC
                """,
                conn,
            )
        df.to_csv(output_path, index=False)
        return output_path

    def get_papers_for_extraction(self, limit: int = 10) -> list[dict[str, Any]]:
        with self.connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT paper_id, title, abstract, publication_year, source_api
                FROM papers
                WHERE abstract IS NOT NULL
                    AND abstract != ''
                    AND paper_id NOT IN (
                        SELECT paper_id FROM paper_extractions
                    )
                ORDER BY publication_year DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [dict(row) for row in rows]

    def upsert_paper_extraction(self, extraction: dict[str, Any]) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO paper_extractions(
                    extraction_id,
                    paper_id,
                    research_question,
                    method,
                    dataset,
                    key_finding,
                    field,
                    relevance_label,
                    confidence,
                    model_name,
                    prompt_version,
                    raw_output_json,
                    created_at
                )
                VALUES (
                    :extraction_id,
                    :paper_id,
                    :research_question,
                    :method,
                    :dataset,
                    :key_finding,
                    :field,
                    :relevance_label,
                    :confidence,
                    :model_name,
                    :prompt_version,
                    :raw_output_json,
                    :created_at
                )
                ON CONFLICT(extraction_id) DO UPDATE SET
                    research_question = excluded.research_question,
                    method = excluded.method,
                    dataset = excluded.dataset,
                    key_finding = excluded.key_finding,
                    field = excluded.field,
                    relevance_label = excluded.relevance_label,
                    confidence = excluded.confidence,
                    model_name = excluded.model_name,
                    prompt_version = excluded.prompt_version,
                    raw_output_json = excluded.raw_output_json,
                    created_at = excluded.created_at
                """,
                extraction,
            )
