# backend/db/supabase.py
from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY
from typing import Optional
import json

# Initialize client
# This is a module-level singleton — created once, reused everywhere
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
print("✅ Supabase client initialized")


async def save_agent_run(run_id: str, event_type: str, event_payload: dict, final_state: dict):
    """
    Saves the complete result of an agent swarm run to PostgreSQL.
    Called by Nexus after every run completes.
    """
    try:
        data = {
            "run_id": run_id,
            "event_type": event_type,
            "event_payload": event_payload,
            "scout_result": final_state.get("scout_result"),
            "oracle_result": final_state.get("oracle_result"),
            "planner_result": final_state.get("planner_result"),
            "weaver_result": final_state.get("weaver_result"),
            "scribe_result": final_state.get("scribe_result"),
            "alerts": final_state.get("alerts", []),
            "daily_briefing": final_state.get("daily_briefing"),
            "errors": final_state.get("errors", [])
        }
        
        result = supabase.table("agent_runs").insert(data).execute()
        print(f"[Supabase] ✅ Saved agent run {run_id}")
        return result
    except Exception as e:
        print(f"[Supabase] ❌ Failed to save run {run_id}: {e}")


async def save_alert(run_id: str, source: str, severity: str, message: str, payload: dict = None):
    """Saves a single alert to the alerts table."""
    try:
        data = {
            "run_id": run_id,
            "source": source,
            "severity": severity,
            "message": message,
            "payload": payload or {}
        }
        result = supabase.table("alerts").insert(data).execute()
        print(f"[Supabase] ✅ Saved alert from {source} — {severity}")
        return result
    except Exception as e:
        print(f"[Supabase] ❌ Failed to save alert: {e}")


async def save_pr(repo_name: str, pr_number: int, title: str, author: str, 
                   risk_score: float, risk_level: str, files_changed: list):
    """Saves PR analysis result to pr_history table."""
    try:
        data = {
            "repo_name": repo_name,
            "pr_number": pr_number,
            "title": title,
            "author": author,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "files_changed": files_changed
        }
        result = supabase.table("pr_history").insert(data).execute()
        print(f"[Supabase] ✅ Saved PR #{pr_number} — risk: {risk_level}")
        return result
    except Exception as e:
        print(f"[Supabase] ❌ Failed to save PR: {e}")


async def get_recent_alerts(limit: int = 20) -> list:
    """Fetches recent alerts for the dashboard."""
    try:
        result = supabase.table("alerts")\
            .select("*")\
            .order("created_at", desc=True)\
            .limit(limit)\
            .execute()
        return result.data
    except Exception as e:
        print(f"[Supabase] ❌ Failed to fetch alerts: {e}")
        return []


async def get_recent_runs(limit: int = 10) -> list:
    """Fetches recent agent runs for the dashboard."""
    try:
        result = supabase.table("agent_runs")\
            .select("run_id, event_type, alerts, daily_briefing, created_at")\
            .order("created_at", desc=True)\
            .limit(limit)\
            .execute()
        return result.data
    except Exception as e:
        print(f"[Supabase] ❌ Failed to fetch runs: {e}")
        return []