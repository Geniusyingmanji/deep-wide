from __future__ import annotations

import sys
import copy
import tempfile
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25029_evidence_conditioned_runtime as target  # noqa: E402
from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter  # noqa: E402
from test_v24990_query_vector_paired_runtime import SyntheticRobustSearch  # noqa: E402
from test_v25025_evidence_conditioned_paired_runtime import EvidenceModel, QUESTION  # noqa: E402


def limits():
    return ScoreFirstLimits(wall_seconds=240, model_calls=3, search_queries=4, fetch_targets=10, search_results_per_query=3, evidence_chars=60000, page_chars=5000)


class EvidenceConditionedRuntimeTests(unittest.TestCase):
    def _run(self, valid=True):
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            out=Path(raw); slots=out/"slots"; slots.mkdir()
            for index in range(1,9): (slots/f"slot_{index:02d}.lock").write_text("{}\n")
            inner=EvidenceModel(valid_refinement=valid)
            model=DeadlineAwareGlobalModelSlotLimiter(inner,slot_directory=slots,output_root=out,slot_cap=8,absolute_deadline=time.monotonic()+240)
            searches={phase:SyntheticRobustSearch(QUESTION,"999") for phase in target.PHASES}
            result=target.run_task({"opaque_id":"task_"+"1"*24,"question":QUESTION},model=model,searches=searches,limits=limits())
        return inner,target.validate_result(result)

    def test_exact_production_budget_and_success(self):
        inner,result=self._run()
        receipt=result["content_free_receipt"]
        self.assertTrue(result["model_success"])
        self.assertEqual(inner.requests,3)
        self.assertEqual(receipt["model_logical_call_count"],3)
        self.assertEqual(receipt["physical_query_count"],4)
        self.assertLessEqual(receipt["physical_fetch_count"],10)
        self.assertTrue(receipt["refinement_strategy_applied"])

    def test_invalid_refinement_exact_handoff_still_three_calls(self):
        inner,result=self._run(valid=False)
        receipt=result["content_free_receipt"]
        self.assertEqual(inner.requests,3)
        self.assertTrue(receipt["exact_legacy_second_wave_handoff"])
        self.assertFalse(receipt["refinement_strategy_applied"])

    def test_receipt_is_content_free_and_entropy_free(self):
        _inner,result=self._run()
        receipt=result["content_free_receipt"]
        self.assertFalse(receipt["entropy_or_information_gain_assigns_signed_credit"])
        self.assertFalse(receipt["benchmark_launch_or_evaluator_authorized"])

    def test_resealed_resource_tamper_fails_closed(self):
        _inner,result=self._run()
        changed=copy.deepcopy(result["content_free_receipt"])
        changed["physical_fetch_count"] -= 1
        changed.pop("receipt_payload_sha256")
        from deepwide_agent.v24263_global_model_limiter import payload_sha256
        changed["receipt_payload_sha256"]=payload_sha256(changed)
        with self.assertRaises(ValueError): target.validate_receipt(changed)


if __name__ == "__main__": unittest.main()
