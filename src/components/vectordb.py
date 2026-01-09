# src/components/vectordb.py
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from src.config import cfg

def get_embeddings():
    """Khởi tạo Embedding Model (OpenAI text-embedding-3-small)"""
    return OpenAIEmbeddings(
        model="text-embedding-3-large",
        api_key=cfg.llm.api_key
    )

def get_vectorstore():
    """
    Kết nối tới Vector DB (Qdrant).
    Nếu chưa có collection, nó sẽ tự tạo (logic của langchain-qdrant).
    """
    embeddings = get_embeddings()
    
    # Kết nối Qdrant (Local hoặc Cloud)
    # Nếu chạy Docker: url="http://localhost:6333"
    # Nếu chạy In-Memory (test): location=":memory:"
    
    url = f"http://{cfg.qdrant.host}:{cfg.qdrant.port}"
    
    vectorstore = QdrantVectorStore.from_existing_collection(
        embedding=embeddings,
        collection_name=cfg.qdrant.collection_name,
        url=url,
        api_key=cfg.qdrant.api_key,
        prefer_grpc=True
    )
    return vectorstore

def get_retriever():
    """Trả về retriever object để dùng trong LangChain"""
    vectorstore = get_vectorstore()
    return vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": cfg.search.max_results}
    )