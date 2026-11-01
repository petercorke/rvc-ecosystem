# Writing notebooks that work on the desktop and in JupyterLite

A notebook in RTB, MVTB or bdsim has to run in two very different places:

* **Desktop**: Jupyter, JupyterLab or VS Code, talking to a real Python on your machine.
* **JupyterLite**: the same notebook running in a browser tab, on Python compiled to
  WebAssembly (Pyodide), behind a "Try it Now" badge. Nothing is installed, nothing runs on a server.

This page is a short tutorial on writing one notebook that works in both. The common jobs are
**making a new plot** and **adding to an existing plot**, so most of it is about plotting.
Everything marked *tested* was checked while writing this page: VS Code and local Jupyter with
Matplotlib 3.11, and a local JupyterLite site (kernel 0.6.1, Pyodide 0.27.6, Matplotlib 3.8.4).
Colab is covered in section 3.3; it was tested by hand with RTB, a static plot and an animation, on 2026-11-01.

## 1. The two environments

| | Desktop | JupyterLite |
|---|---|---|
| Python | your install, any version | Pyodide, in the browser |
| Packages | already installed with `pip` | installed by the notebook at start-up, from PyPI or from wheels bundled with the site |
| Compiled extensions | work | only if built for WebAssembly, otherwise use a pure-Python wheel |
| Plot windows | can be separate windows (`macosx`, `qt`) or in the notebook | in the notebook only |
| `plt.show(block=True)` | can block until a window is closed | cannot meaningfully block |
| Saved edits | in your file | in the browser; see [section 7](#7-pitfalls) |

The notebook must therefore (1) set itself up differently in each place, and (2) restrict itself to
plotting that behaves the same in both. Section 3 covers the first, sections 4 and 5 the second.

## 2. Matplotlib backends: static images or live widgets

The **backend** decides what a figure *is* in a notebook. The one-line magic that selects it is the
most important line in the first cell.

| Backend (magic) | What you get | Good | Bad |
|---|---|---|---|
| `inline` (`%matplotlib inline`) | a static image (PNG or SVG), placed in the cell output | simple, light, works everywhere, renders on GitHub and in exported HTML | **no later changes**: the figure is closed at the end of the cell, so a later cell cannot add to it; no zoom or pan |
| `ipympl` (`%matplotlib widget`, same thing) | a **live widget** in the cell: zoom, pan, and later cells can change it | the "add to the plot from a later cell" job works; it is interactive | each figure is a widget kept alive until closed, so figures pile up (section 6); saved notebooks show only a snapshot image; needs `ipympl` installed (and, in JupyterLite, in the site, section 3) |
| `macosx`, `qt`, `tk` | a separate native window | fast, familiar | desktop only; the notebook and the window are separate; `block=` matters |
| `notebook` (nbagg) | an older live widget | none now | belongs to the classic Notebook, **not supported in JupyterLab or Notebook 7** (per the Matplotlib and Jupyter documentation, not tested here); do not use it. Several older RTB notebooks still have `%matplotlib notebook` and need migrating |

*Tested:* `inline` ignores `block` and closes figures after the cell, so editing an earlier plot
produces nothing. `ipympl` also ignores `block`, keeps the figure open, and a later cell can change it,
in VS Code and in local Jupyter. In JupyterLite the figures are live widgets with the same `ipympl`
backend; the later-cell edit and `block=` were not reported separately there.

**Recommendation: use `%matplotlib ipympl`.** It is the only choice where the two jobs below work.
In a local JupyterLite test site it worked, provided the kernel had `ipympl` installed and the site was
built in an environment that has `ipympl` (which brings the `jupyter-matplotlib` extension into the site).

MVTB's docs build currently rewrites `%matplotlib ipympl` to `%matplotlib inline` for its JupyterLite
site, so there its notebooks run with static images. Whether that rewrite can be dropped has **not** been
tried on MVTB's own site, and there may be reasons for it that this page does not know. It is worth an
experiment there; nobody should change it on the strength of this page alone.

## 3. The setup cells

Every notebook starts with a title cell, then **two** setup cells.

### 3.1 The bootstrap cell (generated, do not hand-edit)

This cell gets the packages installed. Every notebook in the big 3 should copy this mechanism, not
re-invent it:

* the logic lives once per repo, in `docs/notebooks/_<nickname>_nb_bootstrap.py`, which is a copy of
  the canonical [`notebooks/bootstrap_template.py`](./notebooks/bootstrap_template.py) in this repo with
  only its repo-specific constants changed (package name, what JupyterLite needs first);
* `sync_bootstrap.py` pastes it into every notebook as a generated cell with a marker comment, and
  `sync_bootstrap.py --check` fails CI if any notebook has drifted;
* each notebook carries its own copy because Colab fetches only the single `.ipynb`;
* the cell is folded by default (`"jupyter": {"source_hidden": true}`), and prints one line saying where it
  is running and which versions it found.

The template is RTB's bootstrap (2026-11-01), the one tested in a real JupyterLite site and on Colab.
MVTB's differs and has a known bug (petercorke/machinevision-toolbox-python#160, below); bdsim has
hand-written install cells (petercorke/bdsim#174).

What it does in each place:

* **JupyterLite** (`sys.platform == "emscripten"`): install through `piplite`, which looks in the site's
  own package index first, so the toolbox is the wheel built with the site; `micropip` alone cannot see
  that index and would install the last release from PyPI. (There is no `/pypi` folder in the kernel, so
  globbing for a wheel there never finds one: that is MVTB#160.) `spatialmath-python` is installed first
  with `deps=False`, because its normal dependency resolution fails in Pyodide (an old `pre-commit`
  dependency); remove that when a fixed release is out. Then whatever the plotting needs that Pyodide
  does not have, in particular `ipympl`, then the toolbox.
* **Colab**: `pip install` the toolbox and `ipympl`, then enable Colab's custom widget manager (below).
* **Desktop**: nothing to install; it checks and reports.

### 3.2 The plotting setup cell

The second cell is the same for every notebook:

```python
%matplotlib ipympl
import matplotlib.pyplot as plt
import numpy as np

plt.close("all")   # re-running the notebook from the top starts with no figures
```

The `plt.close("all")` matters because of the figure limit, section 6.

### 3.3 Colab

Colab is closer to the desktop than to JupyterLite. It is a real Python on a server, with normal `pip`,
compiled packages and no WebAssembly restrictions. The difference from your own desktop is that the
toolbox is not installed, and that is the one thing MVTB's bootstrap treats specially: it detects Colab
(`import google.colab`), `pip install`s the toolbox into the runtime, and returns `COLAB = True`. The
flag stays available to later cells; MVTB uses it in five notebooks, to set the display option
`last_expr_or_assign` only on Colab.

Sections 4 to 6 apply as on the desktop, with two things the bootstrap does for you. Colab does not ship
`ipympl`, so the bootstrap installs it with the toolbox. And live Matplotlib figures need Colab's own
custom widget manager, so the bootstrap calls `google.colab.output.enable_custom_widget_manager()` before
the first figure. Tested by hand on Colab with RTB (petercorke/robotics-toolbox-python#911): a static plot
is a live widget you can rotate, and an animation is a stream of images that cannot be rotated (the same
as the desktop). Without that call a figure may display but not respond to the mouse.

Also on Colab, the IPython shell is `google.colab._shell.Shell`, not a `ZMQInteractiveShell`, so a check
for "am I in a notebook" has to look for `google.colab` in `sys.modules` as well. RTB's did not, and
treated Colab as a desktop window, which displayed the same figure three times. spatialmath's
`environment()` (rai-opensource/spatialmath-python#271) does it once for all three repos.

## 4. The two common jobs

### Job 1: a new plot

**Write `fig, ax = plt.subplots()`, not `plt.figure()`.**

```python
fig, ax = plt.subplots()
smb.plot_circle(2, (5, 5), ax=ax)     # a toolbox plot draws onto it
ax.set(xlim=(0, 10), ylim=(0, 10), aspect="equal")
```

Why not `plt.figure()`? Toolbox plot functions (they all go through spatialmath's `axes_logic`) draw onto
the **current axes** if there are any. A bare `plt.figure()` has *no* axes, so the toolbox decides it
has nothing to use and creates a **second** figure, leaving yours empty. That is the empty extra figure
you have probably seen. `plt.subplots()` gives you a figure that already has axes, so the toolbox uses it.
Passing `ax=ax` is then optional but good practice, and mandatory if you have several axes.

*Tested:* in VS Code, local Jupyter and JupyterLite, a bare `plt.figure()` followed by a toolbox plot
left an empty figure; `plt.subplots()` did not.

> **Note, 2026-10-17.** A fix to spatialmath's `axes_logic` will let a bare `plt.figure()` work: the toolbox
> will put its axes in the empty figure instead of making a second one, and it autoscales them. The change is
> in a branch of Peter's fork (`fix/axes-logic-reuse-empty-figure`, with tests) and is **not yet a pull
> request** to the upstream spatialmath but is now
> [rai-opensource/spatialmath-python#265](https://github.com/rai-opensource/spatialmath-python/pull/265),
> opened 2026-10-17. It is pending on RAI to merge it and publish a release. Until a release containing it is on PyPI, and the notebooks can
> require that version, keep to `plt.subplots()` as written here. When that happens this note and the
> "known gap" in section 9 should be updated.

Two practical notes:

* Matplotlib axes made by `plt.subplots()` have limits 0 to 1. Plot functions that draw an image set their
  own limits; some others do not. If a plot looks empty, set the limits.
* For 3D: `fig = plt.figure(); ax = fig.add_subplot(projection="3d")`. The extra step gives the figure
  its axes.

### Job 2: add to an existing plot

Two cases.

**In the same cell** (works in every backend, including `inline`): call another plot function. It draws on
the current axes.

```python
fig, ax = plt.subplots()
smb.plot_circle(2, (5, 5), ax=ax)
smb.plot_circle(1, (2, 8), ax=ax)     # added to the same plot
```

**From a later cell** (needs a live backend, so `ipympl`): keep `fig` and `ax`, and ask for a redraw.

```python
smb.plot_circle(1, (8, 2), ax=ax)
fig.canvas.draw_idle()
```

The plot in the earlier cell changes; no new figure appears. *Tested* with `ipympl` in VS Code and in
local Jupyter; in JupyterLite the figure is live, and this exact edit has not been checked separately.
If a notebook must also work under `inline`, keep the creating and adding code in one cell.

## 5. `block=`

Plot methods in the toolboxes take `block=`. The contract is:

| `block` | does | use |
|---|---|---|
| `None` (usually the default) | does not call `plt.show` at all; the environment decides | **notebooks: leave it alone** |
| `False` | `plt.show(block=False)`: show, return at once | scripts that keep running |
| `True` | `plt.show(block=True)`: show, wait until the window is closed | scripts that should wait; desktop GUI backends only |

In a notebook with `inline` or `ipympl`, `block` is ignored by the backend, so there is nothing to gain
from setting it. Do not put `block=True` in a notebook: on a desktop GUI backend it hangs the cell
until you close the window, and it does nothing useful on the others. (The toolboxes do not yet apply
this contract consistently; see the issue tracker.)

## 6. The 20-figure limit

Figures made through `pyplot` stay alive until closed. Matplotlib prints a warning when more than 20
are open:

> More than 20 figures have been opened. Figures created through the pyplot interface
> (`matplotlib.pyplot.figure`) are retained until explicitly closed and may consume too much memory.

It is a warning (`figure.max_open_warning`, default 20), not a hard stop. But with `ipympl` every open
figure is a live widget, so the cost is real, and in a notebook it is easy to hit: re-running a cell makes
another figure each time. Keep it under control:

* `plt.close("all")` in the plotting setup cell (section 3.2). Re-running the notebook from the top
  then starts clean. The earlier widgets go blank, which is what you want.
* Close figures you are finished with: `plt.close(fig)`.
* In a loop, a slider callback or an animation, **make one figure outside the loop** and update its
  artists (`line.set_ydata(...)`, then `fig.canvas.draw_idle()`). Never call `plt.subplots()` inside it.
* Do not silence the warning with `rcParams["figure.max_open_warning"] = 0`; it only hides the problem.

Closing figures also resets the figure numbers, so `Figure 14` becoming `Figure 1` after
`plt.close("all")` is expected.

## 7. Pitfalls

* **JupyterLite keeps a stale copy of a notebook.** It stores every notebook the visitor opens in the
  browser, keyed by file name, so a republished site does not replace it, and old outputs and kernel
  state survive. The fix is in the site's root `jupyter-lite.json` (RTB has it, MVTB and bdsim need it,
  tracked in `rvc-ecosystem` #19): `"enableMemoryStorage": true` with `"contentsStorageDrivers"` and
  `"settingsStorageDrivers"` both `["memoryStorageDriver"]`. The cost is that a visitor's own edits are
  lost on reload. Until a site has that, test a changed notebook under a **new file name**.
* **A notebook with no kernel in its metadata** makes JupyterLite show a "select kernel" box. The docs
  workflow writes `{"name": "python", "display_name": "Python (Pyodide)", "language": "python"}`
  into every staged notebook.
* **Safari** cannot run recent Pyodide kernels (no WebAssembly JSPI), which is why the kernel is pinned to
  `jupyterlite-pyodide-kernel==0.6.1`; see `rvc-ecosystem` #19.
* **Clear the outputs before committing.** Saved outputs are cruft in git and a source of confusion.
* **Use `%pip`, not `!pip`,** if a notebook installs anything.
* **Colors:** use a palette that is safe for color-vision deficiency (see `AGENTS.md`); avoid red and green
  as the only contrast.

## 8. A checklist for a new notebook

1. Title cell, then the generated bootstrap cell, then the plotting setup cell (`%matplotlib ipympl`,
   `plt.close("all")`).
2. Every new plot starts with `fig, ax = plt.subplots()`; no bare `plt.figure()`.
3. Additions to an earlier plot use `fig` and `ax` and `fig.canvas.draw_idle()`.
4. No `block=` in notebooks; no `%matplotlib notebook`; no `plt.show()` just to display a figure.
5. Restart the kernel, run all cells, and check that `plt.get_fignums()` has the number of figures
   you expect (an extra one is an empty figure from a bare `plt.figure()`).
6. Run it again in the *other* environment: the same file on the desktop, then in a local JupyterLite
   build (`jupyter lite build`, serve the output folder, open it under a new file name).
7. Outputs cleared; `sync_bootstrap.py --check` passes.

## 9. What is and is not known

*Tested while writing this page:* sections 2 and 4 in VS Code, local Jupyter and a local JupyterLite
site (in a Chromium-based browser); the figure-limit warning; the staleness setting.

*Not tested, so treat with care:* the later-cell edit (job 2) and `block=` in JupyterLite; Safari and Firefox with JupyterLite; Colab with MVTB or bdsim; `block=False` and `%matplotlib macosx` inside a notebook on the desktop windows (a script was checked on
`macosx`, `tkagg` and `qtagg` with PySide6: `plt.show()` waits until every window is closed, then returns); whether MVTB's own site works unchanged
with `ipympl` instead of `inline`.

*Known gap:* a bare `plt.figure()` followed by a toolbox plot leaves an empty figure. A fix for
spatialmath's `axes_logic` exists as a branch of the fork (`fix/axes-logic-reuse-empty-figure`, with
tests), proposed upstream as rai-opensource/spatialmath-python#265 on 2026-10-17, and pending RAI's
merge and a release after that.
Nothing here depends on it.
