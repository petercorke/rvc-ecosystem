#!/usr/bin/env python
"""Clear the outputs of notebooks, and write them the way Jupyter does.

Notebooks are committed without outputs or execution counts, so a diff shows only what
was changed, and with the same kernel and language in the metadata: an editor writes the
name and version of your Python environment into a notebook, which is noise in every
diff.  Only the metadata that belongs to the repo (``<nickname>_bootstrap``) is kept.  The
file is written as nbformat writes it, so that opening and saving a notebook in an editor
never shows up as a change.

Pure standard library, so it runs as a commit hook on any machine that has Python.

Usage::

    clear_outputs.py            tidy every notebook in docs/notebooks
    clear_outputs.py --check    only report; exit 1 if any needs it
    clear_outputs.py FILE ...   only these notebooks, if they are in docs/notebooks
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nbconfig

KERNELSPEC = {"display_name": "Python 3", "language": "python", "name": "python3"}
LANGUAGE_INFO = {"name": "python"}


def normalize_metadata(nb: dict) -> bool:
    """Set a notebook's metadata to its canonical form, in place.

    The keys that belong to the repo, ``<nickname>_bootstrap``, are kept: whatever the
    nickname, they end in ``_bootstrap``.

    :returns: True if it was (or would be) changed.
    """
    old = nb.get("metadata", {})
    new = {"kernelspec": dict(KERNELSPEC), "language_info": dict(LANGUAGE_INFO)}
    new.update(
        {k: v for k, v in old.items() if k.endswith(nbconfig.OWN_METADATA_SUFFIX)}
    )
    if old == new:
        return False
    nb["metadata"] = new
    return True


def clear_cell(cell: dict) -> bool:
    """Clear one cell's outputs and execution count in place.

    :returns: True if the cell was (or would be) changed.
    """
    if cell.get("cell_type") != "code":
        return False
    changed = False
    if cell.get("outputs"):
        changed = True
        cell["outputs"] = []
    if cell.get("execution_count") is not None:
        changed = True
        cell["execution_count"] = None
    if "execution" in cell.get("metadata", {}):
        changed = True
        del cell["metadata"]["execution"]
    return changed


def process_notebook(path: Path, fix: bool) -> bool:
    """Check (and optionally tidy) one notebook.

    :returns: True if the notebook was (or would be) changed.
    """
    raw = path.read_text(encoding="utf-8")
    nb = json.loads(raw)
    # a list, not a generator: any() would stop at the first dirty cell
    changed = any([clear_cell(cell) for cell in nb.get("cells", [])])  # noqa: C419
    changed = normalize_metadata(nb) or changed
    text = nbconfig.canonical_text(nb)
    changed = changed or text != raw
    if changed and fix:
        nbconfig.write(path, text)
    return changed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    nbconfig.add_arguments(parser)
    parser.add_argument(
        "--check", action="store_true", help="report only; exit 1 if any needs tidying"
    )
    args = parser.parse_args(argv)
    config = nbconfig.config_from(args)

    any_changed = False
    for path in nbconfig.notebooks(config, args.files):
        if process_notebook(path, fix=not args.check):
            any_changed = True
            print(f"{path}: {'needs tidying' if args.check else 'tidied'}")
    return 1 if args.check and any_changed else 0


if __name__ == "__main__":
    sys.exit(main())
