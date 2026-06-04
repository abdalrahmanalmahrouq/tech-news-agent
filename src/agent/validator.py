from agent.state import AgentState


def validator_node(state: AgentState) -> dict:
    summaries = state["summaries"]
    run_meta = state.get("run_meta", {"retry_count": 0, "errors": []})

    validated = []
    rejected = []

    for summary in summaries:
        reasons = []

        if summary.get("relevance_score", 0) < 0.5:
            reasons.append(f"low relevance score: {summary.get('relevance_score')}")

        if len(summary.get("summary", "")) < 50:
            reasons.append("summary too short")

        if not summary.get("headline") or summary.get("headline") == "No headline":
            reasons.append("missing headline")

        if not summary.get("url"):
            reasons.append("missing url")

        if not summary.get("verified", True):
            count = summary.get("sources_found", 0)
            reasons.append(f"not verified — {count} corroborating source(s) found")

            
        if reasons:
            rejected.append({"summary": summary, "reasons": reasons})
            print(f"✗ Rejected: {summary.get('headline', 'unknown')[:60]}")
            print(f"  Reasons: {', '.join(reasons)}")
        else:
            validated.append(summary)
            print(f"✓ Validated: {summary.get('headline', '')[:60]}")

    run_meta["rejected"] = rejected
    run_meta["retry_count"] = run_meta.get("retry_count", 0) + 1

    return {
        "validated": validated,
        "run_meta": run_meta,
    }


def routing_function(state: AgentState) -> str:
    validated  = state.get("validated", [])
    run_meta   = state.get("run_meta", {})
    retry_count = run_meta.get("retry_count", 0)

    if len(validated) == 0 and retry_count < 2:
        rejected = run_meta.get("rejected", [])
        quality_failures = [
            r for r in rejected
            if any("low relevance" not in reason for reason in r["reasons"])
        ]
        if quality_failures:
            return "retry"   # genuine output quality problem — retry worth it

    return "continue"        # low relevance or retries exhausted — accept what we have