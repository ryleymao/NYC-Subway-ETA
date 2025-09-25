from fastapi import FastAPI
from .service.routes import router as api_router

app = FastAPI(title="NYC Subway Live ETA", version="0.1.0")

@app.get("/health")
def health():
    return {"ok": True}

app.include_router(api_router)
