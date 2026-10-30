# Rules and judging

The event is 60 minutes. Individuals and teams share one leaderboard. Suggested team
size is 2–4, with no enforced limit and no team-size points. AI coding assistants are
permitted. Submit one repository and one final commit per entrant.

## Correctness and controls

Preserve required processing stages, extracted fields, classification, arithmetic,
source references, documented failures, legitimate source recovery and lifecycle
semantics. Changed inputs must change outputs correctly. Duplicate content with
different document IDs still produces a result for each submission. Incidental
UUIDs, timestamps, retry counts and operation counts may change when behavior remains
correct. Never fabricate progress, success, calls or telemetry.

Do not change `benchmark.py`, `docflow/workload.py`, `docflow/models.py`,
`docflow/safety.py`, datasets, tests or judging controls. Application implementation
changes and participant-added monitoring are allowed. Preserve dependencies and
monitoring configuration between compared runs; if they change, rerun the baseline.
Do not disable monitoring, remove required OCR in an OCR-enabled evaluation, alter
inputs, return hardcoded answers, falsify uploads, or suppress valid retries.
Judges execute trusted controls and hidden workloads outside the submission checkout.

## Scoring

| Criterion | Points | Assessment |
|---|---:|---|
| Resource efficiency | 40 | Formula below, only after essential correctness passes |
| Application correctness | 25 | 15 fields/classification, 5 failures/recovery, 5 lifecycle/input isolation |
| Effective use of NetGreener | 20 | 5 integration, 5 real evidence, 5 evidence-based investigation, 5 verification |
| Results and explanation | 15 | 5 reproducible comparison, 5 justified changes, 5 clear complete submission |

All essential tests must pass for any efficiency points. Judges calculate:

`efficiency = 40 × clamp(1 − median_native_CPU_after / median_native_CPU_before, 0, 1)`

Native CPU means NetGreener's attributed `POST /jobs` CPU with the same measurement
scope and provenance in both runs. It is an allocated process-window estimate, not
physical energy consumption. Use three or more fresh-process trials, the same full
40-document workload, hardware, runtime, package versions, concurrency and cache
conditions. Baseline must have positive native CPU. Reject missing, nonfinite,
negative, incompatible or unverifiable measurements. A provenance change requires
remeasurement; it cannot earn points. Independent process CPU and wall duration are
corroborating evidence, not substitutes for native telemetry. Attempts and operation
counts aid investigation but are not independent efficiency metrics.

Do not score memory, GPU, token/cost, physical energy, carbon or water reductions.
Use the same organizer hardware when possible. Local benchmark JSON never awards
native efficiency points by itself. Scores from untrusted participant files must be
confirmed through controlled execution and authenticated native evidence.

## Submission handling

Commit before the 60-minute deadline and record the commit SHA. Ties are resolved by
correctness points, then NetGreener-use points, then explanation points; remaining
exact ties share rank. Team size and commit time are not tie-breakers.

Invalid benchmark data receives no efficiency points until judges can reproduce a
valid comparison. Failed telemetry uploads must be disclosed with their times and
local evidence. Organizer-verified service outages may receive a measurement-only
extension for all affected entrants using the frozen deadline commit; no code changes.
An incomplete submission is scored only on verifiable evidence and must still pass
the correctness gate for efficiency points. Organizers announce submission channel,
cutoff timezone and any outage extension consistently before judging.
