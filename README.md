# RAG Knowledge API

## 先看这张图

如果你是用 Spring Boot 思维来理解这个项目，先记这一版就够了：

```text
客户端（iOS / Web）
        |
        v
app/main.py
FastAPI 接口入口层
≈ Spring Boot 的 Controller
        |
        v
app/rag_service.py
RAG 业务处理层
≈ Spring Boot 的 Service
        |
        v
向量检索 / 模型调用
test 模式：本地 mock embedding + 内存向量库 + mock answer
production 模式：OpenAI Embeddings + ChatOpenAI + Chroma
≈ Spring Boot 的 Repository/外部服务/数据库
        |
        v
app/schemas.py
请求与响应的数据结构定义
≈ Spring Boot 的 DTO / Request / Response class
```

你以后如果一段时间没回来，先只回忆这三层：

- [app/main.py](./app/main.py)：接口入口层
- [app/rag_service.py](./app/rag_service.py)：业务核心层
- [app/schemas.py](./app/schemas.py)：数据结构层

最短调用链是：

`客户端请求 -> main.py -> rag_service.py -> main.py -> schemas.py -> JSON 响应`

## Day 7：iOS 视角的完整 AI 架构图

到了 Day 7，就不要再只盯 `FastAPI` 本身，而要把整条链路一起看：

```text
iOS App
用户输入问题 / 上传内容
        |
        v
FastAPI
app/main.py
后端门面层，负责接请求、调业务、回 JSON
        |
        v
RAG Service
app/rag_service.py
业务逻辑层，负责检索、组装上下文、生成答案
        |
        +----------------------+
        |                      |
        v                      v
Vector DB                  LLM API
Chroma / 内存向量库         ChatOpenAI / mock answer
负责语义检索                负责生成自然语言答案
        |
        v
FastAPI 返回 JSON
AskResponse / HealthResponse / IngestResponse
        |
        v
iOS App 展示结果
答案 / 来源 / 状态
```

可以先把这五层记成：

- `iOS`：客户端层
- `FastAPI`：后端门面层
- `RAG Service`：业务逻辑层
- `Vector DB`：检索层
- `LLM API`：生成层

如果以后你在 iOS App 里接 AI，这条链路通常会是这样：

1. 用户在 iPhone 上输入问题
2. iOS 调 FastAPI 的 `/api/ask`
3. [app/main.py](./app/main.py) 接住请求
4. [app/rag_service.py](./app/rag_service.py) 先做检索
5. 向量库返回最相关的资料片段
6. `rag_service.py` 再把问题和资料交给模型
7. 模型生成答案
8. `main.py` 用 [app/schemas.py](./app/schemas.py) 组织成 JSON
9. FastAPI 把结果回给 iOS
10. iOS 把答案和来源展示给用户

所以 Day 7 最重要的不是某个单独文件，而是脑子里能稳定记住这句：

`iOS -> FastAPI -> RAG Service -> Vector DB / LLM API -> FastAPI -> iOS`

## Day 3 总结

这套结构的核心不是“文件分开而已”，而是先约定每一层只做自己的事：

- [app/main.py](./app/main.py)：只负责接口入口，不堆复杂业务
- [app/rag_service.py](./app/rag_service.py)：只负责业务主流程
- [app/schemas.py](./app/schemas.py)：只负责请求和响应结构

这样做的目的很实际：

- 自己过一周回来还能快速定位
- 别的开发者一看就知道去哪里改
- 不会把接口层写成巨型业务文件
- 后面功能继续增加时，更容易维护

## Day 4 总结

Day 4 的核心可以先用一句很白的话记住：

先把乱的输入输出变规范，再让业务层处理。

放到这个项目里，就是：

- [app/main.py](./app/main.py)：接住不同输入，例如 JSON、文件上传
- [app/schemas.py](./app/schemas.py)：把接口输入输出定义成统一结构
- [app/loaders.py](./app/loaders.py)：把外部输入转换成统一内部对象 `Document`
- [app/rag_service.py](./app/rag_service.py)：只处理已经整理好的统一数据

