from datetime import datetime

from pydantic import BaseModel, Field


class KnowledgeDocumentResource(BaseModel):
    id: str
    filename: str
    content_type: str
    character_count: int
    chunk_count: int
    created_at: datetime


class KnowledgeSearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=2_000)
    top_k: int = Field(default=5, ge=1, le=12)


class SourceCitation(BaseModel):
    document_id: str
    filename: str
    chunk_index: int
    excerpt: str
    score: float


class KnowledgeSearchResponse(BaseModel):
    sources: list[SourceCitation]


class ChatTurn(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(min_length=1, max_length=4_000)


class AssistantChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4_000)
    history: list[ChatTurn] = Field(default_factory=list, max_length=20)


class AssistantChatResponse(BaseModel):
    answer: str
    sources: list[SourceCitation]
    mode: str
