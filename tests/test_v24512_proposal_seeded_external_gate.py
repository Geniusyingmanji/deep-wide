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
from scripts import v24512_proposal_seeded_external_gate as target  # noqa: E402


def reseal(value: dict, field: str) -> None:
    value.pop(field, None)
    value[field] = payload_sha256(value)


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _cli_validator_smoke(command: str) -> int:
    protocol = target.build_protocol(now=0, require_pristine=False)
    base = target.predecessor.base

    def validate_in_process(args: argparse.Namespace) -> None:
        validated = base.validate_protocol(ROOT, value=protocol)
        binding = validated.get("record_bound_binding", {})
        if (
            validated.get("protocol_id") != target.PROTOCOL_ID
            or binding != target._record_bound_binding()
            or base.RUNNER_MARKER != target.RUNNER_MARKER
            or base.run_targeted_worker
            is not target.run_proposal_seeded_record_bound_worker
        ):
            raise RuntimeError("V2.45.12 CLI validator context is incomplete")
        print(
            json.dumps(
                {
                    "command": args.command,
                    "protocol_id": validated["protocol_id"],
                    "validator_context_passed": True,
                    "network_model_search_fetch_or_evaluator_called": False,
                },
                sort_keys=True,
            )
        )

    original_worker = base._worker
    original_supervisor = base._supervisor
    original_argv = sys.argv
    try:
        base._worker = validate_in_process
        base._supervisor = validate_in_process
        sys.argv = [str(ROOT / target.RUNNER_MARKER), command]
        target.main()
    finally:
        sys.argv = original_argv
        base._worker = original_worker
        base._supervisor = original_supervisor
    return 0


