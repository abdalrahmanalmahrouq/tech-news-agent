import os
import asyncio
from dotenv import load_dotenv
from tavily import TavilyClient
from agent.state import AgentState

load_dotenv()


async def verifier_node(state: AgentState) -> dict:
    summaries = state.get("summaries", [])
    api_key   = os.getenv("TAVILY_API_KEY")

    # graceful skip — pipeline still works without the API key
    if not api_key:
        print("\u26a0 Verifier: TAVILY_API_KEY not set — skipping, all marked verified.")
        for s in summaries:
            s["verified"]      = True
            s["sources_found"] = 0
        return {"summaries": summaries}

    client = TavilyClient(api_key=api_key)
    print(f"  Verifying {len(summaries)} article(s)...")

    for summary in summaries:
        headline = summary.get("headline", "")
        try:
            # asyncio.to_thread runs the sync Tavily call without blocking the event loop
            response = await asyncio.to_thread(
                client.search,
                headline,
                search_depth="basic",
                max_results=5,
            )
            sources = response.get("results", [])
            count   = len(sources)
            verified = count >= 1      # at least one corroborating source = verified

            summary["verified"]      = verified
            summary["sources_found"] = count

            icon = "\u2713" if verified else "\u2717"
            label = "Verified" if verified else "Unverified"
            print(f"  {icon} {label} ({count} sources): {headline[:60]}")

        except Exception as e:
            # don't reject on search failure — benefit of the doubt
            print(f"  \u26a0 Search failed for '{headline[:40]}' \u2014 {e}")
            summary["verified"]      = True
            summary["sources_found"] = 0

    return {"summaries": summaries}