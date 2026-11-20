# Run DocFlow Rescue

Prepare CPython **3.14.10**, Git and your editor before the event. This exact runtime
and the checked-in dependency lock were tested on Windows. Check `py -3.14 --version`.
The bootstrap refuses a different patch version to avoid silent benchmark differences.
If the Python launcher cannot find your installed runtime, invoke the Python 3.14.10
executable directly with `scripts/bootstrap.py`.
No large model download, Redis, Docker or GPU is required. Azure inference uses
the dedicated temporary resource; obtain the organizer-supplied `.env` before running
the demo or benchmark. Dependencies, Node, account access and Azure configuration
should be ready before the timed competition.

```powershell
py -3.14 scripts/bootstrap.py
# Save the privately supplied configuration as .env in this folder.
.\.venv\Scripts\python.exe -m docflow --check-azure-config
.\.venv\Scripts\python.exe -m docflow
.\.venv\Scripts\python.exe -m pytest -q
```

Bootstrap creates a fresh `.venv`, installs the hash-locked application/test packages,
and checks dependencies. Use a fresh clone/environment for the challenge. Do not reuse
a development environment containing unrelated packages. On other platforms the Python
path is `.venv/bin/python`; those platforms have not been tested for this event.

## React document workspace

Install Node.js 22.12 or later before the event (tested with Node.js 22.12.0 and
npm 10.9.0). Keep two terminals open at the repository root.

Terminal 1 starts the backend:

```powershell
.\.venv\Scripts\python.exe -m uvicorn docflow.api:app --host 127.0.0.1 --port 8002 --workers 1 --timeout-graceful-shutdown 15
```

Terminal 2 starts React:

```powershell
cd frontend
npm ci
npm run dev
```

Open **http://127.0.0.1:5173**. The competition screen uses the supplied workload;
participants do not need to upload documents.

1. Integrate NetGreener and confirm telemetry covers the actual processing workers
   in the benchmark's fresh processes, not only the web server.
2. Click **Run baseline** before optimizing. It runs the full 40-document workload
   in three fresh processes and saves the report.
3. Investigate with NetGreener, optimize the permitted application code, and run
   `.\.venv\Scripts\python.exe -m pytest -q`. Restart the backend after code changes.
4. Click **Run optimized benchmark**, then **Compare results**. Download both reports
   and the comparison, and attach real NetGreener evidence separately.

Each trial expects 37 successes and 3 legitimate arithmetic failures. Benchmarks make
paid Azure requests and can take several minutes. Keep the machine idle. The UI
shows completed trials; saved reports survive backend restarts under
`.runtime/competition/`. A new baseline clears the current optimized comparison;
older report files remain on disk. An interrupted run must be repeated.

The UI invokes the unchanged `benchmark.py` runner. Its workers call the API through
TestClient; they do not send processing requests to the running Uvicorn server.
Monitoring installed only around the Uvicorn launch will not automatically cover
these workers. Verify actual worker coverage before collecting scored evidence.
The CLI below remains available for reproduction and detailed diagnosis.

**Explore the pipeline** is optional and separate from scoring. Expand it to run
small demo documents, inspect processing attempts and source references, or test
custom supported-format TXT, digital PDF, PNG, or inbox JSON files. PNG OCR requires
Tesseract. Exploration demos also make paid Azure requests. Document jobs are blocked
while a benchmark is running. Close other browser tabs and avoid unrelated traffic
during controlled trials. Local timing reports alone do not establish scoring eligibility.

Vite forwards `/api` requests to the local backend; no CORS configuration or browser
API key is needed. Keep Azure credentials only in the root `.env`, never in frontend
source or a `VITE_` variable. There is no monitoring integration in this frontend.
To check the production bundle, run `npm run build` in `frontend`; `npm run preview`
serves that bundle on the same frontend port and still needs the backend running.
Stop the development server before previewing on that port. Press Ctrl+C in each
terminal to stop its server.

## Temporary Azure configuration

Place the organizer-supplied shared configuration in `.env` at the repository root.
For your own setup, copy `.env.example` to `.env` and fill in the supplied endpoint,
deployment name and key. The loader uses `python-dotenv`, preserves the endpoint
hostname, and does not expand variables inside credential values. Existing
`AZURE_OPENAI_BASE_URL` and `AZURE_OPENAI_MODEL` settings are also accepted.
Keep `.env` private; it is ignored by Git. Do not paste it into submissions or logs.

Check configuration without sending a request:

```powershell
.\.venv\Scripts\python.exe -m docflow --check-azure-config
```

The application uses the OpenAI Responses client against the supplied Azure v1
endpoint and deployment. Structured documents run locally; documents containing a
`Narrative:` section make real, paid inference requests. Both browser samples and
the default CLI workload include eight such documents. Requests have a 20-second
timeout, no hidden SDK retries, a 1,024-output-token cap and bounded application
retries. The deployment uses minimal reasoning. Do not change these measurement
conditions between baseline and optimized runs.

After the event, delete your local `.env`; the organizer will delete the dedicated
Azure resource to revoke shared access. No credential belongs in Git or a browser bundle.

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
.\.venv\Scripts\python.exe -m uvicorn docflow.api:app --host 127.0.0.1 --port 8002 --workers 1 --timeout-graceful-shutdown 15
```

Open http://127.0.0.1:8002/docs. `POST /documents/process` processes a single document.
`POST /jobs` accepts a batch and returns a job ID while its background task runs.
Inspect `/jobs/{job_id}/status`, then `/jobs/{job_id}/results`. Request cancellation
with `POST /jobs/{job_id}/cancel`. A second simultaneous submission returns HTTP 409.
Jobs live in memory; the last eight are retained. Restarting the server clears them.
Use one Uvicorn worker because the registry is process-local. Stop with Ctrl+C.
The job deadline is 90 seconds, OCR calls are limited to ten seconds, and benchmark
children have a hard 120-second process timeout. Cancellation is checked between
stages, during table parsing and during retry backoff. An in-flight inference request
may finish before cancellation takes effect, bounded by its request timeout. This is a local synthetic-document service, not a
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
that telemetry exists. Each run uses three fresh processes. Reserve up to 8 minutes for all six official trials, uploads and comparison.
Latency and shared quota contention vary; run the baseline early. Keep the machine idle and preserve the
JSON reports. CLI benchmarks use the same API/background pipeline via TestClient,
which waits for background work to finish. Interactive HTTP returns acceptance sooner.

If a job hits a budget, keep that failure as evidence and investigate. Do not raise
safety bounds, modify controls, or omit difficult documents to obtain a score. For a
quick development smoke only, `benchmark.py run --rows 10 ...` is available; reduced
workloads are not final submissions.

Public tests use offline provider responses and never call Azure. They do not prove
live compatibility. A successful live workload and authenticated telemetry supply that
evidence. Optional OCR fixtures are a separate local exercise, not a replacement for
the official hybrid workload.
