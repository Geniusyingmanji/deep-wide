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

from scripts.audit_v24231_webswarm_guidance_baseline import (  # noqa: E402
    ROOT,
    audit_python_source,
    build_audit,
    payload_sha256,
    publish_new,
)


class AuditV24231WebSwarmGuidanceBaselineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = build_audit(ROOT, created_at_unix=1)

    def test_replay_covers_probe_scout_experience_ablations_and_cost(self) -> None:
        replay = self.value["synthetic_contract_replay"]
        for field in (
            "webswarm_v1_three_topology_probe_tactics_replayed",
            "exact_two_scout_schedule_replayed",
            "same_instance_same_parent_homogeneous_sibling_requirement_replayed",
            "process_signal_hash_schema_replayed",
            "generic_process_advice_renderer_replayed",
            "full_no_probing_and_two_no_experience_controls_replayed",
            "upstream_no_experience_schedule_difference_disclosed",
            "matched_schedule_no_experience_control_present",
            "probe_and_extractor_overhead_ledger_replayed",
            "shared_total_budget_cap_and_overhead_debit_replayed",
            "nested_privileged_runtime_metadata_rejected",
            "cross_parent_experience_rejected",
        ):
            self.assertTrue(replay[field], field)
        for field in (
            "raw_fact_answer_query_url_or_page_text_visible_to_schema",
            "process_signal_hash_or_raw_fact_visible_in_rendered_advice",
            "process_fact_separation_independently_verified",
            "experience_has_factual_evidence_authority",
            "synthetic_benchmark_rows_or_real_evaluator_payload_read",
        ):
            self.assertFalse(replay[field], field)

    def test_static_audit_rejects_expansive_capabilities_and_privilege(self) -> None:
        for source in (
            "import os\ndef x(): return os.getenv('TOKEN')\n",
            "import pathlib\ndef x(): return pathlib.Path('x').read_text()\n",
            "import requests\ndef x(): return requests.get('https://example.invalid')\n",
            "import subprocess\ndef x(): return subprocess.run(['true'])\n",
            "def x(): return open('x')\n",
            "def x(): return eval('1')\n",
            "def x(v): return getattr(v, 'secret')\n",
            "def x(v): return v['ground_truth']\n",
            "def x(v): return v.get('question_type')\n",
        ):
            with self.subTest(source=source):
                with self.assertRaisesRegex(RuntimeError, "capability boundary"):
                    audit_python_source(source)

    def test_audit_is_sealed_label_blind_build_only_and_authorizes_nothing(self) -> None:
        value = self.value
        unsigned = dict(value)
        seal = unsigned.pop("audit_payload_sha256")
        self.assertEqual(seal, payload_sha256(unsigned))
        self.assertTrue(value["label_blind_runtime"])
        self.assertTrue(value["build_only"])
        self.assertTrue(value["baseline_only"])
        self.assertTrue(value["audit_valid"])
        self.assertTrue(value["claims"]["build_only_guidance_baseline_available"])
        self.assertFalse(value["claims"]["runtime_integration_available"])
        self.assertFalse(value["claims"]["benchmark_score_available"])
        self.assertFalse(value["claims"]["benchmark_improvement_observed"])
        self.assertFalse(value["claims"]["sota"])
        for field, enabled in value["authorization"].items():
            self.assertFalse(enabled, field)

    def test_active_forward_guard_has_no_v24231_import(self) -> None:
        guard = self.value["active_forward_guard"]
        self.assertEqual(guard["file_count"], 5)
        self.assertTrue(guard["module_absent_from_guarded_forward_entrypoints"])
        self.assertTrue(
            all(count == 0 for count in guard["module_name_hit_count_by_file"].values())
        )

    def test_source_reference_and_forbidden_literal_scan_are_exact(self) -> None:
        reference = self.value["source_reference"]
        self.assertEqual(reference["arxiv_id"], "2607.08662")
        self.assertEqual(reference["version"], 1)
        self.assertEqual(reference["public_code_fixed_scout_count"], 2)
        self.assertEqual(
            reference["public_repository_commit"],
            "40c9aacad7cd6e9cdb3e7add954d59b766425717",
        )
        scan = self.value["control_source_forbidden_literal_scan"]
        self.assertEqual(scan["file_count"], 4)
        self.assertEqual(scan["hit_count"], 0)
        self.assertFalse(scan["credential_or_concrete_opaque_id_literal_present"])

    def test_scientific_scope_discloses_semantic_and_schedule_limits(self) -> None:
        scope = self.value["scientific_scope"]
        for field in (
            "webswarm_v1_probe_and_two_scout_experience_contract_implemented",
            "centralized_centralized_with_gaps_and_distributed_tactics_implemented",
            "same_instance_same_parent_homogeneous_siblings_enforced",
            "upstream_faithful_no_experience_control_implemented",
            "upstream_no_experience_also_changes_scout_schedule",
            "matched_schedule_no_experience_control_added",
            "probe_extractor_model_token_tool_and_wall_cost_recorded",
            "generic_process_advice_renderer_implemented",
            "shared_total_budget_cap_includes_method_overhead",
        ):
            self.assertTrue(scope[field], field)
        for field in (
            "raw_fact_answer_query_url_or_page_text_visible_in_experience_schema",
            "process_fact_separation_independently_verified",
            "generic_tactic_semantics_independently_verified",
            "shared_total_budget_enforcement_implemented",
            "experience_has_factual_evidence_authority",
            "real_model_extractor_probe_search_or_sibling_execution_observed",
            "runtime_integration_complete",
            "dev64_gate_evaluated",
            "fresh_exact220_evaluated",
            "quality_cost_or_benchmark_effect_observed",
        ):
            self.assertFalse(scope[field], field)

    def test_publish_rejects_noncanonical_output(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            with self.assertRaisesRegex(RuntimeError, "noncanonical"):
                publish_new(Path(directory) / "receipt.json", self.value)

    def test_publish_is_create_exclusive_no_follow_and_fsyncs_file_and_parent(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            root = Path(directory).resolve()
            target = root / "results" / "receipt.json"
            target.parent.mkdir()
            with (
                mock.patch(
                    "scripts.audit_v24231_webswarm_guidance_baseline.ROOT", root
                ),
                mock.patch(
                    "scripts.audit_v24231_webswarm_guidance_baseline.OUTPUT",
                    Path("results/receipt.json"),
                ),
                mock.patch(
                    "scripts.audit_v24231_webswarm_guidance_baseline.os.open",
                    wraps=os.open,
                ) as open_mock,
                mock.patch(
                    "scripts.audit_v24231_webswarm_guidance_baseline.os.fsync",
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
