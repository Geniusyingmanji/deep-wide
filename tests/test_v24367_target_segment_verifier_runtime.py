from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24323_shared_prefix_cell_entropy import payload_sha256  # noqa: E402
from deepwide_agent.v24367_target_segment_verifier_runtime import (  # noqa: E402
    run_v24367_task,
    validate_result,
)
from test_v24342_semantic_active_runtime import Clock, limits  # noqa: E402


SEED = "c" * 64
TASK = {
    "opaque_id": "task_0123456789abcdef01234567",
    "question": (
        "Use public web sources to return one Markdown table about Alpha and "
        "Beta. The column names are: Name, Founding year. Return one table only."
    ),
}
PLAN = json.dumps(
    {
        "language": "English",
        "columns": ["wrong"],
        "row_target_hint": "",
        "queries": ["one", "two", "three", "four"],
    }
)
BASELINE = """```markdown
| Name | Founding year |
| --- | --- |
| Alpha | Unknown |
| Beta | Unknown |
```"""
CANDIDATE = """```markdown
| Name | Founding year |
| --- | --- |
| Alpha | 2025 |
| Beta | 2024 |
```"""
HIDDEN_MARKER = "TARGET_SEGMENT_HIDDEN_24367"


class Model:
    def __init__(self) -> None:
        self.requests = 0
        self.attempts = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.total_tokens = 0
        self.prompts: list[tuple[str, str, bool]] = []

    def complete(self, system, user, *, max_output_tokens, json_mode=False):
        del max_output_tokens
        self.prompts.append((system, user, json_mode))
        self.requests += 1
        self.attempts += 1
        self.input_tokens += 10
        self.output_tokens += 5
        self.total_tokens += 15
        if len(self.prompts) == 1:
            return SimpleNamespace(text=PLAN)
        if len(self.prompts) == 2:
            return SimpleNamespace(text=BASELINE)
        supports: list[dict] = []
        in_catalog = False
        for line in user.splitlines():
            if line == "PROGRAMMATIC SEMANTIC SUPPORT SETS:":
                in_catalog = True
                continue
            if in_catalog and line.startswith("Propose a revised table"):
                break
            if in_catalog and line.startswith("{"):
                supports.append(json.loads(line))
        declarations = []
        for row_key, candidate in (("Alpha", "2025"), ("Beta", "2024")):
            selected = next(
                item
                for item in supports
                if item["row_key"] == row_key
                and item["candidate_value"] == candidate
            )
            declarations.append(
                {
                    "row_key": row_key,
                    "column": "Founding year",
                    "support_set_id": selected["support_set_id"],
                    "evidence_ids": selected["evidence_ids"],
                }
            )
        return SimpleNamespace(
            text=json.dumps(
                {"candidate_table": CANDIDATE, "cell_support": declarations}
            )
        )


class Search:
    def __init__(
        self,
        *,
        hidden_mode: str = "support",
    ) -> None:
        self.hidden_mode = hidden_mode
        self.calls = 0
        self.failures = 0
        self.tool_calls = 0
        self.fetch_calls = 0
        self.fetch_failures = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.total_tokens = 0
        self.search_invocations = 0
        self.fetch_invocations = 0

    def search_many(self, queries, **kwargs):
        del queries, kwargs
        self.search_invocations += 1
        self.calls += 1
        self.tool_calls += 1
        indices = range(1, 7) if self.search_invocations == 1 else range(4, 13)
        return [
            {
                "query": "synthetic",
                "results": [
                    {
                        "title": f"record-{index}",
                        "url": f"https://host{index}.example/item/{self.search_invocations}",
                        "fetch_url": f"https://host{index}.example/item/{self.search_invocations}",
                    }
                    for index in indices
                ],
            }
        ]

    def fetch_urls(self, requests):
        self.fetch_invocations += 1
        values = list(requests)
        self.fetch_calls += len(values)
        hidden = self.fetch_invocations == 3
        if not hidden:
            content = (
                "Alpha was founded in 2025. Beta was established in 2024."
            )
        elif self.hidden_mode == "support":
            content = (
                f"Alpha was founded in 2025, while Beta was founded in 2024. "
                f"{HIDDEN_MARKER}"
            )
        elif self.hidden_mode == "conflict":
            content = (
                f"Alpha was founded in 2026, while Beta was founded in 2024. "
                f"{HIDDEN_MARKER}"
            )
        else:
            content = f"Alpha and Beta publish documentation. {HIDDEN_MARKER}"
        return [
            {
                "query": "synthetic",
                "results": [
                    {
                        "title": item["title"],
                        "url": item["url"],
                        "requested_url": item["url"],
                        "raw_content": content,
                    }
                ],
            }
            for item in values
        ]


