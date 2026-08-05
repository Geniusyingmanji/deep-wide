from __future__ import annotations

import copy
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24457_adaptive_entropy_support as adaptive  # noqa: E402
from deepwide_agent import v24490_entropy_targeted_support_search as targeted  # noqa: E402
from deepwide_agent import v24496_targeted_reserve_contradiction as reserve  # noqa: E402
from deepwide_agent.v24485_execution_scoped_validation_memo import (  # noqa: E402
    ExecutionValidationMemo,
)
from deepwide_agent.v24504_proof_carrying_record_bound_reserve import (  # noqa: E402
    run_single_validation_v24503_task,
)
from deepwide_agent.v24508_execution_scoped_high_level_validation_memo import (  # noqa: E402
    HighLevelValidationMemo,
    LAYERS,
    binding_contract,
    validate_receipt,
)
from test_v24342_semantic_active_runtime import limits  # noqa: E402
from test_v24390_uncertainty_active_evidence_runtime import SEED, TASK  # noqa: E402
from test_v24412_receipt_snapshot_diagnosis import AdvancingClock  # noqa: E402
from test_v24503_record_bound_reserve_integration import clients  # noqa: E402


def execute(*, memoized: bool):
    temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
    clock = AdvancingClock()
    model, search = clients(
        Path(temporary.name), clock, mode="split_support"
    )
    started = time.perf_counter()
    high = HighLevelValidationMemo()
    with ExecutionValidationMemo() as low:
        if memoized:
            with high:
                value = run_single_validation_v24503_task(
                    TASK,
                    model=model,
                    search=search,
                    partition_seed_sha256=SEED,
                    limits=limits(),
                    monotonic=clock,
                )
        else:
            value = run_single_validation_v24503_task(
                TASK,
                model=model,
                search=search,
                partition_seed_sha256=SEED,
                limits=limits(),
                monotonic=clock,
            )
    return (
        temporary,
        value,
        time.perf_counter() - started,
        low.content_free_receipt(),
        high.content_free_receipt() if memoized else None,
    )


class V24508ExecutionScopedHighLevelValidationMemoTests(unittest.TestCase):
    fixture: tuple

    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = execute(memoized=True)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.fixture[0].cleanup()

    def test_full_chain_receipt_has_one_miss_per_layer_and_safe_hits(self) -> None:
        _temporary, _value, elapsed, low, high = self.fixture
        validated = validate_receipt(high)
        self.assertEqual(validated["total_misses"], 3)
        self.assertGreaterEqual(validated["total_hits"], 3)
        self.assertEqual(validated["total_mismatches"], 0)
        for item in validated["layers"].values():
            self.assertEqual(item["misses"], 1)
            self.assertGreaterEqual(item["hits"], 1)
        self.assertEqual(low["total_misses"], 8)
        self.assertEqual(low["total_mismatches"], 0)
        self.assertLess(elapsed, 15.0)

    def test_memoized_result_is_identical_to_unmemoized_full_chain(self) -> None:
        temporary, plain, elapsed, _low, _high = execute(memoized=False)
        self.addCleanup(temporary.cleanup)
        memoized = self.fixture[1]
        self.assertEqual(
            plain._trusted_outcome().record_bound_result,
            memoized._trusted_outcome().record_bound_result,
        )
        self.assertEqual(
            plain._trusted_outcome().effect_equivalence_receipt,
            memoized._trusted_outcome().effect_equivalence_receipt,
        )
        self.assertLess(self.fixture[2], elapsed)

    def test_same_seal_tamper_falls_through_and_fails_closed(self) -> None:
        adaptive_result = self.fixture[1]._trusted_outcome().parent.parent.parent.adaptive_result
        with HighLevelValidationMemo() as memo:
            adaptive.validate_result(adaptive_result)
            adaptive.validate_result(adaptive_result)
            changed = copy.deepcopy(adaptive_result)
            changed["candidate_prediction"] += " tamper"
            with self.assertRaises(ValueError):
                adaptive.validate_result(changed)
        receipt = memo.content_free_receipt()
        self.assertEqual(receipt["layers"]["v24457"]["misses"], 1)
        self.assertEqual(receipt["layers"]["v24457"]["hits"], 1)
        self.assertEqual(receipt["layers"]["v24457"]["mismatches"], 1)

    def test_bindings_restore_after_exception_and_drift_fails_before_patch(self) -> None:
        originals = {spec.name: spec.owner.validate_result for spec in LAYERS}
        with self.assertRaisesRegex(RuntimeError, "boom"):
            with HighLevelValidationMemo():
                raise RuntimeError("boom")
        for spec in LAYERS:
            self.assertIs(spec.owner.validate_result, originals[spec.name])
        with patch.object(adaptive, "validate_result", lambda value: value):
            with self.assertRaisesRegex(RuntimeError, "binding drifted"):
                HighLevelValidationMemo().__enter__()
            self.assertIs(targeted.validate_result, originals["v24490"])
            self.assertIs(reserve.validate_result, originals["v24496"])

    def test_contract_and_runtime_source_are_label_blind(self) -> None:
        contract = binding_contract()
        self.assertEqual(contract["layer_names"], ["v24457", "v24490", "v24496"])
        self.assertFalse(
            contract[
                "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
            ]
        )
        from scripts import audit_v24398_failure_observability_build as audit

        accesses, imports = audit._ast_findings(
            Path(
                "src/deepwide_agent/v24508_execution_scoped_high_level_validation_memo.py"
            )
        )
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])


if __name__ == "__main__":
    unittest.main()
