from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from deepwide_agent.v24200_successor import payload_sha256
from scripts.preregister_v24206_markdown_component import (
    CONTROL_FILES,
    DECISION_FIELDS,
    ROOT,
    build_protocol,
    publish_new,
)


class PreregisterV24206MarkdownComponentTests(unittest.TestCase):
    def test_protocol_owns_only_selected_markdown_component(self) -> None:
        with mock.patch(
            "scripts.preregister_v24206_markdown_component.protected_processes",
            return_value={},
        ):
            value = build_protocol(ROOT, created_at_unix=1, require_pristine=False)
        contract = value["publication_contract"]
        self.assertEqual(contract["summary"]["decision_count"], 36)
        self.assertEqual(contract["summary"]["markdown_selected_count"], 24)
        self.assertEqual(contract["summary"]["no_markdown_noop_count"], 12)
        self.assertEqual(contract["summary"]["p12_historical_binding_count"], 8)
        self.assertEqual(contract["summary"]["mainline_rebase_count"], 16)
        self.assertEqual(contract["schema76_schema77_expected_joint_tests"], {
            "schema76": 118,
            "schema77": 127,
        })
        self.assertTrue(
            value["authorization"]["selected_baseline_markdown_candidate_materialization"]
        )
        self.assertFalse(
            value["authorization"]["branch_scope_patch_or_namespace_alias"]
        )
        self.assertFalse(
            value["authorization"]["search_yield_implementation_or_publication"]
        )
        self.assertFalse(
            value["authorization"]["entropy_controller_implementation_or_publication"]
        )
        self.assertFalse(value["authorization"]["package_gate_evaluation_or_launch"])
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