这样做的目的也很实际：

- 不同来源的数据更容易统一处理
- 业务层不用为每种输入分别写一套逻辑
- 数据传入传出会更稳定
- 后面扩展输入类型时更容易维护

## Day 5 总结

Day 5 的核心可以先这样记：

FastAPI 本身只是入口，真正的价值在它后面接了什么能力。

放到这个项目里，可以先这样看：

- [app/main.py](./app/main.py)：接口入口层，只负责接请求和回结果
- [app/rag_service.py](./app/rag_service.py)：外部能力编排层，真正把模型、检索、业务流程串起来
- [app/config.py](./app/config.py)：外部能力配置入口，例如模型名、API key、向量库目录
- [app/loaders.py](./app/loaders.py)：负责把真实输入整理成业务层能处理的统一格式

对这个项目来说，Day 5 里最重要的“后面能力”主要是：

- OpenAIEmbeddings
- ChatOpenAI
- Chroma
- LangSmith traceable
- test 模式下的本地 mock runtime

所以可以先把最短理解记成：

`iOS / Web -> FastAPI -> RAGService -> 模型 / 向量库 / 文件处理 -> FastAPI -> 客户端`

## Day 6 总结

Day 6 的核心可以先这样记：

不是先修所有 bug，而是先判断 bug 在哪一层。

你现在这个项目，最实用的排查顺序是：

1. 先看控制台日志  
   先确认服务有没有正常启动。

2. 再看 `/docs` 和 `/openapi.json`  
   先确认接口有没有正常注册。

3. 再调最简单的接口，例如 `/health`  
   先确认请求能不能打进去。

4. 再判断问题属于哪一层  
   - 请求层：URL、端口、路径不对
   - 参数层：JSON 结构不对、字段缺失、校验失败
   - 业务层：service、loader、config、外部能力调用有问题

对这个项目来说，可以先粗略这样分：

- [app/main.py](./app/main.py)：服务和接口入口层，先看服务是否启动、路由是否注册
- [app/schemas.py](./app/schemas.py)：参数和返回结构层，先看请求 JSON 是否符合定义
- [app/loaders.py](./app/loaders.py)：输入转换层，先看文件或文本有没有被正确转成 `Document`
- [app/rag_service.py](./app/rag_service.py)：业务层，先看检索、模型调用、mock/production 分支是否正常

所以 Day 6 的目标不是“掌握全部错误”，而是建立一个固定的判断顺序。

### Day 6 四步调试法

#### 第一步：先看控制台日志

这一层先确认的不是业务，而是服务本身有没有真正启动成功。

- 如果你是用 `.venv/bin/python -m app.main` 启动，就先盯终端输出
- 正常情况下应该能看到：
  - `Started server process`
  - `Application startup complete`
  - `Uvicorn running on http://127.0.0.1:8000`

这一步主要对应：

- [app/main.py](./app/main.py)
- [app/config.py](./app/config.py)
- `.env`

如果这里就报错，通常优先怀疑：

- 运行命令不对
- 虚拟环境没启用
- 配置项有问题
- `main.py` 或导入模块本身出错

也就是说，这一步是在判断：
“服务有没有活着，而不是接口逻辑对不对。”

#### 第二步：再看 `/docs` 和 `/openapi.json`

这一步主要是确认接口层有没有正常注册。

- 如果 `/docs` 能打开，说明 FastAPI 基本已经正常工作
- 如果 `/openapi.json` 能返回，说明路由和 schema 基本都已注册成功

这一步最对应的文件是：

- [app/main.py](./app/main.py)
- [app/schemas.py](./app/schemas.py)

原因是：

- 路由装饰器都写在 `main.py`
- 请求和响应结构会影响 OpenAPI 文档生成

如果这一步不通，通常优先怀疑：

- 路由没注册成功
- 服务其实没真正跑起来
- host / port 访问错了
- `schemas.py` 或 `main.py` 有加载问题

这一步本质是在确认：
“这个后端到底有没有把接口暴露出来。”

