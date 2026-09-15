#!/usr/bin/env python
from __future__ import annotations

import argparse
from importlib import metadata
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys


PACKAGES = ["numpy", "scipy", "scikit-learn", "pandas", "matplotlib", "threadpoolctl"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repos", default="vendor/official/PROVENANCE.json")
    parser.add_argument("--output", default="results/environment.json")
    args = parser.parse_args()
    matlab = os.environ.get("MATLAB_EXE", "") or shutil.which("matlab") or ""
    matlab_version = ""
    matlab_error = ""
    if matlab:
        cp = subprocess.run([matlab, "-batch", "disp(version)"], text=True, capture_output=True, timeout=90, check=False)
        if cp.returncode == 0:
            matlab_version = cp.stdout.strip().splitlines()[-1]
        else:
            matlab_error = (cp.stderr or cp.stdout)[-2000:]
    packages = {}
    for name in PACKAGES:
        try:
            packages[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            packages[name] = None
    repos = {}
    if Path(args.repos).exists():
        repos = json.loads(Path(args.repos).read_text(encoding="utf-8"))
    payload = {
        "schema": "psfce-v4-environment-v1",
        "platform": platform.platform(),
        "machine": platform.machine(),
        "python": sys.version,
        "python_executable": sys.executable,
        "packages": packages,
        "matlab_executable": matlab,
        "matlab_version": matlab_version,
        "matlab_error": matlab_error,
        "official_repositories": repos,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
