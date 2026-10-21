import os
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt, QPoint
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

from clearscore.app import MainWindow, configure_app
from tests.helpers import make_pdf


def wait_for(app, predicate, timeout=12):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        app.processEvents()
        if predicate():
            return
        QTest.qWait(30)
    raise AssertionError("UI operation timed out")


def test_gui_import_compare_settings_export(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    configure_app(app)
    window = MainWindow()
    window.show()
    path = make_pdf(tmp_path / "曲谱.pdf", pages=2, shared=True)
    window.load_file(path)
    wait_for(app, lambda: window.prepared is not None and not window.busy)
    assert window.page_select.count() == 2
    assert window.export_button.isEnabled()
    QTest.mouseClick(window.tabs.button(2), Qt.MouseButton.LeftButton)
    assert len(window.view._items) == 2
    window.page_select.setCurrentIndex(1)
    assert window.page_select.currentIndex() == 1
    QTest.mouseClick(window.tabs.button(3), Qt.MouseButton.LeftButton)
    assert len(window.view._items) == 1
    window.view.zoom(1.2)
    window.view.fit_width()
    QTest.mouseClick(window.auto, Qt.MouseButton.LeftButton, pos=QPoint(8, window.auto.height() // 2))
    window.strength.setValue(38)
    assert not window.export_button.isEnabled()
    wait_for(app, lambda: not window.debounce.isActive() and not window.busy and window.prepared.report.settings["threshold"] == 202)
    output = tmp_path / "净谱.pdf"
    monkeypatch.setattr(window, "file_dialog", lambda *_a, **_k: (str(output), "PDF (*.pdf)"))
    window.export_pdf()
    assert output.is_file()
    assert window.exported == output
    assert window.folder_button.isVisible()
    # A failed import clears the previous exportable result.
    errors = []
    monkeypatch.setattr(window, "popup", lambda message, **_k: errors.append(message))
    bad = tmp_path / "bad.pdf"
    bad.write_bytes(b"invalid")
    window.load_file(bad)
    wait_for(app, lambda: not window.busy and bool(errors))
    assert window.prepared is None
    assert not window.export_button.isEnabled()
    window.close()
