from __future__ import annotations

import copy
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24549_proof_carrying_alias_joint as proof  # noqa: E402
from deepwide_agent import v24550_total_alias_joint_projection as total  # noqa: E402
from deepwide_agent.v24309_runner_exit_integration import _new_json  # noqa: E402
from deepwide_agent.v24323_shared_prefix_cell_entropy import payload_sha256  # noqa: E402
from test_v24524_alias_title_integration import TASK  # noqa: E402
from test_v24549_proof_carrying_alias_joint import (  # noqa: E402
    MANIFEST,
    populate,
    read,
    rewrite,
    validate,
)


def positive_capability(source_root: Path, destination: Path):
    shutil.copytree(source_root, destination)
    directory = destination / "task"
    auxiliary = proof.auxiliary_directory(destination, 1)
    receipt = read(auxiliary / proof.RECEIPT_NAME)
    activity = receipt["alias_surface_receipt"]
    for field in (
        "title_initialism_hit_lead_count",
        "url_initialism_hit_lead_count",
        "title_alias_surface_hit_lead_count",
        "url_alias_surface_hit_lead_count",
        "alias_surface_hit_lead_count",
        "selected_title_initialism_hit_lead_count",
        "selected_url_initialism_hit_lead_count",
        "selected_title_alias_surface_hit_lead_count",
        "selected_url_alias_surface_hit_lead_count",
        "selected_alias_surface_hit_lead_count",
    ):
        activity[field] = 1
    receipt["targeted_new_observation_count"] = 1
    receipt["information_gain_total_nats_after_targeted_search"] = (
        receipt["information_gain_total_nats_before_targeted_search"] + 0.6
    )
    receipt["information_gain_gain_nats"] = 0.6
    receipt["epistemic_credit_total_nats_after_targeted_search"] = (
        receipt["epistemic_credit_total_nats_before_targeted_search"] + 0.5
    )
    receipt["epistemic_credit_gain_nats"] = 0.5
    receipt["decision_credit_total_nats_after_targeted_search"] = (
        receipt["decision_credit_total_nats_before_targeted_search"] + 0.4
    )
    receipt["decision_credit_gain_nats"] = 0.4
    receipt["safe_change_count_after_targeted_search"] = (
        receipt["safe_change_count_before_targeted_search"] + 1
    )
    receipt["safe_change_improvement_count"] = 1
    receipt["candidate_changed_cell_count_after_targeted_search"] = 1
    receipt["action_information_credit_nats"] = 0.6
    receipt["action_epistemic_credit_nats"] = 0.5
    receipt["action_decision_credit_nats"] = 0.4
    receipt["action_positive_information_gain_count"] = 1
    receipt["action_positive_epistemic_credit_count"] = 1
    receipt["action_positive_decision_credit_count"] = 1
    receipt["acquisition_active_and_positive_information_gain_count"] = 1
    receipt["acquisition_active_and_positive_epistemic_gain_count"] = 1
    receipt["new_observation_and_alias_surface_hit_count"] = 1
    receipt["new_observation_and_selected_alias_surface_hit_count"] = 1
    receipt[
        "selected_alias_surface_hit_and_positive_information_gain_count"
    ] = 1
    receipt[
        "selected_alias_surface_hit_new_observation_and_positive_information_gain_count"
    ] = 1
    receipt.pop("receipt_payload_sha256")
    receipt["receipt_payload_sha256"] = payload_sha256(receipt)
    rewrite(auxiliary / proof.RECEIPT_NAME, receipt)
    (auxiliary / proof.CERTIFICATE_NAME).unlink()
    certificate = proof.build_certificate(
        ordinal=1,
        directory=directory,
        auxiliary=auxiliary,
        output_root=destination,
        joint_receipt=receipt,
        validator_manifest_sha256=MANIFEST,
    )
    _new_json(auxiliary / proof.CERTIFICATE_NAME, certificate)
    return validate(destination)


