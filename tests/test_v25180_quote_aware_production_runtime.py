from __future__ import annotations

import ast
import copy
import hashlib
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
    v25165_observed_vertical_key_value_runtime as frozen_parent,
)
from deepwide_agent import (  # noqa: E402
    v25180_quote_aware_production_runtime as target,
)
from deepwide_agent.clients import ModelResult  # noqa: E402
from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import payload_sha256  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import (  # noqa: E402
    DeadlineAwareGlobalModelSlotLimiter,
)
from test_v25123_visible_legacy_query_compatible_runtime import TASK  # noqa: E402
from test_v25147_deterministic_quote_candidate_runtime import (  # noqa: E402
    CandidateModel,
)
from test_v25151_generic_record_quote_candidate_runtime import (  # noqa: E402
    GenericRecordSearch,
)


PRODUCTION = (
    "| Domain | Type | TLD Manager |\n"
    "| --- | --- | --- |\n"
    r"| .in | country \| code | 111 |"
)
CANDIDATE_CONTENT = '{"Domain":".in","TLD Manager":"999"}'
NO_GAIN_CONTENT = "Public background without requested fields."


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


class EscapedProductionModel(CandidateModel):
    def __init__(self, text: str = PRODUCTION, **kwargs) -> None:
        super().__init__(**kwargs)
        self.production_text = text

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
                text=self.production_text,
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


