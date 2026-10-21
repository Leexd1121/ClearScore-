import hashlib
import json
import marshal
from pathlib import Path
import zipfile

import pytest

from scripts.release_safety import (
    FIXED_TIME, ReleaseBlocked, audit_portable, check_name, collect_source, scan_bytes, write_zip,
)


def manifest(root, text_files, assets=None):
    (root / "scripts").mkdir(exist_ok=True)
    (root / "scripts/public-files.json").write_text(json.dumps({
        "text_files": text_files, "assets": assets or {},
    }), encoding="utf-8")


def test_only_approved_files_are_packaged_and_no_git_is_needed(tmp_path):
    (tmp_path / "README.md").write_text("Public documentation", encoding="utf-8")
    (tmp_path / ".env").write_text("private settings", encoding="utf-8")
    (tmp_path / "private.pdf").write_bytes(b"private sample")
    manifest(tmp_path, ["README.md"])
    assert collect_source(tmp_path, ()) == {"README.md": b"Public documentation"}


def test_local_identity_and_credentials_block_without_disclosing_matches(tmp_path):
    marker = "fictional-identity-for-test"
    (tmp_path / "README.md").write_text(marker, encoding="utf-8")
    manifest(tmp_path, ["README.md"])
    with pytest.raises(ReleaseBlocked) as error:
        collect_source(tmp_path, (marker,))
    assert marker not in str(error.value)
    for encoding in ("utf-8", "utf-16-le", "utf-16-be"):
        assert scan_bytes(marker.encode(encoding), (marker,), source=False)
    token = "gh" + "p_" + "A" * 36
    (tmp_path / "README.md").write_text(token, encoding="utf-8")
    with pytest.raises(ReleaseBlocked) as error:
        collect_source(tmp_path, ())
    assert token not in str(error.value)


@pytest.mark.parametrize("name", ["../outside.txt", "/outside.txt", ".git/config", ".env", "data/sample.pdf", "private.key", "C:" + "/private.txt"])
def test_forbidden_entries_cannot_be_allowlisted(name):
    with pytest.raises(ReleaseBlocked):
        check_name(name)


def test_replacing_an_approved_demo_asset_requires_review(tmp_path):
    asset = tmp_path / "demo.png"
    asset.write_bytes(b"approved synthetic asset")
    manifest(tmp_path, [], {"demo.png": hashlib.sha256(asset.read_bytes()).hexdigest()})
    assert "demo.png" in collect_source(tmp_path, ())
    asset.write_bytes(b"a different image")
    with pytest.raises(ReleaseBlocked, match="needs review"):
        collect_source(tmp_path, ())


def test_source_archive_is_reproducible_without_host_metadata(tmp_path):
    first, second = tmp_path / "first.zip", tmp_path / "second.zip"
    files = {"README.md": b"public", "clearscore/app.py": b"pass\n"}
    write_zip(first, files)
    write_zip(second, dict(reversed(list(files.items()))))
    assert first.read_bytes() == second.read_bytes()
    with zipfile.ZipFile(first) as archive:
        assert not archive.comment
        for item in archive.infolist():
            assert item.date_time == FIXED_TIME
            assert not item.extra and not item.comment
            assert item.filename.startswith("ClearScore/")


def test_public_project_manifest_is_complete_and_clean():
    root = Path(__file__).resolve().parents[1]
    files = collect_source(root, ())
    assert {"README.md", "LICENSE", "run.py", "scripts/public-files.json", ".github/workflows/ci.yml"} <= files.keys()


@pytest.mark.parametrize("unsafe_filename", [False, True])
def test_frozen_code_is_inspected_after_decompression(tmp_path, monkeypatch, unsafe_filename):
    marker = "fictional-frozen-identity"
    filename = str(tmp_path / "entry.py") if unsafe_filename else "entry.py"
    code = compile("value = " + repr(marker), filename, "exec")

    class FrozenArchive:
        toc = {"entry": (0, 0, 0, 1, "s")}

        def extract(self, name):
            return marshal.dumps(code)

    monkeypatch.setattr("PyInstaller.archive.readers.CArchiveReader", lambda path: FrozenArchive())
    (tmp_path / "净谱.exe").write_bytes(b"container with compressed code")
    markers = () if unsafe_filename else (marker,)
    with pytest.raises(ReleaseBlocked) as error:
        audit_portable(tmp_path, markers)
    assert marker not in str(error.value)
    assert str(tmp_path) not in str(error.value)
