from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import audit_v25277_third_disjoint_checkpoint_population as target  # noqa: E402


class V25277ThirdDisjointCheckpointPopulationAuditTests(unittest.TestCase):
    @staticmethod
    def _fake_tests() -> dict:
        return {
            "expected": target.EXPECTED_TESTS,
            "observed": target.EXPECTED_TESTS,
            "passed": True,
            "suites": [
                {
                    "pattern": pattern,
                    "expected": expected,
                    "observed": expected,
                    "returncode": 0,
                    "passed": True,
                    "output_sha256": "a" * 64,
                }
                for pattern, expected in target.TEST_SUITES
            ],
        }

    @staticmethod
    def _clean_git(*args: str) -> str:
        if args == ("rev-parse", "HEAD") or args == ("rev-parse", "target/main"):
            return target.EXPECTED_FREEZE_COMMIT
        if args == ("status", "--porcelain"):
            return ""
        if args == (
            "diff-tree",
            "--no-commit-id",
            "--name-only",
            "-r",
            target.EXPECTED_SELECTION_PARENT,
        ):
            return str(target.START)
        if args == (
            "diff-tree",
            "--no-commit-id",
            "--name-only",
            "-r",
            target.EXPECTED_FREEZE_COMMIT,
        ):
            return "\n".join(sorted((str(target.CLAIM), str(target.POPULATION))))
        if args == (
            "rev-parse",
            target.EXPECTED_SELECTION_PARENT + "^{commit}",
        ):
            return target.EXPECTED_SELECTION_PARENT
        if args == ("rev-parse", target.EXPECTED_SELECTION_PARENT + "^"):
            return target.EXPECTED_START_PARENT
        if args == ("rev-parse", target.EXPECTED_FREEZE_COMMIT + "^{commit}"):
            return target.EXPECTED_FREEZE_COMMIT
        if args == ("rev-parse", target.EXPECTED_FREEZE_COMMIT + "^"):
            return target.EXPECTED_SELECTION_PARENT
        raise AssertionError(args)

    def test_fixed_chain_start_claim_population_and_parent_validate(self) -> None:
        self.assertEqual(
            target._fixed_hashes(),
            {str(path): digest for path, digest in target.FIXED_HASHES.items()},
        )
        claim, population, start, parent = target._load()
        self.assertEqual(
            claim["selection_parent_commit"], target.EXPECTED_SELECTION_PARENT
        )
        self.assertEqual(
            population["selection_parent_commit"], target.EXPECTED_SELECTION_PARENT
        )
        self.assertEqual(target.validate_start(start), start)
        self.assertTrue(parent["audit_valid"])

    def test_git_chain_is_one_start_file_then_two_frozen_files(self) -> None:
        self.assertEqual(target._git_chain_exact(), (True, True))

    def test_population_is_exact20_by2_history_zero_and_prior384_disjoint(self) -> None:
        _claim, population, _start, _parent = target._load()
        tasks = target.freeze.validate_task_vector(
            population["population"]["task_vector"]
        )
        selected = {
            package
            for task in tasks
            for package in target.freeze._packages_from_question(task["question"])
        }
        self.assertEqual(len(tasks), 20)
        self.assertEqual(len(selected), 40)
        prior = target.freeze._prior_entities()
        self.assertEqual(len(prior), 384)
        self.assertFalse(selected.intersection(prior))
        self.assertEqual(
            population["history_receipt"]["history_zero_disjoint_selected_total"],
            40,
        )

    def test_build_audit_authorizes_protocol_design_only(self) -> None:
        with mock.patch.object(
            target.base, "_git", side_effect=self._clean_git
        ), mock.patch.object(target, "_tests", return_value=self._fake_tests()):
            value = target.build_audit(now=1, tracked=False)
        self.assertEqual(target.validate_audit(value), value)
        self.assertTrue(
            value["authorization"]["paired_checkpoint_reliability_protocol_design"]
        )
        self.assertFalse(
            value["authorization"]
            ["paired_checkpoint_reliability_external_activation_or_launch"]
        )
        self.assertFalse(
            value["authorization"]
            ["evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota"]
        )

    def test_resealed_nested_hidden_overlap_launch_or_credit_tamper_fails(self) -> None:
        with mock.patch.object(
            target.base, "_git", side_effect=self._clean_git
        ), mock.patch.object(target, "_tests", return_value=self._fake_tests()):
            value = target.build_audit(now=1, tracked=False)
        for kind in (
            "suite_hidden",
            "watcher_hidden",
            "receipt_hidden",
            "overlap",
            "launch",
            "credit",
            "check_hidden",
        ):
            changed = copy.deepcopy(value)
            if kind == "suite_hidden":
                changed["tests"]["suites"][0]["hidden"] = True
            elif kind == "watcher_hidden":
                changed["runtime_state"]["protected_watchers"][0]["hidden"] = True
            elif kind == "receipt_hidden":
                changed["selection_receipt"]["hidden"] = True
            elif kind == "overlap":
                changed["selection_receipt"]["selected_prior_overlap_count"] = 1
            elif kind == "launch":
                changed["authorization"][
                    "paired_checkpoint_reliability_external_activation_or_launch"
                ] = True
            elif kind == "credit":
                changed[
                    "entropy_or_information_gain_assigns_signed_credit"
                ] = True
            else:
                changed["checks"]["hidden"] = True
            changed.pop("audit_payload_sha256")
            changed["audit_payload_sha256"] = target.contract.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_audit(changed)

    def test_auditor_has_no_dpkg_history_network_model_or_evaluator_effect(self) -> None:
        source = (ROOT / target.SOURCE).read_text(encoding="utf-8")
        for forbidden in (
            "dpkg-query",
            "git log",
            "requests.",
            "urlopen(",
            "HardTotalWallResponsesClient(",
            "run_official_eval_local",
        ):
            self.assertNotIn(forbidden, source)
        self.assertNotIn("print(task", source)
        self.assertNotIn("print(package", source)


if __name__ == "__main__":
    unittest.main()
