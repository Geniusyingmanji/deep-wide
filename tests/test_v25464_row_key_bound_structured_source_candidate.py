from __future__ import annotations

import ast
import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25464_row_key_bound_structured_source_candidate as target  # noqa: E402


COLUMNS = ("Package", "Version", "Authors", "Status")
BASE = (
    "```markdown\n"
    "| Package | Version | Authors | Status |\n"
    "| --- | --- | --- | --- |\n"
    "| alpha | 1.0 | Alice; Bob | Unknown |\n"
    "```"
)


def page(content: str, *, url: str = "https://registry.example/package/alpha", title: str = "alpha") -> dict[str, str]:
    return {"url": url, "title": title, "content": content}


class V25464RowKeyBoundStructuredSourceCandidateTests(unittest.TestCase):
    def test_parent_row_key_binds_detail_page_then_labelled_fields(self) -> None:
        value = target.build_application(
            BASE,
            columns=COLUMNS,
            pages=[page("Version: 2.0\nStatus: Stable")],
        )
        self.assertIn("| alpha | 2.0 | Alice; Bob | Stable |", value["candidate_prediction"])
        receipt = value["content_free_receipt"]
        self.assertEqual(receipt["applied_coordinate_count"], 2)
        registry = value["private_candidate_registry"]
        self.assertEqual(
            {(item["field"], item["identity_binding_kind"]) for item in registry["candidates"]},
            {
                ("Version", "unique_url_path_and_surface_page_binding"),
                ("Status", "unique_url_path_and_surface_page_binding"),
            },
        )

    def test_four_page_bound_structured_surfaces_are_supported(self) -> None:
        fixtures = {
            "horizontal": (
                "| Version | Status |\n| --- | --- |\n| 2.0 | Stable |"
            ),
            "vertical": "| Version | 2.0 |\n| Status | Stable |",
            "labelled": "Version: 2.0\nStatus: Stable",
            "json": '{"Version":"2.0","Status":"Stable"}',
        }
        for name, content in fixtures.items():
            with self.subTest(name=name):
                registry = target.build_candidate_registry(
                    BASE, columns=COLUMNS, pages=[page(content)]
                )
                self.assertEqual(
                    [(item["field"], item["exact_value"]) for item in registry["candidates"]],
                    [("Version", "2.0"), ("Status", "Stable")],
                )

    def test_wrong_path_wrong_surface_or_duplicate_coordinates_fail_closed(self) -> None:
        cases = {
            "wrong_path": [page("Status: Stable", url="https://registry.example/package/beta")],
            "wrong_surface": [page("Status: Stable", title="beta")],
            "duplicate": [
                page("Status: Stable"),
                page(
                    "Status: Stable",
                    url="https://registry.example/package/alpha/details",
                    title="alpha details",
                ),
            ],
        }
        for name, pages in cases.items():
            with self.subTest(name=name):
                value = target.build_application(BASE, columns=COLUMNS, pages=pages)
                self.assertEqual(value["candidate_prediction"], BASE)
                self.assertTrue(value["content_free_receipt"]["candidate_identity_handoff"])

    def test_explicit_identity_record_is_preserved_on_uniquely_bound_page(self) -> None:
        content = (
            "| Package | Version | Authors | Status |\n"
            "| --- | --- | --- | --- |\n"
            "| alpha | 2.0 | Alice; Bob | Stable |"
        )
        registry = target.build_candidate_registry(
            BASE, columns=COLUMNS, pages=[page(content)]
        )
        self.assertEqual(len(registry["candidates"]), 2)
        self.assertTrue(
            all(
                item["identity_binding_kind"]
                == "explicit_record_identity_and_unique_page_binding"
                for item in registry["candidates"]
            )
        )

    def test_conflict_unknown_list_collapse_and_surface_only_changes_fail_closed(self) -> None:
        fixtures = {
            "conflict": "Status: Stable\nStatus: Draft",
            "unknown": "Status: Unknown",
            "list_collapse": "Authors: Alice",
            "separator_only": "Authors: Alice, Bob",
            "case_only": "Version: 1.0",
        }
        for name, content in fixtures.items():
            with self.subTest(name=name):
                value = target.build_application(
                    BASE, columns=COLUMNS, pages=[page(content)]
                )
                self.assertEqual(value["candidate_prediction"], BASE)

    def test_cross_page_identity_and_field_join_is_impossible(self) -> None:
        pages = [
            page("alpha", url="https://registry.example/package/alpha", title="alpha"),
            page(
                "Status: Stable",
                url="https://registry.example/package/beta",
                title="beta",
            ),
        ]
        value = target.build_application(BASE, columns=COLUMNS, pages=pages)
        self.assertEqual(value["candidate_prediction"], BASE)

    def test_explicit_and_page_bound_coordinates_must_not_compete(self) -> None:
        content = (
            "| Package | Version | Authors | Status |\n"
            "| --- | --- | --- | --- |\n"
            "| alpha | 2.0 | Alice; Bob | Stable |\n\n"
            "Version: 2.0\nStatus: Stable"
        )
        value = target.build_application(
            BASE, columns=COLUMNS, pages=[page(content)]
        )
        self.assertEqual(value["candidate_prediction"], BASE)
        receipt = value["private_candidate_registry"]["content_free_receipt"]
        self.assertEqual(receipt["ambiguous_same_value_coordinate_count"], 2)

    def test_replay_and_tamper_fail_closed(self) -> None:
        pages = [page("Version: 2.0\nStatus: Stable")]
        value = target.build_application(BASE, columns=COLUMNS, pages=pages)
        self.assertEqual(
            target.validate_application(
                value, base_prediction=BASE, columns=COLUMNS, pages=pages
            ),
            value,
        )
        changed = copy.deepcopy(value)
        changed["private_candidate_registry"]["candidates"][0]["exact_value"] = "9.9"
        changed["private_candidate_registry"].pop("artifact_payload_sha256")
        changed["private_candidate_registry"]["artifact_payload_sha256"] = target.payload_sha256(
            changed["private_candidate_registry"]
        )
        changed.pop("artifact_payload_sha256")
        changed["artifact_payload_sha256"] = target.payload_sha256(changed)
        with self.assertRaises(ValueError):
            target.validate_application(changed)

    def test_pure_label_blind_module_has_no_external_capability(self) -> None:
        source = Path(target.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports: list[str] = []
        forbidden_accesses: list[str] = []
        forbidden_fields = {
            "category",
            "question_type",
            "task_category",
            "split",
            "ground_truth",
            "gold",
            "answer_key",
            "score",
            "reward",
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
            elif (
                isinstance(node, ast.Subscript)
                and isinstance(node.slice, ast.Constant)
                and node.slice.value in forbidden_fields
            ):
                forbidden_accesses.append(str(node.slice.value))
        self.assertEqual(forbidden_accesses, [])
        self.assertFalse(
            any(
                name == forbidden or name.startswith(forbidden + ".")
                for forbidden in (
                    "os",
                    "pathlib",
                    "subprocess",
                    "socket",
                    "requests",
                    "httpx",
                )
                for name in imports
            )
        )
        self.assertNotIn("model.complete", source)
        self.assertNotIn("search_many", source)
        self.assertNotIn("fetch_urls", source)


if __name__ == "__main__":
    unittest.main()
