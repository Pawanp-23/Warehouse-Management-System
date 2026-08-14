import hashlib
import math
import re
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from pypdf import PdfReader
from pymongo.errors import DuplicateKeyError
from ftfy import fix_text

from core.database import get_database

WORD_PATTERN = re.compile(r"[a-z0-9][a-z0-9_-]{1,}", re.IGNORECASE)
ALLOWED_SUFFIXES = {".pdf", ".txt", ".md"}


def _terms(text: str) -> list[str]:
    return sorted(set(match.group(0).lower() for match in WORD_PATTERN.finditer(text)))


def _extract_text(filename: str, content: bytes) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise ValueError("Only PDF, TXT, and Markdown documents are supported")
    if suffix == ".pdf":
        try:
            text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(content)).pages)
        except Exception as error:
            raise ValueError("The PDF could not be read") from error
    else:
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError as error:
            raise ValueError("Text documents must use UTF-8 encoding") from error
    text = fix_text(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if len(text) < 40:
        raise ValueError("The document contains too little readable text")
    return text


def _chunk(text: str, size: int = 180, overlap: int = 35) -> list[str]:
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        chunks.append(" ".join(words[start:start + size]))
        if start + size >= len(words):
            break
        start += size - overlap
    return chunks


async def ingest_document(organization_id: str, actor_id: str, filename: str, content_type: str, content: bytes) -> dict:
    safe_filename = Path(filename).name[:180]
    text = _extract_text(safe_filename, content)
    chunks = _chunk(text)
    now = datetime.now(timezone.utc)
    document = {
        "_id": str(uuid4()), "organization_id": organization_id, "filename": safe_filename,
        "content_type": content_type, "sha256": hashlib.sha256(content).hexdigest(),
        "character_count": len(text), "chunk_count": len(chunks), "created_by": actor_id,
        "created_at": now, "updated_at": now,
    }
    db = get_database()
    try:
        await db.knowledge_documents.insert_one(document)
    except DuplicateKeyError as error:
        raise ValueError("This document is already in the tenant knowledge base") from error
    try:
        await db.knowledge_chunks.insert_many([
            {"_id": str(uuid4()), "organization_id": organization_id, "document_id": document["_id"],
             "filename": safe_filename, "chunk_index": index, "text": chunk, "terms": _terms(chunk),
             "created_at": now}
            for index, chunk in enumerate(chunks)
        ])
    except Exception:
        await db.knowledge_documents.delete_one({"_id": document["_id"], "organization_id": organization_id})
        raise
    return document


async def list_documents(organization_id: str) -> list[dict]:
    return await get_database().knowledge_documents.find({"organization_id": organization_id}).sort("created_at", -1).to_list(length=200)


async def delete_document(organization_id: str, document_id: str) -> bool:
    db = get_database()
    document = await db.knowledge_documents.find_one({"_id": document_id, "organization_id": organization_id}, {"_id": 1})
    if not document:
        return False
    await db.knowledge_chunks.delete_many({"organization_id": organization_id, "document_id": document_id})
    await db.knowledge_documents.delete_one({"organization_id": organization_id, "_id": document_id})
    return True


async def search(organization_id: str, query: str, top_k: int) -> list[dict]:
    query_terms = _terms(query)
    if not query_terms:
        return []
    candidates = await get_database().knowledge_chunks.find(
        {"organization_id": organization_id, "terms": {"$in": query_terms}}
    ).limit(250).to_list(length=250)
    phrase = query.lower().strip()
    ranked = []
    for chunk in candidates:
        text_lower = chunk["text"].lower()
        matches = sum(1 + math.log1p(text_lower.count(term)) for term in query_terms if term in text_lower)
        coverage = sum(term in text_lower for term in query_terms) / len(query_terms)
        score = matches + coverage * 4 + (5 if phrase in text_lower else 0)
        ranked.append({**chunk, "score": round(score, 3)})
    ranked.sort(key=lambda item: item["score"], reverse=True)
    return ranked[:top_k]
