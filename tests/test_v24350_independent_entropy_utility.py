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
from deepwide_agent.v24333_programmatic_support_catalog import CellTarget  # noqa: E402
from deepwide_agent.v24350_independent_entropy_utility import (  # noqa: E402
    build_independent_utility_catalog,
    render_proposal_catalog,
    resolve_independent_utility_selection,
    validate_independent_utility_catalog,
    validate_independent_utility_receipt,
)


SEED = "5" * 64
TARGET = CellTarget("Alpha", "Founding year", "Unknown")


def pages(value: str = "2025") -> list[dict]:
    return [
        {
            "host": f"source{index}.example",
            "content": f"Alpha was founded in {value} according to this source.",
            "fetch_integrity": True,
        }
        for index in range(1, 5)
    ]


class V24350IndependentEntropyUtilityTests(unittest.TestCase):
    def positive_catalog(self) -> dict:
        value = build_independent_utility_catalog(
            [TARGET], pages(), partition_seed_sha256=SEED
        )
        self.assertGreater(value["utility_aligned_support_set_count"], 0)
        return value

    def test_preproposal_split_admits_independently_verified_entropy_credit(self) -> None:
        catalog = self.positive_catalog()
        item = catalog["utility_sets"][0]
        receipt = resolve_independent_utility_selection(
            catalog,
            row_key=item["row_key"],
            column=item["column"],
            new_value=item["candidate_value"],
            utility_set_id=item["utility_set_id"],
            declared_proposal_evidence_ids=item["proposal_evidence_ids"],
        )
        self.assertTrue(receipt["admitted"])
        self.assertEqual(receipt["verifier_outcome_delta"], 1)
        self.assertGreater(receipt["utility_aligned_entropy_credit_nats"], 0)
        self.assertEqual(
            receipt["utility_aligned_entropy_credit_nats"],
            receipt["proposal_conditional_entropy_reduction_nats"],
        )

    def test_source_partition_is_content_independent_and_disjoint(self) -> None:
        before = self.positive_catalog()
        after = build_independent_utility_catalog(
            [TARGET], pages("2026"), partition_seed_sha256=SEED
        )
        self.assertEqual(
            before["proposal_source_key_sha256s"],
            after["proposal_source_key_sha256s"],
        )
        self.assertEqual(
            before["verifier_source_key_sha256s"],
            after["verifier_source_key_sha256s"],
        )
        self.assertFalse(
            set(before["proposal_source_key_sha256s"])
            & set(before["verifier_source_key_sha256s"])
        )
        self.assertFalse(before["candidate_value_or_entropy_used_for_source_partition"])

    def test_hidden_verifier_conflict_quarantines_utility(self) -> None:
        positive = self.positive_catalog()
        verifier_hosts = {page["host"] for page in positive["verifier_pages"]}
        conflicted = pages()
        for page in conflicted:
            if page["host"] in verifier_hosts:
                page["content"] = "Alpha was founded in 2024 according to this source."
        catalog = build_independent_utility_catalog(
            [TARGET], conflicted, partition_seed_sha256=SEED
        )
        self.assertEqual(catalog["utility_aligned_support_set_count"], 0)
        self.assertGreater(
            catalog["quarantine_reasons"].get(
                "quarantine_no_independent_candidate_support", 0
            )
            + catalog["quarantine_reasons"].get("quarantine_independent_conflict", 0),
            0,
        )

    def test_proposal_render_hides_verifier_pages_hosts_and_receipts(self) -> None:
        catalog = self.positive_catalog()
        rendered = render_proposal_catalog(catalog)
        self.assertIn("utility_set_id", rendered)
        for page in catalog["verifier_pages"]:
            self.assertNotIn(page["host"], rendered)
            self.assertNotIn(page["content"], rendered)
        for item in catalog["utility_sets"]:
            for digest in item["verifier_projection_receipt_sha256s"]:
                self.assertNotIn(digest, rendered)

    def test_wrong_selection_binding_has_zero_credit(self) -> None:
        catalog = self.positive_catalog()
        item = catalog["utility_sets"][0]
        cases = (
            {"row_key": "Beta"},
            {"new_value": "2026"},
            {"declared_proposal_evidence_ids": ["R9999"]},
            {"utility_set_id": "f" * 64},
        )
        base = {
            "row_key": item["row_key"],
            "column": item["column"],
            "new_value": item["candidate_value"],
            "utility_set_id": item["utility_set_id"],
            "declared_proposal_evidence_ids": item["proposal_evidence_ids"],
        }
        for patch in cases:
            with self.subTest(patch=patch):
                receipt = resolve_independent_utility_selection(
                    catalog, **{**base, **patch}
                )
                self.assertFalse(receipt["admitted"])
                self.assertEqual(receipt["utility_aligned_entropy_credit_nats"], 0)

    def test_catalog_and_receipt_tamper_fail_replay(self) -> None:
        catalog = self.positive_catalog()
        altered = copy.deepcopy(catalog)
        altered["utility_sets"][0]["verifier_outcome_delta"] = 0
        altered.pop("catalog_payload_sha256")
        altered["catalog_payload_sha256"] = payload_sha256(altered)
        with self.assertRaises(ValueError):
            validate_independent_utility_catalog(altered)

        item = catalog["utility_sets"][0]
        receipt = resolve_independent_utility_selection(
            catalog,
            row_key=item["row_key"],
            column=item["column"],
            new_value=item["candidate_value"],
            utility_set_id=item["utility_set_id"],
            declared_proposal_evidence_ids=item["proposal_evidence_ids"],
        )
        receipt["verifier_conflicting_source_count"] = 1
        receipt.pop("receipt_sha256")
        receipt["receipt_sha256"] = payload_sha256(receipt)
        with self.assertRaises(ValueError):
            validate_independent_utility_receipt(receipt)

    def test_public_receipt_is_content_free_and_label_blind(self) -> None:
        catalog = self.positive_catalog()
        item = catalog["utility_sets"][0]
        receipt = resolve_independent_utility_selection(
            catalog,
            row_key=item["row_key"],
            column=item["column"],
            new_value=item["candidate_value"],
            utility_set_id=item["utility_set_id"],
            declared_proposal_evidence_ids=item["proposal_evidence_ids"],
        )
        encoded = json.dumps(receipt, ensure_ascii=False)
        self.assertNotIn("Alpha", encoded)
        self.assertNotIn("2025", encoded)
        for page in catalog["original_pages"]:
            self.assertNotIn(page["host"], encoded)
            self.assertNotIn(page["content"], encoded)
        self.assertFalse(
            receipt[
                "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
            ]
        )
        self.assertFalse(
            receipt[
                "file_environment_network_model_search_fetch_process_or_evaluator_accessed"
            ]
        )


if __name__ == "__main__":
    unittest.main()
