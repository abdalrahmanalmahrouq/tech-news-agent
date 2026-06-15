import uuid
from datetime import datetime
from loguru import logger
from agent.state import AgentState


def orchestrator_node(state: AgentState) -> dict:
    run_meta = state.get("run_meta", {})
    run_id = run_meta.get("run_id") or str(uuid.uuid4())[:8]
    started_at = datetime.utcnow().isoformat()


    logger.info("▶ Run {} started at {}", run_id, started_at)

    return {
        "run_meta": {
            "run_id": run_id,
            "started_at": started_at,
            "status": "running",
            "retry_count": 0,
            "errors": [],
        }
    }