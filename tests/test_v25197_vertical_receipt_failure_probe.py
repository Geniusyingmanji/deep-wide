from __future__ import annotations

import copy
import sys
import threading
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import (  # noqa: E402
    v25158_vertical_key_value_candidate_runtime as parent,
)
from deepwide_agent import v25197_vertical_receipt_failure_probe as target  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import payload_sha256  # noqa: E402
from test_v25158_vertical_key_value_candidate_runtime import (  # noqa: E402
    V25158VerticalKeyValueCandidateTests,
    VERTICAL,
)


class V25197VerticalReceiptFailureProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        helper = V25158VerticalKeyValueCandidateTests(methodName="runTest")
        _inner, result = helper._run(VERTICAL)
        cls.receipt = copy.deepcopy(result["content_free_receipt"])
        target.install_probe()

    def _changed(self, field: str, value) -> dict:
        changed = copy.deepcopy(self.receipt)
        changed[field] = value
        changed.pop("receipt_payload_sha256")
        changed["receipt_payload_sha256"] = payload_sha256(changed)
        return changed

    def test_valid_parent_return_is_preserved_and_no_failure_is_recorded(self) -> None:
        token = target.begin_task()
        try:
            result = parent.validate_receipt(self.receipt)
            self.assertEqual(result, self.receipt)
            self.assertIsNone(target.failure_observation())
        finally:
            target.end_task(token)

    def test_frozen_exception_is_preserved_and_finite_observation_is_recorded(self) -> None:
        changed = self._changed(
            "raw_candidate_observation_count",
            self.receipt["raw_candidate_observation_count"] + 1,
        )
        token = target.begin_task()
        try:
            with self.assertRaisesRegex(
                ValueError,
                "V2.51.58 vertical key-value candidate receipt drifted",
            ):
                parent.validate_receipt(changed)
            observation = target.failure_observation()
            self.assertIsNotNone(observation)
            self.assertIn("grammar_accounting", observation["violation_codes"])
        finally:
            target.end_task(token)

    def test_nonparent_observer_exception_is_not_converted_or_recorded(self) -> None:
        token = target.begin_task()
        try:
            with self.assertRaises(TypeError):
                parent.validate_receipt(None)  # type: ignore[arg-type]
            self.assertIsNone(target.failure_observation())
        finally:
            target.end_task(token)

    def test_observer_failure_is_isolated_and_frozen_validator_still_decides(self) -> None:
        changed = self._changed("context_cap_preserved", False)
        token = target.begin_task()
        try:
            with mock.patch.object(
                target.observer,
                "observe_receipt_invariants",
                side_effect=RuntimeError("synthetic observer failure"),
            ):
                with self.assertRaisesRegex(
                    ValueError,
                    "V2.51.58 vertical key-value candidate receipt drifted",
                ):
                    parent.validate_receipt(changed)
            self.assertIsNone(target.failure_observation())
        finally:
            target.end_task(token)

    def test_task_contexts_are_thread_isolated(self) -> None:
        barrier = threading.Barrier(2)
        outputs: list[tuple[str, object]] = []

        def worker(kind: str) -> None:
            token = target.begin_task()
            try:
                barrier.wait(timeout=5)
                if kind == "invalid":
                    changed = self._changed(
                        "context_cap_preserved", False
                    )
                    with self.assertRaises(ValueError):
                        parent.validate_receipt(changed)
                else:
                    parent.validate_receipt(self.receipt)
                outputs.append((kind, target.failure_observation()))
            finally:
                target.end_task(token)

        threads = [
            threading.Thread(target=worker, args=(kind,))
            for kind in ("valid", "invalid")
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)
            self.assertFalse(thread.is_alive())
        by_kind = dict(outputs)
        self.assertIsNone(by_kind["valid"])
        self.assertIn(
            "fixed_evidence_or_context_flag",
            by_kind["invalid"]["violation_codes"],
        )

    def test_install_is_idempotent_but_foreign_patch_fails_closed(self) -> None:
        target.install_probe()
        observed = parent.validate_receipt
        try:
            parent.validate_receipt = lambda value: value
            with self.assertRaises(RuntimeError):
                target.install_probe()
        finally:
            parent.validate_receipt = observed


if __name__ == "__main__":
    unittest.main()
