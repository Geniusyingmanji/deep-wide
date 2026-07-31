from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24200_successor import payload_sha256  # noqa: E402
from scripts.preregister_v24212_entropy_component import publish_new  # noqa: E402
from scripts.preregister_v24213_entropy_recovery import (  # noqa: E402
    CONTROL_FILES,
    DECISION_FIELDS,
    build_protocol,
)


class PreregisterV24213EntropyRecoveryTests(unittest.TestCase):
    def test_protocol_freezes_exact_delta_and_new_paths(self) -> None:
        with mock.patch(
            "scripts.preregister_v24213_entropy_recovery.protected_processes",
            return_value={},
        ), mock.patch(
            "scripts.preregister_v24213_entropy_recovery._failed_watcher_pids",
            return_value=[],
        ):
            value = build_protocol(
                ROOT, created_at_unix=1, require_pristine=False
            )
        self.assertEqual(
            value["publication_contract"]["only_recovery_delta"],
            "validate_v24210_frozen_false_field_under_its_exact_registered_name",
        )
        self.assertTrue(
            value["publication_contract"][
                "v24212_activation_state_candidate_or_publication_reuse_forbidden"
            ]
        )
        self.assertFalse(value["authorization"]["shared_api_lease_acquire"])
        self.assertFalse(
            value["authorization"]["benchmark_forward_or_full220_launch"]
        )
        self.assertEqual(set(value["control_surface"]["manifest"]), set(CONTROL_FILES))
        self.assertEqual(
            value["decision_contract_sha256"],
            payload_sha256({key: value[key] for key in DECISION_FIELDS}),
        )

    def test_publish_is_create_exclusive(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "protocol.json"
            publish_new(path, {"ok": True})
            with self.assertRaises(FileExistsError):
                publish_new(path, {"ok": False})


if __name__ == "__main__":
    unittest.main()
