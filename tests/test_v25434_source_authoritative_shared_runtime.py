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
from deepwide_agent import v25434_source_authoritative_shared_runtime as target  # noqa: E402
from deepwide_agent.clients import ModelResult  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import (  # noqa: E402
    DeadlineAwareGlobalModelSlotLimiter,
)
from test_v25123_visible_legacy_query_compatible_runtime import limits  # noqa: E402
from test_v25349_shared_prefix_grounded_fact_paired_runtime import FactSearch  # noqa: E402


QUESTION = (
    "Use public sources and the official IANA website to return one table for "
    "the visible rows below.\n<ENTITIES>\n1. .in\n2. .uk\n</ENTITIES>\n"
    "Columns exactly: Domain | Type | TLD Manager. Preserve row order."
)
TASK = {
    "opaque_id": "task_0123456789abcdef01234567",
    "question": QUESTION,
}


def record_page(*, value: str = "999", url: str | None = None) -> dict[str, str]:
    chosen_url = url or "https://www.iana.org/domains/root/db/in.html"
    return {
        "title": ".in",
        "url": chosen_url,
        "fetch_url": chosen_url,
        "requested_url": chosen_url,
        "raw_content": (
            "| Domain | Type | TLD Manager |\n"
            "| --- | --- | --- |\n"
            f"| .in | country-code | {value} |"
        ),
        "content": "",
    }


class SourcePageSearch(FactSearch):
    def __init__(self, question: str, phase: str, *, mode: str = "valid") -> None:
        super().__init__(question, phase)
        self.mode = mode

    def search_many(self, queries, **kwargs):
        output = super().search_many(queries, **kwargs)
        if self._phase != target.PHASES[1] or not output:
            return output
        urls = ["https://www.iana.org/domains/root/db/in.html"]
        if self.mode == "conflict":
            urls.append("https://www.iana.org/domains/root/db/in-alt.html")
        elif self.mode == "unbound":
            urls = ["https://example.org/records/in.html"]
        available = [
            item
            for batch in output
            for item in batch.get("results", [])
            if isinstance(item, dict)
        ]
        for item, url in zip(available, urls, strict=False):
            item.update({"url": url, "fetch_url": url, "title": ".in"})
        return output

    def fetch_urls(self, requests_):
        output = super().fetch_urls(requests_)
        if self._phase != target.PHASES[1]:
            return output
        pages = [record_page()]
        if self.mode == "conflict":
            pages.append(
                record_page(
                    value="888",
                    url="https://www.iana.org/domains/root/db/in-alt.html",
                )
            )
        elif self.mode == "unbound":
            pages = [record_page(url="https://example.org/records/in.html")]
        flattened = [item for batch in output for item in batch.get("results", [])]
        for index, item in enumerate(flattened):
            if index < len(pages):
                item.update(pages[index])
        return output


class SourceModel:
    def __init__(self) -> None:
        self.requests = self.attempts = 0
        self.input_tokens = self.output_tokens = self.total_tokens = 0
        self.logical_calls = 0
        self.systems: list[str] = []
        self.users: list[str] = []

    def complete(self, system, user, *, max_output_tokens, json_mode=False):
        del max_output_tokens
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
                    "columns": ["ignored"],
                    "queries": [
                        "IANA .in domain record",
                        "IANA .uk domain record",
                        "IANA domain type",
                        "IANA TLD manager",
                    ],
                }
            )
        elif self.logical_calls == 2:
            text = json.dumps(
                {
                    "pivots": [".in", ".uk"],
                    "row_targets": [".in", ".uk"],
                    "authority_terms": ["IANA"],
                    "queries": [".in IANA record", ".uk IANA record"],
                    "records": [],
                }
            )
        else:
            self.assert_joint_mode = bool(json_mode)
            table = (
                "| Domain | Type | TLD Manager |\n"
                "|---|---|---|\n"
                "| .in | country-code | 111 |\n"
                "| .uk | country-code | 222 |"
            )
            text = json.dumps({"table": table, "records": []})
        return ModelResult(text=text, usage={}, response_id=None, attempts=1)


def run_runtime(*, mode: str = "valid", question: str = QUESTION):
    model = SourceModel()
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
                SourcePageSearch(question, phase, mode=mode),
                budget,
                phase=phase,
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
    return (
        model,
        target.validate_result(result),
        target.validate_stage_receipt(stage),
        cap.validate_budget_receipt(budget.receipt()),
    )


def run_parent_with_same_search(*, mode: str = "valid", question: str = QUESTION):
    model = SourceModel()
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
                SourcePageSearch(question, phase, mode=mode),
                budget,
                phase=phase,
            )
            for phase in target.PHASES
        }
        target.parent.run_task(
            task,
            model=outer,
            searches=searches,
            limits=limits(),
            budget=budget,
            monotonic=time.monotonic,
        )
    return model


