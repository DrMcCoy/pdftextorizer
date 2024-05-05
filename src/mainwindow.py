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

from PyQt5.QtCore import QEvent, Qt
from PyQt5.QtGui import QImage, QKeySequence, QPalette, QPixmap
from PyQt5.QtWidgets import QAction, QFileDialog, QLabel, QMainWindow, QMessageBox, QSizePolicy, QStatusBar, QStyle

from pdffile import PDFFile
from util import Util


class MainWindow(QMainWindow):
    """! PDF Textorizer main window.
    """

    def __init__(self, args: argparse.Namespace) -> None:
        super().__init__()

        self._args = args

        self._pdf_filename: Optional[str] = None
        self._pdf: Optional[PDFFile] = None

        self._set_window_title()
        self.setStatusBar(QStatusBar(self))

        self._create_menu()
        self._create_viewport()

        self.resize(500, 500)

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

    def _create_viewport(self) -> None:
        self._page_image = QImage()
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
        except (FileNotFoundError, ValueError) as err:
            self._show_error(str(err), "Can't open PDF")
            return

        self._pdf_filename = filename
        self._set_window_title()

        self._page_image = self._pdf.render_page(0) or QImage()

        width = self._page_view.width()
        height = self._page_view.height()
        aspect_ratio_mode = Qt.KeepAspectRatio  # type: ignore[attr-defined]
        transform_mode = Qt.SmoothTransformation  # type: ignore[attr-defined]

        self._page_view.setPixmap(QPixmap.fromImage(self._page_image).scaled(width, height,
                                                                             aspectRatioMode=aspect_ratio_mode,
                                                                             transformMode=transform_mode))

    def _close_pdf(self) -> None:
        self._pdf = None
        self._pdf_filename = None

        self._set_window_title()
        self._page_view.setPixmap(QPixmap())

    def _open_pdf_file(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(self, "Open PDF", filter="PDF files (*.pdf)")
        if not filename or filename == '':
            return

        self._open_pdf(filename)

    def eventFilter(self, widget, event):  # pylint: disable=invalid-name
        """! Special event handling for the main window.
        """

        if event.type() == QEvent.Resize and widget is self._page_view:
            width = self._page_view.width()
            height = self._page_view.height()
            aspect_ratio_mode = Qt.KeepAspectRatio  # type: ignore[attr-defined]
            transform_mode = Qt.SmoothTransformation  # type: ignore[attr-defined]

            self._page_view.setPixmap(QPixmap.fromImage(self._page_image).scaled(width, height,
                                                                                 aspectRatioMode=aspect_ratio_mode,
                                                                                 transformMode=transform_mode))
            return True
        return super().eventFilter(widget, event)
