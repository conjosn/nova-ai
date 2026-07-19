"""Offline, persistent retrieval memory backed by ChromaDB."""

from __future__ import annotations

import hashlib
import math
import re
import threading
from datetime import datetime, timezone
from typing import Any

from utils.logger import NovaLogger
from utils.paths import MEMORY_PATH, ensure_data_dirs

logger = NovaLogger()


class LocalHashEmbeddingFunction:
    """Tiny deterministic embedding that never downloads a remote model.

    This is deliberately lightweight for Nova's small nodes. It provides lexical
    similarity immediately; a learned local embedding model can replace it later.
    """

    dimensions = 384

    @staticmethod
    def name() -> str:
        return "nova_local_hash"

    @staticmethod
    def build_from_config(config: dict[str, Any]) -> LocalHashEmbeddingFunction:
        del config
        return LocalHashEmbeddingFunction()

    def get_config(self) -> dict[str, Any]:
        return {"dimensions": self.dimensions, "version": 1}

    def default_space(self) -> str:
        return "cosine"

    def __call__(self, input: list[str]) -> list[list[float]]:
        embeddings: list[list[float]] = []
        for document in input:
            vector = [0.0] * self.dimensions
            tokens = re.findall(r"[a-z0-9_'-]+", document.lower())
            for token in tokens:
                digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
                value = int.from_bytes(digest, "little")
                index = value % self.dimensions
                vector[index] += -1.0 if value & 1 else 1.0
            norm = math.sqrt(sum(component * component for component in vector))
            if norm:
                vector = [component / norm for component in vector]
            embeddings.append(vector)
        return embeddings

    def embed_query(self, input: list[str]) -> list[list[float]]:
        return self(input)


class PersistentMemory:
    def __init__(self, collection_name: str = "nova_memory") -> None:
        try:
            import chromadb
            from chromadb.config import Settings
        except ImportError as exc:
            raise RuntimeError("chromadb is not installed") from exc

        ensure_data_dirs()
        self.collection_name = collection_name
        self.client = chromadb.PersistentClient(
            path=str(MEMORY_PATH),
            settings=Settings(anonymized_telemetry=False),
        )
        self._embedding_function = LocalHashEmbeddingFunction()
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self._embedding_function,
            metadata={"hnsw:space": "cosine"},
        )
        self._lock = threading.RLock()

    @staticmethod
    def _memory_id(content: str, memory_type: str) -> str:
        payload = f"{memory_type}\0{content.strip()}".encode()
        return hashlib.sha256(payload).hexdigest()

    def add_memory(self, content: str, metadata: dict[str, Any] | None = None) -> str | None:
        normalized = content.strip()
        if not normalized:
            return None
        safe_metadata = {
            key: value
            for key, value in (metadata or {}).items()
            if isinstance(value, str | int | float | bool)
        }
        safe_metadata.setdefault("type", "general")
        safe_metadata.setdefault("created_at", datetime.now(timezone.utc).isoformat())
        memory_id = self._memory_id(normalized, str(safe_metadata["type"]))
        with self._lock:
            self.collection.upsert(
                documents=[normalized],
                metadatas=[safe_metadata],
                ids=[memory_id],
            )
        return memory_id

    def retrieve_relevant(
        self,
        query: str,
        n_results: int = 5,
        *,
        memory_type: str | None = None,
    ) -> list[str]:
        if not query.strip() or n_results <= 0:
            return []
        with self._lock:
            count = self.collection.count()
            if count == 0:
                return []
            kwargs: dict[str, Any] = {
                "query_texts": [query],
                "n_results": min(n_results, count),
                "include": ["documents"],
            }
            if memory_type:
                kwargs["where"] = {"type": memory_type}
            results = self.collection.query(**kwargs)
        documents = results.get("documents") or [[]]
        return [document for document in documents[0] if document]

    def clear(self) -> None:
        with self._lock:
            self.client.delete_collection(self.collection_name)
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                embedding_function=self._embedding_function,
                metadata={"hnsw:space": "cosine"},
            )
