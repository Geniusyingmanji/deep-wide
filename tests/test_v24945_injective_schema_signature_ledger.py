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

from deepwide_agent import native_search  # noqa: E402
from deepwide_agent import v24942_compact_schema_bound_record_ledger as exact  # noqa: E402
from deepwide_agent import v24945_injective_schema_signature_ledger as candidate  # noqa: E402


QUESTION = (
    "Return exactly one Markdown table. Column names: "
    "Country or area | Total population [SP.POP.TOTL] @2020 | "
    "Surface area [AG.SRF.TOTL.K2] @2020."
)


def page(content: str, *, url: str = "https://data.example.test/table") -> dict[str, str]:
    return {"title": "Official data", "url": url, "content": content}


class V24945InjectiveSchemaSignatureLedgerTests(unittest.TestCase):
    def test_native_html_layout_recovers_reordered_semantic_headers(self) -> None:
        _title, text = native_search.html_to_text(
            "<table><tr><th>Area or Country</th><th>Population, total</th>"
            "<th>Area, surface</th></tr><tr><td>Alpha</td><td>991</td>"
            "<td>42</td></tr><tr><td>Beta</td><td>881</td><td>37</td>"
            "</tr></table>"
        )
        old = exact.build_projection(QUESTION, [page(text)])
        new = candidate.build_projection(QUESTION, [page(text)])
        self.assertEqual(old["admissible_bound_observation_count"], 0)
        receipt = new["content_free_receipt"]
        self.assertEqual(receipt["pipe_group_count"], 1)
        self.assertEqual(receipt["signature_header_bound_table_count"], 1)
        self.assertEqual(receipt["valid_width_table_row_count"], 2)
        self.assertEqual(receipt["discovered_row_key_count"], 2)
        self.assertEqual(receipt["admissible_bound_observation_count"], 4)
        self.assertEqual(receipt["retained_admissible_bound_observation_count"], 4)

    def test_exact_parent_behavior_is_preserved(self) -> None:
        content = (
            "Country or area | Total population | Surface area\n"
            "Alpha | 991 | 42\nBeta | 881 | 37"
        )
        old = exact.build_projection(QUESTION, [page(content)])
        new = candidate.build_projection(QUESTION, [page(content)])
        self.assertEqual(
            old["admissible_bound_observation_count"],
            new["admissible_bound_observation_count"],
        )
        self.assertEqual(
            new["content_free_receipt"]["exact_header_bound_table_count"], 1
        )
        self.assertEqual(
            new["content_free_receipt"]["signature_header_bound_table_count"], 0
        )

    def test_single_token_near_match_does_not_bind(self) -> None:
        question = "Column names: Country | Population [POP] @2020."
        value = candidate.build_projection(
            question, [page("Nation | Populations\nAlpha | 991")]
        )
        self.assertEqual(value["admissible_bound_observation_count"], 0)

    def test_shared_visible_signature_fails_closed(self) -> None:
        question = (
            "Column names: Country | Total population [P20] @2020 | "
            "Population total [P21] @2021."
        )
        value = candidate.build_projection(
            question,
            [page("Country | Population, total\nAlpha | 991")],
        )
        receipt = value["content_free_receipt"]
        self.assertGreaterEqual(receipt["ambiguous_header_mapping_count"], 1)
        self.assertEqual(receipt["header_bound_table_count"], 0)
        self.assertEqual(receipt["admissible_bound_observation_count"], 0)

    def test_duplicate_page_target_mapping_fails_closed(self) -> None:
        value = candidate.build_projection(
            QUESTION,
            [
                page(
                    "Country or area | Population, total | Total population\n"
                    "Alpha | 991 | 991"
                )
            ],
        )
        receipt = value["content_free_receipt"]
        self.assertGreaterEqual(receipt["ambiguous_header_mapping_count"], 1)
        self.assertEqual(receipt["admissible_bound_observation_count"], 0)

    def test_wrong_width_and_cross_page_join_fail_closed(self) -> None:
        wrong = candidate.build_projection(
            QUESTION,
            [page("Area or Country | Population, total | Area, surface\nAlpha | 991")],
        )
        self.assertEqual(wrong["malformed_table_row_count"], 1)
        self.assertEqual(wrong["admissible_bound_observation_count"], 0)
        cross = candidate.build_projection(
            QUESTION,
            [
                page("Area or Country: Alpha", url="https://one.example.test/a"),
                page(
                    "Population, total: 991\nArea, surface: 42",
                    url="https://two.example.test/b",
                ),
            ],
        )
        self.assertEqual(cross["admissible_bound_observation_count"], 0)

    def test_signature_labelled_record_is_contiguous_and_bound(self) -> None:
        value = candidate.build_projection(
            QUESTION,
            [
                page(
                    "Area or Country: Alpha\nPopulation, total: 991\n"
                    "Area, surface: 42"
                )
            ],
        )
        receipt = value["content_free_receipt"]
        self.assertEqual(receipt["signature_identity_label_bound_record_count"], 1)
        self.assertEqual(receipt["admissible_bound_observation_count"], 2)

    def test_conflicting_signature_coordinate_is_omitted(self) -> None:
        pages = [
            page(
                "Area or Country | Population, total | Area, surface\n"
                "Alpha | 991 | 42",
                url="https://one.example.test/a",
            ),
            page(
                "Area or Country | Population, total | Area, surface\n"
                "Alpha | 992 | 42",
                url="https://two.example.test/b",
            ),
        ]
        value = candidate.build_projection(QUESTION, pages)
        self.assertEqual(value["conflicting_coordinate_count"], 1)
        self.assertEqual(value["admissible_bound_observation_count"], 2)
        ledger = value["projection"].split("Area or Country |", 1)[0]
        self.assertNotIn('[1,"991"]', ledger)
        self.assertNotIn('[1,"992"]', ledger)
        self.assertIn('[2,"42"]', ledger)

    def test_replay_tamper_caps_and_entropy_credit(self) -> None:
        pages = [
            page(
                "Area or Country | Population, total | Area, surface\n"
                "Alpha | 991 | 42"
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
        tampered = copy.deepcopy(value)
        tampered["record_ledger"][0]["row_key"] = "Injected"
        with self.assertRaises(ValueError):
            candidate.validate_projection(
                tampered, question=QUESTION, pages=pages, replay=False
            )

    def test_runtime_module_has_no_io_network_model_or_process_capability(self) -> None:
        source = (
            ROOT / "src/deepwide_agent/v24945_injective_schema_signature_ledger.py"
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
