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

from scripts.audit_v24247_candidate_runtime_assembly import (  # noqa: E402
    ROOT,
    audit_python_source,
    build_audit,
    payload_sha256,
    publish_new,
)


class AuditV24247CandidateRuntimeAssemblyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = build_audit(ROOT, created_at_unix=1)

    def test_receipt_is_sealed_label_blind_candidate_not_production(self) -> None:
        value = self.value
        unsigned = dict(value)
        seal = unsigned.pop("audit_payload_sha256")
        self.assertEqual(seal, payload_sha256(unsigned))
        self.assertTrue(value["label_blind_runtime"])
        self.assertTrue(value["candidate_runtime_assembly"])
        self.assertTrue(value["audit_valid"])
        self.assertTrue(
            value["claims"]["candidate_typed_runtime_assembly_available"]
        )
        self.assertFalse(value["claims"]["active_runtime_wrapper_available"])
        self.assertFalse(value["claims"]["benchmark_score_available"])
        self.assertFalse(value["claims"]["sota"])

    def test_parent_receipt_and_four_control_files_are_exact(self) -> None:
        parent = self.value["parent_receipt"]
        self.assertEqual(
            parent["file_sha256"],
            "6ba7760478ca4d1f5c5d3b7311cf013b6118c32281e02e4d86ec17f5c9d30a8d",
        )
        self.assertEqual(
            parent["payload_sha256"],
            "54330e7b0bd2b157c79381e99e1b8a3b9c483e5217d3356633123283e1c7a867",
        )
        self.assertEqual(
            parent["v24246_control_manifest_sha256"],
            "adccf1c2ebecea0da829f2b6f98517778d00eca229a51e45d27bf1f18b41b990",
        )
        self.assertEqual(parent["v24246_control_files_rehashed"], 4)
        self.assertTrue(parent["v24246_candidate_parent_validated"])

    def test_fake_replay_assembles_three_durable_typed_paths(self) -> None:
        replay = self.value["fake_assembly_replay"]
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
        self.assertFalse(
            replay[
                "private_prompt_query_answer_snippet_url_page_or_json_in_receipts"
            ]
        )
        self.assertTrue(replay["unknown_adapter_subclass_rejected_before_effect"])
        self.assertTrue(replay["rejection_created_no_new_journal_event"])
        self.assertFalse(replay["public_callback_or_fault_hook_parameter_present"])
        self.assertFalse(
            replay[
                "benchmark_question_prediction_mapping_gold_evaluator_or_score_used_for_routing"
            ]
        )

    def test_scope_and_authorization_are_exact(self) -> None:
        scope = self.value["scientific_scope"]
        for field in (
            "known_adapter_exact_type_enforcement_implemented",
            "known_request_exact_type_enforcement_implemented",
            "all_effects_routed_through_durable_deadline_scheduler",
            "post_settlement_typed_processing_implemented",
        ):
            self.assertTrue(scope[field], field)
        for field in (
            "caller_supplied_callback_interface_implemented",
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
        self.assertTrue(authorization["isolated_typed_provider_effect_capability"])
        for field, enabled in authorization.items():
            if field == "isolated_typed_provider_effect_capability":
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
        self.assertEqual(static["known_adapter_bind_call_site_count"], 1)
        self.assertEqual(static["exact_class_descriptor_bind_call_site_count"], 1)
        self.assertEqual(static["instance_dispatch_bind_call_site_count"], 0)
        self.assertEqual(
            static["durable_deadline_scheduler_run_effect_call_site_count"], 1
        )
        self.assertEqual(static["strict_model_json_parser_call_site_count"], 1)
        self.assertEqual(static["search_lead_projection_call_site_count"], 1)
        self.assertEqual(static["fetched_page_projection_call_site_count"], 1)
        self.assertEqual(static["public_callback_or_fault_hook_parameter_count"], 0)
        self.assertEqual(static["privileged_metadata_read_count"], 0)

    def test_static_audit_rejects_expansive_or_instance_dispatch_mutations(self) -> None:
        canonical = (
            ROOT / "src/deepwide_agent/v24247_candidate_runtime_assembly.py"
        ).read_text(encoding="utf-8")
        cases = (
            canonical + "\nimport os\nos.getenv('TOKEN')\n",
            canonical + "\nopen('unexpected')\n",
            canonical.replace(
                "type(adapter).bind(adapter, request, meter_contract=meter)",
                "adapter.bind(request, meter_contract=meter)",
                1,
            ),
            canonical.replace(
                "return self._scheduler.run_effect(",
                "return RetryDeadlineExecutionResult(",
                1,
            ),
            canonical.replace(
                'receipt.get("benchmark_or_evaluator_metadata_used_for_routing")',
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
                    "scripts.audit_v24247_candidate_runtime_assembly.ROOT",
                    root,
                ),
                mock.patch(
                    "scripts.audit_v24247_candidate_runtime_assembly.OUTPUT",
                    Path("results/receipt.json"),
                ),
                mock.patch(
                    "scripts.audit_v24247_candidate_runtime_assembly.os.open",
                    wraps=os.open,
                ) as open_mock,
                mock.patch(
                    "scripts.audit_v24247_candidate_runtime_assembly.os.fsync",
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
