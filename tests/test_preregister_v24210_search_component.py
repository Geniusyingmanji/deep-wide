from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from deepwide_agent.v24200_successor import payload_sha256
from scripts.preregister_v24210_search_component import (
    CONTROL_FILES,
    DECISION_FIELDS,
    ROOT,
    build_protocol,
    publish_new,
)


class PreregisterV24210SearchComponentTests(unittest.TestCase):
    def test_protocol_freezes_full_parent_graph_and_no_execution(self) -> None:
        with mock.patch(
            "scripts.preregister_v24210_search_component.protected_processes",
            return_value={},
        ):
            value = build_protocol(ROOT, created_at_unix=1, require_pristine=False)
        summary = value["publication_contract"]["summary"]
        self.assertEqual(summary["decision_count"], 36)
        self.assertEqual(summary["semantic_parent_branch_count"], 9)
        self.assertEqual(summary["unique_parent_byte_graph_count"], 7)
        self.assertTrue(value["publication_contract"]["p12_scope_parent_is_historical_schema70"])
        self.assertTrue(value["quality_contract"]["no_go_retires_component_without_threshold_change_or_rerun"])
        self.assertFalse(value["authorization"]["entropy_controller_implementation_or_publication"])
        self.assertFalse(value["authorization"]["shared_api_lease_acquire"])
        self.assertFalse(value["authorization"]["benchmark_forward_or_full220_launch"])
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
