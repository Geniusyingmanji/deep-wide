from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24655_unknown_cell_targeted_runtime import (  # noqa: E402
    _independent_pages,
    unknown_cell_targets,
)
from deepwide_agent.v24659_support_closure_runtime import (  # noqa: E402
    MINIMUM_INDEPENDENT_SUPPORT_SOURCES,
    deterministic_support_closure,
    gate_unknown_candidate_with_support_closure,
)
from test_v24655_unknown_cell_targeted_runtime import Search, table  # noqa: E402


def pages(count: int = 2):
    requests = [
        {
            "url": f"https://target-{index}.example/record",
            "query": "",
            "title": "",
        }
        for index in range(count)
    ]
    return _independent_pages(
        Search(targeted_sources=count).fetch_urls(requests), page_chars=5_000
    )


class V24659SupportClosureTests(unittest.TestCase):
    def test_one_declared_id_closes_to_two_exact_local_sources(self) -> None:
        value = deterministic_support_closure(
            row_key="Alpha Phone",
            new_value="2024-09-20",
            declared_evidence_ids=["R0001"],
            targeted_pages=pages(),
        )
        self.assertEqual(value["declared_evidence_ids"], ["R0001"])
        self.assertEqual(value["closed_evidence_ids"], ["R0001", "R0002"])
        self.assertEqual(value["added_evidence_id_count"], 1)
        self.assertTrue(value["minimum_independent_support_sources_unchanged"])
        self.assertFalse(value["entropy_or_task_credit_used"])

    def test_missing_model_citations_can_close_without_changing_value(self) -> None:
        value = deterministic_support_closure(
            row_key="Alpha Phone",
            new_value="2024-09-20",
            declared_evidence_ids=[],
            targeted_pages=pages(),
        )
        self.assertEqual(value["closed_evidence_ids"], ["R0001", "R0002"])
        self.assertFalse(value["proposal_value_changed"])

    def test_unrelated_or_single_page_still_fails_two_source_gate(self) -> None:
        one = deterministic_support_closure(
            row_key="Alpha Phone",
            new_value="2024-09-20",
            declared_evidence_ids=["R0001"],
            targeted_pages=pages(1),
        )
        self.assertEqual(len(one["closed_evidence_ids"]), 1)
        self.assertEqual(MINIMUM_INDEPENDENT_SUPPORT_SOURCES, 2)

    def test_gate_admits_only_after_exact_support_closure(self) -> None:
        candidate, admissions, counts = gate_unknown_candidate_with_support_closure(
            baseline=table(),
            proposed=table("2024-09-20"),
            evidence_declarations=[
                {
                    "row_key": "Alpha Phone",
                    "column": "Release Date",
                    "evidence_ids": ["R0001"],
                }
            ],
            targeted_pages=pages(),
            targets=unknown_cell_targets(table()),
        )
        self.assertIn("| Alpha Phone | 2024-09-20 | Acme |", candidate)
        self.assertTrue(admissions[0]["admitted"])
        self.assertEqual(counts["admitted_cell_change_count"], 1)
        self.assertEqual(counts["support_closure_added_evidence_id_count"], 1)
        self.assertEqual(counts["support_threshold_relaxed"], 0)
        self.assertEqual(counts["proposal_value_changed_by_closure"], 0)

    def test_gate_rejects_single_source_after_closure(self) -> None:
        candidate, admissions, counts = gate_unknown_candidate_with_support_closure(
            baseline=table(),
            proposed=table("2024-09-20"),
            evidence_declarations=[],
            targeted_pages=pages(1),
            targets=unknown_cell_targets(table()),
        )
        self.assertEqual(candidate, table())
        self.assertFalse(admissions[0]["admitted"])
        self.assertEqual(counts["admitted_cell_change_count"], 0)
        self.assertEqual(counts["support_threshold_relaxed"], 0)

    def test_forbidden_non_unknown_mutation_remains_fail_closed(self) -> None:
        candidate, admissions, counts = gate_unknown_candidate_with_support_closure(
            baseline=table(),
            proposed=table("2024-09-20", "Changed Maker"),
            evidence_declarations=[],
            targeted_pages=pages(),
            targets=unknown_cell_targets(table()),
        )
        self.assertEqual(candidate, table())
        self.assertEqual(admissions, [])
        self.assertEqual(counts["forbidden_mutation_count"], 1)

    def test_no_privileged_runtime_capability(self) -> None:
        value = deterministic_support_closure(
            row_key="Alpha Phone",
            new_value="2024-09-20",
            declared_evidence_ids=[],
            targeted_pages=pages(),
        )
        self.assertFalse(
            value[
                "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
            ]
        )
        self.assertTrue(value["uses_only_already_fetched_targeted_pages"])


if __name__ == "__main__":
    unittest.main()
