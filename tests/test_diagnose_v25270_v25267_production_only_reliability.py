from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25267_production_only_exact220_contract as contract  # noqa: E402
from scripts import diagnose_v25270_v25267_production_only_reliability as target  # noqa: E402


class V25270V25267ProductionOnlyReliabilityDiagnosisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = target.build_diagnosis(now=1, require_clean=False)

    def test_frozen_outcome_and_stage_aggregate(self) -> None:
        aggregate = self.value["aggregate"]
        self.assertEqual(aggregate["fixed_task_denominator"], 220)
        self.assertEqual(
            aggregate["outcome_counts"],
            {
                "outer_failure": 11,
                "completed_fallback": 7,
                "completed_model_generated": 202,
            },
        )
        self.assertEqual(
            aggregate["outer_failure_type_counts"], {"ProductionOnlyStageError": 11}
        )
        self.assertEqual(
            aggregate["stage_failure_stage_type_counts"],
            {"sparse_production:ValueError": 11},
        )
        self.assertEqual(aggregate["budget_rejection_tasks"], 0)

    def test_outer_failure_is_mostly_post_effect_internal_validation(self) -> None:
        aggregate = self.value["aggregate"]
        self.assertEqual(
            aggregate["outer_failure_tasks_with_all_model_requests_successful"], 11
        )
        self.assertEqual(aggregate["outer_failure_tasks_with_three_model_successes"], 10)
        self.assertEqual(aggregate["outer_failure_tasks_with_zero_health_event"], 9)
        self.assertEqual(
            aggregate["effect_signature_counts_by_outcome"]["outer_failure"],
            {"q4/f10/m1": 1, "q4/f10/m3": 9, "q4/f11/m3": 1},
        )
        self.assertTrue(
            self.value["diagnosis"][
                "most_outer_failures_are_post_effect_internal_validation_failures_not_transport_failures"
            ]
        )

    def test_completed_fallbacks_are_separate_and_finite(self) -> None:
        aggregate = self.value["aggregate"]
        self.assertEqual(
            aggregate["completed_failure_type_counts"]["production"],
            {"ModelRequestError": 2, "ValueError": 5},
        )
        self.assertEqual(
            aggregate["completed_failure_type_counts"]["post_effect"],
            {"ValueError": 1},
        )
        self.assertEqual(
            aggregate["completed_receipt_flag_totals"]["production_fallback_used"], 7
        )
        self.assertEqual(
            aggregate["effect_signature_counts_by_outcome"]["completed_fallback"],
            {"q4/f10/m3": 7},
        )

    def test_health_events_do_not_equal_failed_tasks(self) -> None:
        aggregate = self.value["aggregate"]
        self.assertEqual(sum(aggregate["terminal_effect_health_totals"].values()), 19)
        self.assertEqual(aggregate["tasks_with_any_health_event"], 18)
        self.assertEqual(
            aggregate["tasks_with_any_health_event_by_outcome"],
            {
                "outer_failure": 2,
                "completed_fallback": 3,
                "completed_model_generated": 13,
            },
        )

    def test_scanner_does_not_materialize_task_content(self) -> None:
        line = next(
            line
            for line in (ROOT / contract.RUNTIME_RESULTS)
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip()
        )
        safe = target.safe_row(line)
        for forbidden in (
            "opaque_id",
            "question",
            "prediction",
            "runtime_result",
            "pages",
            "score",
            "gold",
        ):
            self.assertNotIn(forbidden, safe)
        self.assertTrue(set(target.SAFE_TOP_LEVEL_MEMBERS).issubset(safe))

    def test_added_member_fails_closed_without_selecting_its_value(self) -> None:
        line = next(
            line
            for line in (ROOT / contract.RUNTIME_RESULTS)
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip()
        )
        changed = line.rstrip()[:-1] + ',"unexpected":{"question_type":"forbidden"}}'
        with self.assertRaises(ValueError):
            target.safe_row(changed)

    def test_resealed_count_credit_authorization_or_conclusion_tamper_fails(self) -> None:
        for kind in ("count", "health", "credit", "authorization", "conclusion"):
            changed = copy.deepcopy(self.value)
            if kind == "count":
                changed["aggregate"]["outcome_counts"]["outer_failure"] = 10
            elif kind == "health":
                changed["aggregate"]["terminal_effect_health_totals"][
                    "search_transport_failures"
                ] += 1
            elif kind == "credit":
                changed["entropy_or_information_gain_assigns_signed_credit"] = True
            elif kind == "authorization":
                changed["authorization"]["external_forward_or_new_deepwidebench_rollout"] = True
            else:
                changed["diagnosis"][
                    "pre_checkpoint_failure_must_remain_fail_closed"
                ] = False
            changed.pop("diagnosis_payload_sha256")
            changed["diagnosis_payload_sha256"] = contract.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_diagnosis(changed)

    def test_source_has_no_network_evaluator_or_process_capability(self) -> None:
        source = (ROOT / target.SOURCE).read_text(encoding="utf-8")
        for forbidden in (
            "import requests",
            "import subprocess",
            "from urllib",
            "urlopen(",
            "socket.",
            "Popen(",
            "run_official_eval_local",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
