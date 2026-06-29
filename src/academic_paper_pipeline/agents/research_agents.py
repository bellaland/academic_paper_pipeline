from dataclasses import dataclass
from typing import Any

from academic_paper_pipeline.collectors.arxiv_client import collect_arxiv
from academic_paper_pipeline.collectors.openalex_client import collect_openalex
from academic_paper_pipeline.extractors.langchain_extractor import (
    extract_paper,
    extract_paper_rule_based,
)
from academic_paper_pipeline.reports.generate_report import generate_pipeline_report
from academic_paper_pipeline.storage.sqlite_store import SQLiteStore, new_id, utc_now


@dataclass
class CollectorAgent:
    store: SQLiteStore

    def run(self, query: str, max_results: int = 10) -> dict[str, Any]:
        openalex_result = collect_openalex(
            query=query,
            max_results=max_results,
            store=self.store,
        )
        arxiv_result = collect_arxiv(
            query=query,
            max_results=max_results,
            store=self.store,
        )
        return {
            "openalex": openalex_result,
            "arxiv": arxiv_result,
        }


@dataclass
class ExtractionAgent:
    store: SQLiteStore

    def run(
        self,
        limit: int = 5,
        use_llm: bool = False,
        model_name: str = "gpt-4o-mini",
    ) -> dict[str, int]:
        papers = self.store.get_papers_for_extraction(limit=limit)
        extracted = 0
        failed = 0
        for paper in papers:
            try:
                if use_llm:
                    result = extract_paper(
                        title=paper["title"],
                        abstract=paper["abstract"],
                        model_name=model_name,
                    )
                    extraction_model_name = model_name
                else:
                    result = extract_paper_rule_based(
                        title=paper["title"],
                        abstract=paper["abstract"],
                    )
                    extraction_model_name = "rule_based_v1"
                extraction = {
                    "extraction_id": new_id("extraction"),
                    "paper_id": paper["paper_id"],
                    "research_question": result.research_question,
                    "method": result.method,
                    "dataset": result.dataset,
                    "key_finding": result.key_finding,
                    "field": result.field,
                    "relevance_label": result.relevance_label,
                    "confidence": result.confidence,
                    "model_name": extraction_model_name,
                    "prompt_version": "v1",
                    "raw_output_json": result.model_dump_json(),
                    "created_at": utc_now(),
                }
                self.store.upsert_paper_extraction(extraction)
                extracted += 1
            except Exception as exc:
                failed += 1
                self.store.log_error(
                    run_id=None,
                    source="extraction_agent",
                    record_id=paper["paper_id"],
                    error_type=type(exc).__name__,
                    error_message=str(exc),
                )
        return {"extracted": extracted, "failed": failed}


@dataclass
class QualityCheckAgent:
    store: SQLiteStore

    def run(self) -> dict[str, Any]:
        with self.store.connect() as conn:
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
        extraction_coverage = total_extractions / total_papers if total_papers else 0
        return {
            "total_papers": total_papers,
            "missing_abstracts": missing_abstracts,
            "total_extractions": total_extractions,
            "extraction_coverage": round(extraction_coverage, 3),
            "failed_runs": failed_runs,
        }


@dataclass
class ReportAgent:
    store: SQLiteStore

    def run(self) -> dict[str, str]:
        report_path = generate_pipeline_report(store=self.store)
        return {"report_path": str(report_path)}
