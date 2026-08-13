from __future__ import annotations

import ast
import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent import v25117_grounded_target_record_plan as parent  # noqa: E402
from deepwide_agent import v25346_grounded_fact_bootstrap as target  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import payload_sha256  # noqa: E402


QUESTION = "Build a table of packages with columns Package and Latest version."
COLUMNS = ["Package", "Latest version"]
LEGACY = [
    "packages latest version",
    "package index versions",
    "packages official latest version",
    "package registry version list",
]
PAGES = [
    {
        "url": "https://registry.example/alpha",
        "title": "Alpha package",
        "content": (
            "Package alpha has Latest version 2.3.4 in the official registry. "
            "Release metadata and archive links follow."
        ),
    }
]
PLAN = {
    "pivots": ["Package alpha"],
    "row_targets": ["alpha"],
    "authority_terms": ["official registry"],
    "queries": [
        "alpha package official registry",
        "alpha Latest version official registry",
    ],
}
QUOTE = "Package alpha has Latest version 2.3.4 in the official registry."
RECORD = {
    "page_ordinal": 1,
    "quote": QUOTE,
    "row_identity": "alpha",
    "fields": [
        {
            "column": "Latest version",
            "source_field": "Latest version",
            "value": "2.3.4",
        }
    ],
}


def joint(records):
    return json.dumps({**PLAN, "records": records}, ensure_ascii=False)


def production_user() -> str:
    evidence = (
        "[[EVIDENCE 1]]\n"
        "title=Alpha package\n"
        "url=https://registry.example/alpha\n"
        "content="
        + PAGES[0]["content"]
        + "\n\n"
        + ("background registry material " * 180)
    )
    return (
        "VISIBLE QUESTION:\n"
        + QUESTION
        + "\n\nREQUIRED COLUMNS:\n"
        + json.dumps(COLUMNS)
        + "\n\nBOUNDED WEB MATERIAL:\n"
        + evidence
        + "\n\nProduce the best-supported answer possible within the supplied material."
    )


