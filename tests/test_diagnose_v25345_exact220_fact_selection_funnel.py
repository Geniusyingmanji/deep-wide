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
from scripts import diagnose_v25345_exact220_fact_selection_funnel as target  # noqa: E402


class V25345Exact220FactSelectionFunnelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.aggregate = target._aggregate()

    def test_three_complete_quality_summaries(self) -> None:
        quality = self.aggregate["quality"]
        self.assertEqual(set(quality), {"v24857", "v25267", "v25342"})
        self.assertEqual(quality["v24857"]["whole_table_successes"], 9)
        self.assertEqual(quality["v25267"]["whole_table_successes"], 5)
        self.assertEqual(quality["v25342"]["whole_table_successes"], 6)
        self.assertAlmostEqual(
            quality["v25342"]["quality_composite"], 0.4362022453314952
        )

    def test_v24857_missing_instrumentation_is_not_reported_as_zero(self) -> None:
        funnel = self.aggregate["fact_selection_funnel"]["v24857"]
        self.assertEqual(funnel["record_observation_instrumentation"], "not_instrumented")
        self.assertFalse(funnel["record_or_observation_zero_claimed"])
        self.assertNotIn("retained_records", funnel)
        self.assertEqual(funnel["successful_queries"], 866)
        self.assertEqual(funnel["fetches_attempted"], 2047)

    def test_comparable_record_funnels_show_conversion_bottleneck(self) -> None:
        funnels = self.aggregate["fact_selection_funnel"]
        old = funnels["v25267"]
        new = funnels["v25342"]
        self.assertEqual(old["observable_parent_funnel_tasks"], 208)
        self.assertEqual(new["observable_parent_funnel_tasks"], 209)
        self.assertEqual(old["funnel_count_totals"]["projected_pages"], 1444)
        self.assertEqual(new["funnel_count_totals"]["projected_pages"], 1506)
        self.assertEqual(old["funnel_count_totals"]["retained_records"], 0)
        self.assertEqual(new["funnel_count_totals"]["retained_records"], 1)
        self.assertEqual(new["funnel_count_totals"]["retained_observations"], 2)
        self.assertEqual(
            new["funnel_boolean_task_counts"]["attributable_prediction_change"], 0
        )
        self.assertEqual(new["checkpoint_recovery_event_tasks"], 11)

    def test_revision_history_does_not_support_direct_fourth_call(self) -> None:
        history = self.aggregate["revision_history"]
        self.assertEqual(
            history["v25137_sparse_revision"],
            {
                "provider_forward_tasks": 6,
                "provider_valid_tasks": 6,
                "attributable_prediction_changed_tasks": 1,
            },
        )
        self.assertEqual(
            history["v25141_targeted_revision"][
                "attributable_prediction_changed_tasks"
            ],
            0,
        )
        self.assertEqual(
            history["v25248_shadow_overshoot"][
                "attributable_prediction_changed_tasks"
            ],
            0,
        )
        self.assertFalse(history["direct_fourth_model_call_restoration_supported"])

    def test_safe_rows_do_not_materialize_private_task_content(self) -> None:
        for name, parser in (
            ("v25267", target.safe_v25267_row),
            ("v25342", target.safe_v25342_row),
        ):
            line = next(
                line
                for line in (ROOT / target.RUNS[name]["rows"])
                .read_text(encoding="utf-8")
                .splitlines()
                if line.strip()
            )
            safe = parser(line)
            for forbidden in (
                "opaque_id",
                "question",
                "prediction",
                "runtime_result",
                "page",
                "url",
                "score",
                "gold",
            ):
                self.assertNotIn(forbidden, safe)

    def test_added_top_level_member_fails_closed(self) -> None:
        line = next(
            line
            for line in (ROOT / target.RUNS["v25342"]["rows"])
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip()
        )
        changed = line.rstrip()[:-1] + ',"unexpected":{"question_type":"forbidden"}}'
        with self.assertRaises(ValueError):
            target.safe_v25342_row(changed)

    def test_resealed_aggregate_credit_authorization_or_claim_tamper_fails(self) -> None:
        if target.EXPECTED_AGGREGATE_SHA256 == "TO_BE_FROZEN":
            self.skipTest("aggregate hash is frozen after independent reproduction")
        value = target.build_diagnosis(now=1, require_clean=False)
        for kind in ("aggregate", "credit", "authorization", "diagnosis"):
            changed = copy.deepcopy(value)
            if kind == "aggregate":
                changed["aggregate"]["fact_selection_funnel"]["v25342"][
                    "funnel_count_totals"
                ]["retained_records"] = 2
            elif kind == "credit":
                changed["entropy_or_information_gain_assigns_signed_credit"] = True
            elif kind == "authorization":
                changed["authorization"][
                    "external_forward_or_new_deepwidebench_rollout"
                ] = True
            else:
                changed["diagnosis"][
                    "page_to_record_to_admissible_observation_is_the_primary_observed_bottleneck"
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
