from __future__ import annotations

import ast
import copy
import inspect
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25432_source_authoritative_field_candidate as target  # noqa: E402


COLUMNS = ("Package", "Version", "Authors", "Status")


def table(
    *,
    identity: str = "alpha",
    version: str = "1.0",
    authors: str = "A. One; B. Two",
    status: str = "Unknown",
) -> str:
    return (
        "```markdown\n"
        "| Package | Version | Authors | Status |\n"
        "| --- | --- | --- | --- |\n"
        f"| {identity} | {version} | {authors} | {status} |\n"
        "```"
    )


def page(content: str, *, name: str = "record") -> dict[str, str]:
    return {
        "url": f"https://registry.example/{name}",
        "title": name,
        "content": content,
    }


class V25432SourceAuthoritativeFieldCandidateTests(unittest.TestCase):
    def test_exact_horizontal_table_builds_unique_source_candidates(self) -> None:
        source = (
            "| Package | Version | Authors | Status |\n"
            "| --- | --- | --- | --- |\n"
            "| alpha | 2.0 | A. One; B. Two | Stable |"
        )
        value = target.build_candidate_registry(
            table(), columns=COLUMNS, pages=[page(source)]
        )
        self.assertEqual(
            [(item["candidate_id"], item["field"], item["exact_value"])
             for item in value["candidates"]],
            [("C001", "Version", "2.0"), ("C002", "Status", "Stable")],
        )
        for candidate in value["candidates"]:
            self.assertIn(candidate["source_identity"], candidate["exact_quote"])
            self.assertIn(candidate["source_field"], candidate["exact_quote"])
            self.assertIn(candidate["exact_value"], candidate["exact_quote"])
            self.assertEqual(candidate["source_host"], "registry.example")
        receipt = value["content_free_receipt"]
        self.assertEqual(receipt["additional_model_requests"], 0)
        self.assertEqual(receipt["additional_fetch_calls"], 0)
        self.assertEqual(receipt["positive_signed_credit_count"], 0)

    def test_vertical_labelled_and_json_records_are_mechanically_extracted(self) -> None:
        fixtures = {
            "vertical": "| Package | alpha |\n| Version | 2.0 |\n| Status | Stable |",
            "labelled": "## alpha\nVersion: 2.0\nStatus: Stable",
            "json": '{"Package":"alpha","Version":"2.0","Status":"Stable"}',
        }
        for name, content in fixtures.items():
            with self.subTest(name=name):
                value = target.build_candidate_registry(
                    table(), columns=COLUMNS, pages=[page(content, name=name)]
                )
                self.assertEqual(
                    [(item["field"], item["exact_value"])
                     for item in value["candidates"]],
                    [("Version", "2.0"), ("Status", "Stable")],
                )

    def test_unknown_wrong_identity_and_list_collapse_fail_closed(self) -> None:
        fixtures = {
            "unknown": "## alpha\nStatus: Unknown",
            "wrong_identity": "## beta\nStatus: Stable",
            "list_collapse": "## alpha\nAuthors: A. One",
        }
        for name, content in fixtures.items():
            with self.subTest(name=name):
                value = target.build_candidate_registry(
                    table(), columns=COLUMNS, pages=[page(content, name=name)]
                )
                self.assertEqual(value["candidates"], [])
                applied = target.apply_candidate_selection(
                    table(),
                    columns=COLUMNS,
                    pages=[page(content, name=name)],
                    selector_output='{"candidate_ids":[]}',
                )
                self.assertEqual(applied["candidate_prediction"], table())
                self.assertTrue(
                    applied["content_free_receipt"]["candidate_identity_handoff"]
                )
        collapsed = target.build_candidate_registry(
            table(),
            columns=COLUMNS,
            pages=[page(fixtures["list_collapse"], name="collapse")],
        )
        self.assertEqual(
            collapsed["content_free_receipt"][
                "list_collapse_rejected_coordinate_count"
            ],
            1,
        )

    def test_conflicting_or_multiple_source_coordinates_fail_closed(self) -> None:
        fixtures = {
            "conflict": "## alpha\nStatus: Stable\n\n## alpha\nStatus: Draft",
            "same_value_two_coordinates": (
                "## alpha\nStatus: Stable\n\n## alpha\nstatus: Stable"
            ),
        }
        for name, content in fixtures.items():
            with self.subTest(name=name):
                value = target.build_candidate_registry(
                    table(), columns=COLUMNS, pages=[page(content, name=name)]
                )
                self.assertEqual(value["candidates"], [])
        conflict = target.build_candidate_registry(
            table(), columns=COLUMNS, pages=[page(fixtures["conflict"])]
        )["content_free_receipt"]
        ambiguous = target.build_candidate_registry(
            table(),
            columns=COLUMNS,
            pages=[page(fixtures["same_value_two_coordinates"], name="ambiguous")],
        )["content_free_receipt"]
        self.assertEqual(conflict["conflicting_value_coordinate_count"], 1)
        self.assertEqual(ambiguous["ambiguous_same_value_coordinate_count"], 1)

    def test_selector_can_only_choose_ids_and_values_come_from_registry(self) -> None:
        pages = [page("## alpha\nVersion: 2.0\nStatus: Stable")]
        selected = target.apply_candidate_selection(
            table(),
            columns=COLUMNS,
            pages=pages,
            selector_output='{"candidate_ids":["C002"]}',
        )
        self.assertIn(
            "| alpha | 1.0 | A. One; B. Two | Stable |",
            selected["candidate_prediction"],
        )
        self.assertEqual(selected["content_free_receipt"]["applied_coordinate_count"], 1)
        malicious = '{"candidate_ids":["C001"],"value":"9.9"}'
        rejected = target.apply_candidate_selection(
            table(), columns=COLUMNS, pages=pages, selector_output=malicious
        )
        self.assertEqual(rejected["candidate_prediction"], table())
        self.assertFalse(rejected["content_free_receipt"]["selector_strictly_valid"])

    def test_empty_unknown_duplicate_or_malformed_selection_is_byte_exact_noop(self) -> None:
        pages = [page("## alpha\nStatus: Stable")]
        outputs = (
            '{"candidate_ids":[]}',
            '{"candidate_ids":["C999"]}',
            '{"candidate_ids":["C001","C001"]}',
            '{"candidate_ids":["C001"],"new_value":"Draft"}',
            "C001",
            None,
        )
        for output in outputs:
            with self.subTest(output=output):
                value = target.apply_candidate_selection(
                    table(), columns=COLUMNS, pages=pages, selector_output=output
                )
                self.assertEqual(value["candidate_prediction"], table())
                self.assertTrue(
                    value["content_free_receipt"]["candidate_identity_handoff"]
                )

    def test_shape_key_and_duplicate_base_identity_are_rejected(self) -> None:
        duplicate = table()[:-3] + "\n| alpha | 1.1 | A. One; B. Two | Unknown |\n```"
        with self.assertRaises(ValueError):
            target.build_candidate_registry(
                duplicate,
                columns=COLUMNS,
                pages=[page("## alpha\nStatus: Stable")],
            )
        wrong = target.build_candidate_registry(
            table().replace("| alpha |", "| beta |"),
            columns=COLUMNS,
            pages=[page("## alpha\nStatus: Stable")],
        )
        self.assertEqual(wrong["candidates"], [])

    def test_page_quote_registry_and_application_tamper_fail(self) -> None:
        pages = [page("## alpha\nStatus: Stable")]
        registry = target.build_candidate_registry(
            table(), columns=COLUMNS, pages=pages
        )
        changed = copy.deepcopy(registry)
        changed["candidates"][0]["exact_value"] = "Draft"
        changed["candidates"][0].pop("candidate_payload_sha256")
        changed["candidates"][0]["candidate_payload_sha256"] = target.payload_sha256(
            changed["candidates"][0]
        )
        changed.pop("artifact_payload_sha256")
        changed["artifact_payload_sha256"] = target.payload_sha256(changed)
        with self.assertRaises(ValueError):
            target.validate_registry(changed)
        application = target.apply_candidate_selection(
            table(),
            columns=COLUMNS,
            pages=pages,
            selector_output='{"candidate_ids":["C001"]}',
        )
        changed_application = copy.deepcopy(application)
        changed_application["candidate_prediction"] = table(status="Draft")
        changed_application["candidate_prediction_sha256"] = target.hashlib.sha256(
            changed_application["candidate_prediction"].encode()
        ).hexdigest()
        changed_application.pop("artifact_payload_sha256")
        changed_application["artifact_payload_sha256"] = target.payload_sha256(
            changed_application
        )
        with self.assertRaises(ValueError):
            target.validate_application(changed_application)

    def test_label_blind_pure_module_has_no_forbidden_capability(self) -> None:
        source = inspect.getsource(target)
        tree = ast.parse(source)
        imports = {
            alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        self.assertTrue(
            imports.isdisjoint(
                {
                    "os",
                    "pathlib",
                    "subprocess",
                    "socket",
                    "requests",
                    "urllib.request",
                    "httpx",
                }
            )
        )
        forbidden_literals = {
            "question_type",
            "ground_truth",
            "answer_key",
            "results.csv",
            "task_category",
        }
        literals = {
            node.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        }
        self.assertTrue(forbidden_literals.isdisjoint(literals))
        self.assertNotIn("model.complete", source)
        self.assertNotIn("search_many", source)
        self.assertNotIn("fetch_urls", source)
        self.assertIn("positive_signed_credit_count", source)


if __name__ == "__main__":
    unittest.main()
