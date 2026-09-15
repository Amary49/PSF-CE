#!/usr/bin/env python
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def run(args, cwd=None):
    cp = subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=False)
    if cp.returncode != 0:
        raise RuntimeError(f"command failed: {' '.join(args)}\n{cp.stdout}\n{cp.stderr}")
    return cp.stdout.strip()


def tree_sha256(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file() and ".git" not in p.parts):
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description="Clone author repositories at audited immutable commits.")
    parser.add_argument("--config", default="configs/official_repositories.json")
    parser.add_argument("--dest", default="vendor/official")
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    destination = Path(args.dest)
    destination.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for name, item in config.items():
        target = destination / name
        if not target.exists():
            run(["git", "clone", "--no-checkout", item["url"], str(target)])
        if not (target / ".git").exists():
            raise RuntimeError(f"{name}: destination exists but is not a Git checkout: {target}")
        origin = run(["git", "remote", "get-url", "origin"], cwd=target)
        if origin.rstrip("/") != item["url"].rstrip("/"):
            raise RuntimeError(f"{name}: origin mismatch: {origin}")
        actual = run(["git", "rev-parse", "HEAD"], cwd=target)
        if actual.lower() != item["commit"].lower():
            run(["git", "fetch", "--depth", "1", "origin", item["commit"]], cwd=target)
            run(["git", "checkout", "--detach", item["commit"]], cwd=target)
            actual = run(["git", "rev-parse", "HEAD"], cwd=target)
        if actual.lower() != item["commit"].lower():
            raise RuntimeError(f"{name}: commit mismatch after checkout")
        license_files = [
            p.relative_to(target).as_posix()
            for p in target.iterdir()
            if p.is_file() and p.name.lower().startswith(("license", "copying"))
        ]
        manifest[name] = {
            **item,
            "actual_commit": actual,
            "origin": origin,
            "path": str(target.resolve()),
            "tree_sha256": tree_sha256(target),
            "license_files": license_files,
            "redistributed_in_v4_zip": False,
        }
        print(f"{name}: {actual} ({item['status']})")
    out = destination / "PROVENANCE.json"
    out.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
