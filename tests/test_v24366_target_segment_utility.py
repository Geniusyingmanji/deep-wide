from __future__ import annotations

import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24323_shared_prefix_cell_entropy import payload_sha256  # noqa: E402
from deepwide_agent.v24333_programmatic_support_catalog import (  # noqa: E402
    CellTarget,
    _source_key,
)
from deepwide_agent.v24341_semantic_evidence_projection import (  # noqa: E402
    build_semantic_active_catalog,
)
from deepwide_agent.v24354_explicit_partition_utility import (  # noqa: E402
    build_explicit_partition_utility_catalog,
)
from deepwide_agent.v24366_target_segment_utility import (  # noqa: E402
    build_target_segment_utility_catalog,
    resolve_target_segment_utility_selection,
    validate_target_segment_utility_catalog,
    validate_target_segment_utility_receipt,
)


SEED = "d" * 64


def page(host: str, content: str) -> dict:
    return {"host": host, "content": content, "fetch_integrity": True}


def source_digest(host: str) -> str:
    return hashlib.sha256(_source_key(host).encode("utf-8")).hexdigest()


def proposal_catalog(
    targets: list[CellTarget] | None = None,
    pages: list[dict] | None = None,
) -> dict:
    selected_targets = targets or [CellTarget("Alpha", "Founding year", "Unknown")]
    selected_pages = pages or [
        page("proposal1.example", "Alpha was founded in 2025."),
        page("proposal2.example", "Alpha was established in 2025."),
    ]
    return build_semantic_active_catalog(selected_targets, selected_pages, [])


def build(
    proposal: dict,
    hidden: list[dict],
    *,
    proposal_hosts: list[str],
    verifier_hosts: list[str],
) -> dict:
    return build_target_segment_utility_catalog(
        proposal,
        hidden,
        partition_seed_sha256=SEED,
        expected_proposal_source_key_sha256s=sorted(
            source_digest(host) for host in proposal_hosts
        ),
        expected_verifier_source_key_sha256s=sorted(
            source_digest(host) for host in verifier_hosts
        ),
    )


def selection(catalog: dict, record: dict, **patch) -> dict:
    arguments = {
        "row_key": record["row_key"],
        "column": record["column"],
        "new_value": record["candidate_value"],
        "proposal_support_set_id": record["proposal_support_set_id"],
        "declared_proposal_evidence_ids": record["proposal_evidence_ids"],
    }
    return resolve_target_segment_utility_selection(
        catalog, **{**arguments, **patch}
    )


