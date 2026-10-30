"""Create the local environment from the hash-locked dependencies."""
import argparse
from pathlib import Path
import subprocess
import sys
import venv

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.parse_args()
    if sys.version_info[:3] != (3, 14, 10):
        raise SystemExit("Use CPython 3.14.10, the verified event runtime; see QUICKSTART.md")
    target = ROOT / ".venv"
    if not target.exists():
        venv.EnvBuilder(with_pip=True).create(target)
    python = target / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    lock = "requirements.lock"
    subprocess.run([str(python), "-m", "pip", "install", "--require-hashes", "--only-binary=:all:", "-r", str(ROOT / lock)], check=True)
    subprocess.run([str(python), "-m", "pip", "check"], check=True)
    print(f"Ready. Run: {python} -m docflow")


if __name__ == "__main__":
    main()
