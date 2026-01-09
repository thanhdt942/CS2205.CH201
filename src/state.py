from typing import List, TypedDict, Optional
from langchain_core.documents import Document

class GraphState(TypedDict):
    question: str
    generation: str
    documents: List[Document]
    retrieve: str # YES/NO
    loop_step: int # Step count for loops
    no_relevant_count: int # Count retrieves with no relevant docs
    document_context: Optional[str]  # Nội dung tài liệu đã OCR (Markdown format)
    citations: List[dict]  # Danh sách các điều luật được trích dẫn
    contradictions: Optional[List[str]]  # Các điểm mâu thuẫn phát hiện được