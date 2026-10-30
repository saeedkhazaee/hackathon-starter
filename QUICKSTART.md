# Run DocFlow Rescue

Prepare CPython **3.14.10**, Git and your editor before the event. This exact runtime
and the checked-in dependency lock were tested on Windows. Check `py -3.14 --version`.
The bootstrap refuses a different patch version to avoid silent benchmark differences.
No large AI model download, Redis, Docker, paid API or GPU is required.

```powershell
py -3.14 scripts/bootstrap.py
.\.venv\Scripts\python.exe -m docflow
.\.venv\Scripts\python.exe -m pytest -q
```

Bootstrap creates a fresh `.venv`, installs the hash-locked application/test packages,
and checks dependencies. Use a fresh clone/environment for the challenge. Do not reuse
a development environment containing unrelated packages. On other platforms the Python
path is `.venv/bin/python`; those platforms have not been tested for this event.

## Try documents

```powershell
.\.venv\Scripts\python.exe -m docflow data/documents/invoice.txt
.\.venv\Scripts\python.exe -m docflow data/documents/contract.pdf
.\.venv\Scripts\python.exe -m docflow --export .runtime/inbox.json
```

The last command exports the small inbox. Add `--workload` for the full benchmark-sized
inbox. All examples use synthetic data and integer cents. For PNG scans, install
Tesseract with English language data before the timer and make `tesseract` available
on PATH. Then run `python -m docflow data/documents/contract_scan.png` using the venv.
An optional 40-document workload with a real scanned contract is available as
`python -m docflow --batch data/fixtures/ocr_workload.json`. It preserves the same
37-success/3-failure contract and requires Tesseract.

Without Tesseract, a scan returns `ocr_unavailable`; it is never treated as extracted
text. The optional scan test is skipped when the binary is absent. Core judging uses
the text/PDF workload; organizer-declared OCR judging uses the same OCR setup for both runs.

## API and job progress

```powershell
.\.venv\Scripts\python.exe -m uvicorn docflow.api:app --host 127.0.0.1 --port 8000 --workers 1 --timeout-graceful-shutdown 15
```

Open http://127.0.0.1:8000/docs. `POST /documents/process` processes a single document.
`POST /jobs` accepts a batch and returns a job ID while its background task runs.
Inspect `/jobs/{job_id}/status`, then `/jobs/{job_id}/results`. Request cancellation
with `POST /jobs/{job_id}/cancel`. A second simultaneous submission returns HTTP 409.
Jobs live in memory; the last eight are retained. Restarting the server clears them.
Use one Uvicorn worker because the registry is process-local. Stop with Ctrl+C.
The job deadline is 90 seconds, OCR calls are limited to ten seconds, and benchmark
children have a hard 120-second process timeout. Cancellation is checked between
stages and during table parsing. This is a local synthetic-document service, not a
hardened public upload endpoint.

## Measure

First discover and integrate NetGreener through its official website and your coding
assistant. Collect real telemetry for both baseline and optimized runs.

```powershell
.\.venv\Scripts\python.exe benchmark.py run --label observed --output .runtime/baseline.json
# After changes, using exactly the same monitoring configuration:
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe benchmark.py run --label observed --output .runtime/optimized.json
.\.venv\Scripts\python.exe benchmark.py compare .runtime/baseline.json .runtime/optimized.json
```

The label records your configuration name; it does not install monitoring or certify
that telemetry exists. Each run uses three fresh processes. Allow roughly 1â€“2 minutes
for a full baseline set on the tested host. Keep the machine idle and preserve the
JSON reports. CLI benchmarks use the same API/background pipeline via TestClient,
which waits for background work to finish. Interactive HTTP returns acceptance sooner.

If a job hits a budget, keep that failure as evidence and investigate. Do not raise
safety bounds, modify controls, or omit difficult documents to obtain a score. For a
quick development smoke only, `benchmark.py run --rows 10 ...` is available; reduced
workloads are not final submissions.
