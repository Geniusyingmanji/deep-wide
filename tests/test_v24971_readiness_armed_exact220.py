from __future__ import annotations

import ast
import copy
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24857_pacing_aware_exact220_contract as parent  # noqa: E402
from deepwide_agent import v24970_same_process_search_readiness as readiness  # noqa: E402
from deepwide_agent import v24971_readiness_armed_exact220_contract as contract  # noqa: E402
from scripts import audit_v24635_exact220 as semantic_audit  # noqa: E402
from scripts import control_v24971_readiness_armed_exact220 as control  # noqa: E402
from scripts import finalize_v24971_readiness_armed_exact220 as finalizer  # noqa: E402
from scripts import run_v24800_exact220 as engine  # noqa: E402
from scripts import run_v24857_pacing_aware_exact220 as pacing  # noqa: E402
from scripts import run_v24857_pacing_aware_exact220_task as pacing_child  # noqa: E402
from scripts import run_v24971_readiness_armed_exact220 as runner  # noqa: E402
from scripts import run_v24971_readiness_armed_exact220_task as child  # noqa: E402


def readiness_receipt(*, passed: bool = True) -> dict:
    aggregate = {name: 0 for name in readiness._DIRECT_COUNTERS + readiness._RATE_COUNTERS}
    aggregate.update(
        {
            "tested_key_count": 12,
            "healthy_key_count": 12 if passed else 11,
            "unhealthy_key_count": 0 if passed else 1,
            "provider_attempts": 12,
            "slot_acquisitions": 12,
            "provider_start_reservations": 12,
            "successful_queries": 12 if passed else 11,
            "failed_queries": 0 if passed else 1,
            "status_2xx": 12 if passed else 11,
            "status_432": 0 if passed else 1,
            "projected_url_leads": 12 if passed else 11,
            "key_local_disables": 0 if passed else 1,
        }
    )
    value = {
        "artifact_version": 1,
        "role": readiness.ROLE,
        "policy_id": readiness.POLICY_ID,
        "session_nonce": "0123456789abcdef",
        "created_at_unix": 100,
        "wall_seconds": 1.0,
        "aggregate": aggregate,
        "passed": passed,
        "same_process_same_memory_pool_handoff_required": True,
        "credential_values_or_hashes_persisted_emitted_or_logged": False,
        "per_key_rows_persisted": False,
        "query_url_title_snippet_page_answer_or_provider_payload_persisted": False,
        "benchmark_manifest_question_prediction_mapping_gold_category_split_evaluator_score_reward_read": False,
        "model_fetch_evaluator_or_benchmark_forward_effect": False,
        "benchmark_forward_authorized_by_receipt_alone": False,
    }
    value["receipt_payload_sha256"] = contract.payload_sha256(value)
    return readiness.validate_receipt(value)


