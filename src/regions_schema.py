"""! Schema definition of a regions file.
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

import fitz
from marshmallow import EXCLUDE, Schema, ValidationError, fields, post_load, validate


class RegionsSchema(Schema):
    """! Schema definition of a regions file.
    """

    class Meta:  # pylint: disable=too-few-public-methods
        """! Meta controls for the schema. """
        unknown = EXCLUDE

    class Version(Schema):
        """! Schema definition for file's version. """

        class Meta:  # pylint: disable=too-few-public-methods
            """! Meta controls for the schema. """
            unknown = EXCLUDE

        major = fields.Int(required=True)
        minor = fields.Int(required=True)
        patch = fields.Int(required=True)

    class PDFFile(Schema):
        """! Schema definition for the PDF's metadata. """

        class Meta:  # pylint: disable=too-few-public-methods
            """! Meta controls for the schema. """
            unknown = EXCLUDE

        name = fields.Str(required=False)

        checksum = fields.Str(required=True)
        pages = fields.Int(required=True)

    class Margins(Schema):
        """! Schema definition for the current margin settings. """

        class Meta:  # pylint: disable=too-few-public-methods
            """! Meta controls for the schema. """
            unknown = EXCLUDE

        left = fields.Int(required=True)
        top = fields.Int(required=True)
        right = fields.Int(required=True)
        bottom = fields.Int(required=True)

        ignore_images = fields.Bool(required=True)

    version = fields.Nested(Version, required=True)

    pdf = fields.Nested(PDFFile, required=True)
    margins = fields.Nested(Margins, required=False)
    pages = fields.Dict(keys=fields.Int(),
                        values=fields.List(fields.List(fields.Int, required=True, validate=validate.Length(equal=4)),
                                           required=True),
                        required=True)

    def get_version(self, data) -> tuple[int, int, int]:
        """! Read the version while ignoring all other fields. """

        if isinstance(data, str):
            result = self.loads(data, partial=True)
        else:
            result = self.load(data, partial=True)

        if "version" not in result:
            raise ValidationError("No version information found")
        if "major" not in result["version"] or "minor" not in result["version"] or "patch" not in result["version"]:
            raise ValidationError("Invalid version information")

        return result["version"]["major"], result["version"]["minor"], result["version"]["patch"]

    @post_load
    def make_pages(self, data, **_):
        """! Convert page data into the proper format (a dict of lists of IRects). """

        data["pages"] = dict(map(lambda page: (page[0], list(map(fitz.IRect, page[1]))), data["pages"].items()))
        return data
