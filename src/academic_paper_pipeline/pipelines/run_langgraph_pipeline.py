from pathlib import Path
from typing import Any, TypedDict

import typer
from langgraph.graph import END, START, StateGraph
from rich.console import Console

from academic_paper_pipeline.collectors.arxiv_client import collect_arxiv
from academic_paper_pipeline.collectors.openalex_client import collect_openalex
from academic_paper_pipeline.extractors.langchain_extractor import (
    extract_paper,
    extract_paper_rule_based,
)
from academic_paper_pipeline.reports.generate_report import generate_pipeline_report
from academic_paper_pipeline.storage.sqlite_store import SQLiteStore, new_id, utc_now

app = typer.Typer(help="Run the full academic paper pipeline with LangGraph.")
console = Console()


class PipelineState(TypedDict, total=False):
    query: str
    max_results: int
    extract_limit: int
    db_path: str
    use_llm: bool
    model_name: str
    openalex_result: dict[str, Any]
    arxiv_result: dict[str, Any]
    extracted: int
    failed_extractions: int
    report_path: str


def collect_openalex_node(state: PipelineState) -> PipelineState:
    store = SQLiteStore(state["db_path"])
    result = collect_openalex(
        query=state["query"],
        max_results=state["max_results"],
        store=store,
    )
    return {"openalex_result": result}


def collect_arxiv_node(state: PipelineState) -> PipelineState:
    store = SQLiteStore(state["db_path"])
    result = collect_arxiv(
        query=state["query"],
        max_results=state["max_results"],
        store=store,
    )
    return {"arxiv_result": result}


def extract_papers_node(state: PipelineState) -> PipelineState:
    store = SQLiteStore(state["db_path"])
    store.initialize()
    papers = store.get_papers_for_extraction(limit=state["extract_limit"])
    extracted = 0
    failed = 0
    for paper in papers:
        try:
            if state["use_llm"]:
                result = extract_paper(
                    title=paper["title"],
                    abstract=paper["abstract"],
                    model_name=state["model_name"],
                )
                extraction_model_name = state["model_name"]
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
            store.upsert_paper_extraction(extraction)
            extracted += 1
        except Exception as exc:
            failed += 1
            store.log_error(
                run_id=None,
                source="extraction",
                record_id=paper["paper_id"],
                error_type=type(exc).__name__,
                error_message=str(exc),
            )
    return {"extracted": extracted, "failed_extractions": failed}


def generate_report_node(state: PipelineState) -> PipelineState:
    store = SQLiteStore(state["db_path"])
    report_path = generate_pipeline_report(store=store)
    return {"report_path": str(report_path)}


def build_graph():
    graph = StateGraph(PipelineState)
    graph.add_node("collect_openalex", collect_openalex_node)
    graph.add_node("collect_arxiv", collect_arxiv_node)
    graph.add_node("extract_papers", extract_papers_node)
    graph.add_node("generate_report", generate_report_node)
    graph.add_edge(START, "collect_openalex")
    graph.add_edge("collect_openalex", "collect_arxiv")
    graph.add_edge("collect_arxiv", "extract_papers")
    graph.add_edge("extract_papers", "generate_report")
    graph.add_edge("generate_report", END)
    return graph.compile()


@app.command()
def main(
    query: str = typer.Option("aritificial intelligence accounting", help="Search query."),
    max_results: int = typer.Option(10, help="Number of papers per source."),
    extract_limit: int = typer.Option(5, help="Number of papers to extract."),
    db_path: str = typer.Option("academic_papers.db", help="SQLite database path."),
    model_name: str = typer.Option("gpt-4o-mini", help="LLM model name."),
    use_llm: bool = typer.Option(False, help="Use LangChain/OpenAI extraction."),
) -> None:
    pipeline = build_graph()
    initial_state = {
        "query": query,
        "max_results": max_results,
        "extract_limit": extract_limit,
        "db_path": db_path,
        "model_name": model_name,
        "use_llm": use_llm,
    }
    console.print("[bold green]Streaming LangGraph pipeline[/bold green]")
    final_result = None
    for update in pipeline.stream(initial_state, stream_mode="updates"):
        console.print(update)
        final_result = update
    console.print("[bold green]LangGraph pipeline completed[/bold green]")
    console.print(final_result)
    graph_path = Path("outputs/langgraph_workflow.mmd")
    graph_path.parent.mkdir(parents=True, exist_ok=True)
    graph_path.write_text(pipeline.get_graph().draw_mermaid(), encoding="utf-8")
    console.print(f"Graph diagram saved to {graph_path}")


if __name__ == "__main__":
    app()
