from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QThread, QTimer, Signal, QUrl, QSettings, QLocale, QTranslator, QLibraryInfo
from PySide6.QtGui import (
    QColor, QDesktopServices, QFont, QFontDatabase, QIcon, QImage, QKeySequence, QPainter,
    QPen, QPixmap, QShortcut, QPalette,
)
from PySide6.QtWidgets import (
    QApplication, QButtonGroup, QCheckBox, QComboBox, QFileDialog,
    QFrame, QGraphicsScene, QGraphicsView, QHBoxLayout, QLabel,
    QMainWindow, QMessageBox, QProgressBar, QPushButton,
    QSizePolicy, QSlider, QStackedWidget, QVBoxLayout, QWidget, QScrollArea, QToolButton, QTreeView, QLineEdit, QListView,
)

from . import __version__
from .core import Cancelled, CleanupError, Settings
from .formats import Document, IMAGE_EXTENSIONS, SUPPORTED_EXTENSIONS, prepare_document, save_document, write_atomic
from .i18n import LANGUAGES, Message, tr, isolated
from .preview import difference_image


STYLE = """
QWidget { font-family: 'Microsoft YaHei UI', 'PingFang SC', sans-serif;
          font-size: 13px; color: #273a34; }
QMainWindow, #root { background: #f3f5f2; }
#header { background: #ffffff; border-bottom: 1px solid #e3e9e4; }
#sidebar { background: #ffffff; border-right: 1px solid #e3e9e4; }
QLabel { background: transparent; }
QLabel#brand { font-size: 21px; font-weight: 700; letter-spacing: 2px; }
QLabel#eyebrow { font-size: 10px; letter-spacing: 2px; color: #83958c; }
QLabel#title { font-size: 24px; font-weight: 600; color: #213e33; }
QLabel#section { font-size: 12px; font-weight: 600; color: #718279; }
QLabel#muted { color: #7d8b83; font-size: 12px; }
QLabel#small { color: #7d8b83; font-size: 11px; }
QLabel#badge { background: #edf5ee; color: #3a7358; padding: 6px 12px;
              border-radius: 12px; font-size: 11px; }
QLabel#fileName { font-size: 14px; font-weight: 600; }
QFrame#fileCard { background: #f5f8f4; border: 1px solid #e4ece4; border-radius: 14px; }
QFrame#statCard { background: #f8f9f6; border: 1px solid #ebeee7; border-radius: 12px; }
QFrame#divider { background: #e9eee8; max-height: 1px; }
QPushButton { background: #ffffff; border: 1px solid #dce5dd; border-radius: 9px;
              padding: 9px 15px; font-weight: 500; }
QPushButton:hover { background: #f0f5ef; border-color: #a9c3b0; }
QPushButton:pressed { background: #e4eee4; }
QPushButton:disabled { color: #aab4ad; background: #f4f6f3; border-color: #e7ece6; }
QPushButton#primary { background: #2e6651; color: white; border: none;
                     font-weight: 600; padding: 12px 20px; }
QPushButton#primary:hover { background: #24533f; }
QPushButton#primary:disabled { background: #b7c9bb; color: #f4f7f4; }
QPushButton#quiet { border: none; background: transparent; color: #6a7d70; }
QPushButton#quiet:hover { background: #edf3ec; color: #274e3c; }
QPushButton#tab { background: transparent; border: none; color: #7f8b83;
                 padding: 8px 13px; border-radius: 7px; }
QPushButton#tab:checked { background: #ffffff; color: #2e6651; font-weight: 600; }
QFrame#tabBar { background: #e8ede6; border-radius: 10px; }
QComboBox { padding: 7px 11px; border: 1px solid #dce5dd; background: #fff; border-radius: 8px; }
QComboBox::drop-down { border: none; width: 22px; }
QComboBox QAbstractItemView { background: white; selection-background-color: #e2ede2; }
QCheckBox { spacing: 9px; }
QCheckBox::indicator { width: 16px; height: 16px; }
QSlider::groove:horizontal { background: #e7ece6; height: 5px; border-radius: 2px; }
QSlider::sub-page:horizontal { background: #6c9579; border-radius: 2px; }
QSlider::handle:horizontal { background: #fff; border: 2px solid #42785a;
                            width: 14px; margin: -6px 0; border-radius: 8px; }
QSlider:disabled::sub-page:horizontal { background: #bbcbbb; }
QProgressBar { background: #e9eee6; border: none; border-radius: 3px; height: 5px; max-height: 5px; }
QProgressBar::chunk { background: #4c8865; border-radius: 3px; }
QGraphicsView { border: none; background: #e8ede6; border-radius: 12px; }
QScrollBar:vertical { background: transparent; width: 8px; margin: 3px; }
QScrollBar::handle:vertical { background: #bac8bb; min-height: 30px; border-radius: 3px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { background: transparent; height: 8px; margin: 3px; }
QScrollBar::handle:horizontal { background: #bac8bb; min-width: 30px; border-radius: 3px; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QToolTip { background: #243d30; color: white; border: none; padding: 6px; }
"""


