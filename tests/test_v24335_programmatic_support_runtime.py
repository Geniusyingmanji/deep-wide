from __future__ import annotations

import copy
import json
import re
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24335_programmatic_support_runtime import (  # noqa: E402
    payload_sha256,
    run_v24335_task,
    run_v24335_total_task,
    validate_result,
)


TASK = {
    "opaque_id": "task_0123456789abcdef01234567",
    "question": (
        "Use web evidence to complete the table. The column names are: Name, Year. "
        "Return one Markdown table only."
    ),
}
PLAN = json.dumps(
    {
        "language": "English",
        "columns": ["wrong"],
        "row_target_hint": "",
        "queries": ["query one", "query two", "query three", "query four"],
    }
)
BASELINE_UNKNOWN = """```markdown
| Name | Year |
| --- | --- |
| Alpha | Unknown |
```"""
BASELINE_KNOWN = """```markdown
| Name | Year |
| --- | --- |
| Alpha | 2024 |
```"""


class Clock:
    def __init__(self) -> None:
        self.value = 100.0

    def __call__(self) -> float:
        self.value += 0.001
        return self.value


class AdaptiveModel:
    def __init__(
        self,
        baseline: str = BASELINE_UNKNOWN,
        *,
        revision_mode: str = "valid",
        baseline_failure: BaseException | None = None,
        recovery: str = BASELINE_KNOWN,
        fatal_plan: BaseException | None = None,
    ) -> None:
        self.baseline = baseline
        self.revision_mode = revision_mode
        self.baseline_failure = baseline_failure
        self.recovery = recovery
        self.fatal_plan = fatal_plan
        self.requests = 0
        self.attempts = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.total_tokens = 0
        self.prompts: list[tuple[str, str, bool]] = []

    def complete(self, system, user, *, max_output_tokens, json_mode=False):
        self.prompts.append((system, user, json_mode))
        self.requests += 1
        self.attempts += 1
        self.input_tokens += 10
        self.output_tokens += 5
        self.total_tokens += 15
        index = len(self.prompts)
        if index == 1:
            if self.fatal_plan is not None:
                raise self.fatal_plan
            return SimpleNamespace(text=PLAN)
        if index == 2:
            if self.baseline_failure is not None:
                raise self.baseline_failure
            return SimpleNamespace(text=self.baseline)
        if self.baseline_failure is not None:
            return SimpleNamespace(text=self.recovery)
        if self.revision_mode == "raise":
            raise RuntimeError("private synthetic revision failure")
        support_lines = []
        in_catalog = False
        for line in user.splitlines():
            if line == "PROGRAMMATIC ELIGIBLE SUPPORT SETS:":
                in_catalog = True
                continue
            if in_catalog and line.startswith("Propose a revised table"):
                break
            if in_catalog and line.startswith("{"):
                support_lines.append(json.loads(line))
        support = next(
            item for item in support_lines if item["candidate_value"] == "2025"
        )
        if self.revision_mode == "fabricated":
            support = {
                **support,
                "support_set_id": "f" * 64,
                "evidence_ids": ["R9999"],
            }
        return SimpleNamespace(
            text=json.dumps(
                {
                    "candidate_table": """```markdown
| Name | Year |
| --- | --- |
| Alpha | 2025 |
```""",
                    "cell_support": [
                        {
                            "row_key": "Alpha",
                            "column": "Year",
                            "support_set_id": support["support_set_id"],
                            "evidence_ids": support["evidence_ids"],
                        }
                    ],
                }
            )
        )


