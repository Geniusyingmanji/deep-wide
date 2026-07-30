from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.preregister_v24187_phase_liveness import (
    CONTROL_FILES,
    DEFAULT_PROTOCOL,
    DEFAULT_STATE,
    PARENTS,
    build_protocol,
    payload_sha,
    validate_protocol,
)


class PreregisterV24187PhaseLivenessTests(unittest.TestCase):
    def test_protocol_is_observation_only_and_phase_aware(self) -> None:
        root = Path(__file__).parents[1]
        fake_parents = {
            relative: {
                "sha256": digest,
                "role": role,
                "decision_contract_sha256": None,
                "contents_emitted": False,
            }
            for relative, (digest, role) in PARENTS.items()
        }
        with patch(
            "scripts.preregister_v24187_phase_liveness._parents",
            return_value=fake_parents,
        ):
            value = build_protocol(
                root, created_at_unix=1, require_pristine_outputs=False
            )
        self.assertEqual(set(value["control_surface"]["manifest"]), set(CONTROL_FILES))
        self.assertEqual(
            value["control_surface"]["manifest_sha256"],
            payload_sha(value["control_surface"]["manifest"]),
        )
        self.assertEqual(value["execution"]["state_path"], str(DEFAULT_STATE))
        self.assertEqual(len(value["phase_contract"]["ordered_phases"]), 8)
        self.assertFalse(value["authorization"]["process_signal"])
        self.assertFalse(
            value["authorization"]["benchmark_model_search_fetch_evaluator_or_api_call"]
        )
        self.assertFalse(value["authorization"]["leaderboard_submission"])

    def test_live_published_protocol_rebuilds_exactly_when_present(self) -> None:
        root = Path(__file__).parents[1]
        path = root / DEFAULT_PROTOCOL
        if not path.exists():
            self.skipTest("protocol not published yet")
        self.assertEqual(
            validate_protocol(root, path)["value"]["role"],
            "v24187_phase_liveness_preregistration",
        )

    def test_pristine_output_guard(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for relative in CONTROL_FILES:
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("x", encoding="utf-8")
            state = root / DEFAULT_STATE
            state.parent.mkdir(parents=True, exist_ok=True)
            state.write_text("{}", encoding="utf-8")
            with patch(
                "scripts.preregister_v24187_phase_liveness._parents",
                return_value={},
            ), self.assertRaises(FileExistsError):
                build_protocol(root, created_at_unix=1)


if __name__ == "__main__":
    unittest.main()
