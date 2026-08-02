from __future__ import annotations

import json
import multiprocessing
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24263_global_model_limiter import (  # noqa: E402
    GlobalModelSlotLimiter,
    POOL_ID,
    validate_receipt,
)


def _prepare_slots(root: Path, cap: int = 2) -> Path:
    slots = root / "slots"
    slots.mkdir()
    for index in range(1, cap + 1):
        (slots / f"slot_{index:02d}.lock").write_text(
            json.dumps({"slot": index}) + "\n", encoding="utf-8"
        )
    return slots


def _worker(
    output_root: str,
    slot_directory: str,
    active,
    maximum,
    lock,
    start_event,
) -> None:
    class Inner:
        def complete(self, *_args, **_kwargs):
            with lock:
                active.value += 1
                maximum.value = max(maximum.value, active.value)
            try:
                time.sleep(0.08)
                return SimpleNamespace(text="ok")
            finally:
                with lock:
                    active.value -= 1

    limiter = GlobalModelSlotLimiter(
        Inner(),
        slot_directory=Path(slot_directory),
        output_root=Path(output_root),
        slot_cap=2,
    )
    start_event.wait()
    limiter.complete("system", "user", max_output_tokens=1)
    validate_receipt(limiter.receipt(), expected_cap=2, expected_acquisitions=1)


class V24263GlobalModelLimiterTests(unittest.TestCase):
    def test_four_processes_never_exceed_two_model_requests(self) -> None:
        context = multiprocessing.get_context("fork")
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            output_root = Path(directory)
            slots = _prepare_slots(output_root)
            active = context.Value("i", 0)
            maximum = context.Value("i", 0)
            lock = context.Lock()
            start = context.Event()
            processes = [
                context.Process(
                    target=_worker,
                    args=(str(output_root), str(slots), active, maximum, lock, start),
                )
                for _ in range(4)
            ]
            for process in processes:
                process.start()
            start.set()
            for process in processes:
                process.join(timeout=5)
                self.assertEqual(process.exitcode, 0)
        self.assertEqual(maximum.value, 2)

    def test_search_like_work_is_not_serialized(self) -> None:
        class Inner:
            def complete(self, *_args, **_kwargs):
                return SimpleNamespace(text="ok")

        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            output_root = Path(directory)
            slots = _prepare_slots(output_root)
            limiter = GlobalModelSlotLimiter(
                Inner(),
                slot_directory=slots,
                output_root=output_root,
                slot_cap=2,
            )
            maximum = 0
            active = 0
            lock = threading.Lock()

            def search_work():
                nonlocal maximum, active
                with lock:
                    active += 1
                    maximum = max(maximum, active)
                time.sleep(0.03)
                with lock:
                    active -= 1

            threads = [threading.Thread(target=search_work) for _ in range(4)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
            limiter.complete("s", "u", max_output_tokens=1)
        self.assertEqual(maximum, 4)

    def test_receipt_is_exact_and_content_free(self) -> None:
        class Inner:
            def complete(self, *_args, **_kwargs):
                return SimpleNamespace(text="secret response")

        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            output_root = Path(directory)
            slots = _prepare_slots(output_root)
            limiter = GlobalModelSlotLimiter(
                Inner(),
                slot_directory=slots,
                output_root=output_root,
            )
            limiter.complete("secret system", "secret user", max_output_tokens=1)
            receipt = limiter.receipt()
            validate_receipt(receipt, expected_acquisitions=1)
        rendered = json.dumps(receipt)
        self.assertNotIn("secret", rendered)
        self.assertFalse(
            receipt[
                "contains_prompt_response_question_query_url_page_prediction_answer_opaque_id_or_credential"
            ]
        )
        tampered = dict(receipt, question="forbidden")
        with self.assertRaisesRegex(ValueError, "receipt drifted"):
            validate_receipt(tampered)

    def test_slot_directory_must_be_existing_ordinary_output_directory(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            output_root = Path(directory)
            outside = ROOT / "results"
            with self.assertRaisesRegex(ValueError, "outside outputs"):
                GlobalModelSlotLimiter(
                    object(),
                    slot_directory=outside,
                    output_root=output_root,
                )

    def test_pool_identity_and_boolean_cap_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            output_root = Path(directory)
            slots = _prepare_slots(output_root)
            with self.assertRaisesRegex(ValueError, "invalid"):
                GlobalModelSlotLimiter(
                    object(),
                    slot_directory=slots,
                    output_root=output_root,
                    slot_cap=True,
                )
            with self.assertRaisesRegex(ValueError, "invalid"):
                GlobalModelSlotLimiter(
                    object(),
                    slot_directory=slots,
                    output_root=output_root,
                    pool_id=POOL_ID + "-drift",
                )

    def test_replaced_slot_symlink_fails_at_acquisition(self) -> None:
        class Inner:
            def complete(self, *_args, **_kwargs):
                return SimpleNamespace(text="ok")

        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            output_root = Path(directory)
            slots = _prepare_slots(output_root)
            limiter = GlobalModelSlotLimiter(
                Inner(),
                slot_directory=slots,
                output_root=output_root,
            )
            first = slots / "slot_01.lock"
            second = slots / "slot_02.lock"
            first.unlink()
            first.symlink_to(second)
            # PID-based offset may select either slot first; replace both to
            # make the no-follow check deterministic.
            target = output_root / "target.lock"
            target.write_text("x", encoding="utf-8")
            second.unlink()
            second.symlink_to(target)
            with self.assertRaises(OSError):
                limiter.complete("s", "u", max_output_tokens=1)


if __name__ == "__main__":
    unittest.main()
