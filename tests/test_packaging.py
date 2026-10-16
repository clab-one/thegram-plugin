"""Offline install-archive contract checks; no account, server or host required."""

from copy import deepcopy
import importlib.util
import json
import hashlib
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
import warnings
import zipfile


REPOSITORY = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("package_plugin", REPOSITORY / "scripts/package_plugin.py")
package = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(package)


def skill(name="thegram-cloud", body=""):
    return (f"---\nname: {name}\ndescription: Synthetic offline fixture.\n---\n\n{body}\n").encode()


class PackagingTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.root = self.directory / "repo"
        self.root.mkdir()
        self.put("skills/thegram-cloud/SKILL.md", skill(body="Read [examples](references/examples.md)."))
        self.put("skills/thegram-cloud/references/examples.md", b"Verified fixture examples.\n")
        self.manifest = {
            "name": "thegram-cloud", "version": "1.5.0",
            "description": "Synthetic Thegram memory plugin.",
            "author": {"name": "Fixture"},
            "extensions": {"com.openai": {"apps": "./.app.json", "interface": {"logo": "./assets/logo.png"}}},
        }
        self.put("plugin.json", package.json_bytes(self.manifest))
        self.put("mcp.json", package.json_bytes({"mcpServers": {"thegram": {
            "type": "streamable-http", "url": "https://vault.thegram.one/mcp",
        }}}))
        self.put("assets/logo.png", b"synthetic image")
        self.put(".claude-plugin/plugin.json", package.json_bytes({"name": "thegram-cloud", "version": "1.5.0"}))
        self.put(".mcp.json", package.json_bytes({"mcpServers": {"thegram": {
            "type": "http", "url": "https://vault.thegram.one/mcp",
        }}}))
        self.put(".app.json", package.json_bytes({"apps": {"thegram": {
            "id": "asdk_app_6acc810ccabc8191acd3f457dc498d43",
        }}}))
        files = {"SKILL.md": (self.root / "skills/thegram-cloud/SKILL.md").read_bytes(),
                 "references/examples.md": (self.root / "skills/thegram-cloud/references/examples.md").read_bytes()}
        self.put("skill-source.lock.json", package.json_bytes({
            "source": {"repository": "clab-one/thegram-mcp", "commit": "0" * 40, "path": "skills/thegram-memory"},
            "files": {name: hashlib.sha256(data.replace(b"name: thegram-cloud\n", b"name: thegram-memory\n")
                       if name == "SKILL.md" else data).hexdigest() for name, data in files.items()},
        }))

    def put(self, name, data):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def zip(self, name, files):
        path = self.directory / name
        with zipfile.ZipFile(path, "w") as archive:
            for member, data in files.items():
                archive.writestr(member, data)
        return path

    def private_files(self, skills="./skills/"):
        # These are fake values. They prove byte/field preservation without
        # reading a real user's downloaded plugin or credentials.
        manifest = {
            "name": "private-original-id", "version": "1.0.0",
            "description": "Original private description", "author": {"name": "Original owner"},
            "apps": "./bindings/original.app.json", "interface": {"displayName": "Private display", "unknown": True},
            "scopes": ["original-scope"], "oauth": {"clientId": "fake-id", "refreshToken": "fake-token"},
            "deployment": {"region": "original", "unknownSetting": 17}, "future": {"kept": [1, 2]},
        }
        if skills is not None:
            manifest["skills"] = skills
        return {
            ".codex-plugin/plugin.json": package.json_bytes(manifest),
            "bindings/original.app.json": b'{"fakeBinding":"unchanged"}\n',
            "assets/private.png": b"private asset preserved",
            "notes/custom.txt": b"unknown payload preserved",
            "skills/thegram-cloud/SKILL.md": skill(body="Old instructions."),
            "skills/thegram-cloud/references/obsolete.md": b"remove old owned reference",
            "skills/another-skill/SKILL.md": skill("another-skill", "Original unrelated skill."),
        }

    def update(self, files, version="1.5.0"):
        source = self.zip("private.zip", files)
        output = self.directory / "updated.zip"
        package.update_private(source, version, output, self.root)
        return package.read_archive(output)

    def test_private_preserves_identity_bindings_settings_and_unrelated_files(self):
        files = self.private_files()
        original = json.loads(files[package.PRIVATE_MANIFEST])
        source_bytes = self.zip("original.zip", files).read_bytes()
        updated = self.update(files)
        manifest = json.loads(updated[package.PRIVATE_MANIFEST])
        expected = deepcopy(original)
        expected["version"] = "1.5.0"
        self.assertEqual(manifest, expected)
        for name in files:
            if name != package.PRIVATE_MANIFEST and not name.startswith(package.SKILL_ROOT + "/"):
                self.assertEqual(updated[name], files[name])
        self.assertNotIn("skills/thegram-cloud/references/obsolete.md", updated)
        self.assertEqual(updated[package.SKILL_ROOT + "/SKILL.md"], (self.root / package.SKILL_ROOT / "SKILL.md").read_bytes())
        self.assertFalse(any("thegram-cloud/thegram-cloud/" in name for name in updated))
        self.assertEqual((self.directory / "original.zip").read_bytes(), source_bytes)

    def test_existing_skill_root_string_is_not_changed(self):
        updated = self.update(self.private_files("./skills/"))
        self.assertEqual(json.loads(updated[package.PRIVATE_MANIFEST])["skills"], "./skills/")

    def test_direct_owned_skill_string_is_not_changed(self):
        updated = self.update(self.private_files("./skills/thegram-cloud/"))
        self.assertEqual(json.loads(updated[package.PRIVATE_MANIFEST])["skills"], "./skills/thegram-cloud/")

    def test_custom_skill_string_becomes_ordered_array(self):
        files = self.private_files("./custom-skills/")
        files["custom-skills/extra/SKILL.md"] = skill("extra")
        updated = self.update(files)
        self.assertEqual(json.loads(updated[package.PRIVATE_MANIFEST])["skills"],
                         ["./custom-skills/", "./skills/thegram-cloud/"])
        self.assertEqual(updated["custom-skills/extra/SKILL.md"], files["custom-skills/extra/SKILL.md"])

    def test_skill_array_order_and_existing_route_are_preserved(self):
        routes = ["./custom-skills/", "./skills/", "./third-skills/"]
        updated = self.update(self.private_files(routes))
        self.assertEqual(json.loads(updated[package.PRIVATE_MANIFEST])["skills"], routes)

    def test_absent_skills_adds_discoverable_route(self):
        updated = self.update(self.private_files(None))
        self.assertEqual(json.loads(updated[package.PRIVATE_MANIFEST])["skills"], ["./skills/"])

    def test_old_owned_location_is_replaced_without_conflicting_instructions(self):
        files = self.private_files(["./old-memory/", "./custom-skills/"])
        files["old-memory/SKILL.md"] = skill(body="Old Thegram instructions.")
        files["old-memory/references/stale.md"] = b"stale"
        files["custom-skills/extra/SKILL.md"] = skill("extra")
        updated = self.update(files)
        self.assertFalse(any(name.startswith("old-memory/") for name in updated))
        self.assertEqual(json.loads(updated[package.PRIVATE_MANIFEST])["skills"],
                         ["./custom-skills/", "./skills/thegram-cloud/"])

    def test_invalid_skills_shapes_and_paths_are_rejected(self):
        for routes in (17, {}, ["./skills/", 3], "../skills", "/skills", "./skills/thegram-cloud/SKILL.md"):
            with self.subTest(routes=routes), self.assertRaises(package.PackageError):
                package.skill_routes({"skills": routes})

    def test_unsafe_archive_names_fail_without_output(self):
        for name in ("../escape", "/absolute", "C:/drive", "\\\\server\\share", "skills\\escape", "a/./b", "a//b"):
            with self.subTest(name=name):
                source = self.zip("unsafe.zip", {**self.private_files(), name: b"unsafe"})
                output = self.directory / "unsafe-output.zip"
                with self.assertRaises(package.PackageError):
                    package.update_private(source, "1.5.0", output, self.root)
                self.assertFalse(output.exists())

    def test_symlink_archive_entry_is_rejected(self):
        source = self.directory / "symlink.zip"
        with zipfile.ZipFile(source, "w") as archive:
            info = zipfile.ZipInfo("link")
            info.create_system = 3
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            archive.writestr(info, "/private/target")
        with self.assertRaises(package.PackageError):
            package.read_archive(source)

    def test_duplicate_and_case_conflicting_archive_entries_are_rejected(self):
        for names in (("same", "same"), ("same", "SAME"), ("node/", "node")):
            with self.subTest(names=names):
                source = self.directory / "duplicate.zip"
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", UserWarning)
                    with zipfile.ZipFile(source, "w") as archive:
                        for name in names:
                            archive.writestr(name, b"same")
                with self.assertRaises(package.PackageError):
                    package.read_archive(source)

    def test_file_directory_collision_is_rejected(self):
        source = self.zip("collision.zip", {"node": b"file", "node/child": b"child"})
        with self.assertRaises(package.PackageError):
            package.read_archive(source)
        source = self.zip("collision-empty-directory.zip", {"node": b"file", "node/empty/": b""})
        with self.assertRaises(package.PackageError):
            package.read_archive(source)

    def test_private_zip_modes_comments_and_empty_directories_are_preserved(self):
        source = self.zip("metadata.zip", self.private_files())
        with zipfile.ZipFile(source, "a") as archive:
            archive.comment = b"original private archive comment"
            info = zipfile.ZipInfo("bindings/helper.sh", (2022, 2, 3, 4, 5, 6))
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | 0o755) << 16
            info.comment = b"original entry metadata"
            archive.writestr(info, b"#!/bin/sh\nexit 0\n")
            archive.writestr("assets/empty/", b"")
        output = self.directory / "metadata-updated.zip"
        package.update_private(source, "1.5.0", output, self.root)
        with zipfile.ZipFile(output) as archive:
            self.assertEqual(archive.comment, b"original private archive comment")
            preserved = archive.getinfo("bindings/helper.sh")
            self.assertEqual(preserved.external_attr >> 16, stat.S_IFREG | 0o755)
            self.assertEqual(preserved.date_time, (2022, 2, 3, 4, 5, 6))
            self.assertEqual(preserved.comment, b"original entry metadata")
            self.assertTrue(archive.getinfo("assets/empty/").is_dir())

    def test_nested_foreign_skill_is_not_deleted(self):
        files = self.private_files()
        files["skills/thegram-cloud/nested/SKILL.md"] = skill("foreign-nested")
        source = self.zip("nested.zip", files)
        output = self.directory / "nested-output.zip"
        with self.assertRaises(package.PackageError):
            package.update_private(source, "1.5.0", output, self.root)
        self.assertFalse(output.exists())

    def test_canonical_foreign_or_unknown_folder_is_not_deleted(self):
        for contents in (skill("other"), b"missing ownership frontmatter", None):
            files = self.private_files()
            if contents is None:
                del files[package.SKILL_ROOT + "/SKILL.md"]
            else:
                files[package.SKILL_ROOT + "/SKILL.md"] = contents
            files[package.SKILL_ROOT + "/data.txt"] = b"must preserve"
            source = self.zip("foreign.zip", files)
            original = source.read_bytes()
            output = self.directory / "foreign-output.zip"
            with self.subTest(contents=contents), self.assertRaises(package.PackageError):
                package.update_private(source, "1.5.0", output, self.root)
            self.assertEqual(source.read_bytes(), original)
            self.assertFalse(output.exists())

    def test_source_and_existing_output_are_never_clobbered(self):
        source = self.zip("source.zip", self.private_files())
        original = source.read_bytes()
        with self.assertRaises(package.PackageError):
            package.update_private(source, "1.5.0", source, self.root)
        self.assertEqual(source.read_bytes(), original)
        output = self.directory / "existing.zip"
        output.write_bytes(b"previous output")
        with self.assertRaises(package.PackageError):
            package.update_private(source, "1.5.0", output, self.root)
        self.assertEqual(output.read_bytes(), b"previous output")

    def test_invalid_private_manifest_fails_without_output(self):
        for manifest in (None, b"not json", b"[]", b"{}"):
            files = self.private_files()
            del files[package.PRIVATE_MANIFEST]
            if manifest is not None:
                files[package.PRIVATE_MANIFEST] = manifest
            source = self.zip("invalid.zip", files)
            output = self.directory / "invalid-output.zip"
            with self.subTest(manifest=manifest), self.assertRaises(package.PackageError):
                package.update_private(source, "1.5.0", output, self.root)
            self.assertFalse(output.exists())

    def test_host_packages_exclude_private_files_and_other_host_manifests(self):
        for name in (".env", "private.zip", "evidence/private.json", "tests/private.json", ".git/config"):
            self.put(name, b"must not be released")
        for host, manifest in (("chatgpt", ".codex-plugin/plugin.json"), ("claude", ".claude-plugin/plugin.json")):
            output = self.directory / (host + ".zip")
            package.build_package(self.root, output, host, "1.5.0")
            files = package.read_archive(output)
            self.assertIn(manifest, files)
            self.assertNotIn("plugin.json", files)
            self.assertNotIn("mcp.json", files)
            self.assertNotIn(".env", files)
            self.assertNotIn("private.zip", files)
            self.assertNotIn(".git/config", files)
            self.assertEqual(package.validate_package(files, host, "1.5.0"), "1.5.0")
            self.assertEqual(".app.json" in files, host == "chatgpt")
            self.assertEqual(json.loads(files[".mcp.json"])["mcpServers"]["thegram"],
                             {"type": "http", "url": "https://vault.thegram.one/mcp"})

    def test_public_archive_reproducible(self):
        for host in ("chatgpt", "claude"):
            first, second = self.directory / (host + "-first.zip"), self.directory / (host + "-second.zip")
            package.build_package(self.root, first, host)
            package.build_package(self.root, second, host)
            self.assertEqual(first.read_bytes(), second.read_bytes())

    def test_public_manifest_version_and_identity_mismatch_fail(self):
        for manifest in ({"name": "other", "version": "1.5.0"}, {"name": "thegram-cloud", "version": "1.4.0"}):
            self.put(".claude-plugin/plugin.json", package.json_bytes(manifest))
            with self.subTest(manifest=manifest), self.assertRaises(package.PackageError):
                package.build_package(self.root, self.directory / "bad.zip", "claude")
        with self.assertRaises(package.PackageError):
            package.build_package(self.root, self.directory / "bad.zip", "chatgpt", "1.6.0")

    def test_public_app_binding_must_keep_the_registered_thegram_identity(self):
        for app in ({"apps": {"other": {"id": "fake-app"}}},
                    {"apps": {"thegram": {"id": "asdk_app_another"}}},
                    {"apps": {"thegram": {"id": "asdk_app_6acc810ccabc8191acd3f457dc498d43",
                                            "access_token": "fake-secret"}}}):
            self.put(".app.json", package.json_bytes(app))
            with self.subTest(app=app), self.assertRaises(package.PackageError):
                package.build_package(self.root, self.directory / "bad.zip", "chatgpt")

    def test_listing_short_description_limit(self):
        self.manifest["extensions"]["com.openai"]["interface"]["shortDescription"] = "x" * 31
        self.put("plugin.json", package.json_bytes(self.manifest))
        with self.assertRaises(package.PackageError):
            package.build_package(self.root, self.directory / "bad.zip", "chatgpt")

    def test_semver_pre_release_numeric_rules(self):
        for version in ("1.5.0", "1.5.0-rc.1", "1.5.0+build.001"):
            self.assertEqual(package.check_version(version), version)
        for version in ("1.5.0-01", "1.5.0-rc..1", "01.5.0", "1.5.0+"):
            with self.subTest(version=version), self.assertRaises(package.PackageError):
                package.check_version(version)

    def test_missing_reference_and_frontmatter_fail(self):
        for data in (b"No frontmatter", skill(body="[missing](references/missing.md)")):
            self.put("skills/thegram-cloud/SKILL.md", data)
            with self.subTest(data=data), self.assertRaises(package.PackageError):
                package.build_package(self.root, self.directory / "bad.zip", "chatgpt")

    def test_duplicate_owned_skill_identity_fails(self):
        self.put("skills/conflicting/SKILL.md", skill())
        with self.assertRaises(package.PackageError):
            package.build_package(self.root, self.directory / "bad.zip", "chatgpt")

    def test_credentials_and_private_files_within_allowed_tree_fail(self):
        for name, data in (("assets/config.json", package.json_bytes({"access_token": "fake-secret"})),
                           ("skills/thegram-cloud/.env", b"private"), ("assets/private.token", b"private")):
            self.put(name, data)
            with self.subTest(name=name), self.assertRaises(package.PackageError):
                package.build_package(self.root, self.directory / "bad.zip", "chatgpt")
            (self.root / name).unlink()

    def test_native_endpoint_credentials_fail(self):
        self.put(".mcp.json", package.json_bytes({"mcpServers": {"thegram": {
            "type": "http", "url": "https://vault.thegram.one/mcp", "headers": {"X-Key": "fake"},
        }}}))
        with self.assertRaises(package.PackageError):
            package.build_package(self.root, self.directory / "bad.zip", "chatgpt")

    def test_build_ignores_generated_finder_metadata(self):
        self.put("skills/.DS_Store", b"generated Finder metadata")
        output = package.build_package(self.root, self.directory / "with-finder-metadata.zip", "chatgpt")
        with zipfile.ZipFile(output) as archive:
            self.assertNotIn("skills/.DS_Store", archive.namelist())

    def test_local_symlink_file_and_directory_fail(self):
        target = self.directory / "external"
        target.write_bytes(b"external")
        link = self.root / "assets/link"
        link.symlink_to(target)
        with self.assertRaises(package.PackageError):
            package.build_package(self.root, self.directory / "bad.zip", "chatgpt")
        link.unlink()
        link.symlink_to(self.root / "skills", target_is_directory=True)
        with self.assertRaises(package.PackageError):
            package.build_package(self.root, self.directory / "bad.zip", "chatgpt")
    def test_private_skill_source_rejects_symlink_ancestor(self):
        separate_root = self.directory / "symlink-repo"
        separate_root.mkdir()
        (separate_root / "skills").symlink_to(self.root / "skills", target_is_directory=True)
        source = self.zip("safe.zip", self.private_files())
        with self.assertRaises(package.PackageError):
            package.update_private(source, "1.5.0", self.directory / "bad.zip", separate_root)

    def test_cli_build_and_validate_work_offline(self):
        output = self.directory / "cli.zip"
        command = [sys.executable, str(REPOSITORY / "scripts/package_plugin.py")]
        built = subprocess.run(command + ["build", "--host", "chatgpt", "--root", str(self.root), "--output", str(output),
                                           "--expected-version", "1.5.0"], capture_output=True, text=True)
        self.assertEqual(built.returncode, 0, built.stderr)
        validated = subprocess.run(command + ["validate", str(output), "--host", "chatgpt", "--expected-version", "1.5.0"],
                                   capture_output=True, text=True)
        self.assertEqual(validated.returncode, 0, validated.stderr)

    def test_claude_private_update_preserves_identity_connection_and_unrelated_payload(self):
        files = self.private_files()
        manifest = files.pop(".codex-plugin/plugin.json")
        files[".claude-plugin/plugin.json"] = manifest
        source = self.zip("claude-private.zip", files)
        output = self.directory / "claude-updated.zip"
        package.update_private(source, "1.5.0", output, self.root, host="claude")
        updated = package.read_archive(output)
        expected = json.loads(manifest)
        expected["version"] = "1.5.0"
        self.assertEqual(json.loads(updated[".claude-plugin/plugin.json"]), expected)
        for name, data in files.items():
            if name != ".claude-plugin/plugin.json" and not name.startswith(package.SKILL_ROOT + "/"):
                self.assertEqual(updated[name], data)

    def test_cli_refuses_drift_from_pinned_shared_workflow_without_output(self):
        self.put("skills/thegram-cloud/SKILL.md", skill(body="Changed separately from the shared workflow."))
        output = self.directory / "drifted.zip"
        result = subprocess.run([sys.executable, str(REPOSITORY / "scripts/package_plugin.py"),
                                 "build", "--host", "chatgpt", "--root", str(self.root),
                                 "--output", str(output)], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
