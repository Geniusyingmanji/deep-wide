from __future__ import annotations

import csv
import io
import json
import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import build_v24733_dual_namespace_surfaces as target  # noqa: E402


def execute_module(name: str, source: str) -> types.ModuleType:
    module = types.ModuleType(name)
    module.__file__ = f"<{name}>"
    module.__package__ = "deepwide_agent"
    sys.modules[name] = module
    try:
        exec(compile(source, module.__file__, "exec"), module.__dict__)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    return module


class V24733DualNamespaceSurfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.surfaces = target.build_surfaces()
        cls.contract_name = "deepwide_agent.v24733_dual_namespace_contract"
        cls.evaluator_name = "deepwide_agent.v24733_dual_namespace_evaluator"
        cls.contract = execute_module(
            cls.contract_name, cls.surfaces[target.CONTRACT]
        )
        cls.evaluator = execute_module(
            cls.evaluator_name, cls.surfaces[target.EVALUATOR]
        )

    @classmethod
    def tearDownClass(cls) -> None:
        sys.modules.pop(cls.evaluator_name, None)
        sys.modules.pop(cls.contract_name, None)

    def test_generated_contract_roundtrips_all_24_tasks(self) -> None:
        tasks = self.contract.task_vector()
        self.assertEqual(len(tasks), 24)
        self.assertTrue(all(set(task) == {"opaque_id", "question"} for task in tasks))
        self.assertEqual(len({task["opaque_id"] for task in tasks}), 24)
        self.assertEqual(
            [self.contract.visible_namespace(task["question"]) for task in tasks].count("ror"),
            12,
        )
        self.assertEqual(
            [self.contract.visible_namespace(task["question"]) for task in tasks].count("worldbank"),
            12,
        )

    def test_generated_evaluator_reads_both_fixed_denominators(self) -> None:
        gold = self.evaluator.gold_rows(
            self.surfaces[target.ROR_GOLD], self.surfaces[target.WB_GOLD]
        )
        self.assertEqual(len(gold["ror"]), 48)
        self.assertEqual(len(gold["worldbank"]), 48)
        self.assertTrue(
            {row["opaque_id"] for row in gold["ror"]}.isdisjoint(
                row["opaque_id"] for row in gold["worldbank"]
            )
        )

    def test_all_unknown_predictions_evaluate_without_schema_failure(self) -> None:
        gold = self.evaluator.gold_rows(
            self.surfaces[target.ROR_GOLD], self.surfaces[target.WB_GOLD]
        )
        rows = []
        for ordinal, task in enumerate(self.contract.task_vector(), 1):
            if ordinal <= 12:
                group = self.contract.ROR_ENTITY_GROUPS[ordinal - 1]
                prediction = "| Organization | ROR ID | Country code |\n|---|---|---|\n" + "\n".join(
                    f"| {entity} | Unknown | Unknown |" for entity in group
                )
            else:
                group = self.contract.WORLD_BANK_COUNTRY_GROUPS[ordinal - 13]
                prediction = (
                    "| "
                    + " | ".join(self.evaluator.WORLD_BANK_COLUMNS)
                    + " |\n|---|---|---|\n"
                    + "\n".join(
                        f"| {name} | Unknown | Unknown |" for name, _iso3 in group
                    )
                )
            rows.append(
                {
                    "opaque_id": task["opaque_id"],
                    "predictions": {"baseline": prediction, "candidate": prediction},
                }
            )
        result = self.evaluator.evaluate_frozen_rows(rows, gold)
        self.assertFalse(result["gate_passed"])
        self.assertEqual(result["ror"]["baseline"]["tasks"], 12)
        self.assertEqual(result["worldbank"]["baseline"]["tasks"], 12)

    def test_provenance_is_resealed_and_ids_are_successor_ids(self) -> None:
        value = json.loads(self.surfaces[target.PROVENANCE])
        unsigned = dict(value)
        seal = unsigned.pop("provenance_payload_sha256")
        self.assertEqual(seal, target.payload_sha256(unsigned))
        self.assertEqual(value["role"], "v24733_dual_namespace_gold_provenance")
        ids = {
            record["opaque_id"]
            for section in ("ror_source", "worldbank_source")
            for record in value[section]["records"]
        }
        expected = {
            f"task_{target.NEW_BASE + ordinal:024x}"
            for ordinal in range(1, target.TASK_COUNT + 1)
        }
        self.assertEqual(ids, expected)

    def test_no_predecessor_version_or_id_survives(self) -> None:
        for text in self.surfaces.values():
            self.assertNotIn("v24730", text)
            self.assertNotIn("V2.47.30", text)
            for ordinal in range(1, target.TASK_COUNT + 1):
                self.assertNotIn(f"task_{target.OLD_BASE + ordinal:024x}", text)

    def test_main_remains_inert_without_new_authorization(self) -> None:
        if not (ROOT / target.AUTHORIZATION).exists():
            self.assertFalse(target._authorization_valid())


if __name__ == "__main__":
    unittest.main()
