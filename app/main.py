from __future__ import annotations

"""
Day 1 先看这个文件时，可以抓住四个最基础的 FastAPI 概念：

1. GET
   用来“读取信息”。
   例如：
   - @app.get("/")
   - @app.get("/health")
   - @app.get("/api/stats")

2. POST
   用来“提交数据”或“触发动作”。
   例如：
   - @app.post("/api/ingest/sample")
   - @app.post("/api/ingest/text")
   - @app.post("/api/ask")

3. path
   这里先把 path 理解成“接口路径”即可，例如：
   - "/health"
   - "/api/ask"
   - "/api/stats"
   它就是 iOS 以后要请求的 URL 路径部分。

4. JSON response
   大多数接口最后都会返回 JSON。
   在这个文件里，return {...} 或 return Pydantic 模型，最终都会变成 JSON。

如果你用 Spring Boot 来理解：
- 这个文件很像 Controller
- 每个 @app.get / @app.post 都像一个接口方法
- response_model 很像“这个接口规定要返回什么 JSON 结构”
"""

from functools import lru_cache

import uvicorn
from fastapi import FastAPI, File, HTTPException, UploadFile

from app.config import Settings, get_settings
from app.loaders import (
    build_text_document,
    load_documents_from_saved_file,
    load_seed_documents,
    save_upload_file,
)
from app.rag_service import RAGService
from app.schemas import (
    AskRequest,
    AskResponse,
    HealthResponse,
    IngestResponse,
    StatsResponse,
    TextIngestRequest,
)


app = FastAPI(
    title="RAG Knowledge API",
    version="0.1.0",
    description="A practical RAG knowledge API built with LangChain, LangSmith, FastAPI, and Chroma.",
)


@lru_cache
def get_cached_settings() -> Settings:
    # 配置和服务都做缓存，保证整个进程里复用同一份运行状态。
    return get_settings()


@lru_cache
def get_cached_service() -> RAGService:
    return RAGService(get_cached_settings())


def get_service() -> RAGService:
    try:
        return get_cached_service()
    except RuntimeError as exc:
        # 配置错误直接转成 HTTP 500，前端或 Swagger 可以马上看到原因。
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/")
def read_root() -> dict[str, object]:
    # 这是最基础的 GET 接口示例。
    # GET 通常用来读取状态或说明信息，不负责提交业务数据。
    settings = get_cached_settings()
    return {
        "project": "RAG Knowledge API",
        "message": "先看 README，再去 /docs 直接调接口。",
        "runtime_mode": settings.runtime_mode,
        "openapi_docs": "/docs",
        "health": "/health",
        "openai_configured": bool(settings.openai_api_key),
        "langsmith_tracing": settings.langsmith_tracing,
    }


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    # 这里的 "/health" 就是 path，也就是接口路径。
    # response_model=HealthResponse 表示：这个接口返回的 JSON 要符合 HealthResponse 的结构。
    settings = get_cached_settings()
    return HealthResponse(
        status="ok",
        runtime_mode=settings.runtime_mode,
        openai_configured=bool(settings.openai_api_key),
        langsmith_tracing=settings.langsmith_tracing,
        langsmith_project=settings.langsmith_project,
    )


@app.get("/api/stats", response_model=StatsResponse)
def stats() -> StatsResponse:
    # 这也是 GET，因为它只是读取当前知识库状态，不提交新数据。
    settings = get_cached_settings()
    service = get_service()
    return StatsResponse(
        collection_name=settings.chroma_collection_name,
        persist_directory=(
            # 测试模式没有落磁盘，所以这里明确标注成 in-memory。
            "in-memory (test mode)"
            if settings.is_test_mode
            else str(settings.chroma_persist_directory)
        ),
        chunk_count=service.collection_count(),
        default_top_k=settings.top_k,
    )


@app.post("/api/ingest/sample", response_model=IngestResponse)
def ingest_sample_documents() -> IngestResponse:
    # 这是 POST 接口示例。
    # POST 常用来触发“创建、导入、执行”这类动作。
    settings = get_cached_settings()
    service = get_service()
    # 这个接口专门用来验证最小 demo 是否能跑通，不依赖用户先准备资料。
    documents = load_seed_documents(settings.seed_docs_directory)
    result = service.ingest_documents(documents)
    return IngestResponse(**result)


@app.post("/api/ingest/text", response_model=IngestResponse)
def ingest_text(request: TextIngestRequest) -> IngestResponse:
    # request: TextIngestRequest 表示这个 POST 接口会接收一个 JSON body。
    # 也就是说，客户端要传入 title / text / source 这样的 JSON 字段。
    service = get_service()
    documents = build_text_document(request.title, request.text, request.source)
    result = service.ingest_documents(documents)
    return IngestResponse(**result)


@app.post("/api/ingest/file", response_model=IngestResponse)
async def ingest_file(file: UploadFile = File(...)) -> IngestResponse:
    # 这个 POST 不是接 JSON，而是接文件上传。
    # 对 iOS 来说，这类接口通常对应 multipart/form-data 请求。
    settings = get_cached_settings()
    service = get_service()

    try:
        saved_path = save_upload_file(file, settings.upload_directory)
        documents = load_documents_from_saved_file(saved_path)
        result = service.ingest_documents(documents)
        return IngestResponse(**result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        await file.close()


@app.post("/api/ask", response_model=AskResponse)
def ask_question(request: AskRequest) -> AskResponse:
    # 这是最典型的“客户端发 JSON，请求后端处理，再返回 JSON”的接口。
    # iOS 以后最常对接的，通常就是这种形式。
    service = get_service()
    # 问答接口本身不做业务逻辑，统一下沉到 RAGService，保持 API 层足够薄。
    result = service.answer_question(request.question, request.top_k)
    return AskResponse(**result)


if __name__ == "__main__":
    settings = get_cached_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
    )
