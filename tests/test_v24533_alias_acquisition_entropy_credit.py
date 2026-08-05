from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24524_alias_title_integration import run_v24524_task  # noqa: E402
from deepwide_agent.v24529_alias_seeded_target_acquisition import (  # noqa: E402
    AliasSeededTargetAcquisition,
)
from deepwide_agent.v24515_neutral_cell_discovery_planner import (  # noqa: E402
    NeutralCellDiscoveryPlanner,
)
from deepwide_agent.v24533_alias_acquisition_entropy_credit import (  # noqa: E402
    build_action_credit_receipt,
    validate_action_credit_receipt,
)
from test_v24342_semantic_active_runtime import limits  # noqa: E402
from test_v24390_uncertainty_active_evidence_runtime import SEED  # noqa: E402
from test_v24412_receipt_snapshot_diagnosis import AdvancingClock  # noqa: E402
from test_v24524_alias_title_integration import TASK, clients  # noqa: E402


class V24533AliasAcquisitionEntropyCreditTests(unittest.TestCase):
    temporary: tempfile.TemporaryDirectory
    receipt: dict

    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        clock = AdvancingClock()
        model, search = clients(Path(cls.temporary.name), clock, mode="support")
        acquisition = AliasSeededTargetAcquisition()
        with NeutralCellDiscoveryPlanner(), acquisition:
            outcome = run_v24524_task(
                TASK,
                model=model,
                search=search,
                partition_seed_sha256=SEED,
                limits=limits(),
                monotonic=clock,
            )
        cls.receipt = build_action_credit_receipt(
            outcome.alias_title_result,
            acquisition.content_free_receipt(),
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def test_activity_without_targeted_observation_gets_zero_action_credit(self) -> None:
        receipt = self.receipt
        self.assertEqual(receipt["target_plan_count"], 1)
        self.assertGreater(receipt["alias_seeded_query_vector_calls"], 0)
        self.assertGreater(receipt["selected_lead_count"], 0)
        self.assertEqual(receipt["targeted_new_observation_count"], 0)
        self.assertEqual(receipt["action_information_credit_nats"], 0)
        self.assertEqual(receipt["action_epistemic_credit_nats"], 0)
        self.assertEqual(receipt["action_decision_credit_nats"], 0)

    def test_synthetic_valid_receipt_allocates_only_verified_stage_delta(self) -> None:
        receipt = self.receipt
        changed = copy.deepcopy(receipt)
        changed["targeted_new_observation_count"] = 2
        changed["information_gain_total_nats_after_targeted_search"] = (
            changed["information_gain_total_nats_before_targeted_search"] + 0.6
        )
        changed["information_gain_gain_nats"] = 0.6
        changed["epistemic_credit_total_nats_after_targeted_search"] = (
            changed["epistemic_credit_total_nats_before_targeted_search"] + 0.5
        )
        changed["epistemic_credit_gain_nats"] = 0.5
        changed["decision_credit_total_nats_after_targeted_search"] = (
            changed["decision_credit_total_nats_before_targeted_search"] + 0.4
        )
        changed["decision_credit_gain_nats"] = 0.4
        changed["safe_change_count_after_targeted_search"] = (
            changed["safe_change_count_before_targeted_search"] + 1
        )
        changed["safe_change_improvement_count"] = 1
        changed["candidate_changed_cell_count_after_targeted_search"] = 1
        changed["action_information_credit_nats"] = 0.6
        changed["action_epistemic_credit_nats"] = 0.5
        changed["action_decision_credit_nats"] = 0.4
        changed["action_positive_information_gain_count"] = 1
        changed["action_positive_epistemic_credit_count"] = 1
        changed["action_positive_decision_credit_count"] = 1
        changed.pop("receipt_payload_sha256")
        from deepwide_agent.v24323_shared_prefix_cell_entropy import payload_sha256

        changed["receipt_payload_sha256"] = payload_sha256(changed)
        validated = validate_action_credit_receipt(changed)
        self.assertEqual(validated["action_information_credit_nats"], 0.6)
        self.assertEqual(validated["action_decision_credit_nats"], 0.4)

    def test_credit_without_observation_or_safe_change_fails_closed(self) -> None:
        receipt = self.receipt
        for mode in ("information", "decision"):
            with self.subTest(mode=mode):
                changed = copy.deepcopy(receipt)
                if mode == "information":
                    changed["action_information_credit_nats"] = 0.1
                    changed["action_positive_information_gain_count"] = 1
                else:
                    changed["action_decision_credit_nats"] = 0.1
                    changed["action_positive_decision_credit_count"] = 1
                changed.pop("receipt_payload_sha256")
                from deepwide_agent.v24323_shared_prefix_cell_entropy import (
                    payload_sha256,
                )

                changed["receipt_payload_sha256"] = payload_sha256(changed)
                with self.assertRaises(ValueError):
                    validate_action_credit_receipt(changed)

    def test_tamper_and_content_flags_fail_closed(self) -> None:
        receipt = self.receipt
        for field, value in (
            ("targeted_logical_query_count", 3),
            ("alias_hint_itself_receives_vote_or_source_credit", True),
            (
                "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
                True,
            ),
        ):
            with self.subTest(field=field):
                changed = copy.deepcopy(receipt)
                changed[field] = value
                changed.pop("receipt_payload_sha256")
                from deepwide_agent.v24323_shared_prefix_cell_entropy import (
                    payload_sha256,
                )

                changed["receipt_payload_sha256"] = payload_sha256(changed)
                with self.assertRaises(ValueError):
                    validate_action_credit_receipt(changed)

    def test_runtime_source_is_label_blind(self) -> None:
        from scripts import audit_v24495_targeted_conversion_projection_build as audit

        accesses, imports = audit.ast_findings(
            Path("src/deepwide_agent/v24533_alias_acquisition_entropy_credit.py")
        )
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])


if __name__ == "__main__":
    unittest.main()
