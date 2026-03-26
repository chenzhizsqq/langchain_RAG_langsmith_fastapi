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
    # runtime_mode 决定当前是“真实模型联调”还是“本地测试联调”。
    base_dir: Path
    runtime_mode: str
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
    mock_embedding_dimensions: int
    langsmith_tracing: bool
    langsmith_project: str | None
    seed_docs_directory: Path
    upload_directory: Path

    def ensure_directories(self) -> None:
        # 生产模式会用到本地 Chroma 持久化目录，上传接口也需要保存原始文件。
        self.chroma_persist_directory.mkdir(parents=True, exist_ok=True)
        self.upload_directory.mkdir(parents=True, exist_ok=True)

    @property
    def is_test_mode(self) -> bool:
        return self.runtime_mode == "test"

    def validate_runtime(self) -> None:
        if self.runtime_mode not in {"production", "test"}:
            raise RuntimeError("APP_MODE 只支持 production 或 test。")

        # test 模式不要求真实 OpenAI key，便于先验证 API 和 RAG 架构链路。
        if not self.is_test_mode and not self.openai_api_key:
            raise RuntimeError(
                "缺少 OPENAI_API_KEY。请先把 .env.example 复制成 .env，并填入你的 OpenAI API Key。"
            )


def get_settings() -> Settings:
    # 所有运行参数统一从这里收口，后面接口层和 RAG 层都只依赖 Settings。
    settings = Settings(
        base_dir=BASE_DIR,
        runtime_mode=os.getenv("APP_MODE", "test").strip().lower(),
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
        mock_embedding_dimensions=_env_int("MOCK_EMBEDDING_DIMENSIONS", 64),
        langsmith_tracing=_env_flag("LANGSMITH_TRACING", False),
        langsmith_project=os.getenv("LANGSMITH_PROJECT"),
        seed_docs_directory=_resolve_path("data/seed_docs"),
        upload_directory=_resolve_path("storage/uploads"),
    )
    settings.ensure_directories()
    settings.validate_runtime()
    return settings
