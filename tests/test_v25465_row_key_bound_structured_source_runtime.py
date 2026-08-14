from __future__ import annotations

import ast
import copy
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25253_outer_physical_cap_observed_runtime as cap  # noqa: E402
from deepwide_agent import v25465_row_key_bound_structured_source_runtime as target  # noqa: E402
from deepwide_agent.clients import ModelResult  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import (  # noqa: E402
    DeadlineAwareGlobalModelSlotLimiter,
)
from test_v25119_grounded_target_record_paired_runtime import (  # noqa: E402
    GroundedFrontierSearch,
    limits,
)


QUESTION = (
    "Use public sources to return one table. "
    "Columns exactly: Package | Version | Authors | Status."
)
TASK = {
    "opaque_id": "task_0123456789abcdef01234567",
    "question": QUESTION,
}


class RowKeyModel:
    def __init__(self) -> None:
        self.requests = self.attempts = 0
        self.input_tokens = self.output_tokens = self.total_tokens = 0
        self.logical_calls = 0
        self.systems: list[str] = []
        self.users: list[str] = []

    def complete(self, system, user, *, max_output_tokens, json_mode=False):
        del max_output_tokens, json_mode
        self.logical_calls += 1
        self.requests += 1
        self.attempts += 1
        self.input_tokens += 10
        self.output_tokens += 5
        self.total_tokens += 15
        self.systems.append(str(system))
        self.users.append(str(user))
        if self.logical_calls == 1:
            text = json.dumps(
                {
                    "language": "English",
                    "columns": ["ignored"],
                    "queries": [
                        "alpha package official",
                        "alpha package metadata",
                        "alpha version",
                        "alpha status",
                    ],
                }
            )
        elif self.logical_calls == 2:
            text = json.dumps(
                {
                    "pivots": ["alpha"],
                    "row_targets": ["alpha"],
                    "authority_terms": ["registry example"],
                    "queries": ["alpha registry record", "alpha registry metadata"],
                    "records": [],
                }
            )
        else:
            text = (
                "| Package | Version | Authors | Status |\n"
                "|---|---|---|---|\n"
                "| alpha | 1.0 | Alice; Bob | Unknown |"
            )
        return ModelResult(text=text, usage={}, response_id=None, attempts=1)


class RowKeySearch(GroundedFrontierSearch):
    def __init__(self, question: str, phase: str, *, mode: str = "valid") -> None:
        super().__init__(question, phase)
        self.mode = mode

    def search_many(self, queries, **kwargs):
        output = super().search_many(queries, **kwargs)
        if self._phase == target.PHASES[0] or not output:
            return output
        first_results = output[0].get("results") if isinstance(output[0], dict) else None
        if isinstance(first_results, list) and first_results:
            first_results[0].update(
                {
                    "url": "https://registry.example/package/alpha/metadata.json",
                    "fetch_url": "https://registry.example/package/alpha/metadata.json",
                    "title": "alpha package metadata",
                }
            )
        for batch in output:
            trace = batch.get("hosted_search_trace") if isinstance(batch, dict) else None
            if not isinstance(trace, dict):
                continue
            for action in trace.get("actions") or []:
                for source in action.get("sources") or []:
                    if "iana.org" in str(source.get("url") or ""):
                        source.update(
                            {
                                "url": "https://registry.example/package/alpha/metadata.json",
                                "fetch_url": "https://registry.example/package/alpha/metadata.json",
                                "title": "alpha package metadata",
                            }
                        )
        return output

    def fetch_urls(self, requests_):
        values = list(requests_)
        if self._phase != target.PHASES[0]:
            output = super().fetch_urls(values)
            replacement = next(
                (
                    request
                    for request in values
                    if "registry.example/package/alpha" in str(request.get("url") or "")
                ),
                None,
            )
            if replacement is None:
                return output
            requested = str(replacement.get("url") or "")
            content = "Version: 2.0\nAuthors: Alice; Bob\nStatus: Stable"
            final = requested
            title = "alpha package metadata"
            if self.mode == "unbound":
                final = "https://registry.example/package/beta/metadata.json"
                title = "beta package metadata"
            elif self.mode == "surface_only":
                content = "Authors: Alice, Bob"
            self._prefixes[requested] = content
            result = {
                "title": title,
                "url": final,
                "fetch_url": requested,
                "requested_url": requested,
                "raw_content": content,
                "content": "",
            }
            if output and output[0].get("results"):
                output[0]["results"][0] = result
            else:
                output.insert(
                    0,
                    {
                        "query": replacement.get("query", ""),
                        "answer": "",
                        "results": [result],
                        "error": None,
                        "provider": "synthetic-fetch",
                    },
                )
            return output
        return super().fetch_urls(values)


