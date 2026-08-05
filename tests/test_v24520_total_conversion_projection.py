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
from deepwide_agent.v24519_proof_carrying_conversion_observability import (  # noqa: E402
    run_conversion_observable_worker,
    validate_proof_carrying_conversion_bundle,
)
from deepwide_agent.v24520_total_conversion_projection import (  # noqa: E402
    aggregate_projections,
    failure_projection,
    task_projection,
    validate_aggregate,
    validate_total_row,
)
from test_v24342_semantic_active_runtime import limits  # noqa: E402
from test_v24390_uncertainty_active_evidence_runtime import SEED, TASK  # noqa: E402
from test_v24412_receipt_snapshot_diagnosis import AdvancingClock  # noqa: E402
from test_v24516_neutral_discovery_record_bound_worker import clients  # noqa: E402


MANIFEST = hashlib.sha256(b"v24520-test-validator-manifest").hexdigest()


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class V24520TotalConversionProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        output_root = Path(cls.temporary.name)
        directory = output_root / "task"
        fixture = output_root / "fixture"
        directory.mkdir(); fixture.mkdir()
        clock = AdvancingClock()
        model, search = clients(fixture, clock)
        run_conversion_observable_worker(
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
        cls.capability = validate_proof_carrying_conversion_bundle(
            read(directory / RESULT_NAME),
            directory=directory,
            expected_model_cap=2,
            expected_validator_manifest_sha256=MANIFEST,
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def test_success_row_consumes_capability_and_preserves_partition(self) -> None:
        row = task_projection(1, self.capability)
        self.assertEqual(
            sum(row["conversion_reason_counts"].values()),
            row["conversion_page_target_pair_count"],
        )
        self.assertEqual(
            row["conversion_grammar_projection_pair_count"],
            row["conversion_reason_counts"][
                "projection_duplicate_parent_observation"
            ],
        )
        self.assertEqual(
            row["conversion_reserve_usable_page_count"],
            row["reserve_usable_page_count"],
        )
        self.assertTrue(row["conversion_receipt_consumed_validated_capability"])

    def test_failure_row_is_zero_but_does_not_claim_private_effects(self) -> None:
        row = failure_projection(2)
        self.assertEqual(row["status"], "failure_as_zero")
        self.assertEqual(row["conversion_page_target_pair_count"], 0)
        self.assertEqual(sum(row["conversion_reason_counts"].values()), 0)
        self.assertFalse(row["private_effects_known_zero"])
        self.assertFalse(row["conversion_receipt_consumed_validated_capability"])

    def test_mixed_total_aggregate_preserves_reason_and_route_counts(self) -> None:
        value = aggregate_projections(
            [self.capability, failure_projection(2)], selected=2
        )
        self.assertEqual(value["success_tasks"], 1)
        self.assertEqual(value["failure_as_zero_tasks"], 1)
        self.assertEqual(
            sum(value["conversion_reason_pair_counts"].values()),
            value["total_conversion_page_target_pair_count"],
        )
        self.assertTrue(value["all_success_rows_consumed_conversion_capabilities"])
        self.assertTrue(
            value[
                "all_failure_rows_are_content_free_conversion_zero_projections"
            ]
        )
        self.assertFalse(value["conversion_failure_rows_claim_zero_private_effects"])
        validate_aggregate(value)

    def test_expanded_success_row_cannot_be_reingested_as_proof(self) -> None:
        row = task_projection(1, self.capability)
        with self.assertRaisesRegex(ValueError, "cannot be re-ingested"):
            aggregate_projections([row], selected=1)

    def test_row_and_aggregate_conservation_tamper_fail_closed(self) -> None:
        row = task_projection(1, self.capability)
        changed = copy.deepcopy(row)
        changed["conversion_reason_counts"][
            "projection_duplicate_parent_observation"
        ] -= 1
        changed["conversion_reason_counts"][
            "no_projection_explicit_relation_absent"
        ] += 1
        with self.assertRaises(ValueError):
            validate_total_row(changed)
        aggregate = aggregate_projections([self.capability], selected=1)
        changed_aggregate = copy.deepcopy(aggregate)
        changed_aggregate["conversion_reason_pair_counts"][
            "projection_duplicate_parent_observation"
        ] -= 1
        with self.assertRaises(ValueError):
            validate_aggregate(changed_aggregate)

    def test_projection_is_content_free_and_runtime_is_label_blind(self) -> None:
        row = task_projection(1, self.capability)
        encoded = json.dumps(row, ensure_ascii=False, sort_keys=True)
        for prohibited in (
            TASK["question"],
            TASK["opaque_id"],
            "Alpha",
            "2025",
            "neutral-discovery",
            "query_vector",
            "raw_content",
            "candidate_prediction",
        ):
            self.assertNotIn(prohibited, encoded)
        from scripts import audit_v24398_failure_observability_build as audit

        accesses, imports = audit._ast_findings(
            Path("src/deepwide_agent/v24520_total_conversion_projection.py")
        )
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])


if __name__ == "__main__":
    unittest.main()
