# academic_paper_pipeline
Academic Paper Pipeline is an agentic research-data infrastructure prototype for web-scale science-of-science research. It collects scholarly metadata from OpenAlex and arXiv, archives raw API responses, normalizes papers/authors/topics into SQLite, applies LLM and rule-based extraction to identify research questions and methods, trains lightweight ML classifiers on extracted paper data, generates run-level research reports, and exposes Prometheus/Grafana-ready monitoring metrics. The repository also includes an AWS-ready architecture for distributed crawling with SQS, S3, ECS/AWS Batch, RDS/PostgreSQL, Step Functions, and failure recovery.

Academic Paper Intelligence Pipeline — Python, LangGraph, LangChain, OpenAlex/arXiv APIs, SQLite, scikit-learn, Prometheus/Grafana
• Built an agentic research-data pipeline for collecting, archiving, normalizing, and storing scholarly-paper metadata for science-of-science analysis.
• Designed SQL schemas for papers, authors, topics, raw records, extractions, model predictions, pipeline runs, and errors to support reproducible data wrangling.
• Applied LLM/rule-based extraction and lightweight ML classifiers to identify research questions, methods, datasets, models, findings, and topic/method categories from scholarly text.
• Implemented automated markdown reports and monitoring-ready metrics for ingestion volume, API latency, parse failures, extraction success rate, classifier outputs, and pipeline runtime.
• Added AWS-ready distributed crawling architecture using SQS, S3, ECS/AWS Batch, RDS/PostgreSQL, Step Functions, rate limiting, retries, and failure recovery.


## Roadmap

### Phase 1: Local research-data pipeline

* Collect paper metadata and abstracts from OpenAlex and arXiv APIs.
* Normalize papers, authors, institutions, venues, topics, and abstracts into SQLite.
* Archive raw API responses as JSONL for reproducibility and data lineage.
* Generate research-ready CSV outputs and a markdown pipeline report.

### Phase 2: Agentic ML/LLM extraction

* Use LangGraph to orchestrate planner, collector, extractor, verifier, and report agents.
* Use LangChain for API tools, prompt templates, structured LLM extraction, and validation.
* Use LangSmith to trace agent runs, tool calls, extraction failures, latency, and evaluation results.
* Apply LLM extraction to identify research questions, methods, datasets, models, findings, limitations, and evidence spans.
* Train lightweight ML classifiers for paper topic and method-type prediction.
* Evaluate extraction quality using hand-labeled examples, evidence-span validation, and error analysis.

### Phase 3: Monitoring and observability

* Track ingestion volume, API latency, parse failures, extraction success rate, model predictions, and pipeline runtime.
* Expose Prometheus-compatible metrics and visualize system health in Grafana.
* Generate run-level reports summarizing processed papers, failed records, error categories, extraction coverage, model metrics, and next recommended actions.

### Phase 4: AWS-ready distributed crawling

* Design a distributed architecture using SQS for crawl/extraction queues, S3 for raw JSON/PDF storage, ECS Fargate or AWS Batch for collector workers, RDS/PostgreSQL for structured records, and Step Functions for orchestration.
* Add crawler-worker interfaces for open-access PDFs and scholarly web pages.
* Implement robots.txt compliance, rate limiting, transparent user-agent configuration, retries, batching, idempotent writes, and failure recovery.


# Academic Paper Intelligence Pipeline

Academic Paper Intelligence Pipeline is an agentic research-data infrastructure prototype for web-scale science-of-science research.

It collects scholarly metadata from OpenAlex and arXiv, archives raw API responses, normalizes papers/authors/topics into SQLite, applies LLM and rule-based extraction to identify research questions and methods, trains lightweight ML classifiers on extracted paper data, generates run-level research reports, and exposes Prometheus/Grafana-ready monitoring metrics.

## Planned Stack

- Python
- OpenAlex API
- arXiv API
- SQLite / PostgreSQL-ready schema
- LangGraph for agentic orchestration
- LangChain for tools and structured LLM extraction
- LangSmith for tracing and evaluation
- scikit-learn for lightweight ML classifiers
- Prometheus + Grafana for monitoring
- AWS-ready design with SQS, S3, ECS/AWS Batch, RDS, and Step Functions

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
pre-commit install
