from __future__ import annotations

import ast
import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24983_late_page_external_contract as target  # noqa: E402


class V24983LatePageExternalContractTests(unittest.TestCase):
    def test_population_is_fixed_unique_and_label_blind(self) -> None:
        tasks = target.task_vector()
        self.assertEqual(len(tasks), 20)
        self.assertEqual(len({row["opaque_id"] for row in tasks}), 20)
        self.assertTrue(all(set(row) == {"opaque_id", "question"} for row in tasks))
        self.assertTrue(all(target.IANA_URL not in row["question"] for row in tasks))

    def test_arm_order_is_exactly_balanced(self) -> None:
        orders = target.arm_order_vector()
        self.assertEqual(sum(row[0] == target.CANDIDATE_ARM for row in orders), 10)
        self.assertTrue(all(set(row) == set(target.ARMS) for row in orders))

    def test_hard_budgets_match_production(self) -> None:
        self.assertEqual(target.EXECUTOR_CONCURRENCY, 20)
        self.assertEqual(target.MODEL_SLOT_CAP, 8)
        self.assertEqual(target.LIMITS["wall_seconds"], 240)
        self.assertEqual(target.LIMITS["model_calls"], 3)
        self.assertEqual(target.LIMITS["search_queries"], 4)
        self.assertEqual(target.LIMITS["fetch_targets"], 10)
        self.assertEqual(target.LIMITS["evidence_chars"], 60_000)
        self.assertEqual(target.LIMITS["page_chars"], 5_000)

    def test_entropy_is_shadow_only(self) -> None:
        self.assertEqual(target.TWO_WAVE_POLICY["information_gain_weight"], 0.0)
        self.assertEqual(target.TWO_WAVE_POLICY["latency_loss_per_second"], 0.0)
        self.assertFalse(target.source_policy()["entropy_or_information_gain_assigns_credit_or_routes"])

    def test_protocol_roundtrip_before_files_are_tracked(self) -> None:
        protocol = target.build_protocol_untracked(ROOT, now=1_786_291_800)
        self.assertEqual(
            target.validate_protocol(ROOT, protocol, tracked=False), protocol
        )
        self.assertFalse(protocol["authorization"]["one_external_forward"])
        self.assertFalse(protocol["authorization"]["public_exact220_launch"])

    def test_protocol_tamper_is_rejected(self) -> None:
        protocol = target.build_protocol_untracked(ROOT, now=1_786_291_800)
        tampered = copy.deepcopy(protocol)
        tampered["execution"]["limits"]["fetch_targets"] = 11
        tampered = target.seal(tampered, "protocol_payload_sha256")
        with self.assertRaises(RuntimeError):
            target.validate_protocol(ROOT, tampered, tracked=False)

    def test_forward_runtime_sources_do_not_import_benchmark_or_evaluator(self) -> None:
        for relative in (target.PROJECTOR, target.FETCH, target.RUNTIME, target.HELPER):
            tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.extend(alias.name.casefold() for alias in node.names)
                elif isinstance(node, ast.ImportFrom):
                    imports.append((node.module or "").casefold())
            self.assertFalse(any("deepwidebench" in name or "evaluate" in name for name in imports))

    def test_future_surfaces_are_append_only_and_distinct(self) -> None:
        paths = {
            target.BUILD_AUDIT,
            target.PROTOCOL,
            target.PREAUDIT,
            target.EXECUTION_START,
            target.FORWARD_RESULT,
            target.FORWARD_AUDIT,
            target.EVALUATOR_PROTOCOL,
            target.RESULT,
            target.POSTAUDIT,
            target.OUTPUT_ROOT,
        }
        self.assertEqual(len(paths), 10)


if __name__ == "__main__":
    unittest.main()
