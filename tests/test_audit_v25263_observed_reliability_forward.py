from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25260_observed_reliability_external_contract as contract  # noqa: E402
from scripts import audit_v25263_observed_reliability_forward as target  # noqa: E402


class V25263ObservedReliabilityForwardAuditTests(unittest.TestCase):
    def test_expected_forward_commit_paths_are_exact(self) -> None:
        self.assertEqual(len(target.EXPECTED_FORWARD_COMMIT_PATHS), 21)
        self.assertIn(str(contract.ATTEMPT_CLAIM), target.EXPECTED_FORWARD_COMMIT_PATHS)
        self.assertIn(str(contract.FORWARD_RESULT), target.EXPECTED_FORWARD_COMMIT_PATHS)
        self.assertIn(str(contract.TASK_ROWS), target.EXPECTED_FORWARD_COMMIT_PATHS)

    def test_forward_commit_boundary_requires_exact_child_chain_paths_and_push(self) -> None:
        head, start_commit, start_base = "d" * 40, "c" * 40, "b" * 40

        def read(_relative: Path, *, tracked: bool = True) -> dict:
            del tracked
            return {"git_head": start_base}

        def git(_root: Path, *args: str) -> str:
            if args == ("rev-parse", "target/main"):
                return head
            if args == ("rev-parse", f"{head}^"):
                return start_commit
            if args[0] == "rev-list" and args[-1] == head:
                return f"{head} {start_commit}"
            if args[0] == "rev-list" and args[-1] == start_commit:
                return f"{start_commit} {start_base}"
            if args[0] == "diff-tree" and args[-1] == head:
                return "\n".join(target.EXPECTED_FORWARD_COMMIT_PATHS)
            if args[0] == "diff-tree" and args[-1] == start_commit:
                return str(contract.EXECUTION_START)
            raise AssertionError(args)

        with mock.patch.object(target, "_read", side_effect=read), mock.patch.object(
            contract, "git", side_effect=git
        ):
            self.assertTrue(target.forward_commit_boundary(head=head))

        def unpublished(_root: Path, *args: str) -> str:
            if args == ("rev-parse", "target/main"):
                return "e" * 40
            return git(_root, *args)

        with mock.patch.object(target, "_read", side_effect=read), mock.patch.object(
            contract, "git", side_effect=unpublished
        ):
            self.assertFalse(target.forward_commit_boundary(head=head))

    def test_recursive_key_scan_detects_forbidden_nested_content(self) -> None:
        self.assertEqual(target._recursive_keys({"safe": [{"url": "x"}]}), {"safe", "url"})

    def test_audit_schema_rejects_resealed_credit_decision_or_hidden_tamper(self) -> None:
        tasks = contract.task_vector(ROOT)
        rows = []
        for task in tasks:
            budget = target.runner.runtime.PhysicalEffectBudget()
            rows.append(target.runner._terminal_outer_failure(task, RuntimeError("x"), 1.0, budget, None, {}))
        aggregate = target.runner.aggregate_rows(rows, wall_seconds=1.0)
        decision = target.runner.reliability_decision(aggregate)
        value = contract.seal(
            {
                "artifact_version": 1,
                "role": "v25263_observed_reliability_forward_audit",
                "protocol_id": contract.PROTOCOL_ID,
                "created_at_unix": 1,
                "protocol_sha256": "a" * 64,
                "execution_start_sha256": "b" * 64,
                "attempt_claim_sha256": "c" * 64,
                "forward_result_sha256": "d" * 64,
                "task_rows_sha256": "e" * 64,
                "prediction_freeze_sha256": "f" * 64,
                "aggregate": aggregate,
                "reliability_decision": decision,
                "checks": {name: True for name in target.AUDIT_CHECK_NAMES},
                "findings": [],
                "audit_valid": True,
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
                "evaluator_or_quality_metric_called": False,
                "entropy_or_information_gain_assigns_signed_credit": False,
                "authorization": {
                    "postforward_reliability_diagnosis": True,
                    "candidate_activation_or_prediction_change": False,
                    "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
                    "retry_resume_skip_replacement_or_selective_rerun": False,
                },
            },
            "audit_payload_sha256",
        )
        self.assertEqual(target.validate_audit(value), value)
        for kind in ("credit", "decision", "hidden"):
            changed = copy.deepcopy(value)
            if kind == "credit":
                changed["entropy_or_information_gain_assigns_signed_credit"] = True
            elif kind == "decision":
                changed["reliability_decision"]["reliability_gate_passed"] = True
            else:
                changed["checks"]["hidden"] = True
            changed.pop("audit_payload_sha256")
            changed["audit_payload_sha256"] = contract.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_audit(changed)

    def test_auditor_source_has_no_evaluator_import_or_score_computation(self) -> None:
        source = (ROOT / target.SOURCE).read_text(encoding="utf-8")
        self.assertNotIn("official_eval", source)
        self.assertNotIn("evaluate_", source)
        self.assertNotIn("from evaluation", source)
        self.assertNotIn("import evaluation", source)


if __name__ == "__main__":
    unittest.main()
