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

from scripts.audit_v24233_webswarm_effect_preauthorization import (  # noqa: E402
    ROOT,
    audit_python_source,
    build_audit,
    payload_sha256,
    publish_new,
)


class AuditV24233WebSwarmEffectPreauthorizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = build_audit(ROOT, created_at_unix=1)

    def test_receipt_is_sealed_build_only_and_authorizes_nothing(self) -> None:
        value = self.value
        unsigned = dict(value)
        seal = unsigned.pop("audit_payload_sha256")
        self.assertEqual(seal, payload_sha256(unsigned))
        self.assertTrue(value["label_blind_runtime"])
        self.assertTrue(value["build_only"])
        self.assertTrue(value["audit_valid"])
        self.assertTrue(
            value["claims"][
                "build_only_effect_preauthorization_primitive_available"
            ]
        )
        self.assertFalse(value["claims"]["runtime_effect_wrapper_available"])
        self.assertFalse(value["claims"]["benchmark_score_available"])
        self.assertFalse(value["claims"]["sota"])
        for field, enabled in value["authorization"].items():
            self.assertFalse(enabled, field)

    def test_parent_receipt_and_control_surface_are_exact(self) -> None:
        parent = self.value["parent_receipt"]
        self.assertEqual(
            parent["file_sha256"],
            "3c2caddb8f574f1af0537ebbfe7064110925bfca9952d0a3a9d15e24c6d27e40",
        )
        self.assertEqual(
            parent["payload_sha256"],
            "50e8921992b2ce7baa97152e66bb75ae231f2e0d8aa80b24ea28cf57990cdbbb",
        )
        self.assertEqual(
            parent["v24232_control_manifest_sha256"],
            "ca6142c8a8ac7f64bfcfb99dd50867b765a4508178bbc7419aa823c484ca54a8",
        )
        self.assertEqual(parent["v24232_control_files_rehashed"], 4)
        self.assertTrue(parent["v24232_build_only_parent_validated"])

    def test_replay_enforces_preauthorization_and_discloses_limits(self) -> None:
        replay = self.value["synthetic_contract_replay"]
        for field in (
            "four_guidance_arms_begin_from_exact_v24232_budget_bundle",
            "declared_upper_bound_charged_before_permit_emission",
            "permit_and_settlement_hash_chain_replayed",
            "actual_cost_above_declared_reservation_rejected",
            "single_use_settlement_replayed",
            "unused_reservation_not_refunded",
            "settlement_preserves_charged_ledger",
            "parallel_permits_require_serial_admission",
        ):
            self.assertTrue(replay[field], field)
        for field in (
            "single_writer_compare_and_swap_independently_verified",
            "declared_reservation_is_conservative_independently_verified",
            "actual_cost_independently_measured",
            "provider_limits_enforce_reservation_independently_verified",
            "external_cost_overrun_prevented_independently_verified",
            "effect_after_permit_independently_verified",
            "runtime_effect_wrapper_integrated",
            "synthetic_benchmark_rows_or_real_evaluator_payload_read",
        ):
            self.assertFalse(replay[field], field)

    def test_scientific_scope_does_not_overclaim_runtime_ordering(self) -> None:
        scope = self.value["scientific_scope"]
        for field in (
            "declared_upper_bound_debited_before_pure_permit_emission",
            "single_use_permit_settlement_and_effect_receipt_enforced",
            "actual_cost_above_declared_reservation_rejected",
            "unused_reservation_not_refunded",
            "settlement_cannot_create_budget_capacity",
            "multiple_pending_permits_supported_after_serial_admission",
        ):
            self.assertTrue(scope[field], field)
        for field in (
            "single_writer_compare_and_swap_independently_verified",
            "declared_reservation_is_conservative_independently_verified",
            "actual_cost_independently_measured",
            "provider_limits_enforce_reservation_independently_verified",
            "external_cost_overrun_prevented_independently_verified",
            "external_effect_occurrence_independently_verified",
            "effect_after_permit_independently_verified",
            "runtime_effect_wrapper_integrated",
            "real_model_search_fetch_or_orchestrator_execution_observed",
            "dev64_gate_evaluated",
            "fresh_exact220_evaluated",
            "quality_cost_or_benchmark_effect_observed",
        ):
            self.assertFalse(scope[field], field)

    def test_active_forward_and_static_capability_audits_are_clean(self) -> None:
        guard = self.value["active_forward_guard"]
        self.assertTrue(guard["module_absent_from_guarded_forward_entrypoints"])
        self.assertTrue(
            all(count == 0 for count in guard["module_name_hit_count_by_file"].values())
        )
        static = self.value["static_capability_audit"]
        self.assertEqual(static["disallowed_import_count"], 0)
        self.assertEqual(static["privileged_metadata_read_count"], 0)
        self.assertFalse(
            static[
                "file_environment_network_model_search_fetch_process_subprocess_or_dynamic_code_capability"
            ]
        )

    def test_static_audit_rejects_expansive_capabilities_and_privilege(self) -> None:
        for source in (
            "import os\ndef x(): return os.getenv('TOKEN')\n",
            "import pathlib\ndef x(): return pathlib.Path('x').read_text()\n",
            "import requests\ndef x(): return requests.get('https://example.invalid')\n",
            "import subprocess\ndef x(): return subprocess.run(['true'])\n",
            "from deepwide_agent.runtime import DeepWideRuntime\n",
            "def x(): return open('x')\n",
            "def x(): return eval('1')\n",
            "def x(v): return v['ground_truth']\n",
            "def x(v): return v.get('question_type')\n",
        ):
            with self.subTest(source=source):
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
                    "scripts.audit_v24233_webswarm_effect_preauthorization.ROOT",
                    root,
                ),
                mock.patch(
                    "scripts.audit_v24233_webswarm_effect_preauthorization.OUTPUT",
                    Path("results/receipt.json"),
                ),
                mock.patch(
                    "scripts.audit_v24233_webswarm_effect_preauthorization.os.open",
                    wraps=os.open,
                ) as open_mock,
                mock.patch(
                    "scripts.audit_v24233_webswarm_effect_preauthorization.os.fsync",
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