class V25180QuoteAwareProductionRuntimeTests(unittest.TestCase):
    def _run(
        self,
        runtime,
        *,
        content: str,
        inner=None,
    ):
        inner = inner or CandidateModel()
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            output_root = Path(raw)
            slots = output_root / "slots"
            slots.mkdir()
            for index in range(1, 5):
                (slots / f"slot_{index:02d}.lock").write_text(
                    "{}\n", encoding="utf-8"
                )
            model = DeadlineAwareGlobalModelSlotLimiter(
                inner,
                slot_directory=slots,
                output_root=output_root,
                slot_cap=4,
                absolute_deadline=time.monotonic() + 240,
            )
            searches = {
                phase: GenericRecordSearch(
                    TASK["question"], phase, content=content
                )
                for phase in runtime.PHASES
            }
            value = runtime.run_task(
                TASK,
                model=model,
                searches=searches,
                limits=limits(),
                monotonic=lambda: 100.0,
            )
        return inner, searches, runtime.validate_result(value)

    def test_accepted_raw_is_byte_exact_parent_behavior_and_effect_parity(self):
        for content, calls in (
            (NO_GAIN_CONTENT, 3),
            (CANDIDATE_CONTENT, 4),
        ):
            with self.subTest(content=content):
                inner, searches, value = self._run(
                    target, content=content, inner=CandidateModel()
                )
                parent_inner, parent_searches, expected = self._run(
                    frozen_parent, content=content, inner=CandidateModel()
                )
                self.assertEqual(value["parent_result"], expected)
                self.assertEqual(
                    value["production_prediction"],
                    expected["production_prediction"],
                )
                self.assertEqual(value["prediction"], expected["prediction"])
                self.assertEqual(value["cost"], expected["cost"])
                self.assertEqual(inner.logical_calls, calls)
                self.assertEqual(parent_inner.logical_calls, calls)
                self.assertEqual(
                    [searches[phase].calls for phase in target.PHASES],
                    [parent_searches[phase].calls for phase in target.PHASES],
                )
                receipt = value["content_free_receipt"]
                self.assertEqual(receipt["quote_aware_repair_attempt_count"], 0)
                self.assertEqual(receipt["public_export_attempt_count"], 0)

    def test_escaped_pipe_repairs_and_no_gain_remains_three_forwards(self):
        inner, _searches, value = self._run(
            target,
            content=NO_GAIN_CONTENT,
            inner=EscapedProductionModel(),
        )
        receipt = value["content_free_receipt"]
        self.assertEqual(inner.logical_calls, 3)
        self.assertEqual(receipt["quote_aware_repair_applied_count"], 1)
        self.assertEqual(receipt["public_export_completed_count"], 1)
        self.assertFalse(receipt["public_export_failure_present"])
        self.assertGreater(
            receipt["production_adjacent_pipe_whitespace_count"], 0
        )
        self.assertEqual(value["prediction"], value["production_prediction"])
        self.assertIn('"country | code"', value["prediction"])
        parsed = target.repair._public_loader_like_values(value["prediction"])
        self.assertEqual(parsed[1], [".in", "country|code", "111"])

    def test_positive_gain_keeps_four_forwards_and_candidate_publication(self):
        inner, _searches, value = self._run(
            target,
            content=CANDIDATE_CONTENT,
            inner=EscapedProductionModel(),
        )
        receipt = value["content_free_receipt"]
        self.assertEqual(inner.logical_calls, 4)
        self.assertNotEqual(value["prediction"], value["production_prediction"])
        self.assertIn("999", value["prediction"])
        self.assertTrue(receipt["final_entity_coordinates_subset"])
        self.assertFalse(receipt["candidate_publication_fallback"])
        self.assertEqual(value["cost"], value["parent_result"]["cost"])

    def test_row_width_and_ambiguous_escape_do_not_activate_repair(self):
        cases = (
            (
                "| Domain | Type | TLD Manager |\n"
                "| --- | --- | --- |\n"
                "| .in | country | code | 111 |"
            ),
            (
                "| Domain | Type | TLD Manager |\n"
                "| --- | --- | --- |\n"
                r"| .in | country\\|code | 111 |"
            ),
        )
        for text in cases:
            with self.subTest(text=text):
                _inner, _searches, value = self._run(
                    target,
                    content=NO_GAIN_CONTENT,
                    inner=EscapedProductionModel(text),
                )
                receipt = value["content_free_receipt"]
                self.assertEqual(receipt["quote_aware_repair_attempt_count"], 1)
                self.assertEqual(receipt["quote_aware_repair_applied_count"], 0)
                self.assertEqual(receipt["public_export_attempt_count"], 0)
                self.assertEqual(value["prediction_kind"], "fallback")

    def test_new_or_moved_entity_falls_back_to_completed_production(self):
        repaired = target.repair.normalize_quote_aware_table(
            PRODUCTION, ("Domain", "Type", "TLD Manager")
        )
        self.assertIsNotNone(repaired)
        production, _public, receipt = repaired or ("", "", {})
        moved = production.replace(
            ".in | country &#124; code | 111",
            ".in&#124;x | country-code | 999",
        )
        public_production, public_final, diagnostics = (
            target.export_public_predictions(
                production,
                moved,
                columns=("Domain", "Type", "TLD Manager"),
                expected_production_entity_cells=receipt[
                    "internal_entity_cell_count"
                ],
                expected_production_entity_occurrences=receipt[
                    "escaped_pipe_occurrence_count"
                ],
            )
        )
        self.assertEqual(public_final, public_production)
        self.assertFalse(diagnostics["final_entity_coordinates_subset"])
        self.assertTrue(diagnostics["candidate_publication_fallback"])

        extra_occurrence = production.replace(
            "country &#124; code", "country &#124; code &#124; extra"
        )
        _public_production, public_final, diagnostics = (
            target.export_public_predictions(
                production,
                extra_occurrence,
                columns=("Domain", "Type", "TLD Manager"),
                expected_production_entity_cells=receipt[
                    "internal_entity_cell_count"
                ],
                expected_production_entity_occurrences=receipt[
                    "escaped_pipe_occurrence_count"
                ],
            )
        )
        self.assertEqual(public_final, public_production)
        self.assertTrue(diagnostics["final_entity_coordinates_subset"])
        self.assertTrue(diagnostics["candidate_publication_fallback"])

    def test_observer_and_repair_failure_preserve_frozen_parent_fallback(self):
        for mode in ("observer", "repair"):
            if mode == "observer":
                patcher = mock.patch.object(
                    target.observer,
                    "observe_production_normalization",
                    side_effect=RuntimeError("synthetic observer failure"),
                )
            else:
                patcher = mock.patch.object(
                    target.repair,
                    "normalize_quote_aware_table",
                    side_effect=RuntimeError("synthetic repair failure"),
                )
            with self.subTest(mode=mode), patcher:
                _inner, _searches, value = self._run(
                    target,
                    content=NO_GAIN_CONTENT,
                    inner=EscapedProductionModel(),
                )
                receipt = value["content_free_receipt"]
                self.assertEqual(value["prediction_kind"], "fallback")
                self.assertEqual(value["prediction"], value["production_prediction"])
                self.assertEqual(receipt["quote_aware_repair_applied_count"], 0)
                if mode == "observer":
                    self.assertTrue(
                        receipt["raw_normalizer_observer_failure_present"]
                    )
                else:
                    self.assertTrue(receipt["quote_aware_repair_failure_present"])

    def test_public_export_failure_preserves_safe_completed_production(self):
        real_export = target.export_public_predictions
        with mock.patch.object(
            target,
            "export_public_predictions",
            side_effect=RuntimeError("synthetic export failure"),
        ):
            _inner, _searches, value = self._run(
                target,
                content=CANDIDATE_CONTENT,
                inner=EscapedProductionModel(),
            )
        receipt = value["content_free_receipt"]
        self.assertEqual(value["prediction"], value["production_prediction"])
        self.assertTrue(receipt["public_export_failure_present"])
        self.assertEqual(receipt["public_export_failure_type"], "RuntimeError")
        self.assertTrue(receipt["public_export_fallback_to_completed_production"])
        self.assertTrue(receipt["candidate_publication_fallback"])
        with mock.patch.object(target, "export_public_predictions", real_export):
            self.assertEqual(target.validate_result(value), value)

    def test_receipt_result_and_public_value_tamper_fail_closed(self):
        _inner, _searches, value = self._run(
            target,
            content=CANDIDATE_CONTENT,
            inner=EscapedProductionModel(),
        )
        for mode in ("count", "failure", "credit", "parent", "public"):
            changed = copy.deepcopy(value)
            receipt = changed["content_free_receipt"]
            if mode == "count":
                receipt["public_export_completed_count"] = 0
            elif mode == "failure":
                receipt["public_export_failure_present"] = True
            elif mode == "credit":
                receipt["entropy_or_information_gain_assigns_signed_credit"] = True
            elif mode == "parent":
                changed["parent_result_payload_sha256"] = "0" * 64
            else:
                changed["prediction"] = changed["prediction"].replace("999", "998")
                changed["prediction_sha256"] = hashlib.sha256(
                    changed["prediction"].encode()
                ).hexdigest()
            receipt.pop("receipt_payload_sha256")
            receipt["receipt_payload_sha256"] = payload_sha256(receipt)
            changed.pop("result_payload_sha256")
            changed["result_payload_sha256"] = payload_sha256(changed)
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                target.validate_result(changed)

    def test_receipt_is_content_free_label_blind_and_build_only(self):
        _inner, _searches, value = self._run(
            target,
            content=CANDIDATE_CONTENT,
            inner=EscapedProductionModel(),
        )
        encoded = json.dumps(value["content_free_receipt"], ensure_ascii=False)
        for forbidden in (
            "country|code",
            "Domain",
            "999",
            TASK["opaque_id"],
            "https://",
        ):
            self.assertNotIn(forbidden, encoded)
        source_path = ROOT / "src/deepwide_agent/v25180_quote_aware_production_runtime.py"
        source = source_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(source_path))
        imports: set[str] = set()
        privileged: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.add((node.module or "").split(".")[0])
            elif (
                isinstance(node, ast.Subscript)
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
            ):
                privileged.add(str(node.slice.value))
        self.assertTrue(
            imports.isdisjoint(
                {"os", "pathlib", "socket", "subprocess", "requests", "httpx", "openai"}
            )
        )
        self.assertEqual(privileged, set())
        self.assertNotIn("run_official_eval_local", source)
        self.assertFalse(value["entropy_or_information_gain_assigns_signed_credit"])
        self.assertFalse(value["benchmark_launch_or_evaluator_authorized"])


if __name__ == "__main__":
    unittest.main()
