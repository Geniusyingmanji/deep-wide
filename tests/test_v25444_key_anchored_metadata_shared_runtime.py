from __future__ import annotations

import ast
import copy
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
from deepwide_agent import v25434_source_authoritative_shared_runtime as old  # noqa: E402
from deepwide_agent import v25440_key_anchored_metadata_candidate as primitive  # noqa: E402
from deepwide_agent import v25444_key_anchored_metadata_shared_runtime as target  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import (  # noqa: E402
    DeadlineAwareGlobalModelSlotLimiter,
)
from test_v25123_visible_legacy_query_compatible_runtime import limits  # noqa: E402
from test_v25434_source_authoritative_shared_runtime import (  # noqa: E402
    QUESTION,
    TASK,
    SourceModel,
    SourcePageSearch,
    run_parent_with_same_search,
)


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


class MetadataHybrid:
    source_capture_valid = True
    source_capture_attempted = True
    source_capture_failure_type = None
    source_columns = ("RFC", "Title", "Authors", "Status", "Stream", "Published")
    source_pages = [
        {
            "url": "https://www.rfc-editor.org/rfc/rfc9080.html",
            "title": "RFC 9080",
            "content": (
                "RFC: 9080\nCategory: Standards Track\n"
                "Published: April 2021\nISSN: 2070-1721\n"
                "Authors: Alice    Bob\n\nAbstract follows."
            ),
        }
    ]


METADATA_BASE = (
    "```markdown\n"
    "| RFC | Title | Authors | Status | Stream | Published |\n"
    "| --- | --- | --- | --- | --- | --- |\n"
    "| RFC 9080 | Old | Old A; Old B | Unknown | IETF | March 2021 |\n"
    "```"
)


class V25444KeyAnchoredMetadataSharedRuntimeTests(unittest.TestCase):
    def test_private_namespace_binds_new_primitive_without_parent_mutation(self) -> None:
        contract = target.integration_contract()
        self.assertTrue(contract["candidate_module_bound_in_private_namespace"])
        self.assertTrue(contract["parent_module_global_candidate_unchanged"])
        self.assertIs(target._NAMESPACE["candidates"], primitive)
        self.assertIsNot(old.candidates, primitive)
        self.assertEqual(contract["additional_candidate_provider_effects"], 0)

    def test_key_anchored_metadata_is_applied_and_replay_valid(self) -> None:
        application, prediction, failure = target._application(
            METADATA_BASE, MetadataHybrid()
        )
        self.assertIsNone(failure)
        self.assertIsNotNone(application)
        checked = primitive.validate_application(application)
        self.assertEqual(prediction, checked["candidate_prediction"])
        self.assertIn("Alice; Bob", prediction)
        self.assertIn("April 2021", prediction)
        registry = checked["private_candidate_registry"]
        self.assertEqual(
            registry["content_free_receipt"]["metadata_identity_qualified_count"],
            1,
        )

    def test_one_parent_forward_preserves_caps_and_applies_parent_candidate(self) -> None:
        model, result, stage, budget = run_runtime()
        receipt = result["source_authoritative_receipt"]
        self.assertEqual(model.logical_calls, 3)
        self.assertEqual(budget["model_admitted_count"], 3)
        self.assertEqual(budget["query_admitted_count"], 4)
        self.assertLessEqual(budget["fetch_admitted_count"], 14)
        self.assertGreaterEqual(receipt["available_candidate_count"], 1)
        self.assertTrue(result["prediction_changed"])
        self.assertIn("| .in | country-code | 999 |", result["prediction"])
        self.assertFalse(stage["failure_present"])

    def test_wrapper_preserves_every_parent_provider_request_byte_exact(self) -> None:
        candidate_model, _result, _stage, _budget = run_runtime()
        parent_model = run_parent_with_same_search()
        self.assertEqual(candidate_model.systems, parent_model.systems)
        self.assertEqual(candidate_model.users, parent_model.users)
        self.assertEqual(candidate_model.logical_calls, parent_model.logical_calls)

    def test_unbound_or_conflicting_pages_are_byte_exact_noops(self) -> None:
        for mode in ("unbound", "conflict"):
            with self.subTest(mode=mode):
                _model, result, _stage, _budget = run_runtime(mode=mode)
                self.assertFalse(result["prediction_changed"])
                self.assertEqual(
                    result["predictions"][target.BASE_ARM],
                    result["predictions"][target.CANDIDATE_ARM],
                )

    def test_resealed_application_prediction_receipt_or_credit_tamper_fails(self) -> None:
        _model, result, stage, _budget = run_runtime()
        for kind in ("prediction", "application", "receipt", "credit", "stage"):
            if kind == "stage":
                changed_stage = copy.deepcopy(stage)
                changed_stage[
                    "query_fetch_model_token_context_and_wall_caps_unchanged"
                ] = False
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
            elif kind == "application":
                changed["private_source_authoritative_application"][
                    "candidate_prediction"
                ] = changed["predictions"][target.BASE_ARM]
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

    def test_privileged_input_rejected_before_any_effect(self) -> None:
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
