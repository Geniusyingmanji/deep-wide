from __future__ import annotations

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

from scripts import activate_v24257_score_first_smoke as target
from scripts.run_v24257_score_first_smoke import payload_sha256


INACTIVE_LEASE = {
    "present": True,
    "active": False,
    "ordinary": True,
    "record_valid": True,
    "owner": None,
    "purpose": None,
    "pid": None,
    "lock_holder_pids": [],
}


def protocol() -> dict:
    return {
        "role": target.PROTOCOL_ROLE,
        "decision_contract_sha256": "d" * 64,
        "control_surface": {"manifest_sha256": "m" * 64},
        "task_contract": {"selected_opaque_ids_sha256": "s" * 64},
    }


class ActivateV24257ScoreFirstSmokeTests(unittest.TestCase):
    def test_activation_grants_only_the_frozen_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            protocol_path = root / target.OUTPUT
            protocol_path.parent.mkdir(parents=True)
            protocol_path.write_text("{}\n", encoding="utf-8")
            with mock.patch.object(
                target, "validate_protocol", return_value=protocol()
            ), mock.patch.object(
                target, "lease_observation", return_value=INACTIVE_LEASE
            ):
                value = target.build_activation(root, created_at_unix=1)

        self.assertEqual(value["status"], "active")
        self.assertFalse(
            value["benchmark_question_prediction_mapping_gold_score_read"]
        )
        self.assertFalse(
            value["official_evaluator_dev64_full220_or_leaderboard_authorized"]
        )
        unsigned = dict(value)
        seal = unsigned.pop("activation_payload_sha256")
        self.assertEqual(seal, payload_sha256(unsigned))

    def test_active_lease_or_future_residue_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with mock.patch.object(
                target, "validate_protocol", return_value=protocol()
            ), mock.patch.object(
                target,
                "lease_observation",
                return_value=dict(INACTIVE_LEASE, active=True),
            ), self.assertRaisesRegex(RuntimeError, "shared lease is active"):
                target.build_activation(root, created_at_unix=1)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            residue = root / next(
                path for path in target.FUTURE_PATHS if path != target.ACTIVATION
            )
            residue.parent.mkdir(parents=True)
            residue.write_text("residue", encoding="utf-8")
            with mock.patch.object(
                target, "validate_protocol", return_value=protocol()
            ), mock.patch.object(
                target, "lease_observation", return_value=INACTIVE_LEASE
            ), self.assertRaisesRegex(RuntimeError, "not pristine"):
                target.build_activation(root, created_at_unix=1)

    def test_publication_is_create_exclusive(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            relative = Path("results/activation.json")
            path = root / relative
            with mock.patch.object(target, "ROOT", root), mock.patch.object(
                target, "ACTIVATION", relative
            ):
                target.publish_new(path, {"ok": True})
                with self.assertRaises(FileExistsError):
                    target.publish_new(path, {"ok": False})


if __name__ == "__main__":
    unittest.main()
