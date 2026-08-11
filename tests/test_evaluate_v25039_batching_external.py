from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25039_batching_external_contract as contract  # noqa: E402
from deepwide_agent import v25038_batching_external_contract as parent_contract  # noqa: E402
from scripts import evaluate_v25039_batching_external as evaluator  # noqa: E402


class _Response:
    def __init__(self, endpoint: str, value: dict, *, status: int = 200) -> None:
        self.url = endpoint
        self.status_code = status
        self._raw = json.dumps(value).encode()

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def raise_for_status(self) -> None:
        if self.status_code != 200:
            raise evaluator.requests.HTTPError(str(self.status_code))

    def iter_content(self, chunk_size: int) -> list[bytes]:
        self.chunk_size = chunk_size
        return [self._raw]


class V25039BatchingEvaluatorTests(unittest.TestCase):
    def tearDown(self) -> None:
        # The frozen successor runner deliberately configures a shared parent
        # engine. Restore it so a combined unittest process remains isolated.
        evaluator.runner.engine.contract = parent_contract
        evaluator.runner.engine.MODEL_SLOT_DIRECTORY = (
            parent_contract.OUTPUT_ROOT / "model_slots"
        )

    def test_endpoint_vector_is_exact_unique_pypi_population(self) -> None:
        values = evaluator.endpoint_vector()
        self.assertEqual(len(values), contract.TASK_COUNT)
        self.assertEqual(len(set(values)), contract.TASK_COUNT)
        self.assertEqual(
            values,
            tuple(
                f"https://pypi.org/pypi/{project}/json"
                for project in contract.PROJECTS
            ),
        )

    def test_protocol_build_is_network_free_and_binds_frozen_parents(self) -> None:
        with mock.patch.object(evaluator.requests, "get") as get:
            value = evaluator.build_evaluator_protocol(
                now=1,
                require_clean=False,
                require_implementation_tracked=False,
            )
        get.assert_not_called()
        self.assertEqual(value["population"]["fixed_denominator"], 20)
        self.assertEqual(value["evaluation"]["calls_per_endpoint"], 1)
        self.assertEqual(value["evaluation"]["retries_or_refetches"], 0)
        self.assertFalse(
            value["authorization"][
                "deepwidebench_dev64_exact220_leaderboard_or_sota"
            ]
        )

    def test_exact_and_partial_four_column_metrics(self) -> None:
        gold = {
            "package": "demo-pkg",
            "version": "2.0",
            "date": "2026-08-01",
            "requires_python": ">= 3.10",
        }
        prediction = (
            "| Package | Latest version | Latest release date (YYYY-MM-DD) | Requires-Python |\n"
            "| --- | --- | --- | --- |\n"
            "| demo_pkg | 2.0 | 2026-08-01 | >=3.10 |"
        )
        exact = evaluator.evaluate_prediction(prediction, gold)
        self.assertEqual(exact["exact_table_success"], 1)
        self.assertEqual(exact["composite"], 1.0)
        partial = evaluator.evaluate_prediction(
            prediction.replace("2026-08-01", "2026-08-02"), gold
        )
        self.assertEqual(partial["exact_table_success"], 0)
        self.assertEqual(partial["item_f1"], 2 / 3)
        self.assertLess(partial["composite"], 1.0)

    def test_bad_separator_or_header_fails_closed(self) -> None:
        gold = {
            "package": "demo",
            "version": "1",
            "date": "2026-01-01",
            "requires_python": ">=3.9",
        }
        bad = "| Package | Version | Date | Python |\n| x | x | x | x |\n| demo | 1 | 2026-01-01 | >=3.9 |"
        value = evaluator.evaluate_prediction(bad, gold)
        self.assertEqual(value["exact_table_success"], 0)
        self.assertEqual(value["composite"], 0.0)

    def test_fetch_gold_makes_one_exact_nonredirecting_call(self) -> None:
        index = 0
        project = contract.PROJECTS[index]
        endpoint = evaluator.endpoint_vector()[index]
        payload = {
            "info": {
                "name": project,
                "version": "3.2.1",
                "requires_python": ">=3.9",
            },
            "releases": {
                "3.2.1": [
                    {"upload_time_iso_8601": "2026-08-02T01:00:00Z"},
                    {"upload_time_iso_8601": "2026-08-01T23:00:00Z"},
                ]
            },
        }
        with mock.patch.object(
            evaluator.requests, "get", return_value=_Response(endpoint, payload)
        ) as get:
            value = evaluator._fetch_gold(index)
        get.assert_called_once()
        self.assertFalse(get.call_args.kwargs["allow_redirects"])
        self.assertTrue(get.call_args.kwargs["stream"])
        self.assertTrue(value["valid"])
        self.assertEqual(value["attempts"], 1)
        self.assertEqual(value["date"], "2026-08-01")

    def test_failed_fetch_is_one_attempt_and_failure_as_zero_ready(self) -> None:
        with mock.patch.object(
            evaluator.requests, "get", side_effect=evaluator.requests.Timeout()
        ) as get:
            value = evaluator._fetch_gold(0)
        get.assert_called_once()
        self.assertFalse(value["valid"])
        self.assertEqual(value["attempts"], 1)
        self.assertEqual(value["version"], "Unknown")

    def test_quality_gate_allows_exact_tie_but_rejects_any_metric_regression(self) -> None:
        metric_names = (
            "entity_recall",
            "row_f1",
            "item_f1",
            "column_f1",
            "composite",
        )
        arms = {
            contract.CONTROL_ARM: {
                "tasks": 20,
                "evaluator_valid": 20,
                "evaluator_invalid_or_not_run": 0,
                "fallback_tasks": 0,
                "exact_table_successes": 5,
                **{name: 0.8 for name in metric_names},
            },
            contract.CANDIDATE_ARM: {
                "tasks": 20,
                "evaluator_valid": 20,
                "evaluator_invalid_or_not_run": 0,
                "fallback_tasks": 0,
                "exact_table_successes": 5,
                **{name: 0.8 for name in metric_names},
            },
        }
        keys = (
            "exact_table_successes",
            *metric_names,
            "evaluator_invalid_or_not_run",
            "fallback_tasks",
        )
        delta = {
            key: arms[contract.CANDIDATE_ARM][key]
            - arms[contract.CONTROL_ARM][key]
            for key in keys
        }
        metrics = {
            "arms": arms,
            f"{contract.CANDIDATE_ARM}_minus_{contract.CONTROL_ARM}": delta,
        }
        mechanism = {
            "mechanism_gate_passed": True,
            "ratios": {"input_tokens": 0.73, "total_tokens": 0.73},
        }
        self.assertTrue(
            evaluator.quality_decision(metrics, mechanism)[
                "batching_external_quality_gate_go"
            ]
        )
        delta["item_f1"] = -0.01
        self.assertFalse(
            evaluator.quality_decision(metrics, mechanism)[
                "batching_external_quality_gate_go"
            ]
        )

    def test_implementation_audit_limits_network_to_fetch_gold(self) -> None:
        value = evaluator.implementation_audit(require_tracked=False)
        self.assertTrue(value["audit_valid"], value["findings"])
        self.assertEqual(
            value["request_calls"],
            [{"function": "_fetch_gold", "method": "get"}],
        )
        self.assertEqual(value["privileged_accesses"], [])
        self.assertEqual(
            value["runner_attributes"],
            ["validate_forward_result", "validate_task_row"],
        )

    def test_gold_row_validator_rejects_identity_or_attempt_tamper(self) -> None:
        rows = [
            evaluator._invalid_gold(index) for index in range(contract.TASK_COUNT)
        ]
        self.assertEqual(
            len(evaluator.validate_gold_rows(rows)), contract.TASK_COUNT
        )
        rows[0]["attempts"] = 2
        with self.assertRaises(RuntimeError):
            evaluator.validate_gold_rows(rows)


if __name__ == "__main__":
    unittest.main()
