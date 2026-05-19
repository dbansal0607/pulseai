# backend/agents/scribe.py
from agents.base import BaseAgent, PulseState

class ScribeAgent(BaseAgent):

    def __init__(self):
        super().__init__(name="Scribe")

    async def run(self, state: PulseState) -> dict:
        self.log("Generating post-mortem...")

        return {
            "scribe_result": {
                "title": "Incident Post-Mortem",
                "timeline": [],
                "root_cause": "Scribe stub — real LLM generation in Week 2",
                "action_items": [],
                "draft_url": None
            }
        }