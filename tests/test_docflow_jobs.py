import threading
import time
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from docflow.api import app
from docflow.jobs import JobStore, Busy, process_batch
from docflow.models import Batch, SourceVersion
from docflow.workload import text_document, business_text, make_workload


def test_transient_source_recovers_and_hash_tracks_used_version():
    doc = text_document("a", "source still uploading", ready=False)
    doc.versions.append(SourceVersion(text=business_text("invoice", 912)))
    record = process_batch(Batch(documents=[doc]))["documents"][0]
    assert record["status"] == "completed"
    assert record["attempt"] == 2
    assert record["attempts"][0]["error"]["code"] == "source_pending"
    assert record["attempts"][0]["content_hash"] != record["content_hash"]
    assert record["result"]["fields"]["invoice_number"] == "INV-912"


def test_new_version_after_invalid_snapshot_must_be_considered():
    doc = text_document("a", business_text("invoice", discrepancy=1))
    doc.versions.append(SourceVersion(text=business_text("invoice")))
    record = process_batch(Batch(documents=[doc]))["documents"][0]
    assert record["status"] == "completed"
    assert record["attempt"] == 2


def test_retrying_document_does_not_starve_other_documents():
    bad = text_document("a", business_text("invoice"), ready=False)
    bad.versions.append(SourceVersion(text=business_text("invoice")))
    good = text_document("b", business_text("receipt"))
    records = process_batch(Batch(documents=[bad, good]))["documents"]
    assert records[1]["status"] == "completed"
    assert records[1]["completed_at"] < records[0]["completed_at"]
    ids = [a["attempt_id"] for r in records for a in r["attempts"]]
    assert len(ids) == len(set(ids))


def test_cancel_and_deadline_release_lane():
    batch = make_workload(rows=2)
    for cancelled in (True, False):
        store = JobStore()
        job = store.submit(batch)
        if cancelled:
            store.cancel(job)
        store.run(job, batch, seconds=0 if not cancelled else 90)
        state = store.snapshot(job)
        assert state["status"] == ("cancelled" if cancelled else "failed")
        assert all(d["completed_at"] for d in state["documents"])
        assert store.lane.locked() is False


def test_running_cancel_and_concurrency_limit():
    store = JobStore()
    batch = make_workload(rows=5000)
    job = store.submit(batch)
    with pytest.raises(Busy):
        store.submit(batch)
    thread = threading.Thread(target=store.run, args=(job, batch))
    thread.start()
    deadline = time.monotonic() + 3
    while store.snapshot(job)["status"] == "pending" and time.monotonic() < deadline:
        time.sleep(0.005)
    store.cancel(job)
    thread.join(timeout=3)
    assert not thread.is_alive()
    assert store.snapshot(job)["status"] == "cancelled"
    assert not store.lane.locked()


def test_input_caps_and_duplicate_ids():
    with pytest.raises(ValidationError):
        SourceVersion(content_base64="not base64!")
    with pytest.raises(ValidationError):
        SourceVersion(text="x", content_base64="eA==")
    doc = text_document("a", business_text())
    with pytest.raises(ValidationError):
        Batch(documents=[doc, doc])
    with pytest.raises(ValidationError):
        Batch(documents=[])
    with pytest.raises(ValidationError):
        SourceVersion(text="x" * 4_000_001)


def test_api_lifecycle_and_single_document():
    batch = make_workload(rows=2)
    with TestClient(app) as client:
        assert client.get("/health").json()["processing_lanes"] == 1
        assert client.get("/jobs/missing").status_code == 404
        assert client.post("/jobs", json={"documents": []}).status_code == 422
        submitted = client.post("/jobs", json=batch.model_dump())
        assert submitted.status_code == 202
        job = submitted.json()["job_id"]
        state = client.get(f"/jobs/{job}/status").json()
        assert state["status"] == "failed"
        assert all("result" not in d for d in state["documents"])
        result = client.get(f"/jobs/{job}/results").json()
        assert sum(d["status"] == "completed" for d in result["documents"]) == 37
        response = client.post("/documents/process", json=batch.documents[0].model_dump())
        assert response.json()["status"] == "completed"
