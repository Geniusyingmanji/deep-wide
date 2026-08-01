from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT_PATH = Path(__file__).resolve().parents[1]
if str(ROOT_PATH) not in sys.path:
    sys.path.insert(0, str(ROOT_PATH))

from scripts.audit_v24243_retry_deadline_scheduler import (  # noqa: E402
    ROOT,
    audit_python_source,
    build_audit,
    payload_sha256,
    publish_new,
)


class AuditV24243RetryDeadlineSchedulerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = build_audit(ROOT, created_at_unix=1)

    def test_receipt_is_sealed_label_blind_candidate(self) -> None:
        value = self.value
        unsigned = dict(value)
        seal = unsigned.pop("audit_payload_sha256")
        self.assertEqual(seal, payload_sha256(unsigned))
        self.assertTrue(value["label_blind_runtime"])
        self.assertTrue(value["candidate_runtime_scheduler"])
        self.assertTrue(value["audit_valid"])
        authorization = value["authorization"]
        self.assertTrue(
            authorization["caller_supplied_effect_callback_invocation_capability"]
        )
        for field, enabled in authorization.items():
            if field == "caller_supplied_effect_callback_invocation_capability":
                continue
            self.assertFalse(enabled, field)
        self.assertFalse(value["claims"]["benchmark_score_available"])
        self.assertFalse(value["claims"]["sota"])

    def test_parent_receipt_and_four_control_files_are_exact(self) -> None:
        parent = self.value["parent_receipt"]
        self.assertEqual(
            parent["file_sha256"],
            "93606959b007272e1b6151a6efc60a5da50ef893e6fb0f4004c583b6c2b9100e",
        )
        self.assertEqual(
            parent["payload_sha256"],
            "e90c354ff56dd8c6ada20ef1a8f0735f6f8f3e6113f0095427e2e84dc2c055bf",
        )
        self.assertEqual(
            parent["v24242_control_manifest_sha256"],
            "38cc04bc40e28e3057c76d52f7cb4bfc511636cf5e3a9f8e56ae6fdea8656418",
        )
        self.assertEqual(parent["v24242_control_files_rehashed"], 4)
        self.assertTrue(parent["v24242_candidate_parent_validated"])

    def test_fake_replay_is_deterministic_and_callback_overrun_fails_closed(self) -> None:
        replay = self.value["fake_schedule_replay"]
        self.assertTrue(replay["fake_callback_local_tempdir_and_virtual_time_only"])
        self.assertFalse(replay["network_socket_or_real_provider_called"])
        self.assertEqual(replay["successful_attempt_count"], 3)
        self.assertEqual(replay["successful_provider_callback_count"], 3)
        self.assertEqual(replay["deterministic_sleep_seconds"], [0.02, 0.04])
        self.assertEqual(replay["required_backoff_total_milliseconds"], 60)
        self.assertEqual(replay["virtual_total_elapsed_nanoseconds"], 75_000_000)
        self.assertTrue(replay["durable_settlement_committed_after_success"])
        self.assertTrue(replay["callback_overrun_rejected_after_return"])
        self.assertEqual(replay["overrun_provider_callback_count"], 1)
        self.assertTrue(replay["overrun_permit_remains_charged"])
        self.assertFalse(replay["overrun_settlement_committed"])
        self.assertFalse(replay["callback_force_cancellation_implemented"])
        self.assertFalse(replay["raw_callback_value_in_receipt"])

    def test_scope_separates_checkpoint_deadline_from_hard_timeout(self) -> None:
        scope = self.value["scientific_scope"]
        for field in (
            "strict_retry_admission_deadline_implemented",
            "deterministic_capped_backoff_implemented",
            "backoff_preauthorized_in_wall_reservation_implemented",
            "injectable_monotonic_clock_and_sleeper_implemented",
            "post_callback_deadline_check_implemented",
        ):
            self.assertTrue(scope[field], field)
        for field in (
            "already_running_callback_force_cancellation_implemented",
            "trusted_hard_total_wall_timeout_implemented",
            "requests_per_call_timeout_treated_as_total_deadline",
            "scheduler_state_durably_persisted",
            "clock_or_sleeper_independently_attested",
            "real_provider_traffic_observed",
            "active_client_or_runner_integrated",
            "dev64_gate_evaluated",
            "fresh_exact220_evaluated",
            "quality_cost_or_benchmark_effect_observed",
        ):
            self.assertFalse(scope[field], field)

    def test_active_forward_and_static_capability_audits_are_exact(self) -> None:
        guard = self.value["active_forward_guard"]
        self.assertTrue(
            guard["module_absent_from_guarded_clients_and_forward_entrypoints"]
        )
        self.assertTrue(
            all(
                count == 0
                for count in guard["module_name_hit_count_by_file"].values()
            )
        )
        static = self.value["static_capability_audit"]
        self.assertEqual(static["caller_supplied_callback_call_site_count"], 1)
        self.assertEqual(static["parent_coordinator_run_effect_call_site_count"], 1)
        self.assertEqual(static["direct_time_sleep_call_site_count"], 0)
        self.assertEqual(static["monotonic_clock_default_site_count"], 1)
        self.assertFalse(
            static[
                "direct_network_environment_file_process_subprocess_or_dynamic_code_capability"
            ]
        )
        self.assertEqual(static["privileged_metadata_read_count"], 0)

    def test_static_audit_rejects_expansive_capabilities_and_privilege(self) -> None:
        for source in (
            "import requests\ndef x(): return requests.get('https://example.invalid')\n",
            "import subprocess\ndef x(): return subprocess.run(['true'])\n",
            "import os\ndef x(): return os.environ.get('TOKEN')\n",
            "from deepwide_agent.runtime import DeepWideRuntime\n",
            "def x(): return open('x')\n",
            "def x(): return eval('1')\n",
            "def x(v): return v['ground_truth']\n",
            "def x(v): return v.get('question_type')\n",
            "def x(v): return getattr(v, 'gold')\n",
        ):
            with self.subTest(source=source):
                with self.assertRaisesRegex(RuntimeError, "capability boundary"):
                    audit_python_source(source)

    def test_publish_rejects_noncanonical_output(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            with self.assertRaisesRegex(RuntimeError, "noncanonical"):
                publish_new(Path(directory) / "receipt.json", self.value)

    def test_publish_is_exclusive_nofollow_and_fsyncs_file_and_parent(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            root = Path(directory).resolve()
            target = root / "results" / "receipt.json"
            target.parent.mkdir()
            with (
                mock.patch(
                    "scripts.audit_v24243_retry_deadline_scheduler.ROOT",
                    root,
                ),
                mock.patch(
                    "scripts.audit_v24243_retry_deadline_scheduler.OUTPUT",
                    Path("results/receipt.json"),
                ),
                mock.patch(
                    "scripts.audit_v24243_retry_deadline_scheduler.os.open",
                    wraps=os.open,
                ) as open_mock,
                mock.patch(
                    "scripts.audit_v24243_retry_deadline_scheduler.os.fsync",
                    wraps=os.fsync,
                ) as fsync_mock,
            ):
                publish_new(target, self.value)
                self.assertGreaterEqual(fsync_mock.call_count, 2)
                first_flags = open_mock.call_args_list[0].args[1]
                self.assertTrue(first_flags & os.O_EXCL)
                self.assertTrue(first_flags & os.O_NOFOLLOW)
                with self.assertRaises(FileExistsError):
                    publish_new(target, self.value)


if __name__ == "__main__":
    unittest.main()
