# backend/agents/nexus.py
import uuid
from langgraph.graph import StateGraph, END
from agents.base import PulseState
from agents.scout import ScoutAgent
from agents.oracle import OracleAgent
from agents.planner import PlannerAgent
from agents.weaver import WeaverAgent
from agents.scribe import ScribeAgent

# ─────────────────────────────────────────────
# INITIALIZE ALL AGENTS
# One instance of each, shared across runs
# ─────────────────────────────────────────────
scout = ScoutAgent()
oracle = OracleAgent()
planner = PlannerAgent()
weaver = WeaverAgent()
scribe = ScribeAgent()


# ─────────────────────────────────────────────
# NODE FUNCTIONS
# Each node wraps an agent's run() method
# Nodes must return a dict that updates the state
# ─────────────────────────────────────────────

async def run_scout(state: PulseState) -> dict:
    return await scout.run(state)

async def run_oracle(state: PulseState) -> dict:
    return await oracle.run(state)

async def run_planner(state: PulseState) -> dict:
    return await planner.run(state)

async def run_weaver(state: PulseState) -> dict:
    return await weaver.run(state)

async def run_scribe(state: PulseState) -> dict:
    return await scribe.run(state)

async def nexus_compile(state: PulseState) -> dict:
    """
    Nexus reads all agent results and decides:
    - Which alerts to fire
    - What to include in the daily briefing
    """
    print("[Nexus] Compiling agent results...")
    
    alerts = []

    # Check Scout result
    scout_result = state.get("scout_result") or {}
    if scout_result.get("risk_level") in ["high", "critical"]:
        alerts.append({
            "source": "Scout",
            "message": f"High risk PR #{scout_result.get('pr_number')} — {scout_result.get('explanation')}",
            "severity": scout_result.get("risk_level")
        })

    # Check Oracle result
    oracle_result = state.get("oracle_result") or {}
    if oracle_result.get("anomaly_detected"):
        alerts.append({
            "source": "Oracle",
            "message": f"Anomaly on {oracle_result.get('service')} — {oracle_result.get('prediction')}",
            "severity": oracle_result.get("severity")
        })

    # Check Planner result
    planner_result = state.get("planner_result") or {}
    if planner_result.get("sprint_failure_probability", 0) > 0.5:
        alerts.append({
            "source": "Planner",
            "message": f"Sprint at risk — {planner_result.get('recommendation')}",
            "severity": "medium"
        })

    return {
        "alerts": alerts,
        "daily_briefing": f"PulseAI Daily Briefing — {len(alerts)} alert(s) detected."
    }


# ─────────────────────────────────────────────
# ROUTING LOGIC
# Decides which agents to run based on event type
# ─────────────────────────────────────────────

def route_event(state: PulseState) -> str:
    """
    After receiving an event, decide which agent to run first.
    PR events → Scout first
    Log events → Oracle first
    Jira events → Planner first
    Slack events → Weaver first
    Incident resolved → Scribe first
    """
    event_type = state.get("event_type", "")
    
    if event_type == "pr_opened":
        return "scout"
    elif event_type == "log_anomaly":
        return "oracle"
    elif event_type == "jira_poll":
        return "planner"
    elif event_type == "slack_message":
        return "weaver"
    elif event_type == "incident_resolved":
        return "scribe"
    else:
        return "nexus_compile"  # Unknown event, just compile whatever we have


# ─────────────────────────────────────────────
# BUILD THE GRAPH
# This is the actual LangGraph state machine
# ─────────────────────────────────────────────

def build_graph():
    graph = StateGraph(PulseState)

    # Add all nodes
    graph.add_node("scout", run_scout)
    graph.add_node("oracle", run_oracle)
    graph.add_node("planner", run_planner)
    graph.add_node("weaver", run_weaver)
    graph.add_node("scribe", run_scribe)
    graph.add_node("nexus_compile", nexus_compile)

    # Entry point — route_event decides first node
    graph.set_conditional_entry_point(route_event)

    # After each specialist agent → always go to nexus_compile
    graph.add_edge("scout", "nexus_compile")
    graph.add_edge("oracle", "nexus_compile")
    graph.add_edge("planner", "nexus_compile")
    graph.add_edge("weaver", "nexus_compile")
    graph.add_edge("scribe", "nexus_compile")

    # After nexus_compile → END
    graph.add_edge("nexus_compile", END)

    return graph.compile()


# Single compiled graph instance — reused across all requests
pulse_graph = build_graph()
print("✅ Nexus graph compiled successfully")


# ─────────────────────────────────────────────
# PUBLIC FUNCTION
# Called by FastAPI routes to trigger the swarm
# ─────────────────────────────────────────────

async def run_swarm(event_type: str, event_payload: dict) -> PulseState:
    initial_state: PulseState = {
        "event_type": event_type,
        "event_payload": event_payload,
        "scout_result": None,
        "oracle_result": None,
        "planner_result": None,
        "weaver_result": None,
        "scribe_result": None,
        "alerts": [],
        "daily_briefing": None,
        "errors": [],
        "run_id": str(uuid.uuid4())
    }
    
    print(f"\n🔄 Swarm triggered — event: {event_type} | run_id: {initial_state['run_id']}")
    
    final_state = await pulse_graph.ainvoke(initial_state)
    
    # Save to Supabase
    try:
        from db.supabase import save_agent_run, save_alert
        await save_agent_run(
            run_id=final_state["run_id"],
            event_type=event_type,
            event_payload=event_payload,
            final_state=final_state
        )
        # Save individual alerts
        for alert in final_state.get("alerts", []):
            await save_alert(
                run_id=final_state["run_id"],
                source=alert["source"],
                severity=alert["severity"],
                message=alert["message"],
                payload=alert
            )
    except Exception as e:
        print(f"[Nexus] ⚠️ Failed to save to Supabase: {e}")
    
    print(f"✅ Swarm complete — {len(final_state['alerts'])} alerts generated")
    return final_state