def label(text: str, name: str = "", wrap: bool = False) -> QLabel:
    result = QLabel(text)
    result.setObjectName(name)
    result.setWordWrap(wrap)
    return result


def button(text: str, name: str = "", callback=None) -> QPushButton:
    result = QPushButton(text)
    result.setObjectName(name)
    result.setCursor(Qt.CursorShape.PointingHandCursor)
    if callback:
        result.clicked.connect(callback)
    return result


def app_icon(size: int = 128) -> QIcon:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor("#2e6651"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(0, 0, size, size, size * 0.25, size * 0.25)
    painter.scale(size / 100, size / 100)
    painter.setPen(QPen(QColor("#91b59d"), 2))
    for y in (35, 45, 55, 65):
        painter.drawLine(23, y, 77, y)
    painter.setPen(QPen(QColor("#ffffff"), 4))
    painter.drawLine(60, 27, 60, 64)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#ffffff"))
    painter.drawEllipse(42, 58, 20, 13)
    painter.end()
    return QIcon(pixmap)


class ProcessJob(QThread):
    progress = Signal(int, object)
    result = Signal(object)
    error = Signal(object)

    def __init__(self, path: Path, settings: Settings, parent=None):
        super().__init__(parent)
        self.path, self.settings = path, settings

    def run(self):
        try:
            prepared = prepare_document(
                self.path, self.settings,
                progress=self.progress.emit,
                cancelled=self.isInterruptionRequested,
            )
            if not self.isInterruptionRequested():
                self.result.emit(prepared)
        except Cancelled:
            pass
        except Exception as exc:
            self.error.emit(exc.message if isinstance(exc, CleanupError) else Message("process_failed"))


class ScoreView(QGraphicsView):
    zoomChanged = Signal(str)

    def __init__(self):
        super().__init__()
        self.setScene(QGraphicsScene(self))
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self._fit = True
        self._items = []
        self.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.caption_font = "Microsoft YaHei UI"

    def show_images(self, images, captions, reset=True):
        previous_count = len(self._items)
        self.scene().clear()
        self._items = []
        x = 0
        for pil, caption in zip(images, captions):
            title = self.scene().addText(caption, QFont(self.caption_font, 20))
            title.setDefaultTextColor(QColor("#6c7f70"))
            title.setPos(x, -55)
            rgb = pil.convert("RGB")
            pixels = rgb.tobytes()
            qimage = QImage(pixels, rgb.width, rgb.height, rgb.width * 3, QImage.Format.Format_RGB888).copy()
            pixmap = QPixmap.fromImage(qimage)
            item = self.scene().addPixmap(pixmap)
            item.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
            item.setPos(x, 0)
            self._items.append(item)
            x += pil.width + 60
        self.scene().setSceneRect(self.scene().itemsBoundingRect().adjusted(-35, -20, 35, 35))
        if reset or self._fit or previous_count != len(images):
            self.fit_page()

    def fit_page(self):
        self._fit = True
        if not self.scene().items():
            return
        self.fitInView(self.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        self._emit_zoom()

    def fit_width(self):
        if not self._items:
            return
        self._fit = False
        self.resetTransform()
        factor = (self.viewport().width() - 35) / self.sceneRect().width()
        self.scale(factor, factor)
        self.centerOn(self.sceneRect().center().x(), self.viewport().height() / factor / 2 - 55)
        self._emit_zoom()

    def zoom(self, factor):
        current = self.transform().m11()
        if 0.08 <= current * factor <= 6:
            self._fit = False
            self.scale(factor, factor)
            self._emit_zoom()

    def _emit_zoom(self):
        self.zoomChanged.emit(f"{self.transform().m11() * 100:.0f}%")

    def wheelEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.zoom(1.18 if event.angleDelta().y() > 0 else 1 / 1.18)
            event.accept()
        else:
            super().wheelEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._fit:
            self.fit_page()



class MainWindow(QMainWindow):
    def __init__(self, language="zh", preferences=None):
        super().__init__()
        self.language = language if language in LANGUAGES else "en"
        self.preferences = preferences
        self.qt_translator = QTranslator(self)
        self.bindings = []
        self._message = Message("ready")
        self.source = None
        self.prepared = None
        self.worker = None
        self.exported = None
        self._closing = False
        self._preview_cache = {}
        self._had_preview = False
        self.resize(1360, 900)
        self.setMinimumSize(1180, 800)
        self.setAcceptDrops(True)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setWindowIcon(app_icon())
        self._build()
        self.debounce = QTimer(self)
        self.debounce.setSingleShot(True)
        self.debounce.setInterval(550)
        self.debounce.timeout.connect(self.process)
        self.auto.toggled.connect(self.settings_changed)
        self.staff.toggled.connect(self.settings_changed)
        self.strength.valueChanged.connect(self.settings_changed)
        self.language_select.currentIndexChanged.connect(self.change_language)
        QShortcut(QKeySequence.StandardKey.Open, self, activated=self.choose_file)
        QShortcut(QKeySequence.StandardKey.SaveAs, self, activated=self.export_pdf)
        QShortcut(QKeySequence("Ctrl+0"), self, activated=self.view.fit_page)
        self.change_language()

    def t(self, key, **values):
        return tr(key, self.language, **values)

    def text(self, key, name="", wrap=False):
        widget = label("", name, wrap)
        self.bindings.append((widget, key))
        return widget

    def btn(self, key, name="", callback=None):
        widget = button("", name, callback)
        self.bindings.append((widget, key))
        return widget

    def _build(self):
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        header = QFrame()
        header.setObjectName("header")
        header.setFixedHeight(88)
        h = QHBoxLayout(header)
        h.setContentsMargins(26, 12, 26, 12)
        logo = QLabel()
        logo.setPixmap(app_icon().pixmap(43, 43))
        h.addWidget(logo)
        brand = QVBoxLayout()
        brand.setSpacing(1)
        brand.addWidget(self.text("brand", "brand"))
        brand.addWidget(label("C L E A R S C O R E", "eyebrow"))
        h.addLayout(brand)
        h.addSpacing(18)
        h.addWidget(self.text("tagline", "muted", True))
        h.addStretch()
        h.addWidget(self.text("local", "badge"))
        self.language_select = QComboBox()
        self.language_select.setAccessibleName("Language / 语言 / Язык / تىل")
        self.language_select.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        for code, name in LANGUAGES.items():
            self.language_select.addItem(name, code)
        self.language_select.setCurrentIndex(list(LANGUAGES).index(self.language))
        self.language_select.setMinimumWidth(146)
        h.addWidget(self.language_select)
        h.addWidget(self.btn("help", "quiet", self.show_help))
        outer.addWidget(header)
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(23, 25, 23, 18)
        side.setSpacing(16)
        side.addWidget(self.text("import_section", "section"))
        card = QFrame()
        card.setObjectName("fileCard")
        c = QVBoxLayout(card)
        c.setContentsMargins(16, 16, 16, 16)
        c.setSpacing(10)
        c.addWidget(self.text("supported_short", "eyebrow", True))
        self.file_name = self.text("choose", "fileName", True)
        self.file_name.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.file_name.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        c.addWidget(self.file_name)
        self.file_meta = self.text("supported_short", "small", True)
        c.addWidget(self.file_meta)
        self.import_button = self.btn("open", callback=self.choose_file)
        c.addWidget(self.import_button)
        side.addWidget(card)
        self.status_card = QFrame()
        self.status_card.setObjectName("statCard")
        stat = QVBoxLayout(self.status_card)
        stat.setContentsMargins(16, 13, 16, 13)
        self.pages_stat = self.text("waiting", "fileName", True)
        self.detect_stat = self.text("analyze_hint", "muted", True)
        self.protect_stat = self.text("resolution", "small", True)
        for widget in (self.pages_stat, self.detect_stat, self.protect_stat):
            stat.addWidget(widget)
        side.addWidget(self.status_card)
        divider = QFrame()
        divider.setObjectName("divider")
        side.addWidget(divider)
        side.addWidget(self.text("settings", "section"))
        self.auto = QCheckBox()
        self.staff = QCheckBox()
        for widget, key in ((self.auto, "auto"), (self.staff, "staff")):
            widget.setChecked(True)
            self.bindings.append((widget, key))
            side.addWidget(widget)
        strength_row = QHBoxLayout()
        strength_row.addWidget(self.text("strength", "muted"))
        strength_row.addStretch()
        self.strength_value = self.text("automatic", "small")
        strength_row.addWidget(self.strength_value)
        side.addLayout(strength_row)
        self.strength = QSlider(Qt.Orientation.Horizontal)
        # Strength always increases left to right, even in an RTL interface.
        self.strength.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.strength.setRange(0, 70)
        self.strength.setValue(35)
        self.strength.setEnabled(False)
        side.addWidget(self.strength)
        scale_widget = QWidget()
        scale_widget.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        scale = QHBoxLayout(scale_widget)
        scale.setContentsMargins(0, 0, 0, 0)
        scale.addWidget(self.text("gentle", "small"))
        scale.addStretch()
        scale.addWidget(self.text("strong", "small"))
        side.addWidget(scale_widget)
        side.addWidget(self.text("limit", "small", True))
        side.addStretch(1)
        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.hide()
        side.addWidget(self.progress)
        self.cancel_button = self.btn("cancel", "quiet", self.cancel)
        self.cancel_button.hide()
        side.addWidget(self.cancel_button)
        self.export_button = self.btn("export", "primary", self.export_pdf)
        self.export_button.setEnabled(False)
        side.addWidget(self.export_button)
        self.folder_button = self.btn("folder", "quiet", self.open_folder)
        self.folder_button.hide()
        side.addWidget(self.folder_button)
        self.footer = label("", "small", True)
        side.addWidget(self.footer)
        self.side_scroll = QScrollArea()
        self.side_scroll.setWidgetResizable(True)
        self.side_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.side_scroll.setFixedWidth(345)
        self.side_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.side_scroll.setWidget(sidebar)
        body.addWidget(self.side_scroll)
        main = QVBoxLayout()
        main.setContentsMargins(25, 23, 25, 16)
        main.setSpacing(13)
        main.addWidget(self.text("workspace", "title"))
        self.subtitle = self.text("subtitle", "muted", True)
        main.addWidget(self.subtitle)
        tab_frame = QFrame()
        tab_frame.setObjectName("tabBar")
        tabs = QHBoxLayout(tab_frame)
        tabs.setContentsMargins(4, 4, 4, 4)
        self.tabs = QButtonGroup(self)
        for index, key in enumerate(("cleaned", "original", "compare", "changes")):
            widget = self.btn(key, "tab")
            widget.setCheckable(True)
            self.tabs.addButton(widget, index)
            tabs.addWidget(widget)
        self.tabs.button(0).setChecked(True)
        self.tabs.idClicked.connect(self.refresh_preview)
        main.addWidget(tab_frame)
        toolbar = QHBoxLayout()
        self.page_select = QComboBox()
        self.page_select.setMinimumWidth(190)
        self.page_select.setEnabled(False)
        self.page_select.currentIndexChanged.connect(self.refresh_preview)
        toolbar.addWidget(self.page_select)
        toolbar.addStretch()
        self.zoom_label = label("100%", "small")
        self.zoom_label.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        toolbar.addWidget(button("−", "quiet", lambda: self.view.zoom(1 / 1.2)))
        toolbar.addWidget(self.zoom_label)
        toolbar.addWidget(button("+", "quiet", lambda: self.view.zoom(1.2)))
        toolbar.addWidget(self.btn("fit", "quiet", lambda: self.view.fit_page()))
        toolbar.addWidget(self.btn("width", "quiet", lambda: self.view.fit_width()))
        main.addLayout(toolbar)
        self.stack = QStackedWidget()
        empty = QWidget()
        layout = QVBoxLayout(empty)
        layout.addStretch()
        icon = QLabel()
        icon.setPixmap(app_icon().pixmap(80, 80))
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon)
        layout.addSpacing(16)
        for key, style in (("drop", "title"), ("drop_sub", "muted")):
            widget = self.text(key, style, True)
            widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(widget)
        layout.addSpacing(20)
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(self.btn("open", "primary", self.choose_file))
        row.addStretch()
        layout.addLayout(row)
        layout.addStretch()
        features = self.text("features", "small", True)
        features.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(features)
        layout.addSpacing(20)
        self.stack.addWidget(empty)
        self.view = ScoreView()
        self.view.zoomChanged.connect(self.zoom_label.setText)
        self.stack.addWidget(self.view)
        main.addWidget(self.stack, 1)
        bottom = QHBoxLayout()
        self.message = label("", "small", True)
        self.message.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        bottom.addWidget(self.message)
        self.report_button = self.btn("report", "quiet", self.export_report)
        self.report_button.setEnabled(False)
        bottom.addWidget(self.report_button)
        main.addLayout(bottom)
        body.addLayout(main, 1)
        outer.addLayout(body, 1)

    def change_language(self, *_):
        self.language = self.language_select.currentData()
        app = QApplication.instance()
        app.removeTranslator(self.qt_translator)
        qt_locale = {"zh": "zh_CN", "ru": "ru"}.get(self.language)
        if qt_locale and self.qt_translator.load("qtbase_" + qt_locale, QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)):
            app.installTranslator(self.qt_translator)
        if self.preferences is not None:
            self.preferences.setValue("language", self.language)
        rtl = self.language == "ug"
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft if rtl else Qt.LayoutDirection.LeftToRight)
        font = "Tahoma" if rtl else "Microsoft YaHei UI" if self.language == "zh" else "Segoe UI"
        # Arabic joining is broken by letter spacing: no tracking in Uyghur text.
        self.setStyleSheet(f"QWidget {{ font-family: '{font}'; }}" +
                          ("QWidget { font-size: 15px; } QLabel#small { font-size: 13px; } QLabel#muted { font-size: 14px; } QLabel#title, QLabel#brand, QLabel#section, QLabel#eyebrow { letter-spacing: 0px; }" if rtl else ""))
        self.view.caption_font = font
        self.setWindowTitle(self.t("window"))
        for widget, key in self.bindings:
            widget.setText(self.t(key))
        self.footer.setText(self.t("footer", version=__version__))
        self.strength.setToolTip(self.t("strength_tip"))
        self.strength_value.setText(self.t("automatic") if self.auto.isChecked() else f"{self.strength.value()} / 70")
        if self.source:
            self.file_name.setText(isolated(self.source.name))
        if self.prepared:
            self.update_stats()
            self.refresh_preview()
        elif self.busy:
            self.file_meta.setText(self.t("reading"))
        self.set_message(self._message)

    def set_message(self, message):
        self._message = message
        self.message.setText(self.t(message))

    @property
    def busy(self):
        return self.worker is not None

    def popup(self, key, *, question=False, title="error_title"):
        box = QMessageBox(self)
        box.setLayoutDirection(self.layoutDirection())
        box.setWindowTitle(self.t(title))
        box.setText(self.t(key))
        box.setTextFormat(Qt.TextFormat.PlainText)
        box.setIcon(QMessageBox.Icon.Question if question else QMessageBox.Icon.Information)
        accept = box.addButton(self.t("ok"), QMessageBox.ButtonRole.AcceptRole)
        if question:
            cancel = box.addButton(self.t("cancel"), QMessageBox.ButtonRole.RejectRole)
            box.setDefaultButton(cancel)
        box.exec()
        return box.clickedButton() is accept

    def file_dialog(self, save=False, suggestion="", filters=None, caption="open"):
        # A non-native dialog follows the selected app language, not the OS language.
        dialog = QFileDialog(self, self.t(caption))
        dialog.setLayoutDirection(self.layoutDirection())
        dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)
        dialog.setOption(QFileDialog.Option.DontConfirmOverwrite, True)
        dialog.setOption(QFileDialog.Option.HideNameFilterDetails, True)
        dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave if save else QFileDialog.AcceptMode.AcceptOpen)
        dialog.setFileMode(QFileDialog.FileMode.AnyFile if save else QFileDialog.FileMode.ExistingFile)
        dialog.setNameFilters(filters or self.import_filters())
        for role, key in ((QFileDialog.DialogLabel.LookIn, "lookin"), (QFileDialog.DialogLabel.FileName, "filename"),
                          (QFileDialog.DialogLabel.FileType, "filetype"), (QFileDialog.DialogLabel.Accept, "save" if save else "open"),
                          (QFileDialog.DialogLabel.Reject, "cancel")):
            dialog.setLabelText(role, self.t(key))
        for name, key in (("backButton", "back"), ("forwardButton", "forward"), ("toParentButton", "up"),
                          ("newFolderButton", "new_folder"), ("listModeButton", "list_view"), ("detailModeButton", "detail_view")):
            widget = dialog.findChild(QToolButton, name)
            if widget:
                widget.setToolTip(self.t(key))
                widget.setAccessibleName(self.t(key))
        dialog.setViewMode(QFileDialog.ViewMode.List)
        filename_edit = dialog.findChild(QLineEdit, "fileNameEdit")
        if filename_edit:
            filename_edit.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        folder_select = dialog.findChild(QComboBox, "lookInCombo")
        if folder_select:
            folder_select.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        sidebar = dialog.findChild(QListView, "sidebar")
        if sidebar and self.language == "ug":
            model = sidebar.model()
            for row in range(model.rowCount()):
                index = model.index(row, 0)
                if model.data(index) in ("My Computer", "Computer"):
                    model.setData(index, self.t("computer"), Qt.ItemDataRole.DisplayRole)
        # List mode avoids OS-localized column headers and file type descriptions.
        tree = dialog.findChild(QTreeView, "treeView")
        if tree:
            tree.header().hide()
        if suggestion:
            dialog.setDirectory(str(Path(suggestion).parent))
            dialog.selectFile(Path(suggestion).name)
        elif self.source:
            dialog.setDirectory(str(self.source.parent))
        dialog.resize(850, 560)
        if not dialog.exec():
            return "", ""
        return dialog.selectedFiles()[0], dialog.selectedNameFilter()

    def import_filters(self):
        image_patterns = " ".join("*" + e for e in sorted(IMAGE_EXTENSIONS))
        return [f"{self.t('all_supported')} (*.pdf *.docx {image_patterns})", "PDF (*.pdf)",
                f"{self.t('images')} ({image_patterns})", f"{self.t('documents')} (*.docx)"]

    def choose_file(self):
        if not self.busy:
            path, _ = self.file_dialog()
            if path:
                self.load_file(path)

    def load_file(self, path):
        if self.busy:
            return
        path = Path(path)
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            self.popup("legacy_word" if path.suffix.lower() == ".doc" else "unsupported")
            return
        self.debounce.stop()
        self.source = path
        self.prepared = None
        self.exported = None
        self._preview_cache.clear()
        self._had_preview = False
        self.stack.setCurrentIndex(0)
        self.page_select.clear()
        self.page_select.setEnabled(False)
        self.folder_button.hide()
        self.file_name.setText(isolated(path.name))
        self.file_name.setToolTip(str(path))
        self.file_meta.setText(self.t("reading"))
        self.auto.blockSignals(True)
        self.auto.setChecked(True)
        self.auto.blockSignals(False)
        self.strength_value.setText(self.t("automatic"))
        self.process()

    def current_settings(self):
        return Settings(None if self.auto.isChecked() else 240 - self.strength.value(), self.staff.isChecked())

    def settings_changed(self, *_):
        self.strength.setEnabled(not self.auto.isChecked() and not self.busy)
        self.strength_value.setText(self.t("automatic") if self.auto.isChecked() else f"{self.strength.value()} / 70")
        if self.source and not self.busy:
            self.export_button.setEnabled(False)
            self.report_button.setEnabled(False)
            self.set_message(Message("updating"))
            self.debounce.start()

    def process(self):
        if not self.source or self.busy:
            return
        self.debounce.stop()
        self._set_busy(True)
        self.set_message(Message("processing"))
        self.worker = ProcessJob(self.source, self.current_settings(), self)
        self.worker.progress.connect(self.on_progress)
        self.worker.result.connect(self.on_result)
        self.worker.error.connect(self.on_error)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()

    def _set_busy(self, state):
        for control in (self.import_button, self.auto, self.staff):
            control.setEnabled(not state)
        self.strength.setEnabled(not state and not self.auto.isChecked())
        self.progress.setVisible(state)
        self.cancel_button.setVisible(state)
        self.export_button.setEnabled(not state and self.prepared is not None)
        self.report_button.setEnabled(not state and self.prepared is not None)
        if state:
            self.progress.setValue(0)
            self.cancel_button.setEnabled(True)

    def on_progress(self, number, message):
        self.progress.setValue(number)
        self.set_message(message)

    def update_stats(self):
        prepared = self.prepared
        report = prepared.report
        count = report.page_count
        index = max(0, self.page_select.currentIndex())
        self.page_select.blockSignals(True)
        self.page_select.clear()
        for number in range(count):
            suffix = "" if number + 1 in report.processed_pages else self.t("unchanged_suffix")
            self.page_select.addItem(self.t(prepared.item_key, n=number + 1, count=count) + suffix)
        self.page_select.setCurrentIndex(min(index, count - 1))
        self.page_select.blockSignals(False)
        self.page_select.setEnabled(True)
        self.file_meta.setText(self.t("file_meta", count=count, size=len(prepared.source_bytes) / 1024 / 1024))
        self.pages_stat.setText(self.t("processed", done=len(report.processed_pages), count=count))
        self.detect_stat.setText(self.t("detected" if any(i.detected for i in report.images) else "not_detected"))
        dark = sum(i.protected_dark_pixels for i in report.images)
        self.protect_stat.setText(self.t("dark_kept", count=dark) if dark else self.t("nothing_changed"))
        self.subtitle.setText(self.t("docx_preview" if prepared.kind == "docx" else "resolution"))

    def on_result(self, prepared):
        self.prepared = prepared
        self.exported = None
        self.folder_button.hide()
        self._preview_cache.clear()
        self.update_stats()
        if self.auto.isChecked():
            thresholds = [i.threshold for i in prepared.report.images if i.threshold]
            if thresholds:
                self.strength.blockSignals(True)
                self.strength.setValue(240 - int(sum(thresholds) / len(thresholds)))
                self.strength.blockSignals(False)
        self.set_message(prepared.report.warnings[0] if prepared.report.warnings else Message("navigation"))
        self.stack.setCurrentIndex(1)
        self.refresh_preview(reset=True)
        self._had_preview = True

    def on_error(self, message):
        self.prepared = None
        self._preview_cache.clear()
        self.stack.setCurrentIndex(0)
        self.page_select.setEnabled(False)
        self.pages_stat.setText(self.t("failed"))
        self.detect_stat.setText(self.t("check_file"))
        self.protect_stat.setText(self.t("source_kept"))
        self.set_message(message)
        if not self._closing:
            self.popup(message)

    def on_finished(self):
        cancelled = self.worker.isInterruptionRequested() if self.worker else False
        if cancelled:
            self.prepared = None
            self.stack.setCurrentIndex(0)
            self.set_message(Message("cancelled"))
            self.pages_stat.setText(self.t("cancelled"))
            self.page_select.setEnabled(False)
        self._set_busy(False)
        if self.worker:
            self.worker.deleteLater()
        self.worker = None
        if self._closing:
            self.close()

    def cancel(self):
        if self.busy:
            self.worker.requestInterruption()
            self.cancel_button.setEnabled(False)
            self.set_message(Message("cancelling"))

    def refresh_preview(self, *_args, reset=False):
        if not self.prepared:
            return
        index = max(0, self.page_select.currentIndex())
        try:
            if index not in self._preview_cache:
                if len(self._preview_cache) >= 3:
                    self._preview_cache.pop(next(iter(self._preview_cache)))
                self._preview_cache[index] = self.prepared.preview(index)
            original, cleaned = self._preview_cache[index]
            mode = self.tabs.checkedId()
            if mode == 0:
                images, keys = [cleaned], ["cleaned"]
            elif mode == 1:
                images, keys = [original], ["original"]
            elif mode == 2:
                images, keys = [original, cleaned], ["original", "cleaned"]
            else:
                images, keys = [difference_image(original, cleaned)], ["difference_caption"]
            self.view.show_images(images, [self.t(k) for k in keys], reset=reset or mode == 2 or not self._had_preview)
        except Exception:
            self.set_message(Message("preview_failed"))

    def export_filters(self):
        if self.prepared.kind == "pdf":
            return ["PDF (*.pdf)"]
        if self.prepared.kind == "docx":
            return ["Word DOCX (*.docx)"]
        if len(self.prepared.frames) > 1:
            return ["TIFF (*.tiff *.tif)", "PDF (*.pdf)"]
        return ["PNG (*.png)", "TIFF (*.tiff *.tif)", "WebP (*.webp)", "PDF (*.pdf)", self.t("lossy") + " (*.jpg *.jpeg)"]

    def export_pdf(self):
        # Retained method name for existing shortcuts; exports the actual file type.
        if self.busy or self.debounce.isActive() or not self.prepared:
            return
        suggestion = self.source.with_name(self.source.stem + "_clean" + self.prepared.default_suffix)
        target, chosen_filter = self.file_dialog(True, str(suggestion), self.export_filters(), "export")
        if not target:
            return
        target = Path(target)
        import re
        extensions = re.findall(r"\*([.][a-z0-9]+)", chosen_filter)
        if extensions and target.suffix.lower() not in extensions:
            target = target.with_suffix(extensions[0])
        elif not target.suffix:
            target = target.with_suffix(self.prepared.default_suffix)
        try:
            if target.resolve() == self.source.resolve() or (target.exists() and os.path.samefile(target, self.source)):
                raise CleanupError("overwrite_source")
            if target.exists() and not self.popup("replace", question=True, title="save"):
                return
            if target.suffix.lower() in (".jpg", ".jpeg") and not self.popup("jpeg_confirm", question=True, title="save"):
                return
            self.exported = save_document(self.prepared, target, self.source)
            self.folder_button.show()
            self.set_message(Message("saved", {"name": isolated(self.exported.name)}))
            self.message.setToolTip(str(self.exported))
        except CleanupError as exc:
            self.popup(exc.message)

    def export_report(self):
        if not self.prepared or self.busy or self.debounce.isActive():
            return
        target, _ = self.file_dialog(True, str(self.source.with_name(self.source.stem + "_report.json")), ["JSON (*.json)"], "report")
        if not target:
            return
        target = Path(target)
        if not target.suffix:
            target = target.with_suffix(".json")
        try:
            if target.resolve() == self.source.resolve() or (target.exists() and os.path.samefile(target, self.source)):
                raise CleanupError("overwrite_source")
            if target.exists() and not self.popup("replace", question=True, title="save"):
                return
            payload = self.prepared.report.to_dict()
            payload["language"] = self.language
            payload["format"] = self.prepared.kind
            payload["messages"] = [self.t(m) for m in self.prepared.report.warnings]
            write_atomic(json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"), target, self.source)
            self.set_message(Message("report_saved"))
        except CleanupError as exc:
            self.popup(exc.message)

    def open_folder(self):
        if self.exported:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.exported.parent)))

    def show_help(self):
        self.popup("help_body", title="help")

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() and not self.busy:
            if any(u.isLocalFile() and Path(u.toLocalFile()).suffix.lower() in SUPPORTED_EXTENSIONS | {".doc"} for u in event.mimeData().urls()):
                event.acceptProposedAction()

    def dropEvent(self, event):
        if self.busy:
            return
        for url in event.mimeData().urls():
            if url.isLocalFile() and Path(url.toLocalFile()).suffix.lower() in SUPPORTED_EXTENSIONS | {".doc"}:
                self.load_file(url.toLocalFile())
                event.acceptProposedAction()
                break

    def closeEvent(self, event):
        self.debounce.stop()
        if self.busy:
            self._closing = True
            self.worker.requestInterruption()
            event.ignore()
        else:
            event.accept()


