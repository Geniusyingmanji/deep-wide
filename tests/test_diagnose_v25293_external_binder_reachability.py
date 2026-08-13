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

from scripts import diagnose_v25293_external_binder_reachability as target  # noqa: E402


REAL_GIT = target.base._git


class V25293ExternalBinderReachabilityDiagnosisTests(unittest.TestCase):
    @staticmethod
    def _clean_git(*args: str) -> str:
        if args in {("rev-parse", "HEAD"), ("rev-parse", "target/main")}:
            return "a" * 40
        if args == ("status", "--porcelain"):
            return ""
        return REAL_GIT(*args)

    @classmethod
    def setUpClass(cls) -> None:
        with mock.patch.object(target.base, "_git", side_effect=cls._clean_git):
            cls.value = target.build_diagnosis(now=1, tracked=False)

    def test_fixed_inputs_and_parent_barrier_are_exact(self) -> None:
        self.assertEqual(
            target._fixed_inputs(),
            {str(path): digest for path, digest in target.FIXED_INPUTS.items()},
        )
        parent = target._parent_barrier()
        self.assertTrue(parent["diagnosis_valid"])
        self.assertEqual(parent["findings"], [])

    def test_rendered_worldbank_pages_have_nonzero_mechanical_reach(self) -> None:
        observed = self.value["worldbank_observed"]["representations"]
        self.assertEqual(observed, target.EXPECTED_WORLD_BANK)
        parent = observed["rendered_markdown"]["parent_30k"]
        candidate = observed["rendered_markdown"]["target_value_30k"]
        self.assertEqual(parent["tasks_with_unique_nonconflicting_support"], 9)
        self.assertEqual(parent["cells_with_unique_nonconflicting_support"], 128)
        self.assertEqual(candidate["tasks_with_unique_nonconflicting_support"], 10)
        self.assertEqual(candidate["cells_with_unique_nonconflicting_support"], 136)

    def test_raw_json_is_zero_and_is_not_misreported_as_quality(self) -> None:
        observed = self.value["worldbank_observed"]
        raw = observed["representations"]["raw_official_json"]
        self.assertEqual(raw, target.EXPECTED_WORLD_BANK["raw_official_json"])
        self.assertFalse(observed["actual_third_slot_proposal_replayed"])
        self.assertFalse(observed["actual_supported_fill_observed"])
        self.assertFalse(observed["actual_candidate_prediction_change_observed"])

    def test_pypi_is_nonreplayable_but_not_intrinsically_rejected(self) -> None:
        observed = self.value["pypi_observed"]
        self.assertFalse(observed["same_forward_raw_response_bytes_persisted"])
        self.assertFalse(observed["binder_reachability_reconstructable"])
        self.assertFalse(observed["domain_intrinsically_rejected"])
        decision = self.value["decision"]
        self.assertEqual(
            decision["next_design_domain"],
            "world_bank_official_json_to_frozen_markdown",
        )
        self.assertFalse(
            decision["historical_correctness_or_per_task_score_used_for_domain_selection"]
        )

    def test_output_is_aggregate_only_label_blind_and_design_only(self) -> None:
        value = self.value
        self.assertEqual(target.validate_diagnosis(value), value)
        self.assertTrue(value["diagnosis_valid"])
        self.assertEqual(value["findings"], [])
        encoded = json.dumps(value, ensure_ascii=False, sort_keys=True)
        self.assertIsNone(target.parent.OPAQUE.search(encoded))
        self.assertNotIn("https://", encoded)
        policy = value["content_policy"]
        self.assertFalse(
            policy[
                "mapping_gold_category_question_type_split_evaluator_metric_score_reward_or_correctness_opened"
            ]
        )
        authorization = value["authorization"]
        self.assertTrue(
            authorization["fresh_disjoint_worldbank_shared_prefix_protocol_design"]
        )
        self.assertFalse(authorization["population_selection_or_freeze"])
        self.assertFalse(authorization["external_activation_or_launch"])
        self.assertFalse(authorization["postfreeze_evaluator"])

    def test_resealed_reachability_effect_pypi_policy_or_authority_tamper_fails(self) -> None:
        for kind in ("reach", "effect", "pypi", "policy", "authority", "hidden"):
            changed = copy.deepcopy(self.value)
            if kind == "reach":
                changed["worldbank_observed"]["representations"][
                    "rendered_markdown"
                ]["parent_30k"]["cells_with_unique_nonconflicting_support"] = 129
            elif kind == "effect":
                changed["worldbank_observed"][
                    "actual_candidate_prediction_change_observed"
                ] = True
            elif kind == "pypi":
                changed["pypi_observed"][
                    "same_forward_raw_response_bytes_persisted"
                ] = True
            elif kind == "policy":
                changed["content_policy"][
                    "historical_per_task_correctness_used_for_selection_or_routing"
                ] = True
            elif kind == "authority":
                changed["authorization"]["external_activation_or_launch"] = True
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
            "requests.",
            "urlopen(",
            "HardTotalWallResponsesClient(",
            "AzureNativeSearchClient(",
            "run_official_eval_local",
            ".complete(",
            "search_many(",
            "fetch_urls(",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