#### 第三步：先调最简单的接口，例如 `/health`

这一步不是在测复杂功能，而是在测最基础的请求链路。

- `/health` 成功，通常说明：
  - 请求已经能打进 FastAPI
  - 路由命中了
  - 返回 JSON 正常
  - 基本配置能被读取

这一步主要对应：

- [app/main.py](./app/main.py)
- [app/schemas.py](./app/schemas.py)
- [app/config.py](./app/config.py)

为什么先调 `/health`：

- 它不依赖文件上传
- 不依赖文档入库
- 不依赖 RAG 检索
- 不依赖复杂业务分支

所以如果 `/health` 都不通，就不要先去怀疑 `rag_service.py`，因为问题多半还没到业务层。

#### 第四步：再判断问题属于哪一层

到了这一步，才开始真正分层定位。

##### 请求层

常见现象：

- 连不上服务
- `404 Not Found`
- `405 Method Not Allowed`
- 控制台没有这次请求日志

优先看：

- [app/main.py](./app/main.py)
- `/docs`
- 请求 URL、端口、路径、HTTP 方法

这层的典型问题是：

- 路径写错
- 端口写错
- 用错 `GET` / `POST`
- 根本没打到后端

##### 参数层

常见现象：

- `422 Unprocessable Entity`
- `400 Bad Request`
- Swagger 里提示字段校验失败

优先看：

- [app/schemas.py](./app/schemas.py)

这层的典型问题是：

- JSON 结构不对
- 必填字段缺失
- 字段类型不对
- 长度或数值范围没满足 `Field(...)` 的规则

这一步的本质是判断：
“请求已经进来了，但数据格式有没有符合接口约定。”

##### 业务层

常见现象：

- 请求进来了
- 参数也合法
- 但返回 `500`
- 或者返回成功但结果明显不对

优先看：

- [app/rag_service.py](./app/rag_service.py)
- [app/loaders.py](./app/loaders.py)
- [app/config.py](./app/config.py)
- [app/mock_runtime.py](./app/mock_runtime.py)

这层的典型问题是：

- 文本或文件没被正确转成 `Document`
- mock / production 模式切错
- 向量库里没数据
- settings 配错
- 外部能力调用异常

这一步本质是在判断：
“不是接口格式问题，而是后面的处理流程出问题了。”

### Day 6 常见错误速查

| 现象 / 状态 | 通常说明什么 | 优先先看哪里 |
| --- | --- | --- |
| 连不上服务 | 服务可能没启动，或者 host / port 不对 | 控制台启动日志、`app/main.py`、`.env` 里的 `APP_HOST` / `APP_PORT` |
| `404 Not Found` | 路径写错，或者接口没注册到这个 URL | `/docs`、`app/main.py` |
| `405 Method Not Allowed` | 路径是对的，但 HTTP 方法错了，例如把 `POST` 写成了 `GET` | `/docs`、`app/main.py` |
| `422 Unprocessable Entity` | 请求 JSON 结构不对，字段缺失、类型不对、校验没过 | `app/schemas.py` |
| `400 Bad Request` | 请求格式本身不合法，或者业务上主动拒绝了输入 | `app/main.py`、`app/loaders.py` |
| `500 Internal Server Error` | 请求进来了，但后端业务层或配置层出错了 | 控制台报错、`app/config.py`、`app/loaders.py`、`app/rag_service.py` |
| 返回成功但结果不对 | 路由和参数可能都没问题，问题多半在业务逻辑或检索结果 | `app/rag_service.py`、`/api/stats`、LangSmith trace |

这是一个重新从零搭好的入门项目，主题就是你要的这五块：

- LangChain
- RAG
- LangSmith
- FastAPI
- Vector DB

这个项目不是只讲概念，而是把概念直接落成一个能跑的 Demo：

- 用 `FastAPI` 暴露接口
- 用 `LangChain` 组织 RAG 流程
- 在生产模式用 `OpenAI Embeddings` 把文本转成向量
- 用 `Chroma` 做本地 Vector DB
- 用 `LangSmith` 看调用链路和调试过程

