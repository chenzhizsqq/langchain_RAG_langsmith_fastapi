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
    # Day 5 可以把这个类理解成：
    # “外部能力的配置入口”
    # 也就是说，后面要接哪些模型、向量库、运行模式，
    # 都先通过这里统一读进来。
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
    # Day 5 对应点：
    # 后端要接外部能力时，通常先需要配置这些能力。
    # 例如：
    # - OPENAI_API_KEY
    #   真实调用 OpenAI 时使用的密钥。
    #   如果 production 模式下这里没配，项目会直接报错，无法调用模型。
    #
    # - OPENAI_CHAT_MODEL
    #   负责“生成回答”的聊天模型名称。
    #   如果这里配错，可能会出现模型不可用、响应异常、成本不符合预期等问题。
    #
    # - OPENAI_EMBEDDING_MODEL
    #   负责“把文本转换成向量”的 embedding 模型名称。
    #   如果这里配错，最直接影响的是检索质量；严重时还可能直接调用失败。
    #
    # - CHROMA_PERSIST_DIRECTORY
    #   Chroma 向量库落盘目录。
    #   如果这里改错，可能会出现：
    #   - 数据写到错误位置
    #   - 之前的向量数据读不到
    #   - 看起来像“知识库丢了”
    #
    # 所以 Settings 这一层虽然不像业务代码那样“显眼”，
    # 但它非常关键，因为很多运行问题本质上都是配置问题。
    settings = Settings(
        base_dir=BASE_DIR,
        # APP_MODE 决定当前走测试链路还是生产链路。
        # - test：不依赖真实 OpenAI key，用本地 mock 跑通结构
        # - production：接真实模型和真实向量库
        runtime_mode=os.getenv("APP_MODE", "test").strip().lower(),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        chat_model=os.getenv("OPENAI_CHAT_MODEL", "gpt-4.1-mini"),
        embedding_model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
        # APP_HOST / APP_PORT 决定 FastAPI 服务监听在哪个地址和端口。
        # iOS / 浏览器 / Swagger 要访问的就是这里。
        app_host=os.getenv("APP_HOST", "127.0.0.1"),
        app_port=_env_int("APP_PORT", 8000),
        chroma_persist_directory=_resolve_path(
            os.getenv("CHROMA_PERSIST_DIRECTORY", "storage/chroma")
        ),
        # collection_name 可以理解成“当前知识库集合名”。
        # 如果这里改了，就像切到另一套集合，旧数据可能看不到。
        chroma_collection_name=os.getenv("CHROMA_COLLECTION_NAME", "rag_knowledge_api_docs"),
        # top_k 决定一次检索返回多少个最相关片段。
        # 太小：可能检索信息不够
        # 太大：可能把不相关内容也带进去
        top_k=_env_int("RAG_TOP_K", 4),
        # chunk_size / chunk_overlap 决定文本切块策略。
        # 它们会直接影响 embedding 质量和检索效果。
        chunk_size=_env_int("RAG_CHUNK_SIZE", 700),
        chunk_overlap=_env_int("RAG_CHUNK_OVERLAP", 120),
        # mock_embedding_dimensions 只在 test 模式下有意义，
        # 用来控制本地 mock embedding 的向量维度。
        mock_embedding_dimensions=_env_int("MOCK_EMBEDDING_DIMENSIONS", 64),
        # LangSmith 相关配置主要用于链路追踪和调试。
        # 如果不开 tracing，不影响主流程运行，但会少掉可观测性。
        langsmith_tracing=_env_flag("LANGSMITH_TRACING", False),
        langsmith_project=os.getenv("LANGSMITH_PROJECT"),
        seed_docs_directory=_resolve_path("data/seed_docs"),
        # 上传目录用于暂存用户上传的原始文件。
        upload_directory=_resolve_path("storage/uploads"),
    )
    settings.ensure_directories()
    settings.validate_runtime()
    return settings
