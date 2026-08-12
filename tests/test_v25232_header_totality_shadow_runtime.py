from __future__ import annotations

import ast
import copy
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import (  # noqa: E402
    v25188_export_failure_tolerant_same_response_runtime as frozen,
    v25232_header_totality_shadow_runtime as target,
)
from deepwide_agent.clients import ModelResult  # noqa: E402
from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import payload_sha256  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import (  # noqa: E402
    DeadlineAwareGlobalModelSlotLimiter,
)
from test_v25123_visible_legacy_query_compatible_runtime import TASK  # noqa: E402
from test_v25147_deterministic_quote_candidate_runtime import CandidateModel  # noqa: E402
from test_v25151_generic_record_quote_candidate_runtime import (  # noqa: E402
    GenericRecordSearch,
)


VERTICAL = "Domain | .in\nType | country-code\nTLD Manager | 999"
SAFE_SHADOW = (
    "| No. | Alias A | Alias B | Alias C |\n"
    "| --- | --- | --- | --- |\n"
    "| 1 | .in | country-code | 111 |"
)
MISSING_DATA = (
    "| No. | Alias A | Alias B | Alias C |\n"
    "| --- | --- | --- | --- |"
)
VALID = (
    "| Domain | Type | TLD Manager |\n"
    "| --- | --- | --- |\n"
    "| .in | country-code | 111 |"
)
QUOTE_AWARE = (
    "| Domain | Type | TLD Manager |\n"
    "| --- | --- | --- |\n"
    r"| .in | country\|code | 111 |"
)
NON_GENERIC_EXTRA = (
    "| Rank | Alias A | Alias B | Alias C |\n"
    "| --- | --- | --- | --- |\n"
    "| 1 | .in | country-code | 111 |"
)


def limits() -> ScoreFirstLimits:
    return ScoreFirstLimits(
        wall_seconds=240,
        model_calls=3,
        search_queries=4,
        fetch_targets=10,
        search_results_per_query=3,
        evidence_chars=60_000,
        page_chars=5_000,
    )


class ProductionModel(CandidateModel):
    def __init__(self, production: str) -> None:
        super().__init__()
        self.production = production

    def complete(self, system, user, *, max_output_tokens, json_mode=False):
        if self.logical_calls == 2:
            self.prompts.append((str(system), str(user), bool(json_mode)))
            self.logical_calls += 1
            self.requests += 1
            self.attempts += 1
            self.input_tokens += 10
            self.output_tokens += 5
            self.total_tokens += 15
            return ModelResult(
                text=self.production,
                usage={},
                response_id=None,
                attempts=1,
                output_truncated=False,
            )
        return super().complete(
            system,
            user,
            max_output_tokens=max_output_tokens,
            json_mode=json_mode,
        )


