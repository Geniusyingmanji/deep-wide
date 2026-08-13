from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import diagnose_v25292_monotone_unknown_fill_eligibility as target  # noqa: E402


REAL_GIT = target.base._git


class V25292MonotoneUnknownFillEligibilityDiagnosisTests(unittest.TestCase):
    @staticmethod
    def _clean_git(*args: str) -> str:
        if args in {("rev-parse", "HEAD"), ("rev-parse", "target/main")}:
            return "a" * 40
        if args == ("status", "--porcelain"):
            return ""
        return REAL_GIT(*args)

    @classmethod
    def setUpClass(cls) -> None:
        with mock.patch.object(
            target.base, "_git", side_effect=cls._clean_git
        ):
            cls.value = target.build_diagnosis(now=1, tracked=False)

    def test_fixed_inputs_parent_authorities_and_result_vector_are_exact(self) -> None:
        self.assertEqual(
            target._fixed_inputs(),
            {str(path): digest for path, digest in target.FIXED_INPUTS.items()},
        )
        authority = target._parent_barrier()
        self.assertTrue(authority["build"]["audit_valid"])
        self.assertTrue(authority["forward"]["audit_valid"])
        vector = target._result_vector()
        self.assertEqual(len(vector), 220)
        self.assertEqual(
            target.seal.payload_sha256(vector),
            target.EXPECTED_RESULT_VECTOR_SHA256,
        )

    def test_prepage_eligibility_is_exact_nonzero_but_only_an_upper_bound(self) -> None:
        observed = self.value["observed_legacy_aggregate"]
        self.assertEqual(observed["parent_eligible_tasks"], 218)
        self.assertEqual(observed["tasks_with_unknown"], 42)
        self.assertEqual(observed["prepage_eligible_tasks"], 41)
        self.assertEqual(observed["total_unknown_cells"], 1465)
        self.assertEqual(observed["legacy_telemetry_unknown_cells"], 1424)
        self.assertEqual(observed["unknown_count_exact_parity_tasks"], 217)
        self.assertEqual(observed["unknown_count_semantic_difference_tasks"], 3)
        self.assertFalse(
            observed["legacy_telemetry_used_for_v25290_eligibility"]
        )
        self.assertTrue(
            observed["prepage_eligible_is_upper_bound_not_full_eligibility"]
        )
        self.assertFalse(observed["full_v25290_eligibility_reconstructable"])
        self.assertFalse(observed["supported_unknown_fill_observed"])
        self.assertFalse(observed["attributable_prediction_change_observed"])

    def test_historical_zero_conversion_is_risk_not_transferred_effect(self) -> None:
        risk = self.value["historical_conversion_risk"]
        self.assertEqual(risk["valid_bundles"], 160)
        self.assertEqual(risk["usable_pages"], 956)
        self.assertEqual(risk["logical_revision_calls"], 153)
        self.assertEqual(risk["prediction_changed_tasks"], 0)
        self.assertFalse(
            risk["same_runtime_candidate_or_support_threshold_as_v25290"]
        )
        self.assertFalse(
            risk["transferred_as_v25290_event_rate_or_quality_effect"]
        )

    def test_diagnosis_is_aggregate_only_label_blind_and_design_only(self) -> None:
        value = self.value
        self.assertEqual(target.validate_diagnosis(value), value)
        self.assertTrue(value["diagnosis_valid"])
        self.assertEqual(value["findings"], [])
        encoded = json.dumps(value, ensure_ascii=False, sort_keys=True)
        self.assertIsNone(target.OPAQUE.search(encoded))
        self.assertNotIn("| Name |", encoded)
        policy = value["content_policy"]
        self.assertFalse(policy["visible_task_files_opened"])
        self.assertFalse(
            policy[
                "mapping_gold_category_question_type_split_evaluator_metric_score_or_reward_opened"
            ]
        )
        authorization = value["authorization"]
        self.assertTrue(
            authorization[
                "fresh_disjoint_shared_prefix_external_population_and_protocol_design"
            ]
        )
        self.assertFalse(authorization["external_activation_or_launch"])
        self.assertFalse(authorization["postfreeze_evaluator"])
        self.assertFalse(
            authorization["deepwidebench_dev64_exact220_forward_or_evaluator"]
        )

    def test_resealed_count_inference_history_policy_launch_or_hidden_tamper_fails(self) -> None:
        for kind in (
            "count",
            "full_inference",
            "history_transfer",
            "policy",
            "launch",
            "source",
            "check_hidden",
        ):
            changed = copy.deepcopy(self.value)
            if kind == "count":
                changed["observed_legacy_aggregate"]["prepage_eligible_tasks"] = 42
            elif kind == "full_inference":
                changed["decision"][
                    "full_page_prefix_and_prompt_eligibility_established"
                ] = True
            elif kind == "history_transfer":
                changed["historical_conversion_risk"][
                    "transferred_as_v25290_event_rate_or_quality_effect"
                ] = True
            elif kind == "policy":
                changed["content_policy"]["visible_task_files_opened"] = True
            elif kind == "launch":
                changed["authorization"]["external_activation_or_launch"] = True
            elif kind == "source":
                changed["source_hashes"][str(target.SOURCE)] = "0" * 64
            else:
                changed["checks"]["hidden"] = True
            changed.pop("diagnosis_payload_sha256")
            changed["diagnosis_payload_sha256"] = target.seal.payload_sha256(
                changed
            )
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_diagnosis(changed)

    def test_diagnoser_has_no_network_model_search_or_evaluator_call(self) -> None:
        source = (ROOT / target.SOURCE).read_text(encoding="utf-8")
        for forbidden in (
            "HardTotalWallResponsesClient(",
            "AzureNativeSearchClient(",
            "requests.",
            "urlopen(",
            "run_official_eval_local",
            ".complete(",
            "search_many(",
            "fetch_urls(",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
