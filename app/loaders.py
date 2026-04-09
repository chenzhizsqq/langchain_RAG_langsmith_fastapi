from __future__ import annotations

"""
这个文件是 Day 4 最关键的文件之一。

它的职责不是定义接口，也不是执行业务主流程，而是：

- 接住“外部输入”
- 把不同形式的输入转换成统一内部格式
- 再交给业务层继续处理

在这个项目里，统一内部格式就是：
- Document

为什么要有 Document？

因为外部输入有很多种：
- JSON 文本
- txt / md 文件
- pdf 文件

如果 rag_service.py 直接分别处理这些原始输入，业务层会很乱。
所以这里先把它们统一转换成 Document，后面的业务层就只需要处理：

- list[Document]

你可以先把这个文件理解成：

- FastAPI / Controller 层和业务层之间的“输入转换层”

如果类比 Spring Boot，它有点像：

- Controller 收到输入之后
- 先做一层 DTO / 文件 / 原始数据 -> 内部业务对象 的转换
- 再把统一对象交给 Service

Day 4 最该盯住的就是这里：
- main.py 负责接住输入
- schemas.py 负责定义 JSON 结构
- loaders.py 负责把外部输入转换成统一内部对象

这个统一内部对象就是：
- Document

所以 Day 4 的最短链路可以先记成：
- JSON / 文件上传 -> main.py -> schemas.py 或 UploadFile -> loaders.py -> Document -> rag_service.py
"""

import re
import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document


TEXT_SUFFIXES = {".txt", ".md", ".markdown"}


def build_text_document(title: str, text: str, source: str | None = None) -> list[Document]:
    # 这个函数处理“纯文本输入”场景。
    # 例如 /api/ingest/text 接收到 title + text 之后，
    # 会先在这里把它转换成统一的 Document。
    # Day 4 对应点：
    # - 外部输入是 JSON 文本
    # - 内部输出是 Document
    return [
        Document(
            # page_content 是真正要进入后续切块 / embedding / 检索流程的正文。
            page_content=text,
            metadata={
                # metadata 是附加信息，后面返回 sources 时会很有用。
                "source": source or f"text:{title}",
                "title": title,
                "document_type": "inline_text",
            },
        )
    ]


def load_seed_documents(seed_directory: Path) -> list[Document]:
    # 这个函数处理“内置示例资料”场景。
    # 它会把 data/seed_docs 里的文本文件统一转成 Document。
    documents: list[Document] = []
    for path in sorted(seed_directory.glob("*")):
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        content = path.read_text(encoding="utf-8")
        documents.append(
            Document(
                page_content=content,
                metadata={
                    "source": f"seed_docs/{path.name}",
                    "title": path.stem,
                    "document_type": "seed_file",
                },
            )
        )
    return documents


def save_upload_file(upload: UploadFile, target_directory: Path) -> Path:
    # 文件上传先保存到本地，再决定怎么读取。
    # 这一步是“原始文件输入 -> 可处理文件路径”的转换。
    # Day 4 对应点：
    # - 这里处理的是外部文件输入
    # - 先保存成稳定文件路径，再继续做后续转换
    original_name = upload.filename or "upload.txt"
    stem = Path(original_name).stem
    suffix = Path(original_name).suffix.lower() or ".txt"
    safe_stem = re.sub(r"[^a-zA-Z0-9_-]+", "-", stem).strip("-") or "upload"
    saved_path = target_directory / f"{safe_stem}-{uuid4().hex}{suffix}"

    with saved_path.open("wb") as buffer:
        shutil.copyfileobj(upload.file, buffer)

    return saved_path


def load_documents_from_saved_file(saved_path: Path) -> list[Document]:
    # 这是 Day 4 的关键函数：
    # 不管外部传进来的是 txt / md / pdf，
    # 这里都尽量把它们转换成统一的 Document 列表。
    # 也就是：
    # - 外部输入格式可以不同
    # - 进入业务层前尽量统一成同一种内部对象
    suffix = saved_path.suffix.lower()

    if suffix in TEXT_SUFFIXES:
        # 文本文件最简单：直接读取内容，包装成一个 Document。
        return [
            Document(
                page_content=saved_path.read_text(encoding="utf-8", errors="ignore"),
                metadata={
                    "source": f"uploads/{saved_path.name}",
                    "title": saved_path.stem,
                    "document_type": "uploaded_text",
                },
            )
        ]

    if suffix == ".pdf":
        # PDF 和纯文本不同，通常会拆成多页，所以这里返回的往往是多个 Document。
        loader = PyPDFLoader(str(saved_path))
        pages = loader.load()
        for page in pages:
            # 对 PDF 页面补 metadata，方便后面知道答案来自哪个文件、哪一页。
            page.metadata["source"] = f"uploads/{saved_path.name}"
            page.metadata["title"] = saved_path.stem
            page.metadata["document_type"] = "uploaded_pdf"
        return pages

    # 这里故意只支持少数格式，目的是先把输入边界控制清楚。
    raise ValueError("当前只支持 .txt、.md、.markdown、.pdf 文件。")