class V25346GroundedFactBootstrapTests(unittest.TestCase):
    def test_joint_system_extends_without_replacing_parent_contract(self) -> None:
        original = parent.SYSTEM_PROMPT + "\n\nPARENT CHECKLIST"
        changed = target.joint_system(original)
        self.assertTrue(changed.startswith(original))
        self.assertIn('"records"', changed[len(original) :])
        with self.assertRaises(ValueError):
            target.joint_system("unrelated system")

    def test_joint_response_strips_records_for_frozen_parent_parser(self) -> None:
        raw = joint([RECORD])
        stripped = target.parent_grounded_output(raw)
        parsed = json.loads(stripped)
        self.assertEqual(set(parsed), target.PARENT_PLAN_KEYS)
        self.assertNotIn("records", parsed)
        prepared = parent.prepare_plan(QUESTION, COLUMNS, LEGACY, PAGES)
        selected = parent.select_plan(
            prepared, stripped, model_call_attempted=True
        )
        self.assertEqual(selected["queries"], PLAN["queries"])
        self.assertTrue(selected["content_free_receipt"]["strategy_applied"])

    def test_verified_fact_changes_same_length_production_prompt(self) -> None:
        control = production_user()
        value = target.build_bootstrap(
            question=QUESTION,
            columns=COLUMNS,
            first_wave_pages=PAGES,
            grounded_model_output=joint([RECORD]),
            production_user=control,
            model_call_attempted=True,
        )
        receipt = value["content_free_receipt"]
        self.assertEqual(len(value["candidate_production_user"]), len(control))
        self.assertNotEqual(value["candidate_production_user"], control)
        self.assertIn("[QUOTE_VERIFIED_RECORD R0001", value["candidate_production_user"])
        self.assertEqual(receipt["additional_model_call_count"], 0)
        self.assertEqual(receipt["verified_record_count"], 1)
        self.assertEqual(receipt["verified_field_count"], 1)
        self.assertEqual(receipt["rendered_record_count"], 1)
        self.assertTrue(receipt["candidate_production_prompt_changed"])
        self.assertTrue(receipt["record_output_strictly_valid"])

    def test_nonverbatim_fact_returns_parent_prompt_byte_exact(self) -> None:
        control = production_user()
        bad = copy.deepcopy(RECORD)
        bad["quote"] = "Package alpha has Latest version 9.9.9 in the official registry."
        bad["fields"][0]["value"] = "9.9.9"
        value = target.build_bootstrap(
            question=QUESTION,
            columns=COLUMNS,
            first_wave_pages=PAGES,
            grounded_model_output=joint([bad]),
            production_user=control,
            model_call_attempted=True,
        )
        receipt = value["content_free_receipt"]
        self.assertEqual(value["candidate_production_user"], control)
        self.assertEqual(receipt["verified_record_count"], 0)
        self.assertFalse(receipt["candidate_production_prompt_changed"])

    def test_conflicting_same_coordinate_fails_closed(self) -> None:
        control = production_user()
        page = copy.deepcopy(PAGES[0])
        page["content"] = (
            "Package alpha has Latest version 2.3.4 and prior version 2.3.3 "
            "in the official registry."
        )
        quote_text = page["content"]
        left = copy.deepcopy(RECORD)
        left["quote"] = quote_text
        right = copy.deepcopy(RECORD)
        right["quote"] = quote_text
        right["fields"][0]["value"] = "2.3.3"
        value = target.build_bootstrap(
            question=QUESTION,
            columns=COLUMNS,
            first_wave_pages=[page],
            grounded_model_output=joint([left, right]),
            production_user=control,
            model_call_attempted=True,
        )
        binding = value["content_free_receipt"]["record_binding_receipt"]
        self.assertEqual(value["candidate_production_user"], control)
        self.assertEqual(binding["ambiguous_same_quote_record_count"], 1)
        self.assertEqual(binding["rendered_record_count"], 0)

    def test_parent_only_or_one_column_output_is_total_noop(self) -> None:
        control = production_user()
        cases = (
            (json.dumps(PLAN), COLUMNS),
            (joint([RECORD]), ["Result"]),
            ("not-json", COLUMNS),
        )
        for raw, columns in cases:
            with self.subTest(columns=columns, raw=raw[:8]):
                value = target.build_bootstrap(
                    question=QUESTION,
                    columns=columns,
                    first_wave_pages=PAGES,
                    grounded_model_output=raw,
                    production_user=control,
                    model_call_attempted=True,
                )
                self.assertEqual(value["candidate_production_user"], control)
                self.assertEqual(
                    value["content_free_receipt"]["additional_model_call_count"], 0
                )

    def test_resealed_receipt_or_artifact_tamper_fails_closed(self) -> None:
        value = target.build_bootstrap(
            question=QUESTION,
            columns=COLUMNS,
            first_wave_pages=PAGES,
            grounded_model_output=joint([RECORD]),
            production_user=production_user(),
            model_call_attempted=True,
        )
        for kind in ("count", "credit", "authorization", "prompt"):
            changed = copy.deepcopy(value)
            receipt = changed["content_free_receipt"]
            if kind == "count":
                receipt["additional_model_call_count"] = 1
            elif kind == "credit":
                receipt["positive_signed_credit_count"] = 1
            elif kind == "authorization":
                receipt["benchmark_launch_or_evaluator_authorized"] = True
            else:
                changed["candidate_production_user"] += "x"
                changed["candidate_production_user_sha256"] = __import__(
                    "hashlib"
                ).sha256(changed["candidate_production_user"].encode()).hexdigest()
            receipt.pop("receipt_payload_sha256")
            receipt["receipt_payload_sha256"] = payload_sha256(receipt)
            changed.pop("artifact_payload_sha256")
            changed["artifact_payload_sha256"] = payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_bootstrap(changed)

    def test_component_is_label_blind_pure_and_build_only(self) -> None:
        path = ROOT / "src/deepwide_agent/v25346_grounded_fact_bootstrap.py"
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports: list[str] = []
        privileged: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
            elif isinstance(node, ast.Subscript) and isinstance(
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
        self.assertEqual(privileged, [])
        for forbidden in (
            "run_official_eval_local",
            "api_key",
            "os.environ",
            "target/main",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
