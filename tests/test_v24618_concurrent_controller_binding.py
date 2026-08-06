from __future__ import annotations

import concurrent.futures
import sys
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24618_concurrent_controller_binding as target  # noqa: E402


def dummy() -> SimpleNamespace:
    return SimpleNamespace(
        proof="original-proof",
        total="original-total",
        bounded="original-bounded",
        collector_repair="original-collector",
    )


class V24618ConcurrentControllerBindingTests(unittest.TestCase):
    def tearDown(self) -> None:
        snapshot = target.content_free_snapshot()
        self.assertEqual(snapshot["holder_count"], 0)
        self.assertFalse(snapshot["controller_present"])
        self.assertTrue(snapshot["runtime_module_invariant_valid"])

    def test_eight_runtime_holders_overlap_and_restore_once(self) -> None:
        controller = dummy()
        barrier = threading.Barrier(8)
        active = 0
        maximum = 0
        state = threading.Lock()

        def hold(_ordinal: int) -> str:
            nonlocal active, maximum
            with target.controller_bindings(
                controller, protocol_compatibility=False
            ):
                with state:
                    active += 1
                    maximum = max(maximum, active)
                barrier.wait(timeout=5)
                self.assertIs(
                    controller.proof,
                    target.binding_vector(protocol_compatibility=False)["proof"],
                )
                time.sleep(0.02)
                with state:
                    active -= 1
                return "ok"

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            values = list(pool.map(hold, range(8)))
        self.assertEqual(values, ["ok"] * 8)
        self.assertEqual(maximum, 8)
        self.assertEqual(controller.proof, "original-proof")
        self.assertEqual(controller.total, "original-total")
        self.assertEqual(controller.bounded, "original-bounded")
        self.assertEqual(controller.collector_repair, "original-collector")

    def test_nested_same_mode_is_reentrant(self) -> None:
        controller = dummy()
        with target.controller_bindings(controller, protocol_compatibility=False):
            first = target.content_free_snapshot()
            with target.controller_bindings(controller, protocol_compatibility=False):
                second = target.content_free_snapshot()
                self.assertEqual(second["holder_count"], first["holder_count"] + 1)
        self.assertEqual(controller.proof, "original-proof")

    def test_same_thread_cross_mode_fails_immediately(self) -> None:
        controller = dummy()
        started = time.monotonic()
        with target.controller_bindings(controller, protocol_compatibility=False):
            with self.assertRaisesRegex(RuntimeError, "would deadlock"):
                with target.controller_bindings(
                    controller, protocol_compatibility=True
                ):
                    pass
        self.assertLess(time.monotonic() - started, 1.0)

    def test_other_mode_waits_then_enters(self) -> None:
        controller = dummy()
        runtime_entered = threading.Event()
        release_runtime = threading.Event()
        protocol_entered = threading.Event()

        def runtime_holder() -> None:
            with target.controller_bindings(controller, protocol_compatibility=False):
                runtime_entered.set()
                release_runtime.wait(timeout=5)

        def protocol_holder() -> None:
            runtime_entered.wait(timeout=5)
            with target.controller_bindings(controller, protocol_compatibility=True):
                protocol_entered.set()

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(runtime_holder)
            second = pool.submit(protocol_holder)
            self.assertTrue(runtime_entered.wait(timeout=5))
            time.sleep(0.05)
            self.assertFalse(protocol_entered.is_set())
            release_runtime.set()
            first.result(timeout=5)
            second.result(timeout=5)
        self.assertTrue(protocol_entered.is_set())

    def test_incompatible_controller_times_out_without_mutation(self) -> None:
        first = dummy()
        second = dummy()
        with target.controller_bindings(first, protocol_compatibility=False):
            with self.assertRaises(TimeoutError):
                with target.controller_bindings(
                    second,
                    protocol_compatibility=False,
                    wait_seconds=0.02,
                ):
                    pass
        self.assertEqual(second.proof, "original-proof")

    def test_exception_releases_final_holder(self) -> None:
        controller = dummy()
        with self.assertRaisesRegex(RuntimeError, "synthetic stop"):
            with target.controller_bindings(controller, protocol_compatibility=False):
                raise RuntimeError("synthetic stop")
        self.assertEqual(controller.proof, "original-proof")

    def test_snapshot_is_content_free(self) -> None:
        snapshot = target.content_free_snapshot()
        self.assertEqual(
            set(snapshot),
            {
                "mode",
                "holder_count",
                "holder_thread_count",
                "maximum_simultaneous_holders",
                "controller_present",
                "runtime_module_invariant_valid",
                "proof_total_bounded_or_collector_object_emitted",
            },
        )
        self.assertFalse(snapshot["proof_total_bounded_or_collector_object_emitted"])

    def test_runtime_source_is_label_blind_and_secret_free(self) -> None:
        from scripts import audit_v24495_targeted_conversion_projection_build as audit

        path = Path("src/deepwide_agent/v24618_concurrent_controller_binding.py")
        accesses, imports = audit.ast_findings(path)
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])
        self.assertIsNone(audit.SECRET.search((ROOT / path).read_text(encoding="utf-8")))


if __name__ == "__main__":
    unittest.main()
