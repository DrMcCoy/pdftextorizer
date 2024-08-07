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
import json
import sys
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from PyQt5.QtCore import QEvent, QPoint, QRect, QRectF, Qt
from PyQt5.QtGui import QFont, QImage, QKeyEvent, QKeySequence, QMouseEvent, QPainter, QPalette, QPixmap
from PyQt5.QtWidgets import (QAction, QApplication, QCheckBox, QDockWidget, QFileDialog, QFrame, QGridLayout,
                             QHBoxLayout, QLabel, QMainWindow, QMessageBox, QProgressDialog, QPushButton, QSizePolicy,
                             QSpinBox, QStackedWidget, QStatusBar, QStyle, QVBoxLayout, QWidget)

from pdffile import PDFFile
from util import Util


class OperationMode(Enum):
    """! The different operation modes PDF Textorizer can be in.
    """
    NORMAL = 0
    ADD_REGION = 1
    REDRAW_REGION = 2


class PageNumberLabel(QLabel):
    """! The label showing the current page.
    """

    def __init__(self, page_stack, index_other: int) -> None:
        super().__init__()
        self._page_stack = page_stack
        self._index_other = index_other

    def mouseReleaseEvent(self, _):  # pylint: disable=invalid-name
        """! Mouse button release event handler.
        """

        self._page_stack.setCurrentIndex(self._index_other)
        self._page_stack.currentWidget().setFocus()


class PageNumberEdit(QSpinBox):
    """! The edit box showing and allowing to modify the current page.
    """

    def __init__(self, page_stack, index_other: int) -> None:
        super().__init__()
        self._page_stack = page_stack
        self._index_other = index_other

    def focusOutEvent(self, event):  # pylint: disable=invalid-name
        """! Focus out event handler.
        """

        self._page_stack.setCurrentIndex(self._index_other)
        super().focusOutEvent(event)


class MainWindow(QMainWindow):
    """! PDF Textorizer main window.
    """

    def __init__(self, args: argparse.Namespace) -> None:
        super().__init__()

        self._args = args

        self._op_mode = OperationMode.NORMAL

        self._current_page: int = 0
        self._page_image = QPixmap()
        self._viewport_image = QPixmap()
        self._viewport_scaled_image = QPixmap()

        self._new_region = QRect()

        self._pdf: Optional[PDFFile] = None

        self._current_region: int = -1
        self._regions_filename: Optional[str] = None
        self._regions_modified: bool = False

        self._set_window_title()
        self.setStatusBar(QStatusBar(self))

        self._create_menu()
        self._create_dock()
        self._create_viewport()

        self.resize(1200, 800)

        if self._args.pdf_file:
            if self._open_pdf(self._args.pdf_file):
                if self._args.regions_file:
                    self._regions_filename = self._args.regions_file
                    self._set_window_title()
                if self._args.page is not None:
                    self._go_to_page(self._args.page)

    def _create_menu(self) -> None:  # pylint: disable=too-many-statements,too-many-locals
        info: dict[str, Any] = Util.get_project_info()

        style = self.style()
        assert style is not None

        menu = self.menuBar()
        assert menu is not None

        file_menu = menu.addMenu("&File")
        assert file_menu is not None

        open_action = QAction("&Open PDF", self)
        open_action.setShortcuts(QKeySequence(Qt.CTRL + Qt.Key_O))  # type: ignore[attr-defined]
        open_action.setStatusTip("Open a new PDF file")
        open_action.triggered.connect(self._open_pdf_file)
        file_menu.addAction(open_action)

        close_action = QAction("&Close PDF", self)
        close_action.setShortcuts(QKeySequence.Close)
        close_action.setStatusTip("Close the currently opened PDF file")
        close_action.triggered.connect(self._close_pdf)
        file_menu.addAction(close_action)

        file_menu.addSeparator()

        load_regions = QAction("&Load Regions", self)
        load_regions.setShortcuts(QKeySequence(Qt.CTRL + Qt.SHIFT + Qt.Key_O))   # type: ignore[attr-defined]
        load_regions.setStatusTip("Load the regions for the currently opened PDF from file")
        load_regions.triggered.connect(self._load_regions)
        file_menu.addAction(load_regions)
        self._action_load_regions = load_regions

        save_regions_as = QAction("Save Regions &As...", self)
        save_regions_as.setShortcuts(QKeySequence(Qt.CTRL + Qt.SHIFT + Qt.Key_S))  # type: ignore[attr-defined]
        save_regions_as.setStatusTip("Save all of the currently opened PDF file into a new regions file")
        save_regions_as.triggered.connect(self._save_regions_as)
        file_menu.addAction(save_regions_as)
        self._action_save_regions_as = save_regions_as

        save_regions = QAction("&Save Regions", self)
        save_regions.setShortcuts(QKeySequence(Qt.CTRL + Qt.Key_S))  # type: ignore[attr-defined]
        save_regions.setStatusTip("Save all regions of the currently opened PDF file")
        save_regions.triggered.connect(self._save_regions)
        file_menu.addAction(save_regions)
        self._action_save_regions = save_regions

        file_menu.addSeparator()

        convert_page = QAction("Convert &Page to Text", self)
        convert_page.setShortcuts(QKeySequence(Qt.CTRL + Qt.Key_P))  # type: ignore[attr-defined]
        convert_page.setStatusTip("Convert all regions of the current page to text and print it to stdout")
        convert_page.triggered.connect(self._convert_page_to_text_print)
        file_menu.addAction(convert_page)
        self._action_convert_page = convert_page

        save_page = QAction("Save Page to Text", self)
        save_page.setShortcuts(QKeySequence(Qt.CTRL + Qt.Key_T))  # type: ignore[attr-defined]
        save_page.setStatusTip("Convert all regions of the current page to text and save it into a file")
        save_page.triggered.connect(self._convert_page_to_text_file)
        file_menu.addAction(save_page)
        self._action_save_page = save_page

        save_all_pages = QAction("Save All Pages to Text", self)
        save_all_pages.setShortcuts(QKeySequence(Qt.CTRL + Qt.SHIFT + Qt.Key_T))  # type: ignore[attr-defined]
        save_all_pages.setStatusTip("Convert all regions of all pages currently opened PDF to text "
                                    "and save it into a file")
        save_all_pages.triggered.connect(self._convert_all_pages_to_text_file)
        file_menu.addAction(save_all_pages)
        self._action_save_all_pages = save_all_pages

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

    def _create_dock(self) -> None:  # pylint: disable=too-many-statements,too-many-locals
        style = self.style()
        assert style is not None

        dock = QDockWidget("", self)
        dock.setAllowedAreas(Qt.RightDockWidgetArea)  # type: ignore[attr-defined]
        dock.setFeatures(QDockWidget.NoDockWidgetFeatures)
        dock.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        dock.setTitleBarWidget(QWidget(None))
        dock.setMinimumSize(320, 1)

        self._page_stack = QStackedWidget()

        self._page_label = PageNumberLabel(self._page_stack, 1)
        self._page_label.setText("")
        self._page_label.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        self._page_label.setAlignment(Qt.AlignCenter)  # type: ignore[attr-defined]

        self._page_edit = PageNumberEdit(self._page_stack, 0)
        self._page_edit.setRange(0, 0)
        self._page_edit.setValue(0)
        self._page_edit.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        self._page_edit.valueChanged.connect(self._modify_page_edit)

        self._page_stack.addWidget(self._page_label)
        self._page_stack.addWidget(self._page_edit)
        self._page_stack.setCurrentWidget(self._page_label)

        page_label_layout = QVBoxLayout()
        page_label_layout.setAlignment(Qt.AlignCenter)  # type: ignore[attr-defined]
        page_label_layout.addWidget(self._page_stack)

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

        first_page_button = QPushButton(style.standardIcon(QStyle.SP_MediaSkipBackward),  # type: ignore[attr-defined]
                                        "", parent=self)
        first_page_button.setStatusTip("First page")
        first_page_button.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        first_page_button.clicked.connect(self._first_page)

        prev_page_button = QPushButton(style.standardIcon(QStyle.SP_MediaSeekBackward),  # type: ignore[attr-defined]
                                       "", parent=self)
        prev_page_button.setStatusTip("Previous page")
        prev_page_button.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        prev_page_button.clicked.connect(self._previous_page)

        next_page_button = QPushButton(style.standardIcon(QStyle.SP_MediaSeekForward),  # type: ignore[attr-defined]
                                       "", parent=self)
        next_page_button.setStatusTip("Next page")
        next_page_button.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        next_page_button.clicked.connect(self._next_page)

        last_page_button = QPushButton(style.standardIcon(QStyle.SP_MediaSkipForward),  # type: ignore[attr-defined]
                                       "", parent=self)
        last_page_button.setStatusTip("Last page")
        last_page_button.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        last_page_button.clicked.connect(self._last_page)

        pages_layout.addWidget(first_page_button)
        pages_layout.addWidget(prev_page_button)
        pages_layout.addWidget(page_label_frame)
        pages_layout.addWidget(next_page_button)
        pages_layout.addWidget(last_page_button)

        pages = QWidget()
        pages.setLayout(pages_layout)

        pages_label = QLabel("Pages:")
        pages_label.setAlignment(Qt.AlignCenter)  # type: ignore[attr-defined]
        dock_layout.addWidget(pages_label)
        dock_layout.addWidget(pages)

        margins_label = QLabel("Margins:")
        margins_label.setAlignment(Qt.AlignCenter)  # type: ignore[attr-defined]
        dock_layout.addWidget(margins_label)

        margins_layout = QGridLayout()
        margins_layout.addWidget(QLabel("Left:"), 0, 0)
        margins_layout.addWidget(QLabel("Right:"), 0, 2)
        margins_layout.addWidget(QLabel("Top:"), 1, 0)
        margins_layout.addWidget(QLabel("Bottom:"), 1, 2)

        self._margin_left = QSpinBox()
        self._margin_left.setStatusTip("Stripe on the left to ignore when detection regions")
        self._margin_left.setRange(0, 9999)
        self._margin_left.setValue(0)
        self._margin_left.setAlignment(Qt.AlignRight)  # type: ignore[attr-defined]
        self._margin_left.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self._margin_right = QSpinBox()
        self._margin_right.setStatusTip("Stripe on the right to ignore when detection regions")
        self._margin_right.setRange(0, 9999)
        self._margin_right.setValue(0)
        self._margin_right.setAlignment(Qt.AlignRight)  # type: ignore[attr-defined]
        self._margin_right.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self._margin_top = QSpinBox()
        self._margin_top.setStatusTip("Stripe on the top to ignore when detection regions")
        self._margin_top.setRange(0, 9999)
        self._margin_top.setValue(0)
        self._margin_top.setAlignment(Qt.AlignRight)  # type: ignore[attr-defined]
        self._margin_top.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self._margin_bottom = QSpinBox()
        self._margin_bottom.setStatusTip("Stripe on the bottom to ignore when detection regions")
        self._margin_bottom.setRange(0, 9999)
        self._margin_bottom.setValue(0)
        self._margin_bottom.setAlignment(Qt.AlignRight)  # type: ignore[attr-defined]
        self._margin_bottom.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        margins_layout.addWidget(self._margin_left, 0, 1)
        margins_layout.addWidget(self._margin_right, 0, 3)
        margins_layout.addWidget(self._margin_top, 1, 1)
        margins_layout.addWidget(self._margin_bottom, 1, 3)

        margins = QWidget()
        margins.setLayout(margins_layout)
        dock_layout.addWidget(margins)

        self._no_image_text = QCheckBox("Ignore text on images?")
        self._no_image_text.setStatusTip("If checked, text drawn over images won't be detected as a region")
        self._no_image_text.setCheckState(Qt.Unchecked)  # type: ignore[attr-defined]

        no_image_text_layout = QHBoxLayout()
        no_image_text_layout.setAlignment(Qt.AlignCenter)  # type: ignore[attr-defined]
        no_image_text_layout.setContentsMargins(0, 0, 0, 0)
        no_image_text_layout.addWidget(self._no_image_text)

        no_image_text = QWidget()
        no_image_text.setLayout(no_image_text_layout)

        dock_layout.addWidget(no_image_text)

        recalc_layout = QGridLayout()

        recalc_regions_button = QPushButton("Recalculate page regions")
        recalc_regions_button.setStatusTip("Remove all regions on the current page and run autodetection again, "
                                           "with the current parameters")
        recalc_regions_button.clicked.connect(self._recalculate_regions)

        recalc_all_regions_button = QPushButton("Recalculate all regions")
        recalc_all_regions_button.setStatusTip("Remove all regions on all pages and run autodetection again, "
                                               "with the current parameters")
        recalc_all_regions_button.clicked.connect(self._recalculate_all_regions)

        clear_regions_button = QPushButton("Clear page regions")
        clear_regions_button.setStatusTip("Remove all regions on the current page")
        clear_regions_button.clicked.connect(self._clear_regions)

        clear_all_regions_button = QPushButton("Clear all regions")
        clear_all_regions_button.setStatusTip("Remove all regions on all pages")
        clear_all_regions_button.clicked.connect(self._clear_all_regions)

        recalc_layout.addWidget(recalc_regions_button, 0, 0)
        recalc_layout.addWidget(recalc_all_regions_button, 1, 0)
        recalc_layout.addWidget(clear_regions_button, 0, 1)
        recalc_layout.addWidget(clear_all_regions_button, 1, 1)

        recalc = QWidget()
        recalc.setLayout(recalc_layout)

        dock_layout.addWidget(recalc)

        regions_label = QLabel("Regions:")
        regions_label.setAlignment(Qt.AlignCenter)  # type: ignore[attr-defined]
        dock_layout.addWidget(regions_label)

        self._region_label = QLabel()
        self._region_label.setText("")
        self._region_label.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        self._region_label.setAlignment(Qt.AlignCenter)  # type: ignore[attr-defined]

        region_label_layout = QVBoxLayout()
        region_label_layout.setAlignment(Qt.AlignCenter)  # type: ignore[attr-defined]
        region_label_layout.addWidget(self._region_label)

        region_label_frame = QFrame()
        region_label_frame.setLayout(region_label_layout)
        region_label_frame.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        region_label_frame.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        region_label_frame.setLineWidth(2)
        region_label_frame.setMinimumWidth(80)

        up_region_button = QPushButton(style.standardIcon(QStyle.SP_ArrowUp),  # type: ignore[attr-defined]
                                       "", parent=self)
        up_region_button.setStatusTip("Reorder regions by moving the current region \"up\"")
        up_region_button.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        up_region_button.clicked.connect(self._up_region)
        self._up_region_button = up_region_button

        first_region_button = QPushButton(style.standardIcon(QStyle.SP_MediaSkipBackward),  # type: ignore[attr-defined]
                                          "", parent=self)
        first_region_button.setStatusTip("First region")
        first_region_button.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        first_region_button.clicked.connect(self._first_region)

        prev_region_button = QPushButton(style.standardIcon(QStyle.SP_MediaSeekBackward),  # type: ignore[attr-defined]
                                         "", parent=self)
        prev_region_button.setStatusTip("Previous region")
        prev_region_button.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        prev_region_button.clicked.connect(self._prev_region)

        next_region_button = QPushButton(style.standardIcon(QStyle.SP_MediaSeekForward),  # type: ignore[attr-defined]
                                         "", parent=self)
        next_region_button.setStatusTip("Next region")
        next_region_button.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        next_region_button.clicked.connect(self._next_region)

        last_region_button = QPushButton(style.standardIcon(QStyle.SP_MediaSkipForward),  # type: ignore[attr-defined]
                                         "", parent=self)
        last_region_button.setStatusTip("Last region")
        last_region_button.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        last_region_button.clicked.connect(self._last_region)

        down_region_button = QPushButton(style.standardIcon(QStyle.SP_ArrowDown),  # type: ignore[attr-defined]
                                         "", parent=self)
        down_region_button.setStatusTip("Reorder regions by moving the current region \"down\"")
        down_region_button.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        down_region_button.clicked.connect(self._down_region)
        self._down_region_button = down_region_button

        regions_layout = QHBoxLayout()
        regions_layout.setAlignment(Qt.AlignCenter)  # type: ignore[attr-defined]
        regions_layout.setSpacing(0)
        regions_layout.addWidget(up_region_button)
        regions_layout.addWidget(first_region_button)
        regions_layout.addWidget(prev_region_button)
        regions_layout.addWidget(region_label_frame)
        regions_layout.addWidget(next_region_button)
        regions_layout.addWidget(last_region_button)
        regions_layout.addWidget(down_region_button)

        regions = QWidget()
        regions.setLayout(regions_layout)
        dock_layout.addWidget(regions)

        self._regions_buttons = regions

        cur_region_layout = QGridLayout()
        cur_region_layout.addWidget(QLabel("Left:"), 0, 0)
        cur_region_layout.addWidget(QLabel("Top:"), 0, 2)
        cur_region_layout.addWidget(QLabel("Width:"), 1, 0)
        cur_region_layout.addWidget(QLabel("Height:"), 1, 2)

        self._cur_region_left = QSpinBox()
        self._cur_region_left.setStatusTip("Left edge of the region")
        self._cur_region_left.setRange(0, 0)
        self._cur_region_left.setValue(0)
        self._cur_region_left.setAlignment(Qt.AlignRight)  # type: ignore[attr-defined]
        self._cur_region_left.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self._cur_region_left.valueChanged.connect(self._modify_region)
        self._cur_region_top = QSpinBox()
        self._cur_region_top.setStatusTip("Top edge of the region")
        self._cur_region_top.setRange(0, 0)
        self._cur_region_top.setValue(0)
        self._cur_region_top.setAlignment(Qt.AlignRight)  # type: ignore[attr-defined]
        self._cur_region_top.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self._cur_region_top.valueChanged.connect(self._modify_region)
        self._cur_region_width = QSpinBox()
        self._cur_region_width.setStatusTip("Width of the region")
        self._cur_region_width.setRange(0, 0)
        self._cur_region_width.setValue(0)
        self._cur_region_width.setAlignment(Qt.AlignRight)  # type: ignore[attr-defined]
        self._cur_region_width.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self._cur_region_width.valueChanged.connect(self._modify_region)
        self._cur_region_height = QSpinBox()
        self._cur_region_height.setStatusTip("Height of the region")
        self._cur_region_height.setRange(0, 0)
        self._cur_region_height.setValue(0)
        self._cur_region_height.setAlignment(Qt.AlignRight)  # type: ignore[attr-defined]
        self._cur_region_height.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self._cur_region_height.valueChanged.connect(self._modify_region)

        cur_region_layout.addWidget(self._cur_region_left, 0, 1)
        cur_region_layout.addWidget(self._cur_region_top, 0, 3)
        cur_region_layout.addWidget(self._cur_region_width, 1, 1)
        cur_region_layout.addWidget(self._cur_region_height, 1, 3)

        cur_region = QWidget()
        cur_region.setLayout(cur_region_layout)

        dock_layout.addWidget(cur_region)

        delete_region_button = QPushButton("Delete region")
        delete_region_button.setStatusTip("Delete the currently selected region")
        delete_region_button.clicked.connect(self._delete_region)
        self._delete_region_button = delete_region_button

        add_region_button = QPushButton("Add region")
        add_region_button.setStatusTip("Add a new region")
        add_region_button.clicked.connect(self._add_region)

        redraw_region_button = QPushButton("Redraw region")
        redraw_region_button.setStatusTip("Modify the current region by drawing onto the page")
        redraw_region_button.clicked.connect(self._redraw_region)
        self._redraw_region_button = redraw_region_button

        add_delete_layout = QGridLayout()

        add_delete_layout.addWidget(add_region_button, 0, 0)
        add_delete_layout.addWidget(delete_region_button, 0, 1)
        add_delete_layout.addWidget(redraw_region_button, 1, 0)

        add_delete = QWidget()
        add_delete.setLayout(add_delete_layout)

        dock_layout.addWidget(add_delete)

        self.addDockWidget(Qt.RightDockWidgetArea, dock, Qt.Vertical)  # type: ignore[attr-defined]

        self._dock = dock

        self._update_page_labels()
        self._update_region_labels()
        self._update_enabled()

    def _create_viewport(self) -> None:
        self._page_image = QPixmap()
        self._page_view = QLabel(self)
        self._page_view.setFocusPolicy(Qt.StrongFocus)  # type: ignore[attr-defined]

        self._page_view.setBackgroundRole(QPalette.Base)
        self._page_view.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self._page_view.setScaledContents(False)
        self._page_view.setAlignment(Qt.AlignCenter)  # type: ignore[attr-defined]

        self._page_view.installEventFilter(self)

        self.setCentralWidget(self._page_view)

    def _set_window_title(self) -> None:
        info: dict[str, Any] = Util.get_project_info()
        title: str = f"{info['name']} {info['version']}"

        if self._pdf:
            title += f" -- {self._pdf.name}"
            if self._regions_filename:
                title += f" -- {Path(self._regions_filename).name}"
                if self._regions_modified:
                    title += "*"

        self.setWindowTitle(title)

    def _show_error(self, error: str, where: Optional[str] = None) -> None:
        message = error
        if where:
            message = where + ": " + message

        print(message, file=sys.stderr)
        if self.isHidden():
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

        if self._viewport_image.isNull():
            self._page_view.setPixmap(QPixmap())
        else:
            self._viewport_scaled_image = self._viewport_image.scaled(width, height,
                                                                      aspectRatioMode=aspect_ratio_mode,
                                                                      transformMode=transform_mode)
            if not self._new_region.isNull():
                paint = QPainter(self._viewport_scaled_image)
                paint.setPen(Qt.blue)  # type: ignore[attr-defined]

                offset_x = int((self._page_view.width() - self._viewport_scaled_image.width()) / 2)
                offset_y = int((self._page_view.height() - self._viewport_scaled_image.height()) / 2)

                paint.drawRect(self._new_region.left() - offset_x, self._new_region.top() - offset_y,
                               self._new_region.width(), self._new_region.height())

            self._page_view.setPixmap(self._viewport_scaled_image)

    def _get_regions(self):
        if not self._pdf:
            return []

        top_margin = self._margin_top.value()
        bottom_margin = self._margin_bottom.value()
        left_margin = self._margin_left.value()
        right_margin = self._margin_right.value()

        no_image_text = self._no_image_text.checkState() == Qt.Checked  # type: ignore[attr-defined]

        regions = self._pdf.get_regions(self._current_page,
                                        top_margin=top_margin, bottom_margin=bottom_margin,
                                        left_margin=left_margin, right_margin=right_margin,
                                        no_image_text=no_image_text)
        return regions or []

    def _draw_region(self, paint, region, index) -> None:
        if not region:
            return

        left = region.x0
        top = region.y0
        width = region.x1 - region.x0 + 1
        height = region.y1 - region.y0 + 1

        paint.drawRect(left, top, width, height)
        paint.drawText(QRectF(left, top, 1000, 1000), f" {index + 1}")

    def _draw_regions(self, regions) -> None:
        if not self._pdf:
            return

        paint = QPainter(self._viewport_image)
        paint.setPen(Qt.red)  # type: ignore[attr-defined]

        font = QFont()
        font.setFamily(font.defaultFamily())
        font.setPointSize(12)
        paint.setFont(font)

        for i, region in enumerate(regions):
            if i == self._current_region:
                continue
            self._draw_region(paint, region, i)

        if self._current_region >= 0 and self._current_region < len(regions):
            paint.setPen(Qt.green)  # type: ignore[attr-defined]
            self._draw_region(paint, regions[self._current_region], self._current_region)

    def _update_page(self) -> None:
        if self._pdf:
            page_image = self._pdf.render_page(self._current_page) or QImage()
            self._page_image = QPixmap.fromImage(page_image)

            self._viewport_image = self._page_image.copy()

            self._draw_regions(self._get_regions())

            self._rescale_page()
        else:
            self._page_image = QPixmap()
            self._viewport_image = QPixmap()
            self._viewport_scaled_image = QPixmap()

            self._page_view.setPixmap(QPixmap())

    def _clear_region_values(self):
        self._cur_region_left.blockSignals(True)
        self._cur_region_left.setRange(0, 0)
        self._cur_region_left.setValue(0)
        self._cur_region_left.blockSignals(False)
        self._cur_region_top.blockSignals(True)
        self._cur_region_top.setRange(0, 0)
        self._cur_region_top.setValue(0)
        self._cur_region_top.blockSignals(False)
        self._cur_region_width.blockSignals(True)
        self._cur_region_width.setRange(0, 0)
        self._cur_region_width.setValue(0)
        self._cur_region_width.blockSignals(False)
        self._cur_region_height.blockSignals(True)
        self._cur_region_height.setRange(0, 0)
        self._cur_region_height.setValue(0)
        self._cur_region_height.blockSignals(False)

    def _update_page_labels(self) -> None:
        if not self._pdf:
            self._page_label.setText("? / ?")
            return

        self._page_label.setText(f"{self._current_page + 1} / {self._pdf.page_count}")

        self._page_edit.blockSignals(True)
        self._page_edit.setRange(1, self._pdf.page_count)
        self._page_edit.setValue(self._current_page + 1)
        self._page_edit.blockSignals(False)

    def _update_region_labels(self, ignore_region_values: bool = False) -> None:
        if not self._pdf:
            self._region_label.setText("? / ?")
            self._clear_region_values()
            return

        regions = self._get_regions()

        self._region_label.setText(f"{self._current_region + 1} / {len(regions)}")

        if self._current_region >= 0 and self._current_region < len(regions):
            if not ignore_region_values:
                region = regions[self._current_region]
                self._cur_region_left.blockSignals(True)
                self._cur_region_left.setRange(0, self._page_image.width() - 1)
                self._cur_region_left.setValue(region.x0)
                self._cur_region_left.blockSignals(False)
                self._cur_region_top.blockSignals(True)
                self._cur_region_top.setRange(0, self._page_image.height() - 1)
                self._cur_region_top.setValue(region.y0)
                self._cur_region_top.blockSignals(False)
                self._cur_region_width.blockSignals(True)
                self._cur_region_width.setRange(0, self._page_image.width())
                self._cur_region_width.setValue(region.x1 - region.x0 + 1)
                self._cur_region_width.blockSignals(False)
                self._cur_region_height.blockSignals(True)
                self._cur_region_height.setRange(0, self._page_image.height() - 1)
                self._cur_region_height.setValue(region.y1 - region.y0 + 1)
                self._cur_region_height.blockSignals(False)
        else:
            self._clear_region_values()

    def _update_enabled(self, ignore_region_values: bool = False):
        if not self._pdf:
            self._action_load_regions.setEnabled(False)
            self._action_save_regions.setEnabled(False)
            self._action_save_regions_as.setEnabled(False)
            self._action_convert_page.setEnabled(False)
            self._action_save_page.setEnabled(False)
            self._action_save_all_pages.setEnabled(False)
            self._cur_region_left.setEnabled(False)
            self._cur_region_top.setEnabled(False)
            self._cur_region_width.setEnabled(False)
            self._cur_region_height.setEnabled(False)
            self._dock.setEnabled(False)
            return

        self._dock.setEnabled(True)

        have_region = self._current_region >= 0 and self._current_region < len(self._get_regions())
        if not ignore_region_values:
            self._cur_region_left.setEnabled(have_region)
            self._cur_region_top.setEnabled(have_region)
            self._cur_region_width.setEnabled(have_region)
            self._cur_region_height.setEnabled(have_region)

        self._up_region_button.setEnabled(have_region)
        self._down_region_button.setEnabled(have_region)
        self._delete_region_button.setEnabled(have_region)
        self._redraw_region_button.setEnabled(have_region)

        have_regions = len(self._get_regions()) > 0
        self._regions_buttons.setEnabled(have_regions)
        self._action_convert_page.setEnabled(have_regions)
        self._action_save_page.setEnabled(have_regions)
        self._action_save_all_pages.setEnabled(True)

        self._action_load_regions.setEnabled(True)
        self._action_save_regions_as.setEnabled(True)

        self._action_save_regions.setEnabled(self._regions_filename is not None and self._regions_modified)

    def _update_all(self, ignore_region_values: bool = False) -> None:
        if self._op_mode == OperationMode.NORMAL:
            QApplication.setOverrideCursor(Qt.WaitCursor)  # type: ignore[attr-defined]

        self._set_window_title()
        self._update_page()
        self._update_page_labels()
        self._update_region_labels(ignore_region_values)
        self._update_enabled(ignore_region_values)

        if self._op_mode == OperationMode.NORMAL:
            QApplication.restoreOverrideCursor()

    def _close_self(self) -> None:
        self.close()

    def _show_about(self) -> None:
        info: dict[str, Any] = Util.get_project_info()

        dlg = QMessageBox(self)
        dlg.setWindowTitle(f"About {info['name']}")
        dlg.setTextFormat(Qt.RichText)  # type: ignore[attr-defined]
        dlg.setText(Util.get_version_string(html=True))
        dlg.exec()

    def _open_pdf(self, filename) -> bool:
        self._close_pdf()

        try:
            self._pdf = PDFFile(filename)
            if self._pdf.page_count == 0:
                raise ValueError("PDF has no pages")

        except (FileNotFoundError, IOError, ValueError) as err:
            self._show_error(str(err), "Can't open PDF")
            return False

        self._regions_filename = None
        self._regions_modified = False

        self._op_mode = OperationMode.NORMAL
        self._new_region = QRect()

        self._current_page = 0
        self._current_region = -1
        self._update_all()

        return True

    def _close_pdf(self) -> None:
        self._pdf = None

        self._regions_filename = None
        self._regions_modified = False

        self._page_image = QPixmap()
        self._viewport_image = QPixmap()

        self._op_mode = OperationMode.NORMAL
        self._new_region = QRect()

        self._current_page = 0
        self._current_region = -1
        self._update_all()

    def _open_pdf_file(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(self, "Open PDF", filter="PDF files (*.pdf)")
        if not filename or filename == '':
            return

        self._open_pdf(filename)

    def _load_regions_internal(self, filename) -> bool:
        if not self._pdf or self._op_mode != OperationMode.NORMAL:
            return False

        try:
            with open(filename, "r", encoding="utf-8") as file:
                data = file.read()
                deserialized = self._pdf.deserialize_regions(data)
                if "margins" in deserialized:
                    self._margin_left.setValue(deserialized["margins"]["left"])
                    self._margin_top.setValue(deserialized["margins"]["top"])
                    self._margin_right.setValue(deserialized["margins"]["right"])
                    self._margin_bottom.setValue(deserialized["margins"]["bottom"])
                    self._no_image_text.setCheckState(
                        Qt.Checked if deserialized["margins"]["ignore_images"] else  # type: ignore[attr-defined]
                        Qt.Unchecked)  # type: ignore[attr-defined]
        except Exception as err:
            self._show_error(str(err), "Can't load regions")
            return False

        return True

    def _load_regions(self) -> None:
        if not self._pdf or self._op_mode != OperationMode.NORMAL:
            return

        filename, _ = QFileDialog.getOpenFileName(self, "Open regions", filter="Region files (*.json)")
        if not filename or filename == '':
            return

        if not self._load_regions_internal(filename):
            return

        self._regions_modified = False
        self._regions_filename = filename

        self._current_region = -1
        self._update_all()

    def _save_regions_internal(self, filename) -> bool:
        if not self._pdf:
            return False

        extra_data = {
            'margins': {
                'left': self._margin_left.value(),
                'top': self._margin_top.value(),
                'right': self._margin_right.value(),
                'bottom': self._margin_bottom.value(),
                'ignore_images': self._no_image_text.checkState() == Qt.Checked  # type: ignore[attr-defined]
            }
        }

        regions = self._pdf.serialize_regions(extra_data)

        try:
            with open(filename, "w", encoding="utf-8") as file:
                json.dump(regions, file, indent=4)
        except Exception as err:
            self._show_error(str(err), "Can't save regions")
            return False

        return True

    def _save_regions_as(self):
        if not self._pdf or self._op_mode != OperationMode.NORMAL:
            return

        dlg = QFileDialog(self, "Save regions", filter="Region files (*.json)")
        dlg.setDefaultSuffix(".json")
        dlg.setAcceptMode(QFileDialog.AcceptSave)
        if not dlg.exec_():
            return

        filename = dlg.selectedFiles()[0]
        if not filename or filename == '':
            return

        if not self._save_regions_internal(filename):
            return

        self._regions_modified = False
        self._regions_filename = filename
        self._set_window_title()
        self._update_enabled()

    def _save_regions(self):
        if not self._pdf or self._op_mode != OperationMode.NORMAL:
            return

        if not self._regions_filename or not self._save_regions_internal(self._regions_filename):
            return

        self._regions_modified = False
        self._set_window_title()
        self._update_enabled()

    def _go_to_page(self, page: int) -> None:
        if not self._pdf or self._op_mode != OperationMode.NORMAL:
            return

        if page < 0 or page >= self._pdf.page_count:
            return

        self._current_page = page
        self._current_region = -1
        self._update_all()

    def _first_page(self) -> None:
        if not self._pdf or self._op_mode != OperationMode.NORMAL:
            return

        self._current_page = 0
        self._current_region = -1
        self._update_all()

    def _previous_page(self) -> None:
        if not self._pdf or self._op_mode != OperationMode.NORMAL:
            return

        if self._current_page == 0:
            return

        self._current_page -= 1
        self._current_region = -1
        self._update_all()

    def _next_page(self) -> None:
        if not self._pdf or self._op_mode != OperationMode.NORMAL:
            return

        if self._current_page >= (self._pdf.page_count - 1):
            return

        self._current_page += 1
        self._current_region = -1
        self._update_all()

    def _last_page(self) -> None:
        if not self._pdf or self._op_mode != OperationMode.NORMAL:
            return

        self._current_page = self._pdf.page_count - 1
        self._current_region = -1
        self._update_all()

    def _first_region(self) -> None:
        if not self._pdf or self._op_mode != OperationMode.NORMAL:
            return

        old_region = self._current_region
        self._current_region = 0
        if self._current_region >= len(self._get_regions()):
            self._current_region = len(self._get_regions()) - 1

        if old_region != self._current_region:
            self._update_all()

    def _next_region(self) -> None:
        if not self._pdf or self._op_mode != OperationMode.NORMAL:
            return

        old_region = self._current_region
        self._current_region += 1
        if self._current_region >= len(self._get_regions()):
            self._current_region = len(self._get_regions()) - 1

        if old_region != self._current_region:
            self._update_all()

    def _prev_region(self) -> None:
        if not self._pdf or self._op_mode != OperationMode.NORMAL or self._current_region == 0:
            return

        if self._current_region < 0:
            self._last_region()
            return

        self._current_region -= 1
        self._update_all()

    def _last_region(self) -> None:
        if not self._pdf or self._op_mode != OperationMode.NORMAL:
            return

        old_region = self._current_region
        self._current_region = len(self._get_regions()) - 1

        if old_region != self._current_region:
            self._update_all()

    def _up_region(self) -> None:
        if not self._pdf or self._op_mode != OperationMode.NORMAL:
            return

        old_region = self._current_region
        self._current_region = self._pdf.reorder_region(self._current_page, self._current_region, -1)

        if old_region != self._current_region:
            self._regions_modified = True
            self._update_all()

    def _down_region(self) -> None:
        if not self._pdf or self._op_mode != OperationMode.NORMAL:
            return

        old_region = self._current_region
        self._current_region = self._pdf.reorder_region(self._current_page, self._current_region, 1)

        if old_region != self._current_region:
            self._regions_modified = True
            self._update_all()

    def _recalculate_regions(self) -> None:
        if not self._pdf or self._op_mode != OperationMode.NORMAL:
            return

        self._regions_modified = True

        self._pdf.clear_regions(self._current_page)
        self._current_region = -1
        self._update_all()

    def _recalculate_all_regions(self) -> None:
        if not self._pdf or self._op_mode != OperationMode.NORMAL:
            return

        self._regions_modified = True

        self._pdf.clear_all_regions()
        self._current_region = -1
        self._update_all()

    def _clear_regions(self) -> None:
        if not self._pdf or self._op_mode != OperationMode.NORMAL:
            return

        self._regions_modified = True

        self._pdf.mark_page_empty(self._current_page)
        self._current_region = -1
        self._update_all()

    def _clear_all_regions(self) -> None:
        if not self._pdf or self._op_mode != OperationMode.NORMAL:
            return

        self._regions_modified = True

        self._pdf.mark_all_pages_empty()
        self._current_region = -1
        self._update_all()

    def _delete_region(self) -> None:
        if not self._pdf or self._op_mode != OperationMode.NORMAL:
            return

        self._regions_modified = True

        self._pdf.remove_region(self._current_page, self._current_region)
        self._current_region = -1
        self._update_all()

    def _add_region(self) -> None:
        if not self._pdf or self._op_mode != OperationMode.NORMAL:
            return

        QApplication.setOverrideCursor(Qt.CrossCursor)  # type: ignore[attr-defined]
        self._op_mode = OperationMode.ADD_REGION
        self._new_region = QRect()
        self._current_region = -1

    def _redraw_region(self) -> None:
        if not self._pdf or self._op_mode != OperationMode.NORMAL or self._current_region < 0:
            return

        QApplication.setOverrideCursor(Qt.CrossCursor)  # type: ignore[attr-defined]
        self._op_mode = OperationMode.REDRAW_REGION
        self._new_region = QRect()

    def _modify_region(self, _: int) -> None:
        if not self._pdf or self._op_mode != OperationMode.NORMAL or self._current_region < 0:
            return

        self._regions_modified = True

        left = self._cur_region_left.value()
        top = self._cur_region_top.value()
        right = left + self._cur_region_width.value() - 1
        bottom = top + self._cur_region_height.value() - 1

        self._pdf.modify_region(self._current_page, self._current_region, left, top, right, bottom)
        self._update_all(ignore_region_values=True)

    def _modify_page_edit(self, _: int) -> None:
        if not self._pdf or self._op_mode != OperationMode.NORMAL:
            return

        self._go_to_page(self._page_edit.value() - 1)

    def _get_page_rect(self) -> Optional[QRect]:
        if not self._pdf:
            return None

        left = int((self._page_view.width() - self._viewport_scaled_image.width()) / 2)
        top = int((self._page_view.height() - self._viewport_scaled_image.height()) / 2)
        return QRect(left, top, self._viewport_scaled_image.width(), self._viewport_scaled_image.height())

    def _get_page_coords(self, view_x: int, view_y: int):
        page_rect = self._get_page_rect()
        if not page_rect:
            return -1, -1

        scale_x = self._page_image.width() / self._viewport_scaled_image.width()
        scale_y = self._page_image.height() / self._viewport_scaled_image.height()

        page_x = (view_x - page_rect.x()) * scale_x
        page_y = (view_y - page_rect.y()) * scale_y

        if page_x < 0 or page_y < 0 or page_x >= self._page_image.width() or page_y >= self._page_image.height():
            return -1, -1

        return page_x, page_y

    def _fix_new_region(self) -> tuple[int, int, int, int]:
        offset_x = int((self._page_view.width() - self._viewport_scaled_image.width()) / 2)
        offset_y = int((self._page_view.height() - self._viewport_scaled_image.height()) / 2)
        scale_x = self._page_image.width() / self._viewport_scaled_image.width()
        scale_y = self._page_image.height() / self._viewport_scaled_image.height()

        left = int((self._new_region.left() - offset_x) * scale_x)
        top = int((self._new_region.top() - offset_y) * scale_y)
        right = int((self._new_region.right() - offset_x) * scale_x)
        bottom = int((self._new_region.bottom() - offset_y) * scale_y)

        if left > right:
            left, right = right, left
        if top > bottom:
            top, bottom = bottom, top

        left = max(0, min(left, self._page_image.width() - 1))
        right = max(0, min(right, self._page_image.width() - 1))
        top = max(0, min(top, self._page_image.height() - 1))
        bottom = max(0, min(bottom, self._page_image.height() - 1))

        return left, right, top, bottom

    def _add_region_end(self, add_created_region: bool):
        if not self._pdf:
            return

        if add_created_region:
            left, right, top, bottom = self._fix_new_region()
            if left < right and top < bottom:
                self._pdf.add_region(self._current_page, left, top, right, bottom)
                self._regions_modified = True

        self._op_mode = OperationMode.NORMAL
        self._new_region = QRect()
        self._current_region = -1
        self._update_all()
        QApplication.restoreOverrideCursor()

    def _redraw_region_end(self, use_created_region: bool):
        if not self._pdf:
            return

        if use_created_region:
            left, right, top, bottom = self._fix_new_region()
            if left < right and top < bottom:
                self._pdf.modify_region(self._current_page, self._current_region, left, top, right, bottom)
                self._regions_modified = True

        self._op_mode = OperationMode.NORMAL
        self._new_region = QRect()
        self._update_all()
        QApplication.restoreOverrideCursor()

    def _convert_page_to_text_print(self) -> None:
        if not self._pdf:
            return

        text = self._pdf.convert_page_to_text(self._current_page, concat_paragraphs=True)
        print(f"---\n{text}")

    def _convert_page_to_text_file(self) -> None:
        if not self._pdf:
            return

        dlg = QFileDialog(self, "Save page to text", filter="Text files (*.txt)")
        dlg.setDefaultSuffix(".txt")
        dlg.setAcceptMode(QFileDialog.AcceptSave)
        if not dlg.exec_():
            return

        filename = dlg.selectedFiles()[0]
        if not filename or filename == '':
            return

        text = self._pdf.convert_page_to_text(self._current_page, concat_paragraphs=True)

        try:
            with open(filename, "w", encoding="utf-8") as file:
                file.write(text)
        except Exception as err:
            self._show_error(str(err), "Can't save text")

    def _convert_all_pages_to_text_file_internal(self, file) -> None:
        if not self._pdf:
            return

        progress = QProgressDialog(f"Converting {self._pdf.page_count} page(s)...", "Abort Conversion",
                                   0, self._pdf.page_count, self)
        progress.setWindowModality(Qt.WindowModal)  # type: ignore[attr-defined]
        progress.setWindowTitle("Converting")
        progress.setMinimumDuration(0)

        for page in range(self._pdf.page_count):
            progress.setValue(page)
            if progress.wasCanceled():
                break

            text = self._pdf.convert_page_to_text(page, concat_paragraphs=True)
            file.write(text)

        # When pressing cancel, the dialog already vanished by itself, at least on Linux. This is contrary to
        # the documentation and might by a Qt/PyQt bug. It also might not happen that way on other platforms.
        # So we're hedging our bets a bit here by checking if the dialog is still shown before setting it to
        # its final value to make it go away.

        if not progress.isHidden():
            progress.setValue(self._pdf.page_count)

    def _convert_all_pages_to_text_file(self) -> None:
        if not self._pdf:
            return

        dlg = QFileDialog(self, "Save all pages to text", filter="Text files (*.txt)")
        dlg.setDefaultSuffix(".txt")
        dlg.setAcceptMode(QFileDialog.AcceptSave)
        if not dlg.exec_():
            return

        filename = dlg.selectedFiles()[0]
        if not filename or filename == '':
            return

        try:
            with open(filename, "w", encoding="utf-8") as file:
                self._convert_all_pages_to_text_file_internal(file)
        except Exception as err:
            self._show_error(str(err), "Can't save text")

    @staticmethod
    def _check_key_event(event: QKeyEvent, key, modifiers=Qt.NoModifier) -> bool:  # type: ignore[attr-defined]
        return event.modifiers() == modifiers and event.key() == key

    def _handle_viewport_key(self, event: QKeyEvent):
        if not self._pdf or self._op_mode != OperationMode.NORMAL:
            return

        if MainWindow._check_key_event(event, Qt.Key_K):  # type: ignore[attr-defined]
            self._next_page()
        elif MainWindow._check_key_event(event, Qt.Key_L):  # type: ignore[attr-defined]
            self._last_page()
        elif MainWindow._check_key_event(event, Qt.Key_J):  # type: ignore[attr-defined]
            self._previous_page()
        elif MainWindow._check_key_event(event, Qt.Key_H):  # type: ignore[attr-defined]
            self._first_page()
        elif MainWindow._check_key_event(event, Qt.Key_H):  # type: ignore[attr-defined]
            self._first_page()
        elif MainWindow._check_key_event(event, Qt.Key_K, Qt.ShiftModifier):  # type: ignore[attr-defined]
            self._next_region()
        elif MainWindow._check_key_event(event, Qt.Key_L, Qt.ShiftModifier):  # type: ignore[attr-defined]
            self._last_region()
        elif MainWindow._check_key_event(event, Qt.Key_J, Qt.ShiftModifier):  # type: ignore[attr-defined]
            self._prev_region()
        elif MainWindow._check_key_event(event, Qt.Key_H, Qt.ShiftModifier):  # type: ignore[attr-defined]
            self._first_region()
        elif MainWindow._check_key_event(event, Qt.Key_H, Qt.ShiftModifier):  # type: ignore[attr-defined]
            self._first_region()
        elif MainWindow._check_key_event(event, Qt.Key_Left):  # type: ignore[attr-defined]
            self._cur_region_left.setValue(self._cur_region_left.value() - 1)
        elif MainWindow._check_key_event(event, Qt.Key_Right):  # type: ignore[attr-defined]
            self._cur_region_left.setValue(self._cur_region_left.value() + 1)
        elif MainWindow._check_key_event(event, Qt.Key_Up):  # type: ignore[attr-defined]
            self._cur_region_top.setValue(self._cur_region_top.value() - 1)
        elif MainWindow._check_key_event(event, Qt.Key_Down):  # type: ignore[attr-defined]
            self._cur_region_top.setValue(self._cur_region_top.value() + 1)
        elif MainWindow._check_key_event(event, Qt.Key_Left, Qt.ShiftModifier):  # type: ignore[attr-defined]
            self._cur_region_width.setValue(self._cur_region_width.value() - 1)
        elif MainWindow._check_key_event(event, Qt.Key_Right, Qt.ShiftModifier):  # type: ignore[attr-defined]
            self._cur_region_width.setValue(self._cur_region_width.value() + 1)
        elif MainWindow._check_key_event(event, Qt.Key_Up, Qt.ShiftModifier):  # type: ignore[attr-defined]
            self._cur_region_height.setValue(self._cur_region_height.value() - 1)
        elif MainWindow._check_key_event(event, Qt.Key_Down, Qt.ShiftModifier):  # type: ignore[attr-defined]
            self._cur_region_height.setValue(self._cur_region_height.value() + 1)
        elif MainWindow._check_key_event(event, Qt.Key_PageUp):  # type: ignore[attr-defined]
            self._up_region()
        elif MainWindow._check_key_event(event, Qt.Key_PageDown):  # type: ignore[attr-defined]
            self._down_region()
        elif MainWindow._check_key_event(event, Qt.Key_Insert):  # type: ignore[attr-defined]
            self._add_region()
        elif MainWindow._check_key_event(event, Qt.Key_Delete):  # type: ignore[attr-defined]
            self._delete_region()
        elif MainWindow._check_key_event(event, Qt.Key_R):  # type: ignore[attr-defined]
            self._redraw_region()

    def _handle_viewport_click(self, event: QMouseEvent):
        if not self._pdf:
            return

        if (self._op_mode == OperationMode.NORMAL and
                event.type() == QEvent.MouseButtonRelease):  # type: ignore[attr-defined]
            x, y = self._get_page_coords(event.x(), event.y())

            old_region = self._current_region
            self._current_region = self._pdf.find_region(self._current_page, x, y)

            if old_region != self._current_region:
                self._update_all()
            return

        if (self._op_mode == OperationMode.ADD_REGION and
                event.type() == QEvent.MouseButtonPress):  # type: ignore[attr-defined]
            if event.button() == Qt.RightButton:  # type: ignore[attr-defined]
                self._add_region_end(False)
                return

            if event.button() == Qt.LeftButton:  # type: ignore[attr-defined]
                if self._new_region.isNull():
                    self._new_region = QRect(event.x(), event.y(), 1, 1)
                self._current_region = -1
                self._update_all()

            return

        if (self._op_mode == OperationMode.REDRAW_REGION and
                event.type() == QEvent.MouseButtonPress):  # type: ignore[attr-defined]
            if event.button() == Qt.RightButton:  # type: ignore[attr-defined]
                self._redraw_region_end(False)
                return

            if event.button() == Qt.LeftButton:  # type: ignore[attr-defined]
                if self._new_region.isNull():
                    self._new_region = QRect(event.x(), event.y(), 1, 1)
                self._update_all()

            return

        if (self._op_mode == OperationMode.ADD_REGION and
                event.type() == QEvent.MouseButtonRelease):  # type: ignore[attr-defined]
            self._add_region_end(True)
            return

        if (self._op_mode == OperationMode.REDRAW_REGION and
                event.type() == QEvent.MouseButtonRelease):  # type: ignore[attr-defined]
            self._redraw_region_end(True)
            return

    def _handle_viewport_move(self, event: QMouseEvent):
        if not self._pdf:
            return

        if self._op_mode == OperationMode.ADD_REGION and not self._new_region.isNull():
            self._new_region.setBottomRight(QPoint(event.x(), event.y()))
            self._update_all()
        if self._op_mode == OperationMode.REDRAW_REGION and not self._new_region.isNull():
            self._new_region.setBottomRight(QPoint(event.x(), event.y()))
            self._update_all()

    def eventFilter(self, widget, event):  # pylint: disable=invalid-name
        """! Special event handling for the main window.
        """

        if event.type() == QEvent.Resize and widget is self._page_view:
            self._rescale_page()
            return True
        if event.type() == QEvent.KeyRelease and widget is self._page_view:
            self._handle_viewport_key(event)
            return True
        if event.type() == QEvent.MouseButtonRelease and widget is self._page_view:
            self._handle_viewport_click(event)
            return True
        if event.type() == QEvent.MouseButtonPress and widget is self._page_view:
            self._handle_viewport_click(event)
            return True
        if event.type() == QEvent.MouseMove and widget is self._page_view:
            self._handle_viewport_move(event)
            return False
        return super().eventFilter(widget, event)

    def showEvent(self, event):  # pylint: disable=invalid-name
        """! Special initializing for the main window.
        """

        super().showEvent(event)
        if self._regions_filename:
            if self._load_regions_internal(self._regions_filename):
                self._update_all()
            else:
                self._regions_filename = None
