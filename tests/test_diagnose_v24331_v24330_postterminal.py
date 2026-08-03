from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24330_forward_contract import payload_sha256  # noqa: E402
from scripts import diagnose_v24331_v24330_postterminal as target  # noqa: E402


class V24331V24330PostterminalTaxonomyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = target.build_report(ROOT, now=1)

    def test_exact_denominator_and_accounting_strata(self) -> None:
        aggregate = self.value["aggregate"]
        effect = aggregate["effect_accounting"]
        self.assertEqual(aggregate["selected_tasks"], 220)
        self.assertEqual(effect["complete_tasks"], 157)
        self.assertEqual(effect["incomplete_tasks"], 63)
        self.assertTrue(effect["complete_subset_conservation_verified"])
        self.assertFalse(effect["incomplete_semantic_last_stage_available"])
        self.assertFalse(effect["incomplete_stage_inferred_or_imputed"])
        complete = effect["complete_task_totals"]
        self.assertEqual(complete["logical_model_admissions"], 449)
        self.assertEqual(complete["provider_model_requests"], 413)
        self.assertEqual(complete["pre_provider_model_rejections"], 36)
        lower = effect["incomplete_task_independent_lower_bounds"]
        self.assertEqual(lower["slot_acquisitions"], 171)
        self.assertEqual(lower["slot_timeouts"], 11)

    def test_admission_failure_is_binding_and_independence_not_entropy_threshold(self) -> None:
        admission = self.value["aggregate"]["admission"]
        self.assertEqual(admission["proposed_cell_changes"], 19)
        self.assertEqual(admission["admitted_cell_changes"], 0)
        self.assertEqual(
            admission["dispositions"],
            {
                "quarantine_fetch_integrity": 11,
                "quarantine_insufficient_independence": 8,
            },
        )
        self.assertFalse(
            self.value["conclusions"][
                "entropy_threshold_was_primary_admission_bottleneck"
            ]
        )
        self.assertTrue(
            self.value["conclusions"][
                "evidence_binding_or_source_independence_was_primary_admission_bottleneck"
            ]
        )

    def test_incomplete_fallbacks_are_not_all_deadline_explained(self) -> None:
        transport = self.value["aggregate"]["transport"]
        self.assertEqual(transport["incomplete_tasks_with_deadline_flag"], 16)
        self.assertEqual(
            transport["incomplete_tasks_with_any_transport_health_event"], 17
        )
        self.assertEqual(
            transport["incomplete_tasks_without_transport_health_event"], 46
        )
        self.assertFalse(
            self.value["conclusions"][
                "all_incomplete_fallbacks_explained_by_deadline_or_transport_health"
            ]
        )

    def test_content_free_and_no_new_benchmark_authority(self) -> None:
        encoded = json.dumps(self.value, ensure_ascii=False)
        self.assertIsNone(target.SECRET.search(encoded))
        self.assertIsNone(target.OPAQUE.search(encoded))
        self.assertNotIn("| Result |", encoded)
        self.assertFalse(self.value["authorization"]["same_run_evaluator"])
        self.assertFalse(self.value["authorization"]["new_exact220"])
        self.assertFalse(self.value["conclusions"]["sota_supported"])

    def test_resealed_tamper_is_recomputed_and_rejected(self) -> None:
        altered = copy.deepcopy(self.value)
        altered["authorization"]["new_exact220"] = True
        altered.pop("taxonomy_payload_sha256")
        altered["taxonomy_payload_sha256"] = payload_sha256(altered)
        with self.assertRaisesRegex(RuntimeError, "taxonomy drifted"):
            target.validate_report(ROOT, altered)


if __name__ == "__main__":
    unittest.main()
