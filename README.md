# Muvon Scoop bucket

[Scoop](https://scoop.sh) manifests for Muvon tools on Windows (x64 and ARM64).

```powershell
scoop bucket add muvon https://github.com/Muvon/scoop-bucket
scoop install muvon/octomind
```

Every app is listed in [`bucket/`](bucket). Update with `scoop update` and `scoop update <app>`.

## How manifests are updated

Manifests are generated, not edited by hand. When a Muvon tool publishes a release with Windows zips, the shared
[release workflow](https://github.com/Muvon/ci-workflow) dispatches `release` to this repository, and
[`update.yml`](.github/workflows/update.yml) runs [`bin/update.py`](bin/update.py) for that tool. The script reads the
latest GitHub release and writes `bucket/<tool>.json`, taking each hash from the SHA256 digest GitHub records for the
asset. A schedule refreshes every manifest every 6 hours in case a dispatch was missed. [`ci.yml`](.github/workflows/ci.yml)
installs every manifest on Windows and runs it.

To add or refresh a tool by hand:

```bash
GITHUB_TOKEN=$(gh auth token) python3 bin/update.py Muvon/<tool>
```