class FakeSearch:
    def __init__(
        self,
        *,
        reserve_entity: str = "Alpha",
        reserve_value: str = "2025",
        collapse_reserve_domain: bool = False,
        reserve_fetch_failure: bool = False,
    ) -> None:
        self.reserve_entity = reserve_entity
        self.reserve_value = reserve_value
        self.collapse_reserve_domain = collapse_reserve_domain
        self.reserve_fetch_failure = reserve_fetch_failure
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
        self.search_invocations += 1
        self.calls += 1
        self.tool_calls += 1
        self.input_tokens += 10
        self.output_tokens += 2
        self.total_tokens += 12
        results = []
        for index in range(1, 11):
            if self.collapse_reserve_domain and index >= 8:
                host = f"sub{index}.shared.example"
            else:
                host = f"host{index}.example"
            results.append(
                {
                    "title": f"record-{index}",
                    "url": f"https://{host}/item",
                    "fetch_url": f"https://{host}/item",
                    "content": "",
                }
            )
        return [
            {
                "query": "content-free synthetic query",
                "answer": "",
                "results": results,
                "error": None,
            }
        ]

    def fetch_urls(self, requests):
        self.fetch_invocations += 1
        values = list(requests)
        self.fetch_calls += len(values)
        reserve = self.fetch_invocations == 2
        if reserve and self.reserve_fetch_failure:
            self.fetch_failures += len(values)
            raise RuntimeError("private synthetic reserve fetch failure")
        return [
            {
                "query": "content-free synthetic query",
                "results": [
                    {
                        "title": item["title"],
                        "url": item["url"],
                        "requested_url": item["url"],
                        "raw_content": (
                            f"Independent official record. {self.reserve_entity} "
                            f"Year is {self.reserve_value}. End of record."
                            if reserve
                            else "Independent core record about Alpha without the year."
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


class V24335ProgrammaticSupportRuntimeTests(unittest.TestCase):
    def run_case(self, model: AdaptiveModel, search: FakeSearch):
        value = run_v24335_task(
            TASK,
            model=model,
            search=search,
            limits=limits(),
            monotonic=Clock(),
        )
        validate_result(value)
        return value

    def test_catalog_is_built_before_revision_and_natural_change_is_admitted(self) -> None:
        model = AdaptiveModel()
        search = FakeSearch()
        value = self.run_case(model, search)
        core = value["core_result"]
        support = value["support_runtime_receipt"]
        self.assertIn("| Alpha | 2025 |", core["candidate_prediction"])
        self.assertNotEqual(
            core["candidate_prediction"], core["baseline_prediction"]
        )
        self.assertEqual(model.requests, 3)
        self.assertTrue(support["catalog_built_before_revision_model_admission"])
        self.assertEqual(support["catalog_status"], "built_eligible")
        self.assertTrue(support["revision_model_admitted"])
        self.assertTrue(support["revision_gate_applied"])
        self.assertEqual(support["admitted_cell_changes"], 1)
        self.assertGreater(
            support["credited_conditional_entropy_reduction_nats"], 0
        )
        revision_prompt = model.prompts[2][1]
        self.assertIn("PROGRAMMATIC ELIGIBLE SUPPORT SETS", revision_prompt)
        self.assertRegex(revision_prompt, r'"support_set_id": "[0-9a-f]{64}"')

    def test_empty_catalog_skips_third_model_call_and_identity_handoff(self) -> None:
        model = AdaptiveModel()
        search = FakeSearch(reserve_entity="Beta")
        value = self.run_case(model, search)
        core = value["core_result"]
        support = value["support_runtime_receipt"]
        self.assertEqual(model.requests, 2)
        self.assertEqual(support["catalog_status"], "built_empty")
        self.assertTrue(support["third_model_call_skipped_no_eligible_support"])
        self.assertFalse(support["revision_model_admitted"])
        self.assertEqual(
            core["candidate_prediction"], core["baseline_prediction"]
        )

    def test_same_registrable_domain_skips_third_model_call(self) -> None:
        model = AdaptiveModel()
        value = self.run_case(
            model, FakeSearch(collapse_reserve_domain=True)
        )
        support = value["support_runtime_receipt"]
        self.assertEqual(model.requests, 2)
        self.assertEqual(support["catalog_status"], "built_empty")
        self.assertGreater(
            support["catalog_quarantined_candidate_groups"].get(
                "quarantine_insufficient_independence", 0
            ),
            0,
        )

    def test_fabricated_support_selection_is_identity_and_zero_credit(self) -> None:
        model = AdaptiveModel(revision_mode="fabricated")
        value = self.run_case(model, FakeSearch())
        core = value["core_result"]
        support = value["support_runtime_receipt"]
        self.assertEqual(model.requests, 3)
        self.assertTrue(support["revision_gate_applied"])
        self.assertEqual(support["admitted_cell_changes"], 0)
        self.assertEqual(support["credited_conditional_entropy_reduction_nats"], 0)
        self.assertEqual(
            support["resolution_dispositions"],
            {"quarantine_unknown_support_set": 1},
        )
        self.assertEqual(
            core["candidate_prediction"], core["baseline_prediction"]
        )

    def test_baseline_recovery_uses_third_call_and_never_builds_catalog(self) -> None:
        model = AdaptiveModel(
            baseline_failure=RuntimeError("private synthetic baseline failure")
        )
        value = self.run_case(model, FakeSearch())
        core = value["core_result"]
        support = value["support_runtime_receipt"]
        self.assertEqual(model.requests, 3)
        self.assertIn("| Alpha | 2024 |", core["baseline_prediction"])
        self.assertEqual(support["catalog_status"], "not_built_ineligible_path")
        self.assertFalse(support["revision_model_admitted"])
        self.assertEqual(
            core["shared_prefix_revision_receipt"]["model_effect_stages"],
            ["plan", "baseline_synthesis", "baseline_recovery"],
        )

    def test_reserve_fetch_failure_builds_empty_catalog_and_skips_revision(self) -> None:
        model = AdaptiveModel()
        value = self.run_case(
            model, FakeSearch(reserve_fetch_failure=True)
        )
        support = value["support_runtime_receipt"]
        self.assertEqual(model.requests, 2)
        self.assertEqual(support["catalog_status"], "built_empty")
        self.assertEqual(support["catalog_page_count"], 0)
        self.assertTrue(support["third_model_call_skipped_no_eligible_support"])

    def test_total_boundary_preserves_effect_lower_bounds(self) -> None:
        model = AdaptiveModel(fatal_plan=KeyboardInterrupt())
        search = FakeSearch()
        value = run_v24335_total_task(
            TASK,
            model=model,
            search=search,
            limits=limits(),
            monotonic=Clock(),
        )
        validate_result(value)
        core_receipt = value["core_result"]["shared_prefix_revision_receipt"]
        support = value["support_runtime_receipt"]
        self.assertFalse(core_receipt["effect_accounting_complete"])
        self.assertEqual(core_receipt["unattributed_model_effects_lower_bound"], 1)
        self.assertEqual(core_receipt["unattributed_model_attempts_lower_bound"], 1)
        self.assertEqual(support["catalog_status"], "runtime_fallback")
        self.assertTrue(support["candidate_identity_handoff"])

    def test_privileged_input_fails_before_any_effect(self) -> None:
        model = AdaptiveModel()
        search = FakeSearch()
        with self.assertRaisesRegex(ValueError, "privileged"):
            run_v24335_total_task(
                {**TASK, "question_type": "forbidden"},
                model=model,
                search=search,
                limits=limits(),
                monotonic=Clock(),
            )
        self.assertEqual(model.requests, 0)
        self.assertEqual(search.calls, 0)

    def test_support_receipt_emits_no_task_or_evidence_content(self) -> None:
        value = self.run_case(AdaptiveModel(), FakeSearch())
        encoded = json.dumps(value["support_runtime_receipt"], ensure_ascii=False)
        for forbidden in (
            TASK["opaque_id"],
            TASK["question"],
            "Alpha",
            "2025",
            "R0001",
            "host8.example",
        ):
            self.assertNotIn(forbidden, encoded)
        self.assertIsNone(re.search(r"task_[0-9a-f]{24}", encoded))

    def test_resealed_proposal_or_page_tamper_fails_replay(self) -> None:
        value = self.run_case(AdaptiveModel(), FakeSearch())
        for field in ("proposed_table", "catalog_pages"):
            with self.subTest(field=field):
                altered = copy.deepcopy(value)
                private = altered["support_runtime_private_state"]
                if field == "proposed_table":
                    private[field] = str(private[field]).replace("2025", "2026")
                else:
                    private[field][0]["content"] = str(
                        private[field][0]["content"]
                    ).replace("2025", "2026")
                altered.pop("result_sha256")
                altered["result_sha256"] = payload_sha256(altered)
                with self.assertRaises(ValueError):
                    validate_result(altered)


if __name__ == "__main__":
    unittest.main()
