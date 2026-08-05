from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import audit_v24531_invalid_callback_recursion as target  # noqa: E402


class V24531InvalidCallbackRecursionAuditTests(unittest.TestCase):
    def test_frozen_start_future_absence_and_replay_block_are_real(self) -> None:
        self.assertTrue(target._frozen_start_valid())
        self.assertTrue(target._future_absent())
        self.assertTrue(target._source_drift_blocks_replay())
        self.assertTrue(target._no_active_v24531_process())

    def test_clean_quarantine_authorizes_fresh_design_only(self) -> None:
        def git(*args: str) -> str:
            return "" if args == ("status", "--porcelain") else "a" * 40

        with (
            patch.object(target, "_frozen_start_valid", return_value=True),
            patch.object(target, "_future_absent", return_value=True),
            patch.object(target, "_source_drift_blocks_replay", return_value=True),
            patch.object(target, "_no_active_v24531_process", return_value=True),
            patch.object(target.common, "_lease_inactive", return_value=True),
            patch.object(target.common, "_watcher", return_value=True),
            patch.object(target.common, "_git", side_effect=git),
            patch.object(target.common, "_tracked", return_value=True),
        ):
            value = target.build_audit(now=0)
        self.assertEqual(value["findings"], [])
        self.assertTrue(value["audit_valid"])
        self.assertFalse(
            value["authorization"]["same_population_resume_retry_or_rerun"]
        )
        self.assertTrue(
            value["authorization"]["fresh_disjoint_successor_protocol_design"]
        )
        self.assertFalse(value["authorization"]["fresh_successor_launch"])
        self.assertFalse(value["authorization"]["paired_dev64_or_exact220"])
        self.assertEqual(value["population"]["next_prior_question_count"], 380)
        self.assertEqual(value["population"]["next_prior_entity_count"], 3040)

    def test_missing_start_result_presence_or_replay_gap_fails_closed(self) -> None:
        cases = (
            ("start", "v24531_frozen_execution_start_drifted"),
            ("future", "v24531_untrusted_future_surface_present"),
            ("replay", "v24531_same_population_replay_not_cryptographically_blocked"),
            ("process", "v24531_process_still_active"),
        )
        for mode, expected in cases:
            with self.subTest(mode=mode):
                def git(*args: str) -> str:
                    return "" if args == ("status", "--porcelain") else "a" * 40

                with (
                    patch.object(
                        target, "_frozen_start_valid", return_value=mode != "start"
                    ),
                    patch.object(
                        target, "_future_absent", return_value=mode != "future"
                    ),
                    patch.object(
                        target,
                        "_source_drift_blocks_replay",
                        return_value=mode != "replay",
                    ),
                    patch.object(
                        target,
                        "_no_active_v24531_process",
                        return_value=mode != "process",
                    ),
                    patch.object(target.common, "_lease_inactive", return_value=True),
                    patch.object(target.common, "_watcher", return_value=True),
                    patch.object(target.common, "_git", side_effect=git),
                    patch.object(target.common, "_tracked", return_value=True),
                ):
                    value = target.build_audit(now=0)
                self.assertIn(expected, value["findings"])
                self.assertFalse(value["audit_valid"])

    def test_lease_watcher_git_and_tracking_fail_closed(self) -> None:
        cases = (
            ("lease", "shared_api_lease_active"),
            ("watcher", "protected_watcher_identity_drifted"),
            ("dirty", "incident_source_worktree_not_clean"),
            ("unpushed", "incident_source_commit_not_pushed"),
            ("untracked", "incident_source_not_tracked"),
        )
        for mode, expected in cases:
            with self.subTest(mode=mode):
                def git(*args: str) -> str:
                    if args == ("status", "--porcelain"):
                        return "M x" if mode == "dirty" else ""
                    if args == ("rev-parse", "HEAD"):
                        return "a" * 40
                    return "b" * 40 if mode == "unpushed" else "a" * 40

                with (
                    patch.object(target, "_frozen_start_valid", return_value=True),
                    patch.object(target, "_future_absent", return_value=True),
                    patch.object(target, "_source_drift_blocks_replay", return_value=True),
                    patch.object(target, "_no_active_v24531_process", return_value=True),
                    patch.object(
                        target.common,
                        "_lease_inactive",
                        return_value=mode != "lease",
                    ),
                    patch.object(
                        target.common,
                        "_watcher",
                        return_value=mode != "watcher",
                    ),
                    patch.object(target.common, "_git", side_effect=git),
                    patch.object(
                        target.common,
                        "_tracked",
                        return_value=mode != "untracked",
                    ),
                ):
                    value = target.build_audit(now=0)
                self.assertIn(expected, value["findings"])
                self.assertFalse(value["audit_valid"])

    def test_runtime_and_audit_sources_are_label_blind_and_secret_free(self) -> None:
        accesses, imports = target.common.ast_findings(target.RUNNER)
        secret_hits = [
            str(path)
            for path in target.SOURCES
            if target.common.SECRET.search(
                target.common._ordinary(path).read_text(encoding="utf-8")
            )
        ]
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])
        self.assertEqual(secret_hits, [])


if __name__ == "__main__":
    unittest.main()
