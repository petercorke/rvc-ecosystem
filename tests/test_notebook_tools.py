"""The notebook tools: clear_outputs.py, sync_bootstrap.py and check_first_cell.py."""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1] / "notebooks"
sys.path.insert(0, str(TOOLS))


def load(name):
    spec = importlib.util.spec_from_file_location(name, TOOLS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


nbconfig = load("nbconfig")
clear = load("clear_outputs")
sync = load("sync_bootstrap")
first = load("check_first_cell")

TEMPLATE = '''"""A template."""
import sys

async def ensure_installed(extras=(), packages=(), min_version=None):
    """Install."""
    print("installing", extras)
    return False
'''
LOGO = '<img src="x.png" width="300" height="120" style="height:auto">'


_ids = iter(range(10_000))


def cell(kind, source, **extra):
    c = {"cell_type": kind, "id": f"c{next(_ids)}", "metadata": {}, "source": source}
    if kind == "code":
        c.update(outputs=[], execution_count=None)
    c.update(extra)
    return c


def notebook(cells, metadata=None):
    return {
        "cells": cells,
        "metadata": metadata or {},
        "nbformat": 4,
        "nbformat_minor": 5,
    }


@pytest.fixture
def folder(tmp_path):
    (tmp_path / "_demo_nb_bootstrap.py").write_text(TEMPLATE, encoding="utf-8")
    return tmp_path


def save(folder, name, nb):
    path = folder / name
    path.write_text(nbconfig.canonical_text(nb), encoding="utf-8")
    return path


def config(folder):
    return nbconfig.Config("demo", folder)


# ---- names ----


def test_the_names_follow_from_the_nickname(folder):
    c = config(folder)
    assert c.marker == "# DEMO_BOOTSTRAP_CELL"
    assert c.metadata_key == "demo_bootstrap"
    assert c.template_path == folder / "_demo_nb_bootstrap.py"
    assert nbconfig.Config("rtb", folder).marker == "# RTB_BOOTSTRAP_CELL"


# ---- clear_outputs ----


def test_a_cell_loses_its_output_and_count():
    c = cell("code", "1", outputs=[{"output_type": "stream"}], execution_count=3)
    c["metadata"]["execution"] = {"x": 1}
    assert clear.clear_cell(c)
    assert (
        c["outputs"] == []
        and c["execution_count"] is None
        and "execution" not in c["metadata"]
    )
    assert not clear.clear_cell(c)
    assert not clear.clear_cell(cell("markdown", "text"))


def test_every_dirty_cell_is_cleared_not_just_the_first(folder):
    nb = notebook(
        [cell("code", "a", execution_count=1), cell("code", "b", execution_count=2)]
    )
    path = save(folder, "a.ipynb", nb)
    assert clear.process_notebook(path, ("demo_bootstrap",), fix=True)
    assert all(
        c["execution_count"] is None for c in json.loads(path.read_text())["cells"]
    )


def test_check_mode_reports_and_does_not_write(folder):
    path = save(folder, "a.ipynb", notebook([cell("code", "a", execution_count=1)]))
    before = path.read_text()
    assert clear.process_notebook(path, ("demo_bootstrap",), fix=False)
    assert path.read_text() == before


def test_it_is_idempotent_and_writes_as_nbformat_does(folder):
    path = save(folder, "a.ipynb", notebook([cell("code", "a", execution_count=1)]))
    clear.process_notebook(path, ("demo_bootstrap",), fix=True)
    first_text = path.read_text()
    assert first_text == nbconfig.canonical_text(json.loads(first_text))
    assert not clear.process_notebook(path, ("demo_bootstrap",), fix=True)
    assert path.read_text() == first_text


def test_editor_metadata_goes_and_the_repos_own_stays():
    nb = notebook(
        [],
        {
            "kernelspec": {"name": "dev", "display_name": "dev"},
            "language_info": {"name": "python", "version": "3.12.1"},
            "demo_bootstrap": {"extras": ["x"]},
            "widgets": {"state": 1},
        },
    )
    assert clear.normalize_metadata(nb, ("demo_bootstrap",))
    assert nb["metadata"] == {
        "kernelspec": clear.KERNELSPEC,
        "language_info": clear.LANGUAGE_INFO,
        "demo_bootstrap": {"extras": ["x"]},
    }


# ---- sync_bootstrap ----


def test_the_call_follows_the_notebooks_settings():
    assert sync.call(TEMPLATE, {}) == "ensure_installed()"
    assert sync.call(TEMPLATE, {"extras": ["ik"]}) == "ensure_installed(extras=['ik'])"
    both = sync.call(TEMPLATE, {"min_version": "1.5.0", "packages": ["control"]})
    assert both == "ensure_installed(packages=['control'], min_version='1.5.0')"


def test_a_setting_the_template_does_not_take_is_an_error():
    with pytest.raises(ValueError, match="does not take extra"):
        sync.call(TEMPLATE, {"extra": ["ik"]})


def test_the_generated_cell_has_the_marker_and_no_docstrings(folder):
    source = "".join(sync.generated_source(config(folder), TEMPLATE, {}))
    assert source.startswith("# DEMO_BOOTSTRAP_CELL")
    assert "from _demo_nb_bootstrap.py" in source and "A template." not in source
    assert source.rstrip().endswith("COLAB = await ensure_installed()")


def test_an_out_of_date_cell_is_regenerated_wherever_it_is(folder):
    stale = cell("code", "# DEMO_BOOTSTRAP_CELL: old\nprint(1)\n")
    path = save(
        folder,
        "a.ipynb",
        notebook([cell("markdown", "title"), cell("code", "x"), stale]),
    )
    assert sync.process_notebook(path, config(folder), TEMPLATE, fix=True)
    cells = json.loads(path.read_text())["cells"]
    assert "ensure_installed" in "".join(cells[2]["source"])
    assert not sync.process_notebook(path, config(folder), TEMPLATE, fix=True)


def test_the_extras_come_from_the_notebooks_metadata(folder):
    nb = notebook(
        [cell("code", "# DEMO_BOOTSTRAP_CELL\n")],
        {"demo_bootstrap": {"extras": ["ik"]}},
    )
    path = save(folder, "a.ipynb", nb)
    sync.process_notebook(path, config(folder), TEMPLATE, fix=True)
    assert "ensure_installed(extras=['ik'])" in "".join(
        json.loads(path.read_text())["cells"][0]["source"]
    )


def test_check_mode_reports_without_writing(folder):
    path = save(folder, "a.ipynb", notebook([cell("code", "# DEMO_BOOTSTRAP_CELL\n")]))
    before = path.read_text()
    assert sync.process_notebook(path, config(folder), TEMPLATE, fix=False)
    assert path.read_text() == before


def test_without_the_cell_nothing_happens_unless_asked_to_add(folder):
    nb = notebook([cell("markdown", "title"), cell("code", "import numpy")])
    path = save(folder, "a.ipynb", nb)
    assert not sync.process_notebook(path, config(folder), TEMPLATE, fix=True)
    assert sync.process_notebook(path, config(folder), TEMPLATE, fix=True, add=True)
    cells = json.loads(path.read_text())["cells"]
    assert [c["cell_type"] for c in cells] == ["markdown", "code", "code"]
    assert sync.is_bootstrap_cell(cells[1], config(folder))  # after the title
    assert cells[1]["metadata"]["jupyter"] == {"source_hidden": True}
    assert not sync.process_notebook(path, config(folder), TEMPLATE, fix=True, add=True)


def test_cells_get_unique_ids_and_nbformat_5(folder):
    nb = notebook([cell("markdown", "a"), cell("code", "b")])
    for c in nb["cells"]:
        del c["id"]
    nb["nbformat_minor"] = 2
    path = save(folder, "a.ipynb", nb)
    assert sync.process_notebook(path, config(folder), TEMPLATE, fix=True)
    data = json.loads(path.read_text())
    ids = [c["id"] for c in data["cells"]]
    assert len(set(ids)) == 2 and data["nbformat_minor"] == 5


def test_the_command_line_end_to_end(folder):
    save(
        folder,
        "a.ipynb",
        notebook([cell("markdown", "title"), cell("code", "x", execution_count=2)]),
    )

    def run(*args):
        return subprocess.run(
            [sys.executable, *args],
            capture_output=True,
            text=True,
            cwd=folder,
            check=False,
        )

    common = ["--nickname", "demo", "--dir", str(folder)]
    assert (
        run(str(TOOLS / "sync_bootstrap.py"), *common, "--check", "--add").returncode
        == 1
    )
    assert run(str(TOOLS / "sync_bootstrap.py"), *common, "--add").returncode == 0
    assert run(str(TOOLS / "clear_outputs.py"), *common).returncode == 0
    assert run(str(TOOLS / "sync_bootstrap.py"), *common, "--check").returncode == 0
    assert run(str(TOOLS / "clear_outputs.py"), *common, "--check").returncode == 0
    assert (
        run(
            str(TOOLS / "sync_bootstrap.py"),
            "--nickname",
            "other",
            "--dir",
            str(folder),
        ).returncode
        == 2
    )


# ---- check_first_cell ----


def test_a_logo_with_width_height_and_auto_style_is_fine():
    assert first.problems(notebook([cell("markdown", f"# Title\n{LOGO}\n")])) == []


@pytest.mark.parametrize(
    "tag, lacks",
    [
        ('<img src="x" width="300">', "height"),
        ('<img src="x" width="300" height="120">', 'style="height:auto"'),
        ('<img src="x" height="120" style="height:auto">', "width"),
        ('<img src="x">', "width, height"),
    ],
)
def test_a_logo_missing_something_says_what(tag, lacks):
    found = first.problems(notebook([cell("markdown", tag)]))
    assert len(found) == 1 and lacks in found[0]


def test_a_first_cell_without_an_image_is_fine_and_a_code_cell_is_not():
    assert first.problems(notebook([cell("markdown", "just a title")])) == []
    assert "should be markdown" in first.problems(notebook([cell("code", LOGO)]))[0]
    assert first.problems(notebook([])) == []


def test_the_source_may_be_a_list_of_lines():
    assert first.problems(notebook([cell("markdown", ["# T\n", '<img src="x">\n'])]))
