"""! PDF File.
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

from typing import Optional

import fitz
from PyQt5.QtGui import QImage

from multi_column import column_boxes


class PDFFile:
    """! PDF File.
    """

    def __init__(self, filename: str) -> None:
        try:
            self._doc = fitz.open(filename)
        except fitz.FileNotFoundError as err:
            raise FileNotFoundError(err) from err
        except fitz.EmptyFileError as err:
            raise ValueError(err) from err
        except fitz.FileDataError as err:
            raise ValueError(err) from err

        self._regions: dict[int, list[fitz.IRect]] = {}

    @property
    def page_count(self):
        """! The number of pages in the PDF file.
        """

        return self._doc.page_count

    def clear_all_regions(self) -> None:
        """! Remove cached regions of all pages.
        """

        self._regions = {}

    def clear_regions(self, page: int) -> None:
        """! Remove cached regions of a page.

        @param page  The page to forget.

        """

        self._regions.pop(page)

    def mark_page_empty(self, page: int) -> None:
        """! Mark a single page as having no regions at all.

        @param page  The page to mark as empty.

        """
        if page >= self.page_count:
            return

        self._regions[page] = []

    def mark_all_pages_empty(self) -> None:
        """! Mark all pages as having no regions at all.
        """
        for i in range(self.page_count):
            self._regions[i] = []

    def render_page(self, page: int) -> Optional[QImage]:
        """! Render a page into an image.

        @param page  The page to render.

        @return An image of the rendered page or None if the page is out of bounds.
        """

        if page >= self.page_count:
            return None

        pix = self._doc.load_page(page).get_pixmap(alpha=False)
        return QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format_RGB888)

    def get_regions(self, page: int, top_margin: int = 0, bottom_margin: int = 0,  # pylint: disable=too-many-arguments
                    left_margin: int = 0, right_margin: int = 0,
                    no_image_text: bool = False) -> Optional[list[fitz.IRect]]:
        """! Returns the regions of a page, caching them afterwards.

        @param page           The page to look at.
        @param top_margin     Ignore this stripe at the top.
        @param bottom_margin  Ignore this stripe at the bottom.
        @param left_margin    Ignore this stripe on the left.
        @param right_margin   Ignore this stripe on the right.
        @param no_image_text  Ignore text drawn over images.

        @return A list of rectangles of found regions, or None if the page is out of bounds.
        """

        if page >= self.page_count:
            return None

        if page not in self._regions:
            self._regions[page] = column_boxes(self._doc.load_page(page),
                                               footer_margin=bottom_margin, header_margin=top_margin,
                                               left_margin=left_margin, right_margin=right_margin,
                                               no_image_text=no_image_text)

        return self._regions[page]
