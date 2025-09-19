from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from prometheus_client import generate_latest

app = FastAPI(title="NYC Subway ETA API", version="0.1.0")

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/metrics", response_class=PlainTextResponse)
def metrics():
    return PlainTextResponse(generate_latest().decode("utf-8"))
