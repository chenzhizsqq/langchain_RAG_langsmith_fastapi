from __future__ import annotations

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    openai_configured: bool
    langsmith_tracing: bool
    langsmith_project: str | None = None


class IngestResponse(BaseModel):
    message: str
    documents_count: int
    chunks_count: int
    collection_count: int
    sources: list[str]


class TextIngestRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=120)
    text: str = Field(..., min_length=1)
    source: str | None = Field(default=None, max_length=200)


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1)
    top_k: int | None = Field(default=None, ge=1, le=10)


class SourceChunk(BaseModel):
    source: str
    chunk_index: int | None = None
    page: int | None = None
    distance: float | None = None
    preview: str


class AskResponse(BaseModel):
    question: str
    answer: str
    sources: list[SourceChunk]


class StatsResponse(BaseModel):
    collection_name: str
    persist_directory: str
    chunk_count: int
    default_top_k: int
