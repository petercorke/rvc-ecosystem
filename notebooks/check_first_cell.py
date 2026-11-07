#!/usr/bin/env python
"""Check the first cell of each notebook: markdown, and a logo that keeps its shape.

The first cell of a notebook is a title and a logo, written as an HTML ``<img>``.  Colab
needs both a ``width`` and a ``height`` to keep the aspect ratio.  But a viewer that limits
an image to the width of its cell (a narrow notebook pane, VS Code, Colab) then shrinks the
width and leaves the height, so the logo is squashed.  ``style="height:auto"`` stops that,
and a viewer that drops the style falls back to the two attributes.  So every ``<img>`` in
the first cell must be::

    <img src="..." width="300" height="120" style="height:auto">

The first cell must also be markdown, not a code cell holding HTML.

Usage::

    check_first_cell.py [--dir docs/notebooks] [FILE ...]   exit 1 if any notebook breaks the rule
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nbconfig

IMG = re.compile(r"<img\b[^>]*>", re.IGNORECASE)


def problems(nb: dict) -> list[str]:
    """What is wrong with the first cell of a notebook, empty if nothing."""
    cells = nb.get("cells", [])
    if not cells:
        return []
    first = cells[0]
    if first.get("cell_type") != "markdown":
        return [
            f"the first cell is a {first.get('cell_type')} cell, it should be markdown"
        ]
    source = first.get("source", "")
    text = "".join(source) if isinstance(source, list) else source
    found = []
    for tag in IMG.findall(text):
        lacking = [
            what
            for what, pattern in (
                ("width", r"\bwidth\s*="),
                ("height", r"\bheight\s*="),
                ('style="height:auto"', r"style\s*=\s*[\"'][^\"']*height\s*:\s*auto"),
            )
            if not re.search(pattern, tag, re.IGNORECASE)
        ]
        if lacking:
            found.append(f"{tag[:60]}... lacks {', '.join(lacking)}")
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    # --nickname is accepted, so a repo can give every hook the same arguments, but not needed
    nbconfig.add_arguments(parser)
    args = parser.parse_args(argv)
    config = nbconfig.config_from(args)

    failed = False
    for path in nbconfig.notebooks(config, args.files):
        for message in problems(json.loads(path.read_text(encoding="utf-8"))):
            failed = True
            print(f"{path}: {message}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
