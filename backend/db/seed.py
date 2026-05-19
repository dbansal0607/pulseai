# backend/db/seed.py
# Run this once to seed realistic demo data into ChromaDB
# This gives Scout a history of incidents to compare PRs against

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.chroma import add_incident

DEMO_INCIDENTS = [
    {
        "id": "inc_001",
        "title": "Payment service outage — auth token expiry bug",
        "description": "Auth tokens were expiring 10x faster than expected due to a miscalculation in auth.py. Caused 3-hour outage affecting checkout. Root cause: off-by-one error in token TTL calculation.",
        "service": "payment-service",
        "files": ["auth.py", "payment.py", "token_manager.py"]
    },
    {
        "id": "inc_002", 
        "title": "Database connection pool exhaustion",
        "description": "Connection pool was exhausted during peak traffic. New connections were opened but never closed in db_utils.py. Memory leak caused gradual degradation over 6 hours.",
        "service": "api-gateway",
        "files": ["db_utils.py", "connection_pool.py", "api/routes.py"]
    },
    {
        "id": "inc_003",
        "title": "User data exposure — missing authorization check",
        "description": "A refactor of the user service removed an authorization middleware. Users could access other users data for 2 hours before detection. Affected user_controller.py.",
        "service": "user-service", 
        "files": ["user_controller.py", "middleware/auth.py", "api/users.py"]
    },
    {
        "id": "inc_004",
        "title": "Notification service crash — unhandled null pointer",
        "description": "Email notifications crashed when user had no email address set. Null check was missing in notification_service.py. Caused silent failures for 15% of users.",
        "service": "notification-service",
        "files": ["notification_service.py", "email_sender.py", "user_model.py"]
    },
    {
        "id": "inc_005",
        "title": "Deployment pipeline failure — config mismatch",
        "description": "Production deployment failed because config.py had hardcoded staging URLs. Caught in smoke test but caused 45-minute deploy delay.",
        "service": "deployment",
        "files": ["config.py", "deploy/pipeline.yml", "settings.py"]
    },
    {
        "id": "inc_006",
        "title": "Search service slowdown — missing database index",
        "description": "A new query in search.py performed a full table scan because the index was dropped in a migration. Response times went from 50ms to 8000ms.",
        "service": "search-service",
        "files": ["search.py", "migrations/0042_add_search_index.py", "models/product.py"]
    },
    {
        "id": "inc_007",
        "title": "Memory leak in background job processor",
        "description": "Background jobs in worker.py were accumulating task objects in memory. Server ran out of memory after 48 hours. Required emergency restart.",
        "service": "worker-service",
        "files": ["worker.py", "task_queue.py", "job_processor.py"]
    },
    {
        "id": "inc_008",
        "title": "Race condition in order processing",
        "description": "Two concurrent requests could both pass the inventory check before either decremented the count. Caused overselling of limited items. Found in order_service.py.",
        "service": "order-service",
        "files": ["order_service.py", "inventory.py", "payment_processor.py"]
    }
]

if __name__ == "__main__":
    print("🌱 Seeding demo incidents into ChromaDB...")
    for incident in DEMO_INCIDENTS:
        add_incident(
            incident_id=incident["id"],
            title=incident["title"],
            description=incident["description"],
            affected_service=incident["service"],
            files_involved=incident["files"]
        )
    print(f"\n✅ Seeded {len(DEMO_INCIDENTS)} incidents into ChromaDB")
    print("Scout can now do RAG-based risk scoring!")