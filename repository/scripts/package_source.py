"""Build a checked, allowlisted source ZIP, including without a Git checkout."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from clearscore import __version__
from scripts.release_safety import collect_source, check_tracked, local_markers, write_zip


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Check without writing a ZIP")
    args = parser.parse_args()
    files = collect_source(ROOT, local_markers(ROOT))
    check_tracked(ROOT, set(files))
    if args.check:
        print(f"Public source check passed: {len(files)} allowlisted files.")
        return
    destination = ROOT / "release" / f"ClearScore-{__version__}-source.zip"
    write_zip(destination, files)
    report = {
        "version": __version__, "scope": "allowlisted source files and approved synthetic assets",
        "result": "pass", "file_count": len(files),
        "findings": [], "archive": destination.name,
        "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
        "files": {name: hashlib.sha256(data).hexdigest() for name, data in files.items()},
        "note": "Pattern and local-identifier checks are safeguards, not a proof of absence of all possible secrets.",
    }
    (destination.parent / "SOURCE-AUDIT.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Created {destination.name}: {len(files)} approved files; privacy checks passed.")


if __name__ == "__main__":
    main()
