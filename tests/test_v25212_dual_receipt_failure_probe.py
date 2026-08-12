from __future__ import annotations

import copy
import sys
import threading
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25135_sparse_production_runtime as sparse  # noqa: E402
from deepwide_agent import v25180_quote_aware_production_runtime as quote  # noqa: E402
from deepwide_agent import v25210_receipt_disposition_observer as observer  # noqa: E402
from deepwide_agent import v25212_dual_receipt_failure_probe as target  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import payload_sha256  # noqa: E402
from test_v25135_sparse_production_runtime import (  # noqa: E402
    SparseProductionRuntimeTests,
)
from test_v25180_quote_aware_production_runtime import (  # noqa: E402
    NO_GAIN_CONTENT,
    V25180QuoteAwareProductionRuntimeTests,
)


class V25212DualReceiptFailureProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        sparse_helper = SparseProductionRuntimeTests(methodName="runTest")
        _inner, _searches, sparse_result = sparse_helper._run(field_page=False)
        cls.sparse_receipt = copy.deepcopy(sparse_result["content_free_receipt"])
        quote_helper = V25180QuoteAwareProductionRuntimeTests(methodName="runTest")
        _inner, _searches, quote_result = quote_helper._run(
            quote, content=NO_GAIN_CONTENT
        )
        cls.quote_receipt = copy.deepcopy(quote_result["content_free_receipt"])
        target.install_probe()

    @staticmethod
    def _changed(value: dict, field: str, replacement) -> dict:
        changed = copy.deepcopy(value)
        changed[field] = replacement
        changed.pop("receipt_payload_sha256", None)
        changed["receipt_payload_sha256"] = payload_sha256(changed)
        return changed

    def test_valid_returns_are_preserved_and_no_failure_is_retained(self) -> None:
        token = target.begin_task()
        try:
            self.assertEqual(
                sparse.validate_receipt(self.sparse_receipt), self.sparse_receipt
            )
            self.assertEqual(
                quote.validate_receipt(self.quote_receipt), self.quote_receipt
            )
            self.assertEqual(target.failure_observations(), {})
        finally:
            target.end_task(token)

    def test_sparse_static_exception_is_preserved_and_classified(self) -> None:
        changed = self._changed(
            self.sparse_receipt,
            "provider_forward_count",
            self.sparse_receipt["provider_forward_count"] + 1,
        )
        token = target.begin_task()
        try:
            with self.assertRaisesRegex(ValueError, target.SPARSE_FAILURE):
                sparse.validate_receipt(changed)
            failures = target.failure_observations()
            self.assertEqual(set(failures), {observer.SPARSE_KIND})
            self.assertIn(
                "provider_forward_accounting",
                failures[observer.SPARSE_KIND]["violation_codes"],
            )
        finally:
            target.end_task(token)

    def test_quote_static_exception_is_preserved_and_classified(self) -> None:
        changed = self._changed(
            self.quote_receipt, "raw_normalizer_observer_failure_type", ""
        )
        token = target.begin_task()
        try:
            with self.assertRaisesRegex(ValueError, target.QUOTE_FAILURE):
                quote.validate_receipt(changed)
            failures = target.failure_observations()
            self.assertEqual(set(failures), {observer.QUOTE_KIND})
            self.assertIn(
                "observer_failure_type_contract",
                failures[observer.QUOTE_KIND]["violation_codes"],
            )
        finally:
            target.end_task(token)

    def test_nonmatching_exception_and_observer_failure_are_not_retained(self) -> None:
        token = target.begin_task()
        try:
            with self.assertRaises(TypeError):
                sparse.validate_receipt(None)  # type: ignore[arg-type]
            self.assertEqual(target.failure_observations(), {})
            changed = self._changed(
                self.sparse_receipt, "physical_fetch_cap", 15
            )
            with mock.patch.object(
                target.observer,
                "observe_sparse_receipt",
                side_effect=RuntimeError("synthetic observer failure"),
            ):
                with self.assertRaisesRegex(ValueError, target.SPARSE_FAILURE):
                    sparse.validate_receipt(changed)
            self.assertEqual(target.failure_observations(), {})
        finally:
            target.end_task(token)

    def test_parent_result_binding_error_is_not_misclassified_as_receipt_error(self) -> None:
        token = target.begin_task()
        try:
            with self.assertRaises(ValueError):
                quote.validate_receipt(self.quote_receipt, parent_result={})
            self.assertEqual(target.failure_observations(), {})
        finally:
            target.end_task(token)

    def test_sparse_and_quote_failures_can_coexist_in_one_task(self) -> None:
        sparse_changed = self._changed(
            self.sparse_receipt, "physical_query_count", 5
        )
        quote_changed = self._changed(
            self.quote_receipt, "parent_result_payload_sha256", "short"
        )
        token = target.begin_task()
        try:
            for validator, changed in (
                (sparse.validate_receipt, sparse_changed),
                (quote.validate_receipt, quote_changed),
            ):
                with self.assertRaises(ValueError):
                    validator(changed)
            self.assertEqual(
                set(target.failure_observations()),
                {observer.SPARSE_KIND, observer.QUOTE_KIND},
            )
        finally:
            target.end_task(token)

    def test_task_contexts_are_thread_isolated(self) -> None:
        barrier = threading.Barrier(2)
        outputs: list[tuple[str, dict]] = []

        def worker(kind: str) -> None:
            token = target.begin_task()
            try:
                barrier.wait(timeout=5)
                if kind == "sparse":
                    changed = self._changed(
                        self.sparse_receipt, "physical_query_count", 5
                    )
                    with self.assertRaises(ValueError):
                        sparse.validate_receipt(changed)
                else:
                    changed = self._changed(
                        self.quote_receipt,
                        "parent_result_payload_sha256",
                        "short",
                    )
                    with self.assertRaises(ValueError):
                        quote.validate_receipt(changed)
                outputs.append((kind, target.failure_observations()))
            finally:
                target.end_task(token)

        threads = [
            threading.Thread(target=worker, args=(kind,))
            for kind in ("sparse", "quote")
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)
            self.assertFalse(thread.is_alive())
        by_kind = dict(outputs)
        self.assertEqual(set(by_kind["sparse"]), {observer.SPARSE_KIND})
        self.assertEqual(set(by_kind["quote"]), {observer.QUOTE_KIND})

    def test_install_is_idempotent_but_foreign_patch_fails_closed(self) -> None:
        target.install_probe()
        observed = sparse.validate_receipt
        try:
            sparse.validate_receipt = lambda value: value
            with self.assertRaises(RuntimeError):
                target.install_probe()
        finally:
            sparse.validate_receipt = observed


if __name__ == "__main__":
    unittest.main()
