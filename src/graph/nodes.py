from langchain_core.documents import Document
from src.components.vectordb import get_retriever
from src.components.ocr import extract_text_with_deepseek
from src.state import GraphState
from src.config import cfg
from src.chains.modules import (
    retrieval_grader, 
    generator, 
    question_rewriter,
    hyde_generator
)
from src.logger import logger

def ocr_node(state: GraphState):
    """Node xử lý OCR từ ảnh đầu vào"""
    logger.info("---NODE: OCR PROCESSING---")
    image_base64 = state.get("image_base64")
    document_context = state.get("document_context")
    
    # Nếu đã có document_context thì không cần OCR lại
    if document_context:
        logger.info(" -> Document context đã có sẵn, bỏ qua OCR")
        return {"document_context": document_context}
    
    # Nếu có ảnh thì thực hiện OCR
    if image_base64:
        try:
            logger.info(" -> Đang trích xuất văn bản từ ảnh...")
            extracted_text = extract_text_with_deepseek(image_base64=image_base64)
            logger.success(f" -> OCR thành công: {len(extracted_text)} ký tự")
            return {"document_context": extracted_text}
        except Exception as e:
            logger.error(f" -> Lỗi OCR: {e}")
            return {"document_context": ""}
    
    # Không có ảnh và không có context
    logger.warning(" -> Không có ảnh hoặc document context")
    return {"document_context": ""}


def retrieve_node(state: GraphState):
    """Node truy xuất điều luật với hỗ trợ HyDE"""
    logger.info("---NODE: RETRIEVE LEGAL PROVISIONS---")
    question = state["question"]
    document_context = state.get("document_context", "")
    
    retriever = get_retriever()
    
    # Kết hợp câu hỏi và document context để tìm kiếm tốt hơn
    if document_context:
        # Sử dụng cả câu hỏi và context để tạo query
        enhanced_query = f"{question}\n\nNgữ cảnh từ tài liệu:\n{document_context[:500]}"  # Giới hạn để tránh quá dài
        logger.info(" -> Sử dụng enhanced query với document context")
    else:
        enhanced_query = question
    
    # Áp dụng HyDE: Tạo hypothetical document từ câu hỏi
    try:
        logger.info(" -> Tạo hypothetical document (HyDE)...")
        hypothetical_doc = hyde_generator.invoke({"question": enhanced_query})
        hyde_query = hypothetical_doc.content
        logger.info(f" -> HyDE query: {hyde_query[:100]}...")
        
        # Sử dụng HyDE query để retrieve
        docs = retriever.invoke(hyde_query)
        logger.info(f" -> Tìm thấy {len(docs)} điều luật với HyDE.")
    except Exception as e:
        logger.warning(f" -> HyDE thất bại, sử dụng query gốc: {e}")
        # Fallback về query gốc nếu HyDE thất bại
        docs = retriever.invoke(enhanced_query)
        logger.info(f" -> Tìm thấy {len(docs)} điều luật.")
    
    return {"documents": docs, "question": question}

def grade_documents_node(state: GraphState):
    logger.info("---NODE: GRADE DOCS (ISREL)---")
    question = state["question"]
    documents = state["documents"]
    no_relevant_count = state.get("no_relevant_count", 0)
    
    filtered_docs = []
    for d in documents:
        score_obj = retrieval_grader.invoke({"question": question, "document": d.page_content})
        if score_obj.score == "relevant":
            logger.success(f" -> Keep doc: {d.page_content[:30]}...")
            filtered_docs.append(d)
        else:
            logger.warning(f" -> Filter out: {d.page_content[:30]}...")

    if not filtered_docs:
        no_relevant_count += 1
        logger.warning(f" -> No relevant docs found. Count: {no_relevant_count}/5")
    else:
        no_relevant_count = 0
            
    return {"documents": filtered_docs, "question": question, "no_relevant_count": no_relevant_count}

