from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.publish_v24207_scope_alias_component import (
    build_selected_publication,
    historical_p12_scope_binding,
    mainline_zero_byte_alias,
)


class PublishV24207ScopeAliasComponentTests(unittest.TestCase):
    def test_historical_p12_binding_is_schema70_and_nonmaterializing(self) -> None:
        value = historical_p12_scope_binding()
        self.assertEqual(value["target_state_schema_version"], 70)
        self.assertTrue(value["historical_bytes_byte_exact"])
        self.assertFalse(value["historical_scope_patch_reapplied"])
        self.assertFalse(value["candidate_root_created"])
        self.assertEqual(value["scope_hook_counts"]["scope_import"], 1)

    def test_mainline_alias_changes_no_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runtime = root / "src/deepwide_agent/runtime.py"
            runtime.parent.mkdir(parents=True)
            source = (
                'STATE_SCHEMA_VERSION = 78\n'
                'PIPELINE_VERSION = "candidate"\n'
                'from .v24102 import (\n    x,\n)\n'
                'from .v24104 import (\n    y,\n)\n'
                'fallback = _v24104_conservative_open_scope_fallback(value, last_errors)\n'
                'state.setdefault("scope_open_fallback_audits", []).append(fallback.audit())\n'
            )
            runtime.write_text(source)
            import hashlib

            digest = hashlib.sha256(runtime.read_bytes()).hexdigest()
            markdown = {
                "publication_payload_sha256": "p" * 64,
                "component_publication": {
                    "candidate_root": str(root),
                    "candidate_regular_file_manifest": {
                        "src/deepwide_agent/runtime.py": digest
                    },
                    "target_state_schema_version": 78,
                    "target_pipeline_version": "candidate",
                    "mainline_scope_hook_preserved_exactly_once": True,
                    "branch_scope_patch_or_alias_applied": False,
                },
            }
            markdown_path = root / "results/markdown.json"
            markdown_path.parent.mkdir()
            markdown_path.write_text("{}")
            before = runtime.read_bytes()
            with mock.patch(
                "scripts.publish_v24207_scope_alias_component.ROOT", root
            ), mock.patch(
                "scripts.publish_v24207_scope_alias_component.MARKDOWN_PUBLICATION",
                Path("results/markdown.json"),
            ):
                value = mainline_zero_byte_alias("schema76", markdown)
            self.assertEqual(runtime.read_bytes(), before)
            self.assertFalse(value["candidate_bytes_modified_or_materialized"])
            self.assertFalse(value["historical_scope_patch_reapplied"])
            self.assertEqual(value["scope_hook_counts"]["scope_import"], 1)

            runtime.write_text(source + "# drift\n")
            with mock.patch(
                "scripts.publish_v24207_scope_alias_component.ROOT", root
            ), mock.patch(
                "scripts.publish_v24207_scope_alias_component.MARKDOWN_PUBLICATION",
                Path("results/markdown.json"),
            ):
                with self.assertRaisesRegex(RuntimeError, "candidate bytes drifted"):
                    mainline_zero_byte_alias("schema76", markdown)

    def test_selected_noop_publication_grants_no_extra_authority(self) -> None:
        selected = {"selected_payload_sha256": "s" * 64}
        order = {
            "decision_sha256": "d" * 64,
            "publication_mode": "no_op_component_absent",
        }
        markdown = {"publication_payload_sha256": "m" * 64}
        with mock.patch(
            "scripts.publish_v24207_scope_alias_component.file_sha256",
            return_value="f" * 64,
        ):
            value = build_selected_publication(selected, order, markdown)
        self.assertIsNone(value["component_publication"])
        self.assertFalse(value["branch_scope_component_published"])
        self.assertFalse(value["candidate_bytes_modified_or_materialized"])
        self.assertFalse(value["search_yield_or_entropy_implemented"])
        self.assertFalse(value["joint_package_built_or_materialized"])
        self.assertFalse(value["benchmark_forward_or_full220_launch_allowed"])
        unsigned = dict(value)
        seal = unsigned.pop("publication_payload_sha256")
        from deepwide_agent.v24200_successor import payload_sha256

        self.assertEqual(seal, payload_sha256(unsigned))


if __name__ == "__main__":
    unittest.main()
