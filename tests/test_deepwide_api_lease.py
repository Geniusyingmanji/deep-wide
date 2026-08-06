from __future__ import annotations

import multiprocessing
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.deepwide_api_lease import (
    DeepWideApiLeaseBusy,
    acquire_deepwide_api_lease,
)


def _try_lease(root: str, queue: multiprocessing.Queue) -> None:
    try:
        with acquire_deepwide_api_lease(
            Path(root), owner="child", purpose="contention_test"
        ):
            queue.put("acquired")
    except DeepWideApiLeaseBusy:
        queue.put("busy")


class DeepWideApiLeaseTests(unittest.TestCase):
    def test_cross_process_contention_is_fail_closed_and_releases(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            queue: multiprocessing.Queue = multiprocessing.Queue()
            with acquire_deepwide_api_lease(
                root, owner="parent", purpose="synthetic_test"
            ):
                process = multiprocessing.Process(
                    target=_try_lease, args=(str(root), queue)
                )
                process.start()
                process.join(10)
                self.assertEqual(process.exitcode, 0)
                self.assertEqual(queue.get(timeout=2), "busy")
            with acquire_deepwide_api_lease(
                root, owner="after", purpose="post_release_test"
            ) as record:
                self.assertEqual(record["owner"], "after")

    def test_lease_path_cannot_escape_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesRegex(ValueError, "below outputs"):
                with acquire_deepwide_api_lease(
                    root,
                    owner="bad",
                    purpose="escape",
                    path=root / "outside.lock",
                ):
                    pass


if __name__ == "__main__":
    unittest.main()
