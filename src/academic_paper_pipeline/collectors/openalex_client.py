import json
import time
from pathlib import Path
from typing import Any

import httpx

from academic_paper_pipeline.config import get_settings
from academic_paper_pipeline.storage.sqlite_store import SQLiteStore, utc_now


def reconstruct_abstract(inverted_index: dict[str, list[int]] | None) -> str | None:
    if not inverted_index:
        return None
    position_to_word: dict[int, str] = {}
    for word, positions in inverted_index.items():
        for position in positions:
            position_to_word[position] = word
    return " ".join(position_to_word[i] for i in sorted(position_to_word))


class OpenAlexClient:
    BASE_URL = "https://api.openalex.org/works"

    def __init__(self, api_key: str | None = None, email: str | None = None) -> None:
        settings = get_settings()
        self.api_key = api_key or settings.openalex_api_key
        self.email = email or settings.openalex_email
        self.client = httpx.Client(timeout=30.0)

    def search_works(self, query: str, max_results: int = 100) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        per_page = min(200, max_results)
        cursor = "*"
        while len(results) < max_results:
            params = {
                "search": query,
                "per-page": per_page,
                "cursor": cursor,
                "sort": "cited_by_count:desc",
            }
            if self.email:
                params["mailto"] = self.email
            if self.api_key:
                params["api_key"] = self.api_key
            response = self.client.get(self.BASE_URL, params=params)
            response.raise_for_status()
            payload = response.json()
            page_results = payload.get("results", [])
            if not page_results:
                break
            results.extend(page_results)
            cursor = payload.get("meta", {}).get("next_cursor")
            if not cursor:
                break
            time.sleep(0.1)
        return results[:max_results]


def normalize_openalex_work(work: dict[str, Any], raw_record_id: str) -> dict[str, Any]:
    primary_location = work.get("primary_location") or {}
    source = primary_location.get("source") or {}
    open_access = work.get("open_access") or {}
    return {
        "paper_id": work.get("id"),
        "doi": work.get("doi"),
        "title": work.get("title") or "Untitled",
        "abstract": reconstruct_abstract(work.get("abstract_inverted_index")),
        "publication_year": work.get("publication_year"),
        "publication_date": work.get("publication_date"),
        "venue": source.get("display_name"),
        "cited_by_count": work.get("cited_by_count") or 0,
        "source_api": "openalex",
        "source_url": work.get("id"),
        "open_access_pdf_url": open_access.get("oa_url"),
        "ingested_at": utc_now(),
        "raw_record_id": raw_record_id,
    }


def write_raw_jsonl(records: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def collect_openalex(
    query: str, max_results: int = 100, store: SQLiteStore | None = None
) -> dict[str, Any]:
    settings = get_settings()
    store = store or SQLiteStore()
    store.initialize()
    run_id = store.create_run(source="openalex", query=query, max_results=max_results)
    client = OpenAlexClient()
    collected = 0
    failed = 0
    try:
        works = client.search_works(query=query, max_results=max_results)
        raw_path = settings.raw_dir / f"openalex_{run_id}.jsonl"
        write_raw_jsonl(works, raw_path)
        for work in works:
            try:
                source_record_id = work.get("id")
                raw_record_id = store.insert_raw_record(
                    run_id=run_id,
                    source="openalex",
                    source_record_id=source_record_id,
                    payload=work,
                )
                paper = normalize_openalex_work(work, raw_record_id=raw_record_id)
                store.upsert_paper(paper)
                collected += 1
                for position, authorship in enumerate(work.get("authorships", [])):
                    author = authorship.get("author") or {}
                    author_id = author.get("id")
                    display_name = author.get("display_name")
                    if author_id and display_name:
                        store.upsert_author(author_id, display_name)
                        store.link_paper_author(paper["paper_id"], author_id, position)
                concepts = work.get("concepts") or []
                topics = work.get("topics") or []
                for concept in concepts:
                    topic_id = concept.get("id")
                    display_name = concept.get("display_name")
                    score = concept.get("score")
                    if topic_id and display_name:
                        store.upsert_topic(topic_id, display_name, score)
                        store.link_paper_topics(paper["paper_id"], topic_id, score)
                for topic in topics:
                    topic_id = topic.get("id")
                    display_name = topic.get("display_name")
                    score = topic.get("score")
                    if topic_id and display_name:
                        store.upsert_topic(topic_id, display_name, score)
                        store.link_paper_topics(paper["paper_id"], topic_id, score)

            except Exception as exc:
                failed += 1
                store.log_error(
                    run_id=run_id,
                    source="openalex",
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
            f"Collected {collected} OpenAlex records with {failed} failures.",
            {"raw_path": str(raw_path)},
        )
        csv_path = store.export_papers_csv()
        return {
            "run_id": run_id,
            "source": "openalex",
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
            source="openalex",
            error_type=type(exc).__name__,
            error_message=str(exc),
        )
        raise