def generate_node(state: GraphState):
    """Node sinh câu trả lời với legal reasoning và Chain-of-Thought"""
    logger.info("---NODE: GENERATE WITH LEGAL REASONING---")
    question = state["question"]
    documents = state.get("documents", [])
    document_context = state.get("document_context", "")
    
    # Chuẩn bị context từ điều luật
    legal_provisions = ""
    citations = []
    if documents:
        legal_provisions = "\n\n".join([
            f"Điều luật {i+1}:\n{d.page_content}" 
            for i, d in enumerate(documents)
        ])
        # Lưu citations để trả về cho user
        citations = [
            {
                "content": d.page_content,
                "source": d.metadata.get("source", "Nguồn không xác định"),
                "relevance_score": d.metadata.get("score", None)
            }
            for d in documents
        ]
        logger.info(f" -> Sử dụng {len(documents)} điều luật")
    else:
        logger.warning(" -> Không có điều luật nào được tìm thấy")
    
    # Kết hợp document context và legal provisions
    full_context = ""
    if document_context:
        full_context += f"NỘI DUNG TÀI LIỆU:\n{document_context}\n\n"
    if legal_provisions:
        full_context += f"CÁC ĐIỀU LUẬT LIÊN QUAN:\n{legal_provisions}\n\n"
    
    # Sinh câu trả lời với legal reasoning
    generation = generator.invoke({
        "context": full_context, 
        "question": question,
        "document_context": document_context
    })
    
    return {
        "generation": generation.content,
        "citations": citations
    }

def transform_query_node(state: GraphState):
    logger.info("---NODE: TRANSFORM QUERY---")
    question = state["question"]
    better_question = question_rewriter.invoke({"question": question})
    return {"question": better_question.content}

def detect_contradictions_node(state: GraphState):
    """Node phát hiện mâu thuẫn giữa tài liệu và quy định pháp luật"""
    logger.info("---NODE: DETECT CONTRADICTIONS---")
    document_context = state.get("document_context", "")
    documents = state.get("documents", [])
    generation = state.get("generation", "")
    
    if not document_context or not documents:
        logger.info(" -> Không đủ thông tin để phát hiện mâu thuẫn")
        return {"contradictions": []}
    
    # Sử dụng LLM để phát hiện mâu thuẫn
    from src.chains.modules import llm
    from langchain_core.prompts import ChatPromptTemplate
    
    contradiction_prompt = ChatPromptTemplate.from_messages([
        ("system", 
         """Bạn là chuyên gia pháp lý. Nhiệm vụ của bạn là phát hiện các điểm mâu thuẫn 
         giữa nội dung trong tài liệu và quy định của pháp luật.
         
         Hãy phân tích và liệt kê các điểm mâu thuẫn (nếu có). Mỗi điểm mâu thuẫn cần:
         - Mô tả rõ điểm nào trong tài liệu mâu thuẫn
         - Chỉ ra điều luật nào quy định khác
         - Giải thích ngắn gọn về mâu thuẫn
         
         Nếu không có mâu thuẫn, trả về danh sách rỗng.
         Trả về dưới dạng danh sách các chuỗi, mỗi chuỗi là một điểm mâu thuẫn."""),
        ("human", 
         """NỘI DUNG TÀI LIỆU:
         {document_context}
         
         CÁC ĐIỀU LUẬT:
         {legal_provisions}
         
         Hãy phát hiện các điểm mâu thuẫn:""")
    ])
    
    legal_provisions = "\n\n".join([d.page_content for d in documents])
    
    try:
        chain = contradiction_prompt | llm
        result = chain.invoke({
            "document_context": document_context[:2000],  # Giới hạn độ dài
            "legal_provisions": legal_provisions[:2000]
        })
        
        # Parse kết quả thành danh sách
        contradictions_text = result.content
        # Đơn giản hóa: tách theo dòng hoặc số thứ tự
        contradictions = [
            line.strip() 
            for line in contradictions_text.split('\n') 
            if line.strip() and not line.strip().startswith('#')
        ]
        
        if contradictions:
            logger.warning(f" -> Phát hiện {len(contradictions)} điểm mâu thuẫn")
        else:
            logger.info(" -> Không phát hiện mâu thuẫn")
            
        return {"contradictions": contradictions}
    except Exception as e:
        logger.error(f" -> Lỗi khi phát hiện mâu thuẫn: {e}")
        return {"contradictions": []}


def prepare_for_final_grade_node(state: GraphState):
    logger.info("---NODE: PREPARE FOR FINAL GRADE---")
    return {
        "question": state["question"],
        "generation": state["generation"],
        "documents": state.get("documents", []),
        "citations": state.get("citations", []),
        "contradictions": state.get("contradictions", [])
    }

def no_answer_node(state: GraphState):
    logger.stop("---NODE: NO ANSWER (Too many failed retrieves)---")
    return {"generation": "Xin lỗi, tôi không tìm thấy thông tin liên quan để trả lời câu hỏi của bạn."}