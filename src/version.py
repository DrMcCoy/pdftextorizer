"""! Figure out the current version number.
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

import re
import subprocess

VERSION_FALLBACK = "1.0.0+unk"


def get_version() -> str:
    """! Figure out the current version number from git, if available.
    """
    try:
        # Call git to describe the current version from the most recent desc/ tag
        result = subprocess.run(["git", "describe", "--tags", "--long", "--match", "desc/*"],
                                capture_output=True, encoding="utf-8", check=True)

        # Cut of the desc/ prefix and change the part separators to be conforming
        version = result.stdout.replace('\r', '').replace('\n', '').split("/", 2)[1]
        version = re.sub(r"(.*)-([^-]*)-([^-]*)", r"\1+\2.\3", version)

        # Update the index and check if files are modified. If so, append .dirty
        subprocess.run(["git", "update-index", "--refresh", "--unmerged"],
                       capture_output=True, encoding="utf-8", check=False)
        result = subprocess.run(["git", "diff-index", "--quiet", "HEAD"],
                                capture_output=True, encoding="utf-8", check=False)
        if result.returncode != 0:
            version = version + ".dirty"

        return version

    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    return VERSION_FALLBACK
