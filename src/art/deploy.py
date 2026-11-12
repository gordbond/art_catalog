"""Publish the built site (derived images only) to the gh-pages branch of origin."""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

BRANCH = "gh-pages"


class DeployError(Exception):
    pass


def _git(cwd: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if result.returncode:
        raise DeployError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def deploy(root: Path, site: Path) -> str:
    """Force-push the contents of `site` as a fresh single-commit gh-pages branch. Returns the remote URL."""
    if not (site / "index.html").exists():
        raise DeployError(f"{site} has no index.html; run `art build` first")
    remote = _git(root, "remote", "get-url", "origin")
    identity = [
        "-c", f"user.name={_git(root, 'config', 'user.name')}",
        "-c", f"user.email={_git(root, 'config', 'user.email')}",
    ]
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "site"
        shutil.copytree(site, work)
        _git(work, "init", "-q", "-b", BRANCH)
        _git(work, "add", "-A")
        _git(work, *identity, "commit", "-q", "-m", "Deploy gallery")
        _git(work, "push", "--force", remote, BRANCH)
    return remote
