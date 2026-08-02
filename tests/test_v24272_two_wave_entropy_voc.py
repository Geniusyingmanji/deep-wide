from __future__ import annotations

import ast
import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from deepwide_agent.v24272_two_wave_entropy_voc import (  # noqa: E402
    FirstWaveObservation,
    TwoWavePolicy,
    beta_expected_information_gain,
    decide_two_wave,
    validate_receipt,
)


def observation(**changes):
    values = {
        "queries_executed": 2,
        "sources_discovered": 6,
        "fetches_attempted": 6,
        "usable_pages": 4,
        "novel_pages": 3,
        "unique_hosts": 2,
        "content_chars": 8_000,
        "required_column_count": 3,
        "explicit_row_target": 0,
        "search_seconds": 4.0,
        "fetch_seconds": 5.0,
        "unrecoverable_search_failures": 0,
    }
    values.update(changes)
    return FirstWaveObservation(**values)


class V24272TwoWaveEntropyVocTests(unittest.TestCase):
    def test_expected_information_gain_is_positive_and_decreases_with_evidence(self) -> None:
        sparse = beta_expected_information_gain(1.0, 1.0, 4)
        informed = beta_expected_information_gain(31.0, 31.0, 4)
        self.assertGreater(sparse, 0.0)
        self.assertGreater(informed, 0.0)
        self.assertGreater(sparse, informed)
        self.assertEqual(beta_expected_information_gain(2.0, 3.0, 0), 0.0)

    def test_sufficient_first_wave_stops_without_delta_budget(self) -> None:
        receipt = decide_two_wave(observation())
        validate_receipt(receipt)
        self.assertEqual(receipt["decision"], "stop")
        self.assertEqual(receipt["reason"], "first_wave_sufficient")
        self.assertEqual(receipt["delta_budget"], {"queries": 0, "fetches": 0, "delta_only": True})

    def test_sparse_fast_wave_expands_on_positive_entropy_voc(self) -> None:
        receipt = decide_two_wave(
            observation(
                sources_discovered=2,
                usable_pages=2,
                novel_pages=1,
                unique_hosts=1,
                content_chars=1_000,
            )
        )
        self.assertEqual(receipt["decision"], "expand")
        self.assertEqual(receipt["reason"], "positive_entropy_voc")
        self.assertEqual(receipt["delta_budget"], {"queries": 2, "fetches": 4, "delta_only": True})
        self.assertGreater(receipt["expected_information_gain_nats"], 0.0)
        self.assertGreater(receipt["expected_terminal_risk_reduction"], 0.0)

    def test_slow_wave_stops_even_if_risk_is_high(self) -> None:
        receipt = decide_two_wave(
            observation(
                sources_discovered=1,
                usable_pages=1,
                novel_pages=1,
                unique_hosts=1,
                content_chars=500,
                search_seconds=16.0,
                fetch_seconds=15.0,
            )
        )
        self.assertEqual(receipt["decision"], "stop")
        self.assertEqual(receipt["reason"], "latency_ceiling")

    def test_all_failed_fetches_can_have_nonpositive_voc(self) -> None:
        policy = TwoWavePolicy(latency_loss_per_second=0.02)
        receipt = decide_two_wave(
            observation(
                sources_discovered=6,
                usable_pages=0,
                novel_pages=0,
                unique_hosts=0,
                content_chars=0,
                search_seconds=5.0,
                fetch_seconds=12.0,
            ),
            policy=policy,
        )
        self.assertEqual(receipt["decision"], "stop")
        self.assertEqual(receipt["reason"], "nonpositive_entropy_voc")

    def test_observation_bounds_and_receipt_tamper_fail_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "novel pages"):
            decide_two_wave(observation(usable_pages=1, novel_pages=2))
        receipt = decide_two_wave(observation())
        for mutation in ("metadata", "decision", "seal"):
            altered = copy.deepcopy(receipt)
            if mutation == "metadata":
                altered["question_type"] = "forbidden"
            elif mutation == "decision":
                altered["decision"] = "expand"
                unsigned = dict(altered)
                unsigned.pop("receipt_sha256")
                altered["receipt_sha256"] = target_hash = __import__(
                    "deepwide_agent.v24272_two_wave_entropy_voc",
                    fromlist=["object_sha256"],
                ).object_sha256(unsigned)
                self.assertEqual(len(target_hash), 64)
            else:
                altered["receipt_sha256"] = "0" * 64
            with self.assertRaises(ValueError):
                validate_receipt(altered)

    def test_kernel_ast_has_no_io_or_dynamic_execution_surface(self) -> None:
        path = SRC / "deepwide_agent/v24272_two_wave_entropy_voc.py"
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
        self.assertTrue(imports.isdisjoint({"os", "pathlib", "subprocess", "requests", "socket", "urllib"}))
        calls = {
            node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        self.assertTrue(calls.isdisjoint({"open", "eval", "exec", "compile", "__import__"}))


if __name__ == "__main__":
    unittest.main()
