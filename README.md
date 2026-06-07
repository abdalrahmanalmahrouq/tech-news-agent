# 🤖 AI News Agent

An autonomous multi-agent pipeline that scrapes Hacker News, summarizes articles with an LLM, verifies headlines against the web, and delivers a curated tech digest to subscribers every day at **07:00 UTC** — fully automated, no human intervention required.

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-multi--agent-7C3AED)
![FastAPI](https://img.shields.io/badge/FastAPI-service-009688)
![Docker](https://img.shields.io/badge/Docker-containerized-2496ED?logo=docker&logoColor=white)
![AWS](https://img.shields.io/badge/AWS-ECR%20%2B%20EC2-FF9900?logo=amazonaws&logoColor=white)
![LangSmith](https://img.shields.io/badge/LangSmith-observability-1C1C1C)

![Landing Page](images/ui.png)

---

## Table of Contents

- [Overview](#overview)
- [Results](#results)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Models](#models)
- [Observability](#observability)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
- [API Endpoints](#api-endpoints)
- [CI/CD Pipeline](#cicd-pipeline)
- [Screenshots](#screenshots)

---

## Overview

AI News Agent is a production-grade GenAI system built to demonstrate real-world multi-agent architecture using LangGraph. It solves the information overload problem for engineers: instead of manually scanning dozens of tech sources every morning, a pipeline of specialised agents does the reading, evaluating, and writing — then drops a clean briefing into your inbox.

**What makes it interesting architecturally:**

- **Multi-agent LangGraph pipeline** — 8 nodes with typed state, a conditional retry edge, and a persistent SQLite checkpoint per run
- **ReAct agent inside a pipeline node** — the Reader node runs a `create_react_agent` loop with two custom tools (`summarize_article`, `score_relevance`) as children of the outer graph
- **Three persistence layers** — subscriber store, seen-URL deduplication (7-day window), and run logs — all SQLite, mounted as a Docker volume so data survives redeployment
- **Proper service architecture** — fire-and-poll FastAPI endpoints, APScheduler cron job, background task isolation, unified `run_id` across HTTP layer, checkpointer, and run logs
- **Full observability stack** — LangSmith auto-instruments every LLM call; loguru provides structured, leveled logs to both terminal and rotating file

---

## Results

The pipeline runs autonomously. Here is what a real run looks like end to end.

### Structured log output (terminal / loguru)

Every stage produces a structured, timestamped log line with the correct severity level. The final line shows the full run summary in one place: run ID, duration, scraped, validated, rejected.

![Terminal run](images/runterminal.png)

### Delivered email digest (Gmail)

The formatter builds an email-safe HTML email with inline styles, sorted by relevance score. The delivery node broadcasts it to all active subscribers via Gmail SMTP.

![Gmail digest](images/gmailmessage.png)

---

## Tech Stack

| Layer | Technology |
|---|---|
| Agent framework | LangGraph (StateGraph, conditional edges, AsyncSqliteSaver checkpointing) |
| LLM client | LangChain + OpenRouter |
| LLM model | xiaomi/MiMo-V2-Flash |
| ReAct agent | `langgraph.prebuilt.create_react_agent` |
| Web scraping | httpx (async, follow_redirects) + BeautifulSoup4 + lxml |
| Fact verification | Tavily API |
| API layer | FastAPI + Pydantic |
| Scheduler | APScheduler 3.x (AsyncIOScheduler + CronTrigger) |
| Logging | loguru (structured, leveled, daily-rotating file sink) |
| Observability | LangSmith |
| Persistence | SQLite × 3 — subscribers, run logs, seen-URL store |
| Checkpointing | AsyncSqliteSaver (LangGraph) |
| Email | Python smtplib + Gmail SMTP (port 465, SMTP_SSL) |
| Frontend | React 18 (browser-compiled via Babel CDN), served from FastAPI StaticFiles |
| Containerisation | Docker + Docker Compose |
| Image registry | AWS Elastic Container Registry (ECR) |
| Compute | AWS EC2 (Ubuntu, t3.micro, eu-north-1) |
| CI/CD | GitHub Actions |
| Package manager | uv |

---

## Architecture

The pipeline is a directed LangGraph `StateGraph` with 8 nodes. All nodes share a single typed `AgentState` dict. The Validator has the only conditional edge: it routes to `formatter` on success and back to `reader` on quality failure (capped at 2 retries).

![Pipeline architecture](images/pipeline_architecture.svg)

### Node responsibilities

| Node | Role | Key detail |
|---|---|---|
| **Orchestrator** | Pre-flight check, run_meta init | Reads `run_id` seeded by `run_pipeline()` — the same id used as `thread_id` and HTTP status key |
| **Scraper** | RSS fetch → URL dedup → page scrape | `asyncio.gather` + `asyncio.Semaphore(5)` for concurrent I/O; 7-day seen-URL dedup |
| **Reader** | Summarise + score each article | `create_react_agent` ReAct loop with `summarize_article` and `score_relevance` tools; `asyncio.gather` across articles |
| **Verifier** | Fact-check headlines | Tavily web search per headline; `asyncio.to_thread` wraps the sync client; defaults to `verified=True` on API failure |
| **Validator** | Quality gate + routing | Rejects on low score, short summary, missing fields, or unverified headline; `routing_function` drives the conditional edge |
| **Formatter** | HTML digest builder | Pure Python — no LLM in the formatter. Sorts by relevance score, renders email-safe inline-style HTML |
| **Delivery** | Archive + email broadcast | Writes digest to `data/digests/{run_id}_{timestamp}.html`; sends one email per active subscriber |

### State flow

```
run_pipeline(urls, run_id)
│
├── seeds run_id into initial_state["run_meta"]
├── sets config = {"configurable": {"thread_id": run_id}}
│
└── ainvoke → StateGraph
    │
    ├─ orchestrator   reads run_id from state, adds started_at / status
    ├─ scraper        appends raw_articles to state
    ├─ reader         appends summaries (concurrent ReAct loops)
    ├─ verifier       mutates summaries in-place (verified, sources_found)
    ├─ validator ──┐  mutates validated; routing_function decides edge
    │              └─ retry → reader  (if quality failure, retry_count < 2)
    ├─ formatter      writes digest HTML string to state
    └─ delivery       writes delivered_to list to run_meta
```

---

## Models

All LLM calls are routed through **OpenRouter**, which provides a unified API across dozens of models with per-call billing and detailed request logs.

**Model in use:** `xiaomi/MiMo-V2-Flash`

MiMo-V2-Flash is a fast, cost-efficient model from Xiaomi optimised for reasoning and tool use — well-suited for the structured JSON outputs required by the ReAct tools and the agent's final response. At ~120–185 tok/s and sub-cent cost per article, it makes the daily run economically viable at scale.

### OpenRouter request logs

Each pipeline run generates multiple individual LLM calls. The Reader's ReAct loop accounts for the majority: roughly 5 calls per article (2 reasoning steps, 2 tool-internal calls, 1 final assembly). The logs below show finish reasons (`stop` for direct responses, `tool_calls` for tool invocations), per-call token counts, and real-time throughput.

![OpenRouter logs](images/openrouterlogs.png)

---

## Observability

### LangSmith tracing

LangSmith is wired via three environment variables — no code changes required. Because the pipeline uses LangChain and LangGraph, every LLM call, tool invocation, and graph node is automatically captured as a nested span with input, output, token counts, latency, and cost.

The trace view makes the ReAct loop structure directly visible: the Reader node contains a `react_agent` span, which contains individual `summarize_article` and `score_relevance` tool spans, each with their own internal LLM call underneath.

![LangSmith traces](images/langsmith.png)

**Key metrics from the dashboard:**

| Metric | Range observed |
|---|---|
| End-to-end latency | 7s (0 new articles) → 121s (heavy run) |
| Tokens per run | 2,800 → 39,600 |
| Cost per run | $0.0003 → $0.005 |
| Error rate | 0% across all logged runs |

> **Note on token counts:** LangSmith aggregates tokens at every level of the span hierarchy, which leads to apparent double-counting at the project level. Per-trace root figures are the accurate reference. OpenRouter's billing logs are the ground truth for actual cost.

### Structured logging (loguru)

Every node emits a structured log line at the appropriate severity level. Log levels are semantic: `DEBUG` for skipped (seen) URLs, `INFO` for successful operations, `WARNING` for rejections and missing configs, `ERROR` for failed fetches or email failures.

A file sink with daily rotation and 7-day retention is added at the service entry point (`api.py`), so all logs from all nodes are captured in `data/logs/agent.log` without any configuration in the nodes themselves.

```
2026-06-07 17:34:40 | INFO  | agent.orchestrator | ▶ Run e991441f started
2026-06-07 17:34:41 | INFO  | agent.scraper      | 📡 Fetching feed: https://hnrss.org/frontpage
2026-06-07 17:34:43 | INFO  | agent.scraper      | ✓ Scraped: Founding Engineer at Proliferate | Y Combinator
2026-06-07 17:34:50 | INFO  | agent.reader       | ✓ Summarized: Founding Engineer at Proliferate | Y Combinator
2026-06-07 17:34:52 | INFO  | agent.verifier     | ✓ Verified (5 sources): Proliferate Seeks Founding Engineer
2026-06-07 17:34:52 | INFO  | agent.validator    | ✓ Validated: Proliferate Seeks Founding Engineer for AI OS Role
2026-06-07 17:34:52 | INFO  | agent.delivery     | ✓ Email sent to abdalrahmanadnan209@gmail.com
2026-06-07 17:34:55 | INFO  | run_logger         | 📊 Run complete | run_id=e991441f | duration=15436ms | scraped=2 | validated=2 | rejected=0
```

---

## Project Structure

```
tech-news-agent/
├── src/
│   └── agent/
│       ├── api.py                  # FastAPI app + APScheduler lifespan + /run /status /subscribe
│       ├── graph.py                # LangGraph pipeline + run_pipeline() entry point
│       ├── state.py                # AgentState TypedDict
│       ├── orchestrator.py         # Node: pre-flight, run_meta init
│       ├── scraper.py              # Node: RSS fetch, URL dedup, async page scraping
│       ├── reader.py               # Node: ReAct agent with summarize + score tools
│       ├── verifier.py             # Node: Tavily headline verification
│       ├── validator.py            # Node: quality gate + routing_function
│       ├── formater.py             # Node: email-safe HTML digest builder
│       ├── delivery.py             # Node: file archive + SMTP broadcast
│       ├── llm.py                  # OpenRouter LLM config via LangChain
│       ├── static/                 # React landing page (served from FastAPI)
│       │   ├── index.html
│       │   ├── app.jsx
│       │   ├── styles.css
│       │   └── tweaks-panel.jsx
│       └── persistence/
│           ├── subscriber_store.py # SQLite subscriber table
│           ├── url_store.py        # SQLite seen-URL dedup (7-day window)
│           ├── run_logger.py       # SQLite run logs
│           └── checkpointer.py    # DB path resolver for AsyncSqliteSaver
├── data/                           # volume-mounted on EC2 — survives redeployment
│   ├── digests/                    # archived HTML digests per run
│   ├── logs/                       # loguru rotating log files
│   ├── news_agent.db               # subscribers + run logs + seen URLs
│   └── checkpoints.db              # LangGraph per-run checkpoints
├── docs/
│   ├── screenshots/
│   ├── pipeline_architecture.svg
│   └── cicd_pipeline.svg
├── .github/
│   └── workflows/
│       └── deploy.yml              # GitHub Actions CI/CD
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── pyproject.toml
```

---

## Quick Start

### Prerequisites

- [uv](https://docs.astral.sh/uv/) installed
- [Docker](https://docs.docker.com/get-docker/) installed
- API keys for: OpenRouter, LangSmith, Tavily
- Gmail account with an [app password](https://myaccount.google.com/apppasswords)

### 1. Clone and configure

```bash
git clone https://github.com/abdalrahmanalmahrouq/tech-news-agent
cd tech-news-agent
cp .env.example .env
```

Fill in `.env`:

```env
# LLM routing
OPENROUTER_API_KEY=sk-or-...

# Observability
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=lsv2_...
LANGSMITH_PROJECT=tech-news-agent

# Fact verification
TAVILY_API_KEY=tvly-...

# Email delivery
SMTP_HOST=smtp.gmail.com
SMTP_PORT=465
SMTP_USER=you@gmail.com
SMTP_PASS=your-app-password
EMAIL_FROM=you@gmail.com
```

### 2. Run with Docker (recommended)

```bash
mkdir -p data
docker compose up --build
```

The service starts at `http://localhost:8000`. The landing page is served at `/`, the API at `/run`, `/status/{run_id}`, and `/subscribe`.

### 3. Run a pipeline manually

```bash
# via API (fire-and-poll)
curl -X POST http://localhost:8000/run
# → {"run_id": "a1b2c3d4", "status": "started"}

curl http://localhost:8000/status/a1b2c3d4
# → {"run_id": "a1b2c3d4", "status": "completed", "scraped": 3, "validated": 2, ...}

# via CLI
cd src
uv run python -m agent.graph
```

### 4. Add a subscriber

```bash
curl -X POST http://localhost:8000/subscribe \
  -H "Content-Type: application/json" \
  -d '{"name": "Your Name", "email": "you@example.com"}'
```

Or use the landing page form at `http://localhost:8000`.

### Scheduled runs

APScheduler fires automatically at **07:00 UTC daily** when the server is running. No cron job or external trigger needed — the scheduler starts inside the FastAPI lifespan context.

---

## API Endpoints

| Method | Endpoint | Description | Auth |
|---|---|---|---|
| `GET` | `/` | Landing page (HTML) | None |
| `GET` | `/health` | Health check → `{"ok": true}` | None |
| `POST` | `/run` | Start a pipeline run in the background → `{"run_id": "...", "status": "started"}` | None |
| `GET` | `/status/{run_id}` | Poll run status → `{"status": "running" \| "completed" \| "failed", ...}` | None |
| `POST` | `/subscribe` | Save subscriber → `{"status": "subscribed", "email": "..."}` | None |

### Fire-and-poll pattern

`POST /run` returns immediately. The pipeline runs as a FastAPI `BackgroundTask`. Poll `GET /status/{run_id}` until you see `"completed"`. The `run_id` returned by the HTTP layer is identical to the `thread_id` used by the LangGraph checkpointer and the `run_id` written to `run_logs` — one id traces the run across all three systems.

---

## CI/CD Pipeline

Every push to `main` triggers a GitHub Actions workflow that builds the Docker image, pushes it to AWS ECR, SSHes into the EC2 instance, pulls the new image, and restarts the container — all without manual intervention.

![CI/CD pipeline](images/cicd_pipeline.svg)

### Workflow summary

```yaml
# .github/workflows/deploy.yml
on:
  push:
    branches: [main]
  workflow_dispatch:        # manual trigger button in GitHub UI
```

| Step | Runs on | What it does |
|---|---|---|
| Checkout | GitHub runner | Clones the repo onto the runner |
| Configure AWS credentials | GitHub runner | Authenticates with IAM user `tech-news-agent-dev` |
| ECR login | GitHub runner | Authenticates Docker with the ECR registry |
| Build + push | GitHub runner | `docker build` → `docker push` to ECR |
| SSH deploy | EC2 instance | ECR login (via IAM role) → `docker compose pull` → `docker compose up -d` |

**GitHub Secrets required:**

| Secret | Description |
|---|---|
| `AWS_ACCESS_KEY_ID` | IAM user access key |
| `AWS_SECRET_ACCESS_KEY` | IAM user secret key |
| `EC2_HOST` | EC2 public IP address |
| `EC2_SSH_KEY` | Full contents of the `.pem` private key file |

Use `[skip ci]` in a commit message to push without triggering a deployment.

---

## Screenshots

### Landing page (live on EC2)

![Landing page](images/ui.png)

### Pipeline run — structured log output

![Terminal run](images/runterminal.png)

### Delivered email digest

![Gmail digest](images/gmailmessage.png)

### LangSmith observability dashboard

![LangSmith](images/langsmith.png)

### OpenRouter model call logs

![OpenRouter](images/openrouterlogs.png)

---

<!-- ## What's next

- APScheduler trigger strategy: domain-based scheduling (weekdays only, skip if 0 new articles)
- Multi-source expansion: add TechCrunch, Ars Technica, HuggingFace blog feeds alongside HN
- Retry logic refinement: retry only on quality failures (short summary, missing fields), not on editorial score
- PostgreSQL migration: replace SQLite when concurrency or horizontal scaling becomes a requirement
- Domain + HTTPS: Route 53 A record + Nginx reverse proxy + Let's Encrypt certificate
- Unsubscribe link: one-click unsubscribe token in email footer -->

---

<p align="center">Built with LangGraph · OpenRouter · FastAPI · Docker · AWS</p>
