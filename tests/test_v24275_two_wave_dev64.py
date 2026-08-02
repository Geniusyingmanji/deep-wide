from __future__ import annotations

import copy
import tempfile
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
import sys

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent import v24275_forward_contract as forward_contract  # noqa: E402
from deepwide_agent.v24275_hard_deadline_fetch import (  # noqa: E402
    HardDeadlineNativeSearchClient,
    validate_fetch_result,
)
from scripts import activate_v24275_two_wave_dev64 as activation_target  # noqa: E402
from scripts import audit_v24275_two_wave_dev64 as audit_target  # noqa: E402
from scripts import finalize_v24275_two_wave_dev64 as finalizer  # noqa: E402
from scripts import preregister_v24275_two_wave_dev64 as prereg  # noqa: E402
from scripts import run_v24275_two_wave_dev64 as runner  # noqa: E402
from scripts import run_v24275_two_wave_task as child  # noqa: E402
from scripts.run_v24257_score_first_smoke import payload_sha256  # noqa: E402


def visible(position: int) -> dict[str, str]:
    return {
        "opaque_id": f"task_{position:024x}",
        "question": "Return a table. Column names: Name, Value.",
    }


def fallback_row(position: int) -> dict:
    return runner._fallback_row(
        visible(position),
        kind="worker_failure_fallback",
        stage="test_executor",
        failure_type="SyntheticFailure",
        elapsed=0.1,
        progress={},
    )


def arm_metrics() -> dict:
    return {
        "runtime_completed": 64,
        "runtime_failed": 0,
        "evaluator_valid": 64,
        "evaluator_invalid_or_not_run": 0,
        "whole_table_successes": 5,
        "entity_acc": 0.73,
        "f1_by_row": 0.27,
        "f1_by_item": 0.43,
        "column_f1": 0.51,
        "quality_composite": 0.485,
        "score": 0.078125,
        "model_generated_tables": 63,
        "fallback_tables": 1,
        "search_total_tokens": 1_900_000,
        "task_wall_sum_seconds": 3_900.0,
    }


