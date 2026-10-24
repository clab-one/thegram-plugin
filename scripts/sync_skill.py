#!/usr/bin/env python3
"""Pin the shared workflow from a validated public release snapshot."""

import argparse
import hashlib
from io import BytesIO
import json
from pathlib import Path

from package_plugin import PackageError, SKILL_ROOT, checked_name, json_bytes, local_tree, read_archive, read_local_file, shared_skill_hashes, validate_public, validate_skill_files, verify_shared_skill


def sync(source: Path, root: Path) -> dict:
    checked_name(source.name)
    if not source.name.endswith(".zip"):
        raise PackageError("The shared workflow source must be a public release ZIP")
    snapshot = read_local_file(source)
    with BytesIO(snapshot) as stream:
        files = read_archive(stream)
    version = validate_public(files)
    imported = {name: data for name, data in files.items() if name.startswith(SKILL_ROOT + "/")}
    existing = local_tree(root, SKILL_ROOT)
    validate_skill_files(existing, [SKILL_ROOT], owned_only=True)
    for name in existing.keys() - imported.keys():
        (root / name).unlink()
    for name, data in imported.items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    lock = {
        "source": {"archive": source.name, "sha256": hashlib.sha256(snapshot).hexdigest(),
                   "version": version, "path": SKILL_ROOT},
        "files": shared_skill_hashes(imported, SKILL_ROOT),
    }
    (root / "skill-source.lock.json").write_bytes(json_bytes(lock))
    verify_shared_skill(root)
    return lock


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--source", type=Path, help="Validated public release ZIP; never an uncommitted source directory")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        if args.check:
            verify_shared_skill(args.root)
            print("Shared workflow matches the pinned public release")
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
