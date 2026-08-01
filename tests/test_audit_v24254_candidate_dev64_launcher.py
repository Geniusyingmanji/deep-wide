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

from scripts.audit_v24254_candidate_dev64_launcher import (  # noqa: E402
    ROOT,
    audit_python_source,
    build_audit,
    payload_sha256,
    publish_new,
)


class AuditV24254CandidateDev64LauncherTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = build_audit(ROOT, created_at_unix=1)

    def test_receipt_is_sealed_label_blind_preparation_not_launch(self) -> None:
        value = self.value
        unsigned = dict(value)
        seal = unsigned.pop("audit_payload_sha256")
        self.assertEqual(seal, payload_sha256(unsigned))
        self.assertTrue(value["label_blind_runtime"])
        self.assertTrue(value["candidate_dev64_launcher_preparation"])
        self.assertTrue(value["audit_valid"])
        self.assertTrue(
            value["claims"]["candidate_dev64_launcher_preparation_available"]
        )
        self.assertFalse(value["claims"]["active_launcher_available"])
        self.assertFalse(value["claims"]["dev64_result_available"])
        self.assertFalse(value["claims"]["benchmark_score_available"])
        self.assertFalse(value["claims"]["sota"])

    def test_parent_receipt_and_control_files_are_exact(self) -> None:
        parent = self.value["parent_receipt"]
        self.assertEqual(
            parent["file_sha256"],
            "9f627eb24acb2c8f71f3f6def8f151193eedb349d01989e68350e9d89bc662cb",
        )
        self.assertEqual(
            parent["payload_sha256"],
            "24893a166feabaea8a7f3e1efddccceb7244bb6688f89751e5ac1506e6ab1b16",
        )
        self.assertEqual(
            parent["v24253_control_manifest_sha256"],
            "cfd9d0ce656cc501a74a97203038d1e3591a954d660c889eb5f4169452f31d35",
        )
        self.assertEqual(parent["v24253_control_files_rehashed"], 4)
        self.assertTrue(parent["v24253_candidate_parent_validated"])
        upstream = self.value["upstream_v24216_priority_receipts"]
        self.assertEqual(len(upstream), 3)
        self.assertEqual(
            [row["sha256"] for row in upstream],
            [
                "5ad2ba72fda4dc516f922ddc33066a72054c7b082abee50dc7ac0b201a42b714",
                "fe3f285142086be6e7e64db5872bbe21b35b103d95747a76f0844bf74c2e30e5",
                "75f70b056e0e780901205e461267e5bd08089c1820d4546e2a8ac181cd491dcb",
            ],
        )

    def test_fake_replay_prepares_only_content_free_empty_roots(self) -> None:
        replay = self.value["fake_launcher_preparation_replay"]
        for field in (
            "local_tempdirs_and_synthetic_visible_inputs_only",
            "exact_visible_dev64_snapshot_validated",
            "four_disjoint_pristine_arm_roots_prepared",
            "three_create_exclusive_receipts_persisted",
            "raw_questions_absent_from_receipts",
            "raw_opaque_ids_absent_from_receipts",
            "input_hash_and_runtime_contract_bound",
            "single_contiguous_lease_required_but_not_acquired",
            "existing_v24216_to_v24220_priority_preserved",
            "outcome_before_engineering_gate_thresholds_frozen",
            "launch_evaluator_exact220_and_sota_unauthorized",
            "reopen_status_byte_equivalent",
        ):
            self.assertTrue(replay[field], field)
        for field in (
            "network_socket_real_model_search_fetch_evaluator_or_api_called",
            "subprocess_or_shared_lease_acquire_called",
            "mapping_gold_category_question_type_evaluator_or_score_read",
        ):
            self.assertFalse(replay[field], field)

    def test_scope_and_authorization_are_exact(self) -> None:
        scope = self.value["scientific_scope"]
        for field in (
            "create_exclusive_pair_preparation_implemented",
            "exact_visible_dev64_input_snapshot_implemented",
            "two_disjoint_pristine_arm_roots_implemented",
            "single_contiguous_shared_lease_contract_frozen",
            "two_arm_terminal_before_evaluator_contract_frozen",
            "failure_as_zero_contract_frozen",
            "outcome_before_engineering_gate_thresholds_frozen",
            "no_resume_or_selective_rerun_contract_frozen",
        ):
            self.assertTrue(scope[field], field)
        for field in (
            "launch_activation_implemented",
            "lease_acquisition_implemented",
            "arm_execution_implemented",
            "evaluator_execution_implemented",
            "failure_as_zero_aggregate_implemented",
            "real_provider_traffic_observed",
            "dev64_gate_evaluated",
            "fresh_exact220_evaluated",
            "quality_cost_or_benchmark_effect_observed",
        ):
            self.assertFalse(scope[field], field)
        for field, allowed in self.value["authorization"].items():
            if field == "isolated_candidate_launcher_preparation_capability":
                self.assertTrue(allowed)
            else:
                self.assertFalse(allowed, field)

    def test_static_and_active_forward_audits_are_exact(self) -> None:
        guard = self.value["active_forward_guard"]
        self.assertTrue(
            guard["module_absent_from_active_runner_launcher_and_forward_entrypoints"]
        )
        self.assertTrue(
            all(count == 0 for count in guard["module_name_hit_count_by_file"].values())
        )
        static = self.value["static_capability_audit"]
        self.assertEqual(static["visible_task_schema_validator_call_count"], 1)
        self.assertEqual(
            static["create_exclusive_package_receipt_publish_call_count"], 3
        )
        self.assertEqual(static["public_preflight_full_binding_call_count"], 1)
        self.assertEqual(static["privileged_metadata_read_count"], 0)
        self.assertEqual(
            static[
                "direct_network_environment_process_subprocess_dynamic_code_launch_lease_evaluator_or_task_call_site_count"
            ],
            0,
        )

    def test_static_audit_rejects_capability_privilege_and_missing_schema_gate(self) -> None:
        canonical = (
            ROOT / "src/deepwide_agent/v24254_candidate_dev64_launcher.py"
        ).read_text(encoding="utf-8")
        cases = {
            "environment": canonical + "\nos.getenv('TOKEN')\n",
            "environment_mapping": canonical + "\nos.environ['TOKEN']\n",
            "process": canonical + "\nos.system('unexpected')\n",
            "process_signal": canonical + "\nos.kill(123, 9)\n",
            "lease": canonical + "\nacquire_deepwide_api_lease(ROOT)\n",
            "public_launch": canonical + "\ndef launch():\n    pass\n",
            "privileged": canonical.replace(
                'task = validate_visible_runtime_task(raw)',
                'task = raw\n        task.get("ground_truth")',
                1,
            ),
            "schema_gate": canonical.replace(
                'task = validate_visible_runtime_task(raw)',
                'task = raw',
                1,
            ),
            "duplicate_key_gate": canonical.replace(
                'json.loads(line, object_pairs_hook=_reject_duplicate_object_pairs)',
                'json.loads(line)',
                1,
            ),
            "publish": canonical.replace(
                '        _publish_new(launcher_root / READY_FILE, ready)\n',
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
                    "scripts.audit_v24254_candidate_dev64_launcher.ROOT",
                    root,
                ),
                mock.patch(
                    "scripts.audit_v24254_candidate_dev64_launcher.OUTPUT",
                    Path("results/receipt.json"),
                ),
                mock.patch(
                    "scripts.audit_v24254_candidate_dev64_launcher.os.open",
                    wraps=os.open,
                ) as opener,
                mock.patch(
                    "scripts.audit_v24254_candidate_dev64_launcher.os.fsync",
                    wraps=os.fsync,
                ) as syncer,
            ):
                publish_new(target, self.value)
            self.assertTrue(target.is_file())
            flags = opener.call_args_list[0].args[1]
            self.assertTrue(flags & os.O_EXCL)
            self.assertTrue(flags & os.O_NOFOLLOW)
            self.assertGreaterEqual(syncer.call_count, 2)
            with (
                mock.patch(
                    "scripts.audit_v24254_candidate_dev64_launcher.ROOT",
                    root,
                ),
                mock.patch(
                    "scripts.audit_v24254_candidate_dev64_launcher.OUTPUT",
                    Path("results/receipt.json"),
                ),
            ):
                with self.assertRaises(FileExistsError):
                    publish_new(target, self.value)


if __name__ == "__main__":
    unittest.main()
