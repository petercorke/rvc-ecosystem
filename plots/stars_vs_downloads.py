"""Scatter plot of GitHub stars vs PyPI downloads (last 30 days), plus a
"dependency multiplier" table.

The multiplier is a package's monthly downloads divided by the summed monthly
downloads of the packages that depend on it directly.  Near 1 means its
downloads are explained by its dependents; well above 1 means direct use.
Dependents overlap (installing RTB also installs SMTB), so it is only a rough
indicator.

Usage: python plots/stars_vs_downloads.py   (writes next to this script)
"""

import json
import urllib.request
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

# nickname: (github repo, pypi name, group)
PACKAGES: dict[str, tuple[str, str, str]] = {
    "RTB": ("petercorke/robotics-toolbox-python", "roboticstoolbox-python", "big3"),
    "MVTB": ("petercorke/machinevision-toolbox-python", "machinevision-toolbox-python", "big3"),
    "bdsim": ("petercorke/bdsim", "bdsim", "big3"),
    "SMTB": ("rai-opensource/spatialmath-python", "spatialmath-python", "other"),
    "ansitable": ("petercorke/ansitable", "ansitable", "other"),
    "pgraph": ("petercorke/pgraph-python", "pgraph-python", "other"),
}

# direct dependencies, from each repo's pyproject.toml (checked 2026-10-15)
DEPENDENTS: dict[str, list[str]] = {
    "ansitable": ["SMTB", "RTB", "MVTB", "bdsim"],
    "pgraph": ["RTB", "MVTB"],
}

COLORS = {"big3": "#E69F00", "other": "#0072B2"}  # Okabe-Ito, color-blind safe


def get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "rvc-ecosystem"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode())


def main() -> None:
    here = Path(__file__).parent
    stars, dl = {}, {}
    for name, (repo, pypi, _) in PACKAGES.items():
        stars[name] = get_json(f"https://api.github.com/repos/{repo}")["stargazers_count"]
        dl[name] = get_json(f"https://pypistats.org/api/packages/{pypi}/recent")["data"]["last_month"]

    fig, ax = plt.subplots(figsize=(7, 5), dpi=150)
    for name, (_, _, group) in PACKAGES.items():
        ax.scatter(stars[name], dl[name], s=90, color=COLORS[group], zorder=3)
        ax.annotate(name, (stars[name], dl[name]), xytext=(8, 6), textcoords="offset points")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("GitHub stars")
    ax.set_ylabel("PyPI downloads, last 30 days")
    ax.set_title("Stars vs monthly downloads")
    ax.grid(True, which="both", alpha=0.25)
    fig.tight_layout()
    fig.savefig(here / "stars_vs_downloads.png")

    lines = ["| Package | Stars | Downloads/month | Direct dependents | Dependents' downloads | Multiplier |",
             "|---|---:|---:|---|---:|---:|"]
    for name in PACKAGES:
        deps = DEPENDENTS.get(name)
        if deps:
            total = sum(dl[d] for d in deps)
            extra = f"{', '.join(deps)} | {total:,} | {dl[name] / total:.2f}"
        else:
            extra = "– | – | –"
        lines.append(f"| {name} | {stars[name]:,} | {dl[name]:,} | {extra} |")
    (here / "stars_vs_downloads.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
