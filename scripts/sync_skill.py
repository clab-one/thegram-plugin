#!/usr/bin/env python3
"""Import the committed shared workflow without changing the cloud skill identity."""

import argparse
import json
from pathlib import Path
import subprocess

from package_plugin import PackageError, SKILL_ROOT, frontmatter, json_bytes, local_tree, shared_skill_hashes, validate_skill_files, verify_shared_skill

CANONICAL_ROOT = "skills/thegram-memory"


def git(source: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(source), *args], capture_output=True, text=True, check=False)
    if result.returncode:
        raise PackageError("Cannot inspect the canonical source commit")
    return result.stdout.strip()


def sync(source: Path, root: Path) -> dict:
    commit = git(source, "rev-parse", "HEAD")
    if git(source, "status", "--porcelain", "--untracked-files=all", "--", CANONICAL_ROOT):
        raise PackageError("Commit the canonical skill and references before pinning their source")
    files = local_tree(source, CANONICAL_ROOT)
    if frontmatter(files[CANONICAL_ROOT + "/SKILL.md"], "SKILL.md")["name"] != "thegram-memory":
        raise PackageError("The canonical skill identity must remain thegram-memory")
    imported = {}
    for name, data in files.items():
        relative = name.removeprefix(CANONICAL_ROOT + "/")
        if relative == "SKILL.md":
            data = data.replace(b"name: thegram-memory\n", b"name: thegram-cloud\n", 1)
        imported[SKILL_ROOT + "/" + relative] = data
    validate_skill_files(imported, [SKILL_ROOT], owned_only=True)
    existing = local_tree(root, SKILL_ROOT)
    validate_skill_files(existing, [SKILL_ROOT], owned_only=True)
    for name in existing.keys() - imported.keys():
        (root / name).unlink()
    for name, data in imported.items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    lock = {
        "source": {"repository": "clab-one/thegram-mcp", "commit": commit, "path": CANONICAL_ROOT},
        "files": shared_skill_hashes(files, CANONICAL_ROOT),
    }
    (root / "skill-source.lock.json").write_bytes(json_bytes(lock))
    verify_shared_skill(root)
    return lock


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        if args.check:
            verify_shared_skill(args.root)
            print("Shared workflow matches the pinned canonical source")
        elif args.source:
            lock = sync(args.source, args.root)
            print(json.dumps(lock, ensure_ascii=False, indent=2))
        else:
            parser.error("--source or --check is required")
    except (PackageError, OSError, json.JSONDecodeError) as error:
        parser.exit(1, f"Shared skill sync failed: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
