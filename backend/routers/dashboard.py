# backend/routers/dashboard.py
from fastapi import APIRouter
from agents.nexus import run_swarm

router = APIRouter()

@router.get("/status")
async def status():
    return {"status": "PulseAI running"}

@router.post("/test-swarm")
async def test_swarm():
    """
    Test endpoint — triggers the swarm with a fake PR event.
    Use this to verify the full agent pipeline works.
    """
    result = await run_swarm(
        event_type="pr_opened",
        event_payload={
            "pr_number": 42,
            "title": "Fix payment service auth bug",
            "files_changed": ["auth.py", "payment.py"],
            "author": "dhruv"
        }
    )
    return {
        "run_id": result["run_id"],
        "scout_result": result["scout_result"],
        "oracle_result": result["oracle_result"],
        "alerts": result["alerts"],
        "daily_briefing": result["daily_briefing"],
        "errors": result["errors"]
    }