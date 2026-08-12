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

from scripts import diagnose_v25176_v25175_normalizer_representation as target  # noqa: E402


class V25176NormalizerRepresentationDiagnosisTests(unittest.TestCase):
    def test_parent_gate_and_content_free_aggregate_are_bound(self) -> None:
        forward, audit = target._validate_parents()
        self.assertTrue(audit["audit_valid"])
        self.assertTrue(
            forward["mechanism_decision"]["normalizer_localization_gate_passed"]
        )
        self.assertTrue(
            forward["mechanism_decision"]["production_reliability_gate_passed"]
        )
        self.assertEqual(forward["aggregate"]["production_fallback_tasks"], 1)
        self.assertEqual(
            forward["aggregate"]["disposition_counts"][
                "malformed_row_or_escaped_pipe_reject"
            ],
            1,
        )

    def test_synthetic_representation_experiment_preserves_literal_values(self) -> None:
        value = target.representation_experiment()
        self.assertFalse(
            value["frozen_exact_parser_accepts_backslash_escaped_pipe"]
        )
        self.assertFalse(
            value["frozen_normalizer_accepts_backslash_escaped_pipe"]
        )
        self.assertFalse(
            value[
                "public_loader_semantics_preserve_backslash_escaped_pipe_shape"
            ]
        )
        self.assertTrue(
            value["internal_numeric_entity_is_frozen_parser_compatible"]
        )
        self.assertTrue(
            value["csv_quoted_pipe_is_public_loader_column_shape_compatible"]
        )
        self.assertTrue(
            value[
                "csv_quoted_pipe_preserves_nonwhitespace_literal_and_delimiter"
            ]
        )
        self.assertTrue(
            value["public_loader_strips_whitespace_adjacent_to_internal_pipe"]
        )
        self.assertFalse(value["csv_quoted_pipe_exactly_preserves_full_cell"])

    def test_diagnosis_is_conservative_and_build_only(self) -> None:
        value = target.build_diagnosis(now=1)
        checked = target.validate_diagnosis(value)
        diagnosis = checked["diagnosis"]
        self.assertTrue(
            diagnosis[
                "aggregate_cannot_distinguish_row_width_mismatch_from_backslash_escaped_pipe"
            ]
        )
        self.assertTrue(
            diagnosis["natural_reject_is_not_claimed_to_be_an_escaped_pipe"]
        )
        self.assertEqual(diagnosis["entropy_or_information_gain_signed_credit"], 0)
        self.assertEqual(
            checked["authorization"],
            {
                "quote_aware_literal_preserving_normalizer_build_only": True,
                "runtime_integration_or_external_protocol": False,
                "old_population_retry_resume_rerun_or_reuse": False,
                "binding_successor_design": False,
                "vertical_binding_policy_change": False,
                "evaluator_or_quality_result": False,
                "deepwidebench_dev64_exact220_leaderboard_or_sota": False,
            },
        )

    def test_resealed_overclaim_launch_credit_or_parent_tamper_fails(self) -> None:
        value = target.build_diagnosis(now=1)
        for kind in ("overclaim", "launch", "credit", "parent"):
            changed = copy.deepcopy(value)
            if kind == "overclaim":
                changed["diagnosis"][
                    "natural_reject_is_not_claimed_to_be_an_escaped_pipe"
                ] = False
            elif kind == "launch":
                changed["authorization"]["runtime_integration_or_external_protocol"] = True
            elif kind == "credit":
                changed["diagnosis"]["entropy_or_information_gain_signed_credit"] = 1
            else:
                changed["parents"]["forward_audit_sha256"] = "0" * 64
            changed.pop("diagnosis_payload_sha256")
            changed["diagnosis_payload_sha256"] = target.contract.payload_sha256(
                changed
            )
            with self.subTest(kind=kind), self.assertRaises(RuntimeError):
                target.validate_diagnosis(changed)

    def test_module_is_label_blind_and_never_opens_task_rows(self) -> None:
        path = ROOT / target.SOURCE
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
        self.assertEqual(privileged, set())
        self.assertNotIn("read_text(encoding=\"utf-8\").splitlines()", source)
        self.assertNotIn("run_official_eval_local", source)
        self.assertIsNone(target.contract.SECRET.search(source))


if __name__ == "__main__":
    unittest.main()
