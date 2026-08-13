from __future__ import annotations

import ast
import copy
import json
import sys
import tempfile
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25253_outer_physical_cap_observed_runtime as cap  # noqa: E402
from deepwide_agent import v25354_pre_effect_query_compatible_grounded_fact_runtime as frozen_projector  # noqa: E402
from deepwide_agent import v25370_shared_synthesis_changed_safe_runtime as parent  # noqa: E402
from deepwide_agent import v25375_schema_total_changed_safe_runtime as target  # noqa: E402
from deepwide_agent.clients import ModelResult  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import (  # noqa: E402
    DeadlineAwareGlobalModelSlotLimiter,
)
from test_v25123_visible_legacy_query_compatible_runtime import (  # noqa: E402
    QUESTION,
    TASK,
    limits,
)
from test_v25349_shared_prefix_grounded_fact_paired_runtime import (  # noqa: E402
    FACT_QUOTE,
    FactSearch,
)


EXPANDED_QUESTION = (
    "Identify the country matching capital New Delhi and currency INR, then use "
    "the IANA Root Zone Database. Please output one Markdown table with the "
    "columns, in this exact order:\nDomain | Type | TLD Manager\nPreserve spelling."
)
NO_EXPLICIT_QUESTION = (
    "Identify the country matching capital New Delhi and currency INR, then "
    "return the requested IANA Root Zone Database facts in one table."
)


class TotalModel:
    def __init__(self, *, plan_columns=None, invalid_plan: bool = False) -> None:
        self.plan_columns = plan_columns
        self.invalid_plan = invalid_plan
        self.requests = self.attempts = 0
        self.input_tokens = self.output_tokens = self.total_tokens = 0
        self.logical_calls = 0

    def complete(self, system, user, *, max_output_tokens, json_mode=False):
        del system, user, max_output_tokens, json_mode
        self.logical_calls += 1
        self.requests += 1
        self.attempts += 1
        self.input_tokens += 10
        self.output_tokens += 5
        self.total_tokens += 15
        if self.logical_calls == 1:
            if self.invalid_plan:
                text = "not-json"
            else:
                text = json.dumps(
                    {
                        "language": "English",
                        "columns": self.plan_columns or ["ignored"],
                        "queries": [
                            "capital New Delhi currency INR country",
                            "New Delhi INR official source",
                            "country domain type",
                            "country TLD manager",
                        ],
                    }
                )
        elif self.logical_calls == 2:
            text = json.dumps(
                {
                    "pivots": ["India"],
                    "row_targets": [".in"],
                    "authority_terms": ["IANA Root Zone Database"],
                    "queries": [
                        "India .in Domain Type IANA",
                        "India .in TLD Manager IANA",
                    ],
                    "records": [
                        {
                            "page_ordinal": 1,
                            "quote": FACT_QUOTE,
                            "row_identity": ".in",
                            "fields": [
                                {
                                    "column": "TLD Manager",
                                    "source_field": "TLD Manager",
                                    "value": "999",
                                }
                            ],
                        }
                    ],
                }
            )
        else:
            columns = self.plan_columns or ["Domain", "Type", "TLD Manager"]
            if self.invalid_plan:
                columns = ["Result", "Value"]
            if columns == ["Result", "Value"]:
                text = "| Result | Value |\n|---|---|\n| India | Unknown |"
            else:
                text = (
                    "| Domain | Type | TLD Manager |\n"
                    "|---|---|---|\n"
                    "| .in | country-code | 111 |"
                )
        return ModelResult(text=text, usage={}, response_id=None, attempts=1)


def run(question: str, model: TotalModel):
    task = {"opaque_id": TASK["opaque_id"], "question": question}
    with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
        root = Path(raw)
        slots = root / "slots"
        slots.mkdir()
        for index in range(1, 5):
            (slots / f"slot_{index:02d}.lock").write_text("{}\n")
        bounded = DeadlineAwareGlobalModelSlotLimiter(
            model,
            slot_directory=slots,
            output_root=root,
            slot_cap=4,
            absolute_deadline=time.monotonic() + 240,
        )
        budget = cap.PhysicalEffectBudget()
        outer = cap.HardCappedModelLimiter(bounded, budget)
        searches = {
            phase: cap.HardCappedSearchClient(
                FactSearch(question, phase), budget, phase=phase
            )
            for phase in target.PHASES
        }
        result, stage = target.run_task(
            task,
            model=outer,
            searches=searches,
            limits=limits(),
            budget=budget,
            monotonic=time.monotonic,
        )
    return target.validate_result(result), target.validate_stage_receipt(stage)


