from __future__ import annotations

import copy
import json
import sys
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24661_support_closure_task_runtime import (  # noqa: E402
    run_v24661_task,
    strict_deterministic_support_closure,
    validate_result,
)
from test_v24655_unknown_cell_targeted_runtime import (  # noqa: E402
    Model,
    Search,
    TASK,
    limits,
    revision,
)


class V24661StrictClosureTests(unittest.TestCase):
    def test_strict_closure_preserves_unresolved_declared_id(self) -> None:
        pages = [
            {
                "evidence_id": f"R{index:04d}",
                "host": f"source-{index}.example",
                "content": "Alpha Phone official Release Date 2024-09-20",
            }
            for index in (1, 2)
        ]
        value = strict_deterministic_support_closure(
            row_key="Alpha Phone",
            new_value="2024-09-20",
            declared_evidence_ids=["R9999"],
            targeted_pages=pages,
        )
        self.assertEqual(value["closed_evidence_ids"], ["R9999", "R0001", "R0002"])
        self.assertTrue(value["unresolved_declared_evidence_ids_preserved"])

    def test_one_valid_declared_id_yields_incremental_admission(self) -> None:
        proposal = json.loads(revision())
        proposal["cell_evidence"][0]["evidence_ids"] = ["R0001"]
        result = run_v24661_task(
            TASK,
            model=Model(values=[Model().values[0], Model().values[1], json.dumps(proposal)]),
            search=Search(),
            limits=limits(),
            monotonic=time.monotonic,
        )
        validate_result(result)
        receipt = result["receipt"]
        self.assertEqual(receipt["counterfactual_parent_admitted_cell_change_count"], 0)
        self.assertEqual(receipt["strict_closure_admitted_cell_change_count"], 1)
        self.assertEqual(
            receipt["incremental_strict_closure_admitted_cell_change_count"], 1
        )
        self.assertEqual(receipt["support_closure_added_evidence_id_count"], 3)

    def test_unresolved_declared_id_keeps_revision_rejected(self) -> None:
        proposal = json.loads(revision())
        proposal["cell_evidence"][0]["evidence_ids"] = ["R9999"]
        result = run_v24661_task(
            TASK,
            model=Model(values=[Model().values[0], Model().values[1], json.dumps(proposal)]),
            search=Search(),
            limits=limits(),
            monotonic=time.monotonic,
        )
        self.assertEqual(result["predictions"]["baseline"], result["predictions"]["unknown_cell_targeted"])
        self.assertEqual(result["receipt"]["admitted_cell_change_count"], 0)

    def test_single_source_remains_rejected(self) -> None:
        proposal = json.loads(revision())
        proposal["cell_evidence"][0]["evidence_ids"] = []
        result = run_v24661_task(
            TASK,
            model=Model(values=[Model().values[0], Model().values[1], json.dumps(proposal)]),
            search=Search(targeted_sources=1),
            limits=limits(),
            monotonic=time.monotonic,
        )
        self.assertEqual(result["receipt"]["admitted_cell_change_count"], 0)
        self.assertFalse(result["receipt"]["support_threshold_relaxed"])

    def test_no_revision_has_zero_closure_effects(self) -> None:
        result = run_v24661_task(
            TASK,
            model=Model(values=[Model().values[0], Model().values[1], RuntimeError("revision")]),
            search=Search(),
            limits=limits(),
            monotonic=time.monotonic,
        )
        receipt = result["receipt"]
        self.assertEqual(receipt["support_closure_invocation_count"], 0)
        self.assertEqual(receipt["incremental_strict_closure_admitted_cell_change_count"], 0)

    def test_result_reseal_cannot_authorize_entropy_or_new_effect(self) -> None:
        result = run_v24661_task(
            TASK, model=Model(), search=Search(), limits=limits(), monotonic=time.monotonic
        )
        for field in (
            "entropy_or_task_credit_used_by_closure",
            "new_model_search_fetch_or_evaluator_effect",
        ):
            tampered = copy.deepcopy(result)
            tampered["receipt"][field] = True
            tampered["receipt"].pop("receipt_sha256")
            from deepwide_agent.v24637_objective_alignment_runtime import payload_sha256
            tampered["receipt"]["receipt_sha256"] = payload_sha256(tampered["receipt"])
            tampered.pop("result_sha256")
            tampered["result_sha256"] = payload_sha256(tampered)
            with self.assertRaises(ValueError):
                validate_result(tampered)

    def test_fixed_effect_budget_is_unchanged(self) -> None:
        model = Model()
        search = Search()
        result = run_v24661_task(
            TASK, model=model, search=search, limits=limits(), monotonic=time.monotonic
        )
        receipt = result["receipt"]
        self.assertEqual(model.requests, 3)
        self.assertEqual(receipt["admitted_logical_query_count"], 3)
        self.assertEqual(receipt["admitted_total_fetch_targets"], 10)
        self.assertFalse(receipt["new_model_search_fetch_or_evaluator_effect"])


if __name__ == "__main__":
    unittest.main()
