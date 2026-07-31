from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from deepwide_agent.v24200_successor import payload_sha256
from scripts.preregister_v24207_scope_alias_component import (
    CONTROL_FILES,
    DECISION_FIELDS,
    ROOT,
    build_protocol,
    publish_new,
)


class PreregisterV24207ScopeAliasComponentTests(unittest.TestCase):
    def test_protocol_owns_only_branch_scope_alias(self) -> None:
        with mock.patch(
            "scripts.preregister_v24207_scope_alias_component.protected_processes",
            return_value={},
        ):
            value = build_protocol(ROOT, created_at_unix=1, require_pristine=False)
        summary = value["publication_contract"]["summary"]
        self.assertEqual(summary["decision_count"], 36)
        self.assertEqual(summary["scope_selected_count"], 12)
        self.assertEqual(summary["p12_historical_binding_count"], 4)
        self.assertEqual(summary["mainline_zero_byte_alias_count"], 8)
        self.assertTrue(value["authorization"]["historical_p12_schema70_binding"])
        self.assertTrue(value["authorization"]["mainline_zero_byte_namespace_alias"])
        self.assertFalse(value["authorization"]["candidate_byte_or_runtime_behavior_change"])
        self.assertFalse(value["authorization"]["search_yield_implementation_or_publication"])
        self.assertFalse(value["authorization"]["entropy_controller_implementation_or_publication"])
        self.assertFalse(value["authorization"]["joint_package_build_merge_materialization_or_freeze_generation"])
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
