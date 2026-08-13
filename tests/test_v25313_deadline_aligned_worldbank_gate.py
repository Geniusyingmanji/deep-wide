from __future__ import annotations

import ast
import copy
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25309_worldbank_monotone_fill_external_contract as old_contract  # noqa: E402
from deepwide_agent import v25313_deadline_aligned_worldbank_gate as target  # noqa: E402
from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import POOL_ID  # noqa: E402
from deepwide_agent.v24272_two_wave_entropy_voc import TwoWavePolicy  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter  # noqa: E402
from deepwide_agent.v24319_runner_integration import _aligned_deadlines  # noqa: E402
from test_v24319_runner_integration import Clock  # noqa: E402
import test_v25309_worldbank_monotone_fill_external as old_tests  # noqa: E402


class V25313DeadlineAlignedWorldBankGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.population = old_contract.frozen_population(ROOT)
        fixture = old_tests.V25309WorldBankMonotoneFillExternalTests(
            "test_real_parent_chain_admits_one_supported_third_slot_fill"
        )
        fixture.population = cls.population
        cls.fixture = fixture

    def _objects(self, *, aligned: bool = True):
        visible, _columns, values = self.fixture._fixture(fill=True)
        temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        self.addCleanup(temporary.cleanup)
        output = Path(temporary.name)
        clock = Clock(100.0)
        inner = old_tests.SyntheticModel(values)
        model = DeadlineAwareGlobalModelSlotLimiter(
            inner,
            slot_directory=old_tests._make_slots(output),
            output_root=output,
            slot_cap=8,
            pool_id=POOL_ID,
            absolute_deadline=340.0,
            cleanup_reserve_seconds=5.0,
            minimum_attempt_seconds=0.05 if aligned else 0.01,
            monotonic=clock,
            sleeper=clock.sleep,
        )
        search = target.DeadlineAlignedFrozenWorldBankSnapshotSearchClient(
            self.population["pages"], absolute_deadline=340.0, monotonic=clock
        )
        return visible, inner, model, search, clock

    def test_constructor_aligns_all_deadline_identity_fields_before_effect(self) -> None:
        _visible, _inner, model, search, _clock = self._objects()
        self.assertTrue(_aligned_deadlines(model, search))
        self.assertEqual(model.minimum_attempt_seconds, 0.05)
        self.assertEqual(search.minimum_attempt_seconds, 0.05)
        receipt = target.deadline_identity_receipt(model, search)
        self.assertTrue(receipt["aligned_deadlines"])
        self.assertTrue(receipt["checked_before_model_search_or_fetch_effect"])
        self.assertEqual(model.receipt()["acquisitions"], 0)
        self.assertEqual(search.snapshot_transport_receipt()["search_invocations"], 0)

    def test_mismatched_model_fails_before_any_effect(self) -> None:
        visible, inner, model, search, clock = self._objects(aligned=False)
        with self.assertRaises(ValueError):
            target.run_paired_task(
                visible,
                model=model,
                search=search,
                limits=ScoreFirstLimits(**target.PARENT_LIMITS),
                two_wave_policy=TwoWavePolicy(**target.PARENT_TWO_WAVE_POLICY),
                monotonic=clock,
            )
        self.assertEqual(inner.requests, 0)
        self.assertEqual(model.receipt()["acquisitions"], 0)
        self.assertEqual(search.snapshot_transport_receipt()["search_invocations"], 0)

    def test_aligned_runtime_reaches_supported_third_slot_fill(self) -> None:
        visible, inner, model, search, clock = self._objects()
        result = target.run_paired_task(
            visible,
            model=model,
            search=search,
            limits=ScoreFirstLimits(**target.PARENT_LIMITS),
            two_wave_policy=TwoWavePolicy(**target.PARENT_TWO_WAVE_POLICY),
            monotonic=clock,
        )
        target.validate_result(result)
        receipt = result["content_free_paired_receipt"]
        self.assertEqual(receipt["parent_logical_model_calls"], 2)
        self.assertEqual(receipt["final_logical_model_calls"], 3)
        self.assertEqual(receipt["supported_unknown_fill_count"], 1)
        self.assertTrue(receipt["candidate_prediction_changed"])
        self.assertEqual(inner.requests, 3)

    def test_deadline_receipt_tamper_fails_closed(self) -> None:
        _visible, _inner, model, search, _clock = self._objects()
        receipt = target.deadline_identity_receipt(model, search)
        changed = copy.deepcopy(receipt)
        changed["minimum_attempt_seconds_search_micros"] = 10_000
        changed.pop("receipt_payload_sha256")
        changed["receipt_payload_sha256"] = target.payload_sha256(changed)
        with self.assertRaises(ValueError):
            target.validate_deadline_identity_receipt(changed)

    def test_source_has_no_io_evaluator_or_privileged_routing(self) -> None:
        path = ROOT / "src/deepwide_agent/v25313_deadline_aligned_worldbank_gate.py"
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(item.name for item in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.add(node.module or "")
        for forbidden in ("os", "pathlib", "requests", "subprocess", "urllib.request"):
            self.assertNotIn(forbidden, imports)
        for forbidden in (
            "benchmark_question_type", "ground_truth", "answer_key", "results.csv"
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
