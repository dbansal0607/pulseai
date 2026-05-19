# backend/agents/scout.py
from agents.base import BaseAgent, PulseState

class ScoutAgent(BaseAgent):
    
    def __init__(self):
        super().__init__(name="Scout")

    async def run(self, state: PulseState) -> dict:
        self.log("Analyzing PR for risk...")
        
        # STUB: real logic comes in Week 2
        # Will: fetch PR diff, run RAG against incident history, score risk
        pr_number = state["event_payload"].get("pr_number", "unknown")
        
        return {
            "scout_result": {
                "pr_number": pr_number,
                "risk_score": 0.0,       # 0.0 to 1.0
                "risk_level": "low",     # low / medium / high / critical
                "explanation": "Scout stub — real analysis coming in Week 2",
                "affected_files": [],
                "similar_incidents": []
            }
        }