## 你会做出什么

你会得到一个最小可运行的知识库问答服务：

1. 把文档切块
2. 把切块后的文本做 embedding
3. 存进 Chroma 向量库
4. 用户提问时做相似度检索
5. 把检索到的上下文交给大模型生成答案
6. 在 LangSmith 里看到整个调用过程

## 为什么这套组合适合初学者

- `LangChain` 适合把“加载文档、切块、Embedding、检索、调用模型”串起来。
- `RAG` 是 AI 应用最常见的入门场景之一，比一上来做 Agent 更容易建立理解。
- `LangSmith` 能帮你看到“问题到底出在哪”，这对初学者特别重要。
- `FastAPI` 很适合把 Python AI 代码包成接口，之后接前端或 App 都方便。
- `Chroma` 可以本地跑，不用一开始就接云端向量库。

## 目录结构

```text
langchain_RAG_langsmith_fastapi/
├── app/
│   ├── config.py
│   ├── loaders.py
│   ├── main.py
│   ├── rag_service.py
│   └── schemas.py
├── data/
│   └── seed_docs/
│       ├── 01-langchain.md
│       ├── 02-rag.md
│       ├── 03-langsmith.md
│       ├── 04-fastapi.md
│       └── 05-vector-db.md
├── docs/
│   ├── 01-学习路线.md
│   ├── 02-RAG工作流.md
│   └── 03-LangSmith与调试.md
├── storage/
│   └── 运行时目录，保存 Chroma 数据和上传文件，不是手动维护的源码目录
├── .env.example
├── pyproject.toml
└── README.md
```

## 先建立最小理解

### 1. LangChain 是什么

它不是模型本身，而是帮你把 AI 应用开发里的各种组件串起来的工具层。

比如：

- 文档加载
- 文本切块
- Embedding
- 向量检索
- Prompt 组织
- 调用大模型

### 2. RAG 是什么

RAG = Retrieval-Augmented Generation，中文可以理解成“先查资料，再生成答案”。

核心目的：减少模型胡编，尽量让答案基于你自己的资料。

### 3. Vector DB 是什么

Vector DB 存的不是普通字符串索引，而是 embedding 向量。这样它可以按“语义相似度”找内容，而不是只按关键词。

### 4. FastAPI 在这里做什么

它把这套 RAG 能力暴露成 HTTP API。以后你要接网页、移动端、管理后台，都会方便很多。

### 5. LangSmith 做什么

LangSmith 主要用来看链路、调试和评估。你可以看到：

- 检索了哪些文档
- prompt 长什么样
- 模型回了什么
- 哪一步变慢了

## 快速开始

### 1. 进入目录

```bash
cd langchain_RAG_langsmith_fastapi
```

### 2. 创建虚拟环境

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. 安装依赖

```bash
pip install -e .
```

### 4. 准备环境变量

```bash
cp .env.example .env
```

默认的 `.env.example` 已经是 `APP_MODE=test`，所以你现在只是测试整个架构的话，不需要真实 OpenAI Key。

如果你要切到生产模式，再把这些项补上：

- `APP_MODE=production`
- `OPENAI_API_KEY=你的真实 key`

如果你还想看 LangSmith 链路，再填：

- `LANGSMITH_API_KEY`
- `LANGSMITH_TRACING=true`

### 5. 启动服务

```bash
.venv/bin/python -m app.main
```

如果你想要开发时自动重载，可以改用：

```bash
python -m uvicorn app.main:app --reload
```

打开：

- Swagger 文档: `http://127.0.0.1:8000/docs`
- 健康检查: `http://127.0.0.1:8000/health`

## 跑一遍完整流程

### 第一步：导入内置示例文档

```bash
curl -X POST http://127.0.0.1:8000/api/ingest/sample
```

在 `APP_MODE=test` 下，这一步会使用本地 mock embedding 和内存向量库，把文档正常写入检索层，用来验证你的整体架构是否跑通。

