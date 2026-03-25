from __future__ import annotations

import re
import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document


TEXT_SUFFIXES = {".txt", ".md", ".markdown"}


def build_text_document(title: str, text: str, source: str | None = None) -> list[Document]:
    return [
        Document(
            page_content=text,
            metadata={
                "source": source or f"text:{title}",
                "title": title,
                "document_type": "inline_text",
            },
        )
    ]


def load_seed_documents(seed_directory: Path) -> list[Document]:
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
    original_name = upload.filename or "upload.txt"
    stem = Path(original_name).stem
    suffix = Path(original_name).suffix.lower() or ".txt"
    safe_stem = re.sub(r"[^a-zA-Z0-9_-]+", "-", stem).strip("-") or "upload"
    saved_path = target_directory / f"{safe_stem}-{uuid4().hex}{suffix}"

    with saved_path.open("wb") as buffer:
        shutil.copyfileobj(upload.file, buffer)

    return saved_path


def load_documents_from_saved_file(saved_path: Path) -> list[Document]:
    suffix = saved_path.suffix.lower()

    if suffix in TEXT_SUFFIXES:
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
        loader = PyPDFLoader(str(saved_path))
        pages = loader.load()
        for page in pages:
            page.metadata["source"] = f"uploads/{saved_path.name}"
            page.metadata["title"] = saved_path.stem
            page.metadata["document_type"] = "uploaded_pdf"
        return pages

    raise ValueError("当前只支持 .txt、.md、.markdown、.pdf 文件。")
