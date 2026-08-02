from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from scripts import activate_v24258_score_first_smoke_successor as activate  # noqa: E402
from scripts import preregister_v24258_score_first_smoke_successor as prereg  # noqa: E402
from scripts.run_v24257_score_first_smoke import payload_sha256  # noqa: E402


INACTIVE = {"active": False, "ordinary": True, "record_valid": True}


class V24258ScoreFirstSuccessorTests(unittest.TestCase):
    def test_failure_receipt_requires_zero_effect_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            log = root / prereg.RUNNER_LOG
            log.parent.mkdir(parents=True)
            log.write_text(
                '"marker": RUNNER_MARKER\nNameError: name \'RUNNER_MARKER\' is not defined\n',
                encoding="utf-8",
            )
            with mock.patch.object(
                prereg, "validate_parent_protocol", return_value={"control_surface": {"manifest_sha256": "m"}}
            ), mock.patch.object(
                prereg, "_parent_activation", return_value={"activation_payload_sha256": "a"}
            ), mock.patch.object(
                prereg, "sha256", return_value="f" * 64
            ):
                value = prereg.build_failure_receipt(
                    root,
                    now=1,
                    proc_root=root / "proc",
                    processes=[],
                    observed_lease=INACTIVE,
                )
        self.assertFalse(value["network_model_search_fetch_evaluator_or_api_called"])
        self.assertFalse(value["retry_under_parent_protocol_authorized"])
        unsigned = dict(value)
        self.assertEqual(unsigned.pop("failure_payload_sha256"), payload_sha256(unsigned))

    def test_failure_receipt_rejects_execution_residue(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            log = root / prereg.RUNNER_LOG
            log.parent.mkdir(parents=True)
            log.write_text(
                '"marker": RUNNER_MARKER\nNameError: name \'RUNNER_MARKER\' is not defined\n',
                encoding="utf-8",
            )
            residue = root / prereg.EXECUTION_START
            residue.parent.mkdir(parents=True, exist_ok=True)
            residue.write_text("{}", encoding="utf-8")
            with mock.patch.object(prereg, "validate_parent_protocol", return_value={}), mock.patch.object(
                prereg, "_parent_activation", return_value={"activation_payload_sha256": "a"}
            ), mock.patch.object(prereg, "sha256", return_value="f" * 64), self.assertRaisesRegex(
                RuntimeError, "not clean"
            ):
                prereg.build_failure_receipt(
                    root,
                    now=1,
                    proc_root=root / "proc",
                    processes=[],
                    observed_lease=INACTIVE,
                )

    def test_activation_preserves_existing_watcher_and_grants_no_benchmark(self) -> None:
        protocol = {
            "role": prereg.ROLE,
            "decision_contract_sha256": "d" * 64,
            "control_surface": {"manifest_sha256": "m" * 64},
            "execution": {
                "existing_watcher": {
                    "marker": prereg.WATCHER_MARKER,
                    "pid": 7,
                    "start_ticks": 9,
                }
            },
        }
        rows = [{"pid": 7, "argv": ["python", "-I", "-B", prereg.WATCHER_MARKER]}]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            protocol_path = root / activate.OUTPUT
            protocol_path.parent.mkdir(parents=True)
            protocol_path.write_text("{}\n", encoding="utf-8")
            with mock.patch.object(activate, "validate_protocol", return_value=protocol), mock.patch.object(
                activate, "_start_ticks", return_value=9
            ):
                value = activate.build_activation(
                    root,
                    now=1,
                    proc_root=root / "proc",
                    processes=rows,
                    observed_lease=INACTIVE,
                )
        self.assertTrue(value["one_corrected_smoke16_successor_launch"])
        self.assertFalse(value["official_evaluator_dev64_full220_or_leaderboard"])
        self.assertFalse(
            value[
                "new_or_restarted_watcher_process_signal_parent_retry_resume_or_selective_rerun"
            ]
        )

    def test_wrapper_process_path_is_compatible_with_frozen_watcher(self) -> None:
        self.assertTrue(str(prereg.WRAPPER).endswith("/" + prereg.COMPATIBLE_RUNNER_SUFFIX))
        source = (ROOT / prereg.WRAPPER).read_text(encoding="utf-8")
        self.assertIn("frozen.RUNNER_MARKER = RUNNER_MARKER", source)
        for forbidden in ("category", "question_type", "ground_truth", "evaluator"):
            self.assertNotIn(forbidden, source)

    def test_publication_is_create_exclusive(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "receipt.json"
            prereg._publish(path, {"ok": True})
            with self.assertRaises(FileExistsError):
                prereg._publish(path, {"ok": False})


if __name__ == "__main__":
    unittest.main()
