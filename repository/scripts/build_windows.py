"""Build a relocatable, windowed application. Run with the project's Python."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import hashlib
import pefile
from importlib import metadata

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from collect_licenses import collect
from clearscore import __version__
from scripts.release_safety import audit_portable, collect_source, check_tracked, local_markers, write_zip


def main():
    if sys.platform != "win32":
        raise SystemExit("This packaging script targets Windows.")
    os.chdir(ROOT)
    markers = local_markers(ROOT)
    public_source = collect_source(ROOT, markers)
    check_tracked(ROOT, set(public_source))
    assets = ROOT / "build" / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    from PySide6.QtWidgets import QApplication
    from clearscore.app import app_icon, configure_app
    app = QApplication.instance() or QApplication([])
    configure_app(app)
    app_icon().pixmap(256, 256).save(str(assets / "icon.ico"))
    collect(assets / "licenses")
    heif_dlls = []
    heif_dist = metadata.distribution("pi-heif-decoder")
    for item in heif_dist.files or []:
        if str(item).lower().endswith(".dll"):
            heif_dlls.extend(["--add-binary", str(heif_dist.locate_file(item)) + os.pathsep + "."])
    subprocess.run([
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
        "--windowed", "--onedir", "--name", "净谱",
        "--icon", str(assets / "icon.ico"),
        "--collect-data", "pypdfium2",
        "--collect-data", "pypdfium2_raw",
        "--collect-all", "pi_heif",
        "--exclude-module", "pillow_heif",
        "--exclude-module", "_pillow_heif",
        "--exclude-module", "docx",
        "--exclude-module", "PySide6.QtQml",
        "--exclude-module", "PySide6.QtQuick",
        "--exclude-module", "PySide6.QtNetwork",
        "--exclude-module", "PySide6.QtTest",
        "--exclude-module", "tkinter",
        "--exclude-module", "pytest",
        "--specpath", "build",
        *heif_dlls,
        "run.py",
    ], check=True)
    produced = ROOT / "dist" / "净谱"
    # Fresh release staging prevents files from a previous local run leaking in.
    staging = Path(tempfile.mkdtemp(prefix="portable-", dir=ROOT / "build"))
    target = staging / "ClearScore"
    shutil.copytree(produced, target)
    # Qt 6.12 uses Windows' unversioned ICU API. A host PATH containing a
    # version-suffixed ICU (e.g. Poppler/Conda) can fool PyInstaller's resolver
    # into bundling the wrong icuuc.dll. Let Windows resolve its own system ICU
    # when Qt requests those unversioned imports, rather than ship host DLLs.
    qt_core = pefile.PE(str(target / "_internal" / "PySide6" / "Qt6Core.dll"))
    uses_windows_icu = any(
        entry.dll.lower() == b"icuuc.dll"
        and any(symbol.name == b"ucnv_open" for symbol in entry.imports)
        for entry in qt_core.DIRECTORY_ENTRY_IMPORT
    )
    qt_core.close()
    if uses_windows_icu:
        for distribution in (produced, target):
            internal = distribution / "_internal"
            for dll in [internal / "icuuc.dll", *internal.glob("icudt*.dll")]:
                if dll.exists():
                    dll.unlink()
    shutil.copytree(assets / "licenses", target / "licenses", dirs_exist_ok=True)
    for name, data in public_source.items():
        if name.startswith("docs/") or name in ("LICENSE", "README.md", "THIRD_PARTY_NOTICES.md"):
            destination = target / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
    # A frozen GUI can fail despite passing source tests (DLL/plugin packaging).
    # Verify a real launch, PDF processing, and preview before publishing a ZIP.
    import json
    from tests.helpers import make_pdf, score_image
    from tests.test_formats import make_docx
    pdf = make_pdf(assets / "smoke-input.pdf")
    png = assets / "smoke-input.png"
    score_image().save(png)
    tiff = assets / "smoke-input.tiff"
    score_image().save(tiff, save_all=True, append_images=[score_image().rotate(180)])
    word = make_docx(assets / "smoke-input.docx", png)
    avif = assets / "smoke-input.avif"
    score_image().save(avif)
    heic = ROOT / "tests" / "fixtures" / "synthetic-score.heic"
    environment = os.environ.copy()
    environment["QT_QPA_PLATFORM"] = "offscreen"
    for sample, language in ((pdf, "zh"), (png, "en"), (word, "ru"), (tiff, "ug"), (avif, "en"), (heic, "ug")):
        smoke_dir = assets / ("smoke-" + sample.suffix.lstrip("."))
        smoke_dir.mkdir(exist_ok=True)
        result_file = smoke_dir / "smoke-result.json"
        if result_file.exists():
            result_file.unlink()
        subprocess.run([
            str(target / "净谱.exe"), "--smoke-test", str(sample), str(smoke_dir), language,
        ], env=environment, timeout=60, check=True)
        result = json.loads(result_file.read_text(encoding="utf-8"))
        if not result.get("ok") or not result.get("export_enabled"):
            raise RuntimeError(f"Packaged GUI smoke check failed for {sample.name}: {result}")
        print(f"Packaged check passed: {sample.suffix} / {language}")
    (ROOT / "release").mkdir(exist_ok=True)
    privacy = audit_portable(target, markers)
    archive = ROOT / "release" / f"ClearScore-{__version__}-windows-x64.zip"
    files = {path.relative_to(target).as_posix(): path.read_bytes() for path in target.rglob("*") if path.is_file()}
    write_zip(archive, files)
    privacy.update({"archive": archive.name, "result": "pass", "sha256": hashlib.sha256(archive.read_bytes()).hexdigest()})
    (ROOT / "release" / "PORTABLE-AUDIT.json").write_text(json.dumps(privacy, indent=2) + "\n", encoding="utf-8")
    # The ZIP is built from fresh checked staging, never from this convenience copy.
    try:
        shutil.copytree(target, ROOT / "dist" / "ClearScore", dirs_exist_ok=True)
    except (PermissionError, shutil.Error):
        print("The local application folder could not be refreshed; the checked ZIP is ready to extract.")
    print(f"Built {archive.name}; portable privacy checks passed.")


if __name__ == "__main__":
    main()
