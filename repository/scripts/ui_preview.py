"""Create a product screenshot using a synthetic, redistributable music fixture."""
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from clearscore.app import MainWindow, configure_app
from tests.helpers import make_pdf

app = QApplication([])
configure_app(app)
window = MainWindow(sys.argv[3] if len(sys.argv) > 3 else "zh")
window.show()
Path("tmp").mkdir(exist_ok=True)
source = Path(sys.argv[1]) if len(sys.argv) > 1 else make_pdf(Path("tmp/练习曲 · Demo.pdf"), pages=3, shared=True)
destination = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("docs/interface.png")
destination.parent.mkdir(parents=True, exist_ok=True)
window.load_file(source)


def capture():
    if window.busy or window.prepared is None:
        QTimer.singleShot(150, capture)
        return
    window.tabs.button(2).click()
    app.processEvents()
    window.grab().save(str(destination))
    window.close()
    app.quit()


QTimer.singleShot(500, capture)
QTimer.singleShot(20000, app.quit)
app.exec()
