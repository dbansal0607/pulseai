# backend/agents/weaver.py
from agents.base import BaseAgent, PulseState

class WeaverAgent(BaseAgent):

    def __init__(self):
        super().__init__(name="Weaver")

    async def run(self, state: PulseState) -> dict:
        self.log("Searching knowledge graph...")

        return {
            "weaver_result": {
                "relevant_decisions": [],
                "relevant_discussions": [],
                "context_summary": "Weaver stub — real semantic search in Week 2"
            }
        }