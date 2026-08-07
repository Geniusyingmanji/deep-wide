from __future__ import annotations

import ast
import copy
import dataclasses
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from deepwide_agent.v24272_two_wave_entropy_voc import (  # noqa: E402
    FirstWaveObservation,
    decide_two_wave,
)
from deepwide_agent.v24799_fixed_full_budget_control import (  # noqa: E402
    POLICY_VALUES,
    build_synthetic_gate,
    fixed_full_budget_policy,
    payload_sha256,
    validate_gate,
)


class V24799FixedFullBudgetControlTests(unittest.TestCase):
    def test_policy_is_same_hard_cap_no_entropy_control(self) -> None:
        policy = fixed_full_budget_policy()
        self.assertEqual(dataclasses.asdict(policy), POLICY_VALUES)
        self.assertEqual(policy.wave1_queries + policy.wave2_queries, 4)
        self.assertEqual(policy.wave1_fetches + policy.wave2_fetches, 10)
        self.assertEqual(policy.information_gain_weight, 0)
        self.assertEqual(policy.latency_loss_per_second, 0)

    def test_synthetic_grid_always_expands_before_safety_ceiling(self) -> None:
        value = build_synthetic_gate()
        self.assertGreater(value["synthetic_observation_count"], 1_000)
        self.assertEqual(
            value["pre_synthesis_safety_ceiling_expand_count"],
            value["synthetic_observation_count"],
        )
        self.assertEqual(
            value["zero_entropy_value_count"],
            value["synthetic_observation_count"],
        )

    def test_first_wave_safety_ceiling_still_stops(self) -> None:
        observation = FirstWaveObservation(
            queries_executed=2,
            sources_discovered=18,
            fetches_attempted=6,
            usable_pages=6,
            novel_pages=6,
            unique_hosts=6,
            content_chars=30_000,
            required_column_count=4,
            explicit_row_target=0,
            search_seconds=16,
            fetch_seconds=14,
        )
        value = decide_two_wave(observation, policy=fixed_full_budget_policy())
        self.assertEqual(value["decision"], "stop")
        self.assertEqual(value["reason"], "latency_ceiling")

    def test_gate_tamper_fails_closed(self) -> None:
        value = build_synthetic_gate()
        altered = copy.deepcopy(value)
        altered["entropy_or_information_gain_used_for_admission"] = True
        unsigned = dict(altered)
        unsigned.pop("receipt_payload_sha256")
        altered["receipt_payload_sha256"] = payload_sha256(unsigned)
        with self.assertRaises(ValueError):
            validate_gate(altered)

    def test_module_has_no_io_or_dynamic_execution_surface(self) -> None:
        path = SRC / "deepwide_agent/v24799_fixed_full_budget_control.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = {
            alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        imports.update(
            (node.module or "").split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        )
        self.assertTrue(
            imports.isdisjoint(
                {"os", "pathlib", "subprocess", "requests", "socket", "urllib"}
            )
        )
        calls = {
            node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        self.assertTrue(
            calls.isdisjoint({"open", "eval", "exec", "compile", "__import__"})
        )


if __name__ == "__main__":
    unittest.main()
