import httpx
from bs4 import BeautifulSoup
from agent.state import AgentState
from agent.persistence.url_store import init_url_store, is_seen, mark_seen


def extract_article_urls(feed_text: str, source_url: str) -> list[str]:
    soup = BeautifulSoup(feed_text, "xml")
    urls = []

    # RSS feeds
    for item in soup.find_all("item"):
        link = item.find("link")
        if link and link.text.strip():
            urls.append(link.text.strip())

    # Atom feeds
    if not urls:
        for entry in soup.find_all("entry"):
            link = entry.find("link")
            if link and link.get("href"):
                urls.append(link["href"].strip())

    return urls


async def fetch_article(client: httpx.AsyncClient, url: str) -> dict | None:
    try:
        response = await client.get(url)
        soup = BeautifulSoup(response.text, "html.parser")

        # remove nav, footer, scripts — get cleaner body text
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        return {
            "url": url,
            "title": soup.title.text.strip() if soup.title else "No title",
            "body_text": soup.get_text(separator=" ", strip=True)[:3000],
            "source": url,
        }
    except Exception as e:
        print(f"✗ Failed to fetch article: {url} — {e}")
        return None


async def scraper_node(state: AgentState) -> dict:
    init_url_store()

    source_urls = state["urls"]
    raw_articles = []

    async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
        for source_url in source_urls:
            try:
                print(f"📡 Fetching feed: {source_url}")
                response = await client.get(source_url)
                article_urls = extract_article_urls(response.text, source_url)
                article_urls = article_urls[:2] # just for testing get first two links 
                print(f"  Found {len(article_urls)} articles in feed")

                for article_url in article_urls:
                    if is_seen(article_url):
                        print(f"  ⏭ Skipped (seen): {article_url[:80]}")
                        continue

                    article = await fetch_article(client, article_url)
                    if article:
                        raw_articles.append(article)
                        print(f"  ✓ Scraped: {article['title'][:60]}")

            except Exception as e:
                print(f"✗ Failed to fetch feed: {source_url} — {e}")

    mark_seen([a["url"] for a in raw_articles])
    print(f"\n  Total new articles scraped: {len(raw_articles)}")
    return {"raw_articles": raw_articles}