PDF Textorizer README
=====================

PDF Textorizer is a GUI application to interactively extract text from
multi-column PDFs, licensed under the terms of the
[GNU Affero General Public License version 3](https://www.gnu.org/licenses/agpl.html)
(or later), written in Python.

Installation
------------

To install PDF Textorizer system-wide, use
```
pip install .
```

To install PDF Textorizer for the current user only, use
```
pip install --user .
```

To install PDF Textorizer in a virtualenv, use
```
pip -m venv env
source env/bin/activate
pip install .
```

Optionally, the included [Makefile](Makefile) can be leveraged to install and
run PDF Textorizer from a virtualenv. Please read the [Makefile](Makefile) itself
to understand what it can do.

A typical example would be:

```
make run
```

This would install PDF Textorizer into a virtualenv and run it.

A more elaborate example:

```
PYTHON=python3 make run arg="-h"
```

This would install PDF Textorizer into a virtualenv and run using "python3" as
the Python environment, with the command line parameter "-h" (thus showing
the help text).
