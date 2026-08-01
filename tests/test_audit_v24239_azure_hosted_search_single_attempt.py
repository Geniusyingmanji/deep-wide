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

from scripts.audit_v24239_azure_hosted_search_single_attempt import (  # noqa: E402
    ROOT,
    audit_python_source,
    build_audit,
    payload_sha256,
    publish_new,
)


class AuditV24239AzureHostedSearchSingleAttemptTests(unittest.TestCase):
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
            value["claims"]["candidate_azure_hosted_search_single_attempt_adapter_available"]
        )
        self.assertFalse(value["claims"]["production_runtime_wrapper_available"])
        self.assertFalse(value["claims"]["provider_action_budget_enforced_pre_effect"])
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
            "93b9752d4a0161944a6a6080c514ea684501b396f35c72e4f3a4e76c7c916b36",
        )
        self.assertEqual(
            parent["payload_sha256"],
            "89e249bec8c76a66883dadb0931aa1f969808629ebb8b82a120d7596ed5fafde",
        )
        self.assertEqual(
            parent["v24238_control_manifest_sha256"],
            "d343b2f5bbd67c52afb107829af852ae504566fb4271d64ca7296450fc3a0eb7",
        )
        self.assertEqual(parent["v24238_control_files_rehashed"], 4)
        self.assertTrue(parent["v24238_candidate_parent_validated"])

    def test_fake_replay_meters_http_tokens_and_provider_actions(self) -> None:
        replay = self.value["fake_transport_replay"]
        self.assertTrue(replay["fake_transport_only"])
        self.assertFalse(replay["network_socket_or_real_provider_called"])
        self.assertEqual(replay["callback_attempt_count"], 2)
        self.assertEqual(replay["transport_post_count"], 2)
        for field in (
            "one_callback_invocation_equals_one_transport_post",
            "first_status_retryable_429",
            "second_status_success_200",
            "retry_usage_unavailable_and_reserved",
            "success_token_usage_observed",
            "success_provider_tool_usage_observed",
            "same_execution_challenge_across_retries",
            "distinct_attempt_reference_across_retries",
            "redirect_following_disabled",
            "raw_queries_response_urls_not_in_receipt",
            "responses_closed",
        ):
            self.assertTrue(replay[field], field)
        self.assertEqual(replay["settled_permit_count"], 1)
        self.assertEqual(replay["pending_permit_count"], 0)

    def test_scientific_scope_discloses_provider_action_and_parser_limits(self) -> None:
        scope = self.value["scientific_scope"]
        for field in (
            "one_callback_invocation_one_transport_post_by_implementation",
            "loopback_only_endpoint_enforced",
            "requests_trust_env_disabled",
            "challenge_and_attempt_reference_headers_sent",
            "observed_provider_tool_actions_metered",
            "response_close_attempted",
            "nominal_timeout_and_output_reservation_checked",
        ):
            self.assertTrue(scope[field], field)
        for field in (
            "internal_retry_implemented",
            "redirect_following_implemented",
            "arbitrary_caller_headers_accepted",
            "environment_or_keyring_credential_read_implemented",
            "provider_challenge_consumption_independently_verified",
            "provider_response_authenticity_independently_verified",
            "provider_tool_action_hard_limit_enforced_pre_effect",
            "provider_tool_action_is_page_evidence",
            "input_token_reservation_coverage_pre_effect_proven",
            "multi_query_marker_coverage_validated_by_adapter",
            "response_body_stream_cap_implemented",
            "response_close_success_independently_verified",
            "requests_timeout_is_total_wall_deadline",
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
        self.assertEqual(static["redirect_following_call_count"], 0)
        self.assertFalse(
            static[
                "file_environment_keyring_process_subprocess_or_dynamic_code_capability"
            ]
        )
        self.assertEqual(static["privileged_metadata_read_count"], 0)

    def test_static_audit_rejects_extra_capabilities_privilege_and_redirect(self) -> None:
        for source in (
            "import os\nclass AzureHostedSearchSingleAttemptAdapter:\n def bind(self): pass\n def single_attempt(self): return os.getenv('TOKEN')\nclass AzureHostedSearchRequest: pass\nclass AzureHostedSearchAttemptValue: pass\nclass AzureHostedSearchActionValue: pass\nclass AzureHostedSearchCitationValue: pass\nclass AzureHostedSearchSourceValue: pass\n",
            "import pathlib\nclass AzureHostedSearchSingleAttemptAdapter:\n def bind(self): pass\n def single_attempt(self): return pathlib.Path('x').read_text()\nclass AzureHostedSearchRequest: pass\nclass AzureHostedSearchAttemptValue: pass\nclass AzureHostedSearchActionValue: pass\nclass AzureHostedSearchCitationValue: pass\nclass AzureHostedSearchSourceValue: pass\n",
            "import subprocess\nclass AzureHostedSearchSingleAttemptAdapter:\n def bind(self): pass\n def single_attempt(self): return subprocess.run(['true'])\nclass AzureHostedSearchRequest: pass\nclass AzureHostedSearchAttemptValue: pass\nclass AzureHostedSearchActionValue: pass\nclass AzureHostedSearchCitationValue: pass\nclass AzureHostedSearchSourceValue: pass\n",
            "def single_attempt(v): return v['ground_truth']\n",
            "def single_attempt(v): return v.get('question_type')\n",
            "class AzureHostedSearchSingleAttemptAdapter:\n def bind(self): pass\n def single_attempt(self): return self._post('x', allow_redirects=True)\nclass AzureHostedSearchRequest: pass\nclass AzureHostedSearchAttemptValue: pass\nclass AzureHostedSearchActionValue: pass\nclass AzureHostedSearchCitationValue: pass\nclass AzureHostedSearchSourceValue: pass\n",
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
                    "scripts.audit_v24239_azure_hosted_search_single_attempt.ROOT",
                    root,
                ),
                mock.patch(
                    "scripts.audit_v24239_azure_hosted_search_single_attempt.OUTPUT",
                    Path("results/receipt.json"),
                ),
                mock.patch(
                    "scripts.audit_v24239_azure_hosted_search_single_attempt.os.open",
                    wraps=os.open,
                ) as open_mock,
                mock.patch(
                    "scripts.audit_v24239_azure_hosted_search_single_attempt.os.fsync",
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
