import json
import asyncio
from loguru import logger
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from agent.state import AgentState
from agent.llm import get_llm

CONCURRENCY = 5


@tool
def summarize_article(text: str) -> str:
    """Summarize an article and return a JSON string with headline, summary and category"""
    llm = get_llm()
    prompt = f"""Read the article below and return a JSON object with exactly these fields:

    {{
        "headline": "one clear headline under 15 words",
        "summary": "exactly 3 sentences summarizing the article",
        "category": "one of: AI, Technology, Tools, Research, Industry, Other"
    }}

    Rules:
    - Return ONLY the JSON object. No explanation, no markdown, no code blocks.

    Article:
    {text[:2000]}
    """
    response = llm.invoke(prompt)
    return response.content.strip()


@tool
def score_relevance(summary: str, category: str) -> float:
    """Score how relevant an article is to AI/tech professionals. Returns a float between 0.0 and 1.0."""
    llm = get_llm()
    prompt = f"""You are scoring article relevance for an AI/tech professional audience.

    Article summary: {summary}
    Category: {category}

    Return ONLY a single float between 0.0 and 1.0
    - 0.9-1.0 = must read
    - 0.6-0.8 = interesting
    - below 0.6 = low value

    No explanation. Just the number.
    """
    response = llm.invoke(prompt)
    try:
        return float(response.content.strip())
    except ValueError:
        return 0.5


def extract_json(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1] if text.count("```") >= 2 else text.lstrip("`")
        text = text.removeprefix("json").strip()
    return text

llm = get_llm()
tools = [summarize_article, score_relevance]
react_agent = create_react_agent(llm, tools)


async def read_one(article: dict, semaphore: asyncio.Semaphore) -> dict | None:
    async with semaphore:
        prompt = f"""You are a TECHNOLOGY news analyst. Follow these steps exactly, in order, with no repetition:

STEP 1: Call summarize_article once with the article content below.
STEP 2: Call score_relevance once using the summary and category from step 1.
STEP 3: Return a single JSON object with these exact fields:
{{
    "headline": "the headline from step 1",
    "summary": "the summary from step 1",
    "category": "the category from step 1",
    "relevance_score": the float from step 2
}}

Do not call any tool more than once. Do not explain anything. Return only the JSON.

Article URL: {article['url']}
Article Title: {article['title']}
Article Content: {article['body_text'][:2000]}
"""
        try:
            result = await react_agent.ainvoke({
                "messages": [{"role": "user", "content": prompt}]
            })
            last_message = result["messages"][-1].content

            try:
                parsed = json.loads(extract_json(last_message))
                summary = {
                    "url": article["url"],
                    "headline": parsed.get("headline", "No headline"),
                    "summary": parsed.get("summary", "No summary"),
                    "category": parsed.get("category", "Other"),
                    "relevance_score": float(parsed.get("relevance_score", 0.5)),
                }
            except (json.JSONDecodeError, AttributeError):
                summary = {
                    "url": article["url"],
                    "headline": article.get("title", "No headline"),
                    "summary": last_message[:300],
                    "category": "Other",
                    "relevance_score": 0.5,
                }

            logger.info("✓ Summarized: {}", article['title'][:60])
            return summary

        except Exception as e:
            logger.error("Failed to summarize: {} — {}", article['url'], e)
            return None


async def reader_node(state: AgentState) -> dict:
    raw_articles = state["raw_articles"]
    semaphore = asyncio.Semaphore(CONCURRENCY)
    results = await asyncio.gather(
        *(read_one(article, semaphore) for article in raw_articles)
    )
    summaries = [s for s in results if s is not None]
    return {"summaries": summaries}