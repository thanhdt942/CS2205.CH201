from pydantic import BaseModel
from typing import Optional, List


class ChatRequest(BaseModel):
    question: str
    image_base64: Optional[str] = None  # Base64 encoded image
    document_context: Optional[str] = None  # Pre-extracted document text (Markdown)


class LegalCitation(BaseModel):
    """Trích dẫn điều luật được sử dụng"""
    content: str  # Nội dung điều luật
    source: Optional[str] = None  # Nguồn (tên văn bản, số điều)
    relevance_score: Optional[float] = None  # Điểm độ liên quan


class ChatResponse(BaseModel):
    answer: str
    citations: List[LegalCitation] = []  # Danh sách các điều luật được trích dẫn
    document_context: Optional[str] = None  # Nội dung tài liệu đã OCR (nếu có)
    contradictions: Optional[List[str]] = None  # Danh sách các điểm mâu thuẫn phát hiện được