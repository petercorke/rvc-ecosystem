import os
import re
import urllib.request
import json
from ansitable import ANSITable, Column

# Packages listed in the text tables
PACKAGES = [
    # Core / "Big 3"
    {"name": "robotics-toolbox-python", "pypi": "roboticstoolbox-python", "repo": "petercorke/robotics-toolbox-python", "codacy_name": "robotics-toolbox-python"},
    {"name": "machinevision-toolbox-python", "pypi": "machinevision-toolbox-python", "repo": "petercorke/machinevision-toolbox-python", "codacy_name": "machinevision-toolbox-python"},
    {"name": "bdsim", "pypi": "bdsim", "repo": "petercorke/bdsim", "codacy_name": "bdsim"},
    # Backing / Foundation packages
    {"name": "spatialmath-python", "pypi": "spatialmath-python", "repo": "rai-opensource/spatialmath-python", "codacy_name": "spatialmath-python"},
    {"name": "swift", "pypi": "swift-sim", "repo": "jhavl/swift", "codacy_name": "swift"},
    {"name": "spatialgeometry", "pypi": "spatialgeometry", "repo": "jhavl/spatialgeometry", "codacy_name": "spatialgeometry"},
    {"name": "ansitable", "pypi": "ansitable", "repo": "petercorke/ansitable", "codacy_name": "ansitable"},
    {"name": "pgraph-python", "pypi": "pgraph-python", "repo": "petercorke/pgraph-python", "codacy_name": "pgraph-python"},
    {"name": "sphinx-pyrunblock", "pypi": "sphinx-pyrunblock", "repo": "petercorke/sphinx-pyrunblock", "codacy_name": "sphinx-pyrunblock"},
    {"name": "arduIO", "pypi": "arduIO", "repo": "petercorke/arduIO", "codacy_name": "arduIO"},
    {"name": "rvc-notation", "pypi": None, "repo": "petercorke/rvc-notation", "codacy_name": "rvc-notation"},
    {"name": "RVC3-python", "pypi": "rvc3python", "repo": "petercorke/RVC3-python", "codacy_name": "RVC3-python"},
]

def http_get_json(url, headers=None):
    """Helper to perform HTTP GET requests returning JSON."""
    try:
        req = urllib.request.Request(url, headers=headers or {"User-Agent": "RVC-Ecosystem-Script"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None

def fetch_monthly_downloads(pypi_name):
    """Fetch last month's download count from PyPI Stats API."""
    if not pypi_name:
        return ""
    url = f"https://pypistats.org/api/packages/{pypi_name.lower()}/recent"
    data = http_get_json(url)
    if data and "data" in data and "last_month" in data["data"]:
        downloads = data["data"]["last_month"]
        return f"{downloads:,}"
    return ""

def fetch_code_coverage(repo_slug):
    """Fetch code coverage percentage from Codecov API."""
    url = f"https://codecov.io/api/v2/github/{repo_slug}"
    data = http_get_json(url)
    if data and "totals" in data and "coverage" in data["totals"]:
        cov = data["totals"]["coverage"]
        return f"{cov:.1f}%"
    return ""

def fetch_kloc(repo_slug):
    """Fetch lines of code estimation using GitHub language bytes API."""
    url = f"https://api.github.com/repos/{repo_slug}/languages"
    # Optional GitHub token to prevent rate-limiting
    token = os.environ.get("GITHUB_TOKEN")
    headers = {"User-Agent": "RVC-Ecosystem-Script"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
        
    data = http_get_json(url, headers=headers)
    if data and isinstance(data, dict):
        total_bytes = sum(data.values())
        # Roughly estimate 1 LOC ≈ 35 bytes for code
        estimated_loc = total_bytes / 35.0
        kloc = estimated_loc / 1000.0
        return f"{kloc:.1f}" if kloc > 0 else ""
    return ""

def fetch_codacy_quality(repo_slug):
    """Fetch Codacy Quality grade badge/score if accessible."""
    # Codacy public badge endpoint check
    url = f"https://api.codacy.com/project/badge/grade/{repo_slug}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "RVC-Ecosystem-Script"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            content = resp.read().decode("utf-8")
            # Extract SVG grade letter (e.g. A, B, C)
            match = re.search(r'text-anchor="middle">([A-F])</text>', content)
            if match:
                return match.group(1)
    except Exception:
        pass
    return ""

def main():
    table = ANSITable(
        Column("Package Name", headalign="<", colalign="<"),
        Column("Coverage", headalign=">", colalign=">"),
        Column("KLOC", headalign=">", colalign=">"),
        Column("Codacy", headalign="^", colalign="^"),
        Column("Monthly Downloads", headalign=">", colalign=">"),
        border="thin"
    )

    print("Fetching package metrics from PyPI, GitHub, Codecov, and Codacy...\n")

    kloc_sum = 0
    downloads_sum = 0
    for pkg in PACKAGES:
        pkg_name = pkg["name"]
        repo = pkg["repo"]
        pypi = pkg["pypi"]

        coverage = fetch_code_coverage(repo)
        kloc = fetch_kloc(repo)
        codacy = fetch_codacy_quality(repo)
        downloads = fetch_monthly_downloads(pypi)

        # Add to sums for total row
        if kloc:
            kloc_sum += float(kloc)
        if downloads:
            downloads_sum += int(downloads.replace(",", ""))

        table.row(
            pkg_name,
            coverage,
            kloc,
            codacy,
            downloads
        )

    table.row("Total", "", f"{kloc_sum:.1f}", "", f"{downloads_sum:,}")
    table.print()

if __name__ == "__main__":
    main()