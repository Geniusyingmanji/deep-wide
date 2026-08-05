from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import audit_v24543_invalid_callback_recursion as target  # noqa: E402


class V24543InvalidCallbackRecursionAuditTests(unittest.TestCase):
    def test_frozen_start_absence_gap_and_process_are_real(self) -> None:
        self.assertTrue(target._frozen_start_valid())
        self.assertTrue(target._future_absent())
        self.assertTrue(target._historical_callback_gap())
        self.assertTrue(target._no_active_v24543_process())

    def build(self, **changes):
        settings = {"start": True, "future": True, "gap": True, "process": True, "lease": True, "watcher": True, "tracked": True}
        settings.update(changes)
        def git(*args: str) -> str:
            return "" if args == ("status", "--porcelain") else "a" * 40
        with (
            patch.object(target, "_frozen_start_valid", return_value=settings["start"]),
            patch.object(target, "_future_absent", return_value=settings["future"]),
            patch.object(target, "_historical_callback_gap", return_value=settings["gap"]),
            patch.object(target, "_no_active_v24543_process", return_value=settings["process"]),
            patch.object(target.common, "_lease_inactive", return_value=settings["lease"]),
            patch.object(target.common, "_watcher", return_value=settings["watcher"]),
            patch.object(target.common, "_git", side_effect=git),
            patch.object(target.common, "_tracked", return_value=settings["tracked"]),
        ):
            return target.build_audit(now=0)

    def test_clean_quarantine_authorizes_fresh_design_only(self) -> None:
        value = self.build()
        self.assertEqual(value["findings"], [])
        self.assertTrue(value["audit_valid"])
        self.assertFalse(value["authorization"]["same_population_resume_retry_or_rerun"])
        self.assertTrue(value["authorization"]["fresh_disjoint_successor_protocol_design"])
        self.assertFalse(value["authorization"]["fresh_successor_activation_or_launch"])
        self.assertEqual(value["population"]["next_prior_question_count"], 420)
        self.assertEqual(value["population"]["next_prior_entity_count"], 3360)
        self.assertTrue(value["incident"]["capability_reprojection_fix_reached"])
        self.assertFalse(value["incident"]["external_effect_counts_recoverable"])

    def test_control_runtime_and_environment_gaps_fail_closed(self) -> None:
        cases = (
            ({"start": False}, "v24543_frozen_execution_start_drifted"),
            ({"future": False}, "v24543_untrusted_future_surface_present"),
            ({"gap": False}, "v24543_historical_callback_recursion_gap_not_bound"),
            ({"process": False}, "v24543_process_still_active"),
            ({"lease": False}, "shared_api_lease_active"),
            ({"watcher": False}, "protected_watcher_identity_drifted"),
            ({"tracked": False}, "quarantine_source_not_tracked"),
        )
        for changes, expected in cases:
            with self.subTest(expected=expected):
                value = self.build(**changes)
                self.assertIn(expected, value["findings"])
                self.assertFalse(value["audit_valid"])

    def test_runtime_and_audit_sources_are_label_blind_and_secret_free(self) -> None:
        accesses, imports = target.common.ast_findings(target.RUNNER)
        secret_hits = [str(path) for path in target.SOURCES if target.common.SECRET.search(target.common._ordinary(path).read_text(encoding="utf-8"))]
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])
        self.assertEqual(secret_hits, [])

    def test_publisher_is_create_only(self) -> None:
        with self.assertRaises(FileExistsError):
            target.publish_new(target.PROTOCOL, {})


if __name__ == "__main__":
    unittest.main()
