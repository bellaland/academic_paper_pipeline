import typer
from rich.console import Console

from academic_paper_pipeline.collectors.arxiv_client import collect_arxiv
from academic_paper_pipeline.reports.generate_report import generate_pipeline_report
from academic_paper_pipeline.storage.sqlite_store import SQLiteStore

app = typer.Typer(help="Collect papers from arXiv and generate pipeline outputs.")
console = Console()


@app.command()
def main(
    query: str = typer.Option("artificial intelligence accounting", help="Search query"),
    max_results: int = typer.Option(100, help="Maximum number of arXiv works to collect"),
    db_path: str = typer.Option("academic_papers.db", help="SQLite database path."),
) -> None:
    store = SQLiteStore(db_path=db_path)
    store.initialize()
    console.print(f"[bold green]Collecting arXiv papers [/bold green]: {query}")
    result = collect_arxiv(query=query, max_results=max_results, store=store)
    report_path = generate_pipeline_report(store=store)
    console.print("[bold green]Collection completed[/bold green]")
    console.print(result)
    console.print(f"Report: {report_path}")


if __name__ == "__main__":
    app()
