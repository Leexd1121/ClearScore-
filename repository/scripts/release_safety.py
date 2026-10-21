"""Release checks. Findings never include matched secret values or host paths."""
from __future__ import annotations

import hashlib
import io
import json
import marshal
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import types
import zipfile


class ReleaseBlocked(RuntimeError):
    pass


FIXED_TIME = (2026, 1, 1, 0, 0, 0)
MANIFEST = "scripts/public-files.json"
SECRET_PATTERNS = (
    rb"\bgh[pousr]_[A-Za-z0-9]{30,}\b",
    rb"\bgithub_pat_[A-Za-z0-9_]{30,}\b",
    rb"\bsk-(?:proj-|ant-|svcacct-)?[A-Za-z0-9_-]{24,}\b",
    rb"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b",
    rb"-----BEGIN (?:RSA |EC |OPENSSH |DSA |ENCRYPTED )?PRIVATE KEY-----",
    rb"https?://[^\s/:@]{2,}:[^\s/@]{4,}@",
    rb"(?i)(?:api[_-]?key|access[_-]?token|client[_-]?secret)\s*[=:]\s*[\"'][A-Za-z0-9_./+=-]{20,}[\"']",
)
PROFILE_PATH = re.compile(rb"(?i)(?:[a-z]:[/\\]+users[/\\]+|/(?:home|users)/)[a-z0-9_.-]+")
FORBIDDEN_PARTS = {".git", ".venv", ".ssh", ".aws", ".azure", ".codex", ".agents", "__pycache__", ".pytest_cache", "node_modules"}
FORBIDDEN_SUFFIXES = {".pdf", ".doc", ".docx", ".log", ".pem", ".key", ".p12", ".pfx", ".sqlite", ".db", ".pyc", ".exe", ".dll", ".zip"}


def local_markers(root: Path) -> tuple[str, ...]:
    """Use local identity only in memory, never in the report or distribution."""
    values = {str(root.resolve()), str(Path.home())}
    for key in ("USERNAME", "USER", "COMPUTERNAME"):
        value = os.environ.get(key, "")
        if len(value) >= 4 and value.lower() not in {"root", "runner", "user", "admin", "administrator"}:
            values.add(value)
    for key in ("user.name", "user.email"):
        try:
            result = subprocess.run(["git", "config", "--get", key], cwd=root,
                                    capture_output=True, text=True, timeout=5)
            value = result.stdout.strip()
            if len(value) >= 4 and value != "ClearScore contributors" and not value.endswith(".invalid"):
                values.add(value)
        except (OSError, subprocess.TimeoutExpired):
            pass
    for key, value in os.environ.items():
        if re.search(r"(?:API_KEY|TOKEN|SECRET|PASSWORD)$", key, re.I) and len(value) >= 16:
            values.add(value)
    return tuple({variant for value in values for variant in (value, value.replace("\\", "/"), value.replace("\\", "\\\\"))})


def scan_bytes(data: bytes, markers: tuple[str, ...], *, source: bool) -> set[str]:
    findings = set()
    lowered = data.lower()
    if any(value.lower().encode(encoding) in lowered
           for value in markers if value
           for encoding in ("utf-8", "utf-16-le", "utf-16-be")):
        findings.add("local-identity-or-credential")
    if source:
        if PROFILE_PATH.search(data):
            findings.add("absolute-user-profile-path")
        if any(re.search(pattern, data) for pattern in SECRET_PATTERNS):
            findings.add("credential-pattern")
    return findings


def check_name(name: str):
    path = PurePosixPath(name)
    if (not name or "\\" in name or ":" in name or path.is_absolute()
            or any(part in {"", ".", ".."} for part in name.split("/"))
            or any(part.lower() in FORBIDDEN_PARTS or part.lower().startswith(".env") for part in path.parts)
            or path.suffix.lower() in FORBIDDEN_SUFFIXES
            or any(word in path.name.lower() for word in ("credentials", "secrets", "clipboard"))):
        raise ReleaseBlocked("The public manifest contains a forbidden file name.")


