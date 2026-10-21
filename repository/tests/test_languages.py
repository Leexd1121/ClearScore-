import re
from string import Formatter

import pytest
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QRawFont, QPalette, QColor
from PySide6.QtWidgets import QApplication, QFileDialog, QLineEdit

from clearscore.app import MainWindow, configure_app
from clearscore.i18n import CATALOGS, LANGUAGES, Message, ROWS, ERROR_ROWS, tr
from tests.helpers import score_image
from tests.test_formats import make_docx
from tests.test_ui import wait_for


def test_all_language_keys_and_placeholders_match():
    keys = [row[0] for row in ROWS + ERROR_ROWS]
    assert len(keys) == len(set(keys))
    placeholders = lambda text: {part[1] for part in Formatter().parse(text) if part[1] is not None}
    for key in keys:
        expected = placeholders(CATALOGS["zh"][key])
        for language in LANGUAGES:
            text = CATALOGS[language][key]
            assert text and placeholders(text) == expected
            if language != "zh":
                assert not re.search(r"[\u4e00-\u9fff]", text)


@pytest.mark.parametrize("language", LANGUAGES)
@pytest.mark.parametrize("kind", ["image", "docx"])
def test_language_switch_format_preview_and_export(tmp_path, language, kind):
    app = QApplication.instance() or QApplication([])
    configure_app(app)
    window = MainWindow(language)
    window.show()
    errors = []
    window.popup = lambda message, **_kwargs: errors.append(message)
    path = tmp_path / "practice.png"
    score_image().save(path)
    if kind == "docx":
        path = make_docx(tmp_path / "practice.docx", path)
    window.load_file(path)
    wait_for(app, lambda: not window.busy and (window.prepared is not None or errors))
    assert not errors
    assert window.prepared.kind == kind
    for lang in LANGUAGES:
        window.language_select.setCurrentIndex(list(LANGUAGES).index(lang))
        assert window.language == lang
        assert window.export_button.text() == tr("export", lang)
        assert window.layoutDirection() == (Qt.LayoutDirection.RightToLeft if lang == "ug" else Qt.LayoutDirection.LeftToRight)
        assert window.view.layoutDirection() == Qt.LayoutDirection.LeftToRight
        window.tabs.button(2).click()
        assert len(window.view._items) == 2
        if kind == "docx":
            assert window.subtitle.text() == tr("docx_preview", lang)
    target = tmp_path / ("result" + window.prepared.default_suffix)
    window.file_dialog = lambda *_a, **_k: (str(target), "")
    window.export_pdf()
    assert target.exists()
    assert not errors
    window.set_message(Message("process_failed"))
    window.language_select.setCurrentIndex(list(LANGUAGES).index(language))
    assert window.message.text() == tr("process_failed", language)
    window.close()


def test_uyghur_font_has_all_script_glyphs():
    app = QApplication.instance() or QApplication([])
    configure_app(app)
    font = QRawFont.fromFont(QFont("Tahoma", 15))
    chars = {c for value in CATALOGS["ug"].values() for c in value if "\u0600" <= c <= "\u06ff"}
    # The Qt QString overload accepts Latin-1; use the UCS-4 integer overload.
    missing = [c for c in chars if not font.supportsCharacter(ord(c))]
    assert not missing, missing


def test_file_dialog_contrast_and_uyghur_direction_under_dark_os_palette():
    app = QApplication.instance() or QApplication([])
    dark = QPalette()
    dark.setColor(QPalette.ColorRole.Window, QColor("#202020"))
    dark.setColor(QPalette.ColorRole.Base, QColor("#202020"))
    app.setPalette(dark)
    configure_app(app)
    window = MainWindow("ug")
    window.show()
    observations = []

    def inspect():
        dialog = app.activeModalWidget()
        observations.append({
            "is_file_dialog": isinstance(dialog, QFileDialog),
            "rtl": dialog.layoutDirection() == Qt.LayoutDirection.RightToLeft,
            "base_light": dialog.palette().color(QPalette.ColorRole.Base).lightness() > 200,
            "window_light": dialog.palette().color(QPalette.ColorRole.Window).lightness() > 200,
            "filename_ltr": dialog.findChild(QLineEdit, "fileNameEdit").layoutDirection() == Qt.LayoutDirection.LeftToRight,
            "label": dialog.labelText(QFileDialog.DialogLabel.FileName) == tr("filename", "ug"),
        })
        dialog.reject()

    QTimer.singleShot(100, inspect)
    assert window.file_dialog() == ("", "")
    assert observations and all(observations[0].values())
    assert tr("docx_preview", "ug").startswith("\u200fWord")
    window.close()
