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

from scripts.audit_v24246_search_page_projection import (  # noqa: E402
    ROOT,
    audit_python_source,
    build_audit,
    payload_sha256,
    publish_new,
)


class AuditV24246SearchPageProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = build_audit(ROOT, created_at_unix=1)

    def test_receipt_is_sealed_label_blind_candidate_not_production(self) -> None:
        value = self.value
        unsigned = dict(value)
        seal = unsigned.pop("audit_payload_sha256")
        self.assertEqual(seal, payload_sha256(unsigned))
        self.assertTrue(value["label_blind_runtime"])
        self.assertTrue(value["candidate_runtime_projection_boundary"])
        self.assertTrue(value["audit_valid"])
        self.assertTrue(
            value["claims"]["candidate_search_lead_and_page_projection_available"]
        )
        self.assertFalse(value["claims"]["search_leads_are_verified_page_evidence"])
        self.assertFalse(value["claims"]["page_text_is_prompt_injection_safe"])
        self.assertFalse(value["claims"]["production_runtime_wrapper_available"])
        self.assertFalse(value["claims"]["benchmark_score_available"])
        self.assertFalse(value["claims"]["sota"])

    def test_parent_receipt_and_four_control_files_are_exact(self) -> None:
        parent = self.value["parent_receipt"]
        self.assertEqual(
            parent["file_sha256"],
            "a444525614fd6d0f6a03f63d60a6633e44cd007981e12e15ab67a407b46d0c48",
        )
        self.assertEqual(
            parent["payload_sha256"],
            "f63659626df1a2d1bf24e3bdb7c82ddbef3a081d1d9eb4730b5480167c40ad3a",
        )
        self.assertEqual(
            parent["v24245_control_manifest_sha256"],
            "53f342792182e8de150f5e8366148bac3c1badac4dfbb2f410209c70461a37d4",
        )
        self.assertEqual(parent["v24245_control_files_rehashed"], 4)
        self.assertTrue(parent["v24245_candidate_parent_validated"])

    def test_fake_replay_projects_only_leads_and_untrusted_page_text(self) -> None:
        replay = self.value["fake_projection_replay"]
        self.assertTrue(
            replay["local_tempdir_virtual_time_and_ephemeral_synthetic_values_only"]
        )
        self.assertFalse(replay["network_socket_model_search_fetch_or_api_called"])
        self.assertEqual(replay["durable_parent_settlements_before_projection"], 2)
        self.assertEqual(replay["search_projected_lead_count"], 1)
        self.assertTrue(replay["provider_answer_and_snippet_absent_from_projection"])
        self.assertTrue(replay["page_script_content_absent_from_projection"])
        self.assertTrue(
            replay["page_text_marked_untrusted_zero_instruction_authority"]
        )
        self.assertFalse(replay["page_active_evidence_eligibility_granted"])
        self.assertTrue(replay["fetch_body_hash_and_length_matches_parent_attempt"])
        self.assertFalse(
            replay["fetch_url_content_type_binding_independently_verified"]
        )
        self.assertTrue(replay["private_literal_sensitive_query_case_rejected"])
        self.assertTrue(replay["projection_rejection_created_no_new_journal_event"])
        self.assertFalse(replay["raw_provider_or_page_content_in_receipts"])

    def test_scope_separates_mechanical_projection_from_semantic_safety(self) -> None:
        scope = self.value["scientific_scope"]
        for field in (
            "post_durable_settlement_projection_implemented",
            "search_provider_answer_snippet_query_score_and_metadata_discarded",
            "fetch_body_bytes_to_parent_response_binding_independently_verified",
        ):
            self.assertTrue(scope[field], field)
        for field in (
            "search_leads_are_page_evidence",
            "fetch_url_content_type_to_parent_response_binding_independently_verified",
            "search_typed_value_to_parent_response_binding_independently_verified",
            "untrusted_page_text_instruction_authority",
            "active_evidence_eligibility_granted",
            "prompt_injection_safety_independently_verified",
            "source_truth_relevance_or_independence_verified",
            "internal_repair_or_provider_effect_implemented",
            "schema_resealing_without_secret_cryptographically_excluded",
            "real_provider_traffic_observed",
            "active_client_or_runner_integrated",
            "dev64_gate_evaluated",
            "fresh_exact220_evaluated",
            "quality_cost_or_benchmark_effect_observed",
        ):
            self.assertFalse(scope[field], field)

    def test_only_pure_projection_capability_is_authorized(self) -> None:
        authorization = self.value["authorization"]
        self.assertTrue(authorization["pure_ephemeral_projection_capability"])
        for field, enabled in authorization.items():
            if field == "pure_ephemeral_projection_capability":
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
        self.assertEqual(static["scheduler_receipt_validation_call_site_count"], 1)
        self.assertEqual(static["fetch_body_sha256_call_site_count"], 1)
        self.assertEqual(static["bounded_html_parser_subclass_count"], 1)
        self.assertEqual(static["privileged_metadata_read_count"], 0)
        self.assertEqual(
            static[
                "repair_model_search_fetch_network_environment_file_process_or_dynamic_code_call_site_count"
            ],
            0,
        )

    def test_static_audit_rejects_expansive_capability_and_missing_binding(self) -> None:
        canonical = (
            ROOT / "src/deepwide_agent/v24246_search_page_projection.py"
        ).read_text(encoding="utf-8")
        cases = (
            canonical + "\nimport os\nos.getenv('TOKEN')\n",
            canonical + "\nimport requests\nrequests.get('https://example.test')\n",
            canonical.replace(
                "validate_retry_deadline_execution_receipt(scheduler)",
                "pass",
                1,
            ),
            canonical.replace(
                "hashlib.sha256(fetch.body).hexdigest()",
                "'0' * 64",
                1,
            ),
            canonical.replace(
                'parent.get("attempt_count") < 1',
                'parent.get("ground_truth") < 1',
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
                    "scripts.audit_v24246_search_page_projection.ROOT",
                    root,
                ),
                mock.patch(
                    "scripts.audit_v24246_search_page_projection.OUTPUT",
                    Path("results/receipt.json"),
                ),
                mock.patch(
                    "scripts.audit_v24246_search_page_projection.os.open",
                    wraps=os.open,
                ) as open_mock,
                mock.patch(
                    "scripts.audit_v24246_search_page_projection.os.fsync",
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
