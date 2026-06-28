import typer
from rich.console import Console

from academic_paper_pipeline.extractors.langchain_extractor import (
    extract_paper,
    extract_paper_rule_based,
)
from academic_paper_pipeline.reports.generate_report import generate_pipeline_report
from academic_paper_pipeline.storage.sqlite_store import SQLiteStore, new_id, utc_now

app = typer.Typer(help="Extract structured fields from stored papers using LangChain.")
console = Console()


@app.command()
def main(
    limit: int = typer.Option(5, help="Maximum number of papers to extract."),
    db_path: str = typer.Option("academic_papers.db", help="SQLite database path."),
    model_name: str = typer.Option("gpt-4o-mini", help="LLM model name."),
    use_llm: bool = typer.Option(False, help="Use LangChain/OpenAI extraction."),
) -> None:
    store = SQLiteStore(db_path=db_path)
    store.initialize()
    papers = store.get_papers_for_extraction(limit=limit)
    if not papers:
        console.print("[yellow]No papers available for extraction. [/yellow]")
        return
    console.print(
        f"[bold green]Extracting structured fields from {len(papers)} papers[/bold green]"
    )
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
            store.upsert_paper_extraction(extraction)
            extracted += 1
            console.print(f"[green]Extracted[/green]: {paper['title'][:80]}")
        except Exception as exc:
            failed += 1
            console.print(f"[red]Failed[/red]: {paper['title'][:80]} | {type(exc).__name__}: {exc}")
    report_path = generate_pipeline_report(store=store)
    console.print("[bold green]Extraction completed[/bold green]")
    console.print(
        {
            "extracted": extracted,
            "failed": failed,
            "report_path": str(report_path),
        }
    )


if __name__ == "__main__":
    app()
