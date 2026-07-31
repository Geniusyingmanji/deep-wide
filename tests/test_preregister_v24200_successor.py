from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from deepwide_agent.v24200_successor import payload_sha256
from scripts.preregister_v24200_successor import (
    CONTROL_FILES,
    DECISION_FIELDS,
    ROOT,
    build_protocol,
    publish_new,
)


class PreregisterV24200SuccessorTests(unittest.TestCase):
    def test_protocol_freezes_hierarchy_and_package_gate_without_launch(self) -> None:
        with mock.patch(
            "scripts.preregister_v24200_successor.protected_processes", return_value={}
        ):
            value = build_protocol(ROOT, created_at_unix=1, require_pristine=False)
        self.assertTrue(value["baseline_contract"]["p12_to_schema76_paired_gate_consumed"])
        self.assertTrue(
            value["component_contract"][
                "mainline_scope_and_markdown_branch_scope_namespaced_separately"
            ]
        )
        self.assertTrue(
            value["component_contract"]["independent_go_does_not_prove_union_package"]
        )
        self.assertTrue(
            value["component_contract"][
                "nonempty_component_set_requires_new_package_gate"
            ]
        )
        self.assertTrue(
            value["component_contract"][
                "empty_component_set_uses_selected_baseline_identity_handoff"
            ]
        )
        self.assertEqual(value["component_contract"]["terminal_package_count"], 36)
        self.assertFalse(value["package_gate_contract"]["benchmark_launch_allowed"])
        self.assertFalse(
            value["authorization"]["candidate_code_build_merge_or_freeze_generation"]
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
