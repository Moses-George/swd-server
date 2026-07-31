from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .core.config import settings
from .routers import (
    auth,
    networks,
    nodes,
    pipes,
    telemetry,
    scenarios,
    energy,
    leaks,
    forecast,
    maintenance,
    quality,
    carbon,
    ws,
    topology
)

app = FastAPI(title="Aquaflow API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in [
    auth.router,
    networks.router,
    nodes.router,
    pipes.router,
    telemetry.router,
    scenarios.router,
    energy.router,
    leaks.router,
    forecast.router,
    maintenance.router,
    quality.router,
    carbon.router,
    ws.router,
    topology.router
]:
    app.include_router(r)


@app.get("/health")
async def health():
    return {"status": "ok"}

# This is important for Vercel
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)