class V24512ProposalSeededExternalGateTests(unittest.TestCase):
    def test_population_is_fresh_against_332_questions_and_2656_entities(self) -> None:
        self.assertTrue(target._fresh_entity_vector_valid())
        self.assertEqual(len(target._prior_questions()), 332)
        self.assertEqual(len(target.QUESTIONS), 8)
        self.assertEqual(sum(map(len, target.ENTITY_GROUPS)), 64)

    def test_v24506_is_closed_and_never_rerun(self) -> None:
        self.assertTrue(target._previous_closed())
        binding = target._record_bound_binding()
        self.assertFalse(binding["v24506_population_rerun"])
        self.assertEqual(binding["prior_external_question_count"], 332)
        self.assertEqual(binding["prior_external_entity_count"], 2656)
        self.assertFalse(binding["new_population_reuses_prior_question_or_entity"])

    def test_protocol_binds_proposal_seeded_worker_without_relaxing_gates(self) -> None:
        value = target.build_protocol(now=0, require_pristine=False)
        binding = value["record_bound_binding"]
        self.assertEqual(
            binding["proposal_seeded_planner_policy"],
            target.PLANNER_POLICY_ID,
        )
        self.assertEqual(
            binding["proposal_seeded_worker_policy"], target.WORKER_POLICY_ID
        )
        self.assertTrue(binding["proposal_seed_is_query_only"])
        self.assertFalse(binding["proposal_votes_promoted_to_active_credit"])
        self.assertFalse(
            binding[
                "source_count_posterior_margin_and_credit_thresholds_relaxed"
            ]
        )
        self.assertEqual(value["gates"], target.predecessor.GATES)
        self.assertFalse(value["authorization"]["external_probe_launch"])
        self.assertFalse(value["authorization"]["paired_dev64_or_exact220"])

    def test_protocol_contains_no_task_content_and_runtime_contract_is_neutral(self) -> None:
        value = target.build_protocol(now=0, require_pristine=False)
        encoded = json.dumps(value, ensure_ascii=False)
        with target.configured_predecessor():
            for ordinal in range(1, 9):
                task = target.predecessor.base.neutral_task(ordinal)
                self.assertEqual(set(task), {"opaque_id", "question"})
                self.assertNotIn(task["opaque_id"], encoded)
                self.assertNotIn(task["question"], encoded)

    def test_resealed_binding_tamper_fails_closed(self) -> None:
        value = target.build_protocol(now=0, require_pristine=False)
        cases = (
            lambda item: item["record_bound_binding"].__setitem__(
                "v24506_population_rerun", True
            ),
            lambda item: item["record_bound_binding"].__setitem__(
                "proposal_seed_is_query_only", False
            ),
            lambda item: item["record_bound_binding"].__setitem__(
                "proposal_votes_promoted_to_active_credit", True
            ),
            lambda item: item["record_bound_binding"].__setitem__(
                "source_count_posterior_margin_and_credit_thresholds_relaxed",
                True,
            ),
        )
        for alter in cases:
            changed = copy.deepcopy(value)
            alter(changed)
            reseal(changed, "protocol_payload_sha256")
            with self.assertRaises(RuntimeError):
                target.validate_protocol(value=changed)

    def test_configured_predecessor_restores_all_bindings(self) -> None:
        missing = object()
        names = (
            "PROTOCOL_ID",
            "PROTOCOL",
            "PARENT",
            "RUNNER_MARKER",
            "_patched_core",
            "validate_protocol",
            "validate_preaudit",
            "validate_activation",
            "validate_execution_start",
        )
        originals = {
            name: getattr(target.predecessor, name, missing) for name in names
        }
        with target.configured_predecessor(validators=True):
            self.assertEqual(target.predecessor.PROTOCOL_ID, target.PROTOCOL_ID)
            self.assertIs(
                target.predecessor.validate_protocol,
                target.validate_protocol,
            )
            with target.predecessor.configured_base():
                self.assertIs(
                    target.predecessor.base.run_targeted_worker,
                    target.run_proposal_seeded_record_bound_worker,
                )
        for name, value in originals.items():
            if value is missing:
                self.assertFalse(hasattr(target.predecessor, name))
            else:
                self.assertIs(getattr(target.predecessor, name), value)

    def test_frozen_protocol_builds_preaudit_activation_and_start(self) -> None:
        base = target.predecessor.base
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            root = Path(temporary).relative_to(ROOT)
            paths = {
                "PROTOCOL": root / "protocol.json",
                "PREAUDIT": root / "preaudit.json",
                "ACTIVATION": root / "activation.json",
                "EXECUTION_START": root / "start.json",
                "RESULT": root / "result.json",
                "DECISION": root / "decision.json",
                "POSTAUDIT": root / "postaudit.json",
            }
            with ExitStack() as stack:
                for name, value in paths.items():
                    stack.enter_context(patch.object(target, name, value))
                protocol = target.build_protocol(now=0, require_pristine=False)
                _write_json(ROOT / paths["PROTOCOL"], protocol)
                tests = {
                    "suites": [
                        {"path": path, "test_count": count, "passed": True}
                        for path, count, _timeout in target.TEST_SUITES
                    ],
                    "test_count": target.EXPECTED_TEST_COUNT,
                    "passed": True,
                    "network_model_search_fetch_or_evaluator_called": False,
                }
                stack.enter_context(
                    patch.object(base, "_run_tests", return_value=tests)
                )
                stack.enter_context(
                    patch.object(base, "_all_sources_tracked", return_value=True)
                )
                stack.enter_context(
                    patch.object(base, "_port_listening", return_value=True)
                )
                stack.enter_context(
                    patch.object(
                        base, "lease_observation", return_value={"active": False}
                    )
                )
                stack.enter_context(
                    patch.object(base, "_future", return_value=True)
                )
                stack.enter_context(
                    patch.object(
                        base,
                        "_git",
                        side_effect=lambda _root, *args: ""
                        if args == ("status", "--porcelain")
                        else "a" * 40,
                    )
                )
                preaudit = target.build_preaudit(now=0)
                _write_json(ROOT / paths["PREAUDIT"], preaudit)
                validated_preaudit = target.validate_preaudit(value=preaudit)
                activation = target.build_activation(now=0)
                _write_json(ROOT / paths["ACTIVATION"], activation)
                validated_activation = target.validate_activation()
                start = target.build_execution_start(now=0)
                _write_json(ROOT / paths["EXECUTION_START"], start)
                validated_start = target.validate_execution_start()
        self.assertTrue(validated_preaudit["audit_valid"])
        self.assertTrue(validated_preaudit["launch_authorized"])
        self.assertEqual(
            validated_preaudit["checks"]["focused_tests"]["test_count"], 32
        )
        self.assertTrue(validated_activation["launch_authorized"])
        self.assertTrue(validated_start["execution_authorized"])
        self.assertFalse(validated_start["benchmark_or_evaluator_authorized"])

    def test_worker_and_supervisor_cli_bind_proposal_seeded_worker(self) -> None:
        for command in ("worker", "supervisor"):
            completed = subprocess.run(
                [
                    str(ROOT / ".venv-eval/bin/python"),
                    "-I",
                    "-B",
                    str(Path(__file__).resolve()),
                    "--cli-validator-smoke",
                    command,
                ],
                cwd=ROOT,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            receipt = json.loads(completed.stdout.strip())
            self.assertEqual(receipt["protocol_id"], target.PROTOCOL_ID)
            self.assertTrue(receipt["validator_context_passed"])
            self.assertFalse(
                receipt["network_model_search_fetch_or_evaluator_called"]
            )

    def test_runtime_source_is_label_blind(self) -> None:
        from scripts import audit_v24398_failure_observability_build as audit

        accesses, imports = audit._ast_findings(
            Path("scripts/v24512_proposal_seeded_external_gate.py")
        )
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--cli-validator-smoke":
        raise SystemExit(_cli_validator_smoke(sys.argv[2]))
    unittest.main()
