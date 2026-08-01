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

from scripts.audit_v24252_candidate_runner_package import (  # noqa: E402
    ROOT,
    audit_python_source,
    build_audit,
    payload_sha256,
    publish_new,
)


class AuditV24252CandidateRunnerPackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = build_audit(ROOT, created_at_unix=1)

    def test_receipt_is_sealed_label_blind_candidate_not_production(self) -> None:
        value = self.value
        unsigned = dict(value)
        seal = unsigned.pop("audit_payload_sha256")
        self.assertEqual(seal, payload_sha256(unsigned))
        self.assertTrue(value["label_blind_runtime"])
        self.assertTrue(value["candidate_restartable_runner_package"])
        self.assertTrue(value["audit_valid"])
        self.assertTrue(
            value["claims"]["candidate_restartable_runner_package_available"]
        )
        self.assertFalse(value["claims"]["active_runtime_wrapper_available"])
        self.assertFalse(value["claims"]["benchmark_score_available"])
        self.assertFalse(value["claims"]["sota"])

    def test_parent_receipt_and_four_control_files_are_exact(self) -> None:
        parent = self.value["parent_receipt"]
        self.assertEqual(
            parent["file_sha256"],
            "163fdd612b6213100599cd9de693c0328d766203f0d0e2d50e8644d26795eef2",
        )
        self.assertEqual(
            parent["payload_sha256"],
            "091138791de18affe6f6e7291ae89b206de0dc0930834082987e402149bccea3",
        )
        self.assertEqual(
            parent["v24251_control_manifest_sha256"],
            "027b34d48a35b396c6374f17ff10be3ee33fd3b333f6b2f86695d759b05210fb",
        )
        self.assertEqual(parent["v24251_control_files_rehashed"], 4)
        self.assertTrue(parent["v24251_candidate_parent_validated"])

    def test_fake_replay_restarts_and_preserves_ordinal_without_credentials(self) -> None:
        replay = self.value["fake_runner_package_replay"]
        self.assertTrue(
            replay["local_tempdir_virtual_time_and_injected_fake_transports_only"]
        )
        self.assertFalse(
            replay["network_socket_or_real_model_search_fetch_api_called"]
        )
        self.assertTrue(replay["model_value_exact_object"])
        self.assertTrue(replay["model_trace_success"])
        self.assertTrue(replay["initialize_then_open_restart_succeeded"])
        self.assertEqual(replay["durable_action_ordinal_before_restart"], 1)
        self.assertEqual(replay["durable_action_ordinal_after_restart"], 3)
        self.assertEqual(replay["durable_success_outcome_count_after_restart"], 3)
        self.assertEqual(replay["legacy_ingestion_produced_page_count"], 1)
        self.assertTrue(replay["injection_like_text_retained_as_untrusted_data"])
        self.assertFalse(replay["search_provider_prose_returned"])
        self.assertFalse(replay["credential_present_in_package_files"])
        self.assertFalse(replay["credential_present_in_contract_or_receipts"])
        self.assertFalse(
            replay["private_prompt_query_url_page_or_json_entered_outcomes"]
        )
        self.assertEqual(replay["model_post_count"], 1)
        self.assertEqual(replay["search_post_count"], 1)
        self.assertEqual(replay["fetch_pool_count"], 1)
        self.assertEqual(replay["fetch_urlopen_count"], 1)

    def test_scope_reports_exact_remaining_limits(self) -> None:
        scope = self.value["scientific_scope"]
        for field in (
            "single_pristine_package_root_implemented",
            "create_exclusive_initial_and_ready_receipts_implemented",
            "restartable_parent_reconstruction_implemented",
            "source_manifest_revalidated_before_each_runner_operation",
            "credentials_are_ephemeral_runtime_arguments",
        ):
            self.assertTrue(scope[field], field)
        for field in (
            "intra_operation_source_to_effect_atomicity_proven",
            "credential_persisted_hashed_or_emitted",
            "loaded_code_identity_independently_attested",
            "direct_parent_chain_bypass_globally_excluded",
            "malicious_same_user_resealing_excluded",
            "network_or_distributed_filesystem_semantics_proven",
            "real_provider_traffic_observed",
            "active_client_or_runner_integrated",
            "dev64_gate_evaluated",
            "fresh_exact220_evaluated",
            "quality_cost_or_benchmark_effect_observed",
        ):
            self.assertFalse(scope[field], field)
        self.assertTrue(scope["credential_retained_in_adapter_memory"])

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
            static["runner_operation_preflight_call_count_by_method"],
            {"complete_json": 1, "search_many": 1, "search": 1, "fetch_urls": 1},
        )
        self.assertEqual(static["privileged_metadata_read_count"], 0)
        self.assertEqual(
            static[
                "direct_network_environment_process_subprocess_or_dynamic_code_call_site_count"
            ],
            0,
        )
        self.assertEqual(
            static["credential_canonicalization_hash_or_persistence_call_site_count"],
            0,
        )

    def test_static_audit_rejects_network_privileged_and_missing_preflight(self) -> None:
        canonical = (
            ROOT / "src/deepwide_agent/v24252_candidate_runner_package.py"
        ).read_text(encoding="utf-8")
        cases = (
            canonical + "\nos.getenv('TOKEN')\n",
            canonical + "\nos.system('unexpected')\n",
            canonical.replace(
                "        self._package._require_ready()\n        return self._inner.complete_json(",
                "        return self._inner.complete_json(",
                1,
            ),
            canonical.replace(
                'contract.get("benchmark_or_evaluator_metadata_used_for_routing")',
                'contract.get("ground_truth")',
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
                    "scripts.audit_v24252_candidate_runner_package.ROOT",
                    root,
                ),
                mock.patch(
                    "scripts.audit_v24252_candidate_runner_package.OUTPUT",
                    Path("results/receipt.json"),
                ),
                mock.patch(
                    "scripts.audit_v24252_candidate_runner_package.os.open",
                    wraps=os.open,
                ) as open_mock,
                mock.patch(
                    "scripts.audit_v24252_candidate_runner_package.os.fsync",
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
