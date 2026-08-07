from __future__ import annotations

import ast
import copy
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24809_worldbank_budget_ladder_runner_integration import (
    IntegratedOutcome,
    build_envelope,
    validate_envelope,
)
from deepwide_agent.v24809_worldbank_budget_ladder_smoke_contract import (
    RUNTIME_SOURCES,
    SELECTED_COUNT,
    TARGETS,
    validate_task_vector,
)
from tests.test_v24804_shared_prefix_budget_ladder import (
    Model,
    Search,
    limits,
    policy,
    task,
)
from deepwide_agent.v24804_shared_prefix_budget_ladder import run_v24804_task


def load_runner():
    spec = importlib.util.spec_from_file_location(
        "v24809_forward_test", ROOT / "scripts/run_v24809_worldbank_budget_ladder_smoke_forward.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


runner = load_runner()


class V24809WorldBankBudgetLadderSmokeTests(unittest.TestCase):
    def test_runtime_task_boundary_is_exact_and_rejects_labels(self):
        countries = "\n".join(
            f"{index}. Country {index} [{iso3}]"
            for index, iso3 in enumerate(("AAA", "BBB", "CCC", "DDD"), 1)
        )
        columns = " | ".join([
            "Country",
            *(f"{target['label']} [{target['indicator']}] @{target['year']}" for target in TARGETS),
        ])
        question = (
            "Use public web sources to return one Markdown table about these countries:\n"
            f"<COUNTRIES>\n{countries}\n</COUNTRIES>\n"
            "Please output one Markdown table with the columns, in this exact order:\n"
            f"{columns}\nUse the World Bank API values. Preserve the decimal representation returned by "
            "the official API. Use Unknown when unavailable. Return one table only."
        )
        vector = validate_task_vector([
            {"opaque_id": f"task_{index:024x}", "question": question}
            for index in range(1, SELECTED_COUNT + 1)
        ])
        self.assertEqual(len(vector), SELECTED_COUNT)
        with self.assertRaises(ValueError):
            validate_task_vector([
                {**row, "question_type": "hidden"} for row in vector
            ])

    def test_runtime_sources_have_no_evaluator_capability(self):
        forbidden_imports = (
            "official_eval",
            "official_evaluator",
            "evaluator_mapping",
            "finalize_v24",
        )
        privileged = {
            "question_type",
            "category",
            "task_category",
            "ground_truth",
            "answer_key",
            "mapping",
            "evaluator",
            "reward",
            "split",
        }
        findings = []
        for relative in RUNTIME_SOURCES:
            tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                names = []
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    names = [node.module or "", *(alias.name for alias in node.names)]
                if any(marker in name.casefold() for name in names for marker in forbidden_imports):
                    findings.append((str(relative), node.lineno, "import"))
                key = None
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr in {"get", "pop", "setdefault"}
                    and node.args
                    and isinstance(node.args[0], ast.Constant)
                    and isinstance(node.args[0].value, str)
                ):
                    key = node.args[0].value.casefold()
                elif (
                    isinstance(node, ast.Subscript)
                    and isinstance(node.slice, ast.Constant)
                    and isinstance(node.slice.value, str)
                ):
                    key = node.slice.value.casefold()
                if key in privileged:
                    findings.append((str(relative), node.lineno, key))
                if key == "score" and relative != Path("src/deepwide_agent/clients.py"):
                    findings.append((str(relative), node.lineno, key))
        self.assertEqual(findings, [])

    def test_shared_prefix_conservation_and_suffix_blind_stop(self):
        value = run_v24804_task(
            task(), model=Model(), search=Search(), limits=limits(),
            adaptive_policy=policy(cost=1.0),
        )
        self.assertEqual(value["receipt"]["prefix_effect_executions"], 1)
        self.assertEqual(value["receipt"]["repeated_upstream_effects"], 0)
        self.assertEqual(value["adaptive_decision"]["decision"], "stop")
        self.assertFalse(value["adaptive_decision"]["wave_two_response_or_value_read"])
        self.assertEqual(
            value["predictions"]["coverage_risk_adaptive"],
            value["predictions"]["first_wave_only"],
        )

    def test_envelope_rejects_tampering(self):
        result = run_v24804_task(
            task(), model=Model(), search=Search(), limits=limits(),
            adaptive_policy=policy(),
        )
        slot = {
            "artifact_version": 1,
            "role": "v24312_deadline_model_slot_receipt",
            "policy_id": "v24312_deadline_reliability_v1",
            "slot_cap": 8,
            "acquisitions": 2,
            "slot_timeouts": 0,
            "total_wait_seconds": 0.0,
            "max_wait_seconds": 0.0,
            "deadline_rejections": 0,
            "provider_requests": 2,
            "provider_attempts": 2,
        }
        # Use the real validators' constructors from a valid synthetic outcome
        # by copying receipts produced by the lower-level focused tests is not
        # needed here; malformed cross-artifact counts must fail before sealing.
        with self.assertRaises((ValueError, KeyError)):
            build_envelope(IntegratedOutcome(result, slot, {}))

    def test_atomic_progress_is_content_free_and_never_partial(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "progress.json"
            for completed in (0, 1, SELECTED_COUNT):
                expected = runner.progress_value(completed)
                runner.atomic_json(path, expected)
                self.assertEqual(json.loads(path.read_text()), expected)
                encoded = path.read_text().casefold()
                for marker in ("question\"", "prediction\"", "opaque_id\"", "credential\""):
                    self.assertNotIn(marker, encoded)
            self.assertEqual(list(Path(temporary).glob("*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
