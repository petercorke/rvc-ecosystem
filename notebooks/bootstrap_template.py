"""Environment bootstrap for a toolbox's Jupyter notebooks: the canonical template.

Installs the toolbox (and reports how) across the three environments a notebook
might run in: a local Jupyter/VS Code install, Google Colab, and JupyterLite
(Pyodide/WASM, in-browser).

This is the reference copy for the big 3 (RTB, MVTB, bdsim).  A repo keeps its own
copy as ``docs/notebooks/_<nickname>_nb_bootstrap.py``, changes only the constants
under "Repo-specific" below, and uses ``sync_bootstrap.py`` to paste it into every
notebook as a generated cell, because Colab fetches only the single .ipynb it is
opened from and cannot see sibling files.  See ``notebooks.md`` section 3.

Derived from RTB's ``_rtb_nb_bootstrap.py`` (2026-11-02, with the Colab backend-list fix, RTB#922), which is the one that has
been tested in a real JupyterLite site and on Colab.  MVTB's differs, see
petercorke/machinevision-toolbox-python#160; bdsim has no bootstrap yet.
"""

import subprocess
import sys

# --- Repo-specific: the only part a repo should change -----------------------------

# the PyPI name of the toolbox, and the name it is imported under
PACKAGE = "roboticstoolbox-python"
IMPORT_NAME = "roboticstoolbox"

# JupyterLite only: packages installed, with their dependencies, before the toolbox.
# Everything the notebooks' plotting needs that Pyodide does not already have.
JL_PACKAGES = ["ipympl"]

# JupyterLite only: packages installed with deps=False before everything else.
# spatialmath-python <= 1.1.18 lists pre-commit (a dev tool) as a runtime dependency;
# its virtualenv requires packaging>=26.3, which conflicts with the packaging 24.2
# built into Pyodide, so a normal resolve fails.  Installed without dependencies
# first, it is then already satisfied when the toolbox's own are resolved.  Remove
# this once a spatialmath release without that dependency is out
# (rai-opensource/spatialmath-python#250).  A package that depends on
# spatialmath-python (pgraph-python, bdsim) needs the same treatment.
JL_NO_DEPS = ["spatialmath-python"]

# extras of the toolbox that need more than Pyodide has, installed in JupyterLite as
# these packages instead of through the extra: extra name -> packages
JL_EXTRAS: dict[str, list[str]] = {"ik": ["sympy"]}

# Colab only: packages installed with the toolbox.  Colab does not ship ipympl,
# which the notebooks select with %matplotlib ipympl.
COLAB_PACKAGES = ["ipympl"]

# ---------------------------------------------------------------------------------


async def ensure_installed(extras: tuple[str, ...] | list[str] = ()) -> bool:
    """Install the toolbox if needed, and report the environment.

    :param extras: toolbox extras the notebook needs, for example ``["ik"]``.  They
        are set per notebook in its metadata (``rtb_bootstrap.extras``) and
        passed here by the generated cell.
    :returns: True if running on Google Colab, False otherwise.
    """
    if sys.platform == "emscripten":
        # In JupyterLite, piplite looks in this site's own package index first, so the
        # toolbox it installs is the wheel that was built with the site.  micropip
        # alone cannot see that index and would install the last release from PyPI.
        # (There is no /pypi folder in the kernel to glob for a wheel.)  Outside
        # JupyterLite, for example a test under Node, there is no piplite.
        try:
            import piplite

            install = piplite.install
        except ImportError:
            import micropip

            install = micropip.install

        for name in JL_NO_DEPS:
            await install(name, deps=False)
        for name in JL_PACKAGES:
            await install(name)
        for extra in extras:
            for name in JL_EXTRAS.get(extra, []):
                await install(name)
        await install(PACKAGE)
        where, colab = "in browser", False
    else:
        try:
            import google.colab  # noqa: F401
        except ImportError:
            where, colab = "locally", False
        else:
            print(f"Installing {PACKAGE}...")
            requirement = PACKAGE
            if extras:
                requirement += "[" + ",".join(extras) + "]"
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "-q", requirement]
                + COLAB_PACKAGES,
                check=True,
            )
            # matplotlib renames the module://ipympl... backend to "widget", and looks
            # it up in a list of backends that it builds once, from the installed
            # packages, the first time it needs it.  Colab imported matplotlib before
            # ipympl was installed, so %matplotlib ipympl is rejected ("... is not a
            # valid value for backend") until the session restarts.  Make matplotlib
            # build the list again.  Clearing the registry is what its own tests do,
            # and it is needed: only resetting the flag registers the backends that
            # were already there (matplotlib-inline's) twice, which is an error.
            # _clear is private, hence the guards.
            try:
                from matplotlib.backends import backend_registry
            except ImportError:
                pass  # an older matplotlib has no registry to refresh
            else:
                clear = getattr(backend_registry, "_clear", None)
                if clear is not None:
                    clear()

            # ipympl figures need Colab's custom widget manager, enabled before the
            # first figure is created.
            from google.colab import output

            output.enable_custom_widget_manager()
            where, colab = "on Colab", True

    import importlib

    module = importlib.import_module(IMPORT_NAME)
    version = getattr(module, "__version__", "unknown")
    print(f"Running {where} using {PACKAGE} v{version}")
    return colab
