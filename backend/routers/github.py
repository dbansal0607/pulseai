# backend/routers/github.py
import hmac
import hashlib
import json
from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from agents.nexus import run_swarm
from config import GITHUB_WEBHOOK_SECRET

router = APIRouter()


def verify_signature(payload_bytes: bytes, signature_header: str) -> bool:
    if not signature_header:
        return False
    
    expected_signature = "sha256=" + hmac.new(
        GITHUB_WEBHOOK_SECRET.encode("utf-8"),
        payload_bytes,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(expected_signature, signature_header)


async def process_webhook(event_type: str, payload: dict):
    print(f"\n📨 Processing GitHub event: {event_type}")
    
    if event_type == "pull_request":
        action = payload.get("action")
        
        if action not in ["opened", "synchronize"]:
            print(f"   Ignoring PR action: {action}")
            return
            
        pr = payload.get("pull_request", {})
        repo = payload.get("repository", {})
        
        event_payload = {
            "pr_number": pr.get("number"),
            "title": pr.get("title"),
            "author": pr.get("user", {}).get("login"),
            "base_branch": pr.get("base", {}).get("ref"),
            "head_branch": pr.get("head", {}).get("ref"),
            "repo_name": repo.get("full_name"),
            "pr_url": pr.get("html_url"),
            "files_changed": [],
            "action": action
        }
        
        result = await run_swarm("pr_opened", event_payload)
        
        print(f"   ✅ Swarm complete — {len(result['alerts'])} alerts")
        print(f"   Scout risk: {result.get('scout_result', {}).get('risk_level', 'N/A')}")

    elif event_type == "push":
        commits = payload.get("commits", [])
        repo = payload.get("repository", {})
        
        print(f"   Push to repo — {len(commits)} commit(s)")


@router.post("/github")
async def github_webhook(request: Request, background_tasks: BackgroundTasks):
    payload_bytes = await request.body()
    
    signature = request.headers.get("X-Hub-Signature-256", "")
    event_type = request.headers.get("X-GitHub-Event", "")
    delivery_id = request.headers.get("X-GitHub-Delivery", "")
    
    print(f"\n🔔 GitHub webhook received — event: {event_type} | delivery: {delivery_id}")
    
    if GITHUB_WEBHOOK_SECRET and not verify_signature(payload_bytes, signature):
        print("   ❌ Invalid signature — rejecting")
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    
    try:
        payload = json.loads(payload_bytes)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    
    background_tasks.add_task(process_webhook, event_type, payload)
    
    return {"status": "received", "event": event_type, "delivery": delivery_id}