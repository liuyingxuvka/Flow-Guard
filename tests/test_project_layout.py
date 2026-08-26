import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import flowguard.project_layout as project_layout
from flowguard.project_layout import (
    CANONICAL_ROLE_ROOTS,
    audit_project_layout,
    current_layout_manifest_text,
    current_layout_readme_text,
)


class ProjectLayoutTests(unittest.TestCase):
    def _create_current_layout(self, root: Path) -> Path:
        flowguard_root = root / ".flowguard"
        flowguard_root.mkdir()
        (flowguard_root / "project.toml").write_text(
            "[flowguard]\nschema_version = \"1.0\"\n",
            encoding="utf-8",
        )
        (flowguard_root / "adoption_log.jsonl").write_text("", encoding="utf-8")
        (flowguard_root / "README.md").write_text(
            current_layout_readme_text(),
            encoding="utf-8",
        )
        for root_name, _role in CANONICAL_ROLE_ROOTS:
            (flowguard_root / root_name).mkdir()
        (flowguard_root / "layout.toml").write_text(
            current_layout_manifest_text(root),
            encoding="utf-8",
        )
        return flowguard_root

    def _snapshot(self, root: Path) -> tuple[tuple[str, str, bytes], ...]:
        rows: list[tuple[str, str, bytes]] = []
        for path in sorted(root.rglob("*")):
            rel = path.relative_to(root).as_posix()
            if path.is_dir():
                rows.append((rel, "directory", b""))
            else:
                rows.append((rel, "file", path.read_bytes()))
        return tuple(rows)

    def test_current_layout_passes_without_writing_or_moving(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            flowguard_root = self._create_current_layout(root)
            (flowguard_root / "structure" / "owners" / "owner-one").mkdir(parents=True)
            (flowguard_root / "structure" / "owners" / "owner-one" / "contract.json").write_text(
                "{}\n",
                encoding="utf-8",
            )
            (flowguard_root / "layout.toml").write_text(
                current_layout_manifest_text(root), encoding="utf-8"
            )
            before = self._snapshot(root)

            report = audit_project_layout(root)

            self.assertTrue(report.ok)
            self.assertEqual("pass", report.status)
            self.assertEqual(3, report.layout_version)
            self.assertTrue(report.manifest_fingerprint.startswith("sha256:"))
            self.assertEqual((), report.findings)
            self.assertEqual((), report.next_actions)
            self.assertEqual(before, self._snapshot(root))

    def test_layout_observation_is_one_shape_walk_and_does_not_hash_members(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            flowguard_root = self._create_current_layout(root)
            governed = flowguard_root / "behavior" / "intent.json"
            governed.write_text("first\n", encoding="utf-8")
            (flowguard_root / "layout.toml").write_text(
                current_layout_manifest_text(root), encoding="utf-8"
            )

            first = audit_project_layout(root)
            first_shape = first.inventory_fingerprint
            governed.write_text("a much longer replacement\n", encoding="utf-8")
            second = audit_project_layout(root)

            self.assertTrue(first.ok, first.to_json_text())
            self.assertTrue(second.ok, second.to_json_text())
            self.assertEqual(first_shape, second.inventory_fingerprint)
            self.assertEqual(1, second.metrics["counters"]["directory_walk_count"])
            self.assertEqual(1, second.metrics["counters"]["content_hash_read_count"])
            self.assertEqual(0, second.metrics["counters"].get("member_content_hash_reads", 0))

    def test_missing_flowguard_root_and_manifest_fail_closed_without_creation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            report = audit_project_layout(root)

            codes = {finding.code for finding in report.findings}
            self.assertEqual("blocked", report.status)
            self.assertIn("flowguard_directory_missing", codes)
            self.assertIn("layout_manifest_missing", codes)
            self.assertFalse((root / ".flowguard").exists())

    def test_layout_manifest_is_mandatory_and_must_be_current(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            flowguard_root = self._create_current_layout(root)
            (flowguard_root / "layout.toml").unlink()

            missing = audit_project_layout(root)

            self.assertIn(
                "layout_manifest_missing",
                {finding.code for finding in missing.findings},
            )

            stale_text = current_layout_manifest_text().replace(
                'authority = "current"',
                'authority = "legacy"',
            )
            (flowguard_root / "layout.toml").write_text(stale_text, encoding="utf-8")

            stale = audit_project_layout(root)

            self.assertIn(
                "layout_manifest_not_current",
                {finding.code for finding in stale.findings},
            )

    def test_empty_role_roots_are_optional_but_present_roots_must_be_directories(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            flowguard_root = self._create_current_layout(root)
            (flowguard_root / "history").rmdir()
            (flowguard_root / "verification").rmdir()
            (flowguard_root / "verification").write_text("not a directory\n", encoding="utf-8")

            report = audit_project_layout(root)

            codes_by_path = {(finding.code, finding.path) for finding in report.findings}
            self.assertNotIn(("canonical_role_root_missing", "history"), codes_by_path)
            self.assertIn(
                ("canonical_role_root_not_directory", "verification"),
                codes_by_path,
            )

    def test_unknown_top_level_directory_is_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            flowguard_root = self._create_current_layout(root)
            (flowguard_root / "mystery").mkdir()

            report = audit_project_layout(root)

            self.assertIn(
                ("unregistered_layout_entry", "mystery"),
                {(finding.code, finding.path) for finding in report.findings},
            )

    def test_retired_layout_names_are_blocked_in_current_role_shapes(self):
        for role_name in ("behavior", "models", "structure", "verification"):
            retired_name = "dna"
            with self.subTest(retired_name=retired_name):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    flowguard_root = self._create_current_layout(root)
                    blocked_path = flowguard_root / role_name / retired_name
                    blocked_path.mkdir()

                    report = audit_project_layout(root)

                    self.assertIn(
                        ("retired_layout_name", f"{role_name}/{retired_name}"),
                        {(finding.code, finding.path) for finding in report.findings},
                    )

    def test_opaque_evidence_and_history_contents_do_not_enter_layout_denominator(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            flowguard_root = self._create_current_layout(root)
            evidence_file = flowguard_root / "evidence" / "run" / "result.json"
            history_file = flowguard_root / "history" / "retired" / "old.json"
            evidence_file.parent.mkdir(parents=True)
            history_file.parent.mkdir(parents=True)
            evidence_file.write_text('{"status":"pass"}\n', encoding="utf-8")
            history_file.write_text('{"status":"retired"}\n', encoding="utf-8")
            (flowguard_root / "layout.toml").write_text(
                current_layout_manifest_text(root), encoding="utf-8"
            )

            first = audit_project_layout(root)
            evidence_file.write_text('{"status":"changed"}\n', encoding="utf-8")
            (flowguard_root / "evidence" / "dna").mkdir()
            (flowguard_root / "history" / "tmp").mkdir()
            second = audit_project_layout(root)

            self.assertTrue(first.ok, first.to_json_text())
            self.assertTrue(second.ok, second.to_json_text())
            self.assertEqual(first.inventory_fingerprint, second.inventory_fingerprint)
            self.assertNotIn("evidence/run/result.json", second.observed_entries)
            self.assertNotIn("history/retired/old.json", second.observed_entries)
            self.assertEqual(1, second.metrics["counters"]["directory_walk_count"])
            self.assertEqual(0, second.metrics["counters"].get("member_content_hash_reads", 0))

    def test_manifest_cannot_alias_two_roles_to_one_root(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            flowguard_root = self._create_current_layout(root)
            manifest_path = flowguard_root / "layout.toml"
            manifest_path.write_text(
                current_layout_manifest_text().replace(
                    'structure = "structure"',
                    'structure = "models"',
                ),
                encoding="utf-8",
            )

            report = audit_project_layout(root)

            self.assertIn(
                "layout_manifest_duplicate_role",
                {finding.code for finding in report.findings},
            )

    def test_symlink_junction_or_reparse_role_root_blocks_before_opaque_contents(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            flowguard_root = self._create_current_layout(root)
            redirected = flowguard_root / "evidence"
            real_check = project_layout._path_is_reparse_or_symlink

            def fake_reparse(path: Path) -> bool:
                if path == redirected:
                    return True
                return real_check(path)

            with patch(
                "flowguard.project_layout._path_is_reparse_or_symlink",
                side_effect=fake_reparse,
            ):
                report = audit_project_layout(root)

            self.assertIn(("layout_reparse_or_symlink", "evidence"),
                          {(finding.code, finding.path) for finding in report.findings})
            self.assertNotIn("evidence/redirected", report.observed_entries)

    def test_reparse_layout_manifest_is_rejected_before_it_can_be_authority(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            flowguard_root = self._create_current_layout(root)
            manifest_path = flowguard_root / "layout.toml"
            real_check = project_layout._path_is_reparse_or_symlink

            def fake_reparse(path: Path) -> bool:
                if path == manifest_path:
                    return True
                return real_check(path)

            with patch(
                "flowguard.project_layout._path_is_reparse_or_symlink",
                side_effect=fake_reparse,
            ):
                report = audit_project_layout(root)

            self.assertEqual("", report.manifest_fingerprint)
            self.assertIn(
                ("layout_reparse_or_symlink", ".flowguard/layout.toml"),
                {(finding.code, finding.path) for finding in report.findings},
            )

    def test_bytecode_and_tool_cache_are_blocked_without_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            flowguard_root = self._create_current_layout(root)
            cache = flowguard_root / "models" / "__pycache__"
            cache.mkdir()
            bytecode = flowguard_root / "verification" / "runner.pyc"
            bytecode.write_bytes(b"generated")
            before = self._snapshot(root)

            report = audit_project_layout(root)

            codes = {finding.code for finding in report.findings}
            self.assertIn("layout_tool_cache", codes)
            self.assertIn("retired_layout_name", codes)
            self.assertIn("layout_bytecode_artifact", codes)
            self.assertEqual(before, self._snapshot(root))

    def test_exact_inventory_change_blocks_and_preserves_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            flowguard_root = self._create_current_layout(root)
            before = self._snapshot(root)
            (flowguard_root / "behavior" / "new-intent.json").write_text(
                "{}\n", encoding="utf-8"
            )

            report = audit_project_layout(root)

            self.assertIn(
                "layout_inventory_conservation_mismatch",
                {finding.code for finding in report.findings},
            )
            self.assertNotEqual(before, self._snapshot(root))
            after_audit = self._snapshot(root)
            self.assertEqual(after_audit, self._snapshot(root))

    def test_wrong_role_is_blocked_but_equal_bytes_are_not_a_layout_error(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            flowguard_root = self._create_current_layout(root)
            (flowguard_root / "models" / "receipt-current.json").write_text(
                "same\n", encoding="utf-8"
            )
            (flowguard_root / "evidence" / "model.py").write_text(
                "same\n", encoding="utf-8"
            )
            (flowguard_root / "behavior" / "same.json").write_text(
                "same\n", encoding="utf-8"
            )
            (flowguard_root / "layout.toml").write_text(
                current_layout_manifest_text(root), encoding="utf-8"
            )

            report = audit_project_layout(root)

            codes = {finding.code for finding in report.findings}
            self.assertIn("layout_role_authority_mismatch", codes)
            self.assertNotIn("layout_inventory_content_collision", codes)

    def test_identity_and_model_pointer_drift_block_current_layout(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            flowguard_root = self._create_current_layout(root)
            manifest_path = flowguard_root / "layout.toml"
            text = manifest_path.read_text(encoding="utf-8")
            manifest_path.write_text(
                text.replace('project_identity = "', 'project_identity = "wrong-'),
                encoding="utf-8",
            )

            report = audit_project_layout(root)

            codes = {finding.code for finding in report.findings}
            self.assertIn("layout_project_identity_mismatch", codes)


if __name__ == "__main__":
    unittest.main()
