from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.activate_v24207_scope_alias_component import build_activation


def proc(root: Path, pid: int, ticks: int) -> None:
    path = root / str(pid)
    path.mkdir(parents=True)
    fields = ["S"] + ["0"] * 18 + [str(ticks)] + ["0"] * 8
    (path / "stat").write_text(f"{pid} (python) " + " ".join(fields))


class ActivateV24207ScopeAliasComponentTests(unittest.TestCase):
    def test_activation_grants_scope_binding_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            proc_root = root / "proc"
            proc_root.mkdir()
            proc(proc_root, 101, 500)
            rows = [{"pid": 101, "argv": ["python", "-I", "-B", "scripts/watch_v24207_scope_alias_component.py"]}]
            with mock.patch(
                "scripts.activate_v24207_scope_alias_component.validate_protocol",
                return_value={"sha256": "a" * 64},
            ), mock.patch(
                "scripts.activate_v24207_scope_alias_component.process_snapshot",
                return_value=rows,
            ):
                value = build_activation(root, proc_root=proc_root, created_at_unix=1)
        self.assertTrue(value["parent_safe_state_envelope_read_allowed"])
        self.assertTrue(value["selected_scope_alias_component_publication_allowed"])
        self.assertFalse(value["candidate_byte_or_runtime_behavior_change_allowed"])
        self.assertFalse(value["search_yield_or_entropy_implementation_allowed"])
        self.assertFalse(value["joint_package_build_or_materialization_allowed"])
        self.assertFalse(value["benchmark_forward_or_full220_launch_allowed"])


if __name__ == "__main__":
    unittest.main()
