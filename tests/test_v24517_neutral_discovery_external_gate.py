from __future__ import annotations

import argparse
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24320_forward_contract import payload_sha256  # noqa: E402
from scripts import v24517_neutral_discovery_external_gate as target  # noqa: E402


def reseal(value: dict, field: str) -> None:
    value.pop(field, None)
    value[field] = payload_sha256(value)


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def _cli_validator_smoke(command: str) -> int:
    protocol = target.build_protocol(now=0, require_pristine=False)
    base = target.predecessor.predecessor.predecessor.base

    def validate_in_process(args: argparse.Namespace) -> None:
        validated = target.validate_protocol(value=protocol)
        if (
            validated["protocol_id"] != target.PROTOCOL_ID
            or validated["record_bound_binding"] != target._record_bound_binding()
            or base.RUNNER_MARKER != target.RUNNER_MARKER
            or base.run_targeted_worker
            is not target.run_neutral_discovery_record_bound_worker
        ):
            raise RuntimeError("V2.45.17 CLI validator context is incomplete")
        print(json.dumps({"command": args.command, "protocol_id": validated["protocol_id"], "validator_context_passed": True, "network_model_search_fetch_or_evaluator_called": False}, sort_keys=True))

    original_worker, original_supervisor, original_argv = base._worker, base._supervisor, sys.argv
    try:
        base._worker = validate_in_process
        base._supervisor = validate_in_process
        sys.argv = [str(ROOT / target.RUNNER_MARKER), command]
        target.main()
    finally:
        sys.argv = original_argv
        base._worker, base._supervisor = original_worker, original_supervisor
    return 0


