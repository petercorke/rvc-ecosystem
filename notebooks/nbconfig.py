"""What the notebook tools share: a repo's names, and how a notebook is written.

A repo is identified by a *nickname* (``rtb``, ``mvtb``, ``bdsim``), from which the names
the tools use follow:

=====================  =======================  ==============================
                       ``bdsim``                what it is
=====================  =======================  ==============================
marker                 ``BDSIM_BOOTSTRAP_CELL``  first line of the generated cell
metadata key           ``bdsim_bootstrap``       a notebook's own settings
template               ``_bdsim_nb_bootstrap.py`` the source of the cell
=====================  =======================  ==============================

See ``notebooks.md`` section 3 for what the tools are for.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

DEFAULT_DIRECTORY = "docs/notebooks"


@dataclass(frozen=True)
class Config:
    nickname: str
    directory: Path

    @property
    def marker(self) -> str:
        return f"# {self.nickname.upper()}_BOOTSTRAP_CELL"

    @property
    def metadata_key(self) -> str:
        return f"{self.nickname}_bootstrap"

    @property
    def template_path(self) -> Path:
        return self.directory / f"_{self.nickname}_nb_bootstrap.py"


def add_arguments(
    parser: argparse.ArgumentParser, files: bool = True, nickname: bool = True
) -> None:
    parser.add_argument(
        "--nickname",
        required=nickname,
        default="repo",
        help="the repo's nickname, such as rtb, mvtb or bdsim",
    )
    parser.add_argument(
        "--dir",
        type=Path,
        default=Path(DEFAULT_DIRECTORY),
        help=f"the folder of notebooks, default {DEFAULT_DIRECTORY}",
    )
    if files:
        parser.add_argument(
            "files",
            nargs="*",
            type=Path,
            help="only these notebooks (default: every *.ipynb in the folder)",
        )


def config_from(args: argparse.Namespace) -> Config:
    return Config(nickname=args.nickname.lower(), directory=args.dir)


def is_under(path: Path, directory: Path) -> bool:
    """True if ``path`` is inside ``directory``, however either is written."""
    return path.resolve().is_relative_to(directory.resolve())


def notebooks(config: Config, files: list[Path]) -> list[Path]:
    """The notebooks to consider: the files given, or all of those in the folder.

    Only notebooks inside the folder count, even if named.  A hook is handed every
    staged ``*.ipynb`` by pre-commit, and a repo may keep notebooks elsewhere that these
    tools must not touch: MVTB's ``tests/RVC`` are regression tests of the book, whose
    recorded output is the point.
    """
    if files:
        return [
            path
            for path in files
            if path.suffix == ".ipynb" and is_under(path, config.directory)
        ]
    return sorted(config.directory.glob("*.ipynb"))


def canonical_text(nb: dict) -> str:
    """The notebook as nbformat (and so VS Code and Jupyter) writes it."""
    return json.dumps(nb, indent=1, ensure_ascii=False, sort_keys=True) + "\n"


def write(path: Path, text: str) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as f:
        f.write(text)
