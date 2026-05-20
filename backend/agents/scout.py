# backend/agents/scout.py
from agents.base import BaseAgent, PulseState
from db.chroma import search_similar_incidents
from config import GROQ_API_KEY
from groq import Groq

client = Groq(api_key=GROQ_API_KEY)

class ScoutAgent(BaseAgent):

    def __init__(self):
        super().__init__(name="Scout")

    async def run(self, state: PulseState) -> dict:
        self.log("Analyzing PR for risk...")

        payload = state["event_payload"]
        pr_number = payload.get("pr_number", "unknown")
        pr_title = payload.get("title", "")
        pr_author = payload.get("author", "unknown")
        files_changed = payload.get("files_changed", [])
        repo_name = payload.get("repo_name", "unknown")

        # Step 1: Search ChromaDB for similar past incidents
        self.log(f"Searching for incidents similar to PR #{pr_number}...")
        similar_incidents = search_similar_incidents(
            pr_files=files_changed,
            pr_title=pr_title,
            n_results=3
        )

        # Step 2: Build context from similar incidents
        incident_context = ""
        if similar_incidents:
            incident_context = "\n\nSimilar past incidents:\n"
            for i, inc in enumerate(similar_incidents, 1):
                meta = inc["metadata"]
                incident_context += f"{i}. {meta.get('title', 'Unknown')} "
                incident_context += f"(service: {meta.get('affected_service', 'unknown')})\n"
        else:
            incident_context = "\n\nNo similar past incidents found."

        # Step 3: Call Groq LLM for risk analysis
        self.log("Calling LLM for risk analysis...")

        prompt = f"""You are Scout, an AI code review agent that analyzes pull requests for risk.

PR Details:
- Repository: {repo_name}
- PR #{pr_number}: {pr_title}
- Author: {pr_author}
- Files changed: {', '.join(files_changed) if files_changed else 'Not available'}
{incident_context}

Analyze this PR and respond in this EXACT JSON format:
{{
    "risk_score": <float between 0.0 and 1.0>,
    "risk_level": "<low|medium|high|critical>",
    "explanation": "<2-3 sentence explanation of the risk>",
    "key_concerns": ["<concern 1>", "<concern 2>"],
    "recommendation": "<what the reviewer should focus on>"
}}

Risk scoring guide:
- 0.0-0.3: low (routine changes, low risk files)
- 0.3-0.6: medium (moderate changes, some risk)
- 0.6-0.8: high (significant changes, sensitive files)
- 0.8-1.0: critical (auth, payment, security files touched)

Respond with ONLY the JSON, no other text."""

        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=500
            )

            raw = response.choices[0].message.content.strip()

            # Parse JSON response
            import json
            # Clean up if model adds markdown
            if "```json" in raw:
                raw = raw.split("```json")[1].split("```")[0].strip()
            elif "```" in raw:
                raw = raw.split("```")[1].split("```")[0].strip()

            result = json.loads(raw)

            self.log(f"Risk analysis complete — {result.get('risk_level', 'unknown')} risk (score: {result.get('risk_score', 0)})")

            return {
                "scout_result": {
                    "pr_number": pr_number,
                    "risk_score": result.get("risk_score", 0.0),
                    "risk_level": result.get("risk_level", "low"),
                    "explanation": result.get("explanation", ""),
                    "key_concerns": result.get("key_concerns", []),
                    "recommendation": result.get("recommendation", ""),
                    "affected_files": files_changed,
                    "similar_incidents": [
                        inc["metadata"].get("title") for inc in similar_incidents
                    ]
                }
            }

        except Exception as e:
            self.log(f"LLM call failed: {e}")
            return {
                "scout_result": {
                    "pr_number": pr_number,
                    "risk_score": 0.0,
                    "risk_level": "low",
                    "explanation": f"Scout analysis failed: {str(e)}",
                    "key_concerns": [],
                    "recommendation": "Manual review recommended",
                    "affected_files": files_changed,
                    "similar_incidents": []
                }
            }