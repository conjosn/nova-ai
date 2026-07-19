"""Local document ingestion for retrieval-augmented Nova conversations."""

from __future__ import annotations

import json
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class DocumentImportResult:
    filename: str
    chunks: int
    characters: int


class WorkspaceLibrary:
    TEXT_EXTENSIONS = {
        ".txt", ".md", ".rst", ".csv", ".json", ".yaml", ".yml", ".toml",
        ".py", ".js", ".ts", ".log",
    }

    def __init__(self, memory: Any) -> None:
        self.memory = memory

    @staticmethod
    def _read_pdf(path: Path) -> str:
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise RuntimeError("PDF import requires pypdf") from exc
        return "\n\n".join(page.extract_text() or "" for page in PdfReader(path).pages)

    @staticmethod
    def _read_docx(path: Path) -> str:
        try:
            from docx import Document
        except ImportError as exc:
            raise RuntimeError("Word import requires python-docx") from exc
        return "\n".join(paragraph.text for paragraph in Document(path).paragraphs)

    @classmethod
    def read_text(cls, path: str | Path) -> str:
        file_path = Path(path).expanduser()
        suffix = file_path.suffix.lower()
        if suffix == ".pdf":
            text = cls._read_pdf(file_path)
        elif suffix == ".docx":
            text = cls._read_docx(file_path)
        elif suffix in cls.TEXT_EXTENSIONS:
            text = file_path.read_text(encoding="utf-8", errors="replace")
            if suffix == ".json":
                with suppress(json.JSONDecodeError):
                    text = json.dumps(json.loads(text), indent=2, ensure_ascii=False)
        else:
            raise ValueError(f"Unsupported knowledge file: {suffix or 'no extension'}")
        normalized = text.strip()
        if not normalized:
            raise ValueError("The selected document contains no readable text")
        return normalized

    @staticmethod
    def chunk_text(text: str, size: int = 1400, overlap: int = 180) -> list[str]:
        if size <= overlap or overlap < 0:
            raise ValueError("Chunk size must be greater than overlap")
        chunks: list[str] = []
        start = 0
        while start < len(text):
            end = min(len(text), start + size)
            if end < len(text):
                boundary = max(text.rfind("\n", start, end), text.rfind(" ", start, end))
                if boundary > start + size // 2:
                    end = boundary
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            if end >= len(text):
                break
            start = max(start + 1, end - overlap)
        return chunks

    def ingest_file(self, path: str | Path) -> DocumentImportResult:
        file_path = Path(path).expanduser().resolve()
        text = self.read_text(file_path)
        chunks = self.chunk_text(text)
        stored = 0
        for index, chunk in enumerate(chunks, start=1):
            memory_id = self.memory.add_memory(
                f"[Document: {file_path.name} | chunk {index}/{len(chunks)}]\n{chunk}",
                {
                    "type": "document",
                    "source": str(file_path),
                    "filename": file_path.name,
                    "chunk": index,
                },
            )
            stored += int(memory_id is not None)
        return DocumentImportResult(file_path.name, stored, len(text))
