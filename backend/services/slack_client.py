# backend/services/slack_client.py
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from config import SLACK_BOT_TOKEN, SLACK_CHANNEL_ID

# Initialize Slack client
client = WebClient(token=SLACK_BOT_TOKEN)


def send_scout_alert(pr_number: int, risk_level: str, risk_score: float,
                      explanation: str, key_concerns: list, 
                      recommendation: str, repo_name: str,
                      similar_incidents: list, pr_url: str = None):
    """
    Sends a formatted Scout alert to Slack.
    Called when Scout detects high/critical risk PR.
    """
    
    # Risk level emoji
    emoji = {
        "low": "🟢",
        "medium": "🟡", 
        "high": "🟠",
        "critical": "🔴"
    }.get(risk_level, "⚪")

    # Build concerns text
    concerns_text = "\n".join([f"• {c}" for c in key_concerns]) if key_concerns else "• Manual review recommended"

    # Build similar incidents text
    incidents_text = "\n".join([f"• {inc}" for inc in similar_incidents[:2]]) if similar_incidents else "• No similar incidents found"

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{emoji} Scout Alert — {risk_level.upper()} Risk PR #{pr_number}"
            }
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Repository:*\n{repo_name}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Risk Score:*\n{risk_score} / 1.0"
                }
            ]
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Analysis:*\n{explanation}"
            }
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Key Concerns:*\n{concerns_text}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Similar Past Incidents:*\n{incidents_text}"
                }
            ]
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Recommendation:*\n{recommendation}"
            }
        },
        {
            "type": "divider"
        }
    ]

    # Add PR link if available
    if pr_url:
        blocks.append({
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "View PR"},
                    "url": pr_url,
                    "style": "danger" if risk_level == "critical" else "primary"
                }
            ]
        })

    try:
        client.chat_postMessage(
            channel=SLACK_CHANNEL_ID,
            blocks=blocks,
            text=f"Scout Alert: {risk_level.upper()} risk PR #{pr_number} — {explanation[:100]}"
        )
        print(f"[Slack] ✅ Scout alert sent for PR #{pr_number}")
    except SlackApiError as e:
        print(f"[Slack] ❌ Failed to send Scout alert: {e.response['error']}")


def send_oracle_alert(service: str, severity: str, prediction: str,
                       estimated_breach_minutes: int, recommended_action: str,
                       likely_cause: str, anomalies: list):
    """
    Sends a formatted Oracle alert to Slack.
    Called when Oracle detects an anomaly.
    """
    
    emoji = {
        "low": "🟡",
        "medium": "🟠",
        "high": "🔴",
        "critical": "🚨"
    }.get(severity, "⚠️")

    anomaly_text = "\n".join([
        f"• {a['metric']}: {a['value']} (z-score: {a['zscore']})"
        for a in anomalies[:3]
    ]) if anomalies else "• Anomaly detected"

    breach_text = f"~{estimated_breach_minutes} minutes" if estimated_breach_minutes else "Unknown"

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{emoji} Oracle Alert — {severity.upper()} on {service}"
            }
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Service:*\n{service}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*SLA Breach In:*\n{breach_text}"
                }
            ]
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Prediction:*\n{prediction}"
            }
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Anomalies Detected:*\n{anomaly_text}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Likely Cause:*\n{likely_cause}"
                }
            ]
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Recommended Action:*\n{recommended_action}"
            }
        },
        {"type": "divider"}
    ]

    try:
        client.chat_postMessage(
            channel=SLACK_CHANNEL_ID,
            blocks=blocks,
            text=f"Oracle Alert: {severity.upper()} anomaly on {service} — {prediction[:100]}"
        )
        print(f"[Slack] ✅ Oracle alert sent for {service}")
    except SlackApiError as e:
        print(f"[Slack] ❌ Failed to send Oracle alert: {e.response['error']}")


def send_daily_briefing(alerts_count: int, scout_result: dict, 
                         oracle_result: dict, planner_result: dict):
    """
    Sends the daily engineering briefing to Slack.
    Called by Nexus every morning.
    """
    
    status_emoji = "🟢" if alerts_count == 0 else ("🔴" if alerts_count > 2 else "🟡")

    scout_text = "No PR risks detected"
    if scout_result and scout_result.get("risk_level") in ["high", "critical"]:
        scout_text = f"PR #{scout_result.get('pr_number')} — {scout_result.get('risk_level')} risk"

    oracle_text = "All services normal"
    if oracle_result and oracle_result.get("anomaly_detected"):
        oracle_text = f"{oracle_result.get('service')} — {oracle_result.get('severity')} anomaly"

    planner_text = "Sprint on track"
    if planner_result:
        prob = planner_result.get("sprint_failure_probability", 0)
        if prob > 0.5:
            planner_text = f"Sprint at risk — {round(prob*100)}% failure probability"

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{status_emoji} PulseAI Daily Briefing"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{alerts_count} alert(s) in last 24 hours*"
            }
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*🔍 Scout:*\n{scout_text}"},
                {"type": "mrkdwn", "text": f"*🔮 Oracle:*\n{oracle_text}"},
                {"type": "mrkdwn", "text": f"*📋 Planner:*\n{planner_text}"},
                {"type": "mrkdwn", "text": f"*✍️ Scribe:*\nReady for incidents"}
            ]
        },
        {"type": "divider"}
    ]

    try:
        client.chat_postMessage(
            channel=SLACK_CHANNEL_ID,
            blocks=blocks,
            text=f"PulseAI Daily Briefing — {alerts_count} alert(s)"
        )
        print(f"[Slack] ✅ Daily briefing sent")
    except SlackApiError as e:
        print(f"[Slack] ❌ Failed to send briefing: {e.response['error']}")