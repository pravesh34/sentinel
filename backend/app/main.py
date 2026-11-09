import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.websockets import WebSocket, WebSocketDisconnect
from .config import settings
from .database.session import init_db, engine
from .observability.logging import setup_logging, new_correlation_id, correlation_id_ctx
from .api.v1.routes import router as v1_router

setup_logging()
app = FastAPI(title="SENTINEL API", version="0.1.0", docs_url="/docs", openapi_url="/openapi.json")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.middleware("http")
async def correlation_middleware(request: Request, call_next):
    cid = request.headers.get("x-correlation-id") or new_correlation_id()
    correlation_id_ctx.set(cid)
    response = await call_next(request)
    response.headers["x-correlation-id"] = cid
    return response

@app.on_event("startup")
def startup():
    init_db()
    # Seed pricing
    try:
        from .models.entities import ProviderPricing
        from .database.session import SessionLocal
        from .cost.pricing import PRICING, PRICING_VERSION
        db = SessionLocal()
        for (prov, model), (inp, out) in PRICING.items():
            if not db.query(ProviderPricing).filter_by(provider=prov, model=model, version=PRICING_VERSION).first():
                db.add(ProviderPricing(provider=prov, model=model, version=PRICING_VERSION, input_per_1k=inp, output_per_1k=out))
        db.commit(); db.close()
    except Exception:
        pass

@app.get("/health")
def health(): return {"status": "ok", "service": "sentinel-backend"}

@app.get("/health/ready")
def ready():
    try:
        with engine.connect() as conn:
            conn.exec_driver_sql("SELECT 1")
        return {"status": "ready", "db": "ok"}
    except Exception as e:
        return {"status": "degraded", "db": str(e)}

@app.websocket("/ws/executions/{eid}")
async def ws_execution(websocket: WebSocket, eid: str):
    await websocket.accept()
    try:
        while True:
            await websocket.send_json({"execution_id": eid, "status": "running", "note": "poll /trace for detail"})
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass

app.include_router(v1_router, prefix="/api/v1")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
