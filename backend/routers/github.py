# backend/routers/github.py
from fastapi import APIRouter

router = APIRouter()

@router.post("/github")
async def github_webhook():
    return {"status": "received"}