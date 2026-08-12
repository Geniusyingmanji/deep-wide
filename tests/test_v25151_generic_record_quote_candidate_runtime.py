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

from deepwide_agent import v25151_generic_record_quote_candidate_runtime as target  # noqa: E402
from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import payload_sha256  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import (  # noqa: E402
    DeadlineAwareGlobalModelSlotLimiter,
)
from test_v25123_visible_legacy_query_compatible_runtime import (  # noqa: E402
    GroundedFrontierSearch,
    TASK,
)
from test_v25147_deterministic_quote_candidate_runtime import (  # noqa: E402
    CandidateModel,
    PRODUCTION,
)


COLUMNS = ("Domain", "Type", "TLD Manager")


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


class GenericRecordSearch(GroundedFrontierSearch):
    def __init__(self, question: str, phase: str, *, content: str) -> None:
        super().__init__(question, phase, field_page=True)
        self._generic_content = content

    def fetch_urls(self, requests):
        values = super().fetch_urls(requests)
        if self._phase == target.SECOND_PHASE:
            for response in values:
                for result in response["results"]:
                    if "iana.org/domains/root/db/records/in.html" in result["url"]:
                        result["raw_content"] = self._generic_content
        return values


class V25151GenericRecordQuoteCandidateTests(unittest.TestCase):
    def _extract(self, content: str):
        return target.extract_quote_candidates(
            PRODUCTION,
            columns=COLUMNS,
            pages=[{"title": "", "content": content}],
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

    def test_flat_json_object_record_is_exact_and_preverified(self) -> None:
        candidates, diagnostics = self._extract(
            '{"Domain":".in","Type":"country-code","TLD Manager":"999"}'
        )
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["new_value"], "999")
        self.assertEqual(candidates[0]["source_kind"], "flat_json_object_record")
        self.assertEqual(diagnostics["flat_json_object_observation_count"], 1)

    def test_inline_labelled_record_is_exact_and_preverified(self) -> None:
        content = "Domain: .in; Type: country-code; TLD Manager: 999"
        candidates, diagnostics = self._extract(content)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["exact_quote"], content)
        self.assertEqual(
            diagnostics["inline_labelled_record_observation_count"], 1
        )

    def test_contiguous_multiline_labelled_record_is_preverified(self) -> None:
        content = "Domain: .in\nType: country-code\nTLD Manager: 999"
        candidates, diagnostics = self._extract(content)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["exact_quote"], content)
        self.assertEqual(
            diagnostics["multiline_labelled_record_observation_count"], 1
        )

    def test_row_heading_followed_by_exact_fields_is_preverified(self) -> None:
        content = "## .in\nType: country-code\nTLD Manager: 999"
        candidates, diagnostics = self._extract(content)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["exact_quote"], content)
        self.assertEqual(
            diagnostics["heading_labelled_record_observation_count"], 1
        )

    def test_unlabelled_narrative_and_partial_record_fail_closed(self) -> None:
        for content in (
            ".in is managed by 999",
            "TLD Manager: 999",
            "Domain: .in\nManager: 999",
            '{"Domain":".in","manager":"999"}',
        ):
            with self.subTest(content=content):
                candidates, _diagnostics = self._extract(content)
                self.assertEqual(candidates, [])

    def test_conflicting_generic_grammars_are_omitted(self) -> None:
        content = (
            "Domain: .in; TLD Manager: 999\n\n"
            "Domain: .in; TLD Manager: 998"
        )
        candidates, diagnostics = self._extract(content)
        self.assertEqual(candidates, [])
        self.assertEqual(diagnostics["conflicting_candidate_count"], 2)

    def test_end_to_end_generic_record_selection_and_reverification(self) -> None:
        inner, result = self._run(
            "Domain: .in\nType: country-code\nTLD Manager: 999"
        )
        receipt = result["content_free_receipt"]
        self.assertEqual(inner.logical_calls, 4)
        self.assertGreater(receipt["raw_candidate_observation_count"], 0)
        self.assertEqual(receipt["available_candidate_count"], 1)
        self.assertEqual(receipt["selected_candidate_count"], 1)
        self.assertEqual(receipt["applied_edit_count"], 1)
        self.assertEqual(receipt["rejected_selected_edit_count"], 0)
        self.assertTrue(receipt["candidate_projection_valid"])
        self.assertIn("999", result["prediction"])

    def test_no_gain_remains_three_forwards_and_identity_replay(self) -> None:
        inner, result = self._run("Public background without requested fields.")
        receipt = result["content_free_receipt"]
        self.assertEqual(inner.logical_calls, 3)
        self.assertEqual(receipt["candidate_revision_entry_count"], 0)
        self.assertEqual(result["prediction"], result["production_prediction"])

    def test_receipt_tamper_fails_closed(self) -> None:
        _inner, result = self._run(
            "Domain: .in\nType: country-code\nTLD Manager: 999"
        )
        for kind in ("grammar", "accounting", "launch", "parent"):
            changed = copy.deepcopy(result)
            receipt = changed["content_free_receipt"]
            if kind == "grammar":
                receipt["flat_json_object_observation_count"] += 1
            elif kind == "accounting":
                receipt["selected_candidate_count"] += 1
            elif kind == "launch":
                receipt["benchmark_launch_or_evaluator_authorized"] = True
            else:
                changed["parent_result_payload_sha256"] = "0" * 64
            receipt.pop("receipt_payload_sha256")
            receipt["receipt_payload_sha256"] = payload_sha256(receipt)
            changed.pop("result_payload_sha256")
            changed["result_payload_sha256"] = payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_result(changed)

    def test_module_is_label_blind_build_only_and_effect_free(self) -> None:
        path = ROOT / "src/deepwide_agent/v25151_generic_record_quote_candidate_runtime.py"
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

    def test_receipt_is_content_free_and_signed_credit_zero(self) -> None:
        _inner, result = self._run(
            "Domain: .in\nType: country-code\nTLD Manager: 999"
        )
        semantic = {
            key: value
            for key, value in result["content_free_receipt"].items()
            if not key.endswith("sha256")
        }
        encoded = json.dumps(semantic, ensure_ascii=False)
        for forbidden in ("India", "IANA", "https://", "111", "999", TASK["opaque_id"]):
            self.assertNotIn(forbidden, encoded)
        self.assertFalse(result["entropy_or_information_gain_assigns_signed_credit"])


if __name__ == "__main__":
    unittest.main()
