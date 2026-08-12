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
for path in (ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import (  # noqa: E402
    v25158_vertical_key_value_candidate_runtime as target,
)
from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import payload_sha256  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import (  # noqa: E402
    DeadlineAwareGlobalModelSlotLimiter,
)
from test_v25123_visible_legacy_query_compatible_runtime import (  # noqa: E402
    TASK,
)
from test_v25147_deterministic_quote_candidate_runtime import (  # noqa: E402
    CandidateModel,
    PRODUCTION,
)
from test_v25151_generic_record_quote_candidate_runtime import (  # noqa: E402
    GenericRecordSearch,
)


COLUMNS = ("Domain", "Type", "TLD Manager")
VERTICAL = "Domain: | .in\n\nType= | country-code\nTLD Manager: | 999"


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


class V25158VerticalKeyValueCandidateTests(unittest.TestCase):
    def _extract(self, content: str, *, pages=None):
        return target.extract_quote_candidates(
            PRODUCTION,
            columns=COLUMNS,
            pages=pages or [{"title": "", "content": content}],
        )

    def _run(self, content: str):
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            output_root = Path(raw)
            slots = output_root / "slots"
            slots.mkdir()
            for index in range(1, 5):
                (slots / f"slot_{index:02d}.lock").write_text("{}\n")
            inner = CandidateModel()
            model = DeadlineAwareGlobalModelSlotLimiter(
                inner,
                slot_directory=slots,
                output_root=output_root,
                slot_cap=4,
                absolute_deadline=time.monotonic() + 240,
            )
            searches = {
                phase: GenericRecordSearch(TASK["question"], phase, content=content)
                for phase in target.PHASES
            }
            value = target.run_task(
                TASK, model=model, searches=searches, limits=limits()
            )
        return inner, target.validate_result(value)

    def test_blank_separated_trailing_punctuation_vertical_block_is_bound(self) -> None:
        candidates, diagnostics = self._extract(VERTICAL)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["row_identity"], ".in")
        self.assertEqual(candidates[0]["field"], "TLD Manager")
        self.assertEqual(candidates[0]["new_value"], "999")
        self.assertEqual(
            candidates[0]["source_kind"],
            "vertical_key_value_identity_field_span",
        )
        self.assertEqual(candidates[0]["exact_quote"], VERTICAL)
        self.assertEqual(diagnostics["vertical_pipe_block_count"], 1)
        self.assertEqual(diagnostics["vertical_identity_bound_block_count"], 1)
        self.assertEqual(
            diagnostics["vertical_key_value_record_observation_count"], 1
        )
        self.assertEqual(diagnostics["verifier_admissible_candidate_count"], 1)

    def test_identity_to_each_field_uses_its_own_unique_bounded_span(self) -> None:
        content = "Domain | .in\nTLD Manager | 999\nType | registry"
        candidates, _diagnostics = self._extract(content)
        by_field = {candidate["field"]: candidate for candidate in candidates}
        self.assertEqual(set(by_field), {"TLD Manager", "Type"})
        self.assertEqual(
            by_field["TLD Manager"]["exact_quote"],
            "Domain | .in\nTLD Manager | 999",
        )
        self.assertEqual(by_field["Type"]["exact_quote"], content)
        self.assertLessEqual(
            len(by_field["Type"]["exact_quote"]),
            target.MAXIMUM_QUOTE_CHARACTERS,
        )

    def test_duplicate_keys_multiple_identities_and_unknown_fail_closed(self) -> None:
        cases = {
            "duplicate-key": (
                "Domain | .in\nTLD Manager | 999\nTLD Manager: | 999"
            ),
            "multiple-identity": (
                "Domain | .in\nDomain: | .in\nTLD Manager | 999"
            ),
            "unknown": "Domain | .in\nTLD Manager | Unknown",
            "wrong-identity": "Domain | .us\nTLD Manager | 999",
        }
        for name, content in cases.items():
            with self.subTest(name=name):
                candidates, diagnostics = self._extract(content)
                self.assertEqual(candidates, [])
                self.assertEqual(diagnostics["available_candidate_count"], 0)

    def test_multiple_identity_bound_tables_on_one_page_are_ambiguous(self) -> None:
        content = (
            "Domain | .in\nTLD Manager | 999\n"
            "untrusted section boundary\n"
            "Domain | .in\nTLD Manager | 999"
        )
        candidates, diagnostics = self._extract(content)
        self.assertEqual(candidates, [])
        self.assertEqual(diagnostics["vertical_identity_bound_block_count"], 2)
        self.assertEqual(diagnostics["vertical_ambiguous_page_count"], 1)
        self.assertEqual(
            diagnostics["vertical_key_value_record_observation_count"], 0
        )

    def test_cross_page_join_is_forbidden_and_cross_page_conflict_abstains(self) -> None:
        candidates, _diagnostics = self._extract(
            "",
            pages=[
                {"title": "", "content": "Domain | .in"},
                {"title": "", "content": "TLD Manager | 999"},
            ],
        )
        self.assertEqual(candidates, [])

        candidates, diagnostics = self._extract(
            "",
            pages=[
                {"title": "", "content": "Domain | .in\nTLD Manager | 999"},
                {"title": "", "content": "Domain | .in\nTLD Manager | 998"},
            ],
        )
        self.assertEqual(candidates, [])
        self.assertEqual(diagnostics["conflicting_candidate_count"], 2)

    def test_overlong_identity_to_field_span_and_key_change_fail_closed(self) -> None:
        content = "Domain | .in\n" + ("\n" * 1_205) + "TLD Manager | 999"
        candidates, diagnostics = self._extract(content)
        self.assertEqual(candidates, [])
        self.assertEqual(diagnostics["vertical_identity_bound_block_count"], 1)

        candidates, _diagnostics = self._extract(
            "Domain | .in\nType | registry\nUnrelated | value"
        )
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["field"], "Type")
        self.assertNotEqual(candidates[0]["field"], "Domain")

    def test_existing_generic_grammars_are_preserved(self) -> None:
        candidates, diagnostics = self._extract(
            '{"Domain":".in","Type":"country-code","TLD Manager":"999"}'
        )
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["source_kind"], "flat_json_object_record")
        self.assertEqual(diagnostics["flat_json_object_observation_count"], 1)
        self.assertEqual(
            diagnostics["vertical_key_value_record_observation_count"], 0
        )

    def test_end_to_end_vertical_candidate_is_selected_and_reverified(self) -> None:
        inner, result = self._run(VERTICAL)
        receipt = result["content_free_receipt"]
        self.assertEqual(inner.logical_calls, 4)
        self.assertEqual(receipt["vertical_identity_bound_block_count"], 1)
        self.assertEqual(
            receipt["vertical_key_value_record_observation_count"], 1
        )
        self.assertEqual(receipt["available_candidate_count"], 1)
        self.assertEqual(receipt["selected_candidate_count"], 1)
        self.assertEqual(receipt["applied_edit_count"], 1)
        self.assertEqual(receipt["rejected_selected_edit_count"], 0)
        self.assertTrue(receipt["candidate_projection_valid"])
        self.assertIn("999", result["prediction"])
        self.assertNotEqual(result["prediction"], result["production_prediction"])

    def test_no_gain_preserves_three_forward_parent_path(self) -> None:
        inner, result = self._run("Public background without requested fields.")
        receipt = result["content_free_receipt"]
        self.assertEqual(inner.logical_calls, 3)
        self.assertEqual(receipt["candidate_revision_entry_count"], 0)
        self.assertEqual(receipt["vertical_pipe_block_count"], 0)
        self.assertEqual(result["prediction"], result["production_prediction"])

    def test_receipt_tamper_and_signed_credit_fail_closed(self) -> None:
        _inner, result = self._run(VERTICAL)
        receipt = result["content_free_receipt"]
        encoded = json.dumps(receipt, ensure_ascii=False)
        for forbidden in (".in", "999", "Domain", TASK["opaque_id"]):
            self.assertNotIn(forbidden, encoded)
        self.assertFalse(result["entropy_or_information_gain_assigns_signed_credit"])
        for kind in ("count", "launch", "parent"):
            changed = copy.deepcopy(result)
            changed_receipt = changed["content_free_receipt"]
            if kind == "count":
                changed_receipt["vertical_pipe_block_count"] = 0
            elif kind == "launch":
                changed_receipt["benchmark_launch_or_evaluator_authorized"] = True
            else:
                changed["parent_result_payload_sha256"] = "0" * 64
            changed_receipt.pop("receipt_payload_sha256")
            changed_receipt["receipt_payload_sha256"] = payload_sha256(
                changed_receipt
            )
            changed.pop("result_payload_sha256")
            changed["result_payload_sha256"] = payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_result(changed)

    def test_module_is_label_blind_build_only_and_effect_free(self) -> None:
        path = (
            ROOT
            / "src/deepwide_agent/v25158_vertical_key_value_candidate_runtime.py"
        )
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports: list[str] = []
        privileged: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
            elif isinstance(node, ast.Subscript) and isinstance(
                node.slice, ast.Constant
            ) and node.slice.value in {
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
        self.assertTrue(
            {name.split(".")[0] for name in imports}.isdisjoint(
                {"os", "pathlib", "socket", "subprocess", "requests", "httpx", "openai"}
            )
        )
        self.assertEqual(privileged, [])


if __name__ == "__main__":
    unittest.main()