class V25375SchemaTotalChangedSafeRuntimeTests(unittest.TestCase):
    def test_exact_visible_path_preserves_frozen_parent_output(self) -> None:
        model = TotalModel()
        result, stage = run(QUESTION, model)
        schema = result["schema_totality_receipt"]
        self.assertEqual(schema["selected_schema_source"], "exact_visible")
        self.assertEqual(schema["selected_column_count"], 3)
        self.assertIn("999", result["prediction"])
        self.assertTrue(result["prediction_changed"])
        self.assertEqual(result["prediction"], result["private_parent_result"]["predictions"][parent.CANDIDATE_ARM])
        self.assertFalse(stage["failure_present"])
        self.assertEqual(model.logical_calls, 3)

    def test_expanded_visible_path_is_incremental_and_terminal(self) -> None:
        result, _stage = run(EXPANDED_QUESTION, TotalModel())
        schema = result["schema_totality_receipt"]
        self.assertEqual(schema["selected_schema_source"], "expanded_visible")
        self.assertTrue(schema["expanded_visible_schema_incremental"])
        self.assertEqual(schema["selected_column_count"], 3)
        self.assertIn("999", result["prediction"])

    def test_same_plan_provider_columns_totalize_absent_visible_schema(self) -> None:
        result, _stage = run(
            NO_EXPLICIT_QUESTION,
            TotalModel(plan_columns=["Domain", "Type", "TLD Manager"]),
        )
        schema = result["schema_totality_receipt"]
        self.assertEqual(schema["pre_effect_schema_source"], "generic_result")
        self.assertEqual(schema["selected_schema_source"], "provider_plan")
        self.assertEqual(schema["selected_column_count"], 3)
        self.assertIn("999", result["prediction"])

    def test_invalid_plan_uses_generic_result_and_stays_terminal(self) -> None:
        result, stage = run(NO_EXPLICIT_QUESTION, TotalModel(invalid_plan=True))
        schema = result["schema_totality_receipt"]
        self.assertEqual(schema["selected_schema_source"], "generic_result")
        self.assertEqual(schema["selected_column_count"], 2)
        self.assertEqual(result["prediction_kind"], "model_generated")
        self.assertFalse(result["prediction_changed"])
        self.assertFalse(stage["failure_present"])

    def test_parent_global_projector_identity_is_unchanged(self) -> None:
        original = parent.query_parent
        run(EXPANDED_QUESTION, TotalModel())
        self.assertIs(parent.query_parent, original)
        self.assertIs(parent.query_parent, frozen_projector)

    def test_mixed_concurrency_keeps_task_local_schema_sources(self) -> None:
        cases = [
            (QUESTION, TotalModel()),
            (EXPANDED_QUESTION, TotalModel()),
            (
                NO_EXPLICIT_QUESTION,
                TotalModel(plan_columns=["Domain", "Type", "TLD Manager"]),
            ),
            (NO_EXPLICIT_QUESTION, TotalModel(invalid_plan=True)),
        ]
        with ThreadPoolExecutor(max_workers=4) as pool:
            values = list(pool.map(lambda pair: run(*pair), cases))
        sources = [value[0]["schema_totality_receipt"]["selected_schema_source"] for value in values]
        self.assertEqual(
            sources,
            ["exact_visible", "expanded_visible", "provider_plan", "generic_result"],
        )
        self.assertIs(parent.query_parent, frozen_projector)

    def test_privileged_boundary_fails_before_effect(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            root = Path(raw)
            slots = root / "slots"
            slots.mkdir()
            for index in range(1, 5):
                (slots / f"slot_{index:02d}.lock").write_text("{}\n")
            model = TotalModel()
            bounded = DeadlineAwareGlobalModelSlotLimiter(
                model,
                slot_directory=slots,
                output_root=root,
                slot_cap=4,
                absolute_deadline=time.monotonic() + 240,
            )
            budget = cap.PhysicalEffectBudget()
            searches = {
                phase: cap.HardCappedSearchClient(
                    FactSearch(QUESTION, phase), budget, phase=phase
                )
                for phase in target.PHASES
            }
            with self.assertRaises(ValueError):
                target.run_task(
                    {**TASK, "category": "forbidden"},
                    model=cap.HardCappedModelLimiter(bounded, budget),
                    searches=searches,
                    limits=limits(),
                    budget=budget,
                    monotonic=time.monotonic,
                )
            self.assertEqual(model.logical_calls, 0)
            self.assertTrue(all(search._inner_search.calls == 0 for search in searches.values()))

    def test_receipt_and_result_tamper_fail_closed(self) -> None:
        result, stage = run(QUESTION, TotalModel())
        changed = copy.deepcopy(result)
        changed["prediction"] += "x"
        with self.assertRaises(ValueError):
            target.validate_result(changed)
        changed_stage = copy.deepcopy(stage)
        changed_stage["failure_present"] = True
        changed_stage.pop("receipt_payload_sha256")
        from deepwide_agent.v24263_global_model_limiter import payload_sha256

        changed_stage["receipt_payload_sha256"] = payload_sha256(changed_stage)
        with self.assertRaises(ValueError):
            target.validate_stage_receipt(changed_stage)

    def test_runtime_source_has_no_privileged_or_io_capability(self) -> None:
        path = ROOT / "src/deepwide_agent/v25375_schema_total_changed_safe_runtime.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        privileged = {
            "category",
            "question_type",
            "task_category",
            "ground_truth",
            "answer_key",
            "split",
            "score",
            "reward",
        }
        hits = []
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
            elif isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
                if node.slice.value in privileged:
                    hits.append(node.slice.value)
        self.assertEqual(hits, [])
        self.assertFalse(
            any(name in {"os", "subprocess", "socket", "urllib", "requests"} for name in imports)
        )


if __name__ == "__main__":
    unittest.main()
