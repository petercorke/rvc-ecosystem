# RVC Ecosystem — Agent Instructions

> **AI agents (Claude, Copilot, Cursor, Gemini, Codex) working in any RVC ecosystem repo
> must read this file.** It contains the invariants and working conventions that apply
> across the ecosystem — the things that must not be violated without explicit discussion
> with Peter Corke (or, for third-party-owned repos, their owner). Human-facing project
> overview and aspirational standards are in [README.md](./README.md). **Where the two
> disagree, this file wins** — README's overlapping sections describe the same ground for
> human readers and may lag behind a change made here, or state a target neither file has
> caught up to yet.

---

## Glossary

| Shorthand | Full name / meaning |
| :--- | :--- |
| RTB | `robotics-toolbox-python` |
| MVTB | `machinevision-toolbox-python` |
| SMTB | `spatialmath-python` |
| SG | `spatialgeometry` |
| bdsim | `bdsim` (unchanged) |
| Swift | `swift` (`jhavl/swift`) |
| "big 3" | RTB, MVTB, bdsim |
| GH | GitHub |
| JL | JupyterLite |
| RAI | RAI Institute — owns SMTB; GitHub org `rai-opensource` |

---

## 1. Repo Ownership & Contribution Rules

**This is the most critical section. Getting it wrong affects other people's repos.**

| Repo | Owner | Contribution model |
| :--- | :--- | :--- |
| RTB, MVTB, bdsim, ansitable, pgraph-python, sphinx-pyrunblock, arduIO, rvc-notation, RVC3-python | Peter Corke (`petercorke`) | Branch → PR; direct push to `main` at Peter's discretion |
| `spatialmath-python` | RAI Institute (`rai-opensource`) | **PR only** — not Peter's call to merge or push unilaterally |
| `swift`, `spatialgeometry` | Jesse Haviland (`jhavl`) | **PR only** — collaborator push access exists on these but must never be used. Push branches to your own fork, never to `origin` (the upstream `jhavl/*` repo) |

Never push directly to a third-party-owned repo, even where technical access exists. If you're
working from a local clone that has both a `fork` (yours) and `origin` (upstream) remote,
double-check which one a `git push` is about to hit — pushing a branch to the wrong remote
here isn't just a style problem, it puts your work-in-progress on someone else's repo without
their knowledge or consent.

