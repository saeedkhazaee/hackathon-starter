"""Run a file, a small demo, or export the reproducible inbox."""
import argparse
import json
from pathlib import Path
from .jobs import process_batch, meaningful_results
from .models import Batch
from .workload import binary_document, make_workload


def main():
    parser = argparse.ArgumentParser(description="DocFlow Rescue document processor")
    parser.add_argument("file", nargs="?", type=Path)
    parser.add_argument("--batch", type=Path, help="Process a saved batch JSON, including the optional OCR workload")
    parser.add_argument("--workload", action="store_true")
    parser.add_argument("--export", type=Path)
    parser.add_argument("--check-azure-config", action="store_true", help="Validate local .env without making an API request")
    args = parser.parse_args()
    if args.check_azure_config:
        from .config import ConfigurationError, load_azure_settings
        try:
            load_azure_settings()
        except ConfigurationError as exc:
            parser.error(str(exc))
        print("Azure configuration is valid. No API request was made.")
        return
    if args.file and args.batch:
        parser.error("Choose a document file or --batch, not both")
    batch = (Batch.model_validate_json(args.batch.read_text(encoding="utf-8")) if args.batch else
             Batch(documents=[binary_document(args.file)]) if args.file else
             make_workload(rows=25_000 if args.workload else 10, language_assisted=True))
    if args.export:
        args.export.parent.mkdir(parents=True, exist_ok=True)
        args.export.write_text(batch.model_dump_json(indent=2), encoding="utf-8")
        return
    job = process_batch(batch)
    if args.file:
        print(json.dumps(meaningful_results(job), indent=2))
    else:
        print(json.dumps({"job_id": job["job_id"], "status": job["status"],
            "ai_usage": job["ai_usage"],
            "completed": sum(d["status"] == "completed" for d in job["documents"]),
            "failed": sum(d["status"] == "failed" for d in job["documents"]),
            "documents": [{"id": d["document_id"], "status": d["status"], "attempts": d["attempt"],
                           "error": d["error"]} for d in job["documents"]]}, indent=2))


if __name__ == "__main__":
    main()
