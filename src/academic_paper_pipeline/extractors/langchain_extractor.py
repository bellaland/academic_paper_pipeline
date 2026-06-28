from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field


class PaperExtraction(BaseModel):
    research_question: str = Field(
        description="The main research question or objective of the paper."
    )
    method: str = Field(description="The main method, model, experiment, or empirical strategy.")
    dataset: str | None = Field(
        default=None,
        description="The dataset, corpus, benchmark, or data source used, if mentioned.",
    )
    key_finding: str | None = Field(
        default=None, description="The main finding or contribution, if stated in the abstract."
    )
    field: str = Field(
        description="The academic field or area, such as accounting, machine learning, economics, NLP, or science of science."
    )
    relevance_label: str = Field(
        description="One of: high, medium, low. Relevance to AI/accouting/science-of-science research."
    )
    confidence: float = Field(description="Confidence score between 0 and 1.")


def build_extractor(model_name: str = "gpt-4o-mini"):
    llm = ChatOpenAI(model=model_name, temperature=0)
    return llm.with_structured_output(PaperExtraction)


def extract_paper(title: str, abstract: str, model_name: str = "gpt-4o-mini") -> PaperExtraction:
    extractor = build_extractor(model_name)
    prompt = f"""
              You are extracting structured metadata from academic paper abstracts.
              Return concise, factual information only. Do not invent datasets, findings, or methods.
              If a field is not mentioned, use null where allowed.
              Title:
              {title}
              Abstract:
              {abstract}
            """
    return extractor.invoke(prompt)


def extract_paper_rule_based(title: str, abstract: str) -> PaperExtraction:
    text = f"{title}{abstract}".lower()
    if "accounting" in text or "financial" in text or "audit" in text:
        field = "accounting / finance"
        relevance_label = "high"
    elif "machine learning" in text or "artificial intelligence" in text or "ai" in text:
        field = "artificial intelligence"
        relevance_label = "medium"
    else:
        field = "generate research"
        relevance_label = "low"
    method = "not specified"
    if "experiment" in text:
        method = "experimental analysis"
    elif "model" in text or "neural" in text:
        method = "machine learning model"
    elif "survey" in text:
        method = "survey analysis"
    elif "dataset" in text or "data" in text:
        method = "data analysis"
    return PaperExtraction(
        research_question=f"What is the main contribution of: {title}?",
        method=method,
        dataset=None,
        key_finding=None,
        field=field,
        relevance_label=relevance_label,
        confidence=0.35,
    )
