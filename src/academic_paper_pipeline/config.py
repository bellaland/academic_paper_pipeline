from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    openalex_api_key: str | None = Field(default=None, alias="OPENALEX_API_KEY")
    openalex_email: str | None = Field(default=None, alias="OPENALEX_EMAIL")

    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    langchain_api_key: str | None = Field(default=None, alias="LANGCHAIN_API_KEY")
    langchain_tracing_v2: bool = Field(default=False, alias="LANGCHAIN_TRACING_V2")
    langchain_project: str = Field(default="academic-paper-pipeline", alias="LANGCHAIN_PROJECT")

    database_url: str = Field(default="sqlite:///academic_papers.db", alias="DATABASE_URL")

    default_query: str = Field(default="artificial intelligence accounting", alias="DEFAULT_QUERY")
    default_max_results: int = Field(default=100, alias="DEFAULT_MAX_RESULTS")
    use_llm: bool = Field(default=False, alias="USE_LLM")

    metrics_port: int = Field(default=8000, alias="METRICS_PORT")

    project_root: Path = Path(__file__).resolve().parents[2]
    data_dir: Path = project_root / "data"
    raw_dir: Path = data_dir / "raw"
    processed_dir: Path = data_dir / "processed"
    labels_dir: Path = data_dir / "labels"
    outputs_dir: Path = project_root / "outputs"
    logs_dir: Path = project_root / "logs"

    class Config:
        populate_by_name = True
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.raw_dir.mkdir(parents=True, exist_ok=True)
    settings.processed_dir.mkdir(parents=True, exist_ok=True)
    settings.labels_dir.mkdir(parents=True, exist_ok=True)
    settings.outputs_dir.mkdir(parents=True, exist_ok=True)
    settings.logs_dir.mkdir(parents=True, exist_ok=True)
    return settings
