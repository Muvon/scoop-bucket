#!/usr/bin/env python3
"""Write Scoop manifests from the latest GitHub release of each tool.

    update.py OWNER/REPO...   create or update bucket/<repo>.json
    update.py                 refresh every manifest already in bucket/

A release qualifies when it ships <repo>-<tag>-<target>.zip archives with
<repo>.exe at the root. Hashes come from the SHA256 digest GitHub records for
each asset, so nothing is downloaded. Fields not owned by this script (such
as "suggest") are kept as they are.
"""

import json
import os
import sys
import urllib.request
from pathlib import Path

BUCKET = Path(__file__).resolve().parent.parent / "bucket"
ARCHITECTURES = {"64bit": "x86_64-pc-windows-msvc", "arm64": "aarch64-pc-windows-msvc"}


def github(path):
	request = urllib.request.Request(f"https://api.github.com/{path}")
	request.add_header("Accept", "application/vnd.github+json")
	token = os.environ.get("GITHUB_TOKEN")
	if token:
		request.add_header("Authorization", f"Bearer {token}")
	with urllib.request.urlopen(request) as response:
		return json.load(response)


def update(repo):
	name = repo.split("/")[1]
	info = github(f"repos/{repo}")
	release = github(f"repos/{repo}/releases/latest")
	tag = release["tag_name"]
	version = tag.removeprefix("v")
	assets = {asset["name"]: asset for asset in release["assets"]}

	architecture, autoupdate = {}, {}
	for arch, target in ARCHITECTURES.items():
		asset = assets.get(f"{name}-{tag}-{target}.zip")
		if asset is None:
			continue
		digest = asset.get("digest") or ""
		if not digest.startswith("sha256:"):
			sys.exit(f"{repo} {tag}: {asset['name']} has no sha256 digest")
		url = asset["browser_download_url"]
		architecture[arch] = {"url": url, "hash": digest.removeprefix("sha256:")}
		autoupdate[arch] = {"url": url.replace(tag, tag.replace(version, "$version"))}
	if not architecture:
		sys.exit(f"{repo} {tag}: no Windows zip named {name}-{tag}-<target>.zip")

	path = BUCKET / f"{name}.json"
	manifest = {
		"version": version,
		"description": info["description"],
		"homepage": info["homepage"] or info["html_url"],
		"license": info["license"]["spdx_id"],
		"architecture": architecture,
		"bin": f"{name}.exe",
		"checkver": {"github": info["html_url"]},
		"autoupdate": {"architecture": autoupdate},
	}
	if path.exists():
		for key, value in json.loads(path.read_text()).items():
			manifest.setdefault(key, value)
	text = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
	if path.exists() and path.read_text() == text:
		print(f"{name}: {version} (unchanged)")
		return
	BUCKET.mkdir(exist_ok=True)
	path.write_text(text)
	print(f"{name}: {version}")


def main():
	repos = sys.argv[1:]
	if not repos:
		repos = [
			json.loads(path.read_text())["checkver"]["github"].removeprefix("https://github.com/")
			for path in sorted(BUCKET.glob("*.json"))
		]
	for repo in repos:
		update(repo)


if __name__ == "__main__":
	main()
