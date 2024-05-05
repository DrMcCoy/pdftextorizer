"""! Utility functions.
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

import email.utils
from importlib import metadata
from typing import Any

PACKAGE_NAME = "pdftextorizer"
COPYRIGHT_YEARS = "2024"


class Util:  # pylint: disable=too-few-public-methods
    """! Utility functions.
    """

    @staticmethod
    def get_project_info() -> dict[str, Any]:
        """! Get project metadata information.

        @return A dict containing project metadata information.
        """
        project_metadata = metadata.metadata(PACKAGE_NAME)

        info: dict[str, Any] = {}
        info["name"] = project_metadata["Name"]
        info["version"] = project_metadata["Version"]
        info["summary"] = project_metadata["Summary"]
        info["years"] = COPYRIGHT_YEARS

        # Project URLs are stored with the "type" information pasted in front
        info["url"] = {}
        for i in project_metadata.get_all("Project-URL") or []:
            parsed = i.split(", ", 1)
            info["url"][parsed[0]] = parsed[1]

        # Authors are stored in an email address format, pasted together into one string
        info["authors"] = []
        for address in project_metadata["Author-email"].split(", "):
            parsed = email.utils.parseaddr(address)
            info["authors"].append(f"{parsed[0]} <{parsed[1]}>")

        return info

    @staticmethod
    def get_version_string() -> str:
        """! Get formated version information.
        """

        info: dict[str, Any] = Util.get_project_info()

        version_string = ""
        version_string += f"{info['name']} {info['version']}\n"
        version_string += f"{info['url']['homepage']}\n"
        version_string += "\n"
        version_string += f"Copyright (c) {info['years']} {', '.join(info['authors'])}\n"
        version_string += "\n"
        version_string += "This is free software; see the source for copying conditions.  There is NO\n"
        version_string += "warranty; not even for MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE."

        return version_string
