from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24323_shared_prefix_cell_entropy import payload_sha256  # noqa: E402
from deepwide_agent.v24342_semantic_active_runtime import (  # noqa: E402
    run_v24342_task,
    run_v24342_total_task,
    validate_result,
)


TASK = {
    "opaque_id": "task_0123456789abcdef01234567",
    "question": (
        "Use web evidence to complete the table. The column names are: Name, "
        "Founding year. Return one Markdown table only."
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
BASELINE_UNKNOWN = """```markdown
| Name | Founding year |
| --- | --- |
| Alpha | Unknown |
```"""
BASELINE_KNOWN = """```markdown
| Name | Founding year |
| --- | --- |
| Alpha | 2025 |
```"""


class Clock:
    def __init__(self) -> None:
        self.value = 100.0

    def __call__(self) -> float:
        self.value += 0.001
        return self.value


class Model:
    def __init__(
        self,
        *,
        baseline: str = BASELINE_UNKNOWN,
        baseline_failure: BaseException | None = None,
        fatal: BaseException | None = None,
        fabricate: bool = False,
    ) -> None:
        self.baseline = baseline
        self.baseline_failure = baseline_failure
        self.fatal = fatal
        self.fabricate = fabricate
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
        if self.fatal is not None:
            raise self.fatal
        index = len(self.prompts)
        if index == 1:
            return SimpleNamespace(text=PLAN)
        if index == 2:
            if self.baseline_failure is not None:
                raise self.baseline_failure
            return SimpleNamespace(text=self.baseline)
        if self.baseline_failure is not None:
            return SimpleNamespace(text=BASELINE_KNOWN)
        support_lines = []
        in_catalog = False
        for line in user.splitlines():
            if line == "PROGRAMMATIC SEMANTIC SUPPORT SETS:":
                in_catalog = True
                continue
            if in_catalog and line.startswith("Propose a revised table"):
                break
            if in_catalog and line.startswith("{"):
                support_lines.append(json.loads(line))
        support = next(item for item in support_lines if item["candidate_value"] == "2025")
        if self.fabricate:
            support = {**support, "support_set_id": "f" * 64, "evidence_ids": ["R9999"]}
        return SimpleNamespace(
            text=json.dumps(
                {
                    "candidate_table": BASELINE_KNOWN,
                    "cell_support": [
                        {
                            "row_key": "Alpha",
                            "column": "Founding year",
                            "support_set_id": support["support_set_id"],
                            "evidence_ids": support["evidence_ids"],
                        }
                    ],
                }
            )
        )


class Search:
    def __init__(self, *, eligible: bool = True, fatal: bool = False) -> None:
        self.eligible = eligible
        self.fatal = fatal
        self.calls = 0
        self.failures = 0
        self.tool_calls = 0
        self.fetch_calls = 0
        self.fetch_failures = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.total_tokens = 0
        self.fetch_invocations = 0

    def search_many(self, queries, **kwargs):
        del queries, kwargs
        if self.fatal:
            raise KeyboardInterrupt()
        self.calls += 1
        self.tool_calls += 1
        self.input_tokens += 10
        self.output_tokens += 2
        self.total_tokens += 12
        return [
            {
                "query": "synthetic",
                "results": [
                    {
                        "title": f"record-{index}",
                        "url": f"https://host{index}.example/item",
                        "fetch_url": f"https://host{index}.example/item",
                    }
                    for index in range(1, 11)
                ],
            }
        ]

    def fetch_urls(self, requests):
        self.fetch_invocations += 1
        values = list(requests)
        self.fetch_calls += len(values)
        core = self.fetch_invocations == 1
        return [
            {
                "query": "synthetic",
                "results": [
                    {
                        "title": item["title"],
                        "url": item["url"],
                        "requested_url": item["url"],
                        "raw_content": (
                            "Alpha was founded in 2025 according to this record."
                            if self.eligible and (core or not core)
                            else "Alpha won an award in 2025."
                        ),
                    }
                ],
            }
            for item in values
        ]


def limits() -> ScoreFirstLimits:
    return ScoreFirstLimits(
        wall_seconds=120,
        model_calls=3,
        search_queries=4,
        fetch_targets=10,
        search_results_per_query=3,
        evidence_chars=60_000,
        page_chars=5_000,
        plan_output_tokens=4_000,
        synthesis_output_tokens=30_000,
        repair_output_tokens=12_000,
    )


class V24342SemanticActiveRuntimeTests(unittest.TestCase):
    def run_case(self, model: Model, search: Search):
        value = run_v24342_task(
            TASK, model=model, search=search, limits=limits(), monotonic=Clock()
        )
        validate_result(value)
        return value

    def test_same_ten_raw_pages_precede_baseline_and_semantic_change_is_admitted(self) -> None:
        model = Model()
        value = self.run_case(model, Search())
        core = value["core_result"]
        receipt = value["semantic_active_receipt"]
        private = value["semantic_active_private_state"]
        self.assertEqual(receipt["core_page_count"], 7)
        self.assertEqual(receipt["reserve_page_count"], 3)
        self.assertEqual(
            receipt["baseline_active_evidence_sha256"],
            receipt["candidate_active_evidence_sha256"],
        )
        self.assertLess(
            private["stage_trace"].index("reserve_fetch_attempted"),
            private["stage_trace"].index("baseline_model_admitted"),
        )
        self.assertIn("[C0001]", model.prompts[1][1])
        self.assertIn("[R0001]", model.prompts[1][1])
        self.assertIn("[C0001]", model.prompts[2][1])
        self.assertIn("[R0001]", model.prompts[2][1])
        self.assertIn("| Alpha | 2025 |", core["candidate_prediction"])
        self.assertEqual(receipt["admitted_cell_changes"], 1)
        self.assertGreater(receipt["credited_conditional_entropy_reduction_nats"], 0)
        self.assertTrue(private["active_resolution_receipts"][0]["admitted"])

    def test_no_semantic_relation_skips_third_model_call(self) -> None:
        model = Model()
        value = self.run_case(model, Search(eligible=False))
        receipt = value["semantic_active_receipt"]
        self.assertEqual(model.requests, 2)
        self.assertEqual(receipt["catalog_status"], "built_empty")
        self.assertTrue(receipt["third_model_call_skipped_no_eligible_support"])
        self.assertEqual(
            value["core_result"]["baseline_prediction"],
            value["core_result"]["candidate_prediction"],
        )

    def test_baseline_recovery_excludes_catalog_and_revision(self) -> None:
        model = Model(baseline_failure=RuntimeError("synthetic"))
        value = self.run_case(model, Search())
        receipt = value["semantic_active_receipt"]
        self.assertEqual(model.requests, 3)
        self.assertEqual(receipt["catalog_status"], "not_built_ineligible_path")
        self.assertFalse(receipt["revision_model_admitted"])
        self.assertTrue(receipt["candidate_identity_handoff"])

    def test_fabricated_support_is_zero_credit_identity(self) -> None:
        value = self.run_case(Model(fabricate=True), Search())
        receipt = value["semantic_active_receipt"]
        self.assertEqual(receipt["proposed_cell_changes"], 1)
        self.assertEqual(receipt["admitted_cell_changes"], 0)
        self.assertEqual(receipt["credited_conditional_entropy_reduction_nats"], 0)
        self.assertTrue(receipt["candidate_identity_handoff"])

    def test_raw_page_projection_and_gate_tamper_all_fail_replay(self) -> None:
        value = self.run_case(Model(), Search())
        for field in ("raw", "projection", "proposal", "gate"):
            with self.subTest(field=field):
                altered = copy.deepcopy(value)
                private = altered["semantic_active_private_state"]
                if field == "raw":
                    private["raw_core_pages"][0]["content"] += " tamper"
                elif field == "projection":
                    private["semantic_active_catalog"]["projections"][0][
                        "relation_span_sha256"
                    ] = "0" * 64
                elif field == "proposal":
                    private["model_proposal"] += " "
                else:
                    private["revision_gate_result"]["admitted_cell_changes"] = 0
                altered.pop("result_sha256")
                altered["result_sha256"] = payload_sha256(altered)
                with self.assertRaises(ValueError):
                    validate_result(altered)

    def test_privileged_runtime_key_is_rejected_before_effect(self) -> None:
        model = Model()
        search = Search()
        with self.assertRaises(ValueError):
            run_v24342_task(
                {**TASK, "category": "forbidden"},
                model=model,
                search=search,
                limits=limits(),
                monotonic=Clock(),
            )
        self.assertEqual(model.requests, 0)
        self.assertEqual(search.calls, 0)

    def test_total_fallback_preserves_effect_lower_bounds(self) -> None:
        model = Model()
        search = Search(fatal=True)
        value = run_v24342_total_task(
            TASK, model=model, search=search, limits=limits(), monotonic=Clock()
        )
        validate_result(value)
        core_receipt = value["core_result"]["shared_prefix_revision_receipt"]
        self.assertFalse(core_receipt["effect_accounting_complete"])
        self.assertGreaterEqual(core_receipt["unattributed_model_effects_lower_bound"], 1)
        self.assertEqual(value["semantic_active_receipt"]["catalog_status"], "runtime_fallback")


if __name__ == "__main__":
    unittest.main()
