# backend/agents/planner.py
import json
import random
from agents.base import BaseAgent, PulseState
from config import GROQ_API_KEY
from groq import Groq

client = Groq(api_key=GROQ_API_KEY)


def generate_sprint_data() -> dict:
    """
    Simulates realistic Jira sprint data.
    In production this comes from the Jira API.
    """
    total_tickets = random.randint(15, 25)
    completed = random.randint(3, total_tickets - 3)
    in_progress = random.randint(2, 6)
    not_started = total_tickets - completed - in_progress

    # Generate some tickets
    tickets = []
    services = ["backend", "frontend", "infra", "ml", "api"]
    
    for i in range(1, total_tickets + 1):
        status = "done" if i <= completed else (
            "in_progress" if i <= completed + in_progress else "todo"
        )
        tickets.append({
            "id": f"BE-{100 + i}",
            "title": random.choice([
                "Implement user auth flow",
                "Fix payment gateway timeout",
                "Add Redis caching layer",
                "Refactor database queries",
                "Write unit tests for API",
                "Deploy to staging environment",
                "Fix mobile UI bug",
                "Add rate limiting",
                "Update API documentation",
                "Performance optimization"
            ]),
            "status": status,
            "component": random.choice(services),
            "story_points": random.choice([1, 2, 3, 5, 8])
        })

    # Create some blockers — unstarted tickets that others depend on
    blockers = []
    todo_tickets = [t for t in tickets if t["status"] == "todo"]
    
    if todo_tickets and random.random() < 0.6:
        blocker = random.choice(todo_tickets)
        blocked_count = random.randint(2, 4)
        blockers.append({
            "ticket": blocker["id"],
            "title": blocker["title"],
            "blocks_count": blocked_count
        })

    days_remaining = random.randint(2, 5)
    velocity = completed / max(1, (10 - days_remaining))  # tickets per day

    return {
        "sprint_name": f"Sprint {random.randint(20, 35)}",
        "total_tickets": total_tickets,
        "completed": completed,
        "in_progress": in_progress,
        "not_started": not_started,
        "days_remaining": days_remaining,
        "blockers": blockers,
        "velocity": round(velocity, 2),
        "tickets": tickets[:8]  # Sample of tickets for LLM context
    }


class PlannerAgent(BaseAgent):

    def __init__(self):
        super().__init__(name="Planner")

    async def run(self, state: PulseState) -> dict:
        self.log("Analyzing sprint health...")

        # Generate sprint data
        sprint = generate_sprint_data()

        completion_rate = sprint["completed"] / sprint["total_tickets"]
        self.log(f"Sprint: {sprint['completed']}/{sprint['total_tickets']} tickets done, "
                f"{sprint['days_remaining']} days left, "
                f"{len(sprint['blockers'])} blocker(s)")

        # Build context for LLM
        blocker_text = ""
        if sprint["blockers"]:
            blocker_text = "\nBlockers:\n"
            for b in sprint["blockers"]:
                blocker_text += f"- {b['ticket']}: {b['title']} (blocks {b['blocks_count']} tickets)\n"

        prompt = f"""You are Planner, an AI sprint analysis agent.

Sprint Data:
- Sprint: {sprint['sprint_name']}
- Total tickets: {sprint['total_tickets']}
- Completed: {sprint['completed']} ({round(completion_rate*100)}%)
- In progress: {sprint['in_progress']}
- Not started: {sprint['not_started']}
- Days remaining: {sprint['days_remaining']}
- Current velocity: {sprint['velocity']} tickets/day
{blocker_text}

Analyze this sprint and respond in this EXACT JSON format:
{{
    "failure_probability": <float 0.0 to 1.0>,
    "status": "<on_track|at_risk|critical>",
    "summary": "<2 sentence sprint health summary>",
    "top_blocker": "<most critical blocker or null>",
    "recommendation": "<single most important action to take>"
}}

Respond with ONLY the JSON, no other text."""

        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=300
            )

            raw = response.choices[0].message.content.strip()
            if "```json" in raw:
                raw = raw.split("```json")[1].split("```")[0].strip()
            elif "```" in raw:
                raw = raw.split("```")[1].split("```")[0].strip()

            result = json.loads(raw)

            self.log(f"Sprint status: {result.get('status')} — "
                    f"failure probability: {result.get('failure_probability')}")

            return {
                "planner_result": {
                    "sprint_name": sprint["sprint_name"],
                    "sprint_failure_probability": result.get("failure_probability", 0.0),
                    "status": result.get("status", "on_track"),
                    "summary": result.get("summary", ""),
                    "blockers": sprint["blockers"],
                    "top_blocker": result.get("top_blocker"),
                    "recommendation": result.get("recommendation", ""),
                    "metrics": {
                        "total": sprint["total_tickets"],
                        "completed": sprint["completed"],
                        "in_progress": sprint["in_progress"],
                        "days_remaining": sprint["days_remaining"],
                        "velocity": sprint["velocity"]
                    }
                }
            }

        except Exception as e:
            self.log(f"LLM call failed: {e}")
            failure_prob = 1.0 - completion_rate
            return {
                "planner_result": {
                    "sprint_name": sprint["sprint_name"],
                    "sprint_failure_probability": round(failure_prob, 2),
                    "status": "at_risk" if failure_prob > 0.5 else "on_track",
                    "summary": f"Sprint at {round(completion_rate*100)}% completion with {sprint['days_remaining']} days left.",
                    "blockers": sprint["blockers"],
                    "recommendation": "Manual sprint review recommended",
                    "metrics": {
                        "total": sprint["total_tickets"],
                        "completed": sprint["completed"],
                        "in_progress": sprint["in_progress"],
                        "days_remaining": sprint["days_remaining"],
                        "velocity": sprint["velocity"]
                    }
                }
            }