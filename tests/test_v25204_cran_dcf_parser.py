from __future__ import annotations

import ast
import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25204_cran_dcf_parser as target  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import payload_sha256  # noqa: E402


class V25204CranDCFParserTests(unittest.TestCase):
    def test_accepts_cran_underscore_dot_hyphen_fields(self) -> None:
        records = target.parse_records(
            "Package: demo\n"
            "Version: 1\n"
            "License_is_FOSS: yes\n"
            "License.restricts-use: no\n"
            "NeedsCompilation: yes\n"
        )
        self.assertEqual(records[0]["License_is_FOSS"], "yes")
        self.assertEqual(records[0]["License.restricts-use"], "no")

    def test_continuation_unfolding_and_record_order_are_exact(self) -> None:
        records = target.parse_records(
            b"Package: first\r\nLicense: GPL-2 |\r\n GPL-3\r\n\r\nPackage: second\r\nVersion: 2\r\n"
        )
        self.assertEqual([row["Package"] for row in records], ["first", "second"])
        self.assertEqual(records[0]["License"], "GPL-2 | GPL-3")

    def test_each_failure_stage_is_finite_and_content_free(self) -> None:
        cases = {
            "decode": b"\xff",
            "orphan_continuation": " secret-payload\n",
            "missing_separator": "SecretPayload demo\n",
            "invalid_field_name": "Secret Payload: value\n",
            "duplicate_field": "Package: secret-payload\nPackage: two\n",
        }
        for stage, value in cases.items():
            records, observed = target.parse_with_observation(value)
            with self.subTest(stage=stage):
                self.assertEqual(records, [])
                self.assertEqual(observed["failure_stage"], stage)
                self.assertNotIn("secret-payload", str(observed))
                self.assertNotIn("SecretPayload", str(observed))

    def test_success_observation_reports_only_record_count(self) -> None:
        records, observed = target.parse_with_observation(
            "Package: secret-name\nVersion: 1\n"
        )
        self.assertEqual(len(records), 1)
        self.assertEqual(observed["record_count"], 1)
        self.assertIsNone(observed["failure_stage"])
        self.assertNotIn("secret-name", str(observed))

    def test_observation_tamper_fails_closed(self) -> None:
        value = target.observation(stage=None, record_count=2)
        changed = copy.deepcopy(value)
        changed["entropy_or_information_gain_assigns_signed_credit"] = True
        changed.pop("observation_payload_sha256")
        changed["observation_payload_sha256"] = payload_sha256(changed)
        with self.assertRaises(ValueError):
            target.validate_observation(changed)

    def test_module_is_label_blind_and_effect_free(self) -> None:
        path = ROOT / "src/deepwide_agent/v25204_cran_dcf_parser.py"
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        privileged = {
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
        hits = {
            str(node.slice.value)
            for node in ast.walk(tree)
            if isinstance(node, ast.Subscript)
            and isinstance(node.slice, ast.Constant)
            and node.slice.value in privileged
        }
        calls = {
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }
        self.assertEqual(hits, set())
        self.assertTrue(
            calls.isdisjoint(
                {"post", "search_many", "fetch_urls", "complete", "open"}
            )
        )


if __name__ == "__main__":
    unittest.main()
