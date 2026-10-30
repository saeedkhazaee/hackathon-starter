"""Independent fresh-process benchmark. Monitoring evidence is submitted separately."""
import argparse
import hashlib
from importlib.metadata import distributions
import json
import math
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def worker(args):
    from fastapi.testclient import TestClient
    from docflow.api import app
    from docflow.jobs import meaningful_results
    from docflow.workload import make_workload
    batch = make_workload(seed=args.seed, rows=args.rows)
    payload = batch.model_dump()
    with TestClient(app) as client:
        start, cpu = time.perf_counter(), time.process_time()
        response = client.post("/jobs", json=payload)
        response.raise_for_status()
        # TestClient waits for actual BackgroundTasks to finish before returning.
        job = client.get(f"/jobs/{response.json()['job_id']}/results").json()
        wall, cpu = time.perf_counter() - start, time.process_time() - cpu
        results = meaningful_results(job)
        expected_ids = [d.document_id for d in batch.documents]
        if [d["document_id"] for d in results] != expected_ids:
            raise ValueError("Missing, reordered or duplicated documents")
        if sum(d["status"] == "completed" for d in results) != 37 or sum(d["status"] == "failed" for d in results) != 3:
            raise ValueError("Workload terminal outcomes changed")
        if any(d["error"]["code"] != "arithmetic_mismatch" for d in results if d["status"] == "failed"):
            raise ValueError("Unexpected document failure")
    return {"wall_seconds": wall, "parent_process_cpu_seconds": cpu,
            "result_sha256": digest(results), "workload_sha256": digest(payload),
            "completed": 37, "failed": 3,
            "attempts": sum(d["attempt"] for d in job["documents"]), "stage_operations": job["operations"]}


def control_hash():
    names = ["benchmark.py", "docflow/workload.py", "docflow/models.py", "docflow/safety.py", "data/classification.json"]
    return digest({name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in names})


def run(args):
    if args.runs < 3:
        raise ValueError("Use at least three fresh-process trials")
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    samples = []
    for index in range(args.runs):
        command = [sys.executable, "-B", str(ROOT / "benchmark.py"), "_worker", "--seed", str(args.seed), "--rows", str(args.rows)]
        completed = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True, timeout=120)
        if completed.returncode:
            raise RuntimeError(f"Benchmark child failed: {completed.stderr[-2000:]}")
        samples.append(json.loads(completed.stdout.strip().splitlines()[-1]))
        print(f"Trial {index + 1}: {samples[-1]['wall_seconds']:.3f}s wall, {samples[-1]['parent_process_cpu_seconds']:.3f}s process CPU", flush=True)
    if len({s["result_sha256"] for s in samples}) != 1 or len({s["workload_sha256"] for s in samples}) != 1:
        raise ValueError("Nondeterministic workload or results")
    packages = sorted((d.metadata["Name"].lower(), d.version) for d in distributions())
    report = {"schema": 2, "conditions": {"seed": args.seed, "rows": args.rows, "runs": args.runs,
        "python": platform.python_version(), "platform": platform.platform(), "host": platform.node(),
        "packages": packages, "concurrency": 1, "cache": "fresh process per trial; empty job store",
        "measurement_label": args.label, "controls_sha256": control_hash(), "workload_sha256": samples[0]["workload_sha256"]},
        "samples": samples, "median_wall_seconds": statistics.median(s["wall_seconds"] for s in samples),
        "median_parent_process_cpu_seconds": statistics.median(s["parent_process_cpu_seconds"] for s in samples),
        "provenance": "Independent time.perf_counter and time.process_time in the API process; excludes child-process CPU",
        "efficiency_score_eligible": False}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return {"report": str(args.output), "median_wall_seconds": report["median_wall_seconds"],
            "median_parent_process_cpu_seconds": report["median_parent_process_cpu_seconds"]}


def validate_report(report):
    samples = report["samples"]
    if report.get("schema") != 2 or len(samples) < 3 or len(samples) != report["conditions"]["runs"]:
        raise ValueError("Invalid report schema or trial count")
    for sample in samples:
        for metric in ("wall_seconds", "parent_process_cpu_seconds"):
            if not isinstance(sample[metric], (int, float)) or not math.isfinite(sample[metric]) or sample[metric] <= 0:
                raise ValueError("Invalid measurement")
        if sample["workload_sha256"] != report["conditions"]["workload_sha256"]:
            raise ValueError("Workload digest mismatch")
        if (sample["completed"], sample["failed"]) != (37, 3):
            raise ValueError("Invalid document outcomes")
    for field, metric in (("median_wall_seconds", "wall_seconds"), ("median_parent_process_cpu_seconds", "parent_process_cpu_seconds")):
        if report[field] != statistics.median(s[metric] for s in samples):
            raise ValueError("Reported median does not match samples")


def compare(args):
    before, after = [json.loads(path.read_text(encoding="utf-8")) for path in (args.before, args.after)]
    for report in (before, after):
        validate_report(report)
    if before["conditions"] != after["conditions"]:
        raise ValueError("Measurement conditions differ; repeat with the same environment, controls and monitoring")
    if len({s["result_sha256"] for r in (before, after) for s in r["samples"]}) != 1:
        raise ValueError("Correctness gate failed: results changed")
    return {"output_equivalence": True, "independent_wall_reduction_pct": 100 * (1 - after["median_wall_seconds"] / before["median_wall_seconds"]),
            "independent_parent_cpu_reduction_pct": 100 * (1 - after["median_parent_process_cpu_seconds"] / before["median_parent_process_cpu_seconds"]),
            "efficiency_score_eligible": False,
            "note": "Local timings alone do not earn efficiency points. Judges verify native telemetry and essential tests separately."}


def main():
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("run", "_worker"):
        child = commands.add_parser(name)
        child.add_argument("--seed", type=int, default=17)
        child.add_argument("--rows", type=int, default=25_000)
        if name == "run":
            child.add_argument("--runs", type=int, default=3)
            child.add_argument("--label", default="local", help="Record the same monitoring configuration label for both runs")
            child.add_argument("--output", type=Path, required=True)
    child = commands.add_parser("compare")
    child.add_argument("before", type=Path)
    child.add_argument("after", type=Path)
    args = parser.parse_args()
    result = {"run": run, "_worker": worker, "compare": compare}[args.command](args)
    print(json.dumps(result, separators=(",", ":") if args.command == "_worker" else None))


if __name__ == "__main__":
    main()
