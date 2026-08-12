# RVC Ecosystem — Agent Instructions

> **AI agents (Claude, Copilot, Cursor, Gemini, Codex) working in any RVC ecosystem repo
> must read this file.** Full development standards and aspirational targets are in
> [README.md](./README.md); this file contains the invariants that must not be
> violated without explicit discussion with Peter Corke.

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
| `spatialmath-python` | RAI Institute (`rai-opensource`) | **PR only** — Peter does not merge or push unilaterally |
| `swift`, `spatialgeometry` | Jesse Haviland (`jhavl`) | **PR only** — Peter has collaborator push rights but never uses them |

Never push directly to a third-party-owned repo, even where technical access exists.

The default branch is `main` — not `master` — in all Peter-governed repos. (`ansitable` and
`rvc-notation` are pending migration; third-party repos follow their own owners' conventions.)

---

## 2. Mathematical Invariants

All code must respect these; do not change them without explicit discussion.

- **Coordinate systems:** right-handed throughout (2D and 3D)
- **Rotation matrices:** $3\times3$ for $SO(3)$, $4\times4$ homogeneous for $SE(3)$
- **Quaternions:** Hamilton convention; scalar component stored/accessed via `UnitQuaternion`/`Quaternion` classes in `spatialmath`
- **Angles:** radians internally, always. Parameters/functions accepting degrees must say so explicitly (e.g. `unit='deg'`)
- **Array broadcasting:** `SpatialVector` and transform objects support vectorised sequences of poses; preserve dimension safety — never silently collapse a pose sequence to a single value

---

## 3. Package Dependency Boundaries

Circular dependencies between these packages are not permitted:

```
bdsim → RTB → SMTB   (SMTB has no upward dependencies)
MVTB  → SMTB
```

- `spatialmath-python` has zero imports from RTB, MVTB, or bdsim
- `robotics-toolbox-python` uses `spatialmath` classes (`SE3`, `SO3`, `UnitQuaternion`, etc.) — do **not** re-implement pose mathematics inside RTB
- `bdsim` blocks that wrap robotics capabilities import from RTB or SMTB

---

## 4. Code Standards

Applies to all Peter-governed repos. Third-party repos (SMTB, swift, SG) follow their own owners' standards; propose changes via PR, not by assumption.

### Type hints
- Modern Python 3.10+ syntax only: `X | Y`, `X | None`, `list[X]`, `dict[K, V]`
- Do **not** use `Union`, `Optional`, `List`, `Dict` from `typing` — remove them from imports when touching a file
- Keep `Any`, `Callable`, `Literal`, `TypeVar`, `TYPE_CHECKING` as needed
- All public methods and functions must be type-hinted

### Docstrings
- reST style: `:param name:`, `:returns:` — not NumPy-style section headers
- `:type:` / `:rtype:` only when shape information adds value beyond the annotation (e.g. `:type q: ndarray(6,n)`)
- Math docstrings use `r"""..."""` for LaTeX

### Deprecation
- A deprecated function issues a `DeprecationWarning` and **returns the expected result** (does not raise)
- A deprecated parameter issues a warning, maps to the new parameter name, and returns the expected result
- Docstrings use `.. deprecated:: X.Y.Z` with the version it was first deprecated
- Warning messages include the version tag; deprecations appear in the CHANGELOG

### Build tooling
- Build backend: **Hatch** (`hatchling`) via `pyproject.toml`
- Package layout: `src/<package_name>/`
- Linting/formatting: **`ruff`** — supersedes `black`; remove `black` from any legacy config
- Type checking: `mypy`
- C++ extensions: `nanobind` + `scikit-build-core`

---

## 5. Tech-Debt Tracking

All repos track tech debt as **GitHub Issues labelled `tech-debt`**. There is no `tech-debt.md` file in any repo. Do not create one.