class V24367TargetSegmentVerifierRuntimeTests(unittest.TestCase):
    def run_case(self, *, hidden_mode: str = "support"):
        model = Model()
        search = Search(hidden_mode=hidden_mode)
        value = run_v24367_task(
            TASK,
            model=model,
            search=search,
            partition_seed_sha256=SEED,
            limits=limits(),
            monotonic=Clock(),
        )
        validate_result(value)
        return value, model, search

    def test_target_segments_recover_two_cross_entity_false_conflicts(self) -> None:
        value, model, search = self.run_case()
        receipt = value["target_segment_verifier_receipt"]
        legacy = value["parent_result"]["hidden_verifier_receipt"]
        self.assertEqual(
            legacy["candidate_changed_cells_after_hidden_verifier"], 0
        )
        self.assertEqual(receipt["candidate_changed_cells_before_hidden_verifier"], 2)
        self.assertEqual(receipt["candidate_changed_cells_after_hidden_verifier"], 2)
        self.assertEqual(receipt["target_segment_recovered_cells"], 2)
        self.assertEqual(receipt["verification_status_counts"]["verified_candidate"], 2)
        self.assertEqual(receipt["selected_disposition_counts"], {"admit_target_segment_utility_support": 2})
        self.assertIn("| Alpha | 2025 |", value["candidate_prediction"])
        self.assertIn("| Beta | 2024 |", value["candidate_prediction"])
        self.assertEqual(model.requests, 3)
        self.assertEqual(search.calls, 2)
        self.assertEqual(search.fetch_calls, 10)

    def test_real_hidden_conflict_reverts_only_the_bound_target(self) -> None:
        value, _, _ = self.run_case(hidden_mode="conflict")
        receipt = value["target_segment_verifier_receipt"]
        self.assertEqual(receipt["candidate_changed_cells_after_hidden_verifier"], 1)
        self.assertIn("| Alpha | Unknown |", value["candidate_prediction"])
        self.assertIn("| Beta | 2024 |", value["candidate_prediction"])
        self.assertEqual(receipt["selected_verification_status_counts"]["independent_conflict"], 1)
        self.assertEqual(receipt["selected_verification_status_counts"]["verified_candidate"], 1)

    def test_missing_hidden_support_preserves_parent_entropy_but_zero_utility(self) -> None:
        value, _, _ = self.run_case(hidden_mode="missing")
        receipt = value["target_segment_verifier_receipt"]
        self.assertEqual(receipt["candidate_changed_cells_after_hidden_verifier"], 0)
        self.assertGreater(
            receipt["selected_proposal_conditional_entropy_reduction_nats"], 0
        )
        self.assertEqual(receipt["utility_aligned_entropy_credit_nats"], 0)
        self.assertEqual(
            receipt["selected_verification_status_counts"],
            {"no_independent_candidate_support": 2},
        )

    def test_both_hidden_pages_remain_excluded_from_model_prompts(self) -> None:
        value, model, _ = self.run_case()
        pages = value["parent_result"]["private_replay_state"]["verifier_pages"]
        prompt_text = "\n".join(user for _, user, _ in model.prompts)
        self.assertEqual(len(pages), 2)
        self.assertNotIn(HIDDEN_MARKER, prompt_text)
        for page_ in pages:
            self.assertIn(HIDDEN_MARKER, page_["content"])
            self.assertNotIn(page_["content"], prompt_text)

    def test_parent_utility_and_result_tamper_fail_replay(self) -> None:
        value, _, _ = self.run_case()
        cases = ("parent", "utility", "candidate", "receipt")
        for field in cases:
            with self.subTest(field=field):
                altered = copy.deepcopy(value)
                if field == "parent":
                    altered["parent_result"]["private_replay_state"][
                        "verifier_pages"
                    ][0]["content"] += " tamper"
                    parent = altered["parent_result"]
                    parent.pop("result_sha256")
                    parent["result_sha256"] = payload_sha256(parent)
                elif field == "utility":
                    catalog = altered["private_replay_state"][
                        "target_segment_utility_catalog"
                    ]
                    record = next(
                        item
                        for item in catalog["verification_records"]
                        if item["verification_status"] == "verified_candidate"
                    )
                    record["utility_aligned_entropy_credit_nats"] = 0.0
                    catalog.pop("catalog_payload_sha256")
                    catalog["catalog_payload_sha256"] = payload_sha256(catalog)
                elif field == "candidate":
                    altered["candidate_prediction"] = BASELINE
                elif field == "receipt":
                    altered["target_segment_verifier_receipt"][
                        "target_segment_recovered_cells"
                    ] = 0
                    receipt = altered["target_segment_verifier_receipt"]
                    receipt.pop("receipt_sha256")
                    receipt["receipt_sha256"] = payload_sha256(receipt)
                altered.pop("result_sha256")
                altered["result_sha256"] = payload_sha256(altered)
                with self.assertRaises(ValueError):
                    validate_result(altered)

    def test_privileged_input_is_rejected_before_any_effect(self) -> None:
        model = Model()
        search = Search()
        with self.assertRaises(ValueError):
            run_v24367_task(
                {**TASK, "question_type": "forbidden"},
                model=model,
                search=search,
                partition_seed_sha256=SEED,
                limits=limits(),
                monotonic=Clock(),
            )
        self.assertEqual(model.requests, 0)
        self.assertEqual(search.calls, 0)
        self.assertEqual(search.fetch_calls, 0)

    def test_public_receipt_is_content_free_and_label_blind(self) -> None:
        value, _, _ = self.run_case()
        receipt = value["target_segment_verifier_receipt"]
        encoded = json.dumps(receipt, ensure_ascii=False)
        for private in ("Alpha", "Beta", "2025", "2024", "host1.example"):
            self.assertNotIn(private, encoded)
        self.assertFalse(
            receipt[
                "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
            ]
        )
        self.assertFalse(receipt["benchmark_launch_or_evaluator_authorized"])


if __name__ == "__main__":
    unittest.main()
