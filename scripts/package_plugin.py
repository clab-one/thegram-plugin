#!/usr/bin/env python3
"""Build public plugin archives or safely overlay a downloaded private plugin.

No extraction, network access or external Python packages are required. Public
archives use the Agent Plugins fixed-location layout. Private ChatGPT downloads
keep their .codex-plugin manifest, app bindings and all unrelated payload bytes.
"""

from __future__ import annotations

import argparse
from copy import copy
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import posixpath
import re
import stat
import tempfile
from urllib.parse import urlsplit
import zipfile


PLUGIN_NAME = "thegram-cloud"
SKILL_ROOT = "skills/thegram-cloud"
PRIVATE_MANIFEST = ".codex-plugin/plugin.json"
PUBLIC_FILES = ("plugin.json", "mcp.json", ".mcp.json")
PUBLIC_TREES = ("skills", "assets", ".claude-plugin")
VERSION_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$")
MARKDOWN_LINK_RE = re.compile(r"!?\[[^\]\n]*\]\(([^\s)]+)(?:\s+[^)]*)?\)")
MAX_FILES = 10000
MAX_BYTES = 256 * 1024 * 1024


class PackageError(ValueError):
    """A package violates the supported layout or safety rules."""


def checked_name(name: str, *, directory: bool = False) -> str:
    """Reject paths whose meaning differs across ZIP consumers/platforms."""
    if not name or "\x00" in name or "\\" in name or name.startswith("/"):
        raise PackageError(f"Unsafe archive path: {name!r}")
    plain = name[:-1] if directory and name.endswith("/") else name
    parts = plain.split("/")
    if any(part in ("", ".", "..") or ":" in part for part in parts):
        raise PackageError(f"Unsafe archive path: {name!r}")
    if name.endswith("/") and not directory:
        raise PackageError(f"Expected a file path: {name!r}")
    return plain


def check_file_tree(files: dict[str, bytes]) -> None:
    folded: dict[str, str] = {}
    for name in files:
        checked_name(name)
        key = name.casefold()
        if key in folded:
            raise PackageError(f"Conflicting paths: {folded[key]} and {name}")
        folded[key] = name
    for name in files:
        for parent in PurePosixPath(name).parents:
            if str(parent).casefold() in folded:
                raise PackageError(f"File/directory collision at {parent}")


def read_archive(path: Path, metadata: dict[str, zipfile.ZipInfo] | None = None) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    seen: dict[str, str] = {}
    directories: set[str] = set()
    total = 0
    try:
        with zipfile.ZipFile(path) as archive:
            if len(archive.infolist()) > MAX_FILES:
                raise PackageError("Archive has too many entries")
            for info in archive.infolist():
                if info.orig_filename != info.filename:
                    raise PackageError(f"Ambiguous archive filename: {info.orig_filename!r}")
                name = checked_name(info.filename, directory=info.is_dir())
                key = name.casefold()
                if key in seen:
                    raise PackageError(f"Duplicate archive path: {info.filename}")
                seen[key] = name
                if metadata is not None:
                    metadata[name] = copy(info)
                mode = (info.external_attr >> 16) & 0xFFFF
                kind = stat.S_IFMT(mode)
                if kind not in (0, stat.S_IFREG, stat.S_IFDIR):
                    raise PackageError(f"Unsupported archive entry (including symlinks): {name}")
                if kind == stat.S_IFDIR and not info.is_dir():
                    raise PackageError(f"Directory entry lacks a trailing slash: {name}")
                if info.flag_bits & 1:
                    raise PackageError(f"Encrypted archive entry: {name}")
                total += info.file_size
                if total > MAX_BYTES:
                    raise PackageError("Archive exceeds the uncompressed size limit")
                if info.is_dir():
                    directories.add(key)
                else:
                    files[name] = archive.read(info)
    except (OSError, zipfile.BadZipFile, RuntimeError) as exc:
        raise PackageError(f"Cannot read archive: {exc}") from exc
    check_file_tree(files)
    for name in files:
        if name.casefold() in directories:
            raise PackageError(f"File/directory collision at {name}")
    for directory in directories:
        for parent in PurePosixPath(directory).parents:
            if str(parent).casefold() in {name.casefold() for name in files}:
                raise PackageError(f"File/directory collision at {parent}")
    return files


