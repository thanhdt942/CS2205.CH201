from dataclasses import dataclass
from typing import Optional

@dataclass
class ServerConfig:
    host: str
    port: int
    reload: bool

@dataclass
class LLMConfig:
    name: str
    temperature: float  
    deployment: str
    base_url: Optional[str] = None 
    api_key: Optional[str] = None

@dataclass
class QdrantConfig:
    collection_name: str
    host: str
    port: int
    api_key: Optional[str] = None

@dataclass
class SearchConfig:
    max_results: int

@dataclass
class DeepSeekConfig:
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: str = "deepseek-chat"

@dataclass
class AppConfig:
    project_name: str
    chunk_size: int
    chunk_overlap: int
    
    server: ServerConfig
    llm: LLMConfig
    qdrant: QdrantConfig
    search: SearchConfig
    deepseek: DeepSeekConfig