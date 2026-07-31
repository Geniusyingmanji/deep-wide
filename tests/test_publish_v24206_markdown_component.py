from __future__ import annotations

import ast
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.publish_v24206_markdown_component import (
    EXPECTED_TESTS,
    build_mainline_candidate_files,
    extend_identity_assertions,
    historical_p12_binding,
    materialize_mainline_candidate,
)


class PublishV24206MarkdownComponentTests(unittest.TestCase):
    EXPECTED_GUARDS = {
        "tests/test_v2406_integrated_bridge_completion.py": 1,
        "tests/test_v2407_integrated_anchor_completion.py": 1,
        "tests/test_v2408_integrated_fresh_stage_evidence.py": 1,
        "tests/test_v24104_integrated_scope_open_fallback.py": 2,
        "tests/test_v24108_integrated_post_verification_partial_release.py": 2,
        "tests/test_v2410_integrated_rank_slot_recovery.py": 3,
        "tests/test_v24127_integrated_exact_identity_merge.py": 2,
        "tests/test_v24132_integrated_membership_fresh_evidence.py": 2,
        "tests/test_v24144_integrated_p10_relation_aware.py": 2,
        "tests/test_v24149_integrated_combined_candidate.py": 2,
    }

    def test_joint_regression_counts_add_exact_markdown_suite(self) -> None:
        self.assertEqual(EXPECTED_TESTS, {"schema76": 118, "schema77": 127})

    def test_mainline_file_maps_have_exact_identity_hooks_and_no_other_components(
        self,
    ) -> None:
        for baseline, schema in (("schema76", 78), ("schema77", 79)):
            files, report = build_mainline_candidate_files(baseline)
            self.assertEqual(report["target_state_schema_version"], schema)
            self.assertTrue(
                report["target_pipeline_version"].endswith(
                    "-selected-markdown-rank-slot"
                )
            )
            self.assertTrue(report["mainline_scope_hook_preserved_exactly_once"])
            self.assertFalse(report["branch_scope_patch_or_alias_applied"])
            self.assertFalse(report["search_yield_or_entropy_implemented"])
            self.assertFalse(report["joint_package_built_or_materialized"])
            guards = dict(self.EXPECTED_GUARDS)
            if baseline == "schema77":
                guards[
                    "tests/test_v24172_integrated_predicate_completion_scheduler.py"
                ] = 2
            self.assertEqual(report["identity_guard_assertion_counts"], guards)
            self.assertIn("src/deepwide_agent/v24102.py", files)
            self.assertIn("tests/test_v24102_markdown_rank_slot.py", files)
            self.assertIn("tests/test_v24102_integrated_markdown_rank_slot.py", files)
            for relative, source in files.items():
                if relative.endswith(".py"):
                    ast.parse(source, filename=relative)

    def test_identity_assertion_extension_is_exact_and_tamper_sensitive(self) -> None:
        source = (
            "from runtime import PIPELINE_VERSION, STATE_SCHEMA_VERSION\n"
            "assert PIPELINE_VERSION == 'old'\n"
            "assert STATE_SCHEMA_VERSION in {1, 2}\n"
        )
        value, count = extend_identity_assertions(
            source, target_version="new", target_schema=3
        )
        self.assertEqual(count, 2)
        self.assertEqual(value.count("PIPELINE_VERSION == 'new'"), 2)
        self.assertEqual(value.count("STATE_SCHEMA_VERSION == 3"), 2)
        ast.parse(value)

        source = (
            "from runtime import PIPELINE_VERSION, STATE_SCHEMA_VERSION\n"
            "class T:\n"
            "    def check(self):\n"
            "        self.assertTrue(PIPELINE_VERSION.endswith('-old'))\n"
            "        self.assertIn(STATE_SCHEMA_VERSION, {1, 2})\n"
        )
        value, count = extend_identity_assertions(
            source, target_version="new", target_schema=3
        )
        self.assertEqual(count, 2)
        self.assertEqual(value.count("PIPELINE_VERSION == 'new'"), 2)
        self.assertEqual(value.count("STATE_SCHEMA_VERSION == 3"), 2)
        self.assertNotIn("{1, 2, 3}", value)
        ast.parse(value)

    def test_historical_p12_binding_is_byte_exact_and_nonmaterializing(self) -> None:
        value = historical_p12_binding()
        self.assertEqual(value["target_state_schema_version"], 69)
        self.assertTrue(value["historical_bytes_byte_exact"])
        self.assertFalse(value["candidate_root_created"])
        self.assertEqual(value["candidate_regular_file_count"], 47)

    def test_real_temp_materialization_runs_joint_schema76_regression(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            candidate = Path(directory) / "candidate"
            value = materialize_mainline_candidate("schema76", candidate)
            self.assertEqual(
                value["integrated_tests"]["tests_run"], EXPECTED_TESTS["schema76"]
            )
            self.assertTrue(value["candidate_regular_file_set_exact"])
            self.assertTrue(value["candidate_forward_execution_closure_exact"])
            self.assertFalse(value["benchmark_forward_or_full220_launch_allowed"])

    def test_real_temp_materialization_runs_joint_schema77_regression(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            candidate = Path(directory) / "candidate"
            value = materialize_mainline_candidate("schema77", candidate)
            self.assertEqual(
                value["integrated_tests"]["tests_run"], EXPECTED_TESTS["schema77"]
            )
            self.assertTrue(value["candidate_regular_file_set_exact"])
            self.assertTrue(value["candidate_forward_execution_closure_exact"])
            self.assertFalse(value["benchmark_forward_or_full220_launch_allowed"])

    def test_materialization_rolls_back_on_test_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            candidate = Path(directory) / "candidate"
            with mock.patch(
                "scripts.publish_v24206_markdown_component.run_integrated_tests",
                side_effect=RuntimeError("synthetic failure"),
            ):
                with self.assertRaisesRegex(RuntimeError, "synthetic failure"):
                    materialize_mainline_candidate("schema76", candidate)
            self.assertFalse(candidate.exists())


if __name__ == "__main__":
    unittest.main()
