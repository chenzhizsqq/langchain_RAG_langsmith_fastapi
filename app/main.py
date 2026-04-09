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

Day 3 再补一个最重要的习惯：
- 这个文件只负责“接”和“回”
- 不负责承载复杂业务流程
- 所以这里应该尽量保持短、小、清楚

也就是说：
- 接口路径写在这里
- Request / Response schema 挂在这里
- 真正的 RAG 业务逻辑往 service 下沉

Day 4 再补一个重点：
- 这个文件负责“接住不同输入形式”
- 例如：
  - POST JSON
  - 文件上传
- 但它不负责深入解析内容，而是把输入转交给 schema / loader / service

Day 5 再补一个重点：
- FastAPI 本身不是 AI 能力本身
- 它更像统一入口和编排入口
- 真正的价值在于：这个入口后面接了哪些外部能力
- 例如：
  - RAGService
  - OpenAI 模型
  - 向量库
  - 文件处理
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
    # 这里导入的不是业务逻辑，而是“接口的数据结构定义”。
    # main.py 会把这些 schema 挂到各个接口上，用来说明：
    # - 请求体应该长什么样
    # - 响应体应该长什么样
    #
    # 用 Spring Boot 思维看，很像在 Controller 里使用：
    # - Request DTO
    # - Response DTO
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
        # 这也体现分层：main.py 负责把业务异常转换成 HTTP 语义。
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/")
def read_root() -> dict[str, object]:
    # 这是最基础的 GET 接口示例。
    # GET 通常用来读取状态或说明信息，不负责提交业务数据。
    # 这个接口没有单独使用 schemas.py 里的 Response Model，
    # 而是直接返回一个普通 dict，FastAPI 最后仍会把它转成 JSON。
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
    # 所以这里对应的 schema 是：
    # - Request：无
    # - Response：HealthResponse
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
    # 所以这里对应的 schema 是：
    # - Request：无
    # - Response：StatsResponse
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
    # 这个接口不需要客户端传 JSON body，
    # 但它仍然会返回一个固定结构的 Response Model。
    # 所以这里对应的 schema 是：
    # - Request：无
    # - Response：IngestResponse
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
    # Day 4 对应点：
    # - 这里演示的是“POST JSON”
    # - 外部输入先被解析成 TextIngestRequest
    # 所以这里对应的 schema 是：
    # - Request：TextIngestRequest
    # - Response：IngestResponse
    # Day 3 要刻意注意：
    # main.py 不直接处理“切块 / 向量化 / 入库”这些业务，
    # 这里只负责把 request 里的字段交给 service。
    service = get_service()
    documents = build_text_document(request.title, request.text, request.source)
    result = service.ingest_documents(documents)
    return IngestResponse(**result)


@app.post("/api/ingest/file", response_model=IngestResponse)
async def ingest_file(file: UploadFile = File(...)) -> IngestResponse:
    # 这个 POST 不是接 JSON，而是接文件上传。
    # 对 iOS 来说，这类接口通常对应 multipart/form-data 请求。
    # Day 4 对应点：
    # - 这里演示的是“文件上传”
    # - UploadFile = File(...) 的感觉很像 Spring Boot 的 MultipartFile
    # 这里写成 async def，不是为了“开线程”，而是因为这是文件 IO 场景，
    # 并且下面会用到 await file.close() 这种异步写法。
    # 所以这里对应的 schema 是：
    # - Request：不是 schemas.py 的 BaseModel，而是 UploadFile
    # - Response：IngestResponse
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
    # 所以这里对应的 schema 是：
    # - Request：AskRequest
    # - Response：AskResponse
    # Day 3 的重点就是这里：
    # main.py 不去自己写检索、拼 prompt、调模型，
    # 而是只把参数转交给 rag_service.py。
    # Day 5 的重点也在这里：
    # FastAPI 只作为入口，真正调用外部 AI / 检索能力的是后面的 service。
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
