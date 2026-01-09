import os
import glob
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_qdrant import QdrantVectorStore
from src.components.vectordb import get_embeddings
from src.config import cfg
from src.logger import logger

def clean_text(text: str) -> str:
    """Clean text by removing invalid Unicode characters"""
    # Remove surrogate characters and invalid characters
    return text.encode('utf-8', 'ignore').decode('utf-8', 'ignore')

def ingest_data():
    logger.info("Starting data ingestion process...")
    
    # 1. Load PDF files from data/ directory
    pdf_files = glob.glob("data/*.pdf")
    if not pdf_files:
        logger.error("No PDF files found in data/ directory")
        return

    documents = []
    logger.info(f"Found {len(pdf_files)} PDF files")
    
    for file_path in pdf_files:
        logger.info(f"Reading file: {file_path}")
        loader = PyPDFLoader(file_path)
        docs = loader.load()
        # Clean text in each document
        for doc in docs:
            doc.page_content = clean_text(doc.page_content)
        documents.extend(docs)

    # 2. Text chunking
    logger.info("Splitting documents into chunks...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=cfg.chunk_size,    # Example: 500
        chunk_overlap=cfg.chunk_overlap, # Example: 50
        separators=["\n\n", "\n", " ", ""]
    )
    splits = text_splitter.split_documents(documents)
    logger.info(f"Created {len(splits)} chunks")

    # 3. Embedding and indexing into Qdrant
    logger.info(f"Uploading to Qdrant collection: {cfg.qdrant.collection_name}...")
    
    url = f"http://{cfg.qdrant.host}:{cfg.qdrant.port}"
    
    # The from_documents function will automatically embed and upsert
    QdrantVectorStore.from_documents(
        documents=splits,
        embedding=get_embeddings(),
        url=url,
        collection_name=cfg.qdrant.collection_name,
        api_key=cfg.qdrant.api_key,
        force_recreate=True # Note: True will delete old data and recreate from scratch
    )
    
    logger.success("Completed! Data is ready")

if __name__ == "__main__":
    ingest_data()