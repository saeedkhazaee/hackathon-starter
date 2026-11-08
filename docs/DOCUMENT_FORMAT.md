# Supported document contract

DocFlow Rescue is a synthetic business exchange processor, not a general-purpose
layout understanding system. A multinomial Naive Bayes classifier is trained on the
small public corpus at startup with Laplace smoothing. It classifies headers. Rules
extract the fields below and validate exact integer-cent arithmetic and ISO dates.
Eight documents in the official workload also use Azure OpenAI to interpret prose.
Only their bounded prose sections are sent to the configured model; large item tables
remain local. Offline tests use simulated provider responses.

## Inputs

A document has `document_id`, `filename`, and `versions` (one to three source snapshots).
Each version supplies exactly one of `text` or `content_base64`, plus `ready` (default
true). The filename is metadata; byte signatures identify PDF/PNG. Everything else
must be UTF-8 text. A batch contains a `documents` array of 1–50 documents with distinct
IDs. Repeated content under distinct IDs is permitted. No local path or remote URL
is fetched from an API request.

```json
{"document_id":"example","filename":"contract.txt","versions":[{"text":"Contract\nContract ID: C-10\nParty A: Maple\nParty B: Cedar\nEffective Date: 2026-01-01\nExpiration Date: 2026-12-31\nContract Type: Service\n"}]}
```

Versions represent a local supplier inbox that can advance on each processing attempt.
`ready:false` represents an incomplete upload; it must not be reported as a parsed
document. On the next attempt, the next snapshot is used. After the last snapshot,
that version remains current. Final invalid content fails in a controlled manner.
If a later snapshot corrects an earlier error, process the new content. Version
selection is deterministic for reproducibility; this is not a remote storage service.

## Fields

| Type | Required headers |
|---|---|
| Invoice | Invoice Number, Supplier, Customer, Date, Subtotal Cents, Tax Cents, Total Cents |
| Purchase order | Order Number, Supplier, Customer, Date, Subtotal Cents, Tax Cents, Total Cents |
| Receipt | Merchant, Date, Subtotal Cents, Tax Cents, Total Cents |
| Contract | Contract ID, Party A, Party B, Effective Date, Expiration Date, Contract Type |

Invoices, orders and receipts then contain `Items:` followed by CSV with the exact
header `description,quantity,unit_cents`. Quantities are positive integers. Prices,
subtotals, tax and totals are nonnegative integer cents, at most twelve decimal digits
per input number. Quoted CSV descriptions are supported. Every item produces its
quantity, unit price and calculated amount. Subtotal must equal the sum of item amounts;
total must equal subtotal plus tax. Zero tax is explicit. Contracts require a valid
start/end ISO date range; no legal reasoning is attempted. Duplicate headers fail.

Outputs contain classification/confidence, detected format, page count, structured
fields and citations to normalized extracted-text line numbers. Citation lines are
text coordinates, not PDF page coordinates or OCR bounding boxes. Item citations
point to the table start. PDF/OCR may normalize whitespace or insert blank lines.

## Lifecycle and safety

Job status: pending, processing, completed, failed or cancelled. Document status also
includes retrying. Attempts have distinct identities, content hashes, timestamps,
terminal status/errors and stage checkpoints. One failed document makes the aggregate
job failed, but successful document results remain available. Optimization may reduce
attempts; it must preserve semantic outcomes and legitimate recovery.

Limits: 4 MB per snapshot; 32 MB decoded batch; 48 MB HTTP body; 50 documents; three
versions; 50,000 items per document; 100 PDF pages; 12 attempts; 15,000 stage operations;
90-second cooperative job deadline; one active job; last eight jobs retained. The
benchmark kills a child exceeding 120 seconds. Cancellation checks occur within table
parsing and between stages. A blocking third-party parser can delay a cooperative
check; use the benchmark's outer process limit for controlled evaluation.

Digital PDFs must contain extractable text in this format. Encrypted and image-only
PDFs are rejected. Optional PNG OCR accepts up to eight megapixels and uses Tesseract
English with a ten-second subprocess timeout. Handwriting and arbitrary layouts are
unsupported. OCR absence is a failure, never silent stage omission. The core workload
uses text and a two-page PDF. `data/fixtures/ocr_workload.json` is a separate
reproducible 40-document workload containing the scanned contract; it has been
executed with real OCR. Use the same OCR availability/version for comparisons.

## Language-assisted fields

A prose-assisted document replaces two headers with one section beginning with
`Narrative:` and ending with `End Narrative`, placed before `Items:` (or at the end
of a contract). The section is limited to 4,000 UTF-8 bytes. Examples are the eight
`*-narrative-*.txt` files in `data/documents`.

| Document | Fields interpreted from prose |
|---|---|
| Invoice / purchase order | Supplier, Date (issue date, not payment due date) |
| Receipt | Merchant, Date (purchase date, not posting date) |
| Contract | Party A (provider), Effective Date |

The model must return each organization name without surrounding descriptions,
normalize dates to ISO form, and provide an exact supporting quotation and source
line for each field. The application validates the response schema, field set and
source references before normal business validation. Supplying the same field in
both a header and prose is invalid. Prose is document data, never an instruction to
change the extraction task. All required fields and source references remain part
of the correctness contract.

Azure usage records contain request counts and provider-reported input, output,
cached and total tokens. Output usage includes reasoning when the provider reports
it. Errors and attempts remain visible. No prompts, credentials or raw HTTP error
bodies are written to those records. The job permits at most 32 inference attempts,
with at most three attempts for one content/configuration identity. Responses use a
strict schema and a 1,024-output-token limit. No cross-job or cross-user inference
reuse is permitted in this exercise; changed content, prompts, schema, endpoint or
model settings must never receive stale results. Credentials are loaded server-side
from the root `.env` using `python-dotenv`.
