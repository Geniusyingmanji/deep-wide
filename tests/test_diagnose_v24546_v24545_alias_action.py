from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24320_forward_contract import payload_sha256  # noqa: E402
from scripts import diagnose_v24546_v24545_alias_action as target  # noqa: E402


class V24546AliasActionCorrelationDiagnosisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = target.build_diagnosis(now=0)

    def test_frozen_public_facts_are_exact(self) -> None:
        observed = self.value["observed"]
        self.assertEqual(observed["target_plan_tasks"], 7)
        self.assertEqual(observed["acquisition_activity_tasks"], 6)
        self.assertEqual(observed["targeted_usable_page_count"], 17)
        self.assertEqual(observed["targeted_new_observation_count"], 1)
        self.assertEqual(observed["alias_title_hit_lead_count"], 0)
        self.assertAlmostEqual(
            observed["raw_information_gain_nats"], 0.209371236041, places=12
        )
        self.assertEqual(observed["action_information_credit_nats"], 0)

    def test_task_level_correlation_is_not_invented(self) -> None:
        self.assertTrue(
            self.value["proved_inferences"][
                "at_least_one_task_added_a_targeted_observation"
            ]
        )
        self.assertTrue(
            self.value["proved_inferences"][
                "at_least_one_task_had_positive_raw_information_gain"
            ]
        )
        self.assertTrue(
            all(
                item is False
                for item in self.value[
                    "unrecoverable_from_frozen_public_aggregate"
                ].values()
            )
        )
        self.assertFalse(self.value["claims"]["alias_action_caused_information_gain"])

    def test_successor_is_append_only_query_blind_and_does_not_relax_credit(self) -> None:
        successor = self.value["successor_contract"]
        self.assertTrue(successor["append_only_new_version"])
        self.assertTrue(successor["query_text_must_not_establish_alias_hit"])
        self.assertFalse(
            successor[
                "alias_hint_itself_receives_vote_source_entropy_or_decision_credit"
            ]
        )
        self.assertTrue(
            successor[
                "preserve_source_posterior_margin_leave_one_out_safe_change_and_decision_credit_thresholds"
            ]
        )
        self.assertEqual(successor["next_population_prior_question_count"], 428)
        self.assertEqual(successor["next_population_prior_entity_count"], 3424)

    def test_resealed_inference_source_and_authorization_tamper_fail_closed(self) -> None:
        cases = (
            lambda value: value["unrecoverable_from_frozen_public_aggregate"].__setitem__(
                "new_observation_and_positive_raw_gain_occurred_on_same_task", True
            ),
            lambda value: value["successor_contract"].__setitem__(
                "query_text_must_not_establish_alias_hit", False
            ),
            lambda value: value["source_policy"].__setitem__(
                "temporary_execution_directory_opened", True
            ),
            lambda value: value["authorization"].__setitem__(
                "fresh_external_probe_launch", True
            ),
        )
        for alter in cases:
            with self.subTest(alter=alter):
                changed = copy.deepcopy(self.value)
                alter(changed)
                changed.pop("diagnosis_payload_sha256")
                changed["diagnosis_payload_sha256"] = payload_sha256(changed)
                with self.assertRaises(RuntimeError):
                    target.validate_diagnosis(changed)

    def test_runtime_source_is_label_blind(self) -> None:
        from scripts import audit_v24495_targeted_conversion_projection_build as audit

        accesses, imports = audit.ast_findings(
            Path("scripts/diagnose_v24546_v24545_alias_action.py")
        )
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])


if __name__ == "__main__":
    unittest.main()
