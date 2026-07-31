from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from deepwide_agent.v24220_source_dependency import payload_sha256
from scripts import run_v24220_source_dependency as runner


class RunV24220SourceDependencyTests(unittest.TestCase):
    def test_preterminal_parent_refuses_without_reading_task_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesRegex(RuntimeError, "ordinary file"):
                runner.validate_parent_terminal_authority(root)

    def test_projection_ignores_question_prediction_and_queries(self) -> None:
        state = {
            "question": "must never be traversed",
            "prediction": "must never be traversed",
            "evidence": [
                {
                    "id": "E1",
                    "text": "body",
                    "url": "https://example.org",
                    "query": "copied visible question",
                    "queries": ["copied visible question"],
                }
            ],
        }
        projection = runner._evidence_projection(state)
        self.assertEqual(len(projection), 1)
        self.assertNotIn("query", projection[0])
        self.assertNotIn("queries", projection[0])
        self.assertNotIn("question", projection[0])
        self.assertNotIn("prediction", projection[0])

    def test_projection_does_not_traverse_unapproved_sibling_metadata(self) -> None:
        state = {"evidence": [{"text": "body", "metadata": {"score": 1}}]}
        projection = runner._evidence_projection(state)
        self.assertEqual(projection, [{"text": "body"}])
        self.assertNotIn("score", str(projection))

    def test_symlink_task_state_is_rejected(self) -> None:
        opaque_id = "task_" + "0" * 24
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "target.json"
            target.write_text("{}", encoding="utf-8")
            link = root / "state.json"
            link.symlink_to(target)
            with mock.patch.object(runner, "_state_path", return_value=link), mock.patch.object(
                runner, "validate_protocol", return_value={"sha256": "p" * 64}
            ), mock.patch.object(
                runner,
                "validate_parent_terminal_authority",
                return_value={
                    "state": {},
                    "report": {},
                    "runtime_completed": 0,
                    "runtime_failed": 220,
                },
            ), mock.patch.object(
                runner,
                "_partition",
                return_value={
                    "test_s01": [opaque_id],
                    "test_s02": [],
                    "test_s03": [],
                    "devval": [],
                },
            ), mock.patch.object(runner, "ROOT", root):
                with self.assertRaisesRegex(RuntimeError, "symlink"):
                    runner.run_audit(root)

    def test_publish_is_create_exclusive(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            detail = Path("detail.json")
            report = Path("report.json")
            (root / detail).write_text("{}", encoding="utf-8")
            with mock.patch.object(runner, "DETAIL", detail), mock.patch.object(
                runner, "REPORT", report
            ):
                with self.assertRaisesRegex(RuntimeError, "rerun"):
                    runner.publish_audit(root)

    def test_ordinary_rejects_symlink_and_escape(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "target"
            target.write_text("x", encoding="utf-8")
            link = root / "link"
            link.symlink_to(target)
            with self.assertRaisesRegex(RuntimeError, "ordinary"):
                runner._ordinary(root, Path("link"))
            with self.assertRaisesRegex(RuntimeError, "noncanonical"):
                runner._ordinary(root, Path("../outside"))

    def test_protocol_control_byte_tamper_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            control = root / "control.py"
            control.write_text("original\n", encoding="utf-8")
            manifest = {"control.py": runner.file_sha256(control)}
            value = {
                "role": "v24220_source_dependency_preregistration",
                "protocol_id": "v24220_post_terminal_label_blind_source_dependency_v1",
                "control_surface": {
                    "file_count": 1,
                    "manifest": manifest,
                    "manifest_sha256": payload_sha256(manifest),
                },
            }
            value["decision_contract_sha256"] = payload_sha256(value)
            protocol = root / "protocol.json"
            protocol.write_text(json.dumps(value), encoding="utf-8")
            runner.validate_protocol(root, Path("protocol.json"))
            control.write_text("tampered\n", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "control bytes drifted"):
                runner.validate_protocol(root, Path("protocol.json"))


if __name__ == "__main__":
    unittest.main()
