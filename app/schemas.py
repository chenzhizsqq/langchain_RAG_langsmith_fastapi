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

再补两个 Day 2 最关键的概念：

1. BaseModel 是什么
   BaseModel 来自 pydantic 这个库。
   它不是 FastAPI 自己定义的，也不是 Python 内建的。
   你可以把它理解成“数据模型父类”。

   当你写：
   class AskRequest(BaseModel):
       ...

   意思就是：
   - AskRequest 是你自己定义的 class
   - 它继承了 pydantic 的 BaseModel
   - 所以它自动拥有“数据解析、类型校验、导出 JSON”这些能力

2. Field 是什么
   Field 也是从 pydantic 导入进来的工具。
   它不是父类，不参与继承。
   它的作用是给字段补充规则，例如：
   - 是否必填
   - 最短长度
   - 最大长度
   - 数值范围

   例如：
   question: str = Field(..., min_length=1)

   这里表示：
   - question 是字符串
   - 这个字段必填
   - 长度至少 1 个字符

你现在也可以先按这三类来读这个文件：

- Request
  表示“客户端传进来的 JSON 结构”
  例如：
  - TextIngestRequest
  - AskRequest

- Response
  表示“服务端返回出去的 JSON 结构”
  例如：
  - HealthResponse
  - IngestResponse
  - AskResponse
  - StatsResponse

- Nested Response
  表示“嵌套在某个 Response 里面的小结构”
  例如：
  - SourceChunk

Day 3 再补一句工程化理解：
- 这个文件只负责“数据长什么样”
- 不负责“业务怎么做”
- 这样别人一看到 schemas.py，就知道这里是结构定义，不是业务逻辑

Day 4 再补一个重点：
- 这个文件主要负责“JSON 输入结构定义”
- 当接口接收 POST JSON 时，通常先在这里定义 Request Model
- 文件上传不一定走 BaseModel，因为文件上传常用的是 UploadFile / File(...)
"""

from pydantic import BaseModel, Field

# 这一行不是“创建 class”，而是“从 pydantic 这个库里导入工具”。
# - BaseModel：数据模型父类
# - Field：字段规则定义工具


class HealthResponse(BaseModel):
    # Response
    # 这是一个 Response Model：描述 /health 返回的 JSON 结构。
    status: str
    runtime_mode: str
    openai_configured: bool
    langsmith_tracing: bool
    langsmith_project: str | None = None


class IngestResponse(BaseModel):
    # Response
    # 导入文档相关接口统一返回这个结构。
    message: str
    documents_count: int
    chunks_count: int
    collection_count: int
    sources: list[str]


class TextIngestRequest(BaseModel):
    # Request
    # 这是一个 Request Model：客户端传 JSON 进来时，要符合这个结构。
    # Day 4 对应点：
    # - 它就是 /api/ingest/text 的 JSON body 结构
    # - 客户端要发文本给后端时，就按这个结构组织 JSON
    # Field(...) 里的规则就是参数校验规则。
    # 这里可以顺便记住：
    # - class ... (BaseModel) 是“定义一个 Pydantic 数据模型”
    # - Field(...) 是“给字段补规则”
    title: str = Field(..., min_length=1, max_length=120)
    text: str = Field(..., min_length=1)
    source: str | None = Field(default=None, max_length=200)


class AskRequest(BaseModel):
    # Request
    # 这是 /api/ask 的请求体。
    # top_k 是可选的；如果传了，就必须在 1 到 10 之间。
    # 用 iOS 思维看，它很像一个 Request struct / Codable model。
    question: str = Field(..., min_length=1)
    top_k: int | None = Field(default=None, ge=1, le=10)


class SourceChunk(BaseModel):
    # Nested Response
    # 这是 AskResponse 里的一部分，表示“命中了哪一段资料”。
    source: str
    chunk_index: int | None = None
    page: int | None = None
    distance: float | None = None
    preview: str


class AskResponse(BaseModel):
    # Response
    # 这是 /api/ask 返回的 JSON 结构。
    # 它不仅返回 answer，也返回 sources，便于你调试 RAG 检索过程。
    # 用 iOS 思维看，它很像一个 Response struct / Codable model。
    question: str
    answer: str
    sources: list[SourceChunk]


class StatsResponse(BaseModel):
    # Response
    # 这是 /api/stats 返回的 JSON 结构。
    collection_name: str
    persist_directory: str
    chunk_count: int
    default_top_k: int
