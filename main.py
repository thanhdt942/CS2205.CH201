import uvicorn
from src.config import cfg 

if __name__ == "__main__":
    print(f"🚀 Starting server [{cfg.project_name}]...")
    print(f"🔗 Listening on http://{cfg.server.host}:{cfg.server.port}")

    uvicorn.run(
        "src.server.app:app",  # Path to the FastAPI app
        host=cfg.server.host,  
        port=cfg.server.port,  
        reload=cfg.server.reload
    )