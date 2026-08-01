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

from scripts.audit_v24253_candidate_runtime_integration import (  # noqa: E402
    ROOT,
    audit_python_source,
    build_audit,
    payload_sha256,
    publish_new,
)


class AuditV24253CandidateRuntimeIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = build_audit(ROOT, created_at_unix=1)

    def test_receipt_is_sealed_label_blind_candidate_not_production(self) -> None:
        value = self.value
        unsigned = dict(value)
        seal = unsigned.pop("audit_payload_sha256")
        self.assertEqual(seal, payload_sha256(unsigned))
        self.assertTrue(value["label_blind_runtime"])
        self.assertTrue(value["candidate_deepwide_runtime_integration"])
        self.assertTrue(value["audit_valid"])
        self.assertTrue(
            value["claims"]["candidate_deepwide_runtime_integration_available"]
        )
        self.assertFalse(value["claims"]["active_runtime_wrapper_available"])
        self.assertFalse(value["claims"]["benchmark_score_available"])
        self.assertFalse(value["claims"]["sota"])

    def test_parent_receipt_and_control_files_are_exact(self) -> None:
        parent = self.value["parent_receipt"]
        self.assertEqual(
            parent["file_sha256"],
            "f8f01f17916ce4518b7938376cc64024810911f9b9649bb9f2d0856f3f002060",
        )
        self.assertEqual(
            parent["payload_sha256"],
            "c65216f474e511a644a67cd10284025919b8da961a1abb65dc018ae844b2cfd8",
        )
        self.assertEqual(
            parent["v24252_control_manifest_sha256"],
            "a0ac4a5dcd619a8a8a23ea16db3410cc6715928291a8986d239a8c9ac8e03435",
        )
        self.assertEqual(parent["v24252_control_files_rehashed"], 4)
        self.assertTrue(parent["v24252_candidate_parent_validated"])

    def test_fake_replay_ingests_only_admitted_page_and_emits_no_secret(self) -> None:
        replay = self.value["fake_runtime_integration_replay"]
        self.assertTrue(
            replay["local_tempdirs_virtual_time_and_injected_fake_transports_only"]
        )
        self.assertFalse(
            replay["network_socket_or_real_model_search_fetch_api_called"]
        )
        self.assertTrue(replay["inherited_search_stage_consumed_candidate_package"])
        self.assertTrue(replay["one_admitted_page_persisted"])
        self.assertTrue(replay["page_source_type_is_explicit_admission"])
        self.assertTrue(
            replay["page_remains_untrusted_zero_instruction_authority"]
        )
        self.assertTrue(replay["checkpoint_package_contract_bound"])
        self.assertTrue(replay["checkpoint_integration_contract_bound"])
        self.assertTrue(replay["status_label_blind_and_launch_unauthorized"])
        self.assertFalse(replay["dev64_contract_contains_raw_ids_or_questions"])
        self.assertFalse(
            replay["credential_present_in_files_contract_or_checkpoint"]
        )
        self.assertEqual(replay["model_post_count"], 0)
        self.assertEqual(replay["search_post_count"], 1)
        self.assertEqual(replay["fetch_urlopen_count"], 1)

    def test_scope_reports_exact_remaining_limits(self) -> None:
        scope = self.value["scientific_scope"]
        for field in (
            "candidate_deepwide_runtime_constructor_implemented",
            "exact_visible_task_schema_enforced",
            "package_preflight_before_task_search_and_direct_fetch",
            "global_admission_derived_page_source_enforced",
            "checkpoint_package_source_and_integration_binding_implemented",
            "three_provider_runtime_mapping_implemented",
            "prospective_same_dev64_gate_contract_frozen",
        ):
            self.assertTrue(scope[field], field)
        for field in (
            "active_runner_constructor_patch_implemented",
            "prospective_dev64_pair_materialized",
            "official_evaluator_opened",
            "real_provider_traffic_observed",
            "dev64_gate_evaluated",
            "fresh_exact220_evaluated",
            "quality_cost_or_benchmark_effect_observed",
        ):
            self.assertFalse(scope[field], field)

    def test_static_and_active_forward_audits_are_exact(self) -> None:
        guard = self.value["active_forward_guard"]
        self.assertTrue(
            guard["module_absent_from_active_runner_launcher_and_forward_entrypoints"]
        )
        self.assertTrue(
            all(count == 0 for count in guard["module_name_hit_count_by_file"].values())
        )
        static = self.value["static_capability_audit"]
        self.assertEqual(
            static["integration_preflight_call_count_by_method"],
            {"run_task": 1, "_search_stage": 1, "_directory_fetch_stage": 1},
        )
        self.assertEqual(static["parent_deepwide_run_task_dispatch_count"], 1)
        self.assertEqual(
            static["parent_search_and_directory_fetch_dispatch_count"], 2
        )
        self.assertEqual(static["runner_search_batch_admission_validator_call_count"], 2)
        self.assertEqual(
            static["checkpoint_complete_page_validation_call_count"], 1
        )
        self.assertEqual(static["privileged_metadata_read_count"], 0)
        self.assertEqual(
            static[
                "direct_network_environment_process_subprocess_or_dynamic_code_call_site_count"
            ],
            0,
        )

    def test_static_audit_rejects_network_privileged_and_missing_preflight(self) -> None:
        canonical = (
            ROOT / "src/deepwide_agent/v24253_candidate_runtime_integration.py"
        ).read_text(encoding="utf-8")
        cases = {
            "environment": canonical + "\nos.getenv('TOKEN')\n",
            "process": canonical + "\nos.system('unexpected')\n",
            "search_preflight": canonical.replace(
                "        self._require_integration()\n        before = len(state.get(\"evidence\") or [])",
                "        before = len(state.get(\"evidence\") or [])",
                1,
            ),
            "privileged_metadata": canonical.replace(
                'opaque_id = task.get("opaque_id")',
                'opaque_id = task.get("ground_truth")',
                1,
            ),
            "checkpoint_admission": canonical.replace(
                "        self._validate_new_pages(state, before=0)\n",
                "",
                1,
            ),
        }
        for name, source in cases.items():
            self.assertNotEqual(source, canonical, name)
            with self.subTest(name=name):
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
                    "scripts.audit_v24253_candidate_runtime_integration.ROOT",
                    root,
                ),
                mock.patch(
                    "scripts.audit_v24253_candidate_runtime_integration.OUTPUT",
                    Path("results/receipt.json"),
                ),
                mock.patch(
                    "scripts.audit_v24253_candidate_runtime_integration.os.open",
                    wraps=os.open,
                ) as open_mock,
                mock.patch(
                    "scripts.audit_v24253_candidate_runtime_integration.os.fsync",
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
