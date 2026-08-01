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

from scripts.audit_v24245_pinned_native_http_fetch import (  # noqa: E402
    ROOT,
    audit_python_source,
    build_audit,
    payload_sha256,
    publish_new,
)


class AuditV24245PinnedNativeHttpFetchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = build_audit(ROOT, created_at_unix=1)

    def test_receipt_is_sealed_label_blind_candidate_not_production(self) -> None:
        value = self.value
        unsigned = dict(value)
        seal = unsigned.pop("audit_payload_sha256")
        self.assertEqual(seal, payload_sha256(unsigned))
        self.assertTrue(value["label_blind_runtime"])
        self.assertTrue(value["candidate_runtime_adapter"])
        self.assertTrue(value["audit_valid"])
        self.assertTrue(
            value["claims"][
                "candidate_dns_to_transport_pinned_native_fetch_available"
            ]
        )
        self.assertFalse(value["claims"]["production_runtime_wrapper_available"])
        self.assertFalse(value["claims"]["single_socket_connection_attempt_attested"])
        self.assertFalse(value["claims"]["benchmark_score_available"])
        self.assertFalse(value["claims"]["sota"])

    def test_sequential_parent_and_native_fetch_dependency_are_exact(self) -> None:
        parent = self.value["sequential_parent_receipt"]
        self.assertEqual(
            parent["file_sha256"],
            "c33f9f464c9e87d68112068a593c077e0841b2836c1487c43831a240f5bebba1",
        )
        self.assertEqual(
            parent["payload_sha256"],
            "60424e494f502a29856b99e87496e47bd5adbaab82307e824fa485f9fc97373c",
        )
        self.assertEqual(
            parent["v24244_control_manifest_sha256"],
            "ead4137f4a3069b8dd6efdef71fb133645ea6efdfe6b0d55e54fec2aed8fd322",
        )
        self.assertEqual(parent["v24244_control_files_rehashed"], 4)
        self.assertTrue(parent["v24244_candidate_parent_validated"])

        dependency = self.value["native_fetch_dependency_receipt"]
        self.assertEqual(
            dependency["file_sha256"],
            "93b9752d4a0161944a6a6080c514ea684501b396f35c72e4f3a4e76c7c916b36",
        )
        self.assertEqual(
            dependency["payload_sha256"],
            "89e249bec8c76a66883dadb0931aa1f969808629ebb8b82a120d7596ed5fafde",
        )
        self.assertEqual(
            dependency["v24238_control_manifest_sha256"],
            "d343b2f5bbd67c52afb107829af852ae504566fb4271d64ca7296450fc3a0eb7",
        )
        self.assertEqual(dependency["v24238_control_files_rehashed"], 4)
        self.assertTrue(dependency["v24238_candidate_dependency_validated"])
        self.assertTrue(dependency["v24238_unpinned_gap_confirmed"])

    def test_fake_replay_pins_and_rotates_one_urlopen_per_callback(self) -> None:
        replay = self.value["fake_pinned_transport_replay"]
        self.assertTrue(replay["fake_resolver_pool_and_response_only"])
        self.assertFalse(replay["network_socket_or_real_fetch_called"])
        self.assertEqual(replay["callback_attempt_count"], 2)
        self.assertEqual(replay["resolver_call_count"], 2)
        self.assertEqual(replay["fresh_pool_count"], 2)
        self.assertEqual(replay["pool_urlopen_count"], 2)
        self.assertEqual(
            replay["pinned_address_sequence"],
            ["93.184.216.34", "93.184.216.35"],
        )
        for field in (
            "one_callback_invocation_equals_one_fresh_pool_and_one_urlopen",
            "attempt_index_address_rotation_is_canonical_and_deterministic",
            "original_host_header_preserved",
            "origin_form_target_preserved",
            "redirect_following_and_internal_retries_disabled",
            "streaming_without_preload_enabled",
            "responses_close_and_release_attempted",
            "fresh_pools_closed",
            "raw_url_or_response_not_in_receipt",
        ):
            self.assertTrue(replay[field], field)
        self.assertEqual(replay["settled_permit_count"], 1)
        self.assertEqual(replay["pending_permit_count"], 0)
        self.assertFalse(
            replay[
                "benchmark_question_prediction_mapping_gold_evaluator_or_score_read"
            ]
        )

    def test_scope_separates_closed_rebinding_window_from_unproven_claims(self) -> None:
        scope = self.value["scientific_scope"]
        for field in (
            "public_address_dns_preflight_implemented",
            "all_resolved_addresses_must_be_public",
            "dns_preflight_result_pinned_to_transport",
            "deterministic_attempt_index_address_selection_implemented",
            "original_host_header_implemented",
            "tls_original_hostname_sni_implemented",
            "tls_original_hostname_certificate_assertion_implemented",
            "urllib3_internal_retry_disabled",
            "fresh_pool_per_callback_implemented",
            "one_urlopen_per_callback_implemented",
            "system_resolver_used_by_default",
            "retained_response_byte_cap_implemented",
            "response_close_attempted",
            "response_release_attempted",
            "pool_close_attempted",
            "caller_public_nonsecret_url_required",
            "sensitive_query_key_rejection_implemented",
            "nominal_timeout_reservation_checked",
            "dns_rebinding_between_validated_resolution_and_socket_target_excluded_by_construction",
        ):
            self.assertTrue(scope[field], field)
        for field in (
            "redirect_following_implemented",
            "total_transport_response_bytes_hard_capped",
            "full_provider_response_hashed_when_truncated",
            "response_and_pool_close_success_independently_verified",
            "single_socket_connection_attempt_independently_attested",
            "provider_response_authenticity_independently_verified",
            "requests_or_environment_proxy_used",
            "arbitrary_caller_headers_accepted",
            "environment_or_keyring_credential_read_implemented",
            "request_url_directly_persisted_or_emitted",
            "url_secret_absence_independently_verified",
            "challenge_and_attempt_reference_headers_sent",
            "provider_challenge_consumption_independently_verified",
            "urllib3_timeout_is_total_wall_deadline",
            "upstream_dns_or_bgp_routing_compromise_excluded",
            "real_provider_traffic_observed",
            "active_client_or_runner_integrated",
            "dev64_gate_evaluated",
            "fresh_exact220_evaluated",
            "quality_cost_or_benchmark_effect_observed",
        ):
            self.assertFalse(scope[field], field)

    def test_only_candidate_network_capability_is_authorized(self) -> None:
        authorization = self.value["authorization"]
        self.assertTrue(authorization["candidate_single_attempt_network_call_capability"])
        for field, enabled in authorization.items():
            if field == "candidate_single_attempt_network_call_capability":
                continue
            self.assertFalse(enabled, field)

    def test_static_and_active_forward_audits_are_exact(self) -> None:
        guard = self.value["active_forward_guard"]
        self.assertTrue(
            guard["module_absent_from_guarded_clients_and_forward_entrypoints"]
        )
        self.assertTrue(
            all(count == 0 for count in guard["module_name_hit_count_by_file"].values())
        )
        static = self.value["static_capability_audit"]
        self.assertEqual(static["single_pool_urlopen_call_site_count"], 1)
        self.assertEqual(static["public_resolution_validation_call_site_count"], 1)
        self.assertEqual(static["urllib3_pool_constructor_count"], 2)
        self.assertEqual(static["original_host_header_literal_count"], 1)
        self.assertEqual(static["tls_server_hostname_keyword_count"], 1)
        self.assertEqual(static["tls_assert_hostname_keyword_count"], 1)
        self.assertEqual(static["tls_cert_required_keyword_count"], 1)
        self.assertEqual(static["redirect_or_retry_enable_call_count"], 0)
        self.assertEqual(static["privileged_metadata_read_count"], 0)

    def test_static_audit_rejects_privilege_extra_transport_and_tls_drift(self) -> None:
        canonical = (ROOT / "src/deepwide_agent/v24245_pinned_native_http_fetch.py").read_text(
            encoding="utf-8"
        )
        cases = (
            canonical.replace("redirect=False", "redirect=True", 1),
            canonical.replace("retries=False", "retries=1", 1),
            canonical.replace("server_hostname=original_hostname", "timeout=1", 1),
            canonical.replace("assert_hostname=original_hostname", "block=False", 1),
            canonical.replace("cert_reqs=ssl.CERT_REQUIRED", "block=False", 1),
            canonical.replace(
                "attempt_index = bound.get(\"attempt_index\")",
                "attempt_index = bound.get(\"ground_truth\")",
                1,
            ),
            canonical + "\nimport os\nos.getenv('TOKEN')\n",
        )
        for source in cases:
            with self.subTest():
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
                    "scripts.audit_v24245_pinned_native_http_fetch.ROOT",
                    root,
                ),
                mock.patch(
                    "scripts.audit_v24245_pinned_native_http_fetch.OUTPUT",
                    Path("results/receipt.json"),
                ),
                mock.patch(
                    "scripts.audit_v24245_pinned_native_http_fetch.os.open",
                    wraps=os.open,
                ) as open_mock,
                mock.patch(
                    "scripts.audit_v24245_pinned_native_http_fetch.os.fsync",
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