def run_runtime(*, mode: str = "valid", task: dict[str, str] | None = None):
    model = RowKeyModel()
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
                RowKeySearch(QUESTION, phase, mode=mode), budget, phase=phase
            )
            for phase in target.PHASES
        }
        result, stage = target.run_task(
            TASK if task is None else task,
            model=outer,
            searches=searches,
            limits=limits(),
            budget=budget,
            monotonic=time.monotonic,
        )
    return (
        model,
        target.validate_result(result),
        target.validate_stage_receipt(stage),
        cap.validate_budget_receipt(budget.receipt()),
    )


def run_parent():
    model = RowKeyModel()
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
        searches = {
            phase: cap.HardCappedSearchClient(
                RowKeySearch(QUESTION, phase), budget, phase=phase
            )
            for phase in target.PHASES
        }
        target.parent.run_task(
            TASK,
            model=cap.HardCappedModelLimiter(bounded, budget),
            searches=searches,
            limits=limits(),
            budget=budget,
            monotonic=time.monotonic,
        )
    return model


class V25465RowKeyBoundStructuredSourceRuntimeTests(unittest.TestCase):
    def test_one_parent_forward_applies_row_key_bound_source_fields(self) -> None:
        model, result, stage, budget = run_runtime()
        self.assertEqual(model.logical_calls, 3)
        self.assertEqual(budget["query_admitted_count"], 4)
        self.assertLessEqual(budget["fetch_admitted_count"], 14)
        self.assertEqual(budget["model_admitted_count"], 3)
        self.assertTrue(result["prediction_changed"])
        self.assertIn("| alpha | 2.0 | Alice; Bob | Stable |", result["prediction"])
        self.assertFalse(stage["failure_present"])
        receipt = result["row_key_bound_source_receipt"]
        self.assertEqual(receipt["available_candidate_count"], 2)
        self.assertEqual(receipt["additional_fetch_calls"], 0)

    def test_parent_provider_request_bytes_are_unchanged(self) -> None:
        candidate, _result, _stage, _budget = run_runtime()
        control = run_parent()
        self.assertEqual(candidate.systems, control.systems)
        self.assertEqual(candidate.users, control.users)
        self.assertEqual(candidate.logical_calls, control.logical_calls)

    def test_unbound_and_surface_equivalent_pages_are_byte_exact_noops(self) -> None:
        for mode in ("unbound", "surface_only"):
            with self.subTest(mode=mode):
                _model, result, _stage, _budget = run_runtime(mode=mode)
                self.assertFalse(result["prediction_changed"])
                self.assertEqual(
                    result["predictions"][target.BASE_ARM],
                    result["predictions"][target.CANDIDATE_ARM],
                )

    def test_privileged_input_rejected_before_any_effect(self) -> None:
        task = {**TASK, "category": "forbidden"}
        with self.assertRaises(ValueError):
            run_runtime(task=task)

    def test_result_stage_application_and_credit_tamper_fail_closed(self) -> None:
        _model, result, stage, _budget = run_runtime()
        for kind in ("prediction", "application", "credit", "stage"):
            if kind == "stage":
                changed_stage = copy.deepcopy(stage)
                changed_stage["query_fetch_model_token_context_and_wall_caps_unchanged"] = False
                changed_stage.pop("receipt_payload_sha256")
                changed_stage["receipt_payload_sha256"] = target.payload_sha256(changed_stage)
                with self.subTest(kind=kind), self.assertRaises(ValueError):
                    target.validate_stage_receipt(changed_stage)
                continue
            changed = copy.deepcopy(result)
            if kind == "prediction":
                changed["prediction"] = changed["prediction"] + "x"
            elif kind == "application":
                changed["private_source_application"]["candidate_prediction"] += "x"
            else:
                changed["row_key_bound_source_receipt"]["positive_signed_credit_count"] = 1
            changed.pop("result_payload_sha256")
            changed["result_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_result(changed)

    def test_integration_contract_and_runtime_are_label_blind(self) -> None:
        contract = target.integration_contract()
        self.assertEqual(contract["runtime_input_keys"], ["opaque_id", "question"])
        self.assertEqual(contract["additional_candidate_provider_effects"], 0)
        source = Path(target.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports: list[str] = []
        privileged: list[str] = []
        forbidden_fields = {
            "category",
            "question_type",
            "task_category",
            "split",
            "ground_truth",
            "gold",
            "answer_key",
            "score",
            "reward",
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
            elif (
                isinstance(node, ast.Subscript)
                and isinstance(node.slice, ast.Constant)
                and node.slice.value in forbidden_fields
            ):
                privileged.append(str(node.slice.value))
        self.assertEqual(privileged, [])
        self.assertFalse(
            any(
                name == forbidden or name.startswith(forbidden + ".")
                for forbidden in (
                    "os",
                    "pathlib",
                    "subprocess",
                    "socket",
                    "requests",
                    "httpx",
                )
                for name in imports
            )
        )


if __name__ == "__main__":
    unittest.main()
