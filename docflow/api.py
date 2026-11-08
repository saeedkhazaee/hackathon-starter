"""Local document API. Run one Uvicorn worker; the registry is process-local."""
from contextlib import asynccontextmanager
from fastapi import FastAPI, BackgroundTasks, HTTPException
from .jobs import JobStore, Busy
from .models import Batch, Document
from typing import Literal

store = JobStore()


@asynccontextmanager
async def lifespan(app):
    global store
    store = JobStore()
    yield
    store.close()


app = FastAPI(title="DocFlow Rescue", version="1.0.0", lifespan=lifespan)


class BodyLimit:
    """Reject large bodies before JSON deserialization, including chunked requests."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] != "POST":
            return await self.app(scope, receive, send)
        messages, size = [], 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            size += len(message.get("body", b""))
            if size > 48_000_000:
                await send({"type": "http.response.start", "status": 413,
                            "headers": [(b"content-type", b"application/json")]})
                await send({"type": "http.response.body", "body": b'{"detail":"Request exceeds 48 MB"}'})
                return
            messages.append(message)
            if not message.get("more_body", False):
                break
        async def replay():
            return messages.pop(0) if messages else await receive()
        await self.app(scope, replay, send)


app.add_middleware(BodyLimit)


def submit(batch):
    try:
        return store.submit(batch)
    except Busy as exc:
        raise HTTPException(409, str(exc)) from exc


def lookup(job_id, results=False):
    try:
        return store.snapshot(job_id, include_results=results)
    except KeyError as exc:
        raise HTTPException(404, "Job not found; jobs expire after eight newer jobs or server restart") from exc


@app.get("/health")
def health():
    import shutil
    from .config import ConfigurationError, load_azure_settings
    try:
        load_azure_settings()
        configured = True
    except ConfigurationError:
        configured = False
    return {"status": "ok", "application": "DocFlow Rescue", "paid_api_required": True,
            "azure_configured": configured,
            "ocr_available": bool(shutil.which("tesseract")), "processing_lanes": 1}


@app.post("/documents/process")
def single(document: Document):
    batch = Batch(documents=[document])
    job_id = submit(batch)
    store.run(job_id, batch)
    return lookup(job_id, True)


@app.get("/samples/{size}")
def sample_batch(size: Literal["demo", "full"]):
    """Synthetic inboxes for the browser; the full benchmark controls stay unchanged."""
    from .workload import make_workload
    return make_workload(rows=10 if size == "demo" else 25_000, language_assisted=True)


@app.post("/jobs", status_code=202)
def create_job(batch: Batch, background_tasks: BackgroundTasks):
    job_id = submit(batch)
    background_tasks.add_task(store.run, job_id, batch)
    return {"job_id": job_id, "status": "pending"}


@app.get("/jobs/{job_id}")
@app.get("/jobs/{job_id}/status")
def status(job_id: str):
    return lookup(job_id)


@app.get("/jobs/{job_id}/results")
def results(job_id: str):
    return lookup(job_id, True)


@app.post("/jobs/{job_id}/cancel")
def cancel(job_id: str):
    lookup(job_id)
    return store.cancel(job_id)
