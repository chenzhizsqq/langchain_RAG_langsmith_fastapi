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
