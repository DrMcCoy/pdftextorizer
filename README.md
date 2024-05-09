PDF Textorizer README
=====================

[TOC]

PDF Textorizer is a GUI application to interactively extract text from
multi-column PDFs, licensed under the terms of the
[GNU Affero General Public License version 3](https://www.gnu.org/licenses/agpl.html)
(or later), written in Python.


What does PDF Textorizer do?
----------------------------

PDF Textorizer loads PDF files and displays them, page by page. It
automatically detects columns of text in a PDF with a multi-column layout and
marks these regions on the currently displayed page.

The user can click on a region to select it. It can then be modified: the user
can move it across the page, change its size, move it up and down in the order
of regions and even delete it. Additionally, the user can add new regions by
drawing them over the current page. And to save the current progress, the whole
set of regions in PDF file can be saved into a JSON file and loaded back in
later.

Once the user is happy with the current setup, the text found in the regions
can be grabbed and exported, in order. As a quick preview, only the current
page can be either saved into a file or printed to standard out, and for the
final pass, the whole PDF can be converted.

Keyboard commands
-----------------

In addition to the global keyboard shortcuts advertised in the main menu,
PDF Textorizer supports a set of keyboard shortcuts for modifying regions.

NOTE: These shortcuts only work when the page view has the focus, by, for
      example, clicking on it first!

| Key Combination | Command                                      |
| --------------- | ---------------------------------------------|
| K               | Move to the first page in the PDF            |
| L               | Move to the previous page in the PDF         |
| J               | Move to the next page in the PDF             |
| H               | Move to the last in the PDF                  |
| Shift+K         | Select the first region on the page          |
| Shift+L         | Select the previous region on the page       |
| Shift+J         | Select the next region on the page           |
| Shift+H         | Select the last on the region                |
| Left            | Move the selected region left                |
| Right           | Move the selected region right               |
| Up              | Move the selected region up                  |
| Down            | Move the selected region down                |
| Shift+Left      | Grow the selected region horizontally        |
| Shift+Right     | Shrink the selected region horizontally      |
| Shift+Up        | Grow the selected region vertically          |
| Shift+Down      | Shrink the selected region vertically        |
| Page Up         | Move the selected region "up" in the stack   |
| Page Down       | Move the selected region "down" in the stack |
| Insert          | Add a new region                             |
| Delete          | Remove the selected region                   |

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
