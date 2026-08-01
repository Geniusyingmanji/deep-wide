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

from scripts.audit_v24236_azure_responses_single_attempt import (  # noqa: E402
    ROOT,
    audit_python_source,
    build_audit,
    payload_sha256,
    publish_new,
)


class AuditV24236AzureResponsesSingleAttemptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = build_audit(ROOT, created_at_unix=1)

    def test_receipt_is_sealed_candidate_adapter_not_production(self) -> None:
        value = self.value
        unsigned = dict(value)
        seal = unsigned.pop("audit_payload_sha256")
        self.assertEqual(seal, payload_sha256(unsigned))
        self.assertTrue(value["label_blind_runtime"])
        self.assertFalse(value["build_only"])
        self.assertTrue(value["candidate_runtime_adapter"])
        self.assertTrue(value["audit_valid"])
        self.assertTrue(
            value["claims"][
                "candidate_azure_responses_single_attempt_adapter_available"
            ]
        )
        self.assertFalse(value["claims"]["production_runtime_wrapper_available"])
        self.assertFalse(value["claims"]["benchmark_score_available"])
        self.assertFalse(value["claims"]["sota"])

    def test_only_candidate_network_capability_is_true(self) -> None:
        authorization = self.value["authorization"]
        self.assertTrue(authorization["candidate_single_attempt_network_call_capability"])
        for field, enabled in authorization.items():
            if field == "candidate_single_attempt_network_call_capability":
                continue
            self.assertFalse(enabled, field)

    def test_parent_receipt_and_four_control_files_are_exact(self) -> None:
        parent = self.value["parent_receipt"]
        self.assertEqual(
            parent["file_sha256"],
            "3f6101c7bb716a0f7d255c2b8d028827e02891c6e12943fa9ae65325a093e6fd",
        )
        self.assertEqual(
            parent["payload_sha256"],
            "e3d0616ac78aded2abf894c4daea4b8cee06905c3f9c0bab9a2e58e8975d8872",
        )
        self.assertEqual(
            parent["v24235_control_manifest_sha256"],
            "1f08afa3ab80460fb6e1c142bca4997d0930c592e494ad59aa2db8d12a3316e5",
        )
        self.assertEqual(parent["v24235_control_files_rehashed"], 4)
        self.assertTrue(parent["v24235_candidate_parent_validated"])

    def test_fake_transport_replays_exactly_one_post_per_callback(self) -> None:
        replay = self.value["fake_transport_replay"]
        self.assertTrue(replay["fake_transport_only"])
        self.assertFalse(replay["network_socket_or_real_provider_called"])
        self.assertEqual(replay["callback_attempt_count"], 2)
        self.assertEqual(replay["transport_post_count"], 2)
        for field in (
            "one_callback_invocation_equals_one_transport_post",
            "first_status_retryable_429",
            "second_status_success_200",
            "same_execution_challenge_across_retries",
            "distinct_attempt_reference_across_retries",
            "redirect_following_disabled",
            "loopback_endpoint_only",
            "raw_prompt_or_response_not_in_receipt",
        ):
            self.assertTrue(replay[field], field)
        self.assertEqual(replay["settled_permit_count"], 1)
        self.assertEqual(replay["pending_permit_count"], 0)

    def test_scientific_scope_discloses_network_and_trust_boundary(self) -> None:
        scope = self.value["scientific_scope"]
        self.assertTrue(
            scope["one_callback_invocation_one_transport_post_by_implementation"]
        )
        self.assertTrue(scope["loopback_only_endpoint_enforced"])
        self.assertTrue(scope["nominal_timeout_and_output_reservation_checked"])
        self.assertTrue(scope["challenge_and_attempt_reference_headers_sent"])
        self.assertTrue(scope["requests_trust_env_disabled"])
        for field in (
            "internal_retry_implemented",
            "redirect_following_implemented",
            "arbitrary_caller_headers_accepted",
            "environment_or_keyring_credential_read_implemented",
            "requests_timeout_is_total_wall_deadline",
            "provider_challenge_consumption_independently_verified",
            "provider_response_authenticity_independently_verified",
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
        self.assertEqual(static["single_transport_post_call_site_count"], 1)
        self.assertTrue(static["network_post_capability"])
        self.assertFalse(
            static[
                "file_environment_keyring_process_subprocess_or_dynamic_code_capability"
            ]
        )
        self.assertEqual(static["privileged_metadata_read_count"], 0)

    def test_static_audit_rejects_extra_capabilities_and_privilege(self) -> None:
        for source in (
            "import os\nclass AzureResponsesSingleAttemptAdapter:\n def bind(self): pass\n def single_attempt(self): return os.getenv('TOKEN')\nclass AzureResponsesRequest: pass\nclass AzureResponsesAttemptValue: pass\n",
            "import pathlib\nclass AzureResponsesSingleAttemptAdapter:\n def bind(self): pass\n def single_attempt(self): return pathlib.Path('x').read_text()\nclass AzureResponsesRequest: pass\nclass AzureResponsesAttemptValue: pass\n",
            "import subprocess\nclass AzureResponsesSingleAttemptAdapter:\n def bind(self): pass\n def single_attempt(self): return subprocess.run(['true'])\nclass AzureResponsesRequest: pass\nclass AzureResponsesAttemptValue: pass\n",
            "def single_attempt(v): return v['ground_truth']\n",
            "def single_attempt(v): return v.get('question_type')\n",
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
                    "scripts.audit_v24236_azure_responses_single_attempt.ROOT",
                    root,
                ),
                mock.patch(
                    "scripts.audit_v24236_azure_responses_single_attempt.OUTPUT",
                    Path("results/receipt.json"),
                ),
                mock.patch(
                    "scripts.audit_v24236_azure_responses_single_attempt.os.open",
                    wraps=os.open,
                ) as open_mock,
                mock.patch(
                    "scripts.audit_v24236_azure_responses_single_attempt.os.fsync",
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
