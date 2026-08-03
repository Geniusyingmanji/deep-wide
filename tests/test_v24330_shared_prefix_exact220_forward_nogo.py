from __future__ import annotations

import ast
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import (  # noqa: E402
    audit_v24330_shared_prefix_exact220_forward_nogo as audit,
)
from scripts import (  # noqa: E402
    publish_v24330_shared_prefix_exact220_forward_nogo as target,
)


class V24330ForwardNoGoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.publication = target.build_publication(ROOT, now=1)

    def test_terminal_pair_and_prediction_freezes_are_exact220(self) -> None:
        state = self.publication["state"]
        self.assertEqual(state["projection"]["terminal_pair_tasks"], 220)
        self.assertEqual(
            state["projection"]["prediction_rows_per_arm"],
            {"baseline": 220, "candidate": 220},
        )
        for arm, freeze in self.publication["freezes"].items():
            self.assertEqual(freeze["arm"], arm)
            self.assertEqual(freeze["terminal"], 220)
            self.assertFalse(freeze["mapping_gold_or_evaluator_opened_or_hashed"])

    def test_accounting_distinguishes_complete_and_incomplete_tasks(self) -> None:
        accounting = self.publication["state"]["projection"]["effect_accounting"]
        self.assertEqual(accounting["complete_tasks"], 157)
        self.assertEqual(accounting["incomplete_tasks"], 63)
        complete = accounting["complete_task_totals"]
        self.assertEqual(complete["logical_model_admissions"], 449)
        self.assertEqual(complete["provider_model_requests"], 413)
        self.assertEqual(complete["pre_provider_model_rejections"], 36)
        self.assertEqual(complete["slot_acquisitions"], 413)
        self.assertEqual(complete["slot_timeouts"], 36)
        incomplete = accounting["incomplete_task_lower_bounds"]
        self.assertEqual(incomplete["slot_acquisitions"], 171)
        self.assertEqual(incomplete["slot_timeouts"], 11)
        self.assertTrue(accounting["complete_subset_conservation_verified"])
        self.assertTrue(
            accounting[
                "global_naive_conservation_is_invalid_for_incomplete_fallbacks"
            ]
        )

    def test_mechanism_did_not_activate_and_forward_gate_is_nogo(self) -> None:
        result = self.publication["result"]
        pair = result["pair"]
        self.assertEqual(pair["candidate_nonidentity_tasks"], 0)
        self.assertEqual(pair["admitted_cell_changes"], 0)
        self.assertEqual(pair["credited_conditional_entropy_reduction_nats"], 0)
        self.assertFalse(result["forward_gate"]["passed"])
        self.assertIn(
            "candidate_nonidentity_tasks",
            result["forward_gate"]["failed_checks"],
        )
        self.assertIn("effect_accounting_complete", result["forward_gate"]["failed_checks"])
        self.assertFalse(result["evaluation_authorized"])
        self.assertFalse(result["benchmark_score_available"])

    def test_deadline_and_slot_gates_preserve_observed_failures(self) -> None:
        result = self.publication["result"]
        pair = result["pair"]
        self.assertEqual(pair["slot_timeouts"], 47)
        self.assertEqual(pair["provider_deadline_failures"], 20)
        self.assertEqual(pair["hard_fetch_deadline_failures"], 23)
        self.assertEqual(pair["deadline_exhausted_tasks"], 53)
        for name in (
            "slot_timeouts",
            "provider_deadline_failures",
            "hard_fetch_deadline_failures",
            "deadline_exhausted_tasks",
        ):
            self.assertIn(name, result["forward_gate"]["failed_checks"])

    def test_publication_contains_no_task_or_prediction_content(self) -> None:
        encoded = json.dumps(
            {
                "diagnostic": self.publication["diagnostic"],
                "result": self.publication["result"],
            },
            ensure_ascii=False,
        )
        self.assertNotRegex(encoded, r"task_[0-9a-f]{24}")
        self.assertNotIn("| Result |", encoded)
        self.assertFalse(
            self.publication["result"]["source_policy"]
            ["task_question_query_url_page_prediction_or_credential_emitted"]
        )

    def test_recovery_source_has_no_remote_execution_calls(self) -> None:
        tree = ast.parse((ROOT / target.__file__).read_text(encoding="utf-8"))
        forbidden = {
            "execute_forward",
            "run_one_task",
            "run_all_evaluators",
            "evaluator_command",
            "acquire_deepwide_api_lease",
        }
        called = {
            node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        self.assertFalse(forbidden.intersection(called))

    def test_closure_audit_keeps_evaluator_closed(self) -> None:
        if not (ROOT / target.RESULT).is_file():
            self.skipTest("closure audit is built only after NO-GO publication")
        value = audit.build_audit(ROOT, now=1)
        self.assertTrue(value["audit_valid"])
        self.assertTrue(value["closure"]["evaluator_side_surface_absent"])
        self.assertFalse(value["authorization"]["same_run_evaluator"])


if __name__ == "__main__":
    unittest.main()
