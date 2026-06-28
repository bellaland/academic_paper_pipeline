from pathlib import Path

import pandas as pd

from academic_paper_pipeline.config import get_settings
from academic_paper_pipeline.storage.sqlite_store import SQLiteStore, utc_now


def _table_to_markdown(df: pd.DataFrame) -> str:
    if df.empty:
        return "_No records._"
    return df.to_markdown(index=False)


def generate_pipeline_report(store: SQLiteStore | None = None) -> Path:
    settings = get_settings()
    store = store or SQLiteStore()
    report_path = settings.outputs_dir / "pipeline_report.md"
    with store.connect() as conn:
        run_df = pd.read_sql_query(
            """
            SELECT run_id, source, query, max_results, started_at, finished_at,
                status, records_collected, records_failed
            FROM pipeline_runs
            ORDER BY started_at DESC
            LIMIT 5
            """,
            conn,
        )
        summary_df = pd.read_sql_query(
            """
            SELECT
                COUNT(*) AS total_papers,
                COUNT(CASE WHEN abstract IS NULL OR abstract = '' THEN 1 END) AS missing_abstracts,
                MIN(publication_year) AS min_year,
                MAX(publication_year) AS max_year,
                SUM(cited_by_count) AS total_citations
            FROM papers
            """,
            conn,
        )
        year_df = pd.read_sql_query(
            """
            SELECT publication_year, COUNT(*) AS paper_count
            FROM papers
            WHERE publication_year IS NOT NULL
            GROUP BY publication_year
            ORDER BY publication_year DESC
            LIMIT 10
            """,
            conn,
        )
        venue_df = pd.read_sql_query(
            """
            SELECT COALESCE(venue, 'UNKNOWN') AS venue, COUNT(*) AS paper_count
            FROM papers
            GROUP BY COALESCE(venue, 'Unknown')
            ORDER BY paper_count DESC
            LIMIT 10
            """,
            conn,
        )
        topic_df = pd.read_sql_query(
            """
            SELECT t.display_name AS topic, COUNT(*) AS paper_count, ROUND(AVG(pt.score), 3) AS avg_score
            FROM paper_topics pt
            JOIN topics t ON pt.topic_id = t.topic_id
            GROUP BY t.display_name
            ORDER BY paper_count DESC, avg_score DESC
            LIMIT 15
            """,
            conn,
        )
        error_df = pd.read_sql_query(
            """
            SELECT error_type, COUNT(*) AS count
            FROM errors
            GROUP BY error_type
            ORDER BY count DESC
            LIMIT 10
            """,
            conn,
        )
        source_df = pd.read_sql_query(
            """
            SELECT source_api, COUNT(*) AS paper_count
            FROM papers
            GROUP BY source_api
            ORDER BY paper_count DESC
            LIMIT 10
            """,
            conn,
        )
        extraction_summary_df = pd.read_sql_query(
            """
            SELECT
                COUNT(*) AS total_extractions,
                COUNT(DISTINCT paper_id) AS papers_extracted,
                COUNT(CASE WHEN model_name LIKE 'rule_based%' THEN 1 END) AS rule_based_extractions,
                COUNT(CASE WHEN model_name NOT LIKE 'rule_based%' THEN 1 END) AS llm_extractions,
                ROUND(AVG(confidence), 3) AS avg_confidence
            FROM paper_extractions
            """,
            conn,
        )
        extraction_field_df = pd.read_sql_query(
            """
            SELECT field, COUNT(*) AS extraction_count
            FROM paper_extractions
            GROUP BY field
            ORDER BY extraction_count DESC
            """,
            conn,
        )
        relevance_df = pd.read_sql_query(
            """
            SELECT relevance_label, COUNT(*) AS extraction_count
            FROM paper_extractions
            GROUP BY relevance_label
            ORDER BY extraction_count DESC
            """,
            conn,
        )
        method_df = pd.read_sql_query(
            """
            SELECT
                method,
                COUNT(*) AS extraction_count
            FROM paper_extractions
            GROUP BY method
            ORDER BY extraction_count DESC
            LIMIT 10
            """,
            conn,
        )
    summary = summary_df.iloc[0].to_dict() if not summary_df.empty else {}
    content = f"""# Academic Paper Pipeline Report

Generated at: `{utc_now()}`

## Summary
| Metric | Value |
|---|---:|
| Total papers | {summary.get("total_papers", 0)} |
| Missing abstracts | {summary.get("missing_abstracts", 0)} |
| Earliest year | {summary.get("min_year", "")} |
| Latest year | {summary.get("max_year", "")} |
| Total citations | {summary.get("total_citations", 0)} |

# Recent pipeline runs
{_table_to_markdown(run_df)}

# Year distribution
{_table_to_markdown(year_df)}

# Top venues
{_table_to_markdown(venue_df)}

# Top topics
{_table_to_markdown(topic_df)}

# Source distribution
{_table_to_markdown(source_df)}

# Extraction summary
{_table_to_markdown(extraction_summary_df)}

# Extraction fields
{_table_to_markdown(extraction_field_df)}

# Relevance labels
{_table_to_markdown(relevance_df)}

# Extraction methods
{_table_to_markdown(method_df)}

# Error summary
{_table_to_markdown(error_df)}

"""
    report_path.write_text(content, encoding="utf-8")
    return report_path
