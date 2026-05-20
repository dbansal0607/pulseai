# backend/agents/oracle.py
import json
import random
import math
from agents.base import BaseAgent, PulseState
from config import GROQ_API_KEY
from groq import Groq

client = Groq(api_key=GROQ_API_KEY)


def calculate_zscore(value: float, mean: float, std: float) -> float:
    """
    Z-score = how many standard deviations away from the mean.
    Z > 2.5 = anomaly (only 1.2% of normal data exceeds this)
    """
    if std == 0:
        return 0
    return abs(value - mean) / std


def generate_log_metrics(service: str, anomalous: bool = False) -> dict:
    """
    Simulates realistic log metrics for a service.
    In production this would come from Grafana/Datadog/CloudWatch.
    
    Normal baseline:
    - Error rate: ~2% (mean=2, std=0.5)
    - Latency p99: ~200ms (mean=200, std=20)
    - Request rate: ~1000/min (mean=1000, std=50)
    
    Anomalous:
    - Error rate spikes to 15-40%
    - Latency spikes to 800-2000ms
    """
    if anomalous:
        return {
            "service": service,
            "error_rate": round(random.uniform(15, 40), 2),      # % errors
            "latency_p99": round(random.uniform(800, 2000), 0),  # ms
            "request_rate": round(random.uniform(400, 700), 0),  # req/min (dropping)
            "memory_usage": round(random.uniform(85, 97), 1),    # % memory
            "cpu_usage": round(random.uniform(75, 95), 1),       # % CPU
        }
    else:
        return {
            "service": service,
            "error_rate": round(random.gauss(2, 0.5), 2),
            "latency_p99": round(random.gauss(200, 20), 0),
            "request_rate": round(random.gauss(1000, 50), 0),
            "memory_usage": round(random.gauss(45, 5), 1),
            "cpu_usage": round(random.gauss(30, 5), 1),
        }


# Baseline stats (what "normal" looks like)
BASELINES = {
    "error_rate":    {"mean": 2.0,    "std": 0.5},
    "latency_p99":   {"mean": 200.0,  "std": 20.0},
    "request_rate":  {"mean": 1000.0, "std": 50.0},
    "memory_usage":  {"mean": 45.0,   "std": 5.0},
    "cpu_usage":     {"mean": 30.0,   "std": 5.0},
}

ANOMALY_THRESHOLD = 2.5  # Z-score threshold


class OracleAgent(BaseAgent):

    def __init__(self):
        super().__init__(name="Oracle")

    async def run(self, state: PulseState) -> dict:
        self.log("Scanning log stream for anomalies...")

        payload = state["event_payload"]
        event_type = state["event_type"]

        # For log_anomaly events, use real payload
        # For other events (like pr_opened), simulate a random service check
        if event_type == "log_anomaly":
            service = payload.get("service", "api-gateway")
            metrics = payload.get("metrics", {})
            # 70% chance of anomaly for demo purposes when explicitly triggered
            anomalous = random.random() < 0.7
            if not metrics:
                metrics = generate_log_metrics(service, anomalous=anomalous)
        else:
            # Background check — scan a random service
            services = ["payment-service", "api-gateway", "user-service",
                       "order-service", "notification-service"]
            service = random.choice(services)
            # 20% chance of anomaly during background checks
            anomalous = random.random() < 0.2
            metrics = generate_log_metrics(service, anomalous=anomalous)

        self.log(f"Checking {service} — error_rate: {metrics['error_rate']}%, "
                f"latency: {metrics['latency_p99']}ms")

        # Run z-score anomaly detection
        anomalies_found = []
        max_zscore = 0

        for metric, value in metrics.items():
            if metric == "service":
                continue
            baseline = BASELINES.get(metric)
            if not baseline:
                continue

            zscore = calculate_zscore(
                value,
                baseline["mean"],
                baseline["std"]
            )

            if zscore > ANOMALY_THRESHOLD:
                anomalies_found.append({
                    "metric": metric,
                    "value": value,
                    "zscore": round(zscore, 2),
                    "baseline_mean": baseline["mean"]
                })
                max_zscore = max(max_zscore, zscore)

        if not anomalies_found:
            self.log(f"✅ {service} — all metrics normal")
            return {
                "oracle_result": {
                    "anomaly_detected": False,
                    "service": service,
                    "severity": "none",
                    "prediction": "All metrics within normal range",
                    "metrics": metrics,
                    "anomalies": [],
                    "estimated_breach_minutes": None
                }
            }

        # Anomaly detected — call LLM for prediction
        self.log(f"⚠️ Anomaly detected on {service} — calling LLM for prediction...")

        anomaly_summary = "\n".join([
            f"- {a['metric']}: {a['value']} (baseline: {a['baseline_mean']}, z-score: {a['zscore']})"
            for a in anomalies_found
        ])

        prompt = f"""You are Oracle, an AI incident prediction agent.

Service: {service}
Anomalies detected:
{anomaly_summary}

Based on these metrics, predict what will happen if no action is taken.
Respond in this EXACT JSON format:
{{
    "severity": "<low|medium|high|critical>",
    "prediction": "<1-2 sentence prediction of what will happen>",
    "estimated_breach_minutes": <integer: minutes until SLA breach, or null>,
    "recommended_action": "<immediate action to take>",
    "likely_cause": "<most likely root cause>"
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

            severity = result.get("severity", "medium")
            self.log(f"🚨 Prediction: {severity} severity — {result.get('prediction', '')[:60]}...")

            return {
                "oracle_result": {
                    "anomaly_detected": True,
                    "service": service,
                    "severity": severity,
                    "prediction": result.get("prediction", ""),
                    "estimated_breach_minutes": result.get("estimated_breach_minutes"),
                    "recommended_action": result.get("recommended_action", ""),
                    "likely_cause": result.get("likely_cause", ""),
                    "metrics": metrics,
                    "anomalies": anomalies_found
                }
            }

        except Exception as e:
            self.log(f"LLM call failed: {e}")
            severity = "high" if max_zscore > 4 else "medium"
            return {
                "oracle_result": {
                    "anomaly_detected": True,
                    "service": service,
                    "severity": severity,
                    "prediction": f"Anomaly detected on {service} — manual investigation required",
                    "metrics": metrics,
                    "anomalies": anomalies_found,
                    "estimated_breach_minutes": 30
                }
            }