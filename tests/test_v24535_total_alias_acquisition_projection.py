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

from deepwide_agent import v24534_proof_carrying_alias_acquisition as proof  # noqa: E402
from deepwide_agent import v24535_total_alias_acquisition_projection as total  # noqa: E402
from deepwide_agent.v24309_runner_exit_integration import _new_json  # noqa: E402
from deepwide_agent.v24323_shared_prefix_cell_entropy import payload_sha256  # noqa: E402
from test_v24534_proof_carrying_alias_acquisition import (  # noqa: E402
    MANIFEST,
    TASK,
    populate_direct,
    read,
    rewrite,
    validate,
)


def positive_capability(source_root: Path, destination: Path):
    shutil.copytree(source_root, destination)
    directory = destination / "task"
    auxiliary = proof.auxiliary_directory(destination, 1)
    receipt = read(auxiliary / proof.RECEIPT_NAME)
    receipt["targeted_new_observation_count"] = 2
    receipt["information_gain_total_nats_after_targeted_search"] = (
        receipt["information_gain_total_nats_before_targeted_search"] + 0.6
    )
    receipt["information_gain_gain_nats"] = 0.6
    receipt["information_gain_regression_nats"] = 0.0
    receipt["epistemic_credit_total_nats_after_targeted_search"] = (
        receipt["epistemic_credit_total_nats_before_targeted_search"] + 0.5
    )
    receipt["epistemic_credit_gain_nats"] = 0.5
    receipt["epistemic_credit_regression_nats"] = 0.0
    receipt["decision_credit_total_nats_after_targeted_search"] = (
        receipt["decision_credit_total_nats_before_targeted_search"] + 0.4
    )
    receipt["decision_credit_gain_nats"] = 0.4
    receipt["decision_credit_regression_nats"] = 0.0
    receipt["safe_change_count_after_targeted_search"] = (
        receipt["safe_change_count_before_targeted_search"] + 1
    )
    receipt["safe_change_improvement_count"] = 1
    receipt["safe_change_regression_count"] = 0
    receipt["candidate_changed_cell_count_after_targeted_search"] = 1
    receipt["action_information_credit_nats"] = 0.6
    receipt["action_epistemic_credit_nats"] = 0.5
    receipt["action_decision_credit_nats"] = 0.4
    receipt["action_decision_credit_regression_nats"] = 0.0
    receipt["action_positive_information_gain_count"] = 1
    receipt["action_positive_epistemic_credit_count"] = 1
    receipt["action_positive_decision_credit_count"] = 1
    receipt["action_decision_credit_regression_count"] = 0
    receipt.pop("receipt_payload_sha256")
    receipt["receipt_payload_sha256"] = payload_sha256(receipt)
    rewrite(auxiliary / proof.RECEIPT_NAME, receipt)
    (auxiliary / proof.CERTIFICATE_NAME).unlink()
    certificate = proof.build_certificate(
        ordinal=1,
        directory=directory,
        auxiliary=auxiliary,
        output_root=destination,
        action_receipt=receipt,
        validator_manifest_sha256=MANIFEST,
    )
    _new_json(auxiliary / proof.CERTIFICATE_NAME, certificate)
    return validate(destination)


class V24535TotalAliasAcquisitionProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        cls.root = Path(cls.temporary.name)
        populate_direct(cls.root)
        cls.capability = validate(cls.root)
        cls.positive_temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        positive_root = Path(cls.positive_temporary.name) / "positive"
        cls.positive = positive_capability(cls.root, positive_root)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.positive_temporary.cleanup()
        cls.temporary.cleanup()

    def test_success_row_consumes_only_capability_and_exposes_activity(self) -> None:
        row = total.task_projection(1, self.capability)
        self.assertEqual(row["status"], "validated_capability")
        self.assertTrue(
            row["acquisition_action_receipt_consumed_validated_capability"]
        )
        self.assertEqual(row["acquisition_action_target_plan_count"], 1)
        self.assertGreater(
            row["acquisition_action_alias_seeded_query_vector_calls"], 0
        )
        self.assertGreater(row["acquisition_action_lead_selection_calls"], 0)
        self.assertEqual(
            row["acquisition_action_targeted_new_observation_count"], 0
        )
        self.assertEqual(row["acquisition_action_action_information_credit_nats"], 0)

    def test_positive_action_credit_is_conserved_at_row_level(self) -> None:
        row = total.task_projection(1, self.positive)
        self.assertEqual(
            row["acquisition_action_targeted_new_observation_count"], 2
        )
        self.assertAlmostEqual(
            row["acquisition_action_action_information_credit_nats"], 0.6
        )
        self.assertAlmostEqual(
            row["acquisition_action_action_epistemic_credit_nats"], 0.5
        )
        self.assertAlmostEqual(
            row["acquisition_action_action_decision_credit_nats"], 0.4
        )
        self.assertEqual(
            row["acquisition_action_action_positive_information_gain_count"], 1
        )
        self.assertEqual(
            row["acquisition_action_action_positive_decision_credit_count"], 1
        )
        self.assertEqual(row["acquisition_action_safe_change_regression_count"], 0)

    def test_failure_row_is_exact_zero_without_private_effect_claim(self) -> None:
        row = total.failure_projection(2)
        self.assertEqual(row["status"], "failure_as_zero")
        self.assertFalse(
            row["acquisition_action_receipt_consumed_validated_capability"]
        )
        self.assertFalse(row["acquisition_action_private_effects_known_zero"])
        self.assertEqual(row["acquisition_action_target_plan_count"], 0)
        self.assertEqual(
            row["acquisition_action_action_information_credit_nats"], 0.0
        )

    def test_public_success_dictionary_cannot_be_reingested_as_proof(self) -> None:
        row = total.task_projection(1, self.positive)
        with self.assertRaises(TypeError):
            total.task_projection(1, row)  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            total.aggregate_projections([row], selected=1)

    def test_mixed_aggregate_preserves_denominator_credit_and_regression(self) -> None:
        value = total.aggregate_projections(
            [self.positive, total.failure_projection(2)], selected=2
        )
        total.validate_aggregate(value)
        self.assertEqual(value["selected"], 2)
        self.assertEqual(value["success_tasks"], 1)
        self.assertEqual(value["failure_as_zero_tasks"], 1)
        self.assertEqual(value["acquisition_plan_tasks"], 1)
        self.assertEqual(value["acquisition_activity_tasks"], 1)
        self.assertEqual(value["acquisition_new_observation_tasks"], 1)
        self.assertEqual(value["acquisition_positive_information_gain_tasks"], 1)
        self.assertEqual(value["acquisition_positive_epistemic_credit_tasks"], 1)
        self.assertEqual(value["acquisition_positive_decision_credit_tasks"], 1)
        self.assertEqual(value["acquisition_decision_credit_regression_tasks"], 0)
        numbers = value["total_acquisition_action_number_fields"]
        self.assertAlmostEqual(numbers["action_information_credit_nats"], 0.6)
        self.assertAlmostEqual(numbers["action_epistemic_credit_nats"], 0.5)
        self.assertAlmostEqual(numbers["action_decision_credit_nats"], 0.4)
        self.assertEqual(numbers["action_decision_credit_regression_nats"], 0.0)
        self.assertTrue(
            value["all_acquisition_failure_rows_are_content_free_zero_projections"]
        )
        self.assertFalse(value["acquisition_failure_rows_claim_zero_private_effects"])

    def test_row_action_eligibility_and_aggregate_credit_tamper_fail_closed(self) -> None:
        row = total.task_projection(1, self.positive)
        for field, replacement in (
            ("acquisition_action_targeted_new_observation_count", 0),
            ("acquisition_action_action_information_credit_nats", 0.5),
            ("acquisition_action_action_decision_credit_nats", 0.6),
        ):
            with self.subTest(field=field):
                changed = copy.deepcopy(row)
                changed[field] = replacement
                with self.assertRaises(ValueError):
                    total.validate_total_row(changed)
        aggregate = total.aggregate_projections([self.positive], selected=1)
        for mode in ("task_count", "credit_total", "regression"):
            with self.subTest(mode=mode):
                changed = copy.deepcopy(aggregate)
                if mode == "task_count":
                    changed["acquisition_positive_information_gain_tasks"] = 0
                elif mode == "credit_total":
                    changed["total_acquisition_action_number_fields"][
                        "action_information_credit_nats"
                    ] = 0.7
                else:
                    changed["total_acquisition_action_number_fields"][
                        "action_decision_credit_regression_nats"
                    ] = 0.1
                with self.assertRaises(ValueError):
                    total.validate_aggregate(changed)

    def test_public_projection_is_content_free(self) -> None:
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
            "sha256",
        ):
            self.assertNotIn(prohibited, encoded)


if __name__ == "__main__":
    unittest.main()
