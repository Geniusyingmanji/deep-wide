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

from scripts.audit_v24237_tavily_search_single_attempt import (  # noqa: E402
    ROOT,
    audit_python_source,
    build_audit,
    payload_sha256,
    publish_new,
)


class AuditV24237TavilySearchSingleAttemptTests(unittest.TestCase):
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
            value["claims"]["candidate_tavily_search_single_attempt_adapter_available"]
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
            "7a5f10ba5ae8f614bfff59c82c2b95b730a088f4597aeebbb7be633ed87c32db",
        )
        self.assertEqual(
            parent["payload_sha256"],
            "feda7566708d85c70d355a6c85803a6920869bfe9685ba5f9aa3f99c16a335eb",
        )
        self.assertEqual(
            parent["v24236_control_manifest_sha256"],
            "3acf7959a239bb8428fbd2a3e92107e76403c358d6d924c41baa978cbce668f0",
        )
        self.assertEqual(parent["v24236_control_files_rehashed"], 4)
        self.assertTrue(parent["v24236_candidate_parent_validated"])

    def test_fake_transport_replays_key_rotation_and_one_post_per_callback(self) -> None:
        replay = self.value["fake_transport_replay"]
        self.assertTrue(replay["fake_transport_only"])
        self.assertFalse(replay["network_socket_or_real_provider_called"])
        self.assertEqual(replay["callback_attempt_count"], 2)
        self.assertEqual(replay["transport_post_count"], 2)
        for field in (
            "one_callback_invocation_equals_one_transport_post",
            "first_status_key_local_432",
            "second_status_success_200",
            "distinct_authorization_credentials_across_attempts",
            "same_execution_challenge_across_retries",
            "distinct_attempt_reference_across_retries",
            "redirect_following_disabled",
            "tls_verification_enabled",
            "exact_https_endpoint_only",
            "credential_absent_from_body_and_receipt",
            "raw_query_or_response_not_in_receipt",
        ):
            self.assertTrue(replay[field], field)
        self.assertEqual(replay["settled_permit_count"], 1)
        self.assertEqual(replay["pending_permit_count"], 0)

    def test_scientific_scope_discloses_credential_and_trust_boundary(self) -> None:
        scope = self.value["scientific_scope"]
        for field in (
            "one_callback_invocation_one_transport_post_by_implementation",
            "exact_https_endpoint_enforced",
            "nominal_timeout_reservation_checked",
            "caller_supplied_credential_required",
            "credential_retained_in_adapter_memory",
            "credential_excluded_from_request_body",
            "direct_credential_echo_rejected_before_response_hash",
            "requests_trust_env_disabled",
            "challenge_and_attempt_reference_headers_sent",
        ):
            self.assertTrue(scope[field], field)
        for field in (
            "internal_retry_implemented",
            "requests_timeout_is_total_wall_deadline",
            "redirect_following_implemented",
            "tls_verification_disabled",
            "arbitrary_caller_headers_accepted",
            "environment_or_keyring_credential_read_implemented",
            "credential_durably_persisted_hashed_or_emitted",
            "provider_challenge_consumption_independently_verified",
            "provider_response_authenticity_independently_verified",
            "real_provider_traffic_observed",
            "active_client_or_runner_integrated",
            "dev64_gate_evaluated",
            "fresh_exact220_evaluated",
            "quality_cost_or_benchmark_effect_observed",
        ):
            self.assertFalse(scope[field], field)
        source = self.value["source_policy"]
        self.assertTrue(source["same_attempt_provider_search_relevance_score_read"])
        self.assertFalse(
            source["gold_evaluator_payload_benchmark_score_reward_or_results_read"]
        )

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
        self.assertEqual(static["tls_verification_bypass_call_count"], 0)
        self.assertEqual(
            static["same_attempt_provider_relevance_score_read_count"],
            1,
        )
        self.assertFalse(
            static[
                "file_environment_keyring_process_subprocess_or_dynamic_code_capability"
            ]
        )
        self.assertEqual(static["privileged_metadata_read_count"], 0)

    def test_static_audit_rejects_extra_capabilities_privilege_and_tls_bypass(self) -> None:
        for source in (
            "import os\nclass TavilySearchSingleAttemptAdapter:\n def bind(self): pass\n def single_attempt(self): return os.getenv('TOKEN')\nclass TavilySearchRequest: pass\nclass TavilySearchAttemptValue: pass\nclass TavilySearchResultValue: pass\n",
            "import pathlib\nclass TavilySearchSingleAttemptAdapter:\n def bind(self): pass\n def single_attempt(self): return pathlib.Path('x').read_text()\nclass TavilySearchRequest: pass\nclass TavilySearchAttemptValue: pass\nclass TavilySearchResultValue: pass\n",
            "import subprocess\nclass TavilySearchSingleAttemptAdapter:\n def bind(self): pass\n def single_attempt(self): return subprocess.run(['true'])\nclass TavilySearchRequest: pass\nclass TavilySearchAttemptValue: pass\nclass TavilySearchResultValue: pass\n",
            "def single_attempt(v): return v['ground_truth']\n",
            "def single_attempt(v): return v.get('question_type')\n",
            "def _decode_value(v): return None\ndef single_attempt(v): return v.get('score')\nclass TavilySearchSingleAttemptAdapter:\n def bind(self): pass\nclass TavilySearchRequest: pass\nclass TavilySearchAttemptValue: pass\nclass TavilySearchResultValue: pass\n",
            "class TavilySearchSingleAttemptAdapter:\n def bind(self): pass\n def single_attempt(self): return self._post('x', verify=False)\nclass TavilySearchRequest: pass\nclass TavilySearchAttemptValue: pass\nclass TavilySearchResultValue: pass\n",
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
                    "scripts.audit_v24237_tavily_search_single_attempt.ROOT",
                    root,
                ),
                mock.patch(
                    "scripts.audit_v24237_tavily_search_single_attempt.OUTPUT",
                    Path("results/receipt.json"),
                ),
                mock.patch(
                    "scripts.audit_v24237_tavily_search_single_attempt.os.open",
                    wraps=os.open,
                ) as open_mock,
                mock.patch(
                    "scripts.audit_v24237_tavily_search_single_attempt.os.fsync",
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