class V25232HeaderTotalityShadowRuntimeTests(unittest.TestCase):
    @classmethod
    def _without_timing_or_seals(cls, value):
        if isinstance(value, dict):
            return {
                key: cls._without_timing_or_seals(child)
                for key, child in value.items()
                if not str(key).endswith("sha256")
                and key not in {"elapsed_seconds"}
            }
        if isinstance(value, list):
            return [cls._without_timing_or_seals(child) for child in value]
        return value

    def _run(self, module, production: str, *, shadow_failure: bool = False):
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            output_root = Path(raw)
            slots = output_root / "slots"
            slots.mkdir()
            for index in range(1, 5):
                (slots / f"slot_{index:02d}.lock").write_text("{}\n")
            inner = ProductionModel(production)
            model = DeadlineAwareGlobalModelSlotLimiter(
                inner,
                slot_directory=slots,
                output_root=output_root,
                slot_cap=4,
                absolute_deadline=time.monotonic() + 240,
            )
            searches = {
                phase: GenericRecordSearch(TASK["question"], phase, content=VERTICAL)
                for phase in module.PHASES
            }
            patcher = (
                mock.patch.object(
                    target.shadow,
                    "normalize_index_positional_header_table",
                    side_effect=RuntimeError("synthetic shadow failure"),
                )
                if shadow_failure
                else mock.patch.object(
                    target.shadow,
                    "normalize_index_positional_header_table",
                    wraps=target.shadow.normalize_index_positional_header_table,
                )
            )
            with patcher:
                value = module.run_task(
                    TASK,
                    model=model,
                    searches=searches,
                    limits=limits(),
                    monotonic=time.monotonic,
                )
        return inner, module.validate_result(value)

    def test_safe_shadow_candidate_is_observed_but_parent_is_unchanged(self) -> None:
        baseline_inner, baseline = self._run(frozen, SAFE_SHADOW)
        inner, result = self._run(target, SAFE_SHADOW)
        receipt = result["content_free_receipt"]
        self.assertEqual(inner.logical_calls, baseline_inner.logical_calls)
        self.assertEqual(
            self._without_timing_or_seals(result["parent_result"]),
            self._without_timing_or_seals(baseline),
        )
        self.assertEqual(result["predictions"], baseline["predictions"])
        self.assertEqual(result["prediction_sha256"], baseline["prediction_sha256"])
        self.assertEqual(result["prediction_kind"], baseline["prediction_kind"])
        self.assertEqual(result["cost"], baseline["cost"])
        self.assertEqual(receipt["shadow_eligibility_count"], 1)
        self.assertEqual(receipt["shadow_entry_count"], 1)
        self.assertEqual(receipt["shadow_completed_count"], 1)
        self.assertEqual(receipt["shadow_candidate_available_count"], 1)
        self.assertTrue(receipt["shadow_receipt"]["accepted"])
        self.assertEqual(result["prediction_kind"], "fallback")

    def test_missing_data_is_observed_and_remains_fail_closed(self) -> None:
        baseline_inner, baseline = self._run(frozen, MISSING_DATA)
        inner, result = self._run(target, MISSING_DATA)
        receipt = result["content_free_receipt"]
        self.assertEqual(inner.logical_calls, baseline_inner.logical_calls)
        self.assertEqual(
            self._without_timing_or_seals(result["parent_result"]),
            self._without_timing_or_seals(baseline),
        )
        self.assertEqual(receipt["shadow_eligibility_count"], 1)
        self.assertEqual(receipt["shadow_candidate_available_count"], 0)
        self.assertEqual(
            receipt["shadow_receipt"]["disposition_counts"][
                "missing_data_rows_reject"
            ],
            1,
        )

    def test_parent_valid_table_does_not_enter_shadow(self) -> None:
        baseline_inner, baseline = self._run(frozen, VALID)
        inner, result = self._run(target, VALID)
        receipt = result["content_free_receipt"]
        self.assertEqual(inner.logical_calls, baseline_inner.logical_calls)
        self.assertEqual(
            self._without_timing_or_seals(result["parent_result"]),
            self._without_timing_or_seals(baseline),
        )
        self.assertEqual(receipt["shadow_eligibility_count"], 0)
        self.assertEqual(receipt["shadow_entry_count"], 0)
        self.assertIsNone(receipt["shadow_receipt"])
        self.assertEqual(result["prediction_kind"], "model_generated")

    def test_quote_aware_active_state_does_not_enter_shadow(self) -> None:
        baseline_inner, baseline = self._run(frozen, QUOTE_AWARE)
        inner, result = self._run(target, QUOTE_AWARE)
        receipt = result["content_free_receipt"]
        self.assertEqual(inner.logical_calls, baseline_inner.logical_calls)
        self.assertEqual(
            self._without_timing_or_seals(result["parent_result"]),
            self._without_timing_or_seals(baseline),
        )
        self.assertEqual(receipt["parent_quote_aware_repair_applied_count"], 1)
        self.assertEqual(receipt["shadow_eligibility_count"], 0)
        self.assertEqual(receipt["shadow_entry_count"], 0)
        self.assertIsNone(receipt["shadow_receipt"])

    def test_non_generic_extra_column_enters_observer_but_has_no_candidate(self) -> None:
        _baseline_inner, baseline = self._run(frozen, NON_GENERIC_EXTRA)
        _inner, result = self._run(target, NON_GENERIC_EXTRA)
        receipt = result["content_free_receipt"]
        self.assertEqual(
            self._without_timing_or_seals(result["parent_result"]),
            self._without_timing_or_seals(baseline),
        )
        self.assertEqual(receipt["shadow_eligibility_count"], 1)
        self.assertEqual(receipt["shadow_completed_count"], 1)
        self.assertEqual(receipt["shadow_candidate_available_count"], 0)
        self.assertEqual(
            receipt["shadow_receipt"]["disposition_counts"][
                "no_generic_leading_index_header_reject"
            ],
            1,
        )

    def test_shadow_failure_is_isolated_and_parent_is_unchanged(self) -> None:
        _baseline_inner, baseline = self._run(frozen, SAFE_SHADOW)
        inner, result = self._run(target, SAFE_SHADOW, shadow_failure=True)
        receipt = result["content_free_receipt"]
        self.assertEqual(inner.logical_calls, 3)
        self.assertEqual(
            self._without_timing_or_seals(result["parent_result"]),
            self._without_timing_or_seals(baseline),
        )
        self.assertEqual(receipt["shadow_entry_count"], 1)
        self.assertEqual(receipt["shadow_completed_count"], 0)
        self.assertTrue(receipt["shadow_failure_present"])
        self.assertEqual(receipt["shadow_failure_type"], "RuntimeError")
        self.assertIsNone(receipt["shadow_receipt"])

    def test_receipt_is_content_free_and_tamper_fails_closed(self) -> None:
        _inner, result = self._run(target, SAFE_SHADOW)
        receipt = result["content_free_receipt"]
        encoded = json.dumps(receipt, ensure_ascii=False, sort_keys=True)
        for forbidden in (
            "Alias",
            ".in",
            "country-code",
            "111",
            "Domain",
            TASK["opaque_id"],
            "https://",
        ):
            self.assertNotIn(forbidden, encoded)
        for kind in ("count", "parent", "behavior", "credit", "launch"):
            changed = copy.deepcopy(result)
            observed = changed["content_free_receipt"]
            if kind == "count":
                observed["shadow_candidate_available_count"] = 0
            elif kind == "parent":
                observed["parent_raw_no_bindable_header_reject"] = False
            elif kind == "behavior":
                observed[
                    "shadow_changes_response_fallback_prediction_candidate_routing_or_budget"
                ] = True
            elif kind == "credit":
                observed["entropy_or_information_gain_assigns_signed_credit"] = True
            else:
                observed["external_forward_evaluator_or_benchmark_authorized"] = True
            observed.pop("receipt_payload_sha256")
            observed["receipt_payload_sha256"] = payload_sha256(observed)
            changed.pop("result_payload_sha256")
            changed["result_payload_sha256"] = payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_result(changed)

    def test_module_is_label_blind_and_uses_no_global_monkeypatch(self) -> None:
        path = ROOT / "src/deepwide_agent/v25232_header_totality_shadow_runtime.py"
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        privileged = {
            str(node.slice.value)
            for node in ast.walk(tree)
            if isinstance(node, ast.Subscript)
            and isinstance(node.slice, ast.Constant)
            and node.slice.value
            in {
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
        }
        module_names = {"effect_parent", "parent", "shadow"}
        assignments_to_other_modules = []
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                continue
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(
                isinstance(target_node, ast.Attribute)
                and isinstance(target_node.value, ast.Name)
                and target_node.value.id in module_names
                for target_node in targets
            ):
                assignments_to_other_modules.append(node)
        self.assertEqual(privileged, set())
        self.assertEqual(assignments_to_other_modules, [])
        self.assertFalse(target.__dict__.get("benchmark_launch"))


if __name__ == "__main__":
    unittest.main()
