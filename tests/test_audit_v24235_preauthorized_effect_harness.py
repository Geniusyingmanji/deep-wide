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

from scripts.audit_v24235_preauthorized_effect_harness import (  # noqa: E402
    ROOT,
    audit_python_source,
    build_audit,
    payload_sha256,
    publish_new,
)


class AuditV24235PreauthorizedEffectHarnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = build_audit(ROOT, created_at_unix=1)

    def test_receipt_is_sealed_candidate_runtime_not_production(self) -> None:
        value = self.value
        unsigned = dict(value)
        seal = unsigned.pop("audit_payload_sha256")
        self.assertEqual(seal, payload_sha256(unsigned))
        self.assertTrue(value["label_blind_runtime"])
        self.assertFalse(value["build_only"])
        self.assertTrue(value["candidate_runtime_harness"])
        self.assertTrue(value["audit_valid"])
        self.assertTrue(
            value["claims"]["candidate_preauthorized_effect_harness_available"]
        )
        self.assertFalse(value["claims"]["production_runtime_wrapper_available"])
        self.assertFalse(value["claims"]["benchmark_score_available"])
        self.assertFalse(value["claims"]["sota"])

    def test_only_candidate_callback_authorization_is_true(self) -> None:
        authorization = self.value["authorization"]
        self.assertTrue(
            authorization["candidate_caller_supplied_effect_callback_invocation"]
        )
        for field, enabled in authorization.items():
            if field == "candidate_caller_supplied_effect_callback_invocation":
                continue
            self.assertFalse(enabled, field)

    def test_parent_receipt_payload_and_four_control_files_are_exact(self) -> None:
        parent = self.value["parent_receipt"]
        self.assertEqual(
            parent["file_sha256"],
            "bc8d819c7ac506211ccac66b838fabeadd7e483c753afe85a88546ecbcf4144e",
        )
        self.assertEqual(
            parent["payload_sha256"],
            "7dca1ae5897b61963763973db72337ddb9a4311e8f687e15553ffb33a9cb23b7",
        )
        self.assertEqual(
            parent["v24234_control_manifest_sha256"],
            "f800894c52616037cdaea613385d4a4fc35a73c092c7c3a57db81c266505be97",
        )
        self.assertEqual(parent["v24234_control_files_rehashed"], 4)
        self.assertTrue(parent["v24234_build_only_parent_validated"])

    def test_replay_covers_order_concurrency_and_failure_without_provider(self) -> None:
        replay = self.value["synthetic_harness_replay"]
        for field in (
            "synthetic_callback_only",
            "permit_seen_before_every_retry_callback",
            "retry_execution_receipt_validated",
            "raw_callback_value_not_persisted_hashed_or_emitted",
            "two_permit_callback_overlap_observed",
            "admission_and_settlement_serialized_by_single_process_lock",
            "callback_exception_failure_receipt_validated",
            "failed_effect_reservation_remains_charged_and_pending",
        ):
            self.assertTrue(replay[field], field)
        self.assertFalse(replay["real_provider_model_search_fetch_or_network_called"])
        self.assertFalse(replay["automatic_whole_effect_replay_authorized"])
        self.assertEqual(replay["retry_callback_call_count"], 2)
        self.assertEqual(replay["final_issued_permit_count"], 4)
        self.assertEqual(replay["final_settled_permit_count"], 3)
        self.assertEqual(replay["final_pending_permit_count"], 1)

    def test_scientific_scope_discloses_callback_and_durability_limits(self) -> None:
        scope = self.value["scientific_scope"]
        for field in (
            "permit_committed_before_process_local_callback_invocation",
            "settlement_committed_after_callback_completion",
            "different_permit_callbacks_can_overlap",
            "same_effect_retry_callbacks_are_sequential_and_bounded",
            "callback_failure_keeps_reservation_charged_and_permit_pending",
            "caller_supplied_callback_may_have_external_effects",
        ):
            self.assertTrue(scope[field], field)
        for field in (
            "automatic_whole_effect_replay_authorized",
            "raw_callback_value_persisted_hashed_or_emitted",
            "callback_is_exactly_one_provider_attempt_independently_verified",
            "external_effect_after_permit_independently_verified",
            "provider_challenge_consumption_independently_verified",
            "cross_process_compare_and_swap_implemented",
            "crash_durable_journal_implemented",
            "callback_timeout_implemented",
            "retry_backoff_implemented",
            "real_provider_adapter_integrated",
            "real_model_search_fetch_or_orchestrator_execution_observed",
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
        self.assertTrue(static["caller_supplied_callback_invocation_capability"])
        self.assertFalse(
            static[
                "direct_file_environment_network_model_search_fetch_process_subprocess_or_dynamic_code_capability"
            ]
        )
        self.assertEqual(static["privileged_metadata_read_count"], 0)

    def test_static_audit_rejects_direct_capabilities_and_privilege(self) -> None:
        for source in (
            "import os\ndef run_effect(callback): return os.getenv('TOKEN')\n",
            "import pathlib\ndef run_effect(callback): return pathlib.Path('x').read_text()\n",
            "import requests\ndef run_effect(callback): return requests.get('https://example.invalid')\n",
            "import subprocess\ndef run_effect(callback): return subprocess.run(['true'])\n",
            "from deepwide_agent.runtime import DeepWideRuntime\n",
            "def run_effect(callback): return open('x')\n",
            "def run_effect(callback): return eval('1')\n",
            "def run_effect(callback, v): callback(v); return v['ground_truth']\n",
            "def run_effect(callback, v): callback(v); return v.get('question_type')\n",
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
                    "scripts.audit_v24235_preauthorized_effect_harness.ROOT",
                    root,
                ),
                mock.patch(
                    "scripts.audit_v24235_preauthorized_effect_harness.OUTPUT",
                    Path("results/receipt.json"),
                ),
                mock.patch(
                    "scripts.audit_v24235_preauthorized_effect_harness.os.open",
                    wraps=os.open,
                ) as open_mock,
                mock.patch(
                    "scripts.audit_v24235_preauthorized_effect_harness.os.fsync",
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
