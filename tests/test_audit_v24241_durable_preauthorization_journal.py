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

from scripts.audit_v24241_durable_preauthorization_journal import (  # noqa: E402
    ROOT,
    audit_python_source,
    build_audit,
    payload_sha256,
    publish_new,
)


class AuditV24241DurablePreauthorizationJournalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = build_audit(ROOT, created_at_unix=1)

    def test_receipt_is_sealed_build_only_and_authorizes_nothing(self) -> None:
        value = self.value
        unsigned = dict(value)
        seal = unsigned.pop("audit_payload_sha256")
        self.assertEqual(seal, payload_sha256(unsigned))
        self.assertTrue(value["label_blind_runtime"])
        self.assertTrue(value["build_only"])
        self.assertTrue(value["candidate_local_posix_store"])
        self.assertTrue(value["audit_valid"])
        self.assertTrue(
            value["claims"]["candidate_local_posix_durable_journal_available"]
        )
        self.assertFalse(value["claims"]["active_harness_durability_available"])
        self.assertFalse(value["claims"]["benchmark_score_available"])
        self.assertFalse(value["claims"]["sota"])
        for field, enabled in value["authorization"].items():
            self.assertFalse(enabled, field)

    def test_parent_receipt_and_four_control_files_are_exact(self) -> None:
        parent = self.value["parent_receipt"]
        self.assertEqual(
            parent["file_sha256"],
            "5d4b5b0861e0de2e3aa334c572c6e5a64677bb55870c30640a0c237de7d6a2ff",
        )
        self.assertEqual(
            parent["payload_sha256"],
            "f9c5de115527ae52ebb880b4ce1084e576e5d760d09cf3001b6778ad2368cddb",
        )
        self.assertEqual(
            parent["v24240_control_manifest_sha256"],
            "6f0ef60927beebe54a473db955c69585add0d1f8016bc88e980a0646e7d746b1",
        )
        self.assertEqual(parent["v24240_control_files_rehashed"], 4)
        self.assertTrue(parent["v24240_candidate_parent_validated"])

    def test_local_replay_is_crash_recoverable_and_incremental(self) -> None:
        replay = self.value["local_journal_replay"]
        for field in (
            "local_posix_filesystem_only",
            "initialized_generation_zero",
            "permit_and_settlement_appended",
            "exact_state_replay_after_two_entries",
            "stale_compare_and_swap_rejected",
            "crash_after_pending_fsync_observed",
            "unique_complete_pending_entry_recovered",
            "clean_generation_after_recovery",
            "generation_files_have_one_link_after_cleanup",
            "entry_contains_only_incremental_event_not_full_state",
            "status_is_content_free",
        ):
            self.assertTrue(replay[field], field)
        self.assertFalse(replay["network_socket_or_real_provider_called"])
        self.assertEqual(replay["recovered_pending_file_count"], 1)

    def test_scope_discloses_local_only_security_boundary(self) -> None:
        scope = self.value["scientific_scope"]
        for field in (
            "local_posix_advisory_lock_implemented",
            "cross_process_cas_for_cooperating_writers_implemented",
            "immutable_no_clobber_generation_files_implemented",
            "content_bound_pending_recovery_implemented",
            "file_and_directory_fsync_implemented",
            "incremental_event_storage_implemented",
            "crash_recovery_after_initialization_implemented",
        ):
            self.assertTrue(scope[field], field)
        for field in (
            "initialization_crash_automatic_recovery_implemented",
            "network_or_distributed_filesystem_semantics_proven",
            "hardware_stable_storage_independently_attested",
            "malicious_same_user_resealing_excluded",
            "independent_append_only_transparency_log_used",
            "active_harness_durability_integrated",
            "real_power_loss_or_kernel_crash_observed",
            "real_provider_traffic_observed",
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
        self.assertEqual(static["disallowed_import_count"], 0)
        self.assertEqual(static["privileged_metadata_read_count"], 0)
        self.assertFalse(
            static[
                "environment_network_model_search_fetch_process_subprocess_or_dynamic_code_capability"
            ]
        )
        for field in (
            "repository_local_file_read_call_count",
            "repository_local_file_write_call_count",
            "fsync_call_count",
            "flock_call_count",
            "hard_link_call_count",
            "create_exclusive_open_call_count",
            "nofollow_open_call_count",
        ):
            self.assertGreater(static[field], 0, field)

    def test_static_audit_rejects_expansive_capabilities_and_privilege(self) -> None:
        for source in (
            "import os\ndef x(): return os.environ.get('TOKEN')\n",
            "import os\ndef x(): return os.execv('/bin/true', ['true'])\n",
            "import requests\ndef x(): return requests.get('https://example.invalid')\n",
            "import subprocess\ndef x(): return subprocess.run(['true'])\n",
            "from deepwide_agent.runtime import DeepWideRuntime\n",
            "def x(): return open('x')\n",
            "def x(): return eval('1')\n",
            "def x(v): return v['ground_truth']\n",
            "def x(v): return v.get('question_type')\n",
            "def x(v): return v.pop('gold')\n",
            "def x(v): return getattr(v, 'ground_truth')\n",
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
                    "scripts.audit_v24241_durable_preauthorization_journal.ROOT",
                    root,
                ),
                mock.patch(
                    "scripts.audit_v24241_durable_preauthorization_journal.OUTPUT",
                    Path("results/receipt.json"),
                ),
                mock.patch(
                    "scripts.audit_v24241_durable_preauthorization_journal.os.open",
                    wraps=os.open,
                ) as open_mock,
                mock.patch(
                    "scripts.audit_v24241_durable_preauthorization_journal.os.fsync",
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
