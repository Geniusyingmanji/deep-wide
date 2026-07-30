from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.audit_v24188_parent_closure import (
    _payload_seal,
    replay_manifest,
)
from scripts.preregister_v24188_parent_closure import payload_sha


def _write(path: Path, text: str = "x") -> str:
    import hashlib

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


class AuditV24188ParentClosureTests(unittest.TestCase):
    def test_all_supported_manifest_formats_replay(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            digest = _write(root / "scripts/a.py")
            manifest = {"scripts/a.py": digest}
            fixtures = [
                {
                    "control_surface": {
                        "manifest": manifest,
                        "manifest_sha256": payload_sha(manifest),
                        "must_remain_absent": ["scripts/__init__.py"],
                    }
                },
                {
                    "stable_manifest": manifest,
                    "stable_manifest_sha256": payload_sha(manifest),
                },
                {
                    "control_manifest": manifest,
                    "control_manifest_sha256": payload_sha(manifest),
                },
                {"frozen_dependencies": {"scripts/a.py": {"sha256": digest}}},
            ]
            for index, value in enumerate(fixtures):
                with self.subTest(index=index):
                    report = replay_manifest(root, Path("owner.json"), value)
                    self.assertEqual(report["entry_byte_drift_count"], 0)
                    self.assertEqual(report["manifest_entry_count"], 1)

    def test_manifest_byte_drift_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            digest = _write(root / "scripts/a.py")
            value = {
                "control_manifest": {"scripts/a.py": digest},
                "control_manifest_sha256": payload_sha({"scripts/a.py": digest}),
            }
            (root / "scripts/a.py").write_text("drift", encoding="utf-8")
            with self.assertRaises(RuntimeError):
                replay_manifest(root, Path("owner.json"), value)

    def test_absence_guard_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            digest = _write(root / "scripts/a.py")
            _write(root / "scripts/__init__.py")
            manifest = {"scripts/a.py": digest}
            value = {
                "control_surface": {
                    "manifest": manifest,
                    "manifest_sha256": payload_sha(manifest),
                    "must_remain_absent": ["scripts/__init__.py"],
                }
            }
            with self.assertRaises(RuntimeError):
                replay_manifest(root, Path("owner.json"), value)

    def test_payload_seal_tamper_is_detected(self) -> None:
        value = {"role": "x"}
        value["audit_payload_sha256"] = payload_sha(value)
        self.assertTrue(_payload_seal(value, "audit_payload_sha256"))
        value["role"] = "y"
        self.assertFalse(_payload_seal(value, "audit_payload_sha256"))

    def test_source_has_no_runtime_content_network_or_mutation_surface(self) -> None:
        source = (
            Path(__file__).parents[1] / "scripts/audit_v24188_parent_closure.py"
        ).read_text(encoding="utf-8")
        for forbidden in (
            "runtime_predictions.jsonl",
            "evaluator_mapping.jsonl",
            "ANTHROPIC_API_KEY",
            "TAVILY_API_KEY",
            "subprocess",
            "os.kill",
            "requests.",
            "urllib",
            "socket.",
            "--resume",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