### 第二步：提问

```bash
curl -X POST http://127.0.0.1:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "LangSmith 在这个项目里主要解决什么问题？",
    "top_k": 4
  }'
```

### 第三步：导入你自己的文本

```bash
curl -X POST http://127.0.0.1:8000/api/ingest/text \
  -H "Content-Type: application/json" \
  -d '{
    "title": "my-notes",
    "text": "RAG 的核心是先检索，再让模型基于上下文生成答案。"
  }'
```

### 第四步：上传文件

支持：

- `.txt`
- `.md`
- `.markdown`
- `.pdf`

示例：

```bash
curl -X POST http://127.0.0.1:8000/api/ingest/file \
  -F "file=@./your-notes.pdf"
```

## 代码怎么对应五个关键词

### LangChain

在 [app/rag_service.py](./app/rag_service.py) 里。

这里负责：

- `RecursiveCharacterTextSplitter`
- `OpenAIEmbeddings`
- `Chroma`
- `ChatOpenAI`
- prompt 组织

补充：

- 在 `APP_MODE=test` 下，项目会自动切到本地 mock embedding、本地内存向量库和本地 mock answer，用来做无 key 的架构联调。
- 在 `APP_MODE=production` 下，项目才会切回 `OpenAIEmbeddings + ChatOpenAI + Chroma`。

### RAG

RAG 的主流程也在 [app/rag_service.py](./app/rag_service.py) 里：

1. ingest 文档
2. 切块
3. 建立向量
4. 相似度检索
5. 组装上下文
6. 调模型回答

### LangSmith

只要你配置：

- `LANGSMITH_TRACING=true`
- `LANGSMITH_API_KEY`

LangChain 的调用就会自动出现在 LangSmith 里。项目里还额外用 `@traceable` 把关键方法包起来了，便于你看每一步。

### FastAPI

入口在 [app/main.py](./app/main.py)：

- `/health`
- `/api/ingest/sample`
- `/api/ingest/text`
- `/api/ingest/file`
- `/api/ask`
- `/api/stats`

### Vector DB

这里选择的是 `Chroma`，默认做本地持久化：

- 默认目录：`storage/chroma`

这是最适合入门的一种方式，因为不需要你先理解云端部署和密钥管理。

## 建议的学习顺序

按这个顺序学，会比较稳：

1. 先理解普通 LLM 问答和 RAG 的区别
2. 再理解 embedding 和向量检索
3. 再看 LangChain 如何把这些步骤串起来
4. 再看 FastAPI 如何把能力封装成 API
5. 最后用 LangSmith 去观察和调试

## 初学者最容易踩的坑

### 1. 以为 LangChain 就是模型

不是。模型是 `OpenAI` 这类服务，LangChain 更像“AI 应用流程编排层”。

### 2. 以为 RAG 能自动保证真相

不是。RAG 只是把相关资料喂给模型，但检索错了、切块不好、资料本身有问题，答案照样会偏。

### 3. 只看最终答案，不看检索过程

这是调试 AI 应用最常见的误区。很多时候问题不是模型，而是检索阶段。

### 4. 一开始就上复杂 Agent

不建议。先把“单轮 RAG + API + tracing”跑通，再往上加复杂能力。

## 下一步怎么扩展

你把这套跑通以后，可以继续做：

1. 给 `/api/ask` 增加对话历史
2. 给 Chroma 增加 metadata 过滤
3. 加一个前端页面
4. 把本地 Chroma 换成 Pinecone、Qdrant 或 Weaviate
5. 加评测集，用 LangSmith 做 answer quality 评估

## 参考思路

这次重建时，我按当前官方文档核对了以下方向：

- LangChain 的 RAG、OpenAI、Chroma 集成
- LangSmith tracing
- FastAPI 官方 tutorial
- Chroma 官方介绍

如果你后面要，我还可以继续在这个目录上帮你补第二阶段内容，比如：

- 多轮对话记忆版
- 前端页面版
- 本地模型版
- PostgreSQL + pgvector 版
