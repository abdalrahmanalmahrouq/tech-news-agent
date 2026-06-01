import uuid
from datetime import datetime
from agent.state import AgentState


def orchestrator_node(state: AgentState) -> dict:
    run_id = str(uuid.uuid4())[:8]
    started_at = datetime.utcnow().isoformat()

    urls = state.get("urls", [])

    if not urls:
        print("✗ Orchestrator: no URLs provided. Aborting.")
        return {
            "run_meta": {
                "run_id": run_id,
                "started_at": started_at,
                "status": "aborted",
                "error": "no URLs provided",
                "retry_count": 0,
                "errors": [],
            }
        }

    print(f"▶ Run {run_id} started at {started_at}")
    print(f"  URLs to process: {len(urls)}")

    return {
        "run_meta": {
            "run_id": run_id,
            "started_at": started_at,
            "status": "running",
            "retry_count": 0,
            "errors": [],
        }
    }