def load_json(files: dict[str, bytes], name: str) -> dict:
    try:
        value = json.loads(files[name])
    except (KeyError, UnicodeError, json.JSONDecodeError) as exc:
        raise PackageError(f"Missing or invalid JSON object: {name}") from exc
    if not isinstance(value, dict):
        raise PackageError(f"Expected JSON object: {name}")
    return value


def json_bytes(value: dict) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def check_version(version: object) -> str:
    match = VERSION_RE.fullmatch(version) if isinstance(version, str) else None
    if not match or (match[4] and any(part.isdigit() and len(part) > 1 and part.startswith("0")
                                     for part in match[4].split("."))):
        raise PackageError(f"Invalid semantic version: {version!r}")
    return version


def frontmatter(data: bytes, name: str) -> dict[str, str]:
    try:
        text = data.decode("utf-8")
    except UnicodeError as exc:
        raise PackageError(f"Skill is not UTF-8: {name}") from exc
    lines = text.splitlines()
    if not lines or lines[0] != "---" or "---" not in lines[1:]:
        raise PackageError(f"Missing skill frontmatter: {name}")
    end = lines[1:].index("---") + 1
    result = {}
    for line in lines[1:end]:
        if ":" in line and not line.startswith((" ", "\t", "#")):
            key, value = line.split(":", 1)
            result[key] = value.strip().strip("\"'")
    for key in ("name", "description"):
        if not result.get(key) or result[key] in ("|", ">"):
            raise PackageError(f"Skill needs a nonempty one-line {key}: {name}")
    return result


def skill_routes(manifest: dict) -> list[str]:
    routes = manifest.get("skills", [])
    if isinstance(routes, str):
        routes = [routes]
    if not isinstance(routes, list) or any(not isinstance(route, str) for route in routes):
        raise PackageError("Private manifest skills must be a local path string or an array of strings")
    normalized = []
    for route in routes:
        route = route.removeprefix("./").rstrip("/")
        checked_name(route)
        if route.endswith("/SKILL.md"):
            raise PackageError("Skill routes must name directories, not SKILL.md files")
        normalized.append(route)
    return normalized


def discovered_skills(files: dict[str, bytes], routes: list[str]) -> list[str]:
    return sorted(name for name in files if name.endswith("/SKILL.md") and any(
        name.startswith(route + "/") for route in routes
    ))


def validate_skill_files(files: dict[str, bytes], routes: list[str], *, owned_only: bool = False) -> None:
    names = discovered_skills(files, routes)
    owned = []
    identities: dict[str, str] = {}
    for name in names:
        # Private unrelated skills belong to the original download. Do not impose
        # our authoring format on them, but detect duplicate owned identities.
        if owned_only and name != SKILL_ROOT + "/SKILL.md":
            try:
                meta = frontmatter(files[name], name)
            except PackageError:
                continue
        else:
            meta = frontmatter(files[name], name)
        identity = meta["name"]
        if not owned_only and identity in identities:
            raise PackageError(f"Duplicate skill name {identity}: {identities[identity]} and {name}")
        identities[identity] = name
        if identity == PLUGIN_NAME:
            owned.append(name)
    if owned != [SKILL_ROOT + "/SKILL.md"]:
        raise PackageError("The bundled thegram-cloud skill must be discoverable exactly once")
    markdown = [name for name in files if name.endswith(".md") and (
        name.startswith(SKILL_ROOT + "/") if owned_only else name.startswith("skills/")
    )]
    for name in markdown:
        try:
            text = files[name].decode("utf-8")
        except UnicodeError as exc:
            raise PackageError(f"Markdown is not UTF-8: {name}") from exc
        for match in MARKDOWN_LINK_RE.finditer(text):
            target = match.group(1).strip("<>")
            if target.startswith(("#", "@")) or urlsplit(target).scheme:
                continue
            target = target.split("#", 1)[0].split("?", 1)[0]
            resolved = posixpath.normpath(posixpath.join(posixpath.dirname(name), target))
            checked_name(resolved)
            if target.startswith("/") or not (resolved in files or any(
                item.startswith(resolved.rstrip("/") + "/") for item in files
            )):
                raise PackageError(f"Missing local reference in {name}: {target}")


