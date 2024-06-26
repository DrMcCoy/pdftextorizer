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

from hashlib import sha1
from pathlib import Path
from typing import Any, Optional

import fitz
from marshmallow import ValidationError
from PyQt5.QtGui import QImage

from multi_column import column_boxes
from regions_schema import RegionsSchema


class PDFFile:
    """! PDF File.
    """

    def __init__(self, filename: str) -> None:
        self._name: str = Path(filename).name

        with open(filename, "rb") as file:
            data = file.read()

        try:
            self._doc = fitz.open(stream=data, filetype="pdf")
        except fitz.EmptyFileError as err:
            raise ValueError(err) from err
        except fitz.FileDataError as err:
            raise ValueError(err) from err

        self._checksum: str = sha1(data).hexdigest()
        self._regions: dict[int, list[fitz.IRect]] = {}

    @property
    def name(self) -> str:
        """! The PDF's filename. """
        return self._name

    @property
    def page_count(self) -> int:
        """! The number of pages in the PDF file. """
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
        if page < 0 or page >= self.page_count:
            return

        self._regions[page] = []

    def mark_all_pages_empty(self) -> None:
        """! Mark all pages as having no regions at all.
        """
        for i in range(self.page_count):
            self._regions[i] = []

    def remove_region(self, page: int, region: int) -> None:
        """! Remove a region from a page.

        @param page    The page to remove the region from.
        @param region  The region to remove.
        """
        if page < 0 or page >= self.page_count or region < 0 or region >= len(self.get_regions(page) or []):
            return

        regions = self.get_regions(page)
        assert regions is not None
        regions.pop(region)

    def add_region(self, page: int, left: int, top: int, right: int, bottom: int) -> None:
        """! Add a new region to a page.

        @param page    The page to add the new region to.
        @param left    The region's left coordinate.
        @param top     The region's top coordinate.
        @param right   The region's right coordinate.
        @param bottom  The region's bottom coordinate.
        """
        if page < 0 or page >= self.page_count:
            return

        p = self._doc.load_page(page)

        left = max(0, min(left, p.rect.width - 1))
        right = max(0, min(right, p.rect.width - 1))
        top = max(0, min(top, p.rect.height - 1))
        bottom = max(0, min(bottom, p.rect.height - 1))

        if left >= right or top >= bottom:
            return

        regions = self.get_regions(page)
        assert regions is not None
        regions.append(fitz.IRect(left, top, right, bottom))

    def modify_region(self, page: int, region: int, left: int, top: int, right: int, bottom: int):
        """! Modify an existing region on a page.

        @param page    The page to modify the region on.
        @param region  The region to modify.
        @param left    The region's new left coordinate.
        @param top     The region's new top coordinate.
        @param right   The region's new right coordinate.
        @param bottom  The region's new bottom coordinate.
        """
        if page < 0 or page >= self.page_count or region < 0 or region >= len(self.get_regions(page) or []):
            return

        p = self._doc.load_page(page)

        left = max(0, min(left, p.rect.width - 1))
        right = max(0, min(right, p.rect.width - 1))
        top = max(0, min(top, p.rect.height - 1))
        bottom = max(0, min(bottom, p.rect.height - 1))

        if left >= right or top >= bottom:
            return

        regions = self.get_regions(page)
        assert regions is not None
        regions[region] = fitz.IRect(left, top, right, bottom)

    def reorder_region(self, page: int, region: int, direction: int) -> int:
        """! Reorder regions of a page, by moving a single region "up" or "down" the stack.

        @param page       The page to reorder the regions of.
        @param region     The region to move.
        @param direction  The direction (and amount) to move the region.
                          If < 0, this moves the region "up" as many places.
                          If > 0, this moves the region "down" as many places.

        @return The new index of the moved region.
        """
        if page < 0 or page >= self.page_count or region < 0 or region >= len(self.get_regions(page) or []):
            return region

        regions = self.get_regions(page)
        assert regions is not None

        # As long as we want and can move the region "up", swap it with its predecessor
        while direction < 0:
            if region == 0:
                break

            regions[region - 1], regions[region] = regions[region], regions[region - 1]

            region -= 1
            direction += 1

        # As long as we want and can move the region "down", swap it with its successor
        while direction > 0:
            if region >= (len(regions) - 1):
                break

            regions[region + 1], regions[region] = regions[region], regions[region + 1]

            region += 1
            direction -= 1

        return region

    def render_page(self, page: int) -> Optional[QImage]:
        """! Render a page into an image.

        @param page  The page to render.

        @return An image of the rendered page or None if the page is out of bounds.
        """

        if page < 0 or page >= self.page_count:
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

        if page < 0 or page >= self.page_count:
            return None

        if page not in self._regions:
            self._regions[page] = column_boxes(self._doc.load_page(page),
                                               footer_margin=bottom_margin, header_margin=top_margin,
                                               left_margin=left_margin, right_margin=right_margin,
                                               no_image_text=no_image_text)

        return self._regions[page]

    def find_region(self, page: int, x: int, y: int) -> int:
        """! Find which region of a page these coordinates are in.

        @param page  The page to look at.
        @param x     X coordinate to check against.
        @param y     Y coordinate to check against.

        @return Index of the region these coordinates are in, or -1 if none match.
        """

        regions = self.get_regions(page) or []

        for i, region in enumerate(regions):
            if (x, y) in region:
                return i

        return -1

    def serialize_regions(self, extra_data: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        """! Serialize the regions of this PDF, with metadata, into a dictionary.

        @param extra_data  A dictionary containing extra data to serialize.

        @return A dictionary containing the serialized data.
        """

        data = {
            'version': {'major': 1, 'minor': 0, 'patch': 1},
            'pdf': {
                'name': self._name,
                'checksum': self._checksum,
                'pages': self.page_count
            },
            'pages': self._regions
        }

        return RegionsSchema().dump((extra_data or {}) | data)

    def deserialize_regions(self, data) -> dict[str, Any]:
        """! Deserialize the regions of this PDF from saved data.

        @param data  The data to deserialize from.

        @return A dictionary containing the deserialized data.
        """

        schema = RegionsSchema()

        major, minor, patch = schema.get_version(data)
        if major != 1 or minor > 0:
            raise ValidationError(f"Unsupported region file version {major}.{minor}.{patch}")

        if isinstance(data, str):
            result = schema.loads(data)
        else:
            result = schema.load(data)

        if result["pdf"]["checksum"] != self._checksum:
            raise ValidationError(f"PDF file checksum mismatch ({self._checksum} vs {result['pdf']['checksum']})")
        if result["pdf"]["pages"] != self.page_count:
            raise ValidationError(f"PDF page count mismatch ({self.page_count} vs {result['pdf']['pages']})")

        self._regions = result["pages"]
        return result

    def _convert_region_to_text(self, page: int, region: fitz.IRect, concat_paragraphs: bool) -> str:
        p = self._doc.load_page(page)

        text = p.get_text(clip=region, sort=True)
        if concat_paragraphs:
            text = text.replace(" \n", " ")

        return text

    def convert_region_to_text(self, page: int, region: int, concat_paragraphs: bool = False) -> str:
        """! Convert a single region of a single page to text.

        @param page               The page to look at.
        @param region             The region to convert.
        @param concat_paragraphs  Autodetect when a line end is not a paragraph end and remove the line end,
                                  concatting paragraphs into single lines.

        @return The text contained in the region as string.
        """
        if page < 0 or page >= self.page_count or region < 0 or region >= len(self.get_regions(page) or []):
            return ""

        regions = self.get_regions(page)
        assert regions is not None

        return self._convert_region_to_text(page, regions[region], concat_paragraphs)

    def convert_page_to_text(self, page: int, concat_paragraphs: bool = False) -> str:
        """! Convert a single page to text, region by region.

        @param page               The page to look at.
        @param concat_paragraphs  Autodetect when a line end is not a paragraph end and remove the line end,
                                  concatting paragraphs into single lines.

        @return The text contained in the page as string.
        """

        if page < 0 or page >= self.page_count:
            return ""

        text = ""

        regions = self.get_regions(page) or []
        for region in regions:
            text += self._convert_region_to_text(page, region, concat_paragraphs) + "\n"

        return text
