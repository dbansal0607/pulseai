# backend/routers/dashboard.py
from fastapi import APIRouter

router = APIRouter()

@router.get("/status")
async def status():
    return {"status": "PulseAI running"}