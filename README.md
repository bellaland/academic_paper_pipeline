# Academic Paper Pipeline

Academic Paper Pipeline is an agentic research-data infrastructure prototype for web-scale science-of-science research.

It collects scholarly metadata from OpenAlex and arXiv, archives raw API responses, normalizes papers, authors, topics, raw records, extraction outputs, pipeline runs, and errors into SQLite, applies LLM and rule-based extraction to identify research questions and methods, orchestrates the workflow with LangGraph, decomposes the system into lightweight research agents, generates reports, and exposes Prometheus/Grafana-ready monitoring metrics.

The project demonstrates practical research engineering skills for large-scale academic-paper analysis, data wrangling, semantic extraction, workflow orchestration, agentic system design, and production-style monitoring.

## Project Overview

This project is designed as a local but extensible prototype for research-data infrastructure. It focuses on the full lifecycle of academic-paper intelligence:

1. Collect paper metadata from public scholarly APIs.
2. Preserve raw source responses for reproducibility.
3. Normalize metadata into a structured relational database.
4. Extract semantic research fields from paper abstracts.
5. Run the workflow through scripts, LangGraph, or agents.
6. Generate reports and CSV exports.
7. Monitor pipeline health using Prometheus and Grafana.
8. Trace LangChain and LangGraph execution with LangSmith.

The project can be run locally with SQLite, but the architecture maps naturally to distributed cloud infrastructure such as SQS, S3, ECS/AWS Batch, RDS/PostgreSQL, Step Functions, Prometheus, Grafana, and CloudWatch.

## Core Features

* Collects academic paper metadata from OpenAlex and arXiv.
* Archives raw API responses as JSONL and XML.
* Normalizes papers, authors, topics, raw records, extraction outputs, runs, events, and errors into SQLite.
* Extracts structured research metadata using LangChain/OpenAI or a rule-based fallback.
* Supports OpenAI-free operation through `--no-use-llm`.
* Generates Markdown reports and CSV exports.
* Orchestrates the full workflow with LangGraph.
* Provides lightweight research-data agents:

  * `CollectorAgent`
  * `ExtractionAgent`
  * `QualityCheckAgent`
  * `ReportAgent`
* Exposes Prometheus-compatible metrics through a FastAPI `/metrics` endpoint.
* Includes a Grafana dashboard JSON for pipeline monitoring.
* Supports LangSmith tracing for LangChain and LangGraph workflows.
* Includes an AWS-ready architecture direction for distributed crawling and failure recovery.

## Architecture

```text
OpenAlex / arXiv
      ↓
Raw JSONL / XML archive
      ↓
SQLite normalized storage
      ↓
LangChain / rule-based extraction
      ↓
LangGraph workflow orchestration
      ↓
CollectorAgent / ExtractionAgent / QualityCheckAgent / ReportAgent
      ↓
Markdown reports + CSV exports
      ↓
Prometheus metrics + Grafana dashboard
```

## Repository Structure

```text
academic_paper_pipeline/
├── data/
│   └── raw/                         # Raw OpenAlex/arXiv API responses
├── monitoring/
│   ├── prometheus.yml               # Prometheus scrape configuration
│   └── grafana/
│       └── academic_paper_pipeline_dashboard.json
├── outputs/
│   ├── papers.csv                   # Exported normalized paper data
│   └── pipeline_report.md           # Generated Markdown report
├── src/
│   └── academic_paper_pipeline/
│       ├── agents/
│       │   └── research_agents.py
│       ├── collectors/
│       │   ├── openalex_client.py
│       │   └── arxiv_client.py
│       ├── extractors/
│       │   └── langchain_extractor.py
│       ├── ml/
│       ├── monitoring/
│       │   └── metrics_server.py
│       ├── pipelines/
│       │   ├── run_collect_openalex.py
│       │   ├── run_collect_arxiv.py
│       │   ├── run_extract_papers.py
│       │   ├── run_langgraph_pipeline.py
│       │   └── run_agent_pipeline.py
│       ├── reports/
│       │   └── generate_report.py
│       └── storage/
│           ├── schema.sql
│           └── sqlite_store.py
├── requirements.txt
├── pyproject.toml
└── README.md
```

## Data Model

The SQLite schema supports the main entities needed for a reproducible research-data pipeline:

