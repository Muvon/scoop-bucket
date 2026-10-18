#!/usr/bin/env python3
"""Write Scoop manifests from the latest GitHub release of each tool.

    update.py OWNER/REPO   create or update bucket/<repo>.json
    update.py              refresh every manifest already in bucket/

A release qualifies when it ships <repo>-<tag>-<target>.zip archives with
<repo>.exe at the root. Hashes come from the SHA256 digest GitHub records for
each asset, so nothing is downloaded. Extra fields in an existing manifest
(such as "suggest") are kept.
"""

import json
import os
import sys
import urllib.request
from pathlib import Path

BUCKET = Path(__file__).resolve().parent.parent / "bucket"
GITHUB = "https://github.com/"

# Scoop architecture name -> Rust target in the archive name
TARGETS = {
    "64bit": "x86_64-pc-windows-msvc",
    "arm64": "aarch64-pc-windows-msvc",
}


def github_api(path):
    request = urllib.request.Request(f"https://api.github.com/{path}")
    request.add_header("Accept", "application/vnd.github+json")
    if token := os.environ.get("GITHUB_TOKEN"):
        request.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(request) as response:
        return json.load(response)


def windows_downloads(repo, name, release):
    """Return {arch: {"url", "hash"}} for each Windows zip in the release."""
    tag = release["tag_name"]
    assets = {asset["name"]: asset for asset in release["assets"]}
    downloads = {}

    for arch, target in TARGETS.items():
        asset = assets.get(f"{name}-{tag}-{target}.zip")
        if asset is None:
            continue
        digest = asset.get("digest") or ""
        if not digest.startswith("sha256:"):
            sys.exit(f"{repo} {tag}: {asset['name']} has no sha256 digest")
        downloads[arch] = {
            "url": asset["browser_download_url"],
            "hash": digest.removeprefix("sha256:"),
        }

    if not downloads:
        sys.exit(f"{repo} {tag}: no Windows zip named {name}-{tag}-<target>.zip")
    return downloads


def update(repo):
    name = repo.split("/")[1]
    info = github_api(f"repos/{repo}")
    release = github_api(f"repos/{repo}/releases/latest")
    tag = release["tag_name"]
    version = tag.removeprefix("v")
    downloads = windows_downloads(repo, name, release)

    # Same URLs with the version as a placeholder, for Scoop's own updater
    version_in_tag = tag.replace(version, "$version")
    autoupdate = {arch: {"url": d["url"].replace(tag, version_in_tag)} for arch, d in downloads.items()}

    manifest = {
        "version": version,
        "description": info["description"],
        "homepage": info["homepage"] or info["html_url"],
        "license": info["license"]["spdx_id"],
        "architecture": downloads,
        "bin": f"{name}.exe",
        "checkver": {"github": info["html_url"]},
        "autoupdate": {"architecture": autoupdate},
    }

    path = BUCKET / f"{name}.json"
    old_text = path.read_text() if path.exists() else ""
    if old_text:
        for key, value in json.loads(old_text).items():
            manifest.setdefault(key, value)

    new_text = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    if new_text == old_text:
        print(f"{name}: {version} (unchanged)")
        return
    BUCKET.mkdir(exist_ok=True)
    path.write_text(new_text)
    print(f"{name}: {version}")


def bucket_repos():
    """OWNER/REPO of every manifest already in the bucket."""
    return [
        json.loads(path.read_text())["checkver"]["github"].removeprefix(GITHUB)
        for path in sorted(BUCKET.glob("*.json"))
    ]


def main():
    # The workflow passes an empty argument when no repository is given
    repos = [repo for repo in sys.argv[1:] if repo] or bucket_repos()
    for repo in repos:
        update(repo)


if __name__ == "__main__":
    main()
