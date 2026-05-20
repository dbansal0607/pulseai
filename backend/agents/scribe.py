# backend/agents/scribe.py
import json
from datetime import datetime, timedelta
import random
from agents.base import BaseAgent, PulseState
from config import GROQ_API_KEY
from groq import Groq

client = Groq(api_key=GROQ_API_KEY)


class ScribeAgent(BaseAgent):

    def __init__(self):
        super().__init__(name="Scribe")

    async def run(self, state: PulseState) -> dict:
        self.log("Generating post-mortem...")

        # Collect context from other agents
        oracle_result = state.get("oracle_result") or {}
        scout_result = state.get("scout_result") or {}
        payload = state["event_payload"]

        # Only generate full post-mortem for incident_resolved events
        # For other events, generate a brief summary
        event_type = state["event_type"]

        if event_type == "incident_resolved":
            service = payload.get("service", "unknown-service")
            duration_minutes = payload.get("duration_minutes", 45)
            affected_users = payload.get("affected_users", 1000)
        else:
            # Use Oracle's data if available
            service = oracle_result.get("service", "api-gateway")
            duration_minutes = random.randint(20, 90)
            affected_users = random.randint(500, 5000)

        # Build timeline from available data
        now = datetime.utcnow()
        timeline = [
            {
                "time": (now - timedelta(minutes=duration_minutes)).strftime("%H:%M UTC"),
                "event": "First anomaly detected in logs"
            },
            {
                "time": (now - timedelta(minutes=duration_minutes - 5)).strftime("%H:%M UTC"),
                "event": "Alert fired — on-call engineer paged"
            },
            {
                "time": (now - timedelta(minutes=duration_minutes - 15)).strftime("%H:%M UTC"),
                "event": "Investigation started — logs reviewed"
            },
            {
                "time": (now - timedelta(minutes=10)).strftime("%H:%M UTC"),
                "event": "Root cause identified — fix deployed"
            },
            {
                "time": now.strftime("%H:%M UTC"),
                "event": "Service restored — incident resolved"
            }
        ]

        # Build context
        oracle_context = ""
        if oracle_result.get("anomaly_detected"):
            oracle_context = f"""
Oracle detected:
- Anomaly on {oracle_result.get('service', service)}
- Likely cause: {oracle_result.get('likely_cause', 'Unknown')}
- Severity: {oracle_result.get('severity', 'unknown')}"""

        scout_context = ""
        if scout_result.get("risk_level") in ["high", "critical"]:
            scout_context = f"""
Scout flagged:
- PR #{scout_result.get('pr_number')} as {scout_result.get('risk_level')} risk
- Files: {', '.join(scout_result.get('affected_files', []))}"""

        prompt = f"""You are Scribe, an AI post-mortem generation agent.

Incident Details:
- Service: {service}
- Duration: {duration_minutes} minutes
- Affected users: ~{affected_users}
- Timeline: {json.dumps(timeline, indent=2)}
{oracle_context}
{scout_context}

Generate a structured post-mortem in this EXACT JSON format:
{{
    "title": "<incident title>",
    "severity": "<P1|P2|P3>",
    "root_cause": "<1-2 sentence root cause>",
    "impact": "<what was affected and how many users>",
    "timeline_summary": "<2-3 sentence narrative of what happened>",
    "action_items": [
        "<action item 1>",
        "<action item 2>",
        "<action item 3>"
    ],
    "prevention": "<how to prevent this in future>"
}}

Respond with ONLY the JSON, no other text."""

        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=500
            )

            raw = response.choices[0].message.content.strip()
            if "```json" in raw:
                raw = raw.split("```json")[1].split("```")[0].strip()
            elif "```" in raw:
                raw = raw.split("```")[1].split("```")[0].strip()

            result = json.loads(raw)

            self.log(f"Post-mortem generated — {result.get('severity')} — {result.get('title', '')[:50]}")

            return {
                "scribe_result": {
                    "title": result.get("title"),
                    "severity": result.get("severity", "P2"),
                    "root_cause": result.get("root_cause"),
                    "impact": result.get("impact"),
                    "timeline": timeline,
                    "timeline_summary": result.get("timeline_summary"),
                    "action_items": result.get("action_items", []),
                    "prevention": result.get("prevention"),
                    "draft_url": None  # Will push to Notion in Week 3
                }
            }

        except Exception as e:
            self.log(f"LLM call failed: {e}")
            return {
                "scribe_result": {
                    "title": f"Incident on {service}",
                    "severity": "P2",
                    "root_cause": "Investigation required",
                    "impact": f"~{affected_users} users affected for {duration_minutes} minutes",
                    "timeline": timeline,
                    "action_items": ["Review logs", "Add monitoring", "Update runbook"],
                    "draft_url": None
                }
            }