class V24366TargetSegmentUtilityTests(unittest.TestCase):
    def test_adjacent_visible_entity_does_not_create_false_conflict(self) -> None:
        alpha = CellTarget("Alpha", "Founding year", "Unknown")
        beta = CellTarget("Beta", "Founding year", "Unknown")
        proposal = proposal_catalog(
            [alpha, beta],
            [
                page("proposal1.example", "Alpha was founded in 2025."),
                page("proposal2.example", "Alpha was established in 2025."),
                page("proposal3.example", "Beta was founded in 2024."),
                page("proposal4.example", "Beta was established in 2024."),
            ],
        )
        hidden = [
            page(
                "verifier.example",
                "Alpha was founded in 2025, while Beta was founded in 2024.",
            )
        ]
        value = build(
            proposal,
            hidden,
            proposal_hosts=[f"proposal{index}.example" for index in range(1, 5)],
            verifier_hosts=["verifier.example"],
        )
        self.assertEqual(value["verification_record_count"], 2)
        self.assertEqual(value["utility_aligned_support_set_count"], 2)
        self.assertEqual(value["verification_status_counts"], {"verified_candidate": 2})

    def test_old_projector_reproduces_cross_entity_false_conflict(self) -> None:
        alpha = CellTarget("Alpha", "Founding year", "Unknown")
        beta = CellTarget("Beta", "Founding year", "Unknown")
        proposal = proposal_catalog(
            [alpha, beta],
            [
                page("proposal1.example", "Alpha was founded in 2025."),
                page("proposal2.example", "Alpha was established in 2025."),
                page("proposal3.example", "Beta was founded in 2024."),
                page("proposal4.example", "Beta was established in 2024."),
            ],
        )
        hidden = [
            page(
                "verifier.example",
                "Alpha was founded in 2025, while Beta was founded in 2024.",
            )
        ]
        old = build_explicit_partition_utility_catalog(
            proposal,
            hidden,
            partition_seed_sha256=SEED,
            expected_proposal_source_key_sha256s=sorted(
                source_digest(f"proposal{index}.example") for index in range(1, 5)
            ),
            expected_verifier_source_key_sha256s=[source_digest("verifier.example")],
        )
        self.assertEqual(old["utility_aligned_support_set_count"], 0)
        self.assertGreater(old["quarantine_reasons"].get("quarantine_independent_conflict", 0), 0)

    def test_real_same_target_conflict_remains_quarantined(self) -> None:
        proposal = proposal_catalog()
        value = build(
            proposal,
            [
                page(
                    "verifier.example",
                    "Alpha was founded in 2025 and was established in 2024",
                )
            ],
            proposal_hosts=["proposal1.example", "proposal2.example"],
            verifier_hosts=["verifier.example"],
        )
        record = value["verification_records"][0]
        self.assertEqual(record["verification_status"], "independent_conflict")
        self.assertEqual(record["verifier_candidate_source_count"], 1)
        self.assertEqual(record["verifier_conflicting_source_count"], 1)
        self.assertEqual(value["utility_aligned_support_set_count"], 0)

    def test_different_hidden_value_is_diagnostic_conflict_not_generic_missing(self) -> None:
        proposal = proposal_catalog()
        value = build(
            proposal,
            [page("verifier.example", "Alpha was founded in 2024.")],
            proposal_hosts=["proposal1.example", "proposal2.example"],
            verifier_hosts=["verifier.example"],
        )
        self.assertEqual(value["verification_status_counts"], {"independent_conflict": 1})

    def test_parent_entropy_survives_no_verifier_support(self) -> None:
        proposal = proposal_catalog()
        value = build(
            proposal,
            [page("verifier.example", "Alpha publishes documentation.")],
            proposal_hosts=["proposal1.example", "proposal2.example"],
            verifier_hosts=["verifier.example"],
        )
        record = value["verification_records"][0]
        self.assertEqual(record["verification_status"], "no_independent_candidate_support")
        self.assertGreater(record["proposal_conditional_entropy_reduction_nats"], 0)
        self.assertGreater(value["proposal_support_entropy_total_nats"], 0)
        self.assertEqual(value["utility_aligned_entropy_total_nats"], 0)
        receipt = selection(value, record)
        self.assertFalse(receipt["admitted"])
        self.assertGreater(receipt["proposal_conditional_entropy_reduction_nats"], 0)
        self.assertEqual(receipt["utility_aligned_entropy_credit_nats"], 0)
        self.assertEqual(receipt["disposition"], "quarantine_no_independent_candidate_support")

    def test_known_baseline_support_has_distinct_status(self) -> None:
        target = CellTarget("Alpha", "Founding year", "2020")
        proposal = proposal_catalog(
            [target],
            [
                page("proposal1.example", "Alpha was founded in 2025."),
                page("proposal2.example", "Alpha was established in 2025."),
                page("proposal3.example", "Alpha was formed in 2025."),
            ],
        )
        value = build(
            proposal,
            [page("verifier.example", "Alpha was founded in 2020.")],
            proposal_hosts=[
                "proposal1.example",
                "proposal2.example",
                "proposal3.example",
            ],
            verifier_hosts=["verifier.example"],
        )
        self.assertEqual(value["verification_status_counts"], {"verifier_supports_baseline": 1})

    def test_binding_tamper_gets_zero_proposal_and_utility_credit(self) -> None:
        proposal = proposal_catalog()
        value = build(
            proposal,
            [page("verifier.example", "Alpha was founded in 2025.")],
            proposal_hosts=["proposal1.example", "proposal2.example"],
            verifier_hosts=["verifier.example"],
        )
        record = value["verification_records"][0]
        valid = selection(value, record)
        self.assertTrue(valid["admitted"])
        self.assertGreater(valid["utility_aligned_entropy_credit_nats"], 0)
        cases = (
            {"new_value": "2026"},
            {"proposal_support_set_id": "f" * 64},
            {"declared_proposal_evidence_ids": ["R9999"]},
        )
        for patch in cases:
            with self.subTest(patch=patch):
                receipt = selection(value, record, **patch)
                self.assertFalse(receipt["admitted"])
                self.assertEqual(receipt["proposal_conditional_entropy_reduction_nats"], 0)
                self.assertEqual(receipt["utility_aligned_entropy_credit_nats"], 0)

    def test_partition_catalog_and_receipt_tamper_fail_closed(self) -> None:
        proposal = proposal_catalog()
        with self.assertRaises(ValueError):
            build(
                proposal,
                [page("verifier.example", "Alpha was founded in 2025.")],
                proposal_hosts=[
                    "proposal1.example",
                    "proposal2.example",
                    "verifier.example",
                ],
                verifier_hosts=["wrong.example"],
            )

        value = build(
            proposal,
            [page("verifier.example", "Alpha was founded in 2025.")],
            proposal_hosts=["proposal1.example", "proposal2.example"],
            verifier_hosts=["verifier.example"],
        )
        altered = copy.deepcopy(value)
        altered["verification_records"][0]["verification_status"] = "independent_conflict"
        altered.pop("catalog_payload_sha256")
        altered["catalog_payload_sha256"] = payload_sha256(altered)
        with self.assertRaises(ValueError):
            validate_target_segment_utility_catalog(altered)

        receipt = selection(value, value["verification_records"][0])
        for field in ("count", "disposition"):
            with self.subTest(field=field):
                altered_receipt = copy.deepcopy(receipt)
                if field == "count":
                    altered_receipt["verifier_conflicting_source_count"] = 1
                else:
                    altered_receipt["disposition"] = "quarantine_independent_conflict"
                    altered_receipt["admitted"] = False
                    altered_receipt["utility_aligned_entropy_credit_nats"] = 0.0
                altered_receipt.pop("receipt_sha256")
                altered_receipt["receipt_sha256"] = payload_sha256(altered_receipt)
                with self.assertRaises(ValueError):
                    validate_target_segment_utility_receipt(altered_receipt)

    def test_public_resolution_is_content_free_and_label_blind(self) -> None:
        proposal = proposal_catalog()
        value = build(
            proposal,
            [page("verifier.example", "Alpha was founded in 2025.")],
            proposal_hosts=["proposal1.example", "proposal2.example"],
            verifier_hosts=["verifier.example"],
        )
        receipt = selection(value, value["verification_records"][0])
        encoded = json.dumps(receipt, ensure_ascii=False)
        for private in ("Alpha", "2025", "verifier.example"):
            self.assertNotIn(private, encoded)
        self.assertFalse(
            receipt[
                "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
            ]
        )
        self.assertFalse(receipt["benchmark_launch_or_evaluator_authorized"])


if __name__ == "__main__":
    unittest.main()