def configure_app(app):
    if sys.platform == "win32" and not QFontDatabase.families():
        fonts = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
        for font in ("msyh.ttc", "msyhbd.ttc", "segoeui.ttf", "tahoma.ttf", "tahomabd.ttf"):
            if (fonts / font).exists():
                QFontDatabase.addApplicationFont(str(fonts / font))
    app.setApplicationName("ClearScore")
    app.setOrganizationName("ClearScore")
    app.setStyle("Fusion")
    # Windows can supply a dark palette even while the app uses light CSS.
    # Set the complete palette so file lists, inputs and dialogs stay readable.
    palette = QPalette()
    for role, color in (
        (QPalette.ColorRole.Window, "#f3f5f2"), (QPalette.ColorRole.WindowText, "#273a34"),
        (QPalette.ColorRole.Base, "#ffffff"), (QPalette.ColorRole.AlternateBase, "#f5f8f4"),
        (QPalette.ColorRole.Text, "#273a34"), (QPalette.ColorRole.Button, "#ffffff"),
        (QPalette.ColorRole.ButtonText, "#273a34"), (QPalette.ColorRole.Highlight, "#2e6651"),
        (QPalette.ColorRole.HighlightedText, "#ffffff"),
    ):
        palette.setColor(role, QColor(color))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor("#98a69d"))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor("#98a69d"))
    app.setPalette(palette)
    app.setStyleSheet(STYLE)
    app.setWindowIcon(app_icon())


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    configure_app(app)
    preferences = QSettings()
    system_language = QLocale.system().name().split("_")[0]
    language = preferences.value("language", system_language if system_language in LANGUAGES else "en")
    window = MainWindow(language, preferences)
    window.show()
    if len(sys.argv) > 1 and Path(sys.argv[1]).suffix.lower() in SUPPORTED_EXTENSIONS | {".doc"}:
        QTimer.singleShot(100, lambda: window.load_file(sys.argv[1]))
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
