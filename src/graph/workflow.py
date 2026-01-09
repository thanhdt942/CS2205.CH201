from langgraph.graph import END, StateGraph
from src.state import GraphState
from src.chains.modules import retrieve_router, hallucination_grader, answer_grader
from src.graph.nodes import (
    ocr_node, prepare_for_final_grade_node, retrieve_node, grade_documents_node, 
    generate_node, transform_query_node, no_answer_node, detect_contradictions_node
)
from src.logger import logger

# --- CONDITIONAL LOGIC ---

def route_after_ocr(state):
    """
    Router: Sau khi OCR, quyết định có cần retrieve không.
    Luôn retrieve nếu có document context hoặc câu hỏi liên quan đến pháp lý.
    """
    logger.info("---DECISION: AFTER OCR - CHECK IF RETRIEVE NEEDED---")
    document_context = state.get("document_context", "")
    question = state.get("question", "")
    
    # Nếu có document context hoặc câu hỏi liên quan đến pháp lý, luôn retrieve
    if document_context or any(keyword in question.lower() for keyword in 
                                ["luật", "điều", "quy định", "pháp lý", "hợp đồng", "văn bản"]):
        return "retrieve"
    
    # Kiểm tra bằng retrieve router
    res = retrieve_router.invoke({"question": question})
    if res.decision == "yes":
        return "retrieve"
    return "generate"

def decide_to_generate(state):
    """
    Decide after grading documents:
    - If have relevant docs -> generate
    - If no relevant docs -> transform query
    - If no relevant docs for 5 consecutive retrieves -> no_answer
    """
    logger.info("---DECISION: AFTER GRADE DOCS---")
    no_relevant_count = state.get("no_relevant_count", 0)
    documents = state.get("documents", [])

    if documents:
        return "generate"
    else:
        if no_relevant_count >= 5:
            logger.stop(" -> No relevant docs for 5 consecutive retrieves. Going to no_answer.")
            return "no_answer"
        else:
            return "transform_query"
        
def grade_generation_v_documents(state):
    """
    Decide after Generate:
    - If not supported by facts -> generate again
    - If supported -> prepare for final grade
    """
    logger.info("---DECISION: GRADE GENERATION AND DOCS---")
    question = state["question"]
    generation = state["generation"]
    documents = state.get("documents", [])
    
    # Check hallucination
    hallu_score = hallucination_grader.invoke({
        "question": question,
        "generation": generation, 
        "documents": "\n\n".join([d.page_content for d in documents])
    })
    if hallu_score.score in ["fully supported", "partially supported"]:
        logger.info(" -> Generation is supported by facts.")
        return "supported"
    else:
        logger.warning(" -> Generation not supported by facts. Regenerating.")
        return "not supported"      


def grade_generation_v_question(state):
    """
    Decide after Prepare for Final Grade:
    - If useful (score >=4) -> END
    - If not useful -> transform query
    """
    logger.info("---DECISION: GRADE GENERATION AND QUESTION---")
    generation = state["generation"]
    question = state["question"]
    
    # Check usefulness
    useful_score = answer_grader.invoke({"generation": generation, "question": question})
    if useful_score.score >= 4:
        logger.success(" -> Generation is useful.")
        return "useful"
    else:
        logger.error(" -> Generation is not useful. Rewriting question.")
        return "not useful"
    
# --- GRAPH BUILD ---

workflow = StateGraph(GraphState)

# 1. Add Nodes to Graph
workflow.add_node("ocr", ocr_node)  # OCR processing
workflow.add_node("retrieve", retrieve_node)
workflow.add_node("grade_documents", grade_documents_node)
workflow.add_node("generate", generate_node)
workflow.add_node("detect_contradictions", detect_contradictions_node)  # Phát hiện mâu thuẫn
workflow.add_node("prepare_for_final_grade", prepare_for_final_grade_node)
workflow.add_node("transform_query", transform_query_node)
workflow.add_node("no_answer", no_answer_node)

# 2. Entry Point: Luôn bắt đầu với OCR
workflow.set_entry_point("ocr")

# 3. After OCR -> decide retrieve or generate
workflow.add_conditional_edges(
    "ocr",
    route_after_ocr,
    {
        "retrieve": "retrieve",
        "generate": "generate"
    }
)

# 4. Normal Edges
workflow.add_edge("retrieve", "grade_documents")
workflow.add_edge("transform_query", "retrieve")

# 4. Conditional Edges

# From Grade Docs -> where? 
workflow.add_conditional_edges(
    "grade_documents",
    decide_to_generate,
    {
        "transform_query": "transform_query",
        "generate": "generate",
        "no_answer": "no_answer"
    }
)

# From no_answer -> END
workflow.add_edge("no_answer", END)

# From Generate -> detect contradictions -> check support
workflow.add_edge("generate", "detect_contradictions")

# From Detect Contradictions -> check if supported
workflow.add_conditional_edges(
    "detect_contradictions",
    grade_generation_v_documents, 
    {
        "not supported": "generate",       
        "supported": "prepare_for_final_grade",   
    }
)

# From Prepare for Final Grade -> where?
workflow.add_conditional_edges(
    "prepare_for_final_grade",
    grade_generation_v_question, 
    {
        "not useful": "transform_query",       
        "useful": END,   
    }
)


# Compile
app_graph = workflow.compile()