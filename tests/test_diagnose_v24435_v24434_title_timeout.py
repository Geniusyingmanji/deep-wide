from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24320_forward_contract import payload_sha256  # noqa: E402
from scripts import diagnose_v24435_v24434_title_timeout as target  # noqa: E402


class V24435TitleTimeoutDiagnosisTests(unittest.TestCase):
    def build_valid(self) -> dict:
        with (
            patch.object(target.base, "_tracked", return_value=True),
            patch.object(
                target.base,
                "_git",
                side_effect=lambda *args: "a" * 40
                if args[:2] == ("rev-parse", "HEAD")
                or args[:2] == ("rev-parse", "target/main")
                else "",
            ),
            patch.object(
                target, "protected_watcher_snapshot", return_value=target.EXPECTED_WATCHERS
            ),
            patch.object(target, "lease_observation", return_value={"active": False}),
        ):
            value = target.build_report(now=0)
        target.validate_report(value)
        return value

    def test_real_parent_counts_separate_timeout_and_title_conversion(self) -> None:
        value = self.build_valid()
        observed = value["public_observation"]
        diagnosis = value["diagnosis"]
        self.assertEqual(observed["success_tasks"], 12)
        self.assertEqual(observed["parent_hard_timeout_tasks"], 4)
        self.assertEqual(observed["slot_timeouts"], 0)
        self.assertEqual(observed["title_unique_anchor_pages"], 17)
        self.assertEqual(observed["active_pages"], 20)
        self.assertEqual(observed["title_projections"], 0)
        self.assertGreater(
            observed["title_positive_information_gain_total_nats"], 0
        )
        self.assertEqual(observed["title_decision_credit_total_nats"], 0)
        self.assertFalse(diagnosis["exact_blocking_child_effect_identifiable"])
        self.assertFalse(
            diagnosis[
                "narrative_label_present_vs_parser_false_negative_identifiable"
            ]
        )

    def test_only_two_append_only_designs_are_authorized(self) -> None:
        authorization = self.build_valid()["authorization"]
        self.assertTrue(authorization["bounded_per_effect_timeout_design"])
        self.assertTrue(authorization["counts_only_narrative_label_taxonomy_design"])
        for name in (
            "external_probe_launch",
            "paired_dev64",
            "exact220",
            "evaluator",
            "leaderboard_or_sota",
        ):
            self.assertFalse(authorization[name])

    def test_resealed_identifiability_or_authorization_tamper_fails(self) -> None:
        for field in ("identifiable", "launch"):
            with self.subTest(field=field):
                value = self.build_valid()
                if field == "identifiable":
                    value["diagnosis"]["exact_blocking_child_effect_identifiable"] = True
                else:
                    value["authorization"]["external_probe_launch"] = True
                value.pop("diagnosis_payload_sha256")
                value["diagnosis_payload_sha256"] = payload_sha256(value)
                with self.assertRaises(RuntimeError):
                    target.validate_report(value)

    def test_untracked_or_dirty_source_fails_closed(self) -> None:
        with (
            patch.object(target.base, "_tracked", return_value=False),
            patch.object(
                target.base,
                "_git",
                side_effect=lambda *args: "dirty"
                if args == ("status", "--porcelain")
                else "a" * 40,
            ),
            patch.object(
                target, "protected_watcher_snapshot", return_value=target.EXPECTED_WATCHERS
            ),
            patch.object(target, "lease_observation", return_value={"active": False}),
        ):
            value = target.build_report(now=0)
        self.assertFalse(value["diagnosis_valid"])
        self.assertFalse(value["authorization"]["bounded_per_effect_timeout_design"])
        self.assertFalse(
            value["authorization"]["counts_only_narrative_label_taxonomy_design"]
        )


if __name__ == "__main__":
    unittest.main()
