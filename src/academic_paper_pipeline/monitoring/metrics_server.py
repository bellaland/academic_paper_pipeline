import sqlite3
from pathlib import Path

import typer
import uvicorn
from fastapi import FastAPI, Response
from prometheus_client import CONTENT_TYPE_LATEST, Gauge, generate_latest

app = FastAPI(title="Academic Paper Pipeline Metrics")
DB_PATH = "academic_papers.db"
papers_total = Gauge(
    "academic_papers_total",
    "Total number of papers stored in the pipeline database.",
)
missing_abstracts_total = Gauge(
    "academic_missing_abstracts_total",
    "Total number of papers with missing abstracts.",
)
extractions_total = Gauge(
    "academic_extractions_total",
    "Total number of paper extraction records.",
)
extraction_coverage = Gauge(
    "academic_extraction_coverage",
    "Share of papers with structured extraction records.",
)
failed_runs_total = Gauge(
    "academic_failed_runs_total",
    "Total number of failed pipeline runs.",
)


def collect_sqlite_metrics(db_path: str = DB_PATH) -> None:
    path = Path(db_path)
    if not path.exists():
        papers_total.set(0)
        missing_abstracts_total.set(0)
        extractions_total.set(0)
        extraction_coverage.set(0)
        failed_runs_total.set(0)
        return
    with sqlite3.connect(path) as conn:
        total_papers = conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
        missing_abstracts = conn.execute(
            """
            SELECT COUNT(*)
            FROM papers
            WHERE abstract IS NULL OR abstract = ''
            """
        ).fetchone()[0]
        total_extractions = conn.execute("SELECT COUNT(*) FROM paper_extractions").fetchone()[0]
        failed_runs = conn.execute(
            """
            SELECT COUNT(*)
            FROM pipeline_runs
            WHERE status = 'failed'
            """
        ).fetchone()[0]
    papers_total.set(total_papers)
    missing_abstracts_total.set(missing_abstracts)
    extractions_total.set(total_extractions)
    extraction_coverage.set(total_extractions / total_papers if total_papers else 0)
    failed_runs_total.set(failed_runs)


@app.get("/metrics")
def metrics() -> Response:
    collect_sqlite_metrics(DB_PATH)
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


cli = typer.Typer(help="Serve Prometheus metrics for the academic paper pipeline.")


@cli.command()
def main(
    db_path: str = typer.Option("academic_papers.db", help="SQLite database path."),
    host: str = typer.Option("127.0.0.1", help="Host to bind."),
    port: int = typer.Option(8000, help="Port to bind."),
) -> None:
    global DB_PATH
    DB_PATH = db_path
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    cli()
