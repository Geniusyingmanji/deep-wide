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

from scripts.audit_v24238_native_http_fetch_single_attempt import (  # noqa: E402
    ROOT,
    audit_python_source,
    build_audit,
    payload_sha256,
    publish_new,
)


class AuditV24238NativeHttpFetchSingleAttemptTests(unittest.TestCase):
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
            value["claims"]["candidate_native_http_fetch_single_attempt_adapter_available"]
        )
        self.assertFalse(value["claims"]["production_runtime_wrapper_available"])
        self.assertFalse(value["claims"]["dns_rebinding_safety_proven"])
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
            "8c9315b3dc01d0255c79dd0fd9ee747961df5abe2c8416541dfd80d5f1d3c8ad",
        )
        self.assertEqual(
            parent["payload_sha256"],
            "6d8f359f55c2c0ca546b29e39e4fbfbd31575252d5131d56d90923cf27d91ca9",
        )
        self.assertEqual(
            parent["v24237_control_manifest_sha256"],
            "bddfff603d5c5466bd5b76e7819f8ce916dadf2f8ba801d07104e2c24a0d2330",
        )
        self.assertEqual(parent["v24237_control_files_rehashed"], 4)
        self.assertTrue(parent["v24237_candidate_parent_validated"])

    def test_fake_replay_repeats_dns_before_one_get_per_callback(self) -> None:
        replay = self.value["fake_transport_replay"]
        self.assertTrue(replay["fake_resolver_and_transport_only"])
        self.assertFalse(replay["network_socket_or_real_fetch_called"])
        self.assertEqual(replay["callback_attempt_count"], 2)
        self.assertEqual(replay["resolver_call_count"], 2)
        self.assertEqual(replay["transport_get_count"], 2)
        for field in (
            "one_callback_invocation_equals_one_transport_get",
            "dns_preflight_repeated_before_each_get",
            "first_status_retryable_500",
            "second_status_success_200",
            "same_url_across_retries",
            "redirect_following_disabled",
            "streaming_enabled",
            "tls_verification_enabled",
            "raw_url_or_response_not_in_receipt",
            "responses_closed",
        ):
            self.assertTrue(replay[field], field)
        self.assertEqual(replay["settled_permit_count"], 1)
        self.assertEqual(replay["pending_permit_count"], 0)

    def test_scientific_scope_discloses_ssrf_hash_and_deadline_limits(self) -> None:
        scope = self.value["scientific_scope"]
        for field in (
            "one_callback_invocation_one_transport_get_by_implementation",
            "public_address_dns_preflight_implemented",
            "system_resolver_used_by_default",
            "retained_response_byte_cap_implemented",
            "response_close_attempted",
            "caller_public_nonsecret_url_required",
            "sensitive_query_key_rejection_implemented",
            "nominal_timeout_reservation_checked",
            "requests_trust_env_disabled",
        ):
            self.assertTrue(scope[field], field)
        for field in (
            "internal_retry_implemented",
            "redirect_following_implemented",
            "tls_verification_disabled",
            "dns_preflight_result_pinned_to_transport",
            "dns_rebinding_fully_excluded",
            "full_provider_response_hashed_when_truncated",
            "total_transport_response_bytes_hard_capped",
            "response_close_success_independently_verified",
            "request_url_directly_persisted_or_emitted",
            "url_secret_absence_independently_verified",
            "requests_timeout_is_total_wall_deadline",
            "arbitrary_caller_headers_accepted",
            "environment_or_keyring_credential_read_implemented",
            "challenge_and_attempt_reference_headers_sent",
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
        self.assertEqual(static["single_transport_get_call_site_count"], 1)
        self.assertEqual(static["system_resolver_call_site_count"], 1)
        self.assertTrue(static["network_get_and_dns_capability"])
        self.assertEqual(static["tls_verification_bypass_call_count"], 0)
        self.assertEqual(static["redirect_following_call_count"], 0)
        self.assertFalse(
            static[
                "file_environment_keyring_process_subprocess_or_dynamic_code_capability"
            ]
        )
        self.assertEqual(static["privileged_metadata_read_count"], 0)

    def test_static_audit_rejects_extra_capability_privilege_and_transport_bypass(self) -> None:
        for source in (
            "import os\nclass NativeHttpFetchSingleAttemptAdapter:\n def bind(self): pass\n def single_attempt(self): return os.getenv('TOKEN')\nclass NativeHttpFetchRequest: pass\nclass NativeHttpFetchAttemptValue: pass\n",
            "import pathlib\nclass NativeHttpFetchSingleAttemptAdapter:\n def bind(self): pass\n def single_attempt(self): return pathlib.Path('x').read_text()\nclass NativeHttpFetchRequest: pass\nclass NativeHttpFetchAttemptValue: pass\n",
            "import subprocess\nclass NativeHttpFetchSingleAttemptAdapter:\n def bind(self): pass\n def single_attempt(self): return subprocess.run(['true'])\nclass NativeHttpFetchRequest: pass\nclass NativeHttpFetchAttemptValue: pass\n",
            "def single_attempt(v): return v['ground_truth']\n",
            "def single_attempt(v): return v.get('question_type')\n",
            "class NativeHttpFetchSingleAttemptAdapter:\n def bind(self): pass\n def single_attempt(self): return self._get('x', verify=False)\nclass NativeHttpFetchRequest: pass\nclass NativeHttpFetchAttemptValue: pass\n",
            "class NativeHttpFetchSingleAttemptAdapter:\n def bind(self): pass\n def single_attempt(self): return self._get('x', allow_redirects=True)\nclass NativeHttpFetchRequest: pass\nclass NativeHttpFetchAttemptValue: pass\n",
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
                    "scripts.audit_v24238_native_http_fetch_single_attempt.ROOT",
                    root,
                ),
                mock.patch(
                    "scripts.audit_v24238_native_http_fetch_single_attempt.OUTPUT",
                    Path("results/receipt.json"),
                ),
                mock.patch(
                    "scripts.audit_v24238_native_http_fetch_single_attempt.os.open",
                    wraps=os.open,
                ) as open_mock,
                mock.patch(
                    "scripts.audit_v24238_native_http_fetch_single_attempt.os.fsync",
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