* `papers`
* `authors`
* `paper_authors`
* `topics`
* `paper_topics`
* `raw_records`
* `paper_extractions`
* `pipeline_runs`
* `pipeline_events`
* `pipeline_errors`

The database stores both normalized fields and links back to raw records, allowing the project to preserve raw evidence while supporting structured analysis.

## Installation

Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Install the package in editable mode:

```bash
pip install -e .
```

Install pre-commit hooks:

```bash
pip install pre-commit
pre-commit install
```

## Environment Variables

Create a local `.env` file if using OpenAI or LangSmith:

```bash
OPENAI_API_KEY=your_openai_api_key

LANGSMITH_TRACING=true
LANGSMITH_API_KEY=your_langsmith_key
LANGSMITH_PROJECT=academic-paper-pipeline
```

The project can still run without OpenAI API quota by using the rule-based extraction fallback with `--no-use-llm`.

## Running the Pipeline

### 1. Collect OpenAlex Papers

```bash
python -m academic_paper_pipeline.pipelines.run_collect_openalex \
  --query "artificial intelligence accounting" \
  --max-results 50
```

This command collects paper metadata from OpenAlex, stores raw JSONL responses, normalizes paper records into SQLite, exports CSV output, and updates the pipeline report.

### 2. Collect arXiv Papers

```bash
python -m academic_paper_pipeline.pipelines.run_collect_arxiv \
  --query "artificial intelligence accounting" \
  --max-results 50
```

This command collects arXiv records, stores raw XML responses, normalizes arXiv metadata into SQLite, exports CSV output, and updates the pipeline report.

### 3. Run Structured Extraction

Run extraction with the rule-based fallback:

```bash
python -m academic_paper_pipeline.pipelines.run_extract_papers \
  --limit 5 \
  --no-use-llm
```

Run extraction with LangChain/OpenAI:

```bash
python -m academic_paper_pipeline.pipelines.run_extract_papers \
  --limit 5 \
  --use-llm
```

The extraction layer identifies fields such as:

* Research question
* Method
* Dataset
* Key finding
* Academic field
* Relevance label
* Confidence score

## LangGraph Workflow

The LangGraph pipeline expresses the full workflow as a stateful graph:

```text
START
  ↓
collect_openalex
  ↓
collect_arxiv
  ↓
extract_papers
  ↓
generate_report
  ↓
END
```

Run the LangGraph workflow:

```bash
python -m academic_paper_pipeline.pipelines.run_langgraph_pipeline \
  --query "artificial intelligence accounting" \
  --max-results 5 \
  --extract-limit 3 \
  --no-use-llm
```

Example output:

```text
LangGraph pipeline completed
{
    "openalex_result": {"collected": 5, "failed": 0},
    "arxiv_result": {"collected": 5, "failed": 0},
    "extracted": 3,
    "failed_extractions": 0,
    "report_path": "outputs/pipeline_report.md"
}
```

This graph structure supports future conditional routing, retries, quality gates, source selection, and dynamic workflow control.

## Agentic Workflow

The project also includes a lightweight agentic workflow. Instead of representing the pipeline only as graph nodes, it decomposes the research-data process into specialized agents:

```text
CollectorAgent
  → collects scholarly metadata from OpenAlex and arXiv

ExtractionAgent
  → extracts structured research fields from stored papers

QualityCheckAgent
  → checks total papers, missing abstracts, extraction coverage, and failed runs

ReportAgent
  → generates the final Markdown pipeline report
```

Run the agentic workflow:

```bash
python -m academic_paper_pipeline.pipelines.run_agent_pipeline \
  --query "artificial intelligence accounting" \
  --max-results 5 \
  --extract-limit 3 \
  --no-use-llm
```

Example output:

```text
Running CollectorAgent
Running ExtractionAgent
Running QualityCheckAgent
Running ReportAgent
Agent pipeline completed
```

The agentic workflow demonstrates role-based decomposition without relying on a chatbot interface.

## Reports and Outputs

The pipeline generates:

```text
outputs/papers.csv
outputs/pipeline_report.md
```

The Markdown report summarizes:

* Total papers
* Missing abstracts
* Earliest and latest publication years
* Citation totals
* Source distribution
* Recent pipeline runs
* Top publication years
* Top venues
* Top topics
* Extraction summary
* Extraction fields
* Relevance labels
* Extraction methods
* Error summary

