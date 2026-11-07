"""The canonical bootstrap template: what ensure_installed does in each environment.

The three environments are faked: JupyterLite by sys.platform and a recording piplite,
Colab by a google.colab module and a recording subprocess.run, and a desktop is the default.
"""

import asyncio
import importlib.metadata
import importlib.util
import sys
import types
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


template = load("bootstrap_template")
sync = load("sync_bootstrap")

GIT_URL = "https://github.com/example/demo"


@pytest.fixture
def env(monkeypatch):
    """A package called demo-pkg, version 1.0.0, in all three environments."""
    versions = {"demo-pkg": "1.0.0"}
    fake = types.ModuleType("demopkg")
    fake.__version__ = "1.0.0"
    monkeypatch.setitem(sys.modules, "demopkg", fake)
    monkeypatch.setattr(template, "PACKAGE", "demo-pkg")
    monkeypatch.setattr(template, "IMPORT_NAME", "demopkg")
    monkeypatch.setattr(template, "GIT_URL", GIT_URL)

    def version(name):
        if name not in versions:
            raise importlib.metadata.PackageNotFoundError(name)
        return versions[name]

    monkeypatch.setattr(importlib.metadata, "version", version)
    return types.SimpleNamespace(versions=versions)


def run(**kwargs):
    return asyncio.run(template.ensure_installed(**kwargs))


# ---- comparing versions ----


def test_older():
    assert template._older("1.4.1", "1.5.0")
    assert template._older("1.5.0.dev3", "1.5.0")
    assert not template._older("1.5.0", "1.5.0")
    assert not template._older("2.0", "1.5.0")
    assert not template._older("unknown", "1.5.0")  # cannot compare, so say nothing


# ---- on a desktop ----


def test_a_desktop_installs_nothing_and_says_where_it_is(env, capsys):
    assert run() is False
    assert "Running locally using demo-pkg v1.0.0" in capsys.readouterr().out


def test_a_desktop_says_which_packages_are_missing(env, capsys):
    env.versions["control"] = "0.10.2"
    run(packages=["control", "other"])
    out = capsys.readouterr().out
    assert "pip install other" in out and "pip install control" not in out


def test_a_desktop_says_what_to_run_when_the_release_is_too_old(env, capsys):
    run(min_version="2.0.0")
    assert (
        "needs demo-pkg 2.0.0 or later: pip install -U demo-pkg"
        in capsys.readouterr().out
    )
    run(min_version="1.0.0")
    assert "needs demo-pkg 1.0.0" not in capsys.readouterr().out


# ---- in JupyterLite ----


@pytest.fixture
def lite(env, monkeypatch):
    calls = []
    fake = types.ModuleType("piplite")

    async def install(name, deps=True):
        calls.append((name, deps))

    fake.install = install
    monkeypatch.setitem(sys.modules, "piplite", fake)
    monkeypatch.setattr(sys, "platform", "emscripten")
    monkeypatch.setattr(template, "JL_PACKAGES", ["ipympl"])
    monkeypatch.setattr(template, "JL_NO_DEPS", [])
    monkeypatch.setattr(template, "JL_EXTRAS", {"ik": ["sympy"]})
    return calls


def test_the_browser_installs_in_order_and_the_toolbox_last(lite, capsys):
    assert run(extras=["ik"], packages=["control"]) is False
    assert [name for name, _ in lite] == ["ipympl", "sympy", "control", "demo-pkg"]
    assert "Running in browser using demo-pkg v1.0.0" in capsys.readouterr().out


def test_the_browser_installs_no_deps_packages_first_without_their_deps(
    lite, monkeypatch
):
    monkeypatch.setattr(template, "JL_NO_DEPS", ["fragile"])
    run()
    assert lite[0] == ("fragile", False)


def test_the_browser_does_not_check_the_version(lite, capsys):
    run(min_version="99")  # the site's wheel is built from the notebook's own commit
    assert "needs" not in capsys.readouterr().out and len(lite) == 2


def test_the_default_installs_no_spatialmath_workaround():
    assert template.JL_NO_DEPS == []


# ---- on Colab ----


@pytest.fixture
def colab(env, monkeypatch):
    commands = []

    def fake_run(command, check):
        commands.append(command)
        if any("git+" in part for part in command):
            env.versions["demo-pkg"] = "2.0.0"  # what the development version says

    google, colab_module = types.ModuleType("google"), types.ModuleType("google.colab")
    google.__path__ = []
    google.colab = colab_module
    colab_module.output = types.SimpleNamespace(
        enable_custom_widget_manager=lambda: None
    )
    monkeypatch.setitem(sys.modules, "google", google)
    monkeypatch.setitem(sys.modules, "google.colab", colab_module)
    monkeypatch.setattr(template.subprocess, "run", fake_run)
    monkeypatch.setattr(template, "COLAB_PACKAGES", ["ipympl"])
    return commands


def test_colab_installs_the_package_extras_and_other_packages_in_one_command(
    colab, capsys
):
    assert run(extras=["ik", "x"], packages=["control"]) is True
    assert colab == [
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "-q",
            "demo-pkg[ik,x]",
            "control",
            "ipympl",
        ]
    ]
    assert "Running on Colab using demo-pkg v1.0.0" in capsys.readouterr().out


def test_colab_keeps_the_release_when_it_is_new_enough(colab, capsys):
    run(min_version="1.0.0")
    assert len(colab) == 1
    assert "development" not in capsys.readouterr().out


def test_colab_installs_the_development_version_when_the_release_is_too_old(
    colab, capsys
):
    run(extras=["ik"], min_version="2.0.0")
    assert len(colab) == 2
    git = colab[1]
    assert "--force-reinstall" in git and "--no-deps" in git
    assert git[-1] == f"demo-pkg @ git+{GIT_URL}@main"
    out = capsys.readouterr().out
    assert "older than 2.0.0, installing from GitHub" in out
    assert (
        "Running on Colab, development version from GitHub using demo-pkg v2.0.0" in out
    )


def test_colab_without_a_git_url_only_says_what_is_missing(colab, monkeypatch, capsys):
    monkeypatch.setattr(template, "GIT_URL", None)
    run(min_version="2.0.0")
    assert len(colab) == 1
    assert "needs demo-pkg 2.0.0 or later" in capsys.readouterr().out


# ---- the tools accept what the template takes ----


def test_sync_bootstrap_takes_the_new_arguments():
    text = (TOOLS / "bootstrap_template.py").read_text(encoding="utf-8")
    assert sync.parameters(text) == ["extras", "packages", "min_version"]
    call = sync.call(text, {"packages": ["control"], "min_version": "1.5.0"})
    assert call == "ensure_installed(packages=['control'], min_version='1.5.0')"
