from fastapi import FastAPI
from src.config import cfg
from src.server.routes import router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title=cfg.project_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")


@app.get("/")
def read_root():
    return {
        "message": f"Welcome to {cfg.project_name}",
        "llm_model": cfg.llm.name,
        "environment": "Running on port " + str(cfg.server.port)
    }

@app.get("/health")
def health_check():
    return {"status": "okkk"}