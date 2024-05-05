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
from typing import Any

from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import QAction, QMainWindow, QMessageBox, QStatusBar, QStyle

from util import Util


class MainWindow(QMainWindow):
    """! PDF Textorizer main window.
    """

    def __init__(self, args: argparse.Namespace) -> None:
        super().__init__()

        self._args = args

        info: dict[str, Any] = Util.get_project_info()
        nameversion: str = f"{info['name']} {info['version']}"

        self.setWindowTitle(nameversion)

        menu = self.menuBar()
        assert menu is not None

        file_menu = menu.addMenu("&File")
        assert file_menu is not None

        exit_action = QAction("&Quit", self)
        exit_action.setShortcuts(QKeySequence.Quit)
        exit_action.setStatusTip(f"Quit {info['name']}")
        exit_action.triggered.connect(self._close_self)
        file_menu.addAction(exit_action)

        about_menu = menu.addMenu("&About")
        assert about_menu is not None

        style = self.style()
        assert style is not None

        about_action = QAction(style.standardIcon(QStyle.SP_FileDialogInfoView),  # type: ignore[attr-defined]
                               f"&About {info['name']}", self)
        about_action.setShortcuts(QKeySequence.WhatsThis)
        about_action.setStatusTip(f"Show information about {info['name']}")
        about_action.triggered.connect(self._show_about)
        about_menu.addAction(about_action)

        self.setStatusBar(QStatusBar(self))

        self.resize(500, 500)

    def _close_self(self) -> None:
        self.close()

    def _show_about(self) -> None:
        info: dict[str, Any] = Util.get_project_info()

        dlg = QMessageBox(self)
        dlg.setWindowTitle(f"About {info['name']}")
        dlg.setText(Util.get_version_string())
        dlg.exec()
