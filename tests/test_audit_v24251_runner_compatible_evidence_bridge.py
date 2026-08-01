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

from scripts.audit_v24251_runner_compatible_evidence_bridge import (  # noqa: E402
    ROOT,
    audit_python_source,
    build_audit,
    payload_sha256,
    publish_new,
)


class AuditV24251RunnerCompatibleEvidenceBridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = build_audit(ROOT, created_at_unix=1)

    def test_receipt_is_sealed_label_blind_candidate_not_production(self) -> None:
        value = self.value
        unsigned = dict(value)
        seal = unsigned.pop("audit_payload_sha256")
        self.assertEqual(seal, payload_sha256(unsigned))
        self.assertTrue(value["label_blind_runtime"])
        self.assertTrue(value["candidate_runner_compatible_evidence_bridge"])
        self.assertTrue(value["audit_valid"])
        self.assertTrue(
            value["claims"]["candidate_runner_compatible_bridge_available"]
        )
        self.assertTrue(
            value["claims"][
                "candidate_explicit_page_evidence_admission_available"
            ]
        )
        self.assertFalse(value["claims"]["active_runtime_wrapper_available"])
        self.assertFalse(value["claims"]["benchmark_score_available"])
        self.assertFalse(value["claims"]["sota"])

    def test_parent_receipt_and_four_control_files_are_exact(self) -> None:
        parent = self.value["parent_receipt"]
        self.assertEqual(
            parent["file_sha256"],
            "d591c0f8f48e8847f17a3169c6fe82f478c3ffbf012abd32b1bf827c29c2127c",
        )
        self.assertEqual(
            parent["payload_sha256"],
            "6745a5edf1135ed9feeb853eb07117fa8beacc744934637882762db399c10a77",
        )
        self.assertEqual(
            parent["v24250_control_manifest_sha256"],
            "b374b071b059c7653f25698ab440a4aa3b7a2587516c9866ed699580df2580d7",
        )
        self.assertEqual(parent["v24250_control_files_rehashed"], 4)
        self.assertTrue(parent["v24250_candidate_parent_validated"])

    def test_fake_replay_admits_page_and_rejects_unknown_direct_fetch(self) -> None:
        replay = self.value["fake_runner_bridge_replay"]
        self.assertTrue(
            replay["local_tempdir_virtual_time_and_injected_fake_transports_only"]
        )
        self.assertFalse(
            replay["network_socket_or_real_model_search_fetch_api_called"]
        )
        self.assertTrue(replay["model_value_exact_object"])
        self.assertTrue(replay["model_trace_runner_cost_compatible"])
        self.assertTrue(replay["search_batch_runner_shape_validated"])
        self.assertEqual(replay["legacy_ingestion_produced_page_count"], 1)
        self.assertTrue(replay["injection_like_text_retained_as_untrusted_data"])
        self.assertFalse(replay["search_provider_answer_or_snippet_returned"])
        self.assertTrue(replay["unknown_direct_fetch_rejected_before_new_claim"])
        self.assertEqual(replay["durable_success_outcome_count"], 3)
        self.assertEqual(replay["model_post_count"], 1)
        self.assertEqual(replay["search_post_count"], 1)
        self.assertEqual(replay["fetch_pool_count"], 1)
        self.assertEqual(replay["fetch_urlopen_count"], 1)
        self.assertFalse(
            replay["private_prompt_query_url_page_or_json_entered_outcomes"]
        )
        self.assertFalse(
            replay[
                "benchmark_question_prediction_mapping_gold_evaluator_or_score_used_for_routing"
            ]
        )

    def test_scope_distinguishes_admission_from_truth_or_injection_safety(self) -> None:
        scope = self.value["scientific_scope"]
        for field in (
            "runner_model_complete_json_surface_implemented",
            "runner_search_many_and_fetch_urls_surfaces_implemented",
            "explicit_page_evidence_ingress_admission_implemented",
            "runner_result_content_hash_binding_implemented",
            "url_or_page_text_hashed_in_admission",
            "admitted_page_text_returned_as_active_evidence",
            "admitted_page_text_is_untrusted_data",
        ):
            self.assertTrue(scope[field], field)
        for field in (
            "admitted_page_text_instruction_authority",
            "raw_url_or_page_text_persisted_by_bridge",
            "schema_resealing_without_secret_cryptographically_excluded",
            "search_leads_returned_as_active_evidence",
            "search_provider_prose_returned",
            "url_content_type_to_response_cryptographic_binding_proven",
            "prompt_injection_safety_independently_verified",
            "source_truth_relevance_or_independence_verified",
            "global_legacy_ingestion_enforcement_implemented",
            "failure_usage_accounting_exact",
            "parallel_provider_execution_implemented",
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
            static["parent_ledger_dispatch_call_site_count_by_method"],
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
                "direct_network_environment_file_process_subprocess_or_dynamic_code_call_site_count"
            ],
            0,
        )
        self.assertTrue(
            static["legacy_raw_content_requires_explicit_admission_validator"]
        )

    def test_static_audit_rejects_network_privileged_and_retry_surface(self) -> None:
        canonical = (
            ROOT
            / "src/deepwide_agent/v24251_runner_compatible_evidence_bridge.py"
        ).read_text(encoding="utf-8")
        cases = (
            canonical + "\nos.getenv('TOKEN')\n",
            canonical + "\nos.system('unexpected')\n",
            canonical.replace(
                "def complete_json(\n        self,\n        system: str,",
                "def complete_json(\n        self,\n        retry: bool,\n        system: str,",
                1,
            ),
            canonical.replace(
                'admission.get("benchmark_or_evaluator_metadata_used_for_routing")',
                'admission.get("ground_truth")',
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
                    "scripts.audit_v24251_runner_compatible_evidence_bridge.ROOT",
                    root,
                ),
                mock.patch(
                    "scripts.audit_v24251_runner_compatible_evidence_bridge.OUTPUT",
                    Path("results/receipt.json"),
                ),
                mock.patch(
                    "scripts.audit_v24251_runner_compatible_evidence_bridge.os.open",
                    wraps=os.open,
                ) as open_mock,
                mock.patch(
                    "scripts.audit_v24251_runner_compatible_evidence_bridge.os.fsync",
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
