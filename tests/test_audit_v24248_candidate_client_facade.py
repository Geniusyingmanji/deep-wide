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

from scripts.audit_v24248_candidate_client_facade import (  # noqa: E402
    ROOT,
    audit_python_source,
    build_audit,
    payload_sha256,
    publish_new,
)


class AuditV24248CandidateClientFacadeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = build_audit(ROOT, created_at_unix=1)

    def test_receipt_is_sealed_label_blind_candidate_not_production(self) -> None:
        value = self.value
        unsigned = dict(value)
        seal = unsigned.pop("audit_payload_sha256")
        self.assertEqual(seal, payload_sha256(unsigned))
        self.assertTrue(value["label_blind_runtime"])
        self.assertTrue(value["candidate_client_facade"])
        self.assertTrue(value["audit_valid"])
        self.assertTrue(
            value["claims"]["candidate_content_free_action_ref_facade_available"]
        )
        self.assertFalse(value["claims"]["legacy_runtime_drop_in_client_available"])
        self.assertFalse(value["claims"]["active_runtime_wrapper_available"])
        self.assertFalse(value["claims"]["active_evidence_admission_available"])
        self.assertFalse(value["claims"]["benchmark_score_available"])
        self.assertFalse(value["claims"]["sota"])

    def test_parent_receipt_and_four_control_files_are_exact(self) -> None:
        parent = self.value["parent_receipt"]
        self.assertEqual(
            parent["file_sha256"],
            "8c627b811be2d1b769dfe93d27891d90555b25c8a7c6077d372842aa4118146b",
        )
        self.assertEqual(
            parent["payload_sha256"],
            "c27ee157cab65f2e5d5ca426b6d3ce21d66e646eadd9bd83890423e7da8dc70c",
        )
        self.assertEqual(
            parent["v24247_control_manifest_sha256"],
            "e2d7dfe1c50e36685d4dcd4d5b1bf2f6420b84bafec0e5be45852d8da4bc9c19",
        )
        self.assertEqual(parent["v24247_control_files_rehashed"], 4)
        self.assertTrue(parent["v24247_candidate_parent_validated"])

    def test_fake_replay_uses_content_free_refs_and_quarantined_values(self) -> None:
        replay = self.value["fake_facade_replay"]
        self.assertTrue(
            replay["local_tempdir_virtual_time_and_injected_fake_transports_only"]
        )
        self.assertFalse(
            replay["network_socket_or_real_model_search_fetch_api_called"]
        )
        self.assertEqual(replay["durable_settled_effect_count"], 3)
        self.assertEqual(replay["model_post_count"], 1)
        self.assertEqual(replay["search_post_count"], 1)
        self.assertEqual(replay["fetch_pool_count"], 1)
        self.assertEqual(replay["fetch_urlopen_count"], 1)
        self.assertTrue(replay["model_json_ephemeral_value_returned"])
        self.assertTrue(replay["search_untrusted_lead_ephemeral_value_returned"])
        self.assertTrue(replay["page_untrusted_text_ephemeral_value_returned"])
        self.assertFalse(replay["search_or_page_active_evidence_eligibility_granted"])
        self.assertFalse(
            replay[
                "private_prompt_query_answer_snippet_url_page_or_json_in_receipts"
            ]
        )
        self.assertTrue(
            replay[
                "same_action_ref_different_prompt_replay_rejected_before_second_post"
            ]
        )
        self.assertEqual(replay["model_post_count_after_replay_rejection"], 1)
        self.assertFalse(replay["public_callback_or_fault_hook_parameter_present"])
        self.assertFalse(
            replay[
                "legacy_complete_json_search_many_or_fetch_urls_surface_present"
            ]
        )
        self.assertFalse(
            replay[
                "benchmark_question_prediction_mapping_gold_evaluator_or_score_used_for_routing"
            ]
        )

    def test_scope_and_authorization_are_exact(self) -> None:
        scope = self.value["scientific_scope"]
        for field in (
            "content_free_action_ref_derivation_implemented",
            "frozen_provider_meter_and_deadline_contracts_implemented",
            "exact_adapter_and_assembly_type_enforcement_implemented",
        ):
            self.assertTrue(scope[field], field)
        for field in (
            "legacy_runtime_client_surface_implemented",
            "search_leads_or_page_text_active_evidence_eligibility_granted",
            "caller_action_ref_semantic_independence_verified",
            "adapter_code_identity_independently_attested",
            "schema_resealing_without_secret_cryptographically_excluded",
            "real_provider_traffic_observed",
            "active_client_or_runner_integrated",
            "dev64_gate_evaluated",
            "fresh_exact220_evaluated",
            "quality_cost_or_benchmark_effect_observed",
        ):
            self.assertFalse(scope[field], field)
        authorization = self.value["authorization"]
        self.assertTrue(
            authorization["isolated_content_free_action_ref_facade_capability"]
        )
        for field, enabled in authorization.items():
            if field == "isolated_content_free_action_ref_facade_capability":
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
        self.assertEqual(
            static["candidate_assembly_dispatch_call_site_count_by_method"],
            {"run_model_json": 1, "run_search_leads": 1, "run_fetched_page": 1},
        )
        self.assertEqual(
            static["invocation_derivation_forbidden_ephemeral_name_count"], 0
        )
        self.assertEqual(static["public_callback_or_fault_hook_parameter_count"], 0)
        self.assertEqual(static["privileged_metadata_read_count"], 0)
        self.assertEqual(
            static[
                "direct_network_environment_file_process_subprocess_or_dynamic_code_call_site_count"
            ],
            0,
        )

    def test_static_audit_rejects_expansive_privileged_and_content_derived_ids(self) -> None:
        canonical = (
            ROOT / "src/deepwide_agent/v24248_candidate_client_facade.py"
        ).read_text(encoding="utf-8")
        cases = (
            canonical + "\nimport os\nos.getenv('TOKEN')\n",
            canonical + "\nopen('unexpected')\n",
            canonical.replace(
                '"ephemeral_content_used": False,',
                '"ephemeral_content_used": False, "query": query,',
                1,
            ),
            canonical.replace(
                'receipt.get("benchmark_or_evaluator_metadata_used_for_routing")',
                'receipt.get("ground_truth")',
                1,
            ),
            canonical.replace(
                ").run_search_leads(",
                ").run_model_json(",
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
                    "scripts.audit_v24248_candidate_client_facade.ROOT",
                    root,
                ),
                mock.patch(
                    "scripts.audit_v24248_candidate_client_facade.OUTPUT",
                    Path("results/receipt.json"),
                ),
                mock.patch(
                    "scripts.audit_v24248_candidate_client_facade.os.open",
                    wraps=os.open,
                ) as open_mock,
                mock.patch(
                    "scripts.audit_v24248_candidate_client_facade.os.fsync",
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