class V24517NeutralDiscoveryExternalGateTests(unittest.TestCase):
    def test_population_is_fresh_against_348_questions_and_2784_entities(self) -> None:
        self.assertTrue(target._fresh_entity_vector_valid())
        self.assertEqual(len(target._prior_questions()), 348)
        self.assertEqual(len(target.QUESTIONS), 8)
        self.assertEqual(sum(map(len, target.ENTITY_GROUPS)), 64)

    def test_v24514_is_closed_and_never_rerun(self) -> None:
        self.assertTrue(target._previous_closed())
        binding = target._record_bound_binding()
        self.assertFalse(binding["v24514_population_rerun"])
        self.assertEqual(binding["prior_external_question_count"], 348)
        self.assertEqual(binding["prior_external_entity_count"], 2784)
        self.assertFalse(binding["new_population_reuses_prior_question_or_entity"])

    def test_parent_freeze_is_valid_and_design_only(self) -> None:
        value = target._parent(ROOT)
        self.assertTrue(value["audit_valid"])
        self.assertTrue(value["label_blind_audit"]["passed"])
        self.assertTrue(value["authorization"]["fresh_disjoint_neutral_discovery_external_protocol_design"])
        self.assertFalse(value["authorization"]["fresh_external_activation_or_launch"])

    def test_protocol_binds_neutral_worker_and_terminal_gates(self) -> None:
        value = target.build_protocol(now=0, require_pristine=False)
        binding = value["record_bound_binding"]
        self.assertEqual(binding["neutral_discovery_planner_policy"], target.PLANNER_POLICY_ID)
        self.assertEqual(binding["neutral_discovery_worker_policy"], target.WORKER_POLICY_ID)
        self.assertFalse(binding["neutral_discovery_query_contains_candidate_value"])
        self.assertFalse(binding["neutral_discovery_seed_receives_vote_or_source_credit"])
        self.assertTrue(binding["absolute_terminal_safe_change_and_decision_credit_required"])
        self.assertEqual(value["gates"], target.GATES)
        self.assertFalse(value["authorization"]["external_probe_launch"])
        self.assertFalse(value["authorization"]["paired_dev64_or_exact220"])

    def test_protocol_contains_no_task_content(self) -> None:
        value = target.build_protocol(now=0, require_pristine=False)
        encoded = json.dumps(value, ensure_ascii=False)
        with target.configured_predecessor(validators=True):
            with target.predecessor.configured_predecessor(validators=True):
                with target.predecessor.predecessor.configured_predecessor(validators=True):
                    for ordinal in range(1, 9):
                        task = target.predecessor.predecessor.predecessor.base.neutral_task(ordinal)
                        self.assertEqual(set(task), {"opaque_id", "question"})
                        self.assertNotIn(task["opaque_id"], encoded)
                        self.assertNotIn(task["question"], encoded)

    def test_resealed_binding_tamper_fails_closed(self) -> None:
        value = target.build_protocol(now=0, require_pristine=False)
        for alter in (
            lambda item: item["record_bound_binding"].__setitem__("v24514_population_rerun", True),
            lambda item: item["record_bound_binding"].__setitem__("neutral_discovery_query_contains_candidate_value", True),
            lambda item: item["record_bound_binding"].__setitem__("neutral_discovery_seed_receives_vote_or_source_credit", True),
        ):
            changed = copy.deepcopy(value); alter(changed); reseal(changed, "protocol_payload_sha256")
            with self.assertRaises(RuntimeError):
                target.validate_protocol(value=changed)

    def test_configured_predecessor_restores_worker_binding(self) -> None:
        base = target.predecessor.predecessor.predecessor.base
        original = base.run_targeted_worker
        with target.configured_predecessor(validators=True):
            with target.predecessor.configured_predecessor(validators=True):
                with target.predecessor.predecessor.configured_predecessor(validators=True):
                    with target.predecessor.predecessor.predecessor.configured_base():
                        self.assertIs(base.run_targeted_worker, target.run_neutral_discovery_record_bound_worker)
        self.assertIs(base.run_targeted_worker, original)

    def test_frozen_protocol_builds_preaudit_activation_and_start(self) -> None:
        base = target.predecessor.predecessor.predecessor.base
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            root = Path(temporary).relative_to(ROOT)
            paths = {name: root / f"{name.lower()}.json" for name in ("PROTOCOL", "PREAUDIT", "ACTIVATION", "EXECUTION_START", "RESULT", "DECISION", "POSTAUDIT")}
            with ExitStack() as stack:
                for name, path in paths.items(): stack.enter_context(patch.object(target, name, path))
                protocol = target.build_protocol(now=0, require_pristine=False); _write_json(ROOT / paths["PROTOCOL"], protocol)
                tests = {"suites": [{"path": path, "test_count": count, "passed": True} for path, count, _ in target.TEST_SUITES], "test_count": target.EXPECTED_TEST_COUNT, "passed": True, "network_model_search_fetch_or_evaluator_called": False}
                stack.enter_context(patch.object(base, "_run_tests", return_value=tests))
                stack.enter_context(patch.object(base, "_all_sources_tracked", return_value=True))
                stack.enter_context(patch.object(base, "_port_listening", return_value=True))
                stack.enter_context(patch.object(base, "lease_observation", return_value={"active": False}))
                stack.enter_context(patch.object(base, "_future", return_value=True))
                stack.enter_context(patch.object(base, "_git", side_effect=lambda _root, *args: "" if args == ("status", "--porcelain") else "a" * 40))
                preaudit = target.build_preaudit(now=0); _write_json(ROOT / paths["PREAUDIT"], preaudit)
                self.assertTrue(target.validate_preaudit(value=preaudit)["audit_valid"])
                activation = target.build_activation(now=0); _write_json(ROOT / paths["ACTIVATION"], activation)
                self.assertTrue(target.validate_activation()["launch_authorized"])
                start = target.build_execution_start(now=0); _write_json(ROOT / paths["EXECUTION_START"], start)
                self.assertTrue(target.validate_execution_start()["execution_authorized"])
        self.assertEqual(preaudit["checks"]["focused_tests"]["test_count"], 39)
        self.assertFalse(start["benchmark_or_evaluator_authorized"])

    def test_worker_and_supervisor_cli_bind_neutral_worker(self) -> None:
        for command in ("worker", "supervisor"):
            completed = subprocess.run([str(ROOT / ".venv-eval/bin/python"), "-I", "-B", str(Path(__file__).resolve()), "--cli-validator-smoke", command], cwd=ROOT, capture_output=True, text=True, timeout=30, check=False)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            receipt = json.loads(completed.stdout.strip())
            self.assertTrue(receipt["validator_context_passed"])
            self.assertFalse(receipt["network_model_search_fetch_or_evaluator_called"])

    def test_runtime_source_is_label_blind(self) -> None:
        from scripts import audit_v24398_failure_observability_build as audit
        accesses, imports = audit._ast_findings(Path("scripts/v24517_neutral_discovery_external_gate.py"))
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--cli-validator-smoke":
        raise SystemExit(_cli_validator_smoke(sys.argv[2]))
    unittest.main()
