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

from deepwide_agent import v24945_injective_schema_signature_ledger as parent  # noqa: E402
from deepwide_agent import v24949_mutual_partial_signature_ledger as candidate  # noqa: E402


QUESTION = (
    "Return exactly one Markdown table. Column names: "
    "Country or area | Cohort | ISO3 | "
    "Agricultural land [AG.LND.AGRI.ZS] @2021."
)


def page(content: str, *, url: str = "https://data.example.test/table") -> dict[str, str]:
    return {"title": "Official data", "url": url, "content": content}


class V24949MutualPartialSignatureLedgerTests(unittest.TestCase):
    def test_native_header_with_literal_scope_suffix_is_bound(self) -> None:
        content = (
            "Area or Country | Cohort | ISO3 | Agricultural land (% of land area)\n"
            "Alpha | C01 | ALP | 44.2\nBeta | X01 | BET | 31.8"
        )
        old = parent.build_projection(QUESTION, [page(content)])
        new = candidate.build_projection(QUESTION, [page(content)])
        self.assertEqual(old["admissible_bound_observation_count"], 4)
        self.assertEqual(new["admissible_bound_observation_count"], 6)
        receipt = new["content_free_receipt"]
        self.assertEqual(receipt["partial_header_bound_table_count"], 1)
        self.assertEqual(receipt["discovered_row_key_count"], 2)
        self.assertEqual(receipt["retained_admissible_bound_observation_count"], 6)
        self.assertTrue(
            all(
                record["binding_kind"]
                == "mutually_unique_partial_signature_header_bound_table"
                for record in new["record_ledger"]
            )
        )

    def test_visible_header_may_be_the_strict_superset(self) -> None:
        question = (
            "Column names: Country or area | Cohort | ISO3 | "
            "Agricultural land percent land area [AG.LND.AGRI.ZS] @2021."
        )
        value = candidate.build_projection(
            question,
            [
                page(
                    "Area or Country | Cohort | ISO3 | Agricultural land\n"
                    "Alpha | C01 | ALP | 44.2"
                )
            ],
        )
        self.assertEqual(value["partial_header_bound_table_count"], 1)
        self.assertEqual(value["admissible_bound_observation_count"], 3)

    def test_both_sides_with_different_extra_tokens_do_not_bind(self) -> None:
        question = (
            "Column names: Country or area | Agricultural land share "
            "[AG.LND.AGRI.ZS] @2021."
        )
        value = candidate.build_projection(
            question,
            [page("Area or Country | Agricultural land percent\nAlpha | 44.2")],
        )
        self.assertEqual(value["partial_header_bound_table_count"], 0)
        self.assertEqual(value["admissible_bound_observation_count"], 0)

    def test_competing_visible_columns_fail_closed(self) -> None:
        question = (
            "Column names: Country or area | Agricultural land male share | "
            "Agricultural land female share."
        )
        value = candidate.build_projection(
            question,
            [page("Area or Country | Agricultural land\nAlpha | 44.2")],
        )
        receipt = value["content_free_receipt"]
        self.assertGreaterEqual(receipt["partial_ambiguous_header_mapping_count"], 1)
        self.assertEqual(receipt["header_bound_table_count"], 0)
        self.assertEqual(receipt["admissible_bound_observation_count"], 0)

    def test_two_page_cells_competing_for_one_column_fail_closed(self) -> None:
        value = candidate.build_projection(
            QUESTION,
            [
                page(
                    "Area or Country | Cohort | ISO3 | Agricultural land percent | "
                    "Agricultural land share\nAlpha | C01 | ALP | 44.2 | 44.2"
                )
            ],
        )
        receipt = value["content_free_receipt"]
        self.assertGreaterEqual(receipt["partial_ambiguous_header_mapping_count"], 1)
        self.assertEqual(receipt["header_bound_table_count"], 0)

    def test_more_than_three_extra_tokens_fail_closed(self) -> None:
        value = candidate.build_projection(
            QUESTION,
            [
                page(
                    "Area or Country | Cohort | ISO3 | "
                    "Agricultural land percent of total national geographic area\n"
                    "Alpha | C01 | ALP | 44.2"
                )
            ],
        )
        self.assertEqual(value["partial_header_bound_table_count"], 0)
        # Exact Cohort and ISO3 remain admissible under the parent behavior.
        self.assertEqual(value["admissible_bound_observation_count"], 2)

    def test_single_token_and_non_ascii_partial_edges_are_disabled(self) -> None:
        single = candidate.build_projection(
            "Column names: Country | Population.",
            [page("Country | Population persons\nAlpha | 10")],
        )
        self.assertEqual(single["partial_header_bound_table_count"], 0)
        non_ascii = candidate.build_projection(
            "Column names: 国家 地区 | 农业 用地.",
            [page("国家 地区 名称 | 农业 用地 百分比\n甲 | 10")],
        )
        self.assertEqual(non_ascii["partial_header_bound_table_count"], 0)

    def test_exact_and_full_signature_parent_behavior_is_preserved(self) -> None:
        exact_content = (
            "Country or area | Cohort | ISO3 | Agricultural land\n"
            "Alpha | C01 | ALP | 44.2"
        )
        old_exact = parent.build_projection(QUESTION, [page(exact_content)])
        new_exact = candidate.build_projection(QUESTION, [page(exact_content)])
        self.assertEqual(old_exact["projection"], new_exact["projection"])
        self.assertEqual(new_exact["partial_header_bound_table_count"], 0)
        signature_content = (
            "Area or Country | Cohort | ISO3 | Land agricultural\n"
            "Alpha | C01 | ALP | 44.2"
        )
        old_signature = parent.build_projection(QUESTION, [page(signature_content)])
        new_signature = candidate.build_projection(QUESTION, [page(signature_content)])
        self.assertEqual(old_signature["projection"], new_signature["projection"])
        self.assertEqual(new_signature["signature_header_bound_table_count"], 1)
        self.assertEqual(new_signature["partial_header_bound_table_count"], 0)

    def test_partial_binding_is_disabled_for_loose_labelled_records(self) -> None:
        value = candidate.build_projection(
            QUESTION,
            [
                page(
                    "Country or area: Alpha\nCohort: C01\nISO3: ALP\n"
                    "Agricultural land percent: 44.2"
                )
            ],
        )
        self.assertEqual(value["partial_header_bound_table_count"], 0)
        self.assertEqual(value["admissible_bound_observation_count"], 2)
        self.assertNotIn("44.2", [x["value"] for x in value["admissible_observations"]])

    def test_wrong_width_cross_page_and_conflict_fail_closed(self) -> None:
        wrong = candidate.build_projection(
            QUESTION,
            [
                page(
                    "Area or Country | Cohort | ISO3 | Agricultural land percent\n"
                    "Alpha | C01 | ALP"
                )
            ],
        )
        self.assertEqual(wrong["malformed_table_row_count"], 1)
        self.assertEqual(wrong["admissible_bound_observation_count"], 0)
        cross = candidate.build_projection(
            QUESTION,
            [
                page(
                    "Area or Country | Cohort | ISO3 | Agricultural land percent",
                    url="https://one.example.test/a",
                ),
                page(
                    "Alpha | C01 | ALP | 44.2",
                    url="https://two.example.test/b",
                ),
            ],
        )
        self.assertEqual(cross["admissible_bound_observation_count"], 0)
        conflict = candidate.build_projection(
            QUESTION,
            [
                page(
                    "Area or Country | Cohort | ISO3 | Agricultural land percent\n"
                    "Alpha | C01 | ALP | 44.2",
                    url="https://one.example.test/a",
                ),
                page(
                    "Area or Country | Cohort | ISO3 | Agricultural land percent\n"
                    "Alpha | C01 | ALP | 45.2",
                    url="https://two.example.test/b",
                ),
            ],
        )
        self.assertEqual(conflict["conflicting_coordinate_count"], 1)
        values = [x["value"] for x in conflict["admissible_observations"]]
        self.assertNotIn("44.2", values)
        self.assertNotIn("45.2", values)

    def test_replay_tamper_caps_and_entropy_credit(self) -> None:
        pages = [
            page(
                "Area or Country | Cohort | ISO3 | Agricultural land percent\n"
                "Alpha | C01 | ALP | 44.2"
            )
        ]
        value = candidate.build_projection(QUESTION, pages)
        self.assertEqual(
            candidate.validate_projection(value, question=QUESTION, pages=pages), value
        )
        self.assertLessEqual(value["projected_rendered_characters"], 30_000)
        receipt = value["content_free_receipt"]
        self.assertEqual(receipt["positive_signed_credit_count"], 0)
        self.assertEqual(receipt["unbound_observation_positive_credit_count"], 0)
        self.assertFalse(receipt["synonym_or_unit_dictionary_applied"])
        tampered = copy.deepcopy(value)
        tampered["record_ledger"][0]["row_key"] = "Injected"
        with self.assertRaises(ValueError):
            candidate.validate_projection(
                tampered, question=QUESTION, pages=pages, replay=False
            )

    def test_runtime_module_has_no_io_network_model_or_process_capability(self) -> None:
        source = (
            ROOT / "src/deepwide_agent/v24949_mutual_partial_signature_ledger.py"
        ).read_text(encoding="utf-8")
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
                    "runpy",
                    "importlib",
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
