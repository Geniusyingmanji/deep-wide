from __future__ import annotations

import ast
import copy
import json
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25129_causal_salience_external_contract as contract  # noqa: E402
from scripts import evaluate_v25129_causal_salience_external as target  # noqa: E402


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
            raise target.requests.HTTPError(str(self.status_code))

    def iter_content(self, chunk_size: int) -> list[bytes]:
        self.chunk_size = chunk_size
        return [self._raw]


class V25129CausalSalienceEvaluatorTests(unittest.TestCase):
    def test_mapping_is_fixed_unique_and_clue_aligned(self) -> None:
        values = target.package_vector()
        self.assertEqual(len(values), 20)
        self.assertEqual(len(set(values)), 20)
        self.assertEqual(values[0], "typer")
        self.assertEqual(values[-1], "cryptography")
        self.assertEqual(len(values), len(contract.CLUES))

    def test_endpoint_vector_is_exact_unique_pypi_population(self) -> None:
        self.assertEqual(
            target.endpoint_vector(),
            tuple(
                f"https://pypi.org/pypi/{project}/json"
                for project in target.package_vector()
            ),
        )

    def test_protocol_build_is_network_free_and_parent_bound(self) -> None:
        with mock.patch.object(target.requests, "get") as get:
            value = target.build_evaluator_protocol(
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
            "released": "2026-08-01",
            "requires": ">= 3.10",
        }
        prediction = (
            "| Package | Version | Released | Requires |\n"
            "| --- | --- | --- | --- |\n"
            "| demo_pkg | 2.0 | 2026-08-01 | >=3.10 |"
        )
        exact = target.evaluate_prediction(prediction, gold)
        self.assertEqual(exact["exact_table_success"], 1)
        self.assertEqual(exact["composite"], 1.0)
        partial = target.evaluate_prediction(
            prediction.replace("2026-08-01", "2026-08-02"), gold
        )
        self.assertEqual(partial["exact_table_success"], 0)
        self.assertEqual(partial["item_f1"], 2 / 3)

    def test_bad_separator_or_header_fails_closed(self) -> None:
        gold = {
            "package": "demo",
            "version": "1",
            "released": "2026-01-01",
            "requires": ">=3.9",
        }
        bad = "| Package | Version | Date | Python |\n| x | x | x | x |\n| demo | 1 | 2026-01-01 | >=3.9 |"
        value = target.evaluate_prediction(bad, gold)
        self.assertEqual(value["exact_table_success"], 0)
        self.assertEqual(value["composite"], 0.0)

    def test_fetch_gold_makes_one_exact_nonredirecting_call(self) -> None:
        index = 0
        project = target.package_vector()[index]
        endpoint = target.endpoint_vector()[index]
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
            target.requests, "get", return_value=_Response(endpoint, payload)
        ) as get:
            value = target._fetch_gold(index)
        get.assert_called_once()
        self.assertFalse(get.call_args.kwargs["allow_redirects"])
        self.assertTrue(get.call_args.kwargs["stream"])
        self.assertTrue(value["valid"])
        self.assertEqual(value["attempts"], 1)
        self.assertEqual(value["released"], "2026-08-01")

    def test_failed_fetch_is_one_attempt_and_failure_as_zero_ready(self) -> None:
        with mock.patch.object(
            target.requests, "get", side_effect=target.requests.Timeout()
        ) as get:
            value = target._fetch_gold(0)
        get.assert_called_once()
        self.assertFalse(value["valid"])
        self.assertEqual(value["attempts"], 1)
        self.assertEqual(value["version"], "Unknown")

    def test_quality_gate_requires_strict_exact_gain_and_nonregression(self) -> None:
        arms = {
            contract.CONTROL_ARM: {
                "tasks": 20,
                "evaluator_valid": 20,
                "evaluator_invalid_or_not_run": 0,
                "fallback_tasks": 0,
                "exact_table_successes": 2,
                **{metric: 0.7 for metric in target.METRICS},
            },
            contract.CANDIDATE_ARM: {
                "tasks": 20,
                "evaluator_valid": 20,
                "evaluator_invalid_or_not_run": 0,
                "fallback_tasks": 0,
                "exact_table_successes": 3,
                **{metric: 0.8 for metric in target.METRICS},
            },
        }
        keys = (
            "exact_table_successes",
            "exact_table_accuracy",
            *target.METRICS,
            "evaluator_invalid_or_not_run",
            "fallback_tasks",
        )
        for arm in contract.ARMS:
            arms[arm]["exact_table_accuracy"] = arms[arm]["exact_table_successes"] / 20
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
            "checks": {
                "exact_physical_query_budget": True,
                "physical_fetch_cap_preserved": True,
                "effective_arm_model_budgets_exact_and_equal": True,
                "evidence_lengths_equal": True,
            },
        }
        self.assertTrue(
            target.quality_decision(metrics, mechanism)[
                "causal_salience_external_quality_gate_go"
            ]
        )
        delta["item_f1"] = -0.01
        self.assertFalse(
            target.quality_decision(metrics, mechanism)[
                "causal_salience_external_quality_gate_go"
            ]
        )

    def test_forward_parent_and_protocol_tamper_fail_closed(self) -> None:
        audit = target._read(contract.FORWARD_AUDIT, tracked=True)
        changed = copy.deepcopy(audit)
        changed["mechanism_decision"]["mechanism_gate_passed"] = False
        changed = contract.seal(changed, "audit_payload_sha256")
        original_read = target._read

        def read_with_tamper(relative: Path, *, tracked: bool) -> dict:
            if relative == contract.FORWARD_AUDIT:
                return changed
            return original_read(relative, tracked=tracked)

        with mock.patch.object(target, "_read", side_effect=read_with_tamper):
            with self.assertRaises(RuntimeError):
                target._validate_forward_parents()

    def test_evaluator_network_and_privileged_capabilities_are_confined(self) -> None:
        audit = target.implementation_audit(require_tracked=False)
        self.assertTrue(audit["audit_valid"], audit["findings"])
        self.assertEqual(
            audit["request_calls"],
            [{"function": "_fetch_gold", "method": "get"}],
        )
        self.assertEqual(audit["privileged_accesses"], [])
        tree = ast.parse((ROOT / contract.EVALUATOR).read_text(encoding="utf-8"))
        self.assertTrue(any(isinstance(node, ast.Import) for node in ast.walk(tree)))


if __name__ == "__main__":
    unittest.main()
