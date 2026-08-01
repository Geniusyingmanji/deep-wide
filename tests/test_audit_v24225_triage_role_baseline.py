from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


ROOT_PATH = Path(__file__).resolve().parents[1]
if str(ROOT_PATH) not in sys.path:
    sys.path.insert(0, str(ROOT_PATH))

from scripts.audit_v24225_triage_role_baseline import (  # noqa: E402
    ROOT,
    audit_python_source,
    build_audit,
    payload_sha256,
    publish_new,
)


class AuditV24225TriageRoleBaselineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = build_audit(ROOT, created_at_unix=1)

    def test_replay_covers_formula_separation_sign_reversal_and_whitening(self) -> None:
        replay = self.value["synthetic_contract_replay"]
        self.assertEqual(replay["role_formula_replay_count"], 4)
        for field in (
            "all_four_triage_v3_role_constants_covered",
            "bounded_5_plus_5_context_covered",
            "judge_verifier_source_separation_covered",
            "additive_role_correction_sign_reversal_disclosed",
            "within_batch_whitening_replayed",
            "nested_privileged_role_judge_metadata_rejected",
            "cross_segment_source_join_rejected",
        ):
            self.assertTrue(replay[field], field)
        self.assertFalse(replay["synthetic_benchmark_rows_or_content_read"])

    def test_static_audit_rejects_io_network_process_and_dynamic_code(self) -> None:
        for source in (
            "import os\ndef x(): return os.getenv('X')\n",
            "import requests\ndef x(): return requests.get('https://example.invalid')\n",
            "import subprocess\ndef x(): return subprocess.run(['true'])\n",
            "def x(): return open('x')\n",
            "def x(): return eval('1')\n",
        ):
            with self.subTest(source=source):
                with self.assertRaisesRegex(RuntimeError, "capability boundary"):
                    audit_python_source(source)

    def test_audit_is_build_only_and_authorizes_nothing(self) -> None:
        value = self.value
        unsigned = dict(value)
        seal = unsigned.pop("audit_payload_sha256")
        self.assertEqual(seal, payload_sha256(unsigned))
        self.assertTrue(value["label_blind_forward"])
        self.assertTrue(value["build_only"])
        self.assertTrue(value["baseline_only"])
        self.assertTrue(value["audit_valid"])
        self.assertTrue(value["claims"]["build_only_baseline_available"])
        self.assertFalse(value["claims"]["runtime_integration_available"])
        self.assertFalse(value["claims"]["benchmark_score_available"])
        self.assertFalse(value["claims"]["benchmark_improvement_observed"])
        self.assertFalse(value["claims"]["sota"])
        for field, enabled in value["authorization"].items():
            self.assertFalse(enabled, field)

    def test_active_forward_guard_has_no_module_import(self) -> None:
        guard = self.value["active_forward_guard"]
        self.assertTrue(guard["module_absent_from_guarded_forward_entrypoints"])
        self.assertTrue(all(count == 0 for count in guard["module_name_hit_count_by_file"].values()))

    def test_scientific_scope_discloses_noncausal_and_additive_limits(self) -> None:
        scope = self.value["scientific_scope"]
        self.assertTrue(
            scope["triage_v3_four_role_constants_and_additive_formula_implemented"]
        )
        self.assertTrue(scope["additive_baseline_can_reverse_verifier_direction"])
        self.assertTrue(scope["final_verifier_outcome_unavailable_to_role_judge"])
        self.assertFalse(scope["role_typing_is_causal_identification"])
        self.assertFalse(scope["role_judge_semantic_correctness_proven"])
        self.assertFalse(scope["real_role_judgments_or_outcome_records_observed"])
        self.assertFalse(scope["gate2b_evaluated"])
        self.assertFalse(scope["benchmark_quality_or_cost_effect_observed"])

    def test_publish_rejects_noncanonical_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeError, "noncanonical"):
                publish_new(Path(directory) / "receipt.json", self.value)


if __name__ == "__main__":
    unittest.main()
