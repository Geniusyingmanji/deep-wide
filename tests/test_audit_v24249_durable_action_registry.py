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

from scripts.audit_v24249_durable_action_registry import (  # noqa: E402
    ROOT,
    audit_python_source,
    build_audit,
    payload_sha256,
    publish_new,
)


class AuditV24249DurableActionRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = build_audit(ROOT, created_at_unix=1)

    def test_receipt_is_sealed_label_blind_candidate_not_production(self) -> None:
        value = self.value
        unsigned = dict(value)
        seal = unsigned.pop("audit_payload_sha256")
        self.assertEqual(seal, payload_sha256(unsigned))
        self.assertTrue(value["label_blind_runtime"])
        self.assertTrue(value["candidate_durable_action_registry"])
        self.assertTrue(value["audit_valid"])
        self.assertTrue(
            value["claims"]["candidate_durable_action_registry_available"]
        )
        self.assertFalse(value["claims"]["active_runtime_wrapper_available"])
        self.assertFalse(value["claims"]["benchmark_score_available"])
        self.assertFalse(value["claims"]["sota"])

    def test_parent_receipt_and_four_control_files_are_exact(self) -> None:
        parent = self.value["parent_receipt"]
        self.assertEqual(
            parent["file_sha256"],
            "ff49c36b7c0b1f8e555538b6d50836184c3e5831b0c3d78c57c04e0c87154e55",
        )
        self.assertEqual(
            parent["payload_sha256"],
            "b8113b8f95618aee80eacf7fa5da315ada2d4f12d3f0d9690aadb79e24b63690",
        )
        self.assertEqual(
            parent["v24248_control_manifest_sha256"],
            "c06f696efa2a5187fc437818f42129835b63f593bca53b2d95585105baa7a5cb",
        )
        self.assertEqual(parent["v24248_control_files_rehashed"], 4)
        self.assertTrue(parent["v24248_candidate_parent_validated"])

    def test_fake_replay_is_durable_content_free_and_no_network(self) -> None:
        replay = self.value["fake_registry_replay"]
        self.assertTrue(
            replay["local_tempdir_virtual_time_and_injected_fake_transports_only"]
        )
        self.assertFalse(
            replay["network_socket_or_real_model_search_fetch_api_called"]
        )
        self.assertEqual(replay["allocated_action_count"], 4)
        self.assertEqual(replay["allocated_ordinals"], [1, 2, 3, 4])
        self.assertEqual(
            replay["allocated_operation_kinds"],
            ["model_json", "search_leads", "fetched_page", "model_json"],
        )
        self.assertTrue(replay["claim_prefix_replayed_for_all_receipts"])
        self.assertEqual(replay["model_post_count"], 2)
        self.assertEqual(replay["search_post_count"], 1)
        self.assertEqual(replay["fetch_pool_count"], 1)
        self.assertEqual(replay["fetch_urlopen_count"], 1)
        self.assertTrue(replay["equal_model_requests_received_distinct_actions"])
        self.assertFalse(replay["equal_ephemeral_request_deduplication_claimed"])
        self.assertTrue(replay["separate_registry_received_distinct_random_domain"])
        self.assertFalse(
            replay["caller_single_registry_ownership_independently_verified"]
        )
        self.assertFalse(
            replay["private_prompt_query_url_page_or_json_entered_receipts"]
        )
        self.assertFalse(
            replay["public_action_ref_callback_or_fault_hook_parameter_present"]
        )
        self.assertFalse(
            replay[
                "benchmark_question_prediction_mapping_gold_evaluator_or_score_used_for_routing"
            ]
        )

    def test_scope_is_precise_about_unresolved_crash_and_bypass_risks(self) -> None:
        scope = self.value["scientific_scope"]
        for field in (
            "os_csprng_instance_domain_implemented",
            "fixed_operation_stage_refs_implemented",
            "global_monotonic_action_ordinal_implemented",
            "durable_claim_before_facade_effect_implemented",
            "local_posix_advisory_lock_implemented",
            "file_and_directory_fsync_implemented",
        ):
            self.assertTrue(scope[field], field)
        for field in (
            "caller_supplied_action_ref_accepted",
            "ephemeral_request_content_used_for_action_identity",
            "equal_ephemeral_request_deduplication_implemented",
            "caller_single_registry_ownership_independently_verified",
            "direct_parent_facade_bypass_globally_excluded",
            "action_claim_order_equals_effect_completion_order_verified",
            "claim_to_effect_outcome_durable_binding_implemented",
            "claimed_but_unstarted_action_recovery_implemented",
            "initialization_crash_automatic_recovery_implemented",
            "adapter_code_identity_independently_attested",
            "malicious_same_user_resealing_excluded",
            "network_or_distributed_filesystem_semantics_proven",
            "search_leads_or_page_text_active_evidence_eligibility_granted",
            "real_provider_traffic_observed",
            "active_client_or_runner_integrated",
            "dev64_gate_evaluated",
            "fresh_exact220_evaluated",
            "quality_cost_or_benchmark_effect_observed",
        ):
            self.assertFalse(scope[field], field)

    def test_static_and_active_forward_audits_are_exact(self) -> None:
        guard = self.value["active_forward_guard"]
        self.assertTrue(
            guard["module_absent_from_guarded_clients_and_forward_entrypoints"]
        )
        self.assertTrue(
            all(count == 0 for count in guard["module_name_hit_count_by_file"].values())
        )
        static = self.value["static_capability_audit"]
        self.assertEqual(
            static["facade_dispatch_call_site_count_by_method"],
            {"run_model_json": 1, "run_search_leads": 1, "run_fetched_page": 1},
        )
        self.assertEqual(static["caller_action_ref_public_parameter_count"], 0)
        self.assertEqual(static["public_callback_or_fault_hook_parameter_count"], 0)
        self.assertEqual(static["privileged_metadata_read_count"], 0)
        self.assertEqual(
            static[
                "direct_network_environment_process_subprocess_or_dynamic_code_call_site_count"
            ],
            0,
        )
        self.assertTrue(
            static["filesystem_capability_restricted_to_local_registry_store"]
        )

    def test_static_audit_rejects_network_privileged_and_public_action_ref(self) -> None:
        canonical = (
            ROOT / "src/deepwide_agent/v24249_durable_action_registry.py"
        ).read_text(encoding="utf-8")
        cases = (
            canonical + "\nos.getenv('TOKEN')\n",
            canonical + "\nos.system('unexpected')\n",
            canonical.replace(
                "def run_model_json(\n        self,\n        *,",
                "def run_model_json(\n        self,\n        *,\n        action_ref: object,",
                1,
            ),
            canonical.replace(
                'receipt.get("benchmark_forward_or_evaluator_authorized")',
                'receipt.get("ground_truth")',
                1,
            ),
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
                    "scripts.audit_v24249_durable_action_registry.ROOT",
                    root,
                ),
                mock.patch(
                    "scripts.audit_v24249_durable_action_registry.OUTPUT",
                    Path("results/receipt.json"),
                ),
                mock.patch(
                    "scripts.audit_v24249_durable_action_registry.os.open",
                    wraps=os.open,
                ) as open_mock,
                mock.patch(
                    "scripts.audit_v24249_durable_action_registry.os.fsync",
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
