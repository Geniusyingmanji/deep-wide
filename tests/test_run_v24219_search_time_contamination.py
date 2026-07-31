from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from deepwide_agent.v24219_search_time_contamination import payload_sha256
from scripts import run_v24219_search_time_contamination as runner


class RunV24219SearchTimeContaminationTests(unittest.TestCase):
    def test_preterminal_parent_refuses_without_reading_task_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / runner.FORWARD_BARRIER).parent.mkdir(parents=True, exist_ok=True)
            with self.assertRaisesRegex(RuntimeError, "ordinary file"):
                runner.validate_terminal_authority(root)

    def test_terminal_authority_requires_sealed_exact220_pair(self) -> None:
        barrier = {
            "role": "v24218_exact220_forward_terminal_barrier",
            "selected": 220,
            "completed": 200,
            "failed": 20,
            "all_four_shards_exact_terminal": True,
            "mapping_path_opened_or_hashed": False,
            "evaluator_input_result_or_score_opened": False,
        }
        barrier["barrier_payload_sha256"] = payload_sha256(barrier)
        result = {
            "role": "v24218_exact220_released_local_result",
            "selected": 220,
            "runtime_completed": 200,
            "runtime_failed": 20,
            "forward_barrier": {"path": str(runner.FORWARD_BARRIER), "sha256": "b" * 64},
            "resume_or_selective_rerun_used": False,
            "mapping_gold_category_question_type_evaluator_score_used_for_forward_routing": False,
            "sota": False,
        }
        result["result_payload_sha256"] = payload_sha256(result)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for relative, value in (
                (runner.FORWARD_BARRIER, barrier),
                (runner.RESULT, result),
            ):
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(value), encoding="utf-8")
            digest = runner.file_sha256(root / runner.FORWARD_BARRIER)
            result["forward_barrier"]["sha256"] = digest
            unsigned = dict(result)
            unsigned.pop("result_payload_sha256")
            result["result_payload_sha256"] = payload_sha256(unsigned)
            (root / runner.RESULT).write_text(json.dumps(result), encoding="utf-8")
            value = runner.validate_terminal_authority(root)
        self.assertEqual(value["runtime_completed"], 200)
        self.assertEqual(value["runtime_failed"], 20)

    def test_projection_ignores_prediction_and_query_values(self) -> None:
        state = {
            "prediction": "must never be opened",
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
        self.assertNotIn("prediction", projection[0])

    def test_symlink_task_state_is_rejected(self) -> None:
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
                "validate_terminal_authority",
                return_value={"result": {}, "forward_barrier": {}, "runtime_completed": 0, "runtime_failed": 220},
            ), mock.patch.object(
                runner, "_manifest", return_value=({"task_" + "0" * 24: "question"}, "m" * 64)
            ), mock.patch.object(
                runner,
                "_partition",
                return_value={
                    "test_s01": ["task_" + "0" * 24],
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


if __name__ == "__main__":
    unittest.main()
