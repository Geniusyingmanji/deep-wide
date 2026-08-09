from __future__ import annotations

import ast
import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent import v24939_schema_bound_record_ledger as candidate  # noqa: E402


QUESTION = (
    "Return exactly one Markdown table. "
    "Column names: Entity | Population [POP] @2024 | GDP [GDP] @2024."
)


def page(
    content: str,
    *,
    title: str = "Official report",
    url: str = "https://data.example.test/report",
) -> dict[str, str]:
    return {"title": title, "url": url, "content": content}


class V24939SchemaBoundRecordLedgerTests(unittest.TestCase):
    def test_open_world_table_discovers_rows_not_enumerated_in_question(self) -> None:
        value = candidate.build_projection(
            QUESTION,
            [page("Entity | Population | GDP\nAlpha | 991 | 42\nBeta | 881 | 37")],
        )
        receipt = value["content_free_receipt"]
        self.assertEqual(receipt["visible_schema_column_count"], 3)
        self.assertEqual(receipt["header_bound_table_count"], 1)
        self.assertEqual(receipt["discovered_row_key_count"], 2)
        self.assertEqual(receipt["admissible_bound_observation_count"], 4)
        self.assertEqual(receipt["retained_admissible_bound_observation_count"], 4)
        self.assertIn('"row_key":"Alpha"', value["projection"])
        self.assertIn('["GDP [GDP] @2024","42"]', value["projection"])

    def test_markdown_table_and_visible_aliases_are_bound(self) -> None:
        content = (
            "| Entity | POP | GDP |\n"
            "| --- | ---: | :--- |\n"
            "| Alpha | 991 | 42 |\n"
            "| Beta | 881 | 37 |"
        )
        value = candidate.build_projection(QUESTION, [page(content)])
        receipt = value["content_free_receipt"]
        self.assertEqual(receipt["discovered_record_count"], 2)
        self.assertEqual(receipt["malformed_table_row_count"], 0)
        self.assertTrue(
            all(
                item["binding_kind"] == "header_bound_table"
                for item in value["record_ledger"]
            )
        )

    def test_identity_labelled_record_is_contiguous_and_bound(self) -> None:
        content = (
            "Entity: Alpha\nPopulation: 991\nGDP: 42\n\n"
            "Entity: Beta\nPopulation: 881\nGDP: 37"
        )
        value = candidate.build_projection(QUESTION, [page(content)])
        receipt = value["content_free_receipt"]
        self.assertEqual(receipt["identity_label_bound_record_count"], 2)
        self.assertEqual(receipt["admissible_bound_observation_count"], 4)
        self.assertTrue(
            all(
                item["binding_kind"] == "identity_label_bound_record"
                for item in value["record_ledger"]
            )
        )

    def test_cross_page_identity_and_value_never_join(self) -> None:
        pages = [
            page("Entity: Alpha", url="https://one.example.test/a"),
            page("Population: 991\nGDP: 42", url="https://two.example.test/b"),
        ]
        value = candidate.build_projection(QUESTION, pages)
        self.assertEqual(
            value["content_free_receipt"]["admissible_bound_observation_count"], 0
        )

    def test_blank_or_unknown_field_terminates_labelled_record(self) -> None:
        for content in (
            "Entity: Alpha\n\nPopulation: 991",
            "Entity: Alpha\nUnrelated: prose\nPopulation: 991",
        ):
            with self.subTest(content=content):
                value = candidate.build_projection(QUESTION, [page(content)])
                self.assertEqual(
                    value["content_free_receipt"][
                        "admissible_bound_observation_count"
                    ],
                    0,
                )

    def test_wrong_table_header_and_bad_width_fail_closed(self) -> None:
        wrong = candidate.build_projection(
            QUESTION,
            [page("Person | Population | GDP\nAlpha | 991 | 42")],
        )
        self.assertEqual(
            wrong["content_free_receipt"]["admissible_bound_observation_count"], 0
        )
        bad_width = candidate.build_projection(
            QUESTION,
            [page("Entity | Population | GDP\nAlpha | 991")],
        )
        self.assertEqual(
            bad_width["content_free_receipt"]["admissible_bound_observation_count"],
            0,
        )
        self.assertEqual(
            bad_width["content_free_receipt"]["malformed_table_row_count"], 1
        )

    def test_conflicting_coordinate_is_omitted_before_projection(self) -> None:
        pages = [
            page(
                "Entity | Population | GDP\nAlpha | 991 | 42",
                url="https://one.example.test/a",
            ),
            page(
                "Entity | Population | GDP\nAlpha | 992 | 42",
                url="https://two.example.test/b",
            ),
        ]
        value = candidate.build_projection(QUESTION, pages)
        receipt = value["content_free_receipt"]
        self.assertEqual(receipt["conflicting_coordinate_count"], 1)
        self.assertEqual(receipt["admissible_bound_observation_count"], 2)
        ledger_projection = value["projection"].split("Entity | Population | GDP", 1)[0]
        self.assertNotIn('["Population [POP] @2024",', ledger_projection)
        self.assertIn('["GDP [GDP] @2024","42"]', ledger_projection)

    def test_duplicate_field_conflict_abstains_only_that_field(self) -> None:
        content = "Entity: Alpha\nPopulation: 991\nPopulation: 992\nGDP: 42"
        value = candidate.build_projection(QUESTION, [page(content)])
        receipt = value["content_free_receipt"]
        self.assertEqual(receipt["duplicate_field_conflict_count"], 1)
        self.assertEqual(receipt["admissible_bound_observation_count"], 1)
        ledger_projection = value["projection"].split("Entity: Alpha", 1)[0]
        self.assertNotIn('["Population [POP] @2024",', ledger_projection)
        self.assertIn('["GDP [GDP] @2024","42"]', ledger_projection)

    def test_unicode_normalization_preserves_binding_and_totals(self) -> None:
        question = "返回 Markdown 表格，列名为：实体｜人口［POP］ @2024｜面积［AREA］。"
        pages = [
            page("实体 | 人口 | 面积\nＡ城 | １⁄２ million | １２３ km²")
        ]
        value = candidate.build_projection(question, pages)
        receipt = value["content_free_receipt"]
        self.assertEqual(receipt["discovered_row_key_count"], 1)
        self.assertEqual(receipt["admissible_bound_observation_count"], 2)
        self.assertEqual(receipt["positive_signed_credit_count"], 0)

    def test_source_url_host_record_row_target_and_value_are_bound(self) -> None:
        value = candidate.build_projection(
            QUESTION,
            [page("Entity | Population | GDP\nAlpha | 991 | 42")],
        )
        record = value["record_ledger"][0]
        observation = value["admissible_observations"][0]
        self.assertEqual(record["source_url"], "https://data.example.test/report")
        self.assertEqual(record["source_host"], "data.example.test")
        self.assertEqual(observation["record_id"], record["record_id"])
        self.assertEqual(observation["row_key"], "Alpha")
        self.assertEqual(observation["target_label"], "Population [POP] @2024")
        self.assertEqual(observation["value"], "991")

    def test_stable_source_order_and_projection_caps_are_preserved(self) -> None:
        filler = "\n".join(f"Background {index} " + "x" * 180 for index in range(60))
        pages = [
            page(
                "Entity | Population | GDP\nAlpha | 991 | 42\n" + filler,
                url="https://first.example.test/a",
            ),
            page(
                "Entity | Population | GDP\nBeta | 881 | 37\n" + filler,
                url="https://second.example.test/b",
            ),
        ]
        value = candidate.build_projection(QUESTION, pages)
        self.assertLessEqual(value["projected_rendered_characters"], 30_000)
        self.assertLess(
            value["projection"].index("first.example.test/a"),
            value["projection"].index("second.example.test/b"),
        )
        parent_receipt = value["parent_projection_receipt"]
        self.assertEqual(parent_receipt["orphan_selected_table_continuation_block_count"], 0)
        self.assertEqual(parent_receipt["orphan_selected_context_dependent_block_count"], 0)

    def test_replay_and_nested_tamper_are_rejected(self) -> None:
        pages = [page("Entity | Population | GDP\nAlpha | 991 | 42")]
        value = candidate.build_projection(QUESTION, pages)
        self.assertEqual(
            candidate.validate_projection(value, question=QUESTION, pages=pages), value
        )
        for tampered in (
            copy.deepcopy(value),
            copy.deepcopy(value),
            copy.deepcopy(value),
        ):
            pass
        tampered_record = copy.deepcopy(value)
        tampered_record["record_ledger"][0]["row_key"] = "Injected"
        with self.assertRaises(ValueError):
            candidate.validate_projection(
                tampered_record, question=QUESTION, pages=pages, replay=False
            )
        tampered_observation = copy.deepcopy(value)
        tampered_observation["admissible_observations"][0]["value"] = "999"
        with self.assertRaises(ValueError):
            candidate.validate_projection(
                tampered_observation, question=QUESTION, pages=pages, replay=False
            )
        tampered_receipt = copy.deepcopy(value)
        tampered_receipt["content_free_receipt"]["positive_signed_credit_count"] = 1
        with self.assertRaises(ValueError):
            candidate.validate_projection(
                tampered_receipt, question=QUESTION, pages=pages, replay=False
            )

    def test_no_visible_schema_means_no_bound_or_positive_credit(self) -> None:
        value = candidate.build_projection(
            "Research Alpha and Beta and summarize the evidence.",
            [page("Entity | Population | GDP\nAlpha | 991 | 42")],
        )
        receipt = value["content_free_receipt"]
        self.assertEqual(receipt["visible_schema_column_count"], 0)
        self.assertEqual(receipt["admissible_bound_observation_count"], 0)
        self.assertEqual(receipt["shadow_information_gain_eligible_observation_count"], 0)
        self.assertEqual(receipt["unbound_observation_positive_credit_count"], 0)
        self.assertEqual(receipt["positive_signed_credit_count"], 0)

    def test_runtime_module_has_no_io_network_model_or_process_capability(self) -> None:
        path = ROOT / "src/deepwide_agent/v24939_schema_bound_record_ledger.py"
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
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
                {
                    "os",
                    "pathlib",
                    "socket",
                    "subprocess",
                    "requests",
                    "httpx",
                    "openai",
                    "importlib",
                    "runpy",
                }
            )
        )
        for forbidden in (
            "ground_truth",
            "question_type",
            "answer_key",
            "results.csv",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