The default branch is `main` — not `master` — in all Peter-governed repos. (`ansitable` and
`rvc-notation` are pending migration; third-party repos follow their own owners' conventions.)

---

## 2. Mathematical Invariants

All code must respect these; do not change them without explicit discussion.

- **Coordinate systems:** right-handed throughout (2D and 3D)
- **Rotation matrices:** $3\times3$ for $SO(3)$, $4\times4$ homogeneous for $SE(3)$
- **Quaternions:** Hamilton convention; scalar component stored/accessed via `UnitQuaternion`/`Quaternion` classes in `spatialmath`
- **Angles:** radians internally, always. Parameters/functions accepting degrees must say so explicitly (e.g. `unit='deg'`)
- **Array broadcasting:** `SpatialVector` and transform objects support vectorised sequences of poses, use
this capability rather than use lists/tuples of pose objects.

---

## 3. Package Dependency Boundaries

Verified against each repo's `pyproject.toml` (2026-08-13) — this is the real graph, not an
idealised one:

```
SMTB (spatialmath-python)        — zero internal dependencies; bottom of the stack
pgraph-python, ansitable         — standalone utility packages
SG (spatialgeometry)             — depends on SMTB only
Swift                            — depends on SG
RTB (robotics-toolbox-python)    — depends on SMTB, SG (required), pgraph-python, ansitable;
                                    Swift is an optional extra (`pip install roboticstoolbox-python[swift]`)
MVTB (machinevision-toolbox-python) — depends on SMTB, pgraph-python, ansitable
bdsim                             — depends on SMTB, ansitable; integrates with RTB *optionally*
                                    (notebook helpers, examples) — not a hard package dependency
```

Rules:
- `spatialmath-python` has zero imports from RTB, MVTB, or bdsim
- `robotics-toolbox-python` uses `spatialmath` classes (`SE3`, `SO3`, `UnitQuaternion`, etc.) — do **not** re-implement pose mathematics inside RTB
- Circular dependencies between any of the above are not permitted

---

## 4. Git and PR Workflow

- **One branch per change set.** Never let unrelated concerns (a feature, a refactor, a bug
  fix, a docs tweak) land tangled together in one branch or one uncommitted working tree —
  no size exception, including for small housekeeping edits.
- **Always confirm a new branch with the person you're working with before creating it** —
  propose a name and wait, rather than deciding unprompted and reporting the name afterward.
- **Never push to a third-party-owned repo's `origin`.** Push to your own fork; open the PR
  from there. See §1.
- **Confirm each merge or PR individually** — approval for one doesn't carry forward to the
  next, even mid-batch.
- **Closing an issue or PR from an external contributor always gets a friendly comment
  first** — thank them, explain the resolution — never a silent or purely technical close.
- Before starting work on a file, check whether one of your own other open, unmerged
  branches already touches it — merge/rebase that in first rather than duplicating or
  fragmenting the work.
- If the person you're working with may also be actively working in the same clone, do your
  branch work in an isolated checkout (e.g. a git worktree) rather than switching the shared
  working tree's branch — don't fight over which branch is checked out.

---

## 5. Code Standards

Applies to all Peter-governed repos. For all Peter's work on third-party repos (SMTB, Swift, SG), in the absence of explicit coding standards in those repos, these standards are considered best practice;  propose changes via PR, not by assumption.

### Type hints
- Modern Python 3.10+ syntax only: `X | Y`, `X | None`, `list[X]`, `dict[K, V]`
- Do **not** use `Union`, `Optional`, `List`, `Dict` from `typing` — remove them from imports when touching a file
- Keep `Any`, `Callable`, `Literal`, `TypeVar`, `TYPE_CHECKING` as needed
- All public methods and functions must be type-hinted

### Docstrings
- reST style: `:param name:`, `:returns:` — not NumPy-style section headers
- every docstring has a one line summary, followed by `:param:` and `:returns:` block, followed by extended description and notes
- as appropriate every docstring has `:seealso:` cross links as the last line
- docstring references to classes and methods should use `:meth:` and `:class:` roles
- `:type:` / `:rtype:` only when shape information adds value beyond the signature annotation
  (e.g. `:type q: ndarray(6,n)`) — the annotation itself covers everything else
- Math docstrings use `r"""..."""` for LaTeX rendering

### Sphinx documentation pages
- Every Sphinx-built doc page's footer: left side reads exactly
  `Copyright © 20xx-present, Peter Corke: built YYYY-MM-DD` (`YYYY-MM-DD` is the doc build
  date, not a fixed string — driven by `html_last_updated_fmt = "%Y-%m-%d"`); right side is
  a smaller-font `GitHub` link back to the repo.
- Confirmed and implemented in bdsim (2026-08-16) — `docs/source/_templates/footer.html`
  (builds the exact left-side text instead of the `sphinx_rtd_theme` default, which reads
  "© Copyright ... Last updated on DD-Mon-YYYY" and is not the desired format) plus
  `docs/source/_static/custom.css` (flexbox on the footer's `contentinfo` div so the GitHub
  link actually renders on the right — a plain `<a>` tag with no CSS just falls inline below
  the copyright line). Copy that file pair as the reference implementation for other repos
  on `sphinx_rtd_theme`; adjust the repo name/URL in `footer.html`.

### Language
- Australian/British spelling in docstrings, comments, commit messages, and user-facing text
  — e.g. neighbour, centre, program not programme
- `color`, not `colour` — always, everywhere: prose, docstrings, comments, *and* code
  identifiers (method/parameter/variable names). This is a firm personal spelling choice, not
  a narrow carve-out for matching library kwargs like matplotlib's `color=`. If `colour`
  appears anywhere in this codebase, it's a stray error, not intentional — fix it on sight.
- Inconsistent on -ise/-ize by preference — -ize is used more often than not; don't "fix" one
  spelling to match the other

### Color choices
- Peter has red-green color-vision deficiency (deuteranomaly) — any default color palette (matplotlib
  cycles, `ansitable` output, Swift scene/plot colors) must be chosen or checked for
  deuteranomaly safety, not just aesthetically distinct. Avoid relying on red/green alone as
  a contrast pair; prefer palettes like `viridis`/`cividis` or a verified CVD-safe
  qualitative set over matplotlib's default `tab10`.

### Deprecation
- A deprecated function issues a `DeprecationWarning` and **returns the expected result**
  (does not raise) — see e.g. `DHRobot.py` in RTB for the pattern
- A deprecated parameter issues a warning, maps to the new parameter name, and returns the
  expected result
- Docstrings use `.. deprecated:: X.Y.Z` with the version it was first deprecated

### Compiled extensions
- **Every compiled extension (C/C++/Cython, nanobind/pybind11/raw C-API, whatever) needs a
  complete, tested pure-Python fallback behind a facade module** — a `try: from .<ext> import
  ... / except ImportError: <pure-Python equivalents>` pattern, with a module-level
  `_C_AVAILABLE` flag so tests can assert on which path actually ran (RTB's `fknm.py`/`frne.py`,
  swift's inline pattern in `Swift.py`). This is standing policy, not a one-off, adopted
  ecosystem-wide 2026-08-25 alongside RTB's pure-Python-wheel change (see §7).
- "Tested" means real cross-validation against the compiled path (not just "the fallback exists
  and doesn't crash") — RTB's `tests/test_fknm_fallback.py` runs each function via both paths
  and checks agreement, gated `@unittest.skipUnless(_C_AVAILABLE, ...)` so a missing extension
  shows as an explicit skip rather than a silent no-op comparison.
- Why this matters beyond Pyodide: it's what makes the pure-Python-wheel strategy in §7 possible
  at all — without complete fallback coverage, that option doesn't exist for a given package.
  It also buys general robustness (a broken toolchain, an unsupported platform, or a build
  failure degrades gracefully instead of making the package uninstallable).
- Not yet audited across every repo with compiled extensions — RTB and swift are confirmed to
  already follow this pattern; SG's `scene` module has a fallback (`scene.py`) but check it's
  actually cross-validated the same rigorous way before assuming parity.

### Build tooling
Target state — check each repo's actual `pyproject.toml` before assuming it's already there:
- Package layout: `src/<package_name>/` — already universal across the ecosystem
- Build backend: **Hatch** (`hatchling`) for pure-Python packages. RTB and SG compile
  `nanobind` C++ extensions and use `scikit-build-core` instead — this is a permanent,
  justified exception, not a pending migration
- Linting/formatting: **`ruff`** is the target, superseding `black`. Only MVTB has actually
  migrated so far — bdsim, SG, Swift, ansitable, and pgraph-python are still on `black`;
  treat this as real outstanding work, not done
- Code quality gate: where Codacy is wired in (currently MVTB, ansitable — badge + automated
  PR comments), a grade of **A** is the aspiration. There is a real, non-trivial backlog
  behind the current grade (tracked as `tech-debt`-labelled issues, e.g. MVTB's Codacy
  findings and its "mypy not in CI" entry). The means of closing that gap — adopting `mypy`,
  fixing specific lint findings, or something else — is a per-repo call to make via its own
  tech-debt process, not centrally mandated here

---

## 6. Tech-Debt Tracking

**Standard going forward: GitHub Issues labelled `tech-debt`.** Log new findings there, not
in a file.

`tech-debt.md` at repo root is the legacy mechanism — it caused real problems (independent
PRs each appending near the tail of the same file produced merge conflicts unrelated to what
those PRs actually changed). RTB and MVTB have already migrated. `ansitable` and
`sphinx-pyrunblock` still carry a `tech-debt.md` file; that's leftover practice, not a
deliberate exception — migrating them is on the list, just not urgent. Don't create a new
`tech-debt.md` in any repo.

---

## 7. Releases and CI

- `release-please` is the target for changelog/release automation on the "big 3" — but it
  has hit real problems in practice, not a solved/simple aspiration. See
  [machinevision-toolbox-python#74](https://github.com/petercorke/machinevision-toolbox-python/pull/74)
  before assuming it "just works."
- Before any PyPI/production publish: build the actual artifact from a clean checkout (not
  the dirty working directory) and verify it in a throwaway venv; separately verify the
  release workflow file itself at the exact tag/branch being released from, diffed against
  `main`'s current version.
- **JupyterLite/Pyodide wheel for a compiled-extension package (RTB, SG): prefer a genuine
  pure-Python (`py3-none-any`) wheel over cross-compiling a real wasm32 binary**, whenever the
  package already has complete, tested pure-Python fallbacks for its compiled functionality —
  RTB adopted this 2026-08-25 (`RTB_PURE_WHEEL=1` + a scikit-build-core `wheel.platlib=false`
  override), eliminating both the Safari/JSPI wasm-runtime constraint and wasm-ABI tag matching
  for the package's own wheel entirely, not just working around them. See the
  `toolbox-maintainer` skill's JupyterLite section for the full mechanism and rationale before
  reaching for cibuildwheel's Pyodide platform on a repo that has this option available.