## Monitoring and Observability

The project includes both LLM workflow tracing and production-style pipeline monitoring.

### LangSmith Tracing

LangSmith can trace LangChain and LangGraph execution, including LLM extraction calls, graph runs, latency, and errors.

Example configuration:

```bash
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=your_langsmith_key
LANGSMITH_PROJECT=academic-paper-pipeline
```

When enabled, traces are visible in the LangSmith project dashboard. This is useful for debugging LLM extraction calls, graph execution, latency, and failures.

### Prometheus Metrics

The pipeline exposes Prometheus-compatible metrics through a FastAPI metrics server.

Start the metrics server:

```bash
python -m academic_paper_pipeline.monitoring.metrics_server \
  --db-path academic_papers.db \
  --port 8000
```

Metrics are available at:

```text
http://127.0.0.1:8000/metrics
```

Exposed metrics include:

```text
academic_papers_total
academic_missing_abstracts_total
academic_extractions_total
academic_extraction_coverage
academic_failed_runs_total
```

Example metrics:

```text
academic_papers_total 105
academic_extractions_total 26
academic_extraction_coverage 0.2476
academic_missing_abstracts_total 16
academic_failed_runs_total 1
```

### Prometheus Setup

Install Prometheus:

```bash
brew install prometheus
```

Run Prometheus using the included config:

```bash
prometheus --config.file=monitoring/prometheus.yml
```

Open Prometheus:

```text
http://localhost:9090
```

Example PromQL queries:

```text
academic_papers_total
academic_extractions_total
academic_extraction_coverage
academic_missing_abstracts_total
academic_failed_runs_total
```

Check scrape target health:

```text
http://localhost:9090/targets
```

The target should show:

```text
academic_paper_pipeline    UP
```

### Grafana Dashboard

Install Grafana:

```bash
brew install grafana
```

Start Grafana:

```bash
brew services start grafana
```

Open Grafana:

```text
http://localhost:3000
```

Add Prometheus as a data source with URL:

```text
http://localhost:9090
```

The included dashboard JSON is located at:

```text
monitoring/grafana/academic_paper_pipeline_dashboard.json
```

The dashboard visualizes:

* Total papers
* Structured extractions
* Extraction coverage
* Missing abstracts
* Failed runs

For extraction coverage, the Grafana panel uses:

```text
academic_extraction_coverage * 100
```

and displays the value as a percentage.

## Execution Modes

The project supports multiple execution modes:

```text
1. Individual OpenAlex collection
2. Individual arXiv collection
3. Standalone extraction
4. LangGraph graph workflow
5. Agentic workflow
6. Prometheus metrics server
7. Grafana dashboard
```

This makes the project useful both as a local research prototype and as a demonstration of production-style research infrastructure.

## AWS-Ready Extension

The repository is designed to map naturally to a distributed AWS architecture:

```text
SQS
  → source collection jobs

ECS / AWS Batch
  → distributed collectors and extractors

S3
  → raw JSONL/XML evidence archive

RDS / PostgreSQL
  → normalized production database

Step Functions
  → workflow orchestration

CloudWatch / Prometheus / Grafana
  → monitoring and alerting
```

This extension would allow the local SQLite prototype to scale into a distributed web-crawling and research-data processing system.

## Development Commands

Compile source files:

```bash
python -m compileall src
```

Run pre-commit checks:

```bash
pre-commit run --all-files
```

Check Git status:

```bash
git status
```

Commit changes:

```bash
git add .
git commit -m "Update project"
git push origin main
```

## Notes

* Use small values such as `--max-results 5` or `--max-results 10` during development.
* Use `--no-use-llm` when OpenAI API quota is unavailable.
* Prometheus runtime files should not be committed.
* Grafana dashboard JSON is committed for reproducible dashboard import.
* Local SQLite data can be regenerated by rerunning the collectors and extraction pipeline.
* The local SQLite prototype is intentionally lightweight but can be extended to PostgreSQL for production use.

## Summary

This project demonstrates a complete research-data engineering workflow for academic paper intelligence: collection, raw evidence preservation, normalized storage, semantic extraction, graph orchestration, agentic decomposition, reporting, and production-style monitoring.

It is especially relevant to research roles involving large-scale academic-paper processing, science-of-science infrastructure, LLM-assisted data extraction, and reproducible data systems.
