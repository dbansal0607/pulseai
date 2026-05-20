# backend/routers/dashboard.py
from fastapi import APIRouter
from agents.nexus import run_swarm
from db.supabase import get_recent_alerts, get_recent_runs

router = APIRouter()

@router.get("/status")
async def status():
    return {"status": "PulseAI running"}

@router.post("/test-swarm")
async def test_swarm():
    result = await run_swarm(
        event_type="pr_opened",
        event_payload={
            "pr_number": 42,
            "title": "Fix payment service auth bug",
            "files_changed": ["auth.py", "payment.py"],
            "author": "dhruv",
            "repo_name": "dbansal0607/pulseai"
        }
    )
    return {
        "run_id": result["run_id"],
        "scout_result": result["scout_result"],
        "oracle_result": result["oracle_result"],
        "planner_result": result["planner_result"],
        "scribe_result": result["scribe_result"],
        "alerts": result["alerts"],
        "daily_briefing": result["daily_briefing"],
        "errors": result["errors"]
    }

@router.get("/alerts")
async def get_alerts():
    alerts = await get_recent_alerts(limit=20)
    return {"alerts": alerts}

@router.get("/runs")
async def get_runs():
    runs = await get_recent_runs(limit=10)
    return {"runs": runs}