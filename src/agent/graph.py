import asyncio
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from agent.state import AgentState
from agent.scraper import scraper_node
from agent.reader import reader_node
from agent.validator import validator_node, routing_function
from agent.orchestrator import orchestrator_node
from agent.persistence.checkpointer import get_db_path
from agent.persistence.run_logger import log_run

def build_graph(checkpointer):
    graph = StateGraph(AgentState)

    graph.add_node("orchestrator", orchestrator_node)
    graph.add_node("scraper", scraper_node)
    graph.add_node("reader", reader_node)
    graph.add_node("validator", validator_node)

    graph.add_edge(START, "orchestrator")
    graph.add_edge("orchestrator", "scraper")
    graph.add_edge("scraper", "reader")
    graph.add_edge("reader", "validator")

    graph.add_conditional_edges(
        "validator",
        routing_function,
        {
            "continue": END,
            "retry": "reader"
        }
    )

    return graph.compile(checkpointer=checkpointer)


async def main():
    initial_state = {
        "urls": [ "https://techcrunch.com/feed/"],
        "raw_articles": [],
        "summaries": [],
        "validated": [],
        "run_meta": {},
    }

    async with AsyncSqliteSaver.from_conn_string(get_db_path()) as checkpointer:
        app = build_graph(checkpointer)
        result = await app.ainvoke(
            initial_state,
            config={"configurable": {"thread_id": "run-001"}}
        )

    log_run(
    run_meta=result["run_meta"],
    raw_articles=result["raw_articles"],
    validated=result["validated"],
)

    print("\n--- VALIDATED ---")
    for s in result["validated"]:
        print(f"Headline:  {s['headline']}")
        print(f"Summary:   {s['summary']}")
        print(f"Category:  {s['category']}")
        print(f"Score:     {s['relevance_score']}")
        print()

    print(f"Run ID:      {result['run_meta'].get('run_id')}")
    print(f"Started at:  {result['run_meta'].get('started_at')}")
    print(f"Status:      {result['run_meta'].get('status')}")
    print(f"Retries:     {result['run_meta'].get('retry_count')}")


if __name__ == "__main__":
    asyncio.run(main())