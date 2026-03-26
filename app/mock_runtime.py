from __future__ import annotations

import math
import re
from hashlib import sha1

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings


TOKEN_PATTERN = re.compile(r"[\u4e00-\u9fff]|[a-zA-Z0-9_]+")


class LocalHashEmbeddings(Embeddings):
    def __init__(self, dimensions: int = 64) -> None:
        self.dimensions = dimensions

    def _tokenize(self, text: str) -> list[str]:
        tokens = TOKEN_PATTERN.findall(text.lower())
        if tokens:
            return tokens
        return [char for char in text.lower() if not char.isspace()]

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for token in self._tokenize(text):
            index = int(sha1(token.encode("utf-8")).hexdigest(), 16) % self.dimensions
            vector[index] += 1.0

        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)


def build_mock_answer(question: str, matches: list[tuple[Document, float]]) -> str:
    sources = []
    highlights = []

    for document, _distance in matches[:3]:
        source = str(document.metadata.get("source", "unknown"))
        if source not in sources:
            sources.append(source)
        text = " ".join(document.page_content.split())
        if text:
            highlights.append(text[:140])

    source_text = "、".join(sources) if sources else "无"
    highlight_text = "；".join(highlights) if highlights else "当前没有足够的检索片段。"

    return (
        "这是测试模式下的本地回答，不依赖真实 OpenAI API。\n"
        f"问题：{question}\n"
        "当前已经跑通的链路包括：文档切块、向量写入、向量检索、上下文组装、API 返回。\n"
        f"命中的来源：{source_text}\n"
        f"检索摘要：{highlight_text}"
    )
