from __future__ import annotations

import copy
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
    resolve_explicit_partition_utility_selection,
    validate_explicit_partition_utility_catalog,
    validate_explicit_partition_utility_receipt,
)


SEED = "a" * 64
TARGET = CellTarget("Alpha", "Founding year", "Unknown")


def digest(host: str) -> str:
    import hashlib

    return hashlib.sha256(_source_key(host).encode("utf-8")).hexdigest()


def page(host: str, value: str = "2025") -> dict:
    return {
        "host": host,
        "content": f"Alpha was founded in {value} according to {host}.",
        "fetch_integrity": True,
    }


def proposal_catalog() -> dict:
    return build_semantic_active_catalog(
        [TARGET],
        [page("proposal1.example"), page("proposal2.example")],
        [],
    )


class V24354ExplicitPartitionUtilityTests(unittest.TestCase):
    def positive(self) -> dict:
        value = build_explicit_partition_utility_catalog(
            proposal_catalog(),
            [page("verifier.example")],
            partition_seed_sha256=SEED,
            expected_proposal_source_key_sha256s=sorted(
                {
                    digest("proposal1.example"),
                    digest("proposal2.example"),
                    digest("missing-proposal.example"),
                }
            ),
            expected_verifier_source_key_sha256s=[digest("verifier.example")],
        )
        self.assertEqual(value["proposal_support_set_count"], 1)
        self.assertEqual(value["utility_aligned_support_set_count"], 1)
        return value

    def test_missing_successful_page_does_not_trigger_repartition(self) -> None:
        value = self.positive()
        self.assertTrue(value["observed_pages_respect_frozen_partition"])
        self.assertLess(
            len(value["observed_proposal_source_key_sha256s"]),
            len(value["expected_proposal_source_key_sha256s"]),
        )
        support = value["proposal_semantic_catalog"]["active_catalog"][
            "base_catalog"
        ]["support_sets"][0]
        utility = value["utility_sets"][0]
        self.assertEqual(
            utility["proposal_support_set_id"], support["support_set_id"]
        )
        self.assertEqual(utility["proposal_evidence_ids"], support["evidence_ids"])

    def test_one_hidden_source_can_align_parent_entropy_credit(self) -> None:
        value = self.positive()
        item = value["utility_sets"][0]
        receipt = resolve_explicit_partition_utility_selection(
            value,
            row_key=item["row_key"],
            column=item["column"],
            new_value=item["candidate_value"],
            proposal_support_set_id=item["proposal_support_set_id"],
            declared_proposal_evidence_ids=item["proposal_evidence_ids"],
        )
        self.assertTrue(receipt["admitted"])
        self.assertEqual(receipt["verifier_candidate_source_count"], 1)
        self.assertGreater(receipt["utility_aligned_entropy_credit_nats"], 0)

    def test_hidden_conflict_quarantines_parent_support(self) -> None:
        value = build_explicit_partition_utility_catalog(
            proposal_catalog(),
            [page("verifier.example", "2024")],
            partition_seed_sha256=SEED,
            expected_proposal_source_key_sha256s=sorted(
                {digest("proposal1.example"), digest("proposal2.example")}
            ),
            expected_verifier_source_key_sha256s=[digest("verifier.example")],
        )
        self.assertEqual(value["utility_aligned_support_set_count"], 0)
        self.assertGreater(
            value["quarantine_reasons"].get(
                "quarantine_no_independent_candidate_support", 0
            )
            + value["quarantine_reasons"].get(
                "quarantine_independent_conflict", 0
            ),
            0,
        )

    def test_page_assigned_to_wrong_frozen_partition_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            build_explicit_partition_utility_catalog(
                proposal_catalog(),
                [page("verifier.example")],
                partition_seed_sha256=SEED,
                expected_proposal_source_key_sha256s=sorted(
                    {
                        digest("proposal1.example"),
                        digest("proposal2.example"),
                        digest("verifier.example"),
                    }
                ),
                expected_verifier_source_key_sha256s=[
                    digest("wrong-verifier.example")
                ],
            )

    def test_wrong_parent_support_or_evidence_binding_has_zero_credit(self) -> None:
        value = self.positive()
        item = value["utility_sets"][0]
        cases = (
            {"proposal_support_set_id": "f" * 64},
            {"declared_proposal_evidence_ids": ["R9999"]},
            {"new_value": "2026"},
        )
        base = {
            "row_key": item["row_key"],
            "column": item["column"],
            "new_value": item["candidate_value"],
            "proposal_support_set_id": item["proposal_support_set_id"],
            "declared_proposal_evidence_ids": item["proposal_evidence_ids"],
        }
        for patch in cases:
            with self.subTest(patch=patch):
                receipt = resolve_explicit_partition_utility_selection(
                    value, **{**base, **patch}
                )
                self.assertFalse(receipt["admitted"])
                self.assertEqual(receipt["utility_aligned_entropy_credit_nats"], 0)

    def test_catalog_and_receipt_tamper_fail_replay(self) -> None:
        value = self.positive()
        altered = copy.deepcopy(value)
        altered["utility_sets"][0]["proposal_support_set_id"] = "f" * 64
        altered.pop("catalog_payload_sha256")
        altered["catalog_payload_sha256"] = payload_sha256(altered)
        with self.assertRaises(ValueError):
            validate_explicit_partition_utility_catalog(altered)

        item = value["utility_sets"][0]
        receipt = resolve_explicit_partition_utility_selection(
            value,
            row_key=item["row_key"],
            column=item["column"],
            new_value=item["candidate_value"],
            proposal_support_set_id=item["proposal_support_set_id"],
            declared_proposal_evidence_ids=item["proposal_evidence_ids"],
        )
        receipt["verifier_conflicting_source_count"] = 1
        receipt.pop("receipt_sha256")
        receipt["receipt_sha256"] = payload_sha256(receipt)
        with self.assertRaises(ValueError):
            validate_explicit_partition_utility_receipt(receipt)

    def test_public_receipt_is_content_free_and_label_blind(self) -> None:
        value = self.positive()
        item = value["utility_sets"][0]
        receipt = resolve_explicit_partition_utility_selection(
            value,
            row_key=item["row_key"],
            column=item["column"],
            new_value=item["candidate_value"],
            proposal_support_set_id=item["proposal_support_set_id"],
            declared_proposal_evidence_ids=item["proposal_evidence_ids"],
        )
        encoded = json.dumps(receipt, ensure_ascii=False)
        self.assertNotIn("Alpha", encoded)
        self.assertNotIn("2025", encoded)
        self.assertNotIn("verifier.example", encoded)
        self.assertFalse(
            receipt[
                "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
            ]
        )


if __name__ == "__main__":
    unittest.main()
