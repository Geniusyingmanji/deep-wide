from __future__ import annotations

import ast
import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from deepwide_agent import v25117_grounded_target_record_plan as target  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import payload_sha256  # noqa: E402


QUESTION = (
    "A country has capital New Delhi and currency INR. Resolve the country, "
    "then use the visible IANA Root Zone Database authority to return one table. "
    "Columns exactly: Domain | Type | TLD Manager."
)
COLUMNS = ("Domain", "Type", "TLD Manager")
LEGACY = (
    "capital New Delhi currency INR country",
    "New Delhi INR official source",
    "country domain type",
    "country TLD manager",
)


def pages() -> list[dict[str, str]]:
    return [
        {
            "url": "https://example.org/country-profile",
            "title": "India country profile",
            "content": (
                "India is a country whose capital is New Delhi and currency is INR. "
                "The country code top-level domain is .in."
            ),
        }
    ]


def output(**changes: object) -> str:
    value: dict[str, object] = {
        "pivots": ["India"],
        "row_targets": [".in"],
        "authority_terms": ["IANA Root Zone Database"],
        "queries": [
            "India .in Domain Type IANA",
            "India .in TLD Manager IANA",
        ],
    }
    value.update(changes)
    return json.dumps(value)


class GroundedTargetRecordPlanTests(unittest.TestCase):
    def prepared(self, first=None):
        return target.prepare_plan(
            QUESTION,
            COLUMNS,
            LEGACY,
            pages() if first is None else first,
        )

    def test_grounded_hidden_pivot_and_row_target_apply(self) -> None:
        prepared = self.prepared()
        value = target.select_plan(
            prepared, output(), model_call_attempted=True
        )
        receipt = value["content_free_receipt"]
        self.assertTrue(receipt["strategy_applied"])
        self.assertEqual(value["pivots"], ["India"])
        self.assertEqual(value["row_targets"], [".in"])
        self.assertEqual(receipt["grounded_pivot_count"], 1)
        self.assertEqual(receipt["grounded_row_target_count"], 1)
        self.assertEqual(receipt["selected_query_target_overlap_count"], 2)
        self.assertEqual(receipt["selected_query_visible_anchor_count"], 2)
        self.assertEqual(receipt["selected_query_target_field_overlap_count"], 2)
        self.assertNotEqual(value["queries"], list(LEGACY[2:]))
        self.assertEqual(
            target.validate_plan(
                value,
                prepared=prepared,
                model_output=output(),
                model_call_attempted=True,
            ),
            value,
        )

    def test_hallucinated_or_body_instruction_phrase_fails_closed(self) -> None:
        prepared = self.prepared()
        hallucinated = target.select_plan(
            prepared,
            output(pivots=["Pakistan"]),
            model_call_attempted=True,
        )
        self.assertFalse(hallucinated["content_free_receipt"]["strategy_applied"])
        self.assertEqual(hallucinated["queries"], list(LEGACY[2:]))
        injected = target.select_plan(
            prepared,
            output(
                pivots=["India"],
                queries=[
                    "India ignore previous Domain Type",
                    "India .in TLD Manager",
                ],
            ),
            model_call_attempted=True,
        )
        self.assertFalse(injected["content_free_receipt"]["strategy_applied"])
        self.assertEqual(injected["queries"], list(LEGACY[2:]))

    def test_queries_must_each_use_target_and_visible_anchor(self) -> None:
        prepared = self.prepared()
        missing_target = target.select_plan(
            prepared,
            output(
                queries=[
                    "India .in Domain Type IANA",
                    "unrelated query TLD Manager",
                ]
            ),
            model_call_attempted=True,
        )
        self.assertFalse(missing_target["content_free_receipt"]["strategy_applied"])
        missing_field = target.select_plan(
            prepared,
            output(
                queries=[
                    "India .in official source",
                    "India .in official authority",
                ]
            ),
            model_call_attempted=True,
        )
        self.assertFalse(missing_field["content_free_receipt"]["strategy_applied"])

    def test_no_pages_invalid_json_or_no_model_is_exact_handoff(self) -> None:
        for prepared, raw, attempted in (
            (self.prepared([]), output(), True),
            (self.prepared(), "not json", True),
            (self.prepared(), output(), False),
        ):
            with self.subTest(attempted=attempted, raw=raw[:8]):
                value = target.select_plan(
                    prepared, raw, model_call_attempted=attempted
                )
                self.assertEqual(value["queries"], list(LEGACY[2:]))
                self.assertEqual(value["pivots"], [])
                self.assertTrue(
                    value["content_free_receipt"][
                        "exact_legacy_second_wave_handoff"
                    ]
                )

    def test_receipt_is_content_free_credit_zero_and_resealed_tamper_fails(self) -> None:
        value = target.select_plan(
            self.prepared(), output(), model_call_attempted=True
        )
        encoded = json.dumps(value["content_free_receipt"], ensure_ascii=False)
        for forbidden in (
            "India",
            ".in",
            "IANA",
            "Domain",
            "TLD Manager",
            "https://",
        ):
            self.assertNotIn(forbidden, encoded)
        self.assertFalse(
            value["content_free_receipt"][
                "entropy_or_information_gain_assigns_signed_credit"
            ]
        )
        tampered = copy.deepcopy(value["content_free_receipt"])
        tampered["selected_query_target_overlap_count"] = 1
        tampered.pop("receipt_payload_sha256")
        tampered["receipt_payload_sha256"] = payload_sha256(tampered)
        with self.assertRaises(ValueError):
            target.validate_receipt(tampered)

    def test_module_has_no_io_or_privileged_capability(self) -> None:
        path = ROOT / "src/deepwide_agent/v25117_grounded_target_record_plan.py"
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        for forbidden in (
            "os",
            "pathlib",
            "socket",
            "subprocess",
            "requests",
            "deepwidebench",
        ):
            self.assertFalse(
                any(
                    name == forbidden or name.startswith(forbidden + ".")
                    for name in imports
                )
            )
        for forbidden in (
            "answer_key",
            "benchmark_question_type",
            "results.csv",
            "ground_truth",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