def collect_source(root: Path, markers: tuple[str, ...]) -> dict[str, bytes]:
    manifest = json.loads((root / MANIFEST).read_text(encoding="utf-8"))
    text_names = manifest["text_files"]
    assets = manifest["assets"]
    names = [*text_names, *assets]
    if len(names) != len(set(names)):
        raise ReleaseBlocked("Duplicate public manifest entry.")
    files = {}
    for name in sorted(names):
        check_name(name)
        source = root / name
        if not source.is_file() or not source.resolve().is_relative_to(root.resolve()):
            raise ReleaseBlocked("A public file is missing or resolves outside the project.")
        if any(p.is_symlink() for p in (source, *source.parents) if p.is_relative_to(root)):
            raise ReleaseBlocked("Symbolic links are not allowed in the public source package.")
        data = source.read_bytes()
        if name in assets:
            if hashlib.sha256(data).hexdigest() != assets[name]:
                raise ReleaseBlocked(f"Public demo asset needs review: {name}")
        else:
            try:
                data.decode("utf-8")
            except UnicodeDecodeError:
                raise ReleaseBlocked(f"Unexpected binary content: {name}") from None
        findings = scan_bytes(data, markers, source=True)
        if findings:
            raise ReleaseBlocked(f"Release blocked: {name} ({', '.join(sorted(findings))}); matched values withheld.")
        files[name] = data
    return files


def check_tracked(root: Path, allowed: set[str]):
    # Source ZIPs also build without Git. If Git is present, catch accidental additions.
    if not (root / ".git").exists():
        return
    result = subprocess.run(["git", "ls-files", "-z"], cwd=root, capture_output=True, check=True)
    tracked = set(filter(None, result.stdout.decode("utf-8").split("\0")))
    if tracked - allowed:
        raise ReleaseBlocked(f"There are {len(tracked - allowed)} tracked files outside the public manifest; file names withheld.")


def write_zip(destination: Path, files: dict[str, bytes], prefix: str = "ClearScore/"):
    """No local mtimes, usernames, extra fields, archive comments or absolute paths."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, data in sorted(files.items()):
            item = zipfile.ZipInfo(prefix + name, FIXED_TIME)
            item.create_system = 3
            item.external_attr = 0o100644 << 16
            item.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(item, data)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(buffer.getvalue())


def audit_portable(directory: Path, markers: tuple[str, ...]) -> dict:
    """Scan frozen modules as well as loose files; compressed bytes alone are insufficient."""
    from PyInstaller.archive.readers import CArchiveReader

    checked_files = checked_modules = 0
    findings = set()

    def inspect_code(code):
        nonlocal checked_modules
        if not isinstance(code, types.CodeType):
            return
        checked_modules += 1
        findings.update(scan_bytes(code.co_filename.encode("utf-8"), markers, source=False))
        if Path(code.co_filename).is_absolute():
            findings.add("absolute-frozen-source-path")
        for value in code.co_consts:
            if isinstance(value, types.CodeType):
                inspect_code(value)
            elif isinstance(value, str):
                findings.update(scan_bytes(value.encode("utf-8"), markers, source=False))
            elif isinstance(value, bytes):
                findings.update(scan_bytes(value, markers, source=False))

    for path in directory.rglob("*"):
        if not path.is_file():
            continue
        if path.is_symlink() or not path.resolve().is_relative_to(directory.resolve()):
            findings.add("portable-link-outside-distribution")
            continue
        checked_files += 1
        relative = path.relative_to(directory)
        if any(p.lower() in FORBIDDEN_PARTS or p.lower().startswith(".env") for p in relative.parts):
            findings.add("private-file-in-portable")
        if path.suffix.lower() in {".pdf", ".docx", ".doc", ".log", ".pem", ".key", ".pfx", ".p12", ".db", ".sqlite"}:
            findings.add("private-document-in-portable")
        data = path.read_bytes()
        findings.update(scan_bytes(data, markers, source=False))
        if path.suffix == ".zip":
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                for item in archive.infolist():
                    payload = archive.read(item)
                    findings.update(scan_bytes(payload, markers, source=False))
                    if item.filename.endswith(".pyc"):
                        inspect_code(marshal.loads(payload[16:]))
    frozen = CArchiveReader(str(directory / "净谱.exe"))
    for name, entry in frozen.toc.items():
        if entry[-1] == "z":
            pyz = frozen.open_embedded_archive(name)
            for module in pyz.toc:
                inspect_code(pyz.extract(module))
        elif entry[-1] in ("s", "m", "M"):
            inspect_code(marshal.loads(frozen.extract(name)))
    if findings:
        raise ReleaseBlocked("Portable release blocked: " + ", ".join(sorted(findings)) + "; matched values withheld.")
    return {"files_checked": checked_files, "python_code_objects_checked": checked_modules,
            "local_identifier_findings": 0, "absolute_frozen_source_paths": 0}
