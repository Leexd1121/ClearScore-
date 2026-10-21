import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QCoreApplication, QEvent


@pytest.fixture(scope="session", autouse=True)
def application_lifetime():
    # Qt font caches are process-global: keep one QApplication for the test run,
    # just as the desktop app does, rather than repeatedly destroying/recreating it.
    app = QApplication.instance() or QApplication([])
    yield app
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    app.processEvents()
