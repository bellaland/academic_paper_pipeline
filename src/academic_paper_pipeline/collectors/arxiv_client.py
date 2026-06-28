import time
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

import feedparser
import httpx

from academic_paper_pipeline.config import get_settings
from academic_paper_pipeline.storage.sqlite_store import SQLiteStore, utc_now


class ArxivClient:
    BASE_URL = "https://export.arxiv.org/api/query"

    def __init__(self) -> None:
        self.client = httpx.Client(timeout=30.0, follow_redirects=True)

    def build_url(self, query: str, start: int = 0, max_results: int = 100) -> str:
        encoded_query = quote_plus(query)
        return (
            f"{self.BASE_URL}"
            f"?search_query=all:{encoded_query}"
            f"&start={start}"
            f"&max_results={max_results}"
            f"&sortBy=submittedDate"
            f"&sortOrder=descending"
        )

    def search_works(self, query: str, max_results: int = 100) -> tuple[list[dict[str, Any]], str]:
        url = self.build_url(query=query, start=0, max_results=max_results)
        response = self.client.get(url)
        response.raise_for_status()
        raw_xml = response.text
        feed = feedparser.parse(raw_xml)
        results: list[dict[str, Any]] = []
        for entry in feed.entries[:max_results]:
            results.append(dict(entry))
        time.sleep(0.1)
        return results, raw_xml


def extract_arxiv_id(entry_id: str | None) -> str | None:
    if not entry_id:
        return None
    return entry_id.rstrip("/").split("/")[-1]


def extract_pdf_url(work: dict[str, Any]) -> str | None:
    for link in work.get("links", []):
        if link.get("type") == "application/pdf":
            return link.get("href")
    return None


def normalize_arxiv_work(work: dict[str, Any], raw_record_id: str) -> dict[str, Any]:
    entry_id = work.get("id")
    arxiv_id = extract_arxiv_id(entry_id)
    published = work.get("published")
    publication_year = None
    publication_date = None
    if published:
        publication_date = published[:10]
        try:
            publication_year = int(published[:4])
        except ValueError:
            publication_year = None
    title = " ".join((work.get("title") or "Untitled").split())
    abstract = " ".join((work.get("summary") or "").split())
    return {
        "paper_id": f"arxiv:{arxiv_id}" if arxiv_id else entry_id,
        "doi": work.get("arxiv_doi"),
        "title": title,
        "abstract": abstract,
        "publication_year": publication_year,
        "publication_date": publication_date,
        "venue": "arXiv",
        "cited_by_count": 0,
        "source_api": "arxiv",
        "source_url": entry_id,
        "open_access_pdf_url": extract_pdf_url(work),
        "ingested_at": utc_now(),
        "raw_record_id": raw_record_id,
    }


def write_raw_xml(raw_xml: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(raw_xml, encoding="utf-8")


def collect_arxiv(
    query: str, max_results: int = 100, store: SQLiteStore | None = None
) -> dict[str, Any]:
    settings = get_settings()
    store = store or SQLiteStore()
    store.initialize()
    run_id = store.create_run(source="arxiv", query=query, max_results=max_results)
    client = ArxivClient()
    collected = 0
    failed = 0
    try:
        works, raw_xml = client.search_works(query=query, max_results=max_results)
        raw_path = settings.raw_dir / f"arxiv_{run_id}.xml"
        write_raw_xml(raw_xml, raw_path)
        for work in works:
            try:
                source_record_id = work.get("id")
                raw_record_id = store.insert_raw_record(
                    run_id=run_id,
                    source="arxiv",
                    source_record_id=source_record_id,
                    payload=work,
                )
                paper = normalize_arxiv_work(work, raw_record_id=raw_record_id)
                store.upsert_paper(paper)
                collected += 1
                for position, author in enumerate(work.get("authors", [])):
                    author_name = author.get("name")
                    if author_name:
                        author_id = f"arxiv_author:{author_name.lower().replace(' ', '_')}"
                        store.upsert_author(author_id, author_name)
                        store.link_paper_author(paper["paper_id"], author_id, position)

            except Exception as exc:
                failed += 1
                store.log_error(
                    run_id=run_id,
                    source="arxiv",
                    record_id=work.get("id"),
                    error_type=type(exc).__name__,
                    error_message=str(exc),
                )
        store.finish_run(
            run_id, status="success", records_collected=collected, records_failed=failed
        )
        store.log_event(
            run_id,
            "collection_finished",
            f"Collected {collected} arXiv records with {failed} failures.",
            {"raw_path": str(raw_path)},
        )
        csv_path = store.export_papers_csv()
        return {
            "run_id": run_id,
            "source": "arxiv",
            "query": query,
            "max_results": max_results,
            "collected": collected,
            "failed": failed,
            "raw_path": str(raw_path),
            "csv_path": str(csv_path),
        }
    except Exception as exc:
        store.finish_run(
            run_id, status="failed", records_collected=collected, records_failed=failed + 1
        )
        store.log_error(
            run_id=run_id,
            source="arxiv",
            error_type=type(exc).__name__,
            error_message=str(exc),
        )
        raise
