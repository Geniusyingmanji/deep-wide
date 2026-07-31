from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.publish_v24210_search_component import (
    build_candidate_files,
    build_selected_publication,
    parent_regression_contract,
    selected_parent_files,
)
from scripts.replay_v24201_repo_local_candidate_dag import build_replay


class PublishV24210SearchComponentTests(unittest.TestCase):
    def test_p12_scope_parent_is_schema70_and_target_is_schema86(self) -> None:
        order = {
            "baseline_name": "p12",
            "semantic_parent_variant": "selected_scope_candidate",
            "target_state_schema_version": 86,
        }
        files, provenance = selected_parent_files(order, {}, {})
        _replay, maps = build_replay()
        self.assertEqual(files, maps["schema70"])
        self.assertEqual(provenance["schema"], "schema70")
        candidate, report = build_candidate_files(order, {}, {})
        self.assertEqual(report["parent_state_schema_version"], 70)
        self.assertEqual(report["target_state_schema_version"], 86)
        self.assertEqual(report["candidate_regular_file_count"], len(candidate))
        self.assertIn("src/deepwide_agent/v24179.py", candidate)
        self.assertIn(
            'source.count("membership_gap_query_plan"), 3',
            candidate["tests/test_v24179_predicate_fair_query_scheduler.py"],
        )
        modules, tests = parent_regression_contract(order, {})
        self.assertEqual(tests, 65)
        self.assertEqual(modules[-1], "tests.test_v24179_predicate_fair_query_scheduler")

    @staticmethod
    def _base() -> tuple[dict, dict, dict, dict]:
        selected = {"selected_payload_sha256": "s" * 64}
        order = {
            "decision_sha256": "d" * 64,
            "search_component_selected": True,
            "p12_scope_uses_historical_schema70_parent": False,
            "mainline_scope_is_zero_byte_markdown_alias": False,
        }
        markdown = {"publication_payload_sha256": "m" * 64}
        scope = {"publication_payload_sha256": "c" * 64}
        return selected, order, markdown, scope

    def test_no_go_retires_without_materialization(self) -> None:
        selected, order, markdown, scope = self._base()
        with mock.patch(
            "scripts.publish_v24210_search_component.file_sha256",
            return_value="f" * 64,
        ), mock.patch(
            "scripts.publish_v24210_search_component.materialize_candidate"
        ) as materialize:
            value = build_selected_publication(
                selected,
                order,
                markdown,
                scope,
                "complete_search_yield_no_go",
                {"status": "complete_search_yield_no_go"},
                {"passed": False},
            )
        materialize.assert_not_called()
        self.assertTrue(value["search_component_retired"])
        self.assertFalse(value["search_component_published"])
        self.assertFalse(value["process_signal_restart_resume_rerun_skip_or_selective_retry"])
        self.assertFalse(value["benchmark_forward_or_full220_launch_allowed"])

    def test_incomplete_attempt_is_terminal_retirement(self) -> None:
        selected, order, markdown, scope = self._base()
        with mock.patch(
            "scripts.publish_v24210_search_component.file_sha256",
            return_value="f" * 64,
        ):
            value = build_selected_publication(
                selected,
                order,
                markdown,
                scope,
                "terminal_incomplete_attempt_no_rerun",
                {"status": "terminal_incomplete_attempt_no_rerun"},
                None,
            )
        self.assertEqual(
            value["publication_disposition"],
            "incomplete_attempt_component_retired_no_rerun",
        )
        self.assertTrue(value["search_component_retired"])

    def test_absent_search_is_content_free_noop(self) -> None:
        selected, order, markdown, scope = self._base()
        order["search_component_selected"] = False
        with mock.patch(
            "scripts.publish_v24210_search_component.file_sha256",
            return_value="f" * 64,
        ):
            value = build_selected_publication(
                selected,
                order,
                markdown,
                scope,
                "complete_search_yield_go",
                {"status": "complete_search_yield_go"},
                {"passed": True},
            )
        self.assertTrue(value["search_component_absent_noop"])
        self.assertIsNone(value["component_publication"])


if __name__ == "__main__":
    unittest.main()
