from __future__ import annotations

"""
这个文件可以先把它理解成：
"接口请求和接口响应的数据结构定义文件"。

如果你是 iOS 开发者，可以把这些 BaseModel 理解成很像 Swift 里的：
- Request DTO
- Response DTO
- Codable struct

Day 1 看这个文件时，重点理解三件事：

1. Request Model
   例如：
   - TextIngestRequest
   - AskRequest
   它们描述“客户端传进来的 JSON 应该长什么样”。

2. Response Model
   例如：
   - HealthResponse
   - IngestResponse
   - AskResponse
   它们描述“服务端回出去的 JSON 应该长什么样”。

3. Field 校验
   例如 min_length、max_length、ge、le。
   这些相当于接口参数校验规则，能帮你在进入业务逻辑之前先拦住明显错误的输入。
"""

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    # 这是一个 Response Model：描述 /health 返回的 JSON 结构。
    status: str
    runtime_mode: str
    openai_configured: bool
    langsmith_tracing: bool
    langsmith_project: str | None = None


class IngestResponse(BaseModel):
    # 导入文档相关接口统一返回这个结构。
    message: str
    documents_count: int
    chunks_count: int
    collection_count: int
    sources: list[str]


class TextIngestRequest(BaseModel):
    # 这是一个 Request Model：客户端传 JSON 进来时，要符合这个结构。
    # Field(...) 里的规则就是参数校验规则。
    title: str = Field(..., min_length=1, max_length=120)
    text: str = Field(..., min_length=1)
    source: str | None = Field(default=None, max_length=200)


class AskRequest(BaseModel):
    # 这是 /api/ask 的请求体。
    # top_k 是可选的；如果传了，就必须在 1 到 10 之间。
    question: str = Field(..., min_length=1)
    top_k: int | None = Field(default=None, ge=1, le=10)


class SourceChunk(BaseModel):
    # 这是 AskResponse 里的一部分，表示“命中了哪一段资料”。
    source: str
    chunk_index: int | None = None
    page: int | None = None
    distance: float | None = None
    preview: str


class AskResponse(BaseModel):
    # 这是 /api/ask 返回的 JSON 结构。
    # 它不仅返回 answer，也返回 sources，便于你调试 RAG 检索过程。
    question: str
    answer: str
    sources: list[SourceChunk]


class StatsResponse(BaseModel):
    # 这是 /api/stats 返回的 JSON 结构。
    collection_name: str
    persist_directory: str
    chunk_count: int
    default_top_k: int
