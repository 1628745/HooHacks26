from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_chat import router as chat_router
from app.api.routes_health import router as health_router
from app.api.routes_pipeline import router as pipeline_router
from app.core.config import settings


app = FastAPI(title="LLM Pipeline Optimizer API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(pipeline_router, prefix="/api/pipeline", tags=["pipeline"])
app.include_router(chat_router, prefix="/api/pipeline", tags=["chat"])
