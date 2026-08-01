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

from scripts.audit_v24232_webswarm_total_budget import (  # noqa: E402
    ROOT,
    audit_python_source,
    build_audit,
    payload_sha256,
    publish_new,
)


class AuditV24232WebSwarmTotalBudgetTests(unittest.TestCase):
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
            value["claims"]["build_only_shared_total_budget_primitive_available"]
        )
        self.assertFalse(value["claims"]["runtime_budget_enforcement_available"])
        self.assertFalse(value["claims"]["benchmark_score_available"])
        self.assertFalse(value["claims"]["sota"])
        for field, enabled in value["authorization"].items():
            self.assertFalse(enabled, field)

    def test_parent_receipt_is_exact(self) -> None:
        parent = self.value["parent_receipt"]
        self.assertEqual(
            parent["file_sha256"],
            "b8480355741d126a70b62ee28e0674275bfae6f84e55cdba409b1a2c5d4e8826",
        )
        self.assertEqual(
            parent["payload_sha256"],
            "90f7af98e4af1279d780ed2fa2a4ec19fc30e12f62a9c9b52e942d555fb31625",
        )
        self.assertEqual(
            parent["v24231_control_manifest_sha256"],
            "8f34021a7cf93059ae4ccbe4b4173ba2102a59df82b0077c8a23c140d0213f6f",
        )
        self.assertEqual(parent["v24231_control_files_rehashed"], 4)
        self.assertTrue(parent["v24231_build_only_parent_validated"])

    def test_replay_enforces_all_dimensions_and_discloses_limits(self) -> None:
        replay = self.value["synthetic_contract_replay"]
        for field in (
            "four_guidance_arms_bound_to_one_exact_total_budget",
            "method_overhead_charged_first_for_every_arm",
            "probe_and_extractor_wall_each_ceiled_before_sum",
            "immutable_hash_chained_transition_replayed",
            "duplicate_charge_ref_rejected",
            "all_nine_budget_dimensions_overflow_rejected",
            "hard_stop_at_exact_cap_replayed_by_tests",
        ):
            self.assertTrue(replay[field], field)
        for field in (
            "caller_reported_cost_independently_verified",
            "pre_side_effect_charge_order_independently_verified",
            "runtime_budget_enforcement_integrated",
            "synthetic_benchmark_rows_or_real_evaluator_payload_read",
        ):
            self.assertFalse(replay[field], field)

    def test_scientific_scope_distinguishes_primitive_from_enforcement(self) -> None:
        scope = self.value["scientific_scope"]
        for field in (
            "model_attempt_search_fetch_other_tool_orchestrator_input_output_and_wall_caps_implemented",
            "four_webswarm_arms_share_one_exact_contract",
            "v24231_probe_and_extractor_overhead_is_first_charge",
            "method_overhead_debited_before_remaining_capacity",
            "charge_chain_is_canonical_immutable_and_duplicate_ref_rejecting",
            "any_dimension_exact_cap_requires_hard_stop",
            "any_dimension_overflow_rejected_before_new_ledger",
        ):
            self.assertTrue(scope[field], field)
        for field in (
            "caller_reported_execution_cost_independently_verified",
            "method_overhead_attempts_extra_tools_independently_verified",
            "charge_happens_before_external_side_effect_independently_verified",
            "runtime_budget_enforcement_integrated",
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
                    "scripts.audit_v24232_webswarm_total_budget.ROOT", root
                ),
                mock.patch(
                    "scripts.audit_v24232_webswarm_total_budget.OUTPUT",
                    Path("results/receipt.json"),
                ),
                mock.patch(
                    "scripts.audit_v24232_webswarm_total_budget.os.open",
                    wraps=os.open,
                ) as open_mock,
                mock.patch(
                    "scripts.audit_v24232_webswarm_total_budget.os.fsync",
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
