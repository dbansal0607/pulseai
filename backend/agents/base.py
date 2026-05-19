# backend/agents/base.py
from typing import TypedDict, Optional, List, Any
from abc import ABC, abstractmethod

# ─────────────────────────────────────────────
# THE SHARED STATE
# This dict flows through every node in the graph.
# Each agent reads what it needs and writes its result back.
# ─────────────────────────────────────────────
class PulseState(TypedDict):
    # Input event
    event_type: str           # "pr_opened", "log_anomaly", "jira_poll", "slack_message"
    event_payload: dict       # Raw data from GitHub / logs / Jira / Slack

    # Agent outputs (filled in as agents run)
    scout_result: Optional[dict]    # PR risk score + explanation
    oracle_result: Optional[dict]   # Incident prediction + severity
    planner_result: Optional[dict]  # Sprint failure probability + blockers
    weaver_result: Optional[dict]   # Relevant past decisions + context
    scribe_result: Optional[dict]   # Post-mortem draft

    # Nexus outputs
    alerts: List[dict]              # List of alerts to send to Slack
    daily_briefing: Optional[str]   # Morning digest text
    
    # Metadata
    errors: List[str]               # Any errors that occurred during processing
    run_id: str                     # Unique ID for this run (for logging)


# ─────────────────────────────────────────────
# THE BASE AGENT
# All 5 agents inherit from this.
# They must implement the `run` method.
# ─────────────────────────────────────────────
class BaseAgent(ABC):
    
    def __init__(self, name: str):
        self.name = name
        print(f"🤖 Agent {self.name} initialized")

    @abstractmethod
    async def run(self, state: PulseState) -> dict:
        """
        Each agent implements this method.
        Receives the full state, returns a dict 
        that gets merged back into the state.
        """
        pass

    def log(self, message: str):
        """Simple logging with agent name prefix"""
        print(f"[{self.name}] {message}")

    def error(self, message: str, state: PulseState) -> PulseState:
        """Adds an error to state and returns it"""
        self.log(f"ERROR: {message}")
        state["errors"].append(f"{self.name}: {message}")
        return state