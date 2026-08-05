from __future__ import annotations

import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24309_runner_exit_integration import _new_json  # noqa: E402
from deepwide_agent.v24399_failure_observable_runner import RESULT_NAME  # noqa: E402
from deepwide_agent.v24525_proof_carrying_alias_title import (  # noqa: E402
    run_alias_title_worker,
    validate_proof_carrying_alias_bundle,
)
from deepwide_agent.v24526_total_alias_title_projection import (  # noqa: E402
    aggregate_projections,
    failure_projection,
    task_projection,
    validate_aggregate,
    validate_total_row,
)
from test_v24342_semantic_active_runtime import limits  # noqa: E402
from test_v24390_uncertainty_active_evidence_runtime import SEED  # noqa: E402
from test_v24412_receipt_snapshot_diagnosis import AdvancingClock  # noqa: E402
from test_v24524_alias_title_integration import TASK, clients  # noqa: E402


MANIFEST = hashlib.sha256(b"v24526-test-validator-manifest").hexdigest()


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class V24526TotalAliasTitleProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        output_root = Path(cls.temporary.name)
        directory = output_root / "task"
        fixture = output_root / "fixture"
        directory.mkdir()
        fixture.mkdir()
        clock = AdvancingClock()
        model, search = clients(fixture, clock, mode="support")
        run_alias_title_worker(
            TASK,
            output_root=output_root,
            directory=directory,
            model_factory=lambda: model,
            search_factory=lambda: search,
            partition_seed_sha256=SEED,
            limits=limits(),
            monotonic=clock,
            expected_model_cap=2,
            writer=lambda name, value: _new_json(directory / name, value),
            validator_manifest_sha256=MANIFEST,
        )
        cls.capability = validate_proof_carrying_alias_bundle(
            read(directory / RESULT_NAME),
            directory=directory,
            expected_model_cap=2,
            expected_validator_manifest_sha256=MANIFEST,
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def test_success_row_consumes_capability_and_exposes_entropy_credit(self) -> None:
        row = task_projection(1, self.capability)
        self.assertEqual(row["status"], "validated_capability")
        self.assertTrue(row["alias_stage_receipt_consumed_validated_capability"])
        self.assertTrue(row["alias_stage_private_effects_known_zero"])
        self.assertGreater(row["alias_stage_unique_alias_anchor_page_count"], 0)
        self.assertGreater(row["alias_stage_alias_observation_count"], 0)
        self.assertGreater(row["alias_stage_safe_change_improvement_count"], 0)
        self.assertGreater(
            row["alias_stage_positive_information_gain_gain_nats"], 0
        )
        self.assertGreater(row["alias_stage_epistemic_credit_gain_nats"], 0)
        self.assertGreater(row["alias_stage_decision_credit_gain_nats"], 0)
        self.assertEqual(
            row["terminal_safe_change_count"],
            row["alias_stage_parent_safe_change_count"],
        )

    def test_failure_row_is_exact_zero_without_private_effect_claim(self) -> None:
        row = failure_projection(2)
        self.assertEqual(row["status"], "failure_as_zero")
        self.assertFalse(row["alias_stage_private_effects_known_zero"])
        self.assertFalse(row["alias_stage_receipt_consumed_validated_capability"])
        self.assertEqual(row["alias_stage_alias_observation_count"], 0)
        self.assertEqual(row["alias_stage_decision_credit_gain_nats"], 0)

    def test_public_success_dictionary_cannot_be_reingested_as_proof(self) -> None:
        row = task_projection(1, self.capability)
        with self.assertRaises(TypeError):
            task_projection(1, row)  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            aggregate_projections([row], selected=1)

    def test_mixed_aggregate_preserves_exact_denominator_and_credit(self) -> None:
        value = aggregate_projections(
            [self.capability, failure_projection(2)], selected=2
        )
        validate_aggregate(value)
        self.assertEqual(value["selected"], 2)
        self.assertEqual(value["success_tasks"], 1)
        self.assertEqual(value["failure_as_zero_tasks"], 1)
        self.assertEqual(value["alias_decision_credit_gain_tasks"], 1)
        self.assertGreater(
            value["total_alias_stage_number_fields"][
                "decision_credit_gain_nats"
            ],
            0,
        )
        self.assertTrue(
            value["all_alias_failure_rows_are_content_free_zero_projections"]
        )
        self.assertFalse(value["alias_failure_rows_claim_zero_private_effects"])

    def test_row_and_aggregate_tamper_fail_closed(self) -> None:
        row = task_projection(1, self.capability)
        tampered = copy.deepcopy(row)
        tampered["alias_stage_decision_credit_gain_nats"] = 0
        with self.assertRaises(ValueError):
            validate_total_row(tampered)
        aggregate = aggregate_projections([self.capability], selected=1)
        tampered_aggregate = copy.deepcopy(aggregate)
        tampered_aggregate["total_alias_stage_count_fields"][
            "additional_fetch_calls"
        ] = 1
        with self.assertRaises(ValueError):
            validate_aggregate(tampered_aggregate)

    def test_public_projection_is_content_free(self) -> None:
        encoded = json.dumps(
            task_projection(1, self.capability), ensure_ascii=False, sort_keys=True
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
