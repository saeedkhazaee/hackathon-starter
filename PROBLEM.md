# The problem: rescue an inefficient document pipeline

**NetGreener AI Efficiency Challenge — Build Smarter. Waste Less.**

You have **60 minutes**, working individually or as a team, to reduce the resources
used by an existing application while preserving its required behavior. Use
NetGreener to investigate the application's resource use and your preferred AI coding
assistant to help investigate and improve it. Your responsibility is to direct the
agent, assess its suggestions and verify what changes actually achieve.

## The business scenario

A company receives invoices, purchase orders, receipts and contracts. Its operations
team needs each document classified, its fields extracted, and its amounts or dates
checked. Valid documents must produce usable results. Invalid documents must produce
clear failures, and an incomplete document must be able to recover when a valid
updated version becomes available.

The company uses **DocFlow Rescue** for this work. The pipeline runs, but some batches
consume unexpectedly large amounts of processing resources. Work can take a long
time without producing useful progress. The team needs evidence explaining where
resources are being spent and changes that reduce waste without losing results.

Your task is to investigate the supplied implementation, identify the causes, and
demonstrate a measured improvement. A long-running document is not automatically
wasteful: a large legitimate input may require substantial work.

## What you are given

The starter includes a local Python application, CLI and HTTP API, synthetic sample
documents, public correctness tests, and a reproducible benchmark. A trained local
machine-learning model classifies documents. Deterministic rules handle structured
fields and validation; Azure OpenAI interprets organization names and dates in prose
for eight documents. Temporary Azure configuration is supplied privately. The React
workspace shows document progress and provider-reported request/token usage.

The full benchmark processes **40 documents**. Its expected outcome is **37 successful
documents and three legitimate arithmetic failures**. An aggregate job marked failed
can therefore be correct; the successful document results must remain available.
Those counts alone are not sufficient proof of correctness.

The core workload uses structured text and digital PDFs. Optional PNG OCR has separate
prerequisites. Supported formats and behavior are defined in the
[document contract](docs/DOCUMENT_FORMAT.md).

## Your mission

1. **Connect.** Start with the [official NetGreener website](https://www.netgreener.com).
   Discover its documentation and developer tools, then integrate monitoring into
   this application. The starter does not include a completed integration.
2. **Observe.** Run the full workload with monitoring enabled. Inspect the resulting
   NetGreener dashboard evidence for runtime and external requests alongside the application's job status, attempts,
   stages, errors and results. The API exposes these through its
   [local interactive documentation](http://127.0.0.1:8002/docs).
3. **Investigate.** Use a specific NetGreener observation to form a hypothesis, then
   connect it to actual application behavior. Direct your coding agent to examine the
   relevant path. Explain which work is necessary and which work fails to contribute
   useful progress; do not treat the agent's explanation as proof.
4. **Optimize.** Change the permitted application implementation to address the causes
   you identified. Preserve all required processing and safety behavior.
5. **Verify.** Run correctness checks and repeat the same instrumented workload under
   comparable conditions. Show that resource use improved and required results remain
   correct, including on changed inputs.

Use the dashboard and application evidence together. An editor screenshot does not
prove a resource improvement, and a lower resource number does not prove correctness.
Automatic stuck-job detection and automatic fixes are not promised features of this
challenge.

## Working with a coding agent

Your agent may generate all implementation code. Judges evaluate the team's
understanding, decisions and verified outcomes; manual coding, longer prompts, larger
diffs and expensive models receive no extra credit.

Capture three consequential decisions during the challenge. For each, record the
observation, your question to the agent, the suggestion you accepted, revised or
rejected, your reason, and the evidence used to check it. Link to a run, application
trace, test result or code diff. Full chat histories are not required. Report decisions
honestly; you do not need to invent a disagreement with your agent.

Be ready to explain the evidence and one way your improvement could fail. The application
combines local processing with real language-model requests. It has no autonomous
agent or MCP workflow. Application attempts and Python function calls must not be
presented as observed AI tool-call telemetry.

## What a successful solution preserves

- Classification, extracted fields, calculations and source references.
- Clear terminal failures for invalid documents and recovery when later source
  versions supply valid content.
- Correct handling of changed content and a result for each submitted document ID,
  including IDs that share the same content.
- Accurate job and attempt records, cancellation, bounded execution and safety limits.

Do not obtain a better score by reducing the workload, skipping required stages,
hardcoding answers, changing protected controls or disabling monitoring. The public
tests help you check your work; judges also evaluate unseen inputs.

## What you must prove

Provide a reproducible before/after comparison using at least three fresh-process
trials for each version. Keep the workload, host, runtime, packages, monitoring,
concurrency and cache conditions comparable. If a measurement condition changes,
collect a new matching baseline.

The rubric is Innovation (25%), Efficiency (40%), Impact (20%) and Presentation (15%).
Efficiency considers verified CPU improvement, external inference efficiency and
eliminated unnecessary work. The numerical allocation is announced before the event.

CPU scoring uses NetGreener-attributed CPU for `POST /jobs`, with matching measurement
scope and provenance. You must prove that the measured scope includes the actual
processing worker. Moving work to an unmeasured process is not an optimization. Local
CPU and wall time provide supporting evidence. Compare actual outbound request and
token measurements with Azure response usage. Any cost estimate must identify its
rates and coverage; a dashboard zero does not prove free inference. This exercise
does not establish physical energy, carbon or water savings. Correctness, trustworthy
measurements and worker coverage must pass before Efficiency points or winner
eligibility are awarded. See [RULES.md](RULES.md) for the exact gates.

Submit your repository and final commit, reproduction steps, test results, real
NetGreener run evidence, three decision records, and an explanation connecting your
observations to your changes. After the coding deadline, demonstrate your work in
three minutes and answer two minutes of jury questions. The goal is **less resource
use for the same required work**.

See [QUICKSTART.md](QUICKSTART.md) for setup, [CHALLENGE.md](CHALLENGE.md) for the
suggested schedule, [RULES.md](RULES.md) for protected files and scoring, and
[SUBMISSION.md](SUBMISSION.md) for the submission checklist.