class V24275TwoWaveDev64Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.protocol = prereg.build_protocol(
            ROOT, now=1, require_pristine=False
        )
        cls.forward_protocol = prereg.build_forward_contract(cls.protocol)

    def test_selection_is_frozen_visible_only_allowlist(self) -> None:
        rows = forward_contract.visible_manifest_rows(ROOT)
        ids = forward_contract.selected_ids(self.forward_protocol)
        self.assertEqual(len(ids), 64)
        self.assertTrue(set(ids).issubset({row["opaque_id"] for row in rows}))
        self.assertEqual(
            self.forward_protocol["task_contract"]["runtime_boundary"],
            ["opaque_id", "question"],
        )
        self.assertFalse(
            self.forward_protocol["task_contract"][
                "mapping_split_category_gold_evaluator_or_score_used_for_selection"
            ]
        )

    def test_protocol_freezes_two_wave_gate_without_launching_full220(self) -> None:
        value = self.protocol
        self.assertEqual(value["forward_contract"]["executor_concurrency"], 8)
        self.assertEqual(value["model_slot_contract"]["slot_cap"], 8)
        self.assertEqual(value["limits"]["search_queries"], 4)
        self.assertEqual(value["limits"]["fetch_targets"], 10)
        self.assertEqual(value["two_wave_policy"]["wave1_queries"], 2)
        self.assertEqual(value["two_wave_policy"]["wave2_queries"], 2)
        self.assertEqual(value["decision_contract"]["maximum_search_token_ratio"], 0.70)
        self.assertEqual(value["decision_contract"]["maximum_task_wall_sum_ratio"], 0.50)
        self.assertTrue(value["parents"]["hard_deadline_capacity_gate"]["passed"])
        self.assertEqual(
            value["parents"]["hard_deadline_capacity_gate"]["concurrency"], 8
        )
        self.assertEqual(
            value["parents"]["revoked_v1_zero_call_freeze"]["status"],
            "revoked_before_activation",
        )
        self.assertTrue(
            value["source_policy"][
                "historical_per_task_control_prediction_freeze_runtime_summary_and_mapping_gold_evaluator_rows_open_only_after_candidate_exact64_freeze"
            ]
        )
        self.assertTrue(
            value["source_policy"][
                "historical_control_aggregate_result_and_evaluator_contract_read_as_preregistration_metadata"
            ]
        )
        self.assertFalse(value["authorization"]["new_exact220_launch"])
        self.assertFalse(
            value["authorization"]["leaderboard_submission_or_sota_claim"]
        )

    def test_preregistration_does_not_open_or_hash_per_task_control_files(self) -> None:
        parents = self.protocol["parents"]
        for name in (
            "frozen_control_prediction_freeze",
            "frozen_control_runtime",
            "frozen_control_summary",
        ):
            self.assertNotIn(name, parents)
        self.assertFalse(
            parents[
                "historical_control_prediction_freeze_runtime_summary_mapping_gold_or_evaluator_rows_opened_or_hashed"
            ]
        )

        opened: list[Path] = []
        hashed: list[Path] = []
        original_read = prereg.read_object
        original_sha = prereg.sha256

        def read(path):
            opened.append(Path(path).resolve())
            return original_read(path)

        def digest(path):
            hashed.append(Path(path).resolve())
            return original_sha(path)

        with mock.patch.object(prereg, "read_object", side_effect=read), mock.patch.object(
            prereg, "sha256", side_effect=digest
        ):
            prereg.build_protocol(ROOT, now=2, require_pristine=False)
        forbidden = {
            (ROOT / prereg.CONTROL_PREDICTION_FREEZE).resolve(),
            (ROOT / prereg.CONTROL_RUNTIME).resolve(),
            (ROOT / prereg.CONTROL_RUN_SUMMARY).resolve(),
        }
        self.assertTrue(forbidden.isdisjoint(opened))
        self.assertTrue(forbidden.isdisjoint(hashed))

    def test_source_policy_timing_tamper_fails_full_and_forward_contracts(self) -> None:
        altered = copy.deepcopy(self.protocol)
        altered["source_policy"][
            "historical_per_task_control_prediction_freeze_runtime_summary_and_mapping_gold_evaluator_rows_open_only_after_candidate_exact64_freeze"
        ] = False
        altered["decision_contract_sha256"] = payload_sha256(
            {key: value for key, value in altered.items() if key != "decision_contract_sha256"}
        )
        with mock.patch.object(
            prereg, "_ordinary", return_value=ROOT / "README.md"
        ), mock.patch.object(
            prereg, "read_object", return_value=altered
        ), self.assertRaisesRegex(RuntimeError, "identity"):
            prereg.validate_protocol(ROOT, prereg.OUTPUT)

        forward = copy.deepcopy(self.forward_protocol)
        forward["source_policy"][
            "historical_control_aggregate_result_and_evaluator_contract_read_as_preregistration_metadata"
        ] = False
        unsigned = dict(forward)
        unsigned.pop("forward_contract_payload_sha256")
        forward["forward_contract_payload_sha256"] = payload_sha256(unsigned)
        with mock.patch.object(
            forward_contract, "_ordinary", return_value=ROOT / "README.md"
        ), mock.patch.object(
            forward_contract, "read_object", return_value=forward
        ), self.assertRaisesRegex(RuntimeError, "identity"):
            forward_contract.validate_protocol(ROOT)

    def test_forward_eager_import_closure_is_frozen_and_capability_free(self) -> None:
        manifest = self.protocol["forward_surface"]["manifest"]
        modules = audit_target._module_manifest(manifest)
        unresolved: list[str] = []
        hits: list[str] = []
        accesses: list[str] = []
        for relative in manifest:
            path = ROOT / relative
            source = path.read_text(encoding="utf-8")
            accesses.extend(audit_target._accesses(path, ROOT))
            for marker in audit_target.FORWARD_CAPABILITY_MARKERS:
                if marker in source:
                    hits.append(f"{relative}:{marker}")
            for module in audit_target._eager_local_imports(path, relative):
                if module != "scripts" and module not in modules:
                    unresolved.append(f"{relative}:{module}")
        self.assertEqual(hits, [])
        self.assertEqual(unresolved, [])
        self.assertEqual(
            sorted(set(accesses) - {"src/deepwide_agent/clients.py:565:score"}),
            [],
        )

    def test_child_requires_every_frozen_provider_budget_and_policy_field(self) -> None:
        values = {
            "proxy_url": child.MODEL["proxy_url"],
            "model": child.MODEL["name"],
            "reasoning_effort": child.MODEL["reasoning_effort"],
            "service_tier": child.MODEL["service_tier"],
            "model_timeout": child.MODEL["timeout_seconds"],
            "model_max_retries": child.MODEL["max_retries"],
            "search_batch_size": child.SEARCH["batch_size"],
            "search_workers": child.SEARCH["workers"],
            "search_context_size": child.SEARCH["context_size"],
            "search_output_tokens": child.SEARCH["max_output_tokens"],
            "search_timeout": child.SEARCH["timeout_seconds"],
            "search_max_retries": child.SEARCH["max_retries"],
            "fetch_workers": child.SEARCH["fetch_workers"],
            "fetch_timeout": child.SEARCH["fetch_timeout_seconds"],
            "model_slot_pool_id": child.MODEL_SLOT_POOL_ID,
            "model_slot_cap": child.MODEL_SLOT_CAP,
            **child.LIMITS,
            **child.TWO_WAVE_POLICY,
        }
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            fake_root = Path(directory)
            slots = fake_root / child.MODEL_SLOT_DIRECTORY
            slots.mkdir(parents=True)
            args = SimpleNamespace(**values)
            with mock.patch.object(child, "ROOT", fake_root):
                child.validate_frozen_configuration(args, slots)
                for name in values:
                    altered = copy.copy(args)
                    current = getattr(altered, name)
                    if isinstance(current, str):
                        setattr(altered, name, current + "-drift")
                    elif isinstance(current, int):
                        setattr(altered, name, current + 1)
                    else:
                        setattr(altered, name, current + 0.125)
                    with self.assertRaisesRegex(RuntimeError, "surface"):
                        child.validate_frozen_configuration(altered, slots)

    def test_task_command_contains_complete_two_wave_policy(self) -> None:
        command = runner.task_command(
            ROOT,
            ROOT / "outputs/a/visible_task.json",
            ROOT / "outputs/a/result.json",
            ROOT / "outputs/a/safe_progress.json",
            ROOT / "outputs/a/model_slot_receipt.json",
            ROOT / "outputs/a/transport_health.json",
        )
        for name, value in runner.TWO_WAVE_POLICY.items():
            flag = "--" + name.replace("_", "-")
            self.assertIn(flag, command)
            self.assertEqual(command[command.index(flag) + 1], str(value))

    def test_runtime_row_rejects_resealed_hard_fetch_counter_mismatch(self) -> None:
        row = fallback_row(1)
        row["telemetry"]["retrieval_completed"] = 1
        row["telemetry"]["retrieval_failed"] = 0
        row["telemetry"]["hard_fetch_helper_calls"] = 1
        with self.assertRaisesRegex(ValueError, "hard-fetch"):
            runner.validate_runtime_row(row)

    def test_hard_fetch_helper_keeps_url_off_argv_and_validates_output(self) -> None:
        calls: list[tuple[list[str], dict]] = []

        class Process:
            pid = 123456789
            returncode = 0

            def communicate(self, value, timeout=None):
                self.input = value
                self.timeout = timeout
                return (
                    '{"status":"ok","url":"https://example.com/final",'
                    '"title":"Title","text":"page body","links":[]}',
                    None,
                )

        process = Process()

        def popen(command, **kwargs):
            calls.append((list(command), dict(kwargs)))
            return process

        client = HardDeadlineNativeSearchClient(
            "http://unused/responses",
            "model",
            fetch_pages=False,
            max_workers=1,
            hard_fetch_deadline_seconds=25,
            popen=popen,
        )
        source = "https://example.com/private-path"
        result = client._fetch_url(source)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(client.fetch_calls, 1)
        self.assertEqual(client.fetch_failures, 0)
        self.assertNotIn(source, "\n".join(calls[0][0]))
        self.assertIn(source, process.input)
        self.assertEqual(process.timeout, 25)
        self.assertTrue(calls[0][1]["start_new_session"])

    def test_hard_fetch_timeout_is_one_total_deadline_and_counts_failure(self) -> None:
        class Process:
            pid = 123456789
            returncode = None

            def communicate(self, value, timeout=None):
                raise __import__("subprocess").TimeoutExpired("helper", timeout)

            def wait(self, timeout=None):
                self.returncode = -15
                return self.returncode

        client = HardDeadlineNativeSearchClient(
            "http://unused/responses",
            "model",
            fetch_pages=False,
            max_workers=1,
            hard_fetch_deadline_seconds=25,
            popen=lambda *args, **kwargs: Process(),
        )
        with mock.patch("os.killpg") as killpg:
            result = client._fetch_url("https://example.com/slow")
        self.assertEqual(result["status"], "hard_deadline_exceeded")
        self.assertEqual(client.fetch_calls, 1)
        self.assertEqual(client.fetch_failures, 1)
        killpg.assert_called_once()

    def test_hard_fetch_result_rejects_oversize_or_extra_fields(self) -> None:
        with self.assertRaisesRegex(ValueError, "schema"):
            validate_fetch_result(
                {
                    "status": "ok",
                    "url": "https://example.com",
                    "title": "Title",
                    "text": "x" * 5001,
                    "links": [],
                }
            )
        with self.assertRaisesRegex(ValueError, "schema"):
            validate_fetch_result(
                {
                    "status": "ok",
                    "url": "https://example.com",
                    "title": "Title",
                    "text": "body",
                    "links": [],
                    "prediction": "forbidden",
                }
            )

    def test_scheduler_runs_exact64_once_with_eight_workers(self) -> None:
        tasks = [visible(position) for position in range(1, 65)]
        active = 0
        maximum = 0
        seen: list[str] = []
        lock = threading.Lock()
        progress: list[dict] = []

        def fake(_root, _protocol, task, _task_root):
            nonlocal active, maximum
            with lock:
                active += 1
                maximum = max(maximum, active)
                seen.append(task["opaque_id"])
            time.sleep(0.003)
            with lock:
                active -= 1
            return runner.TaskOutcome(
                fallback_row(int(task["opaque_id"][5:], 16)), True, True, 0
            )

        outcomes = runner.execute_forward(
            ROOT,
            self.forward_protocol,
            tasks,
            runner=fake,
            progress_writer=progress.append,
        )
        self.assertEqual(len(outcomes), 64)
        self.assertEqual(maximum, 8)
        self.assertEqual(len(seen), len(set(seen)))
        self.assertEqual(progress[-1]["completed_predictions"], 64)

    def test_scheduler_rejects_non64_input(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "task count"):
            runner.execute_forward(
                ROOT, self.forward_protocol, [visible(1)], runner=lambda *_: None
            )

    def test_worker_nonzero_becomes_total_fallback_with_retrieval_failure(self) -> None:
        class Process:
            returncode = 1

            def wait(self, timeout=None):
                return 1

        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            task_root = Path(directory) / "task_0001"
            outcome = runner.run_one_task(
                ROOT,
                self.forward_protocol,
                visible(1),
                task_root,
                popen=lambda *args, **kwargs: Process(),
            )
        self.assertEqual(outcome.row["status"], "completed")
        self.assertEqual(outcome.row["completion_kind"], "worker_failure_fallback")
        self.assertEqual(outcome.row["telemetry"]["retrieval_failed"], 1)
        self.assertEqual(outcome.row["telemetry"]["hard_fetch_helper_calls"], 1)
        self.assertEqual(outcome.row["telemetry"]["fetch_helper_failures"], 1)
        self.assertFalse(outcome.receipt_present)

    def test_decision_requires_quality_latency_and_all_retrieval_health_gates(self) -> None:
        control = arm_metrics()
        candidate = copy.deepcopy(control)
        candidate["search_total_tokens"] = 1_000_000
        candidate["task_wall_sum_seconds"] = 1_800.0
        health = {
            "retrieval_completed": 64,
            "retrieval_failed": 0,
            "unrecoverable_search_failures": 0,
            "cache_misses": 0,
            "cache_serve_network_fetches": 0,
            "hard_fetch_deadline_failures": 0,
            "fetch_helper_failures": 0,
        }
        value = finalizer.decision(self.protocol, control, candidate, health)
        self.assertTrue(value["passed"])
        for name in (
            "retrieval_failed",
            "unrecoverable_search_failures",
            "cache_misses",
            "cache_serve_network_fetches",
            "hard_fetch_deadline_failures",
            "fetch_helper_failures",
        ):
            damaged = dict(health)
            damaged[name] = 1
            if name == "retrieval_failed":
                damaged["retrieval_completed"] = 63
            failed = finalizer.decision(
                self.protocol, control, candidate, damaged
            )
            self.assertFalse(failed["passed"])

    def test_finalizer_validates_candidate_before_control_and_evaluator(self) -> None:
        order: list[str] = []
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            root = Path(directory)
            with mock.patch.object(
                finalizer,
                "validate_candidate_barrier",
                side_effect=lambda *_: order.append("candidate_freeze")
                or {"rows": [{}] * 64},
            ), mock.patch.object(
                finalizer,
                "load_full_protocol_after_candidate",
                side_effect=lambda *_: order.append("full_protocol")
                or (SimpleNamespace(), self.protocol),
            ), mock.patch.object(
                finalizer,
                "load_frozen_control_after_candidate",
                side_effect=lambda *_: order.append("control") or {"ids": []},
            ), mock.patch.object(
                finalizer,
                "validate_live_evaluator_identity",
                side_effect=lambda *_: order.append("evaluator") or {},
            ), self.assertRaisesRegex(RuntimeError, "recovery surface is absent"):
                finalizer.finalize(root, resume_evaluator=True)
        self.assertEqual(
            order, ["candidate_freeze", "full_protocol", "control", "evaluator"]
        )

    def test_activation_blocks_active_lease_without_process_signal(self) -> None:
        preaudit = {
            "role": "v24275_two_wave_dev64_preactivation_audit",
            "audit_valid": True,
            "launch_authorized": True,
            "protocol_sha256": "a" * 64,
            "forward_contract_sha256": "a" * 64,
            "forward_contract_payload_sha256": self.protocol[
                "forward_runtime_contract"
            ]["payload_sha256"],
            "historical_per_task_control_prediction_freeze_runtime_summary_opened_or_hashed": False,
        }
        preaudit["audit_payload_sha256"] = payload_sha256(preaudit)
        with mock.patch.object(
            activation_target, "validate_protocol", return_value=self.protocol
        ), mock.patch.object(
            activation_target, "read_object", return_value=preaudit
        ), mock.patch.object(
            activation_target, "sha256", return_value="a" * 64
        ), mock.patch.object(
            activation_target, "process_snapshot", return_value=[]
        ), mock.patch.object(
            activation_target, "lease_observation", return_value={"active": True}
        ), self.assertRaisesRegex(RuntimeError, "boundary"):
            activation_target.build_activation(ROOT, now=1)


if __name__ == "__main__":
    unittest.main()
