"""A bounded in-memory job registry with one processing lane."""
from collections import deque
from copy import deepcopy
from datetime import datetime, timezone
import threading
import uuid
from .models import content_hash
from .pipeline import process
from .inference import InferenceSession, ProviderError
from .safety import Budget, MAX_ATTEMPTS, ProcessingError, Stopped


def now():
    return datetime.now(timezone.utc).isoformat()


class Busy(Exception):
    pass


class JobStore:
    def __init__(self):
        self.lock = threading.RLock()
        self.lane = threading.Lock()
        self.jobs = {}
        self.cancellations = {}
        self.closed = False

    def submit(self, batch):
        with self.lock:
            if self.closed or not self.lane.acquire(blocking=False):
                raise Busy("One job is already running or the service is shutting down")
            while len(self.jobs) >= 8:
                oldest = next(iter(self.jobs))
                del self.jobs[oldest]
                del self.cancellations[oldest]
            job_id = uuid.uuid4().hex
            self.cancellations[job_id] = threading.Event()
            self.jobs[job_id] = {"job_id": job_id, "status": "pending", "started_at": None,
                                 "completed_at": None, "operations": 0, "documents": [],
                                 "ai_usage": {"requests": 0, "responses_with_usage": 0, "errors": 0,
                                    "input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "cached_tokens": 0}}
            for document in batch.documents:
                self.jobs[job_id]["documents"].append({"document_id": document.document_id,
                    "status": "pending", "stage": "pending", "attempt": 0,
                    "content_hash": content_hash(document.versions[0].bytes()), "started_at": None,
                    "completed_at": None, "attempts": [], "error": None, "result": None})
            return job_id

    def snapshot(self, job_id, include_results=False):
        with self.lock:
            job = self.jobs[job_id]
            result = {k: deepcopy(v) for k, v in job.items() if k != "documents"}
            result["documents"] = [{k: deepcopy(v) for k, v in doc.items()
                                    if include_results or k != "result"} for doc in job["documents"]]
            return result

    def cancel(self, job_id):
        with self.lock:
            if self.jobs[job_id]["status"] in {"pending", "processing"}:
                self.cancellations[job_id].set()
            return self.snapshot(job_id)

    def close(self):
        with self.lock:
            self.closed = True
            for event in self.cancellations.values():
                event.set()

    def run(self, job_id, batch, seconds=90):
        budget = Budget(self.cancellations[job_id], seconds=seconds)
        inference = InferenceSession(job_id)
        with self.lock:
            job = self.jobs[job_id]
            job.update(status="processing", started_at=now())
        queue = deque(enumerate(batch.documents))
        stop_error = None
        try:
            while queue:
                budget.check()
                index, document = queue.popleft()
                with self.lock:
                    record = job["documents"][index]
                    record["attempt"] += 1
                    version = document.version(record["attempt"])
                    digest = content_hash(version.bytes())
                    attempt = {"attempt_id": f"{job_id}:{document.document_id}:{record['attempt']}",
                               "number": record["attempt"], "content_hash": digest, "started_at": now(),
                               "completed_at": None, "status": "processing", "checkpoints": [], "error": None}
                    record["attempts"].append(attempt)
                    record.update(status="processing", content_hash=digest, error=None)
                    record["started_at"] = record["started_at"] or attempt["started_at"]

                def checkpoint(stage, **details):
                    # Preserve received usage even if cancellation arrived in flight.
                    if stage not in {"ai_response", "ai_error"}:
                        budget.check()
                    with self.lock:
                        record["stage"] = stage
                        attempt["checkpoints"].append({"stage": stage, "at": now(), **details})
                        if stage == "ai_request":
                            job["ai_usage"]["requests"] += 1
                        elif stage == "ai_error":
                            job["ai_usage"]["errors"] += 1
                        elif stage == "ai_response":
                            job["ai_usage"]["responses_with_usage"] += 1
                            for metric in ("input_tokens", "output_tokens", "total_tokens", "cached_tokens"):
                                job["ai_usage"][metric] += details.get(metric) or 0

                try:
                    output = process(version, budget, checkpoint, inference)
                except Stopped:
                    raise
                except ProcessingError as exc:
                    with self.lock:
                        error = {"code": exc.code, "message": str(exc)}
                        attempt.update(status="failed", error=error, completed_at=now())
                        record["error"] = error
                        if record["attempt"] < MAX_ATTEMPTS and (not isinstance(exc, ProviderError) or exc.retryable):
                            record["status"] = "retrying"
                            queue.append((index, document))
                        else:
                            record.update(status="failed", completed_at=now())
                else:
                    with self.lock:
                        attempt.update(status="completed", completed_at=now())
                        record.update(status="completed", result=output, error=None, completed_at=now())
        except Stopped as exc:
            stop_error = {"code": exc.code, "message": str(exc)}
        except Exception:
            # Preserve terminal lifecycle on unexpected defects; surface the defect.
            stop_error = {"code": "internal_error", "message": "Unexpected processing failure"}
            raise
        finally:
            with self.lock:
                if stop_error:
                    for record in job["documents"]:
                        if record["status"] not in {"completed", "failed"}:
                            state = "cancelled" if stop_error["code"] == "cancelled" else "failed"
                            record.update(status=state, error=stop_error, completed_at=now())
                            if record["attempts"] and record["attempts"][-1]["status"] == "processing":
                                record["attempts"][-1].update(status=state, error=stop_error, completed_at=now())
                job["status"] = ("cancelled" if stop_error and stop_error["code"] == "cancelled"
                                 else "failed" if any(d["status"] != "completed" for d in job["documents"])
                                 else "completed")
                job.update(completed_at=now(), operations=budget.operations)
                self.lane.release()
            inference.close()


def process_batch(batch):
    store = JobStore()
    job_id = store.submit(batch)
    store.run(job_id, batch)
    return store.snapshot(job_id, include_results=True)


def meaningful_results(job):
    """Correctness contract: exclude incidental time, IDs and implementation counts."""
    return [{"document_id": d["document_id"], "status": d["status"],
             "content_hash": d["content_hash"], "error": d["error"], "result": d["result"]}
            for d in job["documents"]]
