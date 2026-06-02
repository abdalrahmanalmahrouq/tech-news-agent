from typing import TypedDict

class AgentState(TypedDict):
    urls: list[str]           # input: URLs to scrape
    raw_articles: list[dict]  # output: scraped article content
    summaries: list[dict] 
    validated: list[dict]
    digest: str
    run_meta: dict
    