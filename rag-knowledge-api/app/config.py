from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _resolve_path(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = BASE_DIR / path
    return path


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    return int(value) if value else default


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    base_dir: Path
    openai_api_key: str | None
    chat_model: str
    embedding_model: str
    app_host: str
    app_port: int
    chroma_persist_directory: Path
    chroma_collection_name: str
    top_k: int
    chunk_size: int
    chunk_overlap: int
    langsmith_tracing: bool
    langsmith_project: str | None
    seed_docs_directory: Path
    upload_directory: Path

    def ensure_directories(self) -> None:
        self.chroma_persist_directory.mkdir(parents=True, exist_ok=True)
        self.upload_directory.mkdir(parents=True, exist_ok=True)

    def validate_runtime(self) -> None:
        if not self.openai_api_key:
            raise RuntimeError(
                "缺少 OPENAI_API_KEY。请先把 .env.example 复制成 .env，并填入你的 OpenAI API Key。"
            )


def get_settings() -> Settings:
    settings = Settings(
        base_dir=BASE_DIR,
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        chat_model=os.getenv("OPENAI_CHAT_MODEL", "gpt-4.1-mini"),
        embedding_model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
        app_host=os.getenv("APP_HOST", "127.0.0.1"),
        app_port=_env_int("APP_PORT", 8000),
        chroma_persist_directory=_resolve_path(
            os.getenv("CHROMA_PERSIST_DIRECTORY", "storage/chroma")
        ),
        chroma_collection_name=os.getenv("CHROMA_COLLECTION_NAME", "rag_knowledge_api_docs"),
        top_k=_env_int("RAG_TOP_K", 4),
        chunk_size=_env_int("RAG_CHUNK_SIZE", 700),
        chunk_overlap=_env_int("RAG_CHUNK_OVERLAP", 120),
        langsmith_tracing=_env_flag("LANGSMITH_TRACING", False),
        langsmith_project=os.getenv("LANGSMITH_PROJECT"),
        seed_docs_directory=_resolve_path("data/seed_docs"),
        upload_directory=_resolve_path("storage/uploads"),
    )
    settings.ensure_directories()
    return settings
