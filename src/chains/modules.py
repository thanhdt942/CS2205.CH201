from langchain.tools import tool
from langchain.chat_models import init_chat_model
from pydantic import BaseModel, Field
from typing import Literal
from langgraph.graph import StateGraph, START, END
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from src.config import cfg
from langchain_core.prompts import ChatPromptTemplate, FewShotChatMessagePromptTemplate

llm_params = {
    "model": cfg.llm.name,
    "temperature": cfg.llm.temperature,
}

llm = ChatOpenAI(**llm_params)


# --- SCHEMAS (Định nghĩa Output) ---

class RetrieveToken(BaseModel):
    decision: Literal["yes", "no", "continue"] = Field(
        ..., description="'yes' to retrieve, 'no' if general chat, 'continue' if using history."
    )

class IsRelToken(BaseModel):
    score: Literal["relevant", "irrelevant"] = Field(
        ..., description="Is the document relevant to the user question?"
    )

class IsSupToken(BaseModel):
    score: Literal["fully supported", "partially supported", "no support"] = Field(
        ..., description="Check if generation is supported by facts."
    )

class IsUseToken(BaseModel):
    score: int = Field(
        ..., description="Score 1-5. 5 is best.", ge=1, le=5
    )

# --- CHAINS ---

# 1. Router (Retrieve Token)
structured_retrieve = llm.with_structured_output(RetrieveToken)

examples = [
    {"input": "Hi there", "output": "no"},
    {"input": "Viết cho tôi một đoạn code Python tính tổng", "output": "no"},
    {"input": "Self-RAG là gì?", "output": "yes"},
    {"input": "Kiến trúc của AgentIAD hoạt động như thế nào?", "output": "yes"},
    {"input": "Giải thích cơ chế Attention trong Transformer", "output": "no"}, # Kiến thức chung phổ biến
    {"input": "So sánh Llama-2 và Llama-3", "output": "yes"}, # Cần thông tin cụ thể (spec)
]

# 2. Tạo template cho ví dụ
example_prompt = ChatPromptTemplate.from_messages(
    [
        ("human", "{input}"),
        ("ai", "{output}"),
    ]
)

# 3. Tạo Few-shot prompt
few_shot_prompt = FewShotChatMessagePromptTemplate(
    example_prompt=example_prompt,
    examples=examples,
)

# 4. Ghép vào prompt chính
retrieve_prompt = ChatPromptTemplate.from_messages([
    ("system", 
     """You are a retrieval router. Determine if the user's query requires looking up external information.
     
     - Use 'no' for general conversation, basic coding, or universal facts.
     - Use 'yes' for specific entities, paper titles, acronyms (like AgentIAD), or domain-specific queries.
     """),
    few_shot_prompt, # Chèn ví dụ vào đây
    ("human", "{question}")
])

retrieve_router = retrieve_prompt | structured_retrieve

# 2. Retrieval Grader (ISREL Token) - Tối ưu cho legal domain
structured_isrel = llm.with_structured_output(IsRelToken)
isrel_prompt = ChatPromptTemplate.from_messages([
    ("system", 
     """Bạn là chuyên gia đánh giá độ liên quan của điều luật. 
     Đánh giá xem điều luật có liên quan đến câu hỏi pháp lý không.
     - 'relevant': Điều luật có liên quan trực tiếp hoặc gián tiếp đến câu hỏi
     - 'irrelevant': Điều luật không liên quan đến câu hỏi
     
     Hãy đánh giá một cách cẩn thận, vì điều luật có thể liên quan ngay cả khi không đề cập trực tiếp đến chủ đề."""),
    ("human", "Câu hỏi: {question} \n\nĐiều luật: {document}\n\nĐánh giá độ liên quan:"),
])
retrieval_grader = isrel_prompt | structured_isrel

# 3. Hallucination Grader (ISSUP Token)
structured_issup = llm.with_structured_output(IsSupToken)
issup_prompt = ChatPromptTemplate.from_messages([
    ("system", "Assess if generation is supported by facts (fully/partially/no support)."),
    ("human", "Question: {question} \n Facts: {documents} \n Generation: {generation}"),
])
hallucination_grader = issup_prompt | structured_issup

# 4. Answer Grader (ISUSE Token)
structured_isuse = llm.with_structured_output(IsUseToken)
isuse_prompt = ChatPromptTemplate.from_messages([
    ("system", "Rate utility 1-5."),
    ("human", "Question: {question} \n Answer: {generation}"),
])
answer_grader = isuse_prompt | structured_isuse

# 5. HyDE Generator (Hypothetical Document Embeddings)
hyde_prompt = ChatPromptTemplate.from_messages([
    ("system", 
     """Bạn là một chuyên gia pháp lý. Nhiệm vụ của bạn là tạo ra một đoạn văn bản giả định (hypothetical document) 
     chứa câu trả lời lý tưởng cho câu hỏi pháp lý được đưa ra.
     
     Đoạn văn bản này sẽ được sử dụng để tìm kiếm các điều luật thực tế trong cơ sở dữ liệu pháp lý.
     Hãy viết một đoạn văn bản ngắn gọn, chứa các thuật ngữ pháp lý và nội dung liên quan đến câu hỏi.
     Viết bằng tiếng Việt."""),
    ("human", "Câu hỏi: {question}"),
])
hyde_generator = hyde_prompt | llm

# 6. Legal Generator (Sinh câu trả lời với Chain-of-Thought reasoning)
legal_gen_prompt = ChatPromptTemplate.from_messages([
    ("system", 
     """Bạn là một chuyên gia tư vấn pháp lý chuyên nghiệp. Nhiệm vụ của bạn là phân tích tài liệu pháp lý 
     và trả lời câu hỏi dựa trên các điều luật liên quan.
     
     QUY TRÌNH SUY LUẬN (Chain-of-Thought):
     1. Đọc và hiểu nội dung tài liệu (nếu có)
     2. Xác định các điều khoản/quy định trong tài liệu liên quan đến câu hỏi
     3. Đối chiếu với các điều luật được cung cấp
     4. Phát hiện các điểm mâu thuẫn (nếu có) giữa tài liệu và quy định pháp luật
     5. Đưa ra kết luận và giải thích rõ ràng
     
     YÊU CẦU:
     - Sử dụng lập luận logic, rõ ràng
     - Trích dẫn cụ thể các điều luật được sử dụng
     - Nếu phát hiện mâu thuẫn, chỉ ra rõ ràng điểm nào mâu thuẫn và với điều luật nào
     - Trả lời bằng tiếng Việt, chuyên nghiệp
     - Nếu không có đủ thông tin, hãy nói rõ"""),
    ("human", 
     """Câu hỏi: {question}
     
     {context}
     
     Hãy phân tích và trả lời theo quy trình suy luận trên."""),
])
generator = legal_gen_prompt | llm

# 7. Query Rewriter (Tối ưu cho legal domain)
rewrite_prompt = ChatPromptTemplate.from_messages([
    ("system", 
     """Bạn là chuyên gia tìm kiếm pháp lý. Nhiệm vụ của bạn là viết lại câu hỏi để tối ưu cho việc tìm kiếm 
     các điều luật liên quan trong cơ sở dữ liệu pháp lý.
     
     Hãy:
     - Mở rộng các thuật ngữ pháp lý
     - Thêm các từ khóa liên quan
     - Làm rõ ý định tìm kiếm
     - Giữ nguyên ý nghĩa gốc
     - Viết bằng tiếng Việt"""),
    ("human", "Câu hỏi gốc: {question}\n\nViết lại câu hỏi để tối ưu tìm kiếm:"),
])
question_rewriter = rewrite_prompt | llm