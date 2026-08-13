from __future__ import annotations

import ast
import copy
import fcntl
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25290_monotone_unknown_fill_integration as target  # noqa: E402
from deepwide_agent.clients import ModelRequestError  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import payload_sha256  # noqa: E402
from deepwide_agent.v24318_deadline_conservation_runtime import MODEL_FIELD  # noqa: E402
import test_v24860_coverage_revision_integration as parent_test  # noqa: E402


KNOWN = "| Name | Date |\n| --- | --- |\n| Alpha | 2025 |"
UNSUPPORTED = "| Name | Date |\n| --- | --- |\n| Alpha | 2099 |"
KNOWN_EDIT = "| Name | Date |\n| --- | --- |\n| Alpha | 2025 |\n| Beta | 2024 |"


class V25290MonotoneUnknownFillIntegrationTests(unittest.TestCase):
    def build(self, values: list[object]):
        helper = parent_test.V24860CoverageRevisionIntegrationTests()
        return helper.build_parent(values)

    def execute(self, values: list[object], *, pages=None):
        temporary, clock, inner, model, parent = self.build(values)
        self.addCleanup(temporary.cleanup)
        result = target.run_monotone_unknown_fill(
            parent_test.task(),
            parent_result=parent.result,
            parent_model_slot_receipt=parent.model_slot_receipt,
            model=model,
            pages=parent_test.pages_for(parent.result)
            if pages is None
            else pages(parent.result),
            limits=parent_test.limits(),
            monotonic=clock,
        )
        return inner, parent, result

    def test_supported_fill_spends_exact_third_slot(self) -> None:
        inner, parent, value = self.execute(
            [parent_test.PLAN, parent_test.BASELINE, parent_test.SUPPORTED]
        )
        receipt = target.validate_integration_receipt(
            value.integration_receipt
        )
        self.assertEqual(
            receipt["disposition"], "admitted_monotone_unknown_fill"
        )
        self.assertEqual(receipt["logical_final_model_calls"], 3)
        self.assertEqual(receipt["provider_request_delta"], 1)
        self.assertEqual(receipt["model_slot_acquisition_delta"], 1)
        self.assertEqual(value.final_model_slot_receipt["acquisitions"], 3)
        self.assertIn("| Alpha | 2026 |", value.result["prediction"])
        self.assertEqual(
            receipt["monotone_unknown_fill_receipt"][
                "admitted_unknown_fill_count"
            ],
            1,
        )
        self.assertEqual(value.result["parent_result"], parent.result)
        self.assertTrue(value.result["private_task_content_present"])
        self.assertFalse(
            value.result["private_task_content_emitted_to_public_aggregate"]
        )
        self.assertTrue(value.result["private_model_proposal_present"])
        self.assertEqual(
            value.result["private_model_proposal"], parent_test.SUPPORTED
        )
        self.assertEqual(value.result["cost"]["search"], parent.result["cost"]["search"])
        self.assertEqual(
            inner.max_output_tokens[-1], parent_test.limits().repair_output_tokens
        )

    def test_no_unknown_skips_third_slot(self) -> None:
        inner, parent, value = self.execute(
            [parent_test.PLAN, KNOWN, parent_test.SUPPORTED]
        )
        receipt = value.integration_receipt
        self.assertEqual(receipt["disposition"], "identity_no_baseline_unknown")
        self.assertFalse(receipt["logical_revision_call_admitted"])
        self.assertEqual(len(inner.max_output_tokens), 2)
        self.assertEqual(value.result["prediction"], parent.result["prediction"])

    def test_incomplete_prefix_is_identity_without_third_call(self) -> None:
        inner, parent, value = self.execute(
            [parent_test.PLAN, parent_test.BASELINE, parent_test.SUPPORTED],
            pages=lambda result: parent_test.pages_for(result)[:-1],
        )
        self.assertEqual(
            value.integration_receipt["disposition"],
            "identity_incomplete_page_prefix",
        )
        self.assertEqual(len(inner.max_output_tokens), 2)
        self.assertEqual(value.result["prediction"], parent.result["prediction"])

    def test_unsupported_fill_spends_slot_and_preserves_parent(self) -> None:
        _inner, parent, value = self.execute(
            [parent_test.PLAN, parent_test.BASELINE, UNSUPPORTED]
        )
        receipt = value.integration_receipt
        self.assertEqual(receipt["disposition"], "identity_no_supported_fill")
        self.assertTrue(receipt["logical_revision_call_admitted"])
        self.assertEqual(receipt["provider_request_delta"], 1)
        self.assertEqual(value.result["prediction"], parent.result["prediction"])

    def test_model_effect_failure_is_not_misclassified_as_empty(self) -> None:
        _inner, parent, value = self.execute(
            [
                parent_test.PLAN,
                parent_test.BASELINE,
                ModelRequestError("synthetic"),
            ]
        )
        receipt = value.integration_receipt
        self.assertEqual(receipt["disposition"], "identity_model_effect_failed")
        self.assertTrue(receipt["model_effect_failed"])
        self.assertFalse(receipt["proposal_returned"])
        self.assertEqual(value.result["prediction"], parent.result["prediction"])

    def test_local_monotone_gate_failure_preserves_parent(self) -> None:
        temporary, clock, _inner, model, parent = self.build(
            [parent_test.PLAN, parent_test.BASELINE, parent_test.SUPPORTED]
        )
        self.addCleanup(temporary.cleanup)
        with mock.patch.object(
            target,
            "_apply_candidate",
            side_effect=RuntimeError("hidden gate detail"),
        ):
            value = target.run_monotone_unknown_fill(
                parent_test.task(),
                parent_result=parent.result,
                parent_model_slot_receipt=parent.model_slot_receipt,
                model=model,
                pages=parent_test.pages_for(parent.result),
                limits=parent_test.limits(),
                monotonic=clock,
            )
        receipt = value.integration_receipt
        self.assertEqual(
            receipt["disposition"], "identity_monotone_gate_failed"
        )
        self.assertTrue(receipt["monotone_gate_failed"])
        self.assertFalse(receipt["model_effect_failed"])
        self.assertTrue(receipt["proposal_returned"])
        self.assertTrue(receipt["monotone_gate_invoked"])
        self.assertEqual(receipt["provider_request_delta"], 1)
        self.assertEqual(value.result["prediction"], parent.result["prediction"])
        self.assertNotIn("hidden gate detail", str(receipt))

    def test_context_cap_skips_third_slot(self) -> None:
        temporary, clock, inner, model, parent = self.build(
            [parent_test.PLAN, parent_test.BASELINE, parent_test.SUPPORTED]
        )
        self.addCleanup(temporary.cleanup)
        pages = parent_test.pages_for(parent.result)
        for item in pages:
            item["raw_content"] = "\\" * parent_test.limits().page_chars
        value = target.run_monotone_unknown_fill(
            parent_test.task(),
            parent_result=parent.result,
            parent_model_slot_receipt=parent.model_slot_receipt,
            model=model,
            pages=pages,
            limits=parent_test.limits(),
            monotonic=clock,
        )
        self.assertEqual(
            value.integration_receipt["disposition"], "identity_context_cap"
        )
        self.assertEqual(len(inner.max_output_tokens), 2)
        self.assertEqual(value.result["prediction"], parent.result["prediction"])

    def test_modified_parent_limits_fail_before_third_effect(self) -> None:
        temporary, clock, _inner, model, parent = self.build(
            [parent_test.PLAN, parent_test.BASELINE, parent_test.SUPPORTED]
        )
        self.addCleanup(temporary.cleanup)
        original = parent_test.limits()
        altered = type(original)(
            **{
                **original.__dict__,
                "evidence_chars": original.evidence_chars - 1,
            }
        )
        before = model.receipt()
        with self.assertRaisesRegex(ValueError, "inherited parent limits"):
            target.run_monotone_unknown_fill(
                parent_test.task(),
                parent_result=parent.result,
                parent_model_slot_receipt=parent.model_slot_receipt,
                model=model,
                pages=parent_test.pages_for(parent.result),
                limits=altered,
                monotonic=clock,
            )
        self.assertEqual(before, model.receipt())

    def test_third_slot_timeout_is_conserved_without_provider_request(self) -> None:
        temporary, clock, _inner, model, parent = self.build(
            [parent_test.PLAN, parent_test.BASELINE, parent_test.SUPPORTED]
        )
        self.addCleanup(temporary.cleanup)
        handles = [
            open(Path(temporary.name) / "slots" / f"slot_{index:02d}.lock", "r+")
            for index in (1, 2)
        ]
        for handle in handles:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        clock.value = 215.0
        try:
            value = target.run_monotone_unknown_fill(
                parent_test.task(),
                parent_result=parent.result,
                parent_model_slot_receipt=parent.model_slot_receipt,
                model=model,
                pages=parent_test.pages_for(parent.result),
                limits=parent_test.limits(),
                monotonic=clock,
            )
        finally:
            for handle in handles:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
                handle.close()
        receipt = value.integration_receipt
        self.assertEqual(receipt["disposition"], "identity_model_effect_failed")
        self.assertTrue(receipt["model_effect_failed"])
        self.assertEqual(receipt["provider_request_delta"], 0)
        self.assertEqual(receipt["model_slot_timeout_delta"], 1)
        self.assertEqual(value.final_model_slot_receipt["acquisitions"], 2)
        self.assertEqual(value.final_model_slot_receipt["slot_timeouts"], 1)
        self.assertEqual(value.result["prediction"], parent.result["prediction"])

    def test_known_or_structure_change_rejects_whole_proposal(self) -> None:
        for candidate in (KNOWN_EDIT, "not a table"):
            with self.subTest(candidate=candidate):
                _inner, parent, value = self.execute(
                    [parent_test.PLAN, parent_test.BASELINE, candidate]
                )
                self.assertEqual(
                    value.integration_receipt["disposition"],
                    "identity_invalid_or_forbidden_proposal",
                )
                self.assertEqual(
                    value.result["prediction"], parent.result["prediction"]
                )

    def test_truncated_or_empty_proposal_is_identity(self) -> None:
        for candidate, disposition in (
            (
                SimpleNamespace(
                    text=parent_test.SUPPORTED, output_truncated=True
                ),
                "identity_truncated_proposal",
            ),
            ("", "identity_empty_proposal"),
        ):
            with self.subTest(disposition=disposition):
                _inner, parent, value = self.execute(
                    [parent_test.PLAN, parent_test.BASELINE, candidate]
                )
                self.assertEqual(
                    value.integration_receipt["disposition"], disposition
                )
                self.assertEqual(
                    value.result["prediction"], parent.result["prediction"]
                )

    def test_parent_repair_uses_all_slots_and_blocks_revision(self) -> None:
        repaired = parent_test.BASELINE
        inner, parent, value = self.execute(
            [parent_test.PLAN, "not a table", repaired, parent_test.SUPPORTED]
        )
        self.assertEqual(
            parent.result[MODEL_FIELD]["logical_admissions_total"], 3
        )
        self.assertEqual(
            value.integration_receipt["disposition"],
            "identity_parent_not_eligible",
        )
        self.assertEqual(len(inner.max_output_tokens), 3)
        self.assertEqual(value.result["prediction"], parent.result["prediction"])

    def test_prompt_is_unknown_only_exact_table_contract(self) -> None:
        inner, _parent, _value = self.execute(
            [parent_test.PLAN, parent_test.BASELINE, parent_test.SUPPORTED]
        )
        # SyntheticModel does not retain prompts, so verify the pure builder.
        temporary, _clock, _inner, _model, parent = self.build(
            [parent_test.PLAN, parent_test.BASELINE, parent_test.SUPPORTED]
        )
        self.addCleanup(temporary.cleanup)
        pages = tuple(
            target.legacy._prepare_complete_prefix(
                parent_test.pages_for(parent.result),
                parent=parent.result,
                limits=parent_test.limits(),
            )[0]
        )
        system, user = target._proposal_prompt(
            parent_test.task(), parent.result, pages
        )
        self.assertIn("only replace a baseline Unknown cell", system)
        self.assertIn("Copy the exact baseline headers", system)
        self.assertIn("Never add, delete, reorder", system)
        self.assertIn("baseline_table", user)
        self.assertEqual(len(inner.max_output_tokens), 3)

    def test_resealed_result_prediction_or_receipt_tamper_fails(self) -> None:
        _inner, _parent, value = self.execute(
            [parent_test.PLAN, parent_test.BASELINE, parent_test.SUPPORTED]
        )
        for kind in (
            "prediction",
            "known_edit",
            "task",
            "page",
            "proposal",
            "nested",
            "receipt",
            "hidden",
        ):
            changed = copy.deepcopy(value.result)
            if kind == "prediction":
                changed["prediction"] = changed["prediction"].replace(
                    "2026", "2027"
                )
                changed["prediction_sha256"] = __import__("hashlib").sha256(
                    changed["prediction"].encode()
                ).hexdigest()
            elif kind == "known_edit":
                changed["prediction"] = changed["prediction"].replace(
                    "Alpha", "Beta"
                )
                changed["prediction_sha256"] = __import__("hashlib").sha256(
                    changed["prediction"].encode()
                ).hexdigest()
            elif kind == "task":
                changed["private_visible_task"]["question"] += " altered"
            elif kind == "page":
                changed["private_same_forward_pages"][0]["content"] = (
                    "Alpha record. Date: 2027."
                )
            elif kind == "proposal":
                changed["private_model_proposal"] = changed[
                    "private_model_proposal"
                ].replace("2026", "2027")
            elif kind == "nested":
                nested = changed["monotone_unknown_fill_receipt"]
                core_receipt = nested["monotone_unknown_fill_receipt"]
                core_receipt["admitted_unknown_fill_count"] = 0
                core_receipt["prediction_changed"] = False
                core_receipt["candidate_identity_handoff"] = True
                core_receipt.pop("receipt_payload_sha256")
                core_receipt["receipt_payload_sha256"] = payload_sha256(
                    core_receipt
                )
                nested.pop("receipt_payload_sha256")
                nested["receipt_payload_sha256"] = payload_sha256(nested)
            elif kind == "receipt":
                nested = changed["monotone_unknown_fill_receipt"]
                nested["provider_request_delta"] = 0
                nested.pop("receipt_payload_sha256")
                nested["receipt_payload_sha256"] = payload_sha256(nested)
            else:
                changed["hidden"] = True
            changed.pop("result_payload_sha256")
            changed["result_payload_sha256"] = payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_result(
                    changed,
                    final_model_slot_receipt=value.final_model_slot_receipt,
                )

    def test_privileged_input_fails_before_third_effect(self) -> None:
        temporary, clock, _inner, model, parent = self.build(
            [parent_test.PLAN, parent_test.BASELINE, parent_test.SUPPORTED]
        )
        self.addCleanup(temporary.cleanup)
        before = model.receipt()
        with self.assertRaises(ValueError):
            target.run_monotone_unknown_fill(
                {**parent_test.task(), "question_type": "forbidden"},
                parent_result=parent.result,
                parent_model_slot_receipt=parent.model_slot_receipt,
                model=model,
                pages=parent_test.pages_for(parent.result),
                limits=parent_test.limits(),
                monotonic=clock,
            )
        self.assertEqual(before, model.receipt())

    def test_runtime_has_no_evaluator_or_historical_result_capability(self) -> None:
        path = ROOT / "src/deepwide_agent/v25290_monotone_unknown_fill_integration.py"
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        self.assertFalse(
            any("evaluator" in name or "finalize" in name for name in imports)
        )
        privileged: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Subscript) and isinstance(
                node.slice, ast.Constant
            ):
                if node.slice.value in {
                    "category",
                    "question_type",
                    "task_category",
                    "split",
                    "ground_truth",
                    "gold",
                    "answer_key",
                    "score",
                    "reward",
                }:
                    privileged.append(str(node.slice.value))
        self.assertEqual(privileged, [])
        public = next(
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "run_monotone_unknown_fill"
        )
        self.assertEqual(
            [item.arg for item in public.args.args + public.args.kwonlyargs],
            [
                "task",
                "parent_result",
                "parent_model_slot_receipt",
                "model",
                "pages",
                "limits",
                "monotonic",
            ],
        )


if __name__ == "__main__":
    unittest.main()
