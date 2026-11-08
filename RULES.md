# Rules and judging

The coding period is 60 minutes. Individuals and teams share one leaderboard.
Suggested team size is 2–4, with no enforced limit and no team-size points. Solo
entrants count as one-person teams. Submit one repository and one final commit per
entry. There is one overall winning team, with no separate category winners.

## AI-assisted work

Coding agents may write all implementation code. Teams remain responsible for
choosing what to investigate, assessing suggestions and verifying the final behavior.
There is no penalty for extensive AI assistance and no extra credit for manual
typing, code volume, prompt length, model price or the number of agent calls.

Submit three consequential decision records and identify the AI tools/models used
where known. Full chat histories are not required. Each record must connect an
observation, a question to the agent, its suggestion, the team's decision and a
concrete check. Accepted, revised and rejected suggestions are all valid; do not
fabricate a rejection. Judging evaluates the team's understanding rather than
attempting to infer each person's contribution from the final code.

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
inputs, return hardcoded answers, falsify uploads, or suppress valid recovery.

Judges execute trusted controls and unseen workloads outside the submission checkout.
Entries receive equivalent checks for changed inputs, required failure/recovery
behavior and measurement coverage. The three mandatory gates are:

- **Correctness:** all essential checks pass; required outputs and lifecycle behavior
  are preserved, including legitimate failures.
- **Measurement validity:** real NetGreener evidence and reproducible comparisons
  use matching workload, environment, scope and attribution provenance.
- **Worker coverage:** the scored measurement includes the actual document-processing
  work throughout execution. A `process_tree` label alone does not establish coverage
  of a separate worker or container. Independent execution evidence must corroborate it.

Failing any gate earns zero Efficiency points and makes the entry ineligible to win.
Judges may provide feedback on the other criteria. Partial correctness is not a
tradeoff that can be compensated by a lower CPU number.

## Scoring

| Criterion | Points | Assessment |
|---|---:|---|
| Innovation | 25 | 15 for solution design and justified tradeoffs; 10 for evidence-led investigation, hypotheses and critical assessment of agent suggestions |
| Efficiency | 40 | Verified local CPU improvement, external inference efficiency, and demonstrated elimination of unnecessary work |
| Impact | 20 | 10 for demonstrated operational value through useful throughput, responsiveness or reliability; 10 for applicability, limitations and operational tradeoffs |
| Presentation | 15 | 5 for explaining the problem and decisions; 5 for demonstrating evidence and improvement; 5 for reproducibility and answering questions |

Small, effective changes can earn full Innovation points. Extra features and larger
diffs are not inherently innovative. Impact claims must be supported; hypothetical
scale, financial savings or environmental benefits are not measured results.

The organizer will announce the fixed numerical allocation within Efficiency before
the competition. The four official criterion weights above remain unchanged.

Native CPU means NetGreener's attributed `POST /jobs` CPU with the same measurement
scope and provenance in both runs. It is an allocated process-window estimate, not
physical energy consumption. Use three or more fresh-process trials per version,
the same full 40-document workload, hardware, runtime, package versions, concurrency
and cache conditions. Baseline CPU must be positive. Missing, nonfinite, negative,
incompatible or unverifiable measurements are invalid.

The scored scope remains the validated `POST /jobs` processing path. If an
architecture change moves work outside that scope, the lower endpoint value is not
eligible for scoring. Do not substitute a different metric or sum incompatible
measurements. A provenance change requires a new comparable baseline and verified
coverage before judges can accept it.

Evidence of eliminated unnecessary work is assessed on the following dimensions:

- Identifying specific avoidable work and explaining why it is unnecessary.
- Reproducible before/after execution evidence showing that work was reduced.
- Showing that the reduction preserves required work and behavior on
  relevant changed or recovery inputs.

Evidence may include application attempts or verified function-call counts, clearly
labeled by source and connected to the NetGreener investigation. Counts alone do not
prove waste or CPU savings. The starter makes real Azure inference requests but has no MCP or autonomous-agent
workflow; ordinary Python function calls must not be described as observed AI tool calls. Automatic stuck-job
alerts are not a judging prerequisite or a promised feature.

Independent process CPU and wall duration corroborate native telemetry; they do not
replace it. External API evidence must reconcile real outbound requests and tokens with provider
usage. Keep the same deployment, reasoning effort, output limit, prompt and schema
contract between scored runs. Required prose interpretation must still occur; do not
replace it with hardcoded fixture answers or bypass the required language stage.
Cost estimates must identify rates and missing coverage; they are not invoices.
Memory, GPU, physical energy, carbon and water reductions are not scored resource
metrics for this challenge. Use the same organizer hardware when possible. Local
benchmark JSON never awards native efficiency points by itself. Judges confirm
participant evidence through controlled execution and authenticated native records.

## Jury and presentations

The jury consists of one representative from HUMAN IP, one from iA7 and one from
NetGreener. Technical validation establishes the gates and shared resource score
before final judging. Each representative scores all four criteria using the same
rubric and that resource score. The final result is the average of the three totals;
the NetGreener representative can explain telemetry provenance to the panel.

Presentations follow the coding deadline: three minutes for a demonstration and two
minutes for questions. Teams explain the evidence that guided their investigation
and how a seemingly successful improvement could be wrong, plus a change-specific
question where time permits. The spokesperson answers in their own words without
live agent-generated answers. Judges assess understanding, not speaking confidence.
Any shortlist and presentation arrangements are announced before the event and use
the published rubric.

Ties are resolved by average Efficiency points, then Impact, then Innovation. If
still tied, the three jurors select one winner by majority vote using the published
rubric. Team size and commit time are not tie-breakers. No ineligible entry can win;
if no entry passes the gates, the jury will report that outcome rather than waive them.

## Submission handling

Commit before the 60-minute deadline and record the full SHA. Freeze code, decision
records and submission evidence at that deadline. The presentation period does not
permit further code changes.

Invalid benchmark data receives no Efficiency points unless judges can establish a
valid comparison from the frozen submission. Failed telemetry uploads must be
disclosed with their times and local evidence. Organizer-verified service outages
may receive a measurement-only extension for all affected entrants using the frozen
deadline commit; no code changes. Judges may rerun that commit for validation.
Organizers announce the submission channel, cutoff timezone and any outage extension
consistently before judging.

## Prizes

- Winning team: one year of NetGreener access.
- Every participant: two months of NetGreener access.

The included plan, usage allowance, activation date and whether the winning-team
prize covers each member or a shared subscription will be announced before the event.
