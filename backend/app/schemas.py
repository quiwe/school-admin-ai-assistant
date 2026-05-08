from datetime import datetime

from pydantic import BaseModel, Field


class Reference(BaseModel):
    title: str
    content: str


class GenerateReplyRequest(BaseModel):
    question: str = Field(..., min_length=1)
    style: str = "normal"


class GenerateReplyResponse(BaseModel):
    answer: str
    category: str
    confidence: float
    need_human_review: bool
    references: list[Reference]


class RewriteReplyRequest(BaseModel):
    question: str
    answer: str
    style: str = "formal"


class KnowledgeFileRead(BaseModel):
    id: int
    filename: str
    category: str
    upload_time: datetime
    parsed_text: str
    chunk_count: int
    status: str

    class Config:
        from_attributes = True


class KnowledgeFileUpdate(BaseModel):
    category: str | None = None


class FAQCreate(BaseModel):
    question: str
    answer: str
    category: str = "其他"
    allow_auto_reply: bool = True


class FAQUpdate(BaseModel):
    question: str | None = None
    answer: str | None = None
    category: str | None = None
    allow_auto_reply: bool | None = None


class FAQRead(BaseModel):
    id: int
    question: str
    answer: str
    category: str
    allow_auto_reply: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class HistoryCreate(BaseModel):
    student_question: str
    ai_answer: str
    final_answer: str
    category: str = "其他"
    confidence: float = 0.0
    need_human_review: bool = False


class HistoryRead(BaseModel):
    id: int
    student_question: str
    ai_answer: str
    final_answer: str
    category: str
    confidence: float
    need_human_review: bool
    created_at: datetime

    class Config:
        from_attributes = True


class AIProviderConfigRead(BaseModel):
    id: str
    label: str
    provider_type: str
    base_url: str
    model: str
    api_key_configured: bool
    requires_api_key: bool
    docs_url: str | None = None
    note: str | None = None


class AIProviderConfigUpdate(BaseModel):
    id: str
    api_key: str | None = None
    base_url: str | None = None
    model: str | None = None


class AISettingsRead(BaseModel):
    ai_provider: str
    providers: list[AIProviderConfigRead]


class AISettingsUpdate(BaseModel):
    ai_provider: str
    providers: list[AIProviderConfigUpdate] = []


class AIModelListRequest(BaseModel):
    provider_id: str
    api_key: str | None = None
    base_url: str | None = None


class AIModelListResponse(BaseModel):
    models: list[str]
    source: str
