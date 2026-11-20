"""Local UI orchestration of the unchanged, fresh-process benchmark runner."""
from copy import deepcopy
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
import uuid

from .jobs import Busy

ROOT = Path(__file__).resolve().parents[1]


class Competition:
    def __init__(self, directory=None):
        self.directory = directory or ROOT / ".runtime" / "competition"
        self.lock = threading.RLock()
        self.process = None
        self.thread = None
        self.closed = False
        self.state = {"baseline": None, "optimized": None, "comparison": None}
        try:
            saved = json.loads((self.directory / "state.json").read_text())
            for phase in ("baseline", "optimized"):
                run = saved.get(phase)
                if run and run["status"] == "running":
                    run.update(status="interrupted", error="Server restarted. Run this benchmark again.")
            self.state = saved
        except (OSError, ValueError, KeyError, TypeError):
            pass

    def save(self):
        self.directory.mkdir(parents=True, exist_ok=True)
        temporary = self.directory / "state.tmp"
        temporary.write_text(json.dumps(self.state), encoding="utf-8")
        temporary.replace(self.directory / "state.json")

    def snapshot(self):
        with self.lock:
            return deepcopy(self.state)

    def start(self, phase, store):
        with self.lock:
            if self.closed or any(r and r["status"] == "running" for r in
                                  (self.state["baseline"], self.state["optimized"])):
                raise Busy("A benchmark is already running or the server is shutting down.")
            if phase == "optimized" and (not self.state["baseline"] or self.state["baseline"]["status"] != "completed"):
                raise ValueError("Run a successful baseline first.")
            if not store.lane.acquire(blocking=False):
                raise Busy("Wait for the current document job to finish.")
            previous = deepcopy(self.state)
            try:
                if phase == "baseline":
                    self.state["optimized"] = None
                self.state["comparison"] = None
                self.state[phase] = {"id": uuid.uuid4().hex, "status": "running", "trials": [], "error": None}
                self.save()
                self.thread = threading.Thread(target=self.run, args=(phase, store.lane), daemon=True)
                self.thread.start()
            except Exception:
                self.state = previous
                store.lane.release()
                raise
            return deepcopy(self.state[phase])

    def stop_process(self):
        with self.lock:
            process = self.process
        if process is not None and process.poll() is None:
            if os.name == "nt":
                subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                               capture_output=True, timeout=10)
            else:
                import signal
                os.killpg(process.pid, signal.SIGKILL)

    def run(self, phase, lane):
        timer = None
        try:
            with self.lock:
                run = self.state[phase]
                path = self.directory / (run["id"] + ".json")
                if self.closed:
                    raise RuntimeError("closed")
                self.process = subprocess.Popen(
                    [sys.executable, str(ROOT / "benchmark.py"), "run", "--label", "competition",
                     "--output", str(path)], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                    text=True, start_new_session=os.name != "nt",
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            timer = threading.Timer(390, self.stop_process)
            timer.daemon = True
            timer.start()
            for line in self.process.stdout:
                match = re.fullmatch(r"Trial (\d+): ([\d.]+)s wall, ([\d.]+)s process CPU", line.strip())
                if match:
                    with self.lock:
                        run["trials"].append({"number": int(match[1]), "wall_seconds": float(match[2]),
                                              "cpu_seconds": float(match[3])})
                        self.save()
            if self.process.wait() != 0:
                raise RuntimeError("benchmark failed")
            report = json.loads(path.read_text(encoding="utf-8"))
            from benchmark import validate_report
            validate_report(report)
            with self.lock:
                run.update(status="completed", report=report)
        except Exception:
            with self.lock:
                self.state[phase].update(status="failed", error=(
                    "Benchmark did not complete. Check Azure access/quota and processing failures. "
                    "Use the benchmark CLI for detailed diagnosis; do not raise safety limits."))
        finally:
            if timer:
                timer.cancel()
            try:
                # Also stop any surviving worker before allowing interactive jobs.
                self.stop_process()
                with self.lock:
                    if self.process and self.process.stdout:
                        self.process.stdout.close()
                    self.process = None
                    self.save()
            finally:
                lane.release()

    def compare(self):
        with self.lock:
            if not all(self.state[p] and self.state[p]["status"] == "completed" for p in ("baseline", "optimized")):
                raise ValueError("Complete both benchmarks before comparing.")
            from argparse import Namespace
            from benchmark import compare
            result = compare(Namespace(**{key: self.directory / (self.state[phase]["id"] + ".json")
                                          for key, phase in (("before", "baseline"), ("after", "optimized"))}))
            self.state["comparison"] = result
            self.save()
            return result

    def close(self):
        with self.lock:
            self.closed = True
        self.stop_process()
        if self.thread:
            self.thread.join(timeout=15)
