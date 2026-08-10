from __future__ import annotations

import copy
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25038_batching_external_contract as parent  # noqa: E402
from deepwide_agent import v25039_batching_external_contract as contract  # noqa: E402
from scripts import run_v25039_batching_external as runner  # noqa: E402


class V25039BatchingRecoveryTests(unittest.TestCase):
    def test_only_configuration_fix_is_parent_required_page_cap(self) -> None:
        expected = copy.deepcopy(parent.SEARCH)
        expected["max_page_chars"] = 5_000
        self.assertEqual(contract.SEARCH, expected)
        self.assertEqual(parent.SEARCH["max_page_chars"], 20_000)
        self.assertEqual(contract.MODEL, parent.MODEL)
        self.assertEqual(contract.PROJECTS, parent.PROJECTS)
        self.assertEqual(contract.QUERY_PATTERNS, parent.QUERY_PATTERNS)

    def test_task_query_order_and_gates_are_byte_equal_to_parent(self) -> None:
        self.assertEqual(contract.task_vector(), parent.task_vector())
        self.assertEqual(contract.query_vector(), parent.query_vector())
        self.assertEqual(contract.arm_order_vector(), parent.arm_order_vector())
        self.assertEqual(contract.mechanism_gate(), parent.mechanism_gate())
        self.assertEqual(contract.quality_gate(), parent.quality_gate())

    def test_failure_parent_is_zero_effect_and_sealed(self) -> None:
        value = contract._validate_failure(ROOT)
        self.assertEqual(value["search_provider_attempts"], 0)
        self.assertEqual(value["fetch_helper_calls"], 0)
        self.assertEqual(value["model_provider_attempts"], 0)
        self.assertFalse(value["prediction_freeze_created"])
        self.assertFalse(value["pypi_gold_or_evaluator_opened"])

    def test_new_namespace_does_not_reuse_invalidated_output(self) -> None:
        self.assertNotEqual(contract.OUTPUT_ROOT, parent.OUTPUT_ROOT)
        self.assertNotEqual(contract.PROTOCOL, parent.PROTOCOL)
        self.assertNotEqual(contract.EXECUTION_START, parent.EXECUTION_START)
        self.assertNotEqual(contract.FORWARD_RESULT, parent.FORWARD_RESULT)

    def test_source_policy_records_failure_and_exact_fix(self) -> None:
        policy = contract.source_policy()
        self.assertTrue(policy["v25038_pre_effect_failure_bound_and_not_retried"])
        self.assertTrue(
            policy["only_forward_fix_max_page_chars_20000_to_parent_required_5000"]
        )
        self.assertFalse(
            policy["deepwidebench_dev64_exact220_leaderboard_or_sota_authorized"]
        )

    def test_runner_configures_successor_namespace_and_contract(self) -> None:
        runner.configure()
        self.assertIs(runner.engine.contract, contract)
        self.assertEqual(
            runner.engine.MODEL_SLOT_DIRECTORY,
            contract.OUTPUT_ROOT / "model_slots",
        )

    def test_successor_search_client_constructs_with_parent_page_cap(self) -> None:
        runner.configure()
        client = runner.engine._search(
            contract.task_vector()[0]["question"], time.monotonic() + 60.0
        )
        self.assertEqual(client.max_page_chars, 5_000)
        self.assertEqual(client.max_retries, 1)
        self.assertFalse(client.fetch_pages)


if __name__ == "__main__":
    unittest.main()