class V25434SourceAuthoritativeSharedRuntimeTests(unittest.TestCase):
    def test_rfc_joined_url_token_binding_is_exact_not_substring(self) -> None:
        tokens = ("rfc", "editor")
        self.assertEqual(
            target._url_bindings(
                "https://www.rfc-editor.org/rfc/rfc9160.html",
                identity="RFC 9160",
                authority_tokens=tokens,
            ),
            (True, True),
        )
        for url in (
            "https://www.rfc-editor.org/rfc/rfc91601.html",
            "https://rfc9160.example.org/index.html",
        ):
            with self.subTest(url=url):
                self.assertFalse(
                    target._url_bindings(
                        url,
                        identity="RFC 9160",
                        authority_tokens=tokens,
                    )[0]
                )

    def test_one_parent_forward_applies_source_candidate_with_three_calls(self) -> None:
        model, result, stage, budget = run_runtime()
        receipt = result["source_authoritative_receipt"]
        self.assertEqual(model.logical_calls, 3)
        self.assertEqual(budget["model_admitted_count"], 3)
        self.assertEqual(budget["query_admitted_count"], 4)
        self.assertLessEqual(budget["fetch_admitted_count"], 14)
        self.assertTrue(receipt["synthesis_capture_valid"])
        self.assertGreaterEqual(receipt["accepted_authority_page_count"], 1)
        self.assertGreaterEqual(receipt["available_candidate_count"], 1)
        self.assertTrue(result["prediction_changed"])
        self.assertIn("| .in | country-code | 999 |", result["prediction"])
        self.assertFalse(stage["failure_present"])

    def test_wrapper_does_not_change_any_parent_provider_request(self) -> None:
        candidate_model, _result, _stage, _budget = run_runtime()
        parent_model = run_parent_with_same_search()
        self.assertEqual(candidate_model.systems, parent_model.systems)
        self.assertEqual(candidate_model.users, parent_model.users)
        self.assertEqual(candidate_model.logical_calls, parent_model.logical_calls)

    def test_unbound_authority_page_is_exact_base_handoff(self) -> None:
        _model, result, _stage, _budget = run_runtime(mode="unbound")
        receipt = result["source_authoritative_receipt"]
        self.assertEqual(receipt["accepted_authority_page_count"], 0)
        self.assertEqual(receipt["available_candidate_count"], 0)
        self.assertFalse(result["prediction_changed"])
        self.assertEqual(
            result["predictions"][target.BASE_ARM],
            result["predictions"][target.CANDIDATE_ARM],
        )

    def test_multiple_source_coordinates_conflict_and_preserve_base(self) -> None:
        _model, result, _stage, _budget = run_runtime(mode="conflict")
        application = result["private_source_authoritative_application"]
        self.assertIsNotNone(application)
        registry_receipt = application["private_candidate_registry"][
            "content_free_receipt"
        ]
        self.assertGreaterEqual(
            registry_receipt["conflicting_value_coordinate_count"], 1
        )
        self.assertFalse(result["prediction_changed"])

    def test_capture_failure_or_missing_visible_authority_is_noop(self) -> None:
        no_authority = QUESTION.replace("official IANA website", "public pages")
        _model, result, _stage, _budget = run_runtime(question=no_authority)
        receipt = result["source_authoritative_receipt"]
        self.assertEqual(receipt["visible_authority_token_count"], 0)
        self.assertEqual(receipt["accepted_authority_page_count"], 0)
        self.assertFalse(result["prediction_changed"])

    def test_resealed_application_prediction_receipt_or_credit_tamper_fails(self) -> None:
        _model, result, stage, _budget = run_runtime()
        for kind in (
            "prediction",
            "application",
            "page",
            "receipt",
            "credit",
            "stage",
        ):
            if kind == "stage":
                changed_stage = copy.deepcopy(stage)
                changed_stage["query_fetch_model_token_context_and_wall_caps_unchanged"] = False
                changed_stage.pop("receipt_payload_sha256")
                changed_stage["receipt_payload_sha256"] = target.payload_sha256(
                    changed_stage
                )
                with self.subTest(kind=kind), self.assertRaises(ValueError):
                    target.validate_stage_receipt(changed_stage)
                continue
            changed = copy.deepcopy(result)
            if kind == "prediction":
                changed["prediction"] = changed["predictions"][target.BASE_ARM]
                changed["prediction_sha256"] = target.hashlib.sha256(
                    changed["prediction"].encode()
                ).hexdigest()
            elif kind == "application":
                changed["private_source_authoritative_application"][
                    "candidate_prediction"
                ] = changed["predictions"][target.BASE_ARM]
            elif kind == "page":
                changed["private_same_forward_authority_pages"][0][
                    "content"
                ] = changed["private_same_forward_authority_pages"][0][
                    "content"
                ].replace("999", "777")
            elif kind == "receipt":
                changed["source_authoritative_receipt"][
                    "selected_candidate_count"
                ] = 0
            else:
                changed["source_authoritative_receipt"][
                    "positive_signed_credit_count"
                ] = 1
            changed.pop("result_payload_sha256")
            changed["result_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_result(changed)

    def test_privileged_input_rejected_before_effect(self) -> None:
        model = SourceModel()
        task = {**TASK, "category": "forbidden"}
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
                    SourcePageSearch(QUESTION, phase), budget, phase=phase
                )
                for phase in target.PHASES
            }
            with self.assertRaises(ValueError):
                target.run_task(
                    task,
                    model=outer,
                    searches=searches,
                    limits=limits(),
                    budget=budget,
                    monotonic=time.monotonic,
                )
        self.assertEqual(model.logical_calls, 0)
        self.assertEqual(budget.receipt()["model_admitted_count"], 0)

    def test_runtime_is_label_blind_and_has_no_direct_external_capability(self) -> None:
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
        for forbidden in (
            "os",
            "pathlib",
            "subprocess",
            "requests",
            "httpx",
            "socket",
            "urllib",
        ):
            self.assertFalse(
                any(
                    name == forbidden or name.startswith(forbidden + ".")
                    for name in imports
                )
            )
        self.assertNotIn("model.complete", source)
        self.assertNotIn("search_many", source)
        self.assertNotIn("fetch_urls", source)


if __name__ == "__main__":
    unittest.main()
