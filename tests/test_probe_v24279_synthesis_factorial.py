from __future__ import annotations

import copy
import json
import unittest

from scripts import preregister_v24279_synthesis_factorial as prereg
from scripts import probe_v24279_synthesis_factorial as target


def outcome(case: int, arm: str) -> dict:
    spec = next(value for value in prereg.ARMS if value["name"] == arm)
    candidate = arm != "low_free"
    no_reasoning = spec["reasoning"] == "none"
    return {
        "case": case,
        "arm": arm,
        "reasoning": spec["reasoning"],
        "format": spec["format"],
        "terminal": True,
        "failure_type": None,
        "http_status": 200,
        "response_status": "completed",
        "incomplete_reason": "",
        "wall_seconds": 6.0 if candidate else 10.0,
        "input_tokens": 110 if candidate else 100,
        "output_tokens": 30 if no_reasoning else (60 if candidate else 100),
        "reasoning_tokens": 0 if no_reasoning else 20,
        "cached_input_tokens": 0,
        "total_tokens": 140 if no_reasoning else (170 if candidate else 200),
        "request_body_bytes": 1000,
        "row_count": 3,
        "column_count": 3,
        "nonempty_cell_count": 9,
        "exact_cell_match_count": 9,
        "expected_cell_count": 9,
        "canonical_markdown_valid": True,
        "response_text_or_hash_persisted": False,
        "synthetic_evidence_value_persisted": False,
        "benchmark_question_query_url_page_prediction_answer_task_id_or_hash_persisted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
    }


class V24279SynthesisFactorialTests(unittest.TestCase):
    def setUp(self) -> None:
        self.protocol = prereg.build_protocol(require_pristine=False, now=1)
        self.rows = [
            outcome(case, arm["name"])
            for case in range(1, prereg.CASE_COUNT + 1)
            for arm in prereg.ARMS
        ]

    def test_protocol_freezes_balanced_factorial_without_benchmark_authority(self) -> None:
        prereg.validate_protocol(value=self.protocol)
        self.assertEqual(len(prereg.schedule()), 4)
        self.assertFalse(any(self.protocol["authorization"].values()))

    def test_strict_body_and_parsers_preserve_exact_synthetic_cells(self) -> None:
        strict_item = next(
            item
            for item in prereg.schedule()[0]
            if item["format"] == "strict_json"
        )
        body = target._body(prereg.SYNTHETIC_CASES[0], strict_item)
        self.assertEqual(body["text"]["format"]["type"], "json_schema")
        self.assertTrue(body["text"]["format"]["strict"])
        rows = prereg.SYNTHETIC_CASES[0]["rows"]
        strict_rows, valid = target._strict_rows(json.dumps({"rows": rows}))
        self.assertTrue(valid)
        shape = target._evaluate_rows(prereg.SYNTHETIC_CASES[0], strict_rows, valid)
        self.assertEqual(shape["exact_cell_match_count"], 9)
        free_rows, free_valid = target._free_rows(target._render(rows))
        self.assertTrue(free_valid)
        self.assertEqual(
            target._evaluate_rows(prereg.SYNTHETIC_CASES[0], free_rows, free_valid)[
                "exact_cell_match_count"
            ],
            9,
        )

    def test_synthetic_pareto_candidate_passes(self) -> None:
        summary = target.summarize(self.protocol, self.rows, 40.0)
        self.assertTrue(summary["passed"])
        self.assertIn("none_strict", summary["eligible_candidates"])
        self.assertEqual(summary["selected_candidate"], "none_strict")

    def test_missing_cell_slow_or_token_heavy_candidates_fail_closed(self) -> None:
        missing = copy.deepcopy(self.rows)
        for row in missing:
            if row["arm"] != "low_free":
                row["exact_cell_match_count"] = 8
        summary = target.summarize(self.protocol, missing, 40.0)
        self.assertFalse(summary["passed"])
        self.assertEqual(summary["eligible_candidates"], [])

        heavy = copy.deepcopy(self.rows)
        for row in heavy:
            if row["arm"] != "low_free":
                row["output_tokens"] = 100
                row["total_tokens"] = 220
                row["wall_seconds"] = 12.0
        summary = target.summarize(self.protocol, heavy, 40.0)
        self.assertFalse(summary["passed"])

        unsafe = outcome(1, "none_strict")
        unsafe["generated_output"] = "forbidden"
        with self.assertRaisesRegex(RuntimeError, "schema"):
            target.validate_arm(unsafe)


if __name__ == "__main__":
    unittest.main()
