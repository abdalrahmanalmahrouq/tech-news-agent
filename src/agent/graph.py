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
        {
            "continue": "formatter",
            "retry": "reader"
        }
    )
    graph.add_edge("formatter", "delivery")
    graph.add_edge("delivery", END)

    return graph.compile(checkpointer=checkpointer)


async def main():
    initial_state = {
        "urls": [ "https://hnrss.org/frontpage"],
        "raw_articles": [],
        "summaries": [],
        "validated": [],
        "digest": "",
        "run_meta": {},
    }

    config = {"configurable": {"thread_id": "run-001"}}
    
    async with AsyncSqliteSaver.from_conn_string(get_db_path()) as checkpointer:
        app = build_graph(checkpointer)
        final_state = {}
 
        print("\n\U0001f4e1 Streaming pipeline...\n")
        async for event in app.astream_events(initial_state, config=config, version="v2"):
            kind = event["event"]
 
            # print each LLM token the moment it arrives
            if kind == "on_chat_model_stream":
                chunk = event["data"]["chunk"].content
                if chunk:
                    print(chunk, end="", flush=True)
 
            # put a newline after each complete LLM response
            elif kind == "on_chat_model_end":
                print()
 
            # the graph finished — grab the final state
            elif kind == "on_chain_end" and event.get("name") == "LangGraph":
                final_state = event["data"].get("output", {})
 
    log_run(
        run_meta=final_state.get("run_meta", {}),
        raw_articles=final_state.get("raw_articles", []),
        validated=final_state.get("validated", []),
    )
    
    digest = final_state.get("digest", "")
    if digest:
        with open("last_digest.html", "w") as f:
            f.write(digest)
        print(f"\n\U0001f4c4 Digest written to last_digest.html ({len(digest)} chars)")

    print("\n--- VALIDATED ---")
    for s in final_state.get("validated", []):
        print(f"Headline:  {s['headline']}")
        print(f"Summary:   {s['summary']}")
        print(f"Category:  {s['category']}")
        print(f"Score:     {s['relevance_score']}")
        print()
 
    run_meta = final_state.get("run_meta", {})
    print(f"Run ID:        {run_meta.get('run_id')}")
    print(f"Status:        {run_meta.get('status')}")
    print(f"Retries:       {run_meta.get('retry_count')}")
    print(f"Delivered to:  {run_meta.get('delivered_to')}")

if __name__ == "__main__":
    asyncio.run(main())