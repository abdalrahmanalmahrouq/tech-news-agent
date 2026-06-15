import uuid
import asyncio
from loguru import logger
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from agent.state import AgentState
from agent.scraper import scraper_node
from agent.reader import reader_node
from agent.validator import validator_node, routing_function
from agent.orchestrator import orchestrator_node
from agent.persistence.checkpointer import get_db_path
from agent.persistence.run_logger import log_run
from agent.formater import formatter_node
from agent.delivery import delivery_node
from agent.verifier import verifier_node


def build_graph(checkpointer):
    graph = StateGraph(AgentState)

    graph.add_node("orchestrator", orchestrator_node)
    graph.add_node("scraper", scraper_node)
    graph.add_node("reader", reader_node)
    graph.add_node("verifier", verifier_node)
    graph.add_node("validator", validator_node)
    graph.add_node("formatter", formatter_node)
    graph.add_node("delivery", delivery_node)

    graph.add_edge(START, "orchestrator")
    graph.add_edge("orchestrator", "scraper")
    graph.add_edge("scraper", "reader")
    graph.add_edge("reader", "verifier")
    graph.add_edge("verifier", "validator")

    graph.add_conditional_edges(
        "validator",
        routing_function,
        {"continue": "formatter", "retry": "reader"},
    )
    graph.add_edge("formatter", "delivery")
    graph.add_edge("delivery", END)

    return graph.compile(checkpointer=checkpointer)


async def run_pipeline(run_id: str | None = None) -> dict:
    """Run the full pipeline once and return the final state.
    This is the reusable core — the CLI, FastAPI, and the scheduler all call it."""
    run_id = run_id or str(uuid.uuid4())[:8]

    logger.info("Pipeline starting | run_id={}", run_id)

    initial_state = {
        "urls": [],
        "raw_articles": [],
        "summaries": [],
        "validated": [],
        "digest": "",
        "run_meta": {"run_id": run_id},
    }

    config = {"configurable": {"thread_id": run_id}}

    async with AsyncSqliteSaver.from_conn_string(get_db_path()) as checkpointer:
        app = build_graph(checkpointer)
        final_state = await app.ainvoke(initial_state, config=config)

    log_run(
        run_meta=final_state.get("run_meta", {}),
        raw_articles=final_state.get("raw_articles", []),
        validated=final_state.get("validated", []),
    )

    return final_state


async def main():
    logger.add("../data/logs/agent.log", rotation="1 day", retention="7 days", level="INFO")
    """CLI entry point — runs the pipeline then prints results."""
    final_state = await run_pipeline()

    digest = final_state.get("digest", "")
    if digest:
        with open("last_digest.html", "w") as f:
            f.write(digest)
        logger.info("Digest written to last_digest.html ({} chars)", len(digest))

    for s in final_state.get("validated", []):
        logger.info("Headline: {} | Score: {}", s['headline'], s['relevance_score'])

    run_meta = final_state.get("run_meta", {})
    logger.info("Run ID={} | Status={} | Retries={} | Delivered to={}",
                run_meta.get('run_id'), run_meta.get('status'),
                run_meta.get('retry_count'), run_meta.get('delivered_to'))


if __name__ == "__main__":
    asyncio.run(main())