class V24550TotalAliasJointProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        cls.root = Path(cls.temporary.name)
        populate(cls.root)
        cls.capability = validate(cls.root)
        cls.positive_temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        positive_root = Path(cls.positive_temporary.name) / "positive"
        cls.positive = positive_capability(cls.root, positive_root)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.positive_temporary.cleanup()
        cls.temporary.cleanup()

    def test_success_row_consumes_capability_and_exposes_exact_modes(self) -> None:
        row = total.task_projection(1, self.capability)
        self.assertEqual(row["status"], "validated_capability")
        self.assertTrue(row["alias_joint_receipt_consumed_validated_capability"])
        self.assertEqual(row["alias_joint_target_plan_count"], 1)
        self.assertGreater(row["alias_surface_alias_seeded_query_vector_calls"], 0)
        self.assertEqual(row["alias_surface_alias_surface_hit_lead_count"], 0)
        self.assertEqual(
            row[
                "alias_joint_selected_alias_surface_hit_new_observation_and_positive_information_gain_count"
            ],
            0,
        )

    def test_positive_joint_and_credit_are_conserved_at_row_level(self) -> None:
        row = total.task_projection(1, self.positive)
        self.assertEqual(row["alias_surface_selected_alias_surface_hit_lead_count"], 1)
        self.assertEqual(
            row[
                "alias_joint_selected_alias_surface_hit_new_observation_and_positive_information_gain_count"
            ],
            1,
        )
        self.assertAlmostEqual(row["alias_joint_action_information_credit_nats"], 0.6)
        self.assertAlmostEqual(row["alias_joint_action_epistemic_credit_nats"], 0.5)
        self.assertAlmostEqual(row["alias_joint_action_decision_credit_nats"], 0.4)
        self.assertFalse(row["alias_joint_same_task_counts_claim_lead_level_causality"])

    def test_failure_row_is_exact_zero_without_private_effect_claim(self) -> None:
        row = total.failure_projection(2)
        self.assertEqual(row["status"], "failure_as_zero")
        self.assertFalse(row["alias_joint_receipt_consumed_validated_capability"])
        self.assertFalse(row["alias_joint_private_effects_known_zero"])
        self.assertEqual(row["alias_surface_visible_lead_count"], 0)
        self.assertEqual(row["alias_joint_action_information_credit_nats"], 0.0)

    def test_public_success_dictionary_cannot_be_reingested_as_proof(self) -> None:
        row = total.task_projection(1, self.positive)
        with self.assertRaises(TypeError):
            total.task_projection(1, row)  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            total.aggregate_projections([row], selected=1)

    def test_mixed_aggregate_preserves_modes_joint_credit_and_denominator(self) -> None:
        value = total.aggregate_projections(
            [self.positive, total.failure_projection(2)], selected=2
        )
        total.validate_aggregate(value)
        self.assertEqual(value["selected"], 2)
        self.assertEqual(value["success_tasks"], 1)
        self.assertEqual(value["failure_as_zero_tasks"], 1)
        self.assertEqual(value["selected_alias_surface_hit_tasks"], 1)
        self.assertEqual(value["alias_joint_new_observation_tasks"], 1)
        triple = (
            "selected_alias_surface_hit_new_observation_and_positive_information_gain_count"
        )
        self.assertEqual(value[f"{triple}_tasks"], 1)
        self.assertEqual(value["total_alias_joint_count_fields"][triple], 1)
        self.assertAlmostEqual(
            value["total_alias_joint_number_fields"][
                "action_information_credit_nats"
            ],
            0.6,
        )
        self.assertTrue(
            value[
                "all_alias_joint_failure_rows_are_content_free_zero_projections"
            ]
        )
        self.assertFalse(value["alias_joint_failure_rows_claim_zero_private_effects"])

    def test_row_and_aggregate_coordinated_tamper_fail_closed(self) -> None:
        row = total.task_projection(1, self.positive)
        for field, replacement in (
            ("alias_surface_selected_alias_surface_hit_lead_count", 0),
            (
                "alias_joint_selected_alias_surface_hit_new_observation_and_positive_information_gain_count",
                0,
            ),
            ("alias_joint_action_information_credit_nats", 0.5),
        ):
            with self.subTest(field=field):
                changed = copy.deepcopy(row)
                changed[field] = replacement
                with self.assertRaises(ValueError):
                    total.validate_total_row(changed)
        aggregate = total.aggregate_projections([self.positive], selected=1)
        cases = (
            lambda value: value.__setitem__("selected_alias_surface_hit_tasks", 0),
            lambda value: value["total_alias_joint_count_fields"].__setitem__(
                "selected_alias_surface_hit_new_observation_and_positive_information_gain_count",
                0,
            ),
            lambda value: value.__setitem__(
                "alias_joint_same_task_counts_claim_lead_level_causality", True
            ),
        )
        for alter in cases:
            changed = copy.deepcopy(aggregate)
            alter(changed)
            with self.assertRaises(ValueError):
                total.validate_aggregate(changed)

    def test_public_projection_is_content_free_and_label_blind(self) -> None:
        encoded = json.dumps(
            total.task_projection(1, self.positive),
            ensure_ascii=False,
            sort_keys=True,
        )
        for prohibited in (
            TASK["question"],
            TASK["opaque_id"],
            "University of Southern Queensland",
            "1967",
            "usq-one.example",
            "raw_content",
            "candidate_prediction",
        ):
            self.assertNotIn(prohibited, encoded)
        from scripts import audit_v24495_targeted_conversion_projection_build as audit

        accesses, imports = audit.ast_findings(
            Path("src/deepwide_agent/v24550_total_alias_joint_projection.py")
        )
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])


if __name__ == "__main__":
    unittest.main()
