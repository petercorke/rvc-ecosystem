"""What the notebook tools share: a repo's names, and how a notebook is written.

A repo is identified by a *nickname* (``rtb``, ``mvtb``, ``bdsim``), which is read from the
name of its template, ``_<nickname>_nb_bootstrap.py``, in the notebooks folder.  Nothing
needs configuring: ``--nickname`` is only there to choose between several templates, or
to say it when there is none yet.  The names the tools use follow from the nickname:

=====================  ==========================  ==============================
                       ``bdsim``                   what it is
=====================  ==========================  ==============================
marker                 ``BDSIM_BOOTSTRAP_CELL``    first line of the generated cell
metadata key           ``bdsim_bootstrap``         a notebook's own settings
template               ``_bdsim_nb_bootstrap.py``  the source of the cell
=====================  ==========================  ==============================

See ``notebooks.md`` section 3 for what the tools are for.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_DIRECTORY = "docs/notebooks"
TEMPLATE_NAME = re.compile(r"^_(?P<nickname>[A-Za-z0-9]+)_nb_bootstrap\.py$")
# the metadata of a notebook that belongs to the repo, whatever its nickname
OWN_METADATA_SUFFIX = "_bootstrap"


class ConfigError(ValueError):
    """The repo's nickname cannot be settled."""


@dataclass(frozen=True)
class Config:
    directory: Path
    nickname: str | None = None
    # the nicknames of the templates found in the folder, for the error message
    templates: tuple[str, ...] = field(default=(), compare=False)

    def require_nickname(self) -> str:
        """The nickname, or ConfigError saying what to do."""
        if self.nickname:
            return self.nickname
        if self.templates:
            names = ", ".join(f"_{n}_nb_bootstrap.py" for n in self.templates)
            raise ConfigError(
                f"several templates in {self.directory} ({names}): choose one with --nickname"
            )
        raise ConfigError(
            f"no _<nickname>_nb_bootstrap.py in {self.directory}: copy bootstrap_template.py "
            "there and change its constants, or give --nickname"
        )

    @property
    def marker(self) -> str:
        return f"# {self.require_nickname().upper()}_BOOTSTRAP_CELL"

    @property
    def metadata_key(self) -> str:
        return f"{self.require_nickname()}{OWN_METADATA_SUFFIX}"

    @property
    def template_path(self) -> Path:
        return self.directory / f"_{self.require_nickname()}_nb_bootstrap.py"


def templates_in(directory: Path) -> list[str]:
    """The nicknames of the templates in a folder, ``_<nickname>_nb_bootstrap.py``."""
    found = []
    for path in sorted(directory.glob("_*_nb_bootstrap.py")):
        match = TEMPLATE_NAME.match(path.name)
        if match:
            found.append(match.group("nickname").lower())
    return found


def add_arguments(
    parser: argparse.ArgumentParser, files: bool = True, nickname: bool = True
) -> None:
    if nickname:
        parser.add_argument(
            "--nickname",
            default=None,
            help="the repo's nickname, such as rtb, mvtb or bdsim; by default the one in the "
            "name of the template, _<nickname>_nb_bootstrap.py, in --dir",
        )
    parser.add_argument(
        "--dir",
        type=Path,
        default=Path(DEFAULT_DIRECTORY),
        help=f"the folder of notebooks, default {DEFAULT_DIRECTORY}. Notebooks "
        "outside it are left alone, even if named",
    )
    if files:
        parser.add_argument(
            "files",
            nargs="*",
            type=Path,
            help="only these notebooks (default: every *.ipynb in the folder)",
        )


def config_from(args: argparse.Namespace) -> Config:
    found = templates_in(args.dir)
    given = getattr(args, "nickname", None)
    if given:
        return Config(directory=args.dir, nickname=given.lower())
    if len(found) == 1:
        return Config(directory=args.dir, nickname=found[0])
    return Config(directory=args.dir, templates=tuple(found) if len(found) > 1 else ())


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
