"""Developer-only end-to-end check of the packaged GUI and PDF engine."""
import json
from pathlib import Path
import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QMessageBox

from .app import MainWindow, configure_app
from .formats import save_document


def main():
    source, directory = Path(sys.argv[2]), Path(sys.argv[3])
    directory.mkdir(parents=True, exist_ok=True)
    app = QApplication([])
    configure_app(app)
    errors = []
    window = MainWindow(sys.argv[4] if len(sys.argv) > 4 else "zh")
    window.popup = lambda message, **_kwargs: errors.append(str(message))
    window.show()
    window.load_file(source)
    done = False

    def finish(payload):
        nonlocal done
        if done:
            return
        done = True
        (directory / "smoke-result.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        window.close()
        app.quit()

    def poll():
        if window.busy:
            QTimer.singleShot(150, poll)
            return
        if errors or window.prepared is None:
            finish({"ok": False, "errors": errors})
            return
        try:
            window.tabs.button(2).click()
            app.processEvents()
            window.grab().save(str(directory / "smoke-window.png"))
            output = save_document(window.prepared, directory / ("smoke-clean" + window.prepared.default_suffix), source)
            finish({
                "ok": True, "export": str(output),
                "pages": window.prepared.report.page_count,
                "processed_pages": window.prepared.report.processed_pages,
                "export_enabled": window.export_button.isEnabled(),
                "kind": window.prepared.kind,
                "language": window.language,
            })
        except Exception as exc:
            finish({"ok": False, "errors": [str(exc)]})

    QTimer.singleShot(200, poll)
    QTimer.singleShot(45000, lambda: finish({"ok": False, "errors": ["GUI smoke test timeout"]}))
    app.exec()
