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

from deepwide_agent import v24939_schema_bound_record_ledger as parent  # noqa: E402
from deepwide_agent import v24942_compact_schema_bound_record_ledger as candidate  # noqa: E402
from deepwide_agent import v24941_open_world_ledger_external_contract as external_contract  # noqa: E402
from scripts import run_v24940_open_world_ledger_external as page_builder  # noqa: E402
from tests.test_v24940_open_world_ledger_external import catalog_blob, target_blob  # noqa: E402


QUESTION = "From the page include Cohort C01 only.\nColumn names: Country | Cohort | ISO3 | Population [POP] @2021\nOutput format: table only. Cohort C01."


def page() -> dict[str, str]:
    header = ["Country", "Cohort", "ISO3", "Population [POP] @2021", *(f"Archive {i}" for i in range(8))]
    lines = [" | ".join(header)]
    for index in range(16):
        lines.append(" | ".join([
            f"Country {index:02d}",
            "C01" if index % 2 == 0 else "X01",
            f"X{index:02d}",
            str(1000 + index),
            *(f"long archive metadata {slot} row {index} " + "x" * 70 for slot in range(8)),
        ]))
    return {"title": "Official", "url": "https://data.example.test/pop", "content": "\n".join(lines)}


class V24942CompactSchemaBoundRecordLedgerTests(unittest.TestCase):
    def test_compact_render_retains_all_observations_under_5k(self) -> None:
        value = candidate.build_projection(QUESTION, [page()])
        receipt = value["content_free_receipt"]
        self.assertEqual(receipt["admissible_bound_observation_count"], 48)
        self.assertEqual(receipt["retained_admissible_bound_observation_count"], 48)
        self.assertEqual(receipt["missed_admissible_bound_observation_count"], 0)
        self.assertEqual(receipt["retained_admissible_record_count"], 16)

    def test_compact_render_is_smaller_than_parent_ledger(self) -> None:
        old = parent.build_projection(QUESTION, [page()])
        new = candidate.build_projection(QUESTION, [page()])
        self.assertLess(
            new["compact_ledger_characters"],
            sum(len(line) for line in old["projection"].splitlines() if line.startswith("[SBCL:")),
        )
        self.assertGreaterEqual(
            new["retained_admissible_bound_observation_count"],
            old["retained_admissible_bound_observation_count"],
        )
        self.assertLess(new["projected_rendered_characters"], old["projected_rendered_characters"])

    def test_v24941_synthetic_population_reaches_full_retention(self) -> None:
        page_builder.contract = external_contract
        try:
            bundle, tasks, _freeze = page_builder.build_snapshot(catalog_blob(), [target_blob()])
            value = candidate.build_projection(tasks[0]["question"], [bundle["pages"][0]])
        finally:
            from deepwide_agent import v24940_open_world_ledger_external_contract as original
            page_builder.contract = original
        receipt = value["content_free_receipt"]
        self.assertEqual(receipt["admissible_bound_observation_count"], 48)
        self.assertEqual(receipt["retained_admissible_bound_observation_count"], 48)

    def test_schema_header_is_once_and_record_lines_are_atomic(self) -> None:
        value = candidate.build_projection(QUESTION, [page()])
        projection = value["projection"]
        self.assertEqual(projection.count("[SBCL-SCHEMA]"), 1)
        self.assertEqual(projection.count("[SBCL:R"), 16)
        self.assertIn('"targets":[[1,"Cohort"],[2,"ISO3"],[3,"Population [POP] @2021"]]', projection)
        self.assertTrue(all(len(line) <= candidate.BLOCK_CHARACTER_CAP for line in projection.splitlines() if line.startswith("[SBCL:R")))

    def test_conflict_and_cross_page_gates_are_inherited(self) -> None:
        conflicting = [
            {"title": "One", "url": "https://one.example.test/a", "content": "Country | Cohort | ISO3 | Population\nAlpha | C01 | ALP | 10"},
            {"title": "Two", "url": "https://two.example.test/b", "content": "Country | Cohort | ISO3 | Population\nAlpha | C01 | ALP | 11"},
        ]
        value = candidate.build_projection(QUESTION, conflicting)
        self.assertEqual(value["content_free_receipt"]["conflicting_coordinate_count"], 1)
        self.assertNotIn('[3,"10"]', value["projection"])
        self.assertNotIn('[3,"11"]', value["projection"])
        cross = candidate.build_projection(
            QUESTION,
            [
                {"title": "One", "url": "https://one.example.test/a", "content": "Country: Alpha"},
                {"title": "Two", "url": "https://two.example.test/b", "content": "Population: 10"},
            ],
        )
        self.assertEqual(cross["admissible_bound_observation_count"], 0)

    def test_unicode_replay_and_tamper_fail_closed(self) -> None:
        pages = [page()]
        pages[0]["content"] += "\nCompatibility: ½ ℃ ™"
        value = candidate.build_projection(QUESTION, pages)
        self.assertEqual(candidate.validate_projection(value, question=QUESTION, pages=pages), value)
        tampered = copy.deepcopy(value)
        tampered["admissible_observations"][0]["value"] = "tampered"
        with self.assertRaises(ValueError):
            candidate.validate_projection(tampered, question=QUESTION, pages=pages, replay=False)

    def test_entropy_credit_remains_zero(self) -> None:
        receipt = candidate.build_projection(QUESTION, [page()])["content_free_receipt"]
        self.assertTrue(receipt["entropy_information_gain_shadow_only"])
        self.assertEqual(receipt["positive_signed_credit_count"], 0)
        self.assertEqual(receipt["unbound_observation_positive_credit_count"], 0)

    def test_runtime_module_has_no_io_network_model_or_process_capability(self) -> None:
        source = (ROOT / "src/deepwide_agent/v24942_compact_schema_bound_record_ledger.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = {
            alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        imports.update((node.module or "").split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.ImportFrom))
        self.assertTrue(imports.isdisjoint({"os", "pathlib", "socket", "subprocess", "requests", "httpx", "openai", "runpy", "importlib"}))
        for forbidden in ("ground_truth", "question_type", "answer_key", "results.csv"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
