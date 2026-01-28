# app/main.py
from fastapi import FastAPI

from app.routes.auth_routes import router as auth_router
from app.routes.toy_routes import router as toy_router
from app.routes.parent_routes import router as parent_router
from app.routes.admin_routes import router as admin_router

# --------------------------------------------------
# App
# --------------------------------------------------
app = FastAPI(
    title="Toy Agent Backend",
    version="1.0.0",
)

# --------------------------------------------------
# Routers
# --------------------------------------------------

app.include_router(auth_router)
app.include_router(toy_router)
app.include_router(parent_router)
app.include_router(admin_router)

# --------------------------------------------------
# Health
# --------------------------------------------------
@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
