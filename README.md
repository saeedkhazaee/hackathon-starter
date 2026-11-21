#C4Cool

C is a cool programming language. If you object on this claim, I'd love to hear from you.

# NetGreener AI Efficiency Challenge

**Rescue the Runaway AI Pipeline** · **Build Smarter. Waste Less.**

Blockchain & AI Summit · Montreal · November 20, 2026 · **60 minutes**

DocFlow Rescue processes synthetic invoices, purchase orders, receipts and contracts.
It classifies documents with a trained local multinomial Naive Bayes model, extracts
structured fields, checks amounts and dates, and records jobs, attempts and results.
Eight documents also require Azure OpenAI to interpret prose. The rest use local
processing. The organizer privately supplies temporary access to `gpt-5-mini`.

Your company’s document pipeline works, but some workloads consume unexpectedly large
amounts of resources. Investigate with NetGreener, identify the causes, improve the
implementation using your preferred AI coding assistant, and prove the same required
work still completes correctly.

**Connect → Observe → Investigate → Optimize → Verify**

Read [the problem statement](PROBLEM.md) for the scenario, required behavior and
evidence you need to demonstrate an improvement.

## First mission

Your first task is to integrate NetGreener into this application. Visit the
[official NetGreener website](https://www.netgreener.com), explore its developer
packages and documentation, and use your preferred AI coding assistant to connect
NetGreener to this project. The starter has no installed or configured integration.
Prepare your own account/project access before the timed event; never share personal
login credentials or tokens. For team access, use organizer-provisioned permissions.

## Start

Use the official template to create **one public repository** for yourself or your
team, clone it, then follow [QUICKSTART.md](QUICKSTART.md).

```powershell
py -3.14 scripts/bootstrap.py
# Put the organizer-supplied .env at the repository root.
.\.venv\Scripts\python.exe -m docflow --check-azure-config
.\.venv\Scripts\python.exe -m docflow
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m uvicorn docflow.api:app --host 127.0.0.1 --port 8002 --workers 1 --timeout-graceful-shutdown 15
```

Open [API documentation](http://127.0.0.1:8002/docs). The CLI and API use the same
pipeline. The small demo processes 40 documents, with 37 successful results and
three documented arithmetic failures. Demo and benchmark runs make paid Azure requests
using the supplied temporary resource. Offline tests make no paid calls. A failed document is a legitimate result;
reporting it as successfully processed would be incorrect.

For the React document workspace, keep the backend running and open another terminal:

```powershell
cd frontend
npm ci
npm run dev
```

Open **http://127.0.0.1:5173** for the competition workflow: integrate NetGreener,
click **Run baseline**, optimize, click **Run optimized benchmark**, then **Compare results**.
The supplied workload is included; no document uploads are needed. Optional document
exploration is available in a separate expandable section.
Node.js 22.12 or later is required. See [QUICKSTART.md](QUICKSTART.md)
for setup and the distinction between interactive runs and scored benchmarks.

```powershell
.\.venv\Scripts\python.exe benchmark.py run --label local --output .runtime/local.json
```

After integrating monitoring, collect an instrumented baseline and repeat the same
workload after optimizing. Use the same measurement label, runtime, host, packages,
concurrency and cache policy. The benchmark records three fresh-process trials and
independent CPU/wall time; judges verify actual NetGreener evidence separately.
Never compare an uninstrumented baseline with an instrumented optimized run.

## Documents and scope

UTF-8 business exchange documents and digital PDFs work out of the box. Small text
and two-page PDF examples are in `data/documents`. Optional PNG OCR uses a separately
installed Tesseract executable; a synthetic scanned contract is included. The timed
core workload does not require OCR installation. If your declared environment supports
OCR, preserve it. Arbitrary layouts, handwriting and image-only PDFs are outside scope.
See [document contract](docs/DOCUMENT_FORMAT.md) for exact fields and limits.

## Participation and judging

Individuals and teams use the same starter, tools, 60-minute limit, correctness gate
and leaderboard. Suggested team size is 2–4; it is not enforced. Roles are optional:
integration/telemetry, pipeline investigation, job processing, and verification.

| Criterion | Weight |
|---|---:|
| Innovation | 25% |
| Efficiency | 40% |
| Impact | 20% |
| Presentation | 15% |

Coding agents may write all of your code. You are responsible for directing the
investigation, checking suggestions and proving the result. Judges evaluate your
decisions and evidence, not manual typing, code volume, prompt length or model price.
Record three consequential decisions as you work.

Correctness, trustworthy measurements and coverage of the actual processing worker
are mandatory gates. Failing a gate earns zero Efficiency points and makes an entry
ineligible to win. Efficiency considers verified local CPU improvement, external
inference efficiency and elimination of unnecessary work. The organizer announces
the fixed numerical allocation before the timer starts. Team size earns no points.

The jury comprises one representative each from **HUMAN IP**, **iA7** and
**NetGreener**. There is **one overall winning team**; solo entrants count as
one-person teams for judging. Presentations take place after the coding deadline:
three minutes for the demonstration and two minutes for questions.

**Prizes:** one year of NetGreener access for the winning team; two months of access
for every participant. The included plan, usage allowance, activation date and
whether the winning-team prize covers each member or a shared subscription will be
announced before the event.

See [RULES.md](RULES.md), [CHALLENGE.md](CHALLENGE.md), and
[SUBMISSION.md](SUBMISSION.md). Submit one repository and one final evidence set.

Source is MIT licensed. Third-party licenses and optional OCR requirements are in
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). Windows is the tested platform;
macOS/Linux execution and the hosted template workflow remain unverified.