class V24971ReadinessArmedExact220Tests(unittest.TestCase):
    def test_algorithm_budget_capacity_and_policies_equal_parent(self) -> None:
        self.assertEqual(contract.LIMITS, parent.LIMITS)
        self.assertEqual(contract.MODEL, parent.MODEL)
        self.assertEqual(contract.SEARCH, parent.SEARCH)
        self.assertEqual(contract.TWO_WAVE_POLICY, parent.TWO_WAVE_POLICY)
        self.assertEqual(contract.rate_policy(), parent.rate_policy())
        self.assertEqual(contract.pacing_policy(), parent.pacing_policy())
        self.assertEqual(
            (
                contract.SELECTED_COUNT,
                contract.EXECUTOR_CONCURRENCY,
                contract.MODEL_SLOT_CAP,
                contract.TAVILY_KEY_SLOT_CAP,
            ),
            (220, 20, 8, 12),
        )

    def test_only_readiness_handoff_changes_frozen_algorithm(self) -> None:
        value = contract._algorithm_equality()
        self.assertTrue(all(value.values()))
        policy = contract.readiness_policy()
        self.assertTrue(policy["same_process_same_memory_pool_handoff"])
        self.assertFalse(policy["receipt_alone_authorizes_benchmark_forward"])
        self.assertTrue(policy["all_keys_require_2xx_and_nonempty_url_lead"])

    def test_task_vector_is_exact220_and_label_blind(self) -> None:
        tasks = contract.task_vector(ROOT)
        self.assertEqual(len(tasks), 220)
        self.assertEqual(len({item["opaque_id"] for item in tasks}), 220)
        self.assertTrue(all(set(item) == {"opaque_id", "question"} for item in tasks))

    def test_all_four_watchers_are_protected(self) -> None:
        self.assertEqual(
            [item["pid"] for item in contract.protected_watcher_snapshot()],
            [795336, 3061652, 2808901, 2889939],
        )

    def test_process_start_ticks_and_identity(self) -> None:
        ticks = contract.proc_start_ticks(os.getpid())
        self.assertGreater(ticks, 0)
        self.assertTrue(contract.process_matches(os.getpid(), ticks))
        self.assertFalse(contract.process_matches(os.getpid(), ticks + 1))

    def test_process_parser_handles_spaces_in_comm(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            proc = Path(raw)
            target = proc / "41"
            target.mkdir()
            fields = ["S"] + ["0"] * 18 + ["12345"] + ["0"] * 4
            (target / "stat").write_text(
                "41 (name with spaces) " + " ".join(fields), encoding="utf-8"
            )
            self.assertEqual(contract.proc_start_ticks(41, proc), 12345)

    def test_failed_readiness_cannot_build_armed_receipt(self) -> None:
        with mock.patch.object(contract, "validate_protocol", return_value={}), mock.patch.object(
            contract, "validate_preaudit", return_value={}
        ), mock.patch.object(contract, "_read", return_value={}):
            with self.assertRaises(RuntimeError):
                contract.build_armed_receipt(
                    ROOT,
                    readiness_receipt(passed=False),
                    pid=os.getpid(),
                    start_ticks=contract.proc_start_ticks(os.getpid()),
                    arming_git_head="a" * 40,
                    now=100,
                )

    def test_failed_readiness_main_creates_no_armed_or_benchmark_surface(self) -> None:
        keys = tuple(f"synthetic-key-{index:02d}" for index in range(12))

        @contextmanager
        def lease(*_args, **_kwargs):
            yield {"pid": os.getpid()}

        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            local_root = Path(raw)
            (local_root / "outputs").mkdir()
            with mock.patch.object(runner, "ROOT", local_root), mock.patch.object(
                runner, "_read_credentials", return_value=keys
            ), mock.patch.object(
                runner, "_pre_arm_barrier", return_value=({}, "a" * 40)
            ), mock.patch.object(
                runner, "acquire_deepwide_api_lease", lease
            ), mock.patch.object(
                runner.readiness,
                "run_readiness",
                return_value=(readiness_receipt(passed=False), None),
            ), mock.patch.object(runner, "_publish_new") as publish, mock.patch(
                "sys.stdout", new=io.StringIO()
            ):
                runner.main()
            publish.assert_not_called()
            self.assertFalse((local_root / contract.OUTPUT_ROOT).exists())
            self.assertFalse((local_root / contract.ARMED_RECEIPT).exists())

    def test_armed_receipt_requires_same_live_process(self) -> None:
        with mock.patch.object(contract, "validate_protocol", return_value={}), mock.patch.object(
            contract, "validate_preaudit", return_value={}
        ), mock.patch.object(contract, "_read", return_value={}):
            with self.assertRaises(RuntimeError):
                contract.build_armed_receipt(
                    ROOT,
                    readiness_receipt(),
                    pid=os.getpid() + 1,
                    start_ticks=1,
                    arming_git_head="a" * 40,
                    now=100,
                )

    def test_runner_reads_exact_credentials_and_never_logs_them(self) -> None:
        keys = tuple(f"synthetic-key-{index:02d}" for index in range(12))
        self.assertEqual(runner._read_credentials(io.StringIO("\n".join(keys))), keys)
        with self.assertRaises(RuntimeError):
            runner._read_credentials(io.StringIO("\n".join(keys[:11])))
        source = (ROOT / contract.RUNNER).read_text(encoding="utf-8")
        self.assertNotIn("print(credentials", source)
        self.assertNotIn("hash(credentials", source)

    def test_runner_rebinds_frozen_forward_without_second_stdin_read(self) -> None:
        keys = tuple(f"synthetic-key-{index:02d}" for index in range(12))
        capability = mock.Mock()
        capability.consume.return_value = keys
        receipt = readiness_receipt()
        original = (
            pacing.contract,
            engine._read_credentials,
            engine.validate_execution_start,
            engine.acquire_deepwide_api_lease,
        )
        try:
            with mock.patch.object(pacing, "configure"):
                runner._configure_forward((), receipt, capability, {"pid": os.getpid()})
            self.assertIs(pacing.contract, contract)
            self.assertEqual(engine._read_credentials(None), keys)
            self.assertEqual(engine._read_credentials(None), keys)
            capability.consume.assert_called_once_with(receipt)
        finally:
            (
                pacing.contract,
                engine._read_credentials,
                engine.validate_execution_start,
                engine.acquire_deepwide_api_lease,
            ) = original

    def test_child_rebinds_fresh_namespace(self) -> None:
        original = pacing_child.contract
        try:
            child.configure()
            self.assertIs(pacing_child.contract, contract)
        finally:
            pacing_child.contract = original

    def test_control_audits_all_runtime_sources_and_tests(self) -> None:
        self.assertEqual(control.EXPECTED_TESTS, 122)
        self.assertIn(contract.READINESS_SOURCE, control.RUNTIME_SOURCES)
        self.assertEqual(control._runtime_findings(), ([], [], []))

    def test_runtime_sources_have_no_privileged_or_evaluator_capability(self) -> None:
        for relative in control.RUNTIME_SOURCES:
            path = ROOT / relative
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source)
            imports: list[str] = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom):
                    imports.append(node.module or "")
            self.assertFalse(any("evaluator" in name or "finalize" in name for name in imports))
            self.assertEqual(semantic_audit._accesses(path, ROOT), [])

    def test_execution_start_check_set_is_fail_closed(self) -> None:
        expected = {
            "armed_receipt_commit_pushed",
            "arming_git_head_is_ancestor_of_armed_commit",
            "authorization_deadline_open",
            "conflicting_process_pids_empty_except_bound_runner",
            "execution_surface_pristine",
            "gpt56_endpoint_reachable_without_provider_request",
            "protected_watchers_unchanged",
            "runner_command_marker_matches",
            "runner_pid_start_ticks_live",
            "shared_api_lease_held_by_bound_runner",
        }
        self.assertEqual(contract.START_CHECK_KEYS, expected)

    def test_execution_start_artifact_cannot_be_consumed_by_other_process(self) -> None:
        runner_pid = os.getpid() + 1000
        armed = {
            "created_at_unix": 100,
            "authorization_deadline_unix": 200,
            "armed_receipt_payload_sha256": "a" * 64,
            "readiness_receipt_payload_sha256": "b" * 64,
            "readiness": {"session_nonce": "0123456789abcdef"},
            "runner": {
                "pid": runner_pid,
                "start_ticks": 123,
                "marker": contract.RUNNER_MARKER,
            },
        }
        start = {
            "role": "v24971_readiness_armed_exact220_execution_start",
            "protocol_id": contract.PROTOCOL_ID,
            "status": "authorized_not_started",
            "protocol_sha256": "1" * 64,
            "preactivation_audit_sha256": "2" * 64,
            "armed_receipt_sha256": "3" * 64,
            "armed_receipt_payload_sha256": "a" * 64,
            "readiness_receipt_payload_sha256": "b" * 64,
            "dependency_manifest_sha256": "d" * 64,
            "runner": armed["runner"],
            "session_nonce": "0123456789abcdef",
            "authorization_parent_git_head": "f" * 40,
            "created_at_unix": 120,
            "selected": 220,
            "executor_concurrency": 20,
            "model_slot_cap": 8,
            "tavily_key_slot_cap": 12,
            "protected_watchers": [],
            "findings": [],
            "checks": {name: True for name in contract.START_CHECK_KEYS},
            "first_benchmark_model_search_fetch_effect_started": False,
            "credential_value_or_hash_persisted_emitted_or_logged": False,
            "authorization": contract.START_AUTHORIZATION,
            "execution_start_payload_sha256": "seal",
        }
        reads = {
            contract.ARMED_RECEIPT: armed,
            contract.EXECUTION_START: start,
        }
        with mock.patch.object(
            contract,
            "validate_protocol",
            return_value={
                "dependency_manifest_sha256": "d" * 64,
                "execution": {"protected_watchers": []},
            },
        ), mock.patch.object(
            contract, "validate_armed_receipt", return_value=armed
        ), mock.patch.object(
            contract, "_read", side_effect=lambda path: reads[path.relative_to(ROOT)]
        ), mock.patch.object(
            contract,
            "sha256",
            side_effect=lambda path: {
                contract.PROTOCOL: "1" * 64,
                contract.PREAUDIT: "2" * 64,
                contract.ARMED_RECEIPT: "3" * 64,
            }[path.relative_to(ROOT)],
        ), mock.patch.object(contract, "_sealed", return_value=True), mock.patch.object(
            contract, "process_matches", return_value=True
        ):
            with self.assertRaises(RuntimeError):
                contract.validate_execution_start(ROOT, {}, now=130)
            self.assertIs(
                contract.validate_execution_start(
                    ROOT, {}, now=130, require_current_runner=False
                ),
                start,
            )

    def test_await_start_requires_both_artifacts_in_pushed_head(self) -> None:
        protocol = {"execution": {"protected_watchers": []}}
        armed = {"authorization_deadline_unix": 200}
        start = {"authorization_parent_git_head": "b" * 40}
        with mock.patch.object(runner.time, "time", return_value=100), mock.patch.object(
            runner.Path, "is_file", return_value=True
        ), mock.patch.object(runner.Path, "is_symlink", return_value=False), mock.patch.object(
            runner, "_clean_pushed", return_value="c" * 40
        ), mock.patch.object(
            contract, "validate_execution_start", return_value=start
        ), mock.patch.object(
            runner, "_ancestor", return_value=True
        ), mock.patch.object(
            runner, "_head_contains_local", side_effect=[True, True]
        ):
            self.assertIs(runner._await_execution_start(protocol, armed), start)

    def test_start_validation_rejects_expired_capability(self) -> None:
        source = (ROOT / contract.SOURCE).read_text(encoding="utf-8")
        self.assertIn("observed_now > armed.get(\"authorization_deadline_unix\"", source)
        self.assertIn("require_current_runner", source)

    def test_finalizer_uses_fresh_complete_evaluator_surface(self) -> None:
        engine_finalizer = finalizer.parent.base
        names = (
            "contract", "FORWARD_AUDIT", "EVALUATOR_PROTOCOL", "FINAL_RESULT",
            "POSTAUDIT", "EVALUATOR_ROOT", "PREPARE_ATTESTATION",
            "JOINED_OUTCOMES", "OFFICIAL_PREDICTIONS", "EVALUATOR_RUNS",
            "EVALUATOR_LOGS", "MERGED_RESULTS", "MERGE_ATTESTATION", "SUMMARY",
            "EVALUATOR_OWNER", "EVALUATOR_PURPOSE", "CONTROL_FILES",
            "REFERENCES", "_forward_barrier",
        )
        saved = {name: getattr(engine_finalizer, name) for name in names}
        try:
            finalizer.configure()
            self.assertIn("v24971_readiness_armed", str(engine_finalizer.FINAL_RESULT))
            self.assertTrue(
                str(engine_finalizer.EVALUATOR_ROOT).startswith(str(contract.OUTPUT_ROOT))
            )
            self.assertIn(str(contract.READINESS_SOURCE), engine_finalizer.CONTROL_FILES)
            self.assertIn(str(contract.ARMED_RECEIPT), engine_finalizer.CONTROL_FILES)
            self.assertIn(str(contract.EXECUTION_START), engine_finalizer.CONTROL_FILES)
        finally:
            for name, value in saved.items():
                setattr(engine_finalizer, name, value)

    def test_create_only_publication_rejects_overwrite(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            path = Path(directory) / "stage.json"
            control.publish_new(path, {})
            with self.assertRaises(FileExistsError):
                control.publish_new(path, {})


if __name__ == "__main__":
    unittest.main()
