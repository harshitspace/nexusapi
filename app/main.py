from fastapi import FastAPI, HTTPException, status
from app.db.session import engine
from sqlalchemy import text
from app.api.routes import auth, credits, users

app = FastAPI(title="NexusAPI")

app.include_router(auth.router, prefix="/api/v1")
app.include_router(credits.router, prefix="/api/v1")

app.include_router(users.router)

@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        
        return {"status": "ok", "database": "reachable"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "error", "database": "unreachable"}
        )