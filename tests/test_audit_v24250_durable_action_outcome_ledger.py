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

from scripts.audit_v24250_durable_action_outcome_ledger import (  # noqa: E402
    ROOT,
    audit_python_source,
    build_audit,
    payload_sha256,
    publish_new,
)


class AuditV24250DurableActionOutcomeLedgerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = build_audit(ROOT, created_at_unix=1)

    def test_receipt_is_sealed_label_blind_candidate_not_production(self) -> None:
        value = self.value
        unsigned = dict(value)
        seal = unsigned.pop("audit_payload_sha256")
        self.assertEqual(seal, payload_sha256(unsigned))
        self.assertTrue(value["label_blind_runtime"])
        self.assertTrue(value["candidate_durable_action_outcome_ledger"])
        self.assertTrue(value["audit_valid"])
        self.assertTrue(
            value["claims"]["candidate_durable_success_outcome_ledger_available"]
        )
        self.assertFalse(value["claims"]["active_runtime_wrapper_available"])
        self.assertFalse(value["claims"]["benchmark_score_available"])
        self.assertFalse(value["claims"]["sota"])

    def test_parent_receipt_and_four_control_files_are_exact(self) -> None:
        parent = self.value["parent_receipt"]
        self.assertEqual(
            parent["file_sha256"],
            "5394bb6ec6c672b718d403d769a4f2c2343d36cc018ebac46bd20c035cac9daa",
        )
        self.assertEqual(
            parent["payload_sha256"],
            "8eeae6be20853d3ec8551164f906bbcd72e00db97ac55a0ec12ce2dc121bd57a",
        )
        self.assertEqual(
            parent["v24249_control_manifest_sha256"],
            "0d282b27dacbd84836525a2c319991e09600eda9504be35294e417333e5e6a19",
        )
        self.assertEqual(parent["v24249_control_files_rehashed"], 4)
        self.assertTrue(parent["v24249_candidate_parent_validated"])

    def test_fake_replay_binds_success_and_quarantines_uncertainty(self) -> None:
        replay = self.value["fake_outcome_ledger_replay"]
        self.assertTrue(
            replay["local_tempdir_virtual_time_and_injected_fake_transports_only"]
        )
        self.assertFalse(
            replay["network_socket_or_real_model_search_fetch_api_called"]
        )
        self.assertEqual(replay["durable_success_outcome_count_before_fault"], 3)
        self.assertEqual(replay["success_ordinals_before_fault"], [1, 2, 3])
        self.assertTrue(replay["claim_prefix_replayed_for_all_success_outcomes"])
        self.assertEqual(replay["model_post_count_before_fault"], 1)
        self.assertEqual(replay["search_post_count"], 1)
        self.assertEqual(replay["fetch_pool_count"], 1)
        self.assertEqual(replay["fetch_urlopen_count"], 1)
        self.assertTrue(
            replay["successful_effect_then_outcome_publish_fault_observed"]
        )
        self.assertEqual(replay["unresolved_claim_count_after_fault"], 1)
        self.assertTrue(replay["automatic_retry_after_uncertain_effect_rejected"])
        self.assertEqual(replay["model_post_count_after_fault_and_rejection"], 2)
        self.assertFalse(
            replay["private_prompt_query_url_page_or_json_entered_outcomes"]
        )
        self.assertFalse(
            replay[
                "public_action_ref_callback_fault_hook_resume_or_retry_parameter_present"
            ]
        )
        self.assertFalse(
            replay[
                "benchmark_question_prediction_mapping_gold_evaluator_or_score_used_for_routing"
            ]
        )

    def test_scope_is_exact_about_success_only_and_unresolved_claims(self) -> None:
        scope = self.value["scientific_scope"]
        for field in (
            "single_inflight_local_posix_effect_implemented",
            "durable_claim_before_effect_implemented",
            "durable_success_outcome_after_effect_implemented",
            "claim_to_success_outcome_durable_binding_implemented",
            "action_claim_order_equals_success_outcome_order_verified",
        ):
            self.assertTrue(scope[field], field)
        for field in (
            "automatic_retry_or_resume_implemented",
            "failure_outcome_durable_binding_implemented",
            "claimed_but_unstarted_action_recovery_implemented",
            "outcome_publication_crash_automatic_recovery_implemented",
            "caller_single_ledger_ownership_independently_verified",
            "direct_parent_registry_or_facade_bypass_globally_excluded",
            "equal_ephemeral_request_deduplication_implemented",
            "ephemeral_request_content_used_for_outcome_identity",
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
        self.assertEqual(
            static[
                "public_action_ref_callback_fault_hook_resume_or_retry_parameter_count"
            ],
            0,
        )
        self.assertEqual(static["privileged_metadata_read_count"], 0)
        self.assertEqual(
            static[
                "direct_network_environment_process_subprocess_or_dynamic_code_call_site_count"
            ],
            0,
        )
        self.assertTrue(
            static[
                "filesystem_capability_restricted_to_local_registry_and_outcome_stores"
            ]
        )

    def test_static_audit_rejects_network_privileged_and_retry_surface(self) -> None:
        canonical = (
            ROOT / "src/deepwide_agent/v24250_durable_action_outcome_ledger.py"
        ).read_text(encoding="utf-8")
        cases = (
            canonical + "\nos.getenv('TOKEN')\n",
            canonical + "\nos.system('unexpected')\n",
            canonical.replace(
                "def run_model_json(\n        self,\n        *,",
                "def run_model_json(\n        self,\n        *,\n        retry: bool,",
                1,
            ),
            canonical.replace(
                'outcome.get("benchmark_forward_or_evaluator_authorized")',
                'outcome.get("ground_truth")',
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
                    "scripts.audit_v24250_durable_action_outcome_ledger.ROOT",
                    root,
                ),
                mock.patch(
                    "scripts.audit_v24250_durable_action_outcome_ledger.OUTPUT",
                    Path("results/receipt.json"),
                ),
                mock.patch(
                    "scripts.audit_v24250_durable_action_outcome_ledger.os.open",
                    wraps=os.open,
                ) as open_mock,
                mock.patch(
                    "scripts.audit_v24250_durable_action_outcome_ledger.os.fsync",
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
