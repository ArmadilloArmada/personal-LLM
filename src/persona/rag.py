"""RAG document store — ingest company docs and search for persona context."""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]{2,}", text.lower())


def _chunk_text(text: str, size: int = 900, overlap: int = 120) -> list[str]:
    text = text.strip()
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = min(len(text), start + size)
        chunks.append(text[start:end])
        if end >= len(text):
            break
        start = max(0, end - overlap)
    return chunks


class DocumentStore:
    """Workspace-scoped document index with lexical search."""

    SUPPORTED_SUFFIXES = {".txt", ".md", ".markdown", ".csv", ".json", ".yaml", ".yml", ".rst"}

    def __init__(self, workspace_dir: Path):
        self.docs_dir = workspace_dir / "docs"
        self.docs_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.docs_dir / "index.json"
        self._index: dict = {"documents": [], "chunks": []}
        self._load()

    def _load(self) -> None:
        if self.index_path.exists():
            self._index = json.loads(self.index_path.read_text(encoding="utf-8"))
        else:
            self._index = {"documents": [], "chunks": []}

    def _save(self) -> None:
        self.index_path.write_text(json.dumps(self._index, indent=2), encoding="utf-8")

    def list_documents(self) -> list[dict]:
        return list(self._index.get("documents", []))

    def ingest(self, filename: str, content: str) -> dict:
        doc_id = str(uuid.uuid4())[:8]
        safe_name = Path(filename).name
        stored = self.docs_dir / f"{doc_id}_{safe_name}"
        stored.write_text(content, encoding="utf-8")

        doc = {
            "id": doc_id,
            "filename": safe_name,
            "size": len(content),
            "chunks": 0,
            "ingested_at": datetime.now(timezone.utc).isoformat(),
        }

        new_chunks = []
        for i, chunk in enumerate(_chunk_text(content)):
            new_chunks.append(
                {
                    "id": f"{doc_id}_{i}",
                    "doc_id": doc_id,
                    "filename": safe_name,
                    "text": chunk,
                    "tokens": _tokenize(chunk),
                }
            )

        doc["chunks"] = len(new_chunks)
        self._index["documents"] = [d for d in self._index["documents"] if d["id"] != doc_id]
        self._index["documents"].append(doc)
        self._index["chunks"] = [c for c in self._index["chunks"] if c["doc_id"] != doc_id]
        self._index["chunks"].extend(new_chunks)
        self._save()
        return doc

    def ingest_file(self, path: Path) -> dict:
        content = path.read_text(encoding="utf-8", errors="replace")
        return self.ingest(path.name, content)

    def delete(self, doc_id: str) -> bool:
        before = len(self._index["documents"])
        self._index["documents"] = [d for d in self._index["documents"] if d["id"] != doc_id]
        self._index["chunks"] = [c for c in self._index["chunks"] if c["doc_id"] != doc_id]
        for path in self.docs_dir.glob(f"{doc_id}_*"):
            path.unlink(missing_ok=True)
        self._save()
        return len(self._index["documents"]) < before

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        terms = _tokenize(query)
        if not terms:
            return []

        scored: list[tuple[float, dict]] = []
        for chunk in self._index.get("chunks", []):
            tokens = chunk.get("tokens", [])
            if not tokens:
                continue
            score = sum(tokens.count(t) for t in terms) / (len(tokens) ** 0.5)
            if score <= 0:
                continue
            scored.append(
                (
                    score,
                    {
                        "doc_id": chunk["doc_id"],
                        "filename": chunk["filename"],
                        "snippet": chunk["text"][:400],
                        "score": round(score, 3),
                    },
                )
            )

        scored.sort(key=lambda x: x[0], reverse=True)
        seen = set()
        results = []
        for _, item in scored:
            key = (item["doc_id"], item["snippet"][:80])
            if key in seen:
                continue
            seen.add(key)
            results.append(item)
            if len(results) >= top_k:
                break
        return results

    def context_block(self, query: str, top_k: int = 3) -> str:
        hits = self.search(query, top_k=top_k)
        if not hits:
            return ""
        lines = ["Relevant company documents:"]
        for hit in hits:
            lines.append(f"- [{hit['filename']}] {hit['snippet']}")
        return "\n".join(lines)
