import logging
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from incidentlens.config import get_settings
from incidentlens.detection import detect_incidents
from incidentlens.schemas import EventBatch, EventIn, IngestResult
from incidentlens.storage import EventStore

logger = logging.getLogger("incidentlens")


def get_store(request: Request) -> EventStore:
    return request.app.state.store


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logging.basicConfig(level=settings.log_level.upper())
    app.state.settings = settings
    app.state.store = EventStore(settings.database_path)
    app.state.store.initialize()
    logger.info("storage initialized")
    yield


app = FastAPI(
    title="IncidentLens API",
    description="Local-first incident investigation with evidence-backed reports.",
    version="0.1.0",
    lifespan=lifespan,
)


@app.exception_handler(Exception)
async def unexpected_exception_handler(request: Request, exc: Exception):
    logger.exception("unhandled error on %s", request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/health", tags=["operations"])
def health():
    return {"status": "ok", "service": "incidentlens"}


@app.get("/ready", tags=["operations"])
def ready(store: Annotated[EventStore, Depends(get_store)]):
    try:
        count = store.get_event_count()
    except Exception as exc:
        logger.warning("readiness check failed: %s", type(exc).__name__)
        raise HTTPException(status_code=503, detail="Storage unavailable") from exc
    return {"status": "ready", "storage": "ok", "event_count": count}


def check_batch_size(request: Request, count: int):
    if count > request.app.state.settings.max_batch_size:
        raise HTTPException(status_code=413, detail="Batch exceeds configured limit")


@app.post("/v1/events", response_model=IngestResult, status_code=201, tags=["events"])
def ingest_event(event: EventIn, store: Annotated[EventStore, Depends(get_store)]):
    records = store.insert_many([event])
    return IngestResult(accepted=len(records), event_ids=[record.id for record in records])


@app.post("/v1/events/batch", response_model=IngestResult, status_code=201, tags=["events"])
def ingest_batch(
    payload: EventBatch, request: Request, store: Annotated[EventStore, Depends(get_store)]
):
    check_batch_size(request, len(payload.events))
    records = store.insert_many(payload.events)
    return IngestResult(accepted=len(records), event_ids=[record.id for record in records])


@app.get("/v1/events", tags=["events"])
def list_events(
    store: Annotated[EventStore, Depends(get_store)],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    service: Annotated[str | None, Query(max_length=120)] = None,
):
    return store.list_events(limit=limit, service=service)


@app.get("/v1/incidents", tags=["incidents"])
def list_incidents(
    store: Annotated[EventStore, Depends(get_store)],
    limit: Annotated[int, Query(ge=1, le=500)] = 200,
):
    return detect_incidents(store.list_events(limit=limit))


@app.get("/v1/incidents/{incident_id}", tags=["incidents"])
def get_incident(incident_id: str, store: Annotated[EventStore, Depends(get_store)]):
    for report in detect_incidents(store.list_events(limit=500)):
        if report.id == incident_id:
            return report
    raise HTTPException(status_code=404, detail="Incident not found")
