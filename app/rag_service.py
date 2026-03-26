from __future__ import annotations

from collections import defaultdict
from hashlib import sha1
from typing import Any

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langsmith import traceable

from app.config import Settings
from app.mock_runtime import LocalHashEmbeddings, build_mock_answer


class RAGService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.settings.validate_runtime()

        if settings.is_test_mode:
            # 测试模式目标是“先验证架构能不能跑”，所以完全走本地实现：
            # mock embedding + 内存向量库 + mock answer。
            self.embeddings = LocalHashEmbeddings(dimensions=settings.mock_embedding_dimensions)
            self.llm = None
            self.vector_store = InMemoryVectorStore(self.embeddings)
        else:
            # 生产模式才接真实 OpenAI 和 Chroma。
            self.embeddings = OpenAIEmbeddings(model=settings.embedding_model)
            self.llm = ChatOpenAI(model=settings.chat_model, temperature=0)
            self.vector_store = Chroma(
                collection_name=settings.chroma_collection_name,
                embedding_function=self.embeddings,
                persist_directory=str(settings.chroma_persist_directory),
            )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            separators=["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""],
        )
        self.prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    (
                        # 这个 prompt 的职责很单一：限制模型优先依据检索上下文回答，
                        # 避免把普通聊天风格带进知识库问答。
                        "你是一个面向初学者的 RAG 教学助手。"
                        "请优先基于给定 context 回答。"
                        "如果 context 不足，就明确说当前知识库信息不足，并指出还缺什么资料。"
                        "默认使用简体中文回答，先给结论，再给简短解释。"
                    ),
                ),
                (
                    "user",
                    "问题：{question}\n\n可用 context：\n{context}",
                ),
            ]
        )

    def collection_count(self) -> int:
        if self.settings.is_test_mode:
            return len(self.vector_store.store)
        return self.vector_store._collection.count()

    def _chunk_documents(self, documents: list[Document]) -> list[Document]:
        # 进入向量库之前先切块，并为每个来源补一个 chunk_index，
        # 这样后面返回 sources 时能告诉你命中了原文的哪一段。
        split_documents = self.text_splitter.split_documents(documents)
        chunk_counters: dict[str, int] = defaultdict(int)
        normalized: list[Document] = []

        for document in split_documents:
            metadata = dict(document.metadata)
            source = str(metadata.get("source", "unknown"))
            metadata["source"] = source
            metadata["chunk_index"] = chunk_counters[source]
            chunk_counters[source] += 1
            normalized.append(Document(page_content=document.page_content, metadata=metadata))

        return normalized

    def _build_ids(self, documents: list[Document]) -> list[str]:
        ids: list[str] = []
        for document in documents:
            source = str(document.metadata.get("source", "unknown"))
            page = str(document.metadata.get("page", "na"))
            chunk_index = str(document.metadata.get("chunk_index", "na"))
            # 用内容相关的稳定 ID，避免同一份文档重复导入时完全失控。
            payload = f"{source}|{page}|{chunk_index}|{document.page_content}"
            ids.append(sha1(payload.encode("utf-8")).hexdigest())
        return ids

    @traceable(name="ingest_documents")
    def ingest_documents(self, documents: list[Document]) -> dict[str, Any]:
        # ingest 是 RAG 的“索引阶段”入口：切块 -> 向量化 -> 写入向量库。
        chunks = self._chunk_documents(documents)
        if not chunks:
            return {
                "message": "没有可导入的文档内容。",
                "documents_count": 0,
                "chunks_count": 0,
                "collection_count": self.collection_count(),
                "sources": [],
            }

        ids = self._build_ids(chunks)
        self.vector_store.add_documents(documents=chunks, ids=ids)

        sources = sorted({str(document.metadata.get("source", "unknown")) for document in chunks})
        return {
            "message": "文档导入完成。",
            "documents_count": len(documents),
            "chunks_count": len(chunks),
            "collection_count": self.collection_count(),
            "sources": sources,
        }

    def _format_context(self, matches: list[tuple[Document, float]]) -> str:
        # 把检索结果展开成可读 context，便于模型回答，也便于后续接 LangSmith 观察。
        blocks: list[str] = []
        for index, (document, distance) in enumerate(matches, start=1):
            source = str(document.metadata.get("source", "unknown"))
            chunk_index = document.metadata.get("chunk_index", "?")
            page = document.metadata.get("page")
            page_text = f" | page={page}" if page is not None else ""
            blocks.append(
                f"[片段 {index}] source={source} | chunk={chunk_index}{page_text} | distance={distance:.4f}\n"
                f"{document.page_content.strip()}"
            )
        return "\n\n".join(blocks)

    @staticmethod
    def _extract_text(response: Any) -> str:
        text = getattr(response, "text", None)
        if isinstance(text, str) and text.strip():
            return text.strip()

        content = getattr(response, "content", "")
        if isinstance(content, str):
            return content.strip()

        if isinstance(content, list):
            pieces: list[str] = []
            for item in content:
                if isinstance(item, str):
                    pieces.append(item)
                    continue
                if isinstance(item, dict):
                    maybe_text = item.get("text")
                    if isinstance(maybe_text, str):
                        pieces.append(maybe_text)
            joined = "\n".join(piece.strip() for piece in pieces if piece.strip()).strip()
            if joined:
                return joined

        return str(content).strip()

    @staticmethod
    def _preview(text: str, limit: int = 180) -> str:
        single_line = " ".join(text.split())
        if len(single_line) <= limit:
            return single_line
        return f"{single_line[: limit - 3]}..."

    @traceable(name="answer_question")
    def answer_question(self, question: str, top_k: int | None = None) -> dict[str, Any]:
        if self.collection_count() == 0:
            return {
                "question": question,
                "answer": "知识库还是空的。请先调用 /api/ingest/sample 或导入你自己的文件。",
                "sources": [],
            }

        resolved_top_k = top_k or self.settings.top_k
        # ask 是 RAG 的“检索 + 生成阶段”入口。
        matches = self.vector_store.similarity_search_with_score(question, k=resolved_top_k)

        if not matches:
            return {
                "question": question,
                "answer": "没有检索到相关内容。你可以先补充文档，再重新提问。",
                "sources": [],
            }

        context = self._format_context(matches)
        if self.settings.is_test_mode:
            answer = build_mock_answer(question, matches)
        else:
            # 生产模式下，真正把“问题 + 检索上下文”交给 LLM。
            prompt_value = self.prompt.invoke({"question": question, "context": context})
            response = self.llm.invoke(prompt_value)
            answer = self._extract_text(response)

        sources = [
            {
                "source": str(document.metadata.get("source", "unknown")),
                "chunk_index": document.metadata.get("chunk_index"),
                "page": document.metadata.get("page"),
                "distance": float(distance),
                "preview": self._preview(document.page_content),
            }
            for document, distance in matches
        ]

        return {"question": question, "answer": answer, "sources": sources}
