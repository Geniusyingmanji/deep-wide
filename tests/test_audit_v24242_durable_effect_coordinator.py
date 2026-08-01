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

from scripts.audit_v24242_durable_effect_coordinator import (  # noqa: E402
    ROOT,
    audit_python_source,
    build_audit,
    payload_sha256,
    publish_new,
)


class AuditV24242DurableEffectCoordinatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = build_audit(ROOT, created_at_unix=1)

    def test_receipt_is_sealed_candidate_and_only_callback_capability_is_true(self) -> None:
        value = self.value
        unsigned = dict(value)
        seal = unsigned.pop("audit_payload_sha256")
        self.assertEqual(seal, payload_sha256(unsigned))
        self.assertTrue(value["label_blind_runtime"])
        self.assertFalse(value["build_only"])
        self.assertTrue(value["candidate_runtime_coordinator"])
        self.assertTrue(value["audit_valid"])
        authorization = value["authorization"]
        self.assertTrue(authorization["caller_supplied_effect_callback_invocation_capability"])
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
            "0ddc8ba70d93578ff5d391c46da5a71711009b3ce349622e05f528fc899af021",
        )
        self.assertEqual(
            parent["payload_sha256"],
            "95a3e1deb4efc78324f9f88232240f5fa3adabc8a103c26527828c992e63725b",
        )
        self.assertEqual(
            parent["v24241_control_manifest_sha256"],
            "c4ee8e3caba5c4ed78c5d9c6ae84fb5059c632f47b1336fae2923d13e381535f",
        )
        self.assertEqual(parent["v24241_control_files_rehashed"], 4)
        self.assertTrue(parent["v24241_candidate_parent_validated"])

    def test_fake_replay_has_one_post_and_rejects_every_uncertain_replay(self) -> None:
        replay = self.value["fake_durable_effect_replay"]
        self.assertTrue(replay["fake_transport_and_local_tempdir_only"])
        self.assertFalse(replay["network_socket_or_real_provider_called"])
        self.assertEqual(replay["successful_gpt56_adapter_transport_post_count"], 1)
        self.assertEqual(replay["all_synthetic_replays_transport_post_count"], 3)
        self.assertTrue(replay["durable_permit_visible_before_callback"])
        self.assertTrue(replay["durable_settlement_visible_after_callback"])
        self.assertEqual(replay["success_generation_count"], 2)
        self.assertEqual(replay["success_pending_permit_count"], 0)
        for field in (
            "before_callback_crash_replay_rejected",
            "after_callback_crash_replay_rejected",
            "after_settlement_crash_replay_rejected",
        ):
            self.assertTrue(replay[field], field)
        self.assertEqual(replay["before_callback_crash_callback_count"], 0)
        self.assertEqual(replay["after_callback_crash_callback_count"], 1)
        self.assertEqual(replay["after_settlement_crash_callback_count"], 1)
        self.assertFalse(replay["raw_prompt_answer_url_or_credential_in_receipt"])
        self.assertFalse(replay["provider_response_close_attempted_by_v24236"])

    def test_scope_separates_local_ordering_from_unproven_runtime_features(self) -> None:
        scope = self.value["scientific_scope"]
        for field in (
            "durable_permit_before_callback_implemented",
            "durable_settlement_after_callback_implemented",
            "deterministic_invocation_idempotency_binding_implemented",
            "local_posix_crash_durable_effect_ordering_implemented",
            "cross_process_cas_implemented",
            "callback_concurrency_between_effects_implemented",
        ):
            self.assertTrue(scope[field], field)
        for field in (
            "preexisting_pending_permit_automatic_replay_implemented",
            "callback_or_settlement_failure_automatic_replay_implemented",
            "attempt_measurement_durably_persisted",
            "callback_timeout_implemented",
            "retry_backoff_implemented",
            "total_wall_deadline_implemented",
            "provider_challenge_consumption_independently_verified",
            "provider_response_authenticity_independently_verified",
            "network_or_distributed_filesystem_semantics_proven",
            "real_power_loss_or_kernel_crash_observed",
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
            all(count == 0 for count in guard["module_name_hit_count_by_file"].values())
        )
        static = self.value["static_capability_audit"]
        self.assertEqual(static["caller_supplied_callback_call_site_count"], 1)
        self.assertGreaterEqual(static["journal_load_call_site_count"], 1)
        self.assertEqual(static["journal_compare_and_append_call_site_count"], 2)
        self.assertFalse(
            static[
                "direct_network_environment_process_subprocess_or_dynamic_code_capability"
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
                    "scripts.audit_v24242_durable_effect_coordinator.ROOT",
                    root,
                ),
                mock.patch(
                    "scripts.audit_v24242_durable_effect_coordinator.OUTPUT",
                    Path("results/receipt.json"),
                ),
                mock.patch(
                    "scripts.audit_v24242_durable_effect_coordinator.os.open",
                    wraps=os.open,
                ) as open_mock,
                mock.patch(
                    "scripts.audit_v24242_durable_effect_coordinator.os.fsync",
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
