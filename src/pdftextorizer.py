"""! Main entry point for PDF Textorizer.
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

from PyQt5.QtWidgets import QApplication

from mainwindow import MainWindow
from util import Util


class PDFTextorizer:  # pylint: disable=too-few-public-methods
    """! Main PDF Textorizer application.
    """

    @staticmethod
    def _print_version() -> None:
        print(Util.get_version_string())

    @staticmethod
    def _parse_args() -> argparse.Namespace:
        """! Parse command line arguments.

        @return An object containing the parsed command line arguments.
        """
        info: dict[str, Any] = Util.get_project_info()
        nameversion: str = f"{info['name']} {info['version']}"
        description: str = f"{nameversion} -- {info['summary']}"

        parser: argparse.ArgumentParser = argparse.ArgumentParser(description=description, add_help=False)

        # Note: we're setting required to False even on required arguments and do the checks
        # ourselves below. We're doing that because we want more dynamic --version behaviour

        parser.add_argument('-h', '--help', action="help", help='show this help message and exit')
        parser.add_argument("-v", "--version", required=False, action="store_true",
                            help="print the version and exit")

        parser.add_argument('pdf_file', nargs='?', help="PDF file to open")
        parser.add_argument('regions_file', nargs='?', help="Regions file to load")

        args: argparse.Namespace = parser.parse_args()

        if args.version:
            PDFTextorizer._print_version()
            parser.exit()

        return args

    def run(self) -> None:
        """! Run the main PDF Textorizer application.
        """
        args: argparse.Namespace = PDFTextorizer._parse_args()

        app = QApplication([])

        window = MainWindow(args)
        window.show()

        app.exec()


def main() -> None:
    """! PDF Textorizer main function, running the main app.
    """
    pdftextorizer: PDFTextorizer = PDFTextorizer()
    pdftextorizer.run()


if __name__ == '__main__':
    main()
