from __future__ import annotations

import tempfile
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24200_successor import payload_sha256
from scripts.preregister_v24212_entropy_component import (
    CONTROL_FILES,
    DECISION_FIELDS,
    build_protocol,
    publish_new,
)


class PreregisterV24212EntropyComponentTests(unittest.TestCase):
    def test_protocol_freezes_all_parent_graphs_without_execution(self) -> None:
        with mock.patch(
            "scripts.preregister_v24212_entropy_component.protected_processes",
            return_value={},
        ):
            value = build_protocol(ROOT, created_at_unix=1, require_pristine=False)
        summary = value["publication_contract"]["summary"]
        self.assertEqual(summary["decision_count"], 18)
        self.assertEqual(summary["unique_parent_byte_graph_count"], 14)
        self.assertEqual(summary["search_bytes_required_count"], 9)
        self.assertEqual(summary["search_bytes_forbidden_count"], 9)
        self.assertTrue(
            value["publication_contract"][
                "model_file_sha_model_sha_job_sha_and_parent_sha_bound"
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
