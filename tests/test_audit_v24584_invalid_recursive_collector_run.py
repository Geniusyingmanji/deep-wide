from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import audit_v24584_invalid_recursive_collector_run as target  # noqa: E402


class V24584InvalidRecursiveCollectorRunAuditTests(unittest.TestCase):
    def test_frozen_start_absence_gap_and_process_are_real(self) -> None:
        self.assertTrue(target._frozen_start_valid())
        self.assertTrue(target._future_absent())
        self.assertTrue(target._historical_recursive_binding_gap())
        self.assertTrue(target._no_active_process())

    def build(self, **changes):
        settings = {
            "start": True,
            "future": True,
            "gap": True,
            "process": True,
            "lease": True,
            "watcher": True,
            "tracked": True,
        }
        settings.update(changes)

        def git(*args: str) -> str:
            return "" if args == ("status", "--porcelain") else "a" * 40

        with (
            patch.object(target, "_frozen_start_valid", return_value=settings["start"]),
            patch.object(target, "_future_absent", return_value=settings["future"]),
            patch.object(
                target,
                "_historical_recursive_binding_gap",
                return_value=settings["gap"],
            ),
            patch.object(target, "_no_active_process", return_value=settings["process"]),
            patch.object(target.common, "_lease_inactive", return_value=settings["lease"]),
            patch.object(target.common, "_watcher", return_value=settings["watcher"]),
            patch.object(target.common, "_git", side_effect=git),
            patch.object(target.common, "_tracked", return_value=settings["tracked"]),
        ):
            return target.build_audit(now=0)

    def test_clean_quarantine_authorizes_repair_design_only(self) -> None:
        value = self.build()
        self.assertEqual(value["findings"], [])
        self.assertTrue(value["audit_valid"])
        self.assertFalse(
            value["authorization"]["same_population_resume_retry_rerun_or_evaluation"]
        )
        self.assertTrue(
            value["authorization"]["recursive_collector_binding_repair_design"]
        )
        self.assertFalse(
            value["authorization"]["fresh_disjoint_successor_protocol_design"]
        )
        self.assertEqual(value["population"]["next_prior_question_count"], 460)
        self.assertEqual(value["population"]["next_prior_entity_count"], 3680)
        self.assertFalse(value["incident"]["external_effect_counts_recoverable"])

    def test_control_runtime_and_environment_gaps_fail_closed(self) -> None:
        cases = (
            ({"start": False}, "v24583_frozen_execution_start_drifted"),
            ({"future": False}, "v24583_untrusted_future_surface_present"),
            ({"gap": False}, "v24583_historical_recursive_collector_gap_not_bound"),
            ({"process": False}, "v24583_process_still_active"),
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

    def test_incident_is_no_result_and_no_quality_claim(self) -> None:
        incident = self.build()["incident"]
        self.assertEqual(incident["terminal_exception_type"], "RecursionError")
        self.assertTrue(incident["collector_project_reentered_itself"])
        self.assertFalse(incident["public_result_published"])
        self.assertFalse(incident["prededup_mechanism_result_available"])
        self.assertFalse(incident["score_available"])
        self.assertFalse(incident["quality_or_sota_claim_allowed"])

    def test_publisher_is_create_only(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "results") as directory:
            path = Path(directory) / "nested" / "audit.json"
            target.publish_new(path, {})
            with self.assertRaises(FileExistsError):
                target.publish_new(path, {})


if __name__ == "__main__":
    unittest.main()
