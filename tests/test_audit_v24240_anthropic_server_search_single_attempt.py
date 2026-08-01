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

from scripts.audit_v24240_anthropic_server_search_single_attempt import (  # noqa: E402
    ROOT,
    audit_python_source,
    build_audit,
    payload_sha256,
    publish_new,
)


class AuditV24240AnthropicServerSearchSingleAttemptTests(unittest.TestCase):
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
                "candidate_anthropic_server_search_single_attempt_adapter_available"
            ]
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
            "8d1022e6f2570668f6ad46d5c87e21bc2e0524319a910613adff063c51587de7",
        )
        self.assertEqual(
            parent["payload_sha256"],
            "22483f5e0f847eee50b8fa2093ec5cba46eb5b9a84af0b85bbaa55358b5681b8",
        )
        self.assertEqual(
            parent["v24239_control_manifest_sha256"],
            "ca3badf75a01e47dc6d598fd592389f06ca27eaaac9e6a47d9002b546cc4f4b5",
        )
        self.assertEqual(parent["v24239_control_files_rehashed"], 4)
        self.assertTrue(parent["v24239_candidate_parent_validated"])

    def test_fake_replay_meters_http_cache_tokens_and_provider_actions(self) -> None:
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
            "success_token_usage_observed_with_cache",
            "success_provider_tool_usage_observed_and_cross_checked",
            "same_execution_challenge_across_retries",
            "distinct_attempt_reference_across_retries",
            "credential_header_only_and_same_across_retries",
            "redirect_following_disabled_and_tls_enabled",
            "raw_query_answer_credential_urls_not_in_receipt",
            "responses_closed",
        ):
            self.assertTrue(replay[field], field)
        self.assertEqual(replay["settled_permit_count"], 1)
        self.assertEqual(replay["pending_permit_count"], 0)

    def test_scientific_scope_discloses_credential_meter_and_provider_limits(self) -> None:
        scope = self.value["scientific_scope"]
        for field in (
            "one_callback_invocation_one_transport_post_by_implementation",
            "exact_https_endpoint_enforced",
            "requests_trust_env_disabled",
            "caller_supplied_credential_required",
            "credential_retained_in_adapter_memory",
            "credential_excluded_from_request_body",
            "direct_credential_echo_rejected_before_response_hash",
            "challenge_and_attempt_reference_headers_sent",
            "provider_declared_max_uses_sent",
            "provider_declared_max_uses_violation_rejected_post_effect",
            "observed_provider_tool_actions_metered",
            "provider_action_counter_cross_checked",
            "provider_action_counter_mismatch_fails_closed",
            "cache_tokens_included_in_metered_input",
            "response_close_attempted",
            "nominal_timeout_output_and_tool_reservation_checked",
        ):
            self.assertTrue(scope[field], field)
        for field in (
            "internal_retry_implemented",
            "redirect_following_implemented",
            "tls_verification_disabled",
            "arbitrary_caller_headers_accepted",
            "environment_or_keyring_credential_read_implemented",
            "credential_durably_persisted_hashed_or_emitted",
            "provider_challenge_consumption_independently_verified",
            "provider_response_authenticity_independently_verified",
            "provider_tool_action_hard_limit_enforced_pre_effect",
            "provider_tool_action_is_page_evidence",
            "input_token_reservation_coverage_pre_effect_proven",
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
        self.assertEqual(static["tls_verification_disable_call_count"], 0)
        self.assertFalse(
            static[
                "file_environment_keyring_process_subprocess_or_dynamic_code_capability"
            ]
        )
        self.assertEqual(static["privileged_metadata_read_count"], 0)

    def test_static_audit_rejects_extra_capabilities_privilege_redirect_and_tls(self) -> None:
        base = (
            "class AnthropicServerSearchSingleAttemptAdapter:\n"
            " def bind(self): pass\n"
            " def single_attempt(self): pass\n"
            "class AnthropicServerSearchRequest: pass\n"
            "class AnthropicServerSearchAttemptValue: pass\n"
            "class AnthropicServerSearchActionValue: pass\n"
            "class AnthropicServerSearchCitationValue: pass\n"
            "class AnthropicServerSearchResultValue: pass\n"
        )
        for source in (
            "import os\n" + base.replace("pass\nclass", "return os.getenv('TOKEN')\nclass", 1),
            "import pathlib\n" + base.replace("pass\nclass", "return pathlib.Path('x').read_text()\nclass", 1),
            "import subprocess\n" + base.replace("pass\nclass", "return subprocess.run(['true'])\nclass", 1),
            "def single_attempt(v): return v['ground_truth']\n",
            "def single_attempt(v): return v.get('question_type')\n",
            base.replace(
                "def single_attempt(self): pass",
                "def single_attempt(self): return self._post('x', allow_redirects=True, verify=True)",
            ),
            base.replace(
                "def single_attempt(self): pass",
                "def single_attempt(self): return self._post('x', allow_redirects=False, verify=False)",
            ),
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
                    "scripts.audit_v24240_anthropic_server_search_single_attempt.ROOT",
                    root,
                ),
                mock.patch(
                    "scripts.audit_v24240_anthropic_server_search_single_attempt.OUTPUT",
                    Path("results/receipt.json"),
                ),
                mock.patch(
                    "scripts.audit_v24240_anthropic_server_search_single_attempt.os.open",
                    wraps=os.open,
                ) as open_mock,
                mock.patch(
                    "scripts.audit_v24240_anthropic_server_search_single_attempt.os.fsync",
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
