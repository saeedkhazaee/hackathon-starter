# Submit one result

Before the 60-minute deadline, push the final commit to your individual or team public
repository. Record its full SHA and send one submission through the organizer-announced
channel. The organizer must announce that channel before the event starts.

Include:

- Repository URL, final commit SHA, participant names and whether individual or team.
- Reproduction commands, Python/package versions, host description, cache/concurrency
  conditions, workload hash and all trial reports.
- Passing public tests and any declared OCR prerequisites.
- Real NetGreener before/after run links or organizer-accessible exports, with CPU
  attribution provenance. Both runs must use the same instrumentation and workload.
- A concise explanation connecting observed behavior to your hypothesis, changes and
  verification. Identify manual inferences separately from actual product alerts.
- Failures, limitations, and any upload outage details.
- Three consequential decision records using the template below, plus the AI tools
  and models used where known. Full chat histories are not required.
- Evidence that monitoring includes the actual processing worker, including any
  worker/thread/process changes. An endpoint response or a scope label alone is not proof.
- The practical benefit, relevant failure or recovery checks, and limits of your approach.

## Decision record template

Include three short records in your submission, for example in `DECISIONS.md`:

```text
Decision 1: [short title]
Observation: [what we saw; identify NetGreener evidence or application evidence]
Question to the agent: [the specific hypothesis or investigation request]
Agent suggestion: [what it proposed]
Team decision: [accepted, revised or rejected; explain why]
Verification: [what check we ran, its actual result and any remaining uncertainty]
Evidence: [run link/export, trace, test result or code diff]
```

Record decisions while working and commit them before the deadline. All suggestions
may be accepted if justified; do not invent a rejected suggestion. Agents may help
prepare the records, but the team must check their accuracy and be able to explain
them. Neither lengthy prompts nor large amounts of generated code earn extra credit.

## Presentation and questions

After the coding period, prepare a three-minute demonstration of the observation,
hypothesis, targeted change and verified result, followed by two minutes of questions.
Use the frozen submission and its evidence. Presentation preparation does not permit
changing code or adding new decision records after the deadline.

Be ready to explain what evidence directed your investigation and what could make
your improvement appear successful while being wrong. Answer in your own words
without a live agent generating answers. The jury evaluates the team's understanding,
not individual typing effort or speaking confidence.

## Evidence and evaluation

Do not include personal tokens, login credentials, account configuration, private
supplier information or unrelated dashboard data. Give judges access through supported
project permissions; never share a personal login. Screenshots supplement run evidence
but do not establish correctness or comparability by themselves.

Keep the final repository intact. Judges run independent hidden documents and trusted
benchmark controls. Explain any dependency or monitoring changes that required a new
baseline. The same submission format and scoring apply to individuals and teams.

Scoring is Innovation (25%), Efficiency (40%), Impact (20%) and Presentation (15%).
Correctness, measurement validity and worker coverage are mandatory gates for
Efficiency points and winner eligibility. See [RULES.md](RULES.md) for the complete
rubric and [CHALLENGE.md](CHALLENGE.md) for the event workflow.