def read_local_file(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise PackageError(f"Expected a regular file, never a symlink: {path}")
    return path.read_bytes()


def local_tree(root: Path, prefix: str) -> dict[str, bytes]:
    current = root
    for part in PurePosixPath(prefix).parts:
        current = current / part
        if current.is_symlink():
            raise PackageError(f"Symlink directory: {current}")
    directory = root / prefix
    if directory.is_symlink() or not directory.is_dir():
        raise PackageError(f"Expected a directory, never a symlink: {directory}")
    files = {}
    for current, dirs, filenames in os.walk(directory, followlinks=False):
        for dirname in dirs:
            if (Path(current) / dirname).is_symlink():
                raise PackageError(f"Symlink directory: {Path(current) / dirname}")
        for filename in filenames:
            if filename == ".DS_Store":
                continue
            path = Path(current) / filename
            name = path.relative_to(root).as_posix()
            checked_name(name)
            files[name] = read_local_file(path)
    check_file_tree(files)
    return files


def no_credentials(value: object, path: str) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if re.search(r"(?:password|secret|token|authorization|credential|api[_-]?key)", key, re.I) and child:
                raise PackageError(f"Credential-like field is forbidden in public package: {path}.{key}")
            no_credentials(child, path + "." + key)
    elif isinstance(value, list):
        for child in value:
            no_credentials(child, path)
    elif isinstance(value, str) and value.startswith(("https://", "http://")):
        url = urlsplit(value)
        if url.username or url.password:
            raise PackageError(f"Credential-bearing URL is forbidden in public package: {path}")


def no_apps(value: object, path: str) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "apps" and child is not None:
                raise PackageError(f"App bindings belong only in a private download: {path}.apps")
            no_apps(child, path + "." + key)
    elif isinstance(value, list):
        for child in value:
            no_apps(child, path)


def public_server(files: dict[str, bytes], name: str) -> dict:
    servers = load_json(files, name).get("mcpServers")
    if not isinstance(servers, dict) or set(servers) != {"thegram"} or not isinstance(servers["thegram"], dict):
        raise PackageError(f"Expected only the existing Thegram server in {name}")
    return servers["thegram"]


def validate_public(files: dict[str, bytes], expected_version: str | None = None) -> str:
    check_file_tree(files)
    for name in files:
        if name not in PUBLIC_FILES and not any(name.startswith(tree + "/") for tree in PUBLIC_TREES):
            raise PackageError(f"Not allowlisted for a public release: {name}")
        if any(part.startswith(".") or part == "__pycache__" for part in name.split("/")
               if part not in (".claude-plugin", ".mcp.json")):
            raise PackageError(f"Hidden/private file is forbidden in a public release: {name}")
        if name.endswith((".token", ".pyc", ".zip")):
            raise PackageError(f"Private/generated file is forbidden in a public release: {name}")
        if name.endswith(".json"):
            no_credentials(load_json(files, name), name)
    manifest = load_json(files, "plugin.json")
    for key in ("skills", "mcpServers", "apps", "interface"):
        if key in manifest:
            raise PackageError(f"Private/nonportable manifest field is forbidden at portable root: {key}")
    no_apps(manifest, "plugin.json")
    if manifest.get("name") != PLUGIN_NAME:
        raise PackageError("Portable plugin identity must remain thegram-cloud")
    version = check_version(manifest.get("version"))
    if expected_version is not None and version != expected_version:
        raise PackageError(f"Version {version} does not match expected {expected_version}")
    # Agent Plugins 1.0 loads skills/ and mcp.json at fixed paths. No private
    # .codex-plugin fields are injected into the portable root manifest.
    validate_skill_files(files, ["skills"])
    server = public_server(files, "mcp.json")
    if server != {"type": "streamable-http", "url": "https://vault.thegram.one/mcp"}:
        raise PackageError("Portable Thegram endpoint/type changed or includes private settings")
    if ".claude-plugin/plugin.json" in files:
        compat = load_json(files, ".claude-plugin/plugin.json")
        no_apps(compat, ".claude-plugin/plugin.json")
        if compat.get("name") != PLUGIN_NAME or compat.get("version") != version:
            raise PackageError("Claude compatibility identity/version differs from portable manifest")
    if ".mcp.json" in files:
        compat = public_server(files, ".mcp.json")
        if compat != {"type": "http", "url": "https://vault.thegram.one/mcp"}:
            raise PackageError("Claude compatibility endpoint/type changed or includes private settings")
    extensions = manifest.get("extensions", {})
    if not isinstance(extensions, dict) or not isinstance(extensions.get("com.openai", {}), dict):
        raise PackageError("Portable extensions must be objects")
    interface = extensions.get("com.openai", {}).get("interface", {})
    if not isinstance(interface, dict):
        raise PackageError("Portable listing interface must be an object")
    short = interface.get("shortDescription")
    if short is not None and (not isinstance(short, str) or len(short) > 30):
        raise PackageError("Listing shortDescription must have at most 30 characters")
    for key in ("composerIcon", "composerIconDark", "logo", "logoDark"):
        if key in interface:
            target = interface[key]
            if not isinstance(target, str):
                raise PackageError(f"Invalid interface asset: {key}")
            target = target.removeprefix("./")
            checked_name(target)
            if target not in files or not target.startswith("assets/"):
                raise PackageError(f"Missing bundled interface asset: {target}")
    return version


def shared_skill_hashes(files: dict[str, bytes], prefix: str) -> dict[str, str]:
    hashes = {}
    for name, data in sorted(files.items()):
        relative = name.removeprefix(prefix + "/")
        if relative == "SKILL.md":
            data = data.replace(b"name: thegram-cloud\n", b"name: thegram-memory\n", 1)
        hashes[relative] = hashlib.sha256(data).hexdigest()
    return hashes


def verify_shared_skill(root: Path) -> None:
    lock = json.loads(read_local_file(root / "skill-source.lock.json"))
    source = lock.get("source", {})
    if source.get("repository") != "clab-one/thegram-mcp" or source.get("path") != "skills/thegram-memory":
        raise PackageError("The shared workflow lock names an unexpected source")
    if not re.fullmatch(r"[0-9a-f]{40}", str(source.get("commit", ""))):
        raise PackageError("The shared workflow must pin a full source commit")
    if shared_skill_hashes(local_tree(root, SKILL_ROOT), SKILL_ROOT) != lock.get("files"):
        raise PackageError("Bundled workflow differs from the pinned shared skill; run scripts/sync_skill.py")


def write_archive(files: dict[str, bytes], output: Path, source: Path | None = None,
                  metadata: dict[str, zipfile.ZipInfo] | None = None, archive_comment: bytes = b"") -> Path:
    output = output.absolute()
    if source is not None and output.resolve() == source.resolve():
        raise PackageError("Output must not replace the source archive")
    if output.exists() or output.is_symlink():
        raise PackageError(f"Output already exists; choose a new path: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    # Create the final path exclusively only after a complete validated ZIP is
    # ready. A failure never truncates an existing archive or leaks a partial one.
    descriptor, temporary = tempfile.mkstemp(prefix=".thegram-package-", suffix=".zip", dir=output.parent)
    os.close(descriptor)
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.comment = archive_comment
            for name, info in sorted((metadata or {}).items()):
                if info.is_dir():
                    archive.writestr(copy(info), b"")
            for name, data in sorted(files.items()):
                info = copy(metadata[name]) if metadata and name in metadata else None
                if info is None:
                    info = zipfile.ZipInfo(name, (2020, 1, 1, 0, 0, 0))
                    info.create_system = 3
                    info.external_attr = (stat.S_IFREG | 0o644) << 16
                    info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, data)
        os.link(temporary, output)
    except OSError as exc:
        raise PackageError(f"Cannot write output without clobbering: {exc}") from exc
    finally:
        os.unlink(temporary)
    return output


def build_public(root: Path, output: Path, expected_version: str | None = None) -> Path:
    files = {name: read_local_file(root / name) for name in PUBLIC_FILES if (root / name).exists()}
    for tree in PUBLIC_TREES:
        if tree in ("skills", "assets") or (root / tree).exists():
            files.update(local_tree(root, tree))
    validate_public(files, expected_version)
    return write_archive(files, output)


def update_private(source: Path, version: str, output: Path, root: Path) -> Path:
    check_version(version)
    if output.resolve() == source.resolve():
        raise PackageError("Output must not replace the source archive")
    metadata = {}
    files = read_archive(source, metadata)
    with zipfile.ZipFile(source) as archive:
        archive_comment = archive.comment
    manifest = load_json(files, PRIVATE_MANIFEST)
    if not isinstance(manifest.get("name"), str) or not manifest["name"].strip():
        raise PackageError("Private plugin must retain an existing nonempty identity")
    routes = skill_routes(manifest)
    # Replace the canonical owned folder, removing stale reference files rather
    # than nesting one copied folder inside another. Also remove an older route
    # whose skill frontmatter explicitly identifies this same owned skill.
    owned_roots = {SKILL_ROOT}
    if any(name == SKILL_ROOT or name.startswith(SKILL_ROOT + "/") for name in metadata):
        canonical_skill = SKILL_ROOT + "/SKILL.md"
        if canonical_skill not in files or frontmatter(files[canonical_skill], canonical_skill)["name"] != PLUGIN_NAME:
            raise PackageError("Existing canonical skill folder has no verified thegram-cloud ownership")
    for name in discovered_skills(files, routes):
        try:
            meta = frontmatter(files[name], name)
        except PackageError:
            continue
        if meta["name"] == PLUGIN_NAME:
            owned_roots.add(posixpath.dirname(name))
    for name in files:
        if name.endswith("/SKILL.md") and any(name.startswith(owned + "/") and
                                               name != owned + "/SKILL.md" for owned in owned_roots):
            raise PackageError(f"Nested skill under an owned folder needs manual separation: {name}")
    for name in list(files):
        if any(name.startswith(owned + "/") for owned in owned_roots):
            del files[name]
    for name in list(metadata):
        if any(name == owned or name.startswith(owned + "/") for owned in owned_roots):
            del metadata[name]
    files.update(local_tree(root, SKILL_ROOT))
    # Preserve route spelling, ordering and string form whenever its directory
    # already discovers the new skill. A direct obsolete owned route is removed;
    # parent directories with unrelated skills stay exactly as supplied.
    original = manifest.get("skills", [])
    original_list = [original] if isinstance(original, str) else list(original)
    kept = [route for route, normalized in zip(original_list, routes)
            if normalized == SKILL_ROOT or normalized not in owned_roots]
    kept_normalized = skill_routes({"skills": kept})
    if not discovered_skills({SKILL_ROOT + "/SKILL.md": b""}, kept_normalized):
        kept.append("./skills/" if not kept else "./skills/thegram-cloud/")
    if isinstance(original, str) and kept == [original]:
        manifest["skills"] = original
    elif len(kept) == 1 and not isinstance(original, list):
        manifest["skills"] = kept[0]
    else:
        manifest["skills"] = kept
    manifest["version"] = version
    files[PRIVATE_MANIFEST] = json_bytes(manifest)
    check_file_tree(files)
    validate_skill_files(files, skill_routes(manifest), owned_only=True)
    return write_archive(files, output, source, metadata, archive_comment)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    default_root = Path(__file__).resolve().parent.parent
    build = commands.add_parser("build", help="Build a credential-free portable release ZIP")
    build.add_argument("--root", type=Path, default=default_root)
    build.add_argument("--output", type=Path, required=True)
    build.add_argument("--expected-version")
    validate = commands.add_parser("validate", help="Validate a portable release ZIP offline")
    validate.add_argument("archive", type=Path)
    validate.add_argument("--expected-version")
    private = commands.add_parser("update-private", help="Overlay the skill onto a private ChatGPT ZIP")
    private.add_argument("source", type=Path)
    private.add_argument("version")
    private.add_argument("--root", type=Path, default=default_root)
    private.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "build":
            verify_shared_skill(args.root)
            print(build_public(args.root, args.output, args.expected_version))
        elif args.command == "validate":
            version = validate_public(read_archive(args.archive), args.expected_version)
            print(f"Valid portable {PLUGIN_NAME} package {version}; bundled skill and references resolve")
        else:
            verify_shared_skill(args.root)
            print(update_private(args.source, args.version, args.output, args.root))
    except (PackageError, OSError, json.JSONDecodeError) as exc:
        parser.exit(1, f"Packaging failed: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
