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

from scripts import diagnose_v25574_v25573_exact220 as target  # noqa: E402


class V25574V25573Exact220DiagnosisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = target.build_diagnosis(now=1)

    def test_root_cause_and_replay_are_exact(self) -> None:
        failure = self.value["persistent_failure_diagnosis"]
        self.assertEqual(failure["raw_vs_canonical_column_drift_tasks"], 11)
        self.assertTrue(
            failure["raw_vs_canonical_column_drift_set_equals_outer_failure_set"]
        )
        self.assertEqual(
            failure["real_v25395_validator_replay_failure_tasks"], 11
        )
        self.assertEqual(
            failure["real_v25395_validator_replay_exception_histogram"],
            {"ValueError: V2.53.95 selected verifier state drifted": 11},
        )

    def test_reliability_and_quality_are_not_conflated(self) -> None:
        funnel = self.value["reliability_funnel"]
        self.assertEqual(funnel["v25568_outer_failure_tasks"], 40)
        self.assertEqual(funnel["v25573_outer_failure_tasks"], 11)
        self.assertEqual(
            funnel["v25568_failure_to_v25573_runtime_recovered_tasks"], 29
        )
        self.assertEqual(funnel["recovered_canonical_model_generated_tasks"], 24)
        self.assertEqual(funnel["recovered_safe_parent_handoff_tasks"], 5)
        self.assertEqual(
            funnel["recovered_metrics_v25573"]["whole_table_successes"], 0
        )
        self.assertEqual(funnel["v25573_candidate_changed_tasks"], 4)
        self.assertEqual(
            funnel["v25573_candidate_changed_metrics"][
                "whole_table_successes"
            ],
            0,
        )

    def test_rollout_variability_is_descriptive_only(self) -> None:
        value = self.value["rollout_variability_descriptive_not_causal"]
        self.assertEqual(
            value["exact_pattern_histogram"],
            {"00": 211, "10": 5, "11": 4},
        )
        self.assertTrue(
            value["independent_cold_rollouts_do_not_identify_wrapper_causality"]
        )

    def test_resealed_tamper_or_authorization_fails(self) -> None:
        for path, replacement in (
            (("persistent_failure_diagnosis", "raw_vs_canonical_column_drift_tasks"), 10),
            (("authorization", "deepwidebench_forward_or_evaluator"), True),
        ):
            changed = copy.deepcopy(self.value)
            changed.pop("diagnosis_payload_sha256")
            cursor = changed
            for name in path[:-1]:
                cursor = cursor[name]
            cursor[path[-1]] = replacement
            changed["diagnosis_payload_sha256"] = target.contract.payload_sha256(
                changed
            )
            with self.subTest(path=path), self.assertRaises(ValueError):
                target.validate_diagnosis(changed)

    def test_source_has_no_external_or_runtime_privileged_capability(self) -> None:
        tree = ast.parse((ROOT / target.SOURCE).read_text(encoding="utf-8"))
        imports: list[str] = []
        privileged = {
            "category",
            "question_type",
            "task_category",
            "ground_truth",
            "answer_key",
            "reward",
        }
        hits: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
            elif isinstance(node, ast.Subscript) and isinstance(
                node.slice, ast.Constant
            ):
                if node.slice.value in privileged:
                    hits.append(str(node.slice.value))
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
