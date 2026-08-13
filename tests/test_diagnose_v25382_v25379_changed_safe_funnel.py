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

from scripts import diagnose_v25382_v25379_changed_safe_funnel as target  # noqa: E402


class V25382ChangedSafeFunnelDiagnosisTests(unittest.TestCase):
    def test_authoritative_aggregate_funnel_recomputes(self) -> None:
        value = target.build_diagnosis(now=1)
        counts = value["funnel"]["counts"]
        self.assertEqual(counts["task_count"], 220)
        self.assertEqual(counts["record_model_attempted_tasks"], 209)
        self.assertEqual(counts["parsed_record_tasks"], 12)
        self.assertEqual(counts["verified_record_tasks"], 6)
        self.assertEqual(counts["verified_coordinate_count"], 9)
        self.assertEqual(counts["missing_row_rejected_field_count"], 7)
        self.assertEqual(counts["changed_safe_tasks"], 1)

    def test_decision_is_no_go_and_build_only(self) -> None:
        value = target.build_diagnosis(now=1)
        self.assertEqual(value["decision"]["v25379_quality"], "no_go")
        self.assertTrue(value["authorization"]["next_build_only"])
        self.assertFalse(value["authorization"]["new_external_forward"])
        self.assertFalse(value["authorization"]["deepwidebench_forward_or_evaluator"])
        self.assertFalse(value["decision"]["entropy_or_information_gain_signed_credit_authorized"])

    def test_resealed_count_or_authorization_tamper_fails(self) -> None:
        value = target.build_diagnosis(now=1)
        for path, replacement in (
            (("funnel", "counts", "changed_safe_tasks"), 2),
            (("authorization", "new_external_forward"), True),
        ):
            changed = copy.deepcopy(value)
            changed.pop("diagnosis_payload_sha256")
            cursor = changed
            for key in path[:-1]:
                cursor = cursor[key]
            cursor[path[-1]] = replacement
            changed["diagnosis_payload_sha256"] = target.contract.payload_sha256(changed)
            with self.assertRaises(ValueError):
                target.validate_diagnosis(changed)

    def test_source_has_no_external_or_privileged_capability(self) -> None:
        tree = ast.parse((ROOT / target.SOURCE).read_text(encoding="utf-8"))
        imports = []
        privileged = {
            "category",
            "question_type",
            "task_category",
            "ground_truth",
            "answer_key",
            "split",
            "reward",
        }
        hits = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
            elif isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
                if node.slice.value in privileged:
                    hits.append(node.slice.value)
        self.assertEqual(hits, [])
        self.assertFalse(
            any(
                name in {"socket", "subprocess", "urllib", "requests", "httpx"}
                or "evaluator" in name
                for name in imports
            )
        )


if __name__ == "__main__":
    unittest.main()
