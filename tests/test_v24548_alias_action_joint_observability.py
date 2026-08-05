from __future__ import annotations

import copy
import hashlib
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24309_runner_exit_integration import _new_json  # noqa: E402
from deepwide_agent.v24323_shared_prefix_cell_entropy import payload_sha256  # noqa: E402
from deepwide_agent import v24548_alias_action_joint_observability as target  # noqa: E402
from test_v24342_semantic_active_runtime import limits  # noqa: E402
from test_v24390_uncertainty_active_evidence_runtime import SEED  # noqa: E402
from test_v24412_receipt_snapshot_diagnosis import AdvancingClock  # noqa: E402
from test_v24524_alias_title_integration import TASK, clients  # noqa: E402


MANIFEST = hashlib.sha256(b"v24548-test-validator-manifest").hexdigest()


class V24548AliasActionJointObservabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        root = Path(cls.temporary.name)
        directory = root / "task"
        checkpoint = root / "checkpoint"
        fixture = root / "fixture"
        directory.mkdir()
        checkpoint.mkdir()
        fixture.mkdir()
        clock = AdvancingClock()
        cls.model, cls.search = clients(fixture, clock, mode="support")
        with patch(
            "deepwide_agent.v24469_bounded_worker_supervisor.bind_worker_to_parent"
        ):
            cls.result, cls.receipt = target.run_alias_surface_worker_with_receipt(
                TASK,
                ordinal=1,
                expected_supervisor_pid=os.getpid(),
                checkpoint_directory=checkpoint,
                output_root=root,
                directory=directory,
                model_factory=lambda _callback: cls.model,
                search_factory=lambda _callback: cls.search,
                partition_seed_sha256=SEED,
                limits=limits(),
                monotonic=clock,
                expected_model_cap=2,
                writer=lambda name, value: _new_json(directory / name, value),
                validator_manifest_sha256=MANIFEST,
            )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def test_real_worker_exposes_exact_zero_hit_surface_without_query_self_proof(self) -> None:
        receipt = target.validate_joint_receipt(self.receipt)
        surface = receipt["alias_surface_receipt"]
        self.assertEqual(receipt["target_plan_count"], 1)
        self.assertGreater(surface["alias_seeded_query_vector_calls"], 0)
        self.assertEqual(surface["selected_alias_surface_hit_lead_count"], 0)
        self.assertEqual(surface["selected_title_initialism_hit_lead_count"], 0)
        self.assertEqual(surface["selected_url_initialism_hit_lead_count"], 0)
        self.assertFalse(surface["query_text_used_to_establish_alias_hit"])
        self.assertEqual(self.model.acquisitions, 2)
        self.assertEqual(self.search.request_invocations, 4)
        self.assertEqual(self.search.fetch_invocations, 5)

    def test_real_task_has_no_alias_observation_or_targeted_credit(self) -> None:
        receipt = self.receipt
        self.assertEqual(
            receipt["alias_surface_receipt"][
                "selected_alias_surface_hit_lead_count"
            ],
            0,
        )
        self.assertEqual(receipt["targeted_new_observation_count"], 0)
        self.assertEqual(
            receipt["new_observation_and_selected_alias_surface_hit_count"], 0
        )
        self.assertEqual(receipt["action_information_credit_nats"], 0)
        self.assertEqual(receipt["action_decision_credit_nats"], 0)

    def positive(self) -> dict:
        changed = copy.deepcopy(self.receipt)
        activity = changed["alias_surface_receipt"]
        activity["title_initialism_hit_lead_count"] = 1
        activity["url_initialism_hit_lead_count"] = 1
        activity["alias_surface_hit_lead_count"] = 1
        activity["title_alias_surface_hit_lead_count"] = 1
        activity["url_alias_surface_hit_lead_count"] = 1
        activity["selected_title_initialism_hit_lead_count"] = 1
        activity["selected_url_initialism_hit_lead_count"] = 1
        activity["selected_alias_surface_hit_lead_count"] = 1
        activity["selected_title_alias_surface_hit_lead_count"] = 1
        activity["selected_url_alias_surface_hit_lead_count"] = 1
        changed["targeted_new_observation_count"] = 1
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
        changed["acquisition_active_and_positive_information_gain_count"] = 1
        changed["acquisition_active_and_positive_epistemic_gain_count"] = 1
        changed["new_observation_and_alias_surface_hit_count"] = 1
        changed["new_observation_and_selected_alias_surface_hit_count"] = 1
        changed[
            "selected_alias_surface_hit_and_positive_information_gain_count"
        ] = 1
        changed[
            "selected_alias_surface_hit_new_observation_and_positive_information_gain_count"
        ] = 1
        changed.pop("receipt_payload_sha256")
        changed["receipt_payload_sha256"] = payload_sha256(changed)
        return changed

    def test_same_task_triple_joint_is_exact_but_not_lead_causality(self) -> None:
        validated = target.validate_joint_receipt(self.positive())
        self.assertEqual(
            validated[
                "selected_alias_surface_hit_new_observation_and_positive_information_gain_count"
            ],
            1,
        )
        self.assertTrue(
            validated["same_task_joint_counts_do_not_claim_lead_level_causality"]
        )
        self.assertAlmostEqual(validated["action_information_credit_nats"], 0.6)
        self.assertAlmostEqual(validated["action_decision_credit_nats"], 0.4)

    def test_coordinated_joint_query_and_credit_tamper_fail_closed(self) -> None:
        cases = (
            lambda value: value.__setitem__(
                "new_observation_and_selected_alias_surface_hit_count", 1
            ),
            lambda value: value["alias_surface_receipt"].__setitem__(
                "query_text_used_to_establish_alias_hit", True
            ),
            lambda value: value.__setitem__("action_information_credit_nats", 0.1),
            lambda value: value.__setitem__(
                "same_task_joint_counts_do_not_claim_lead_level_causality", False
            ),
        )
        for alter in cases:
            with self.subTest(alter=alter):
                changed = copy.deepcopy(self.receipt)
                alter(changed)
                if "receipt_payload_sha256" in changed:
                    changed.pop("receipt_payload_sha256")
                changed["receipt_payload_sha256"] = payload_sha256(changed)
                with self.assertRaises(ValueError):
                    target.validate_joint_receipt(changed)

    def test_content_free_receipt_and_runtime_source_are_label_blind(self) -> None:
        import json

        encoded = json.dumps(self.receipt, ensure_ascii=False, sort_keys=True)
        for prohibited in (
            TASK["question"],
            TASK["opaque_id"],
            "University of Southern Queensland",
            "1967",
            "usq-one.example",
            "candidate_prediction",
        ):
            self.assertNotIn(prohibited, encoded)
        from scripts import audit_v24495_targeted_conversion_projection_build as audit

        accesses, imports = audit.ast_findings(
            Path("src/deepwide_agent/v24548_alias_action_joint_observability.py")
        )
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])


if __name__ == "__main__":
    unittest.main()
