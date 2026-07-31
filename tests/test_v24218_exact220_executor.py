from __future__ import annotations

import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from deepwide_agent.v24218_exact220_executor import (
    EXPECTED_COUNTS,
    EXPECTED_SHARDS,
    aggregate_evidence_width,
    compile_schedule,
    evidence_width,
    payload_sha256,
    validate_exact_partition,
    validate_terminal_shard,
)
from scripts import run_v24218_exact220_executor as runner


ROOT = Path(__file__).resolve().parents[1]


class V24218Exact220ExecutorTests(unittest.TestCase):
    def canonical_ids(self) -> dict[str, list[str]]:
        paths = {
            "test_s01": ROOT / "configs/full220_v2403_r1_test_s01.ids",
            "test_s02": ROOT / "configs/full220_v2403_r1_test_s02.ids",
            "test_s03": ROOT / "configs/full220_v2403_r1_test_s03.ids",
            "devval": ROOT / "configs/full220_v2403_r1_devval_s04.ids",
        }
        return {
            tag: [line for line in path.read_text().splitlines() if line]
            for tag, path in paths.items()
        }

    def test_canonical_partition_and_capacity_schedule(self) -> None:
        digest = validate_exact_partition(self.canonical_ids())
        self.assertEqual(len(digest), 64)
        schedule = compile_schedule({"selected": 8, "workers": 2, "shards": 4})
        self.assertEqual(schedule["executor_concurrency"], 4)
        self.assertEqual(schedule["agent_width"], 1)
        self.assertEqual(schedule["waves"], [list(EXPECTED_SHARDS)])
        self.assertEqual(schedule["worst_case_model_request_concurrency"], 8)

    def test_schedule_waves_and_capacity_violation(self) -> None:
        schedule = compile_schedule({"selected": 4, "workers": 2, "shards": 2})
        self.assertEqual(
            schedule["waves"],
            [list(EXPECTED_SHARDS[:2]), list(EXPECTED_SHARDS[2:])],
        )
        with self.assertRaisesRegex(RuntimeError, "exceeds"):
            compile_schedule({"selected": 3, "workers": 2, "shards": 2})

    def test_duplicate_partition_is_rejected(self) -> None:
        rows = self.canonical_ids()
        rows["devval"][-1] = rows["devval"][-2]
        with self.assertRaisesRegex(RuntimeError, "opaque ID|disjoint"):
            validate_exact_partition(rows)

    def test_terminal_shard_requires_exact_envelopes(self) -> None:
        ids = self.canonical_ids()["test_s01"]
        rows = [
            {
                "opaque_id": opaque_id,
                "status": "completed",
                "prediction": "| a |\n|---|\n| b |",
            }
            for opaque_id in ids
        ]
        value = validate_terminal_shard(
            tag="test_s01",
            ids=ids,
            runtime_rows=rows,
            summary={"selected": 52, "completed": 52, "failed": 0},
        )
        self.assertEqual(value, {"selected": 52, "completed": 52, "failed": 0})
        rows[-1]["status"] = "running"
        with self.assertRaisesRegex(RuntimeError, "exact terminal"):
            validate_terminal_shard(
                tag="test_s01",
                ids=ids,
                runtime_rows=rows,
                summary={"selected": 52, "completed": 51, "failed": 1},
            )

    def test_evidence_width_deduplicates_query_url_content_and_source(self) -> None:
        evidence = [
            {
                "query": "Alpha Beta",
                "url": "HTTPS://EXAMPLE.COM/A",
                "text": "same body",
                "source_family": "example.com",
            },
            {
                "queries": [" alpha   beta ", "Gamma"],
                "url": "https://example.com/a",
                "text": "same body",
                "source_family": "EXAMPLE.COM",
            },
            {
                "query": "Delta",
                "url": "https://other.test/b",
                "fingerprint": "fingerprint-two",
                "source_family": "other.test",
            },
        ]
        value = evidence_width(evidence)
        self.assertEqual(value["raw_evidence_items"], 3)
        self.assertEqual(value["unique_query_intents"], 3)
        self.assertEqual(value["unique_urls"], 2)
        self.assertEqual(value["unique_content_fingerprints"], 2)
        self.assertEqual(value["unique_source_dependencies"], 2)
        self.assertEqual(value["effective_evidence_width"], 2)
        aggregate = aggregate_evidence_width([{"evidence": evidence}, {"evidence": []}])
        self.assertEqual(aggregate["task_count"], 2)
        self.assertTrue(aggregate["post_terminal_task_state_files_opened"])
        self.assertFalse(aggregate["question_or_prediction_fields_used"])
        self.assertFalse(aggregate["mapping_gold_category_evaluator_score_read"])
        self.assertFalse(aggregate["evidence_content_or_identifier_emitted"])

    def test_payload_seal_is_canonical(self) -> None:
        value = {"b": 2, "a": 1}
        self.assertEqual(payload_sha256(value), payload_sha256(json.loads(json.dumps(value))))

    def test_missing_failed_task_state_counts_as_zero_width(self) -> None:
        ids = self.canonical_ids()
        existing = {
            tag: runner._shard_paths(tag)["out"] / "tasks" / values[0] / "state.json"
            for tag, values in ids.items()
        }

        def is_file(path: Path) -> bool:
            return path in existing.values()

        def read_object(path: Path) -> dict:
            if path in existing.values():
                return {"evidence": [{"url": "https://example.test", "text": "x"}]}
            raise AssertionError(path)

        with mock.patch.object(runner.Path, "is_file", is_file), mock.patch.object(
            runner.Path, "is_symlink", return_value=False
        ), mock.patch.object(runner, "read_opaque_ids", side_effect=lambda path, count: next(
            values for tag, values in ids.items() if runner._shard_paths(tag)["ids"] == path
        )), mock.patch.object(runner, "read_object", side_effect=read_object):
            value = runner._evidence_report()
        self.assertEqual(value["task_count"], 220)
        self.assertEqual(value["task_state_files_opened"], 4)
        self.assertEqual(value["task_state_files_missing_after_terminal_forward"], 216)
        self.assertEqual(value["missing_state_evidence_width_policy"], "zero")

    def test_wave_preflight_barrier_precedes_any_forward(self) -> None:
        events: list[str] = []
        lock = threading.Lock()

        def record(prefix: str, tag: str) -> dict:
            with lock:
                events.append(f"{prefix}:{tag}")
            return {"tag": tag}

        capacity = {
            "schedule": {
                "waves": [
                    ["test_s01", "test_s02"],
                    ["test_s03", "devval"],
                ]
            }
        }
        with mock.patch.object(runner, "materialize_exact220", return_value={}), mock.patch.object(
            runner,
            "run_preflight_once",
            side_effect=lambda tag, runner=None: record("preflight", tag),
        ), mock.patch.object(
            runner,
            "run_forward_after_preflight",
            side_effect=lambda tag, runner=None: record("forward", tag),
        ), mock.patch.object(
            runner, "publish_forward_barrier", return_value={}
        ), mock.patch.object(
            runner, "evaluate_after_barrier", return_value={}
        ), mock.patch.object(
            runner,
            "publish_result",
            return_value={"selected": 220, "runtime_completed": 0, "runtime_failed": 220},
        ):
            value = runner.run_exact220({}, capacity)
        self.assertEqual(value["selected"], 220)
        for wave in (("test_s01", "test_s02"), ("test_s03", "devval")):
            preflight_positions = [events.index(f"preflight:{tag}") for tag in wave]
            forward_positions = [events.index(f"forward:{tag}") for tag in wave]
            self.assertLess(max(preflight_positions), min(forward_positions))
        self.assertLess(
            max(events.index(f"forward:{tag}") for tag in ("test_s01", "test_s02")),
            min(events.index(f"preflight:{tag}") for tag in ("test_s03", "devval")),
        )


if __name__ == "__main__":
    unittest.main()
