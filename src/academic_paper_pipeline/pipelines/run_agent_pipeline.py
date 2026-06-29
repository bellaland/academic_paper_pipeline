import typer
from rich.console import Console

from academic_paper_pipeline.agents.research_agents import (
    CollectorAgent,
    ExtractionAgent,
    QualityCheckAgent,
    ReportAgent,
)
from academic_paper_pipeline.storage.sqlite_store import SQLiteStore

app = typer.Typer(help="Run the academic paper pipeline with research agents.")
console = Console()


@app.command()
def main(
    query: str = typer.Option(
        "artificial intelligence accounting",
        help="Search query",
    ),
    max_results: int = typer.Option(
        10,
        help="Number of papers to collect from each source.",
    ),
    extract_limit: int = typer.Option(
        5,
        help="Number of papers to extract structured fields from.",
    ),
    db_path: str = typer.Option(
        "academic_papers.db",
        help="SQLite database path.",
    ),
    model_name: str = typer.Option(
        "gpt-4o-mini",
        help="LLM model name.",
    ),
    use_llm: bool = typer.Option(
        False,
        help="Use LangChain/OpenAI extracttion.",
    ),
) -> None:
    store = SQLiteStore(db_path=db_path)
    store.initialize()
    collector = CollectorAgent(store=store)
    extractor = ExtractionAgent(store=store)
    quality_checker = QualityCheckAgent(store=store)
    reporter = ReportAgent(store=store)
    console.print("[bold green]Running CollectorAgent[/bold green]")
    collection_result = collector.run(
        query=query,
        max_results=max_results,
    )
    console.print("[bold green]Running ExtractorAgent[/bold green]")
    extraction_result = extractor.run(
        limit=extract_limit,
        use_llm=use_llm,
        model_name=model_name,
    )
    console.print("[bold green]Running QualityCheckAgent[/bold green]")
    quality_result = quality_checker.run()
    console.print("[bold green]Running ReportAgent[/bold green]")
    report_result = reporter.run()
    console.print("[bold green]Agent pipeline completed[/bold green]")
    console.print(
        {
            "collection": collection_result,
            "extraction": extraction_result,
            "quality": quality_result,
            "report": report_result,
        }
    )


if __name__ == "__main__":
    app()
