import uuid
from loguru import logger
from contextlib import asynccontextmanager
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from agent.graph import run_pipeline
from agent.persistence.subscriber_store import add_subscriber
from apscheduler.triggers.cron import CronTrigger
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta
from apscheduler.triggers.date import DateTrigger
# Feeds used when /run is triggered. (You can accept these from the request later.)
DEFAULT_FEEDS = ["https://hnrss.org/frontpage"]

# Live status board: run_id -> {"status": ...}. In memory only — resets on restart.
RUNS: dict[str, dict] = {}



class SubscriberRequest(BaseModel):
    name: str
    email: str 


async def run_and_track(run_id: str, urls: list[str]) -> None:
    """Background wrapper: run the pipeline and record its status in RUNS."""
    RUNS[run_id] = {"status": "running"}
    logger.info("Background task started | run_id={}", run_id)
    try:
        final_state = await run_pipeline(urls, run_id=run_id)
        run_meta = final_state.get("run_meta", {})
        RUNS[run_id] = {
            "status": "completed",
            "scraped": len(final_state.get("raw_articles", [])),
            "validated": len(final_state.get("validated", [])),
            "delivered_to": run_meta.get("delivered_to", []),
        }
        logger.info("Run completed | run_id={} | validated={}", run_id, RUNS[run_id]["validated"])
    except Exception as e:
        RUNS[run_id] = {"status": "failed", "error": str(e)}
        logger.error("Run failed | run_id={} | error={}", run_id, e)

async def scheduled_run():
    """Called by APScheduler daily at 07:00 UTC."""
    run_id = str(uuid.uuid4())[:8]
    logger.info("Scheduled run triggered | run_id={}", run_id)
    await run_and_track(run_id, DEFAULT_FEEDS)

@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = AsyncIOScheduler()
    # scheduler.add_job(
    #     scheduled_run,
    #     CronTrigger(hour=7, minute=0, timezone="UTC"),
    #     id="daily_digest",
    #     name="Daily digest - 07:00 UTC "
    # )
    scheduler.add_job(
    scheduled_run,
    DateTrigger(run_date=datetime.utcnow() + timedelta(minutes=2)),
    id="daily_digest",
)
    scheduler.start()
    logger.info("Scheduler started - daily run at 07:00 UTC")
    yield
    scheduler.shutdown()
    logger.info("Scheduler stopped")

app = FastAPI(title="AI News Agent", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

logger.add("../data/logs/agent.log", rotation="1 day", retention="7 days", level="INFO")


@app.get("/")
async def root():
    return {"ok": True, "service": "AI News Agent"}


@app.post("/run")
async def trigger_run(background_tasks: BackgroundTasks):
    """Start a pipeline run in the background; return a run_id immediately."""
    run_id = str(uuid.uuid4())[:8]
    RUNS[run_id] = {"status": "running"}
    background_tasks.add_task(run_and_track, run_id, DEFAULT_FEEDS)
    logger.info("Run triggered | run_id={}", run_id)
    return {"run_id": run_id, "status": "started"}


@app.get("/status/{run_id}")
async def get_status(run_id: str):
    """Report the status of a run by its run_id."""
    if run_id not in RUNS:
        raise HTTPException(status_code=404, detail="run_id not found")
    return {"run_id": run_id, **RUNS[run_id]}

@app.post("/subscribe")
async def subscribe(request: SubscriberRequest):
    if not request.email.strip() or not request.name.strip():
        raise HTTPException(status_code=400, detail="Name and email are required")
    try:
        add_subscriber(request.email.strip(), request.name.strip())
        logger.info("New Subscriber: {} <{}>", request.name, request.email )
        return {"status": "subscribed", "email": request.email}
    except Exception as e :
        logger.error("Subcriber failed for {} - {}", request.email, e)
        raise HTTPException(status_code=500, detail="Failed to save subscriber")