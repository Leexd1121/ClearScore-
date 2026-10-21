"""Collect unmodified upstream license files into the portable distribution."""
from importlib import metadata
import json
from pathlib import Path
import shutil
import sys


def collect(destination: Path):
    destination.mkdir(parents=True, exist_ok=True)
    names = ["numpy", "Pillow", "pi-heif-decoder", "pypdf", "pypdfium2", "PySide6-Essentials", "shiboken6", "pyinstaller"]
    versions = {"Python": sys.version}
    for name in names:
        dist = metadata.distribution(name)
        versions[name] = dist.version
        for item in dist.files or []:
            parts = str(item).replace("\\", "/").lower()
            if "license" in parts or "copying" in parts or parts.endswith("/metadata"):
                source = Path(dist.locate_file(item))
                if source.is_file():
                    # Keep notices nested to avoid basename collisions.
                    relative = Path(*[p for p in Path(item).parts if p not in ("..", ".")])
                    target = destination / name / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, target)
    for candidate in (Path(sys.base_prefix) / "LICENSE.txt", Path(sys.base_prefix) / "LICENSE"):
        if candidate.exists():
            shutil.copy2(candidate, destination / "Python-LICENSE.txt")
            break
    upstream_texts = Path(__file__).resolve().parents[1] / "licenses"
    for source in upstream_texts.glob("*.txt"):
        shutil.copy2(source, destination / source.name)
    for name in ("LGPL-3.0-only.txt", "GPL-3.0-only.txt"):
        if not (destination / name).is_file():
            raise RuntimeError(f"Missing checked-in license text: {name}")
    (destination / "versions.json").write_text(json.dumps(versions, indent=2), encoding="utf-8")


if __name__ == "__main__":
    collect(Path(sys.argv[1]))
