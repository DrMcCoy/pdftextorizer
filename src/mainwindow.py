"""! Main window for PDF Textorizer.
"""

# PDF Textorizer - Interactively extract text from multi-column PDFs
#
# PDF Textorizer is the legal property of its developers, whose names
# can be found in the AUTHORS file distributed with this source
# distribution.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import argparse
import sys
from typing import Any, Optional

from PyQt5.QtCore import QEvent, QRectF, Qt
from PyQt5.QtGui import QFont, QImage, QKeySequence, QPainter, QPalette, QPixmap
from PyQt5.QtWidgets import (QAction, QDockWidget, QFileDialog, QFrame, QHBoxLayout, QLabel, QMainWindow, QMessageBox,
                             QPushButton, QSizePolicy, QStatusBar, QStyle, QVBoxLayout, QWidget)

from pdffile import PDFFile
from util import Util


class MainWindow(QMainWindow):
    """! PDF Textorizer main window.
    """

    def __init__(self, args: argparse.Namespace) -> None:
        super().__init__()

        self._args = args

        self._current_page: int = 0
        self._page_image = QPixmap()
        self._viewport_image = QPixmap()

        self._pdf_filename: Optional[str] = None
        self._pdf: Optional[PDFFile] = None

        self._set_window_title()
        self.setStatusBar(QStatusBar(self))

        self._create_menu()
        self._create_dock()
        self._create_viewport()

        self.resize(1200, 800)

        if self._args.file:
            self._open_pdf(self._args.file)

    def _create_menu(self) -> None:
        info: dict[str, Any] = Util.get_project_info()

        style = self.style()
        assert style is not None

        menu = self.menuBar()
        assert menu is not None

        file_menu = menu.addMenu("&File")
        assert file_menu is not None

        open_action = QAction(style.standardIcon(QStyle.SP_DirOpenIcon),  # type: ignore[attr-defined]
                              "&Open PDF", self)
        open_action.setShortcuts(QKeySequence.Open)
        open_action.setStatusTip("Open a new PDF file")
        open_action.triggered.connect(self._open_pdf_file)
        file_menu.addAction(open_action)

        close_action = QAction(style.standardIcon(QStyle.SP_DirClosedIcon),  # type: ignore[attr-defined]
                               "&Close PDF", self)
        close_action.setShortcuts(QKeySequence.Close)
        close_action.setStatusTip("Close the currently opened PDF file")
        close_action.triggered.connect(self._close_pdf)
        file_menu.addAction(close_action)

        file_menu.addSeparator()

        exit_action = QAction("&Quit", self)
        exit_action.setShortcuts(QKeySequence.Quit)
        exit_action.setStatusTip(f"Quit {info['name']}")
        exit_action.triggered.connect(self._close_self)
        file_menu.addAction(exit_action)

        about_menu = menu.addMenu("&About")
        assert about_menu is not None

        about_action = QAction(style.standardIcon(QStyle.SP_FileDialogInfoView),  # type: ignore[attr-defined]
                               f"&About {info['name']}", self)
        about_action.setShortcuts(QKeySequence.WhatsThis)
        about_action.setStatusTip(f"Show information about {info['name']}")
        about_action.triggered.connect(self._show_about)
        about_menu.addAction(about_action)

    def _create_dock(self) -> None:  # pylint: disable=too-many-statements
        style = self.style()
        assert style is not None

        dock = QDockWidget("", self)
        dock.setAllowedAreas(Qt.RightDockWidgetArea)  # type: ignore[attr-defined]
        dock.setFeatures(QDockWidget.NoDockWidgetFeatures)
        dock.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        dock.setTitleBarWidget(QWidget(None))
        dock.setMinimumSize(200, 1)

        self._page_label = QLabel()
        self._page_label.setText("")
        self._page_label.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        self._page_label.setAlignment(Qt.AlignCenter)  # type: ignore[attr-defined]

        page_label_layout = QVBoxLayout()
        page_label_layout.setAlignment(Qt.AlignCenter)  # type: ignore[attr-defined]
        page_label_layout.addWidget(self._page_label)

        page_label_frame = QFrame()
        page_label_frame.setLayout(page_label_layout)
        page_label_frame.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        page_label_frame.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        page_label_frame.setLineWidth(2)
        page_label_frame.setMinimumWidth(80)

        dock_layout = QVBoxLayout()
        dock_layout.setSpacing(0)
        dock_layout.setAlignment(Qt.AlignCenter)  # type: ignore[attr-defined]

        dock_frame = QFrame()
        dock_frame.setFrameStyle(QFrame.Box | QFrame.Sunken)
        dock_frame.setLineWidth(1)
        dock_frame.setContentsMargins(2, 0, 0, 0)
        dock_frame.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)

        dock_frame.setLayout(dock_layout)

        dock.setWidget(dock_frame)

        pages_layout = QHBoxLayout()
        pages_layout.setAlignment(Qt.AlignCenter)  # type: ignore[attr-defined]
        pages_layout.setSpacing(0)
        pages_layout.addWidget(page_label_frame)

        pages = QWidget()
        pages.setLayout(pages_layout)

        dock_layout.addWidget(pages)

        page_button_layout = QHBoxLayout()
        page_button_layout.setAlignment(Qt.AlignCenter)  # type: ignore[attr-defined]
        page_button_layout.setSpacing(5)

        first_page_button = QPushButton(style.standardIcon(QStyle.SP_MediaSkipBackward),  # type: ignore[attr-defined]
                                        "", parent=self)
        first_page_button.setStatusTip("First page")
        first_page_button.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        first_page_button.clicked.connect(self._first_page)
        page_button_layout.addWidget(first_page_button)

        prev_page_button = QPushButton(style.standardIcon(QStyle.SP_MediaSeekBackward),  # type: ignore[attr-defined]
                                       "", parent=self)
        prev_page_button.setStatusTip("Previous page")
        prev_page_button.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        prev_page_button.clicked.connect(self._previous_page)
        page_button_layout.addWidget(prev_page_button)

        next_page_button = QPushButton(style.standardIcon(QStyle.SP_MediaSeekForward),  # type: ignore[attr-defined]
                                       "", parent=self)
        next_page_button.setStatusTip("Next page")
        next_page_button.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        next_page_button.clicked.connect(self._next_page)
        page_button_layout.addWidget(next_page_button)

        last_page_button = QPushButton(style.standardIcon(QStyle.SP_MediaSkipForward),  # type: ignore[attr-defined]
                                       "", parent=self)
        last_page_button.setStatusTip("Last page")
        last_page_button.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        last_page_button.clicked.connect(self._last_page)
        page_button_layout.addWidget(last_page_button)

        page_buttons = QWidget()
        page_buttons.setLayout(page_button_layout)

        dock_layout.addWidget(page_buttons)

        self.addDockWidget(Qt.RightDockWidgetArea, dock, Qt.Vertical)  # type: ignore[attr-defined]
        self._update_page_label()

    def _create_viewport(self) -> None:
        self._page_image = QPixmap()
        self._page_view = QLabel(self)

        self._page_view.setBackgroundRole(QPalette.Base)
        self._page_view.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self._page_view.setScaledContents(False)
        self._page_view.setAlignment(Qt.AlignCenter)  # type: ignore[attr-defined]

        self._page_view.installEventFilter(self)

        self.setCentralWidget(self._page_view)

    def _set_window_title(self) -> None:
        info: dict[str, Any] = Util.get_project_info()
        title: str = f"{info['name']} {info['version']}"

        if self._pdf_filename:
            title += f" -- {self._pdf_filename}"

        self.setWindowTitle(title)

    def _show_error(self, error: str, where: Optional[str] = None) -> None:
        message = error
        if where:
            message = where + ": " + message

        if self.isHidden():
            print(message, file=sys.stderr)
            return

        dlg = QMessageBox(self)
        dlg.setIcon(QMessageBox.Critical)
        dlg.setWindowTitle("Error")
        dlg.setText(message)
        dlg.exec()

    def _rescale_page(self) -> None:
        width = self._page_view.width()
        height = self._page_view.height()
        aspect_ratio_mode = Qt.KeepAspectRatio  # type: ignore[attr-defined]
        transform_mode = Qt.SmoothTransformation  # type: ignore[attr-defined]

        self._page_view.setPixmap(self._viewport_image.scaled(width, height,
                                                              aspectRatioMode=aspect_ratio_mode,
                                                              transformMode=transform_mode))

    def _update_page(self) -> None:
        if not self._pdf:
            self._page_view.setPixmap(QPixmap())
            return

        page_image = self._pdf.render_page(self._current_page) or QImage()
        self._page_image = QPixmap.fromImage(page_image)

        self._viewport_image = self._page_image.copy()

        regions = self._pdf.get_regions(self._current_page)
        assert regions is not None

        paint = QPainter(self._viewport_image)
        paint.setPen(Qt.red)  # type: ignore[attr-defined]

        font = QFont()
        font.setFamily(font.defaultFamily())
        font.setPointSize(12)
        paint.setFont(font)

        for i, region in enumerate(regions):
            left = region.x0
            top = region.y0
            width = region.x1 - region.x0
            height = region.y1 - region.y0

            paint.drawRect(left, top, width, height)
            paint.drawText(QRectF(left, top, 1000, 1000), f" {i}")

        self._rescale_page()

    def _update_page_label(self) -> None:
        if not self._pdf:
            self._page_label.setText("? / ?")
            return

        self._page_label.setText(f"{self._current_page + 1} / {self._pdf.page_count}")

    def _close_self(self) -> None:
        self.close()

    def _show_about(self) -> None:
        info: dict[str, Any] = Util.get_project_info()

        dlg = QMessageBox(self)
        dlg.setWindowTitle(f"About {info['name']}")
        dlg.setText(Util.get_version_string())
        dlg.exec()

    def _open_pdf(self, filename) -> None:
        self._close_pdf()

        try:
            self._pdf = PDFFile(filename)
            if self._pdf.page_count == 0:
                raise ValueError("PDF has no pages")

        except (FileNotFoundError, ValueError) as err:
            self._show_error(str(err), "Can't open PDF")
            return

        self._pdf_filename = filename
        self._set_window_title()

        self._current_page = 0
        self._update_page_label()
        self._update_page()

    def _close_pdf(self) -> None:
        self._pdf = None
        self._pdf_filename = None

        self._set_window_title()

        self._current_page = 0
        self._update_page_label()
        self._update_page()

    def _open_pdf_file(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(self, "Open PDF", filter="PDF files (*.pdf)")
        if not filename or filename == '':
            return

        self._open_pdf(filename)

    def _first_page(self) -> None:
        if not self._pdf:
            return

        self._current_page = 0
        self._update_page_label()
        self._update_page()

    def _previous_page(self) -> None:
        if not self._pdf:
            return

        if self._current_page == 0:
            return

        self._current_page -= 1
        self._update_page_label()
        self._update_page()

    def _next_page(self) -> None:
        if not self._pdf:
            return

        if self._current_page >= (self._pdf.page_count - 1):
            return

        self._current_page += 1
        self._update_page_label()
        self._update_page()

    def _last_page(self) -> None:
        if not self._pdf:
            return

        self._current_page = self._pdf.page_count - 1
        self._update_page_label()
        self._update_page()

    def eventFilter(self, widget, event):  # pylint: disable=invalid-name
        """! Special event handling for the main window.
        """

        if event.type() == QEvent.Resize and widget is self._page_view:
            self._rescale_page()
            return True
        return super().eventFilter(widget, event)
