from __future__ import annotations

import ast
import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent import v25440_key_anchored_metadata_candidate as target  # noqa: E402


COLUMNS = ("RFC", "Title", "Authors", "Status", "Stream", "Published")
BASE = (
    "```markdown\n"
    "| RFC | Title | Authors | Status | Stream | Published |\n"
    "| --- | --- | --- | --- | --- | --- |\n"
    "| RFC 9160 | Old | Old A; Old B | Unknown | IETF | April 2022 |\n"
    "| RFC 9161 | Beta | Bob | Proposed Standard | IETF | June 2022 |\n"
    "```"
)


def page(content: str, suffix: str = "9160") -> dict[str, str]:
    return {
        "url": f"https://www.rfc-editor.org/rfc/rfc{suffix}.html",
        "title": f"RFC {suffix}",
        "content": content,
    }


METADATA = (
    "RFC: 9160\n"
    "Category: Standards Track\n"
    "Published: May 2022\n"
    "ISSN: 2070-1721\n"
    "Authors: Alice    Bob\n"
    "\nAbstract follows."
)


class V25440KeyAnchoredMetadataCandidateTests(unittest.TestCase):
    def test_key_qualified_metadata_yields_atomic_authors_and_published(self) -> None:
        registry = target.build_candidate_registry(
            BASE, columns=COLUMNS, pages=[page(METADATA)]
        )
        candidates = registry["candidates"]
        self.assertEqual(len(candidates), 2)
        by_field = {item["field"]: item for item in candidates}
        self.assertEqual(by_field["Authors"]["exact_value"], "Alice; Bob")
        self.assertEqual(
            by_field["Authors"]["value_normalization_kind"],
            "ascii_multi_space_list_atomic",
        )
        self.assertEqual(by_field["Published"]["exact_value"], "May 2022")
        self.assertTrue(
            all(
                item["identity_derivation_kind"]
                == "exact_key_label_qualification"
                for item in candidates
            )
        )
        receipt = registry["content_free_receipt"]
        self.assertEqual(receipt["metadata_block_count"], 1)
        self.assertEqual(receipt["metadata_identity_qualified_count"], 1)
        self.assertEqual(receipt["metadata_value_normalized_count"], 1)

    def test_non_target_labels_are_skipped_but_never_aliased(self) -> None:
        content = (
            "RFC: 9160\nCategory: Experimental\nAuthor: Alice\n"
            "Heading: New Title\nStream: IAB\n"
        )
        registry = target.build_candidate_registry(
            BASE, columns=COLUMNS, pages=[page(content)]
        )
        self.assertEqual([item["field"] for item in registry["candidates"]], ["Stream"])
        receipt = registry["content_free_receipt"]
        self.assertFalse(
            receipt["singular_plural_status_category_title_heading_or_prose_alias_used"]
        )

    def test_raw_identity_can_exactly_name_the_existing_base_row(self) -> None:
        base = BASE.replace("RFC 9160", "9160")
        registry = target.build_candidate_registry(
            base, columns=COLUMNS, pages=[page(METADATA)]
        )
        self.assertEqual(len(registry["candidates"]), 2)
        self.assertTrue(
            all(
                item["identity_derivation_kind"] == "exact_visible_identity"
                and item["source_identity_label"] == "RFC"
                and item["row_identity"] == "9160"
                for item in registry["candidates"]
            )
        )

    def test_metadata_block_stops_at_first_non_labelled_line(self) -> None:
        content = (
            "RFC: 9160\nPublished: May 2022\nAbstract follows.\n"
            "Authors: Alice    Bob\n"
        )
        registry = target.build_candidate_registry(
            BASE, columns=COLUMNS, pages=[page(content)]
        )
        self.assertEqual(
            [(item["field"], item["exact_value"]) for item in registry["candidates"]],
            [("Published", "May 2022")],
        )

    def test_list_atomicity_requires_unique_equal_cardinality_atoms(self) -> None:
        cases = {
            "one_atom": "Authors: Alice",
            "cardinality_drop": "Authors: Alice    Bob    Carol",
            "duplicate_atom": "Authors: Alice    Alice",
            "tab_separator": "Authors: Alice\tBob",
        }
        for kind, authors in cases.items():
            content = "RFC: 9160\n" + authors + "\n"
            with self.subTest(kind=kind):
                registry = target.build_candidate_registry(
                    BASE, columns=COLUMNS, pages=[page(content)]
                )
                self.assertEqual(registry["candidates"], [])

    def test_safe_list_values_still_cannot_collapse_or_expand_cardinality(self) -> None:
        cases = {
            "collapse": "Authors: Alice",
            "expand": "Authors: Alice; Bob; Carol",
        }
        for kind, authors in cases.items():
            with self.subTest(kind=kind):
                registry = target.build_candidate_registry(
                    BASE,
                    columns=COLUMNS,
                    pages=[page("RFC: 9160\n" + authors + "\n")],
                )
                self.assertEqual(registry["candidates"], [])

    def test_parent_horizontal_candidate_is_preserved(self) -> None:
        content = (
            "| RFC | Title | Authors | Status | Stream | Published |\n"
            "| --- | --- | --- | --- | --- | --- |\n"
            "| RFC 9160 | New | Old A; Old B | Unknown | IETF | April 2022 |"
        )
        registry = target.build_candidate_registry(
            BASE, columns=COLUMNS, pages=[page(content)]
        )
        self.assertEqual(len(registry["candidates"]), 1)
        self.assertEqual(registry["candidates"][0]["field"], "Title")
        self.assertEqual(registry["content_free_receipt"]["parent_candidate_count"], 1)

    def test_multiple_source_coordinates_and_conflicts_fail_closed(self) -> None:
        same = [page(METADATA), page(METADATA, "9160-alt")]
        conflict = [
            page(METADATA),
            page(METADATA.replace("May 2022", "July 2022"), "9160-alt"),
        ]
        for kind, pages in (("same", same), ("conflict", conflict)):
            with self.subTest(kind=kind):
                registry = target.build_candidate_registry(
                    BASE, columns=COLUMNS, pages=pages
                )
                self.assertEqual(registry["candidates"], [])
                receipt = registry["content_free_receipt"]
                self.assertGreater(
                    receipt[
                        "ambiguous_same_value_coordinate_count"
                        if kind == "same"
                        else "conflicting_value_coordinate_count"
                    ],
                    0,
                )

    def test_duplicate_visible_fields_inside_one_block_fail_closed(self) -> None:
        for kind, second in (
            ("same", "Published: May 2022"),
            ("conflict", "Published: July 2022"),
        ):
            with self.subTest(kind=kind):
                content = f"RFC: 9160\nPublished: May 2022\n{second}\n"
                registry = target.build_candidate_registry(
                    BASE, columns=COLUMNS, pages=[page(content)]
                )
                self.assertEqual(registry["candidates"], [])
                receipt = registry["content_free_receipt"]
                self.assertEqual(
                    receipt["metadata_duplicate_visible_field_rejected_count"], 1
                )
                self.assertEqual(receipt["metadata_identity_rejected_count"], 1)

    def test_selector_only_chooses_ids_and_application_replays_normalization(self) -> None:
        registry = target.build_candidate_registry(
            BASE, columns=COLUMNS, pages=[page(METADATA)]
        )
        selected = [item["candidate_id"] for item in registry["candidates"]]
        selector = json.dumps({"candidate_ids": selected}, separators=(",", ":"))
        application = target.apply_candidate_selection(
            BASE,
            columns=COLUMNS,
            pages=[page(METADATA)],
            selector_output=selector,
        )
        self.assertNotEqual(application["candidate_prediction"], BASE)
        self.assertIn("Alice; Bob", application["candidate_prediction"])
        self.assertEqual(
            target.validate_application(
                application,
                base_prediction=BASE,
                columns=COLUMNS,
                pages=[page(METADATA)],
                selector_output=selector,
            ),
            application,
        )
        for invalid in (
            '{"candidate_ids":["C999"]}',
            '{"candidate_ids":["C001"],"value":"forged"}',
            '{"candidate_ids":["C001","C001"]}',
        ):
            observed = target.apply_candidate_selection(
                BASE, columns=COLUMNS, pages=[page(METADATA)], selector_output=invalid
            )
            self.assertEqual(observed["candidate_prediction"], BASE)

    def test_candidate_registry_and_application_tamper_fail(self) -> None:
        registry = target.build_candidate_registry(
            BASE, columns=COLUMNS, pages=[page(METADATA)]
        )
        changed = copy.deepcopy(registry)
        changed["candidates"][0]["exact_value"] = "forged"
        changed.pop("artifact_payload_sha256")
        changed["artifact_payload_sha256"] = target.payload_sha256(changed)
        with self.assertRaises(ValueError):
            target.validate_registry(changed)
        for name, replacement in (
            ("source_url", "http://www.rfc-editor.org/rfc/rfc9160.html"),
            ("source_host", "example.invalid"),
            ("source_field", "Published"),
            ("source_identity_label", 9160),
            ("raw_source_value", "Published"),
        ):
            with self.subTest(candidate_field=name):
                changed_candidate = copy.deepcopy(registry["candidates"][0])
                changed_candidate[name] = replacement
                changed_candidate.pop("candidate_payload_sha256")
                changed_candidate["candidate_payload_sha256"] = target.payload_sha256(
                    changed_candidate
                )
                with self.assertRaises(ValueError):
                    target.validate_candidate(changed_candidate)
        selector = json.dumps(
            {"candidate_ids": [item["candidate_id"] for item in registry["candidates"]]},
            separators=(",", ":"),
        )
        application = target.apply_candidate_selection(
            BASE, columns=COLUMNS, pages=[page(METADATA)], selector_output=selector
        )
        changed_app = copy.deepcopy(application)
        changed_app["candidate_prediction"] += "x"
        changed_app.pop("artifact_payload_sha256")
        changed_app["artifact_payload_sha256"] = target.payload_sha256(changed_app)
        with self.assertRaises(ValueError):
            target.validate_application(changed_app)

    def test_none_selector_can_be_replay_validated_as_an_invalid_noop(self) -> None:
        application = target.apply_candidate_selection(
            BASE, columns=COLUMNS, pages=[page(METADATA)], selector_output=None
        )
        self.assertEqual(application["candidate_prediction"], BASE)
        self.assertEqual(
            target.validate_application(
                application,
                base_prediction=BASE,
                columns=COLUMNS,
                pages=[page(METADATA)],
                selector_output=None,
            ),
            application,
        )

    def test_pure_label_blind_module_has_no_external_capability(self) -> None:
        source = (ROOT / "src/deepwide_agent/v25440_key_anchored_metadata_candidate.py").read_text()
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
                {"os", "subprocess", "socket", "requests", "urllib", "http"}
            )
        )
        self.assertNotIn("question_type", source)
        self.assertNotIn("ground_truth", source)
        self.assertNotIn("historical_correctness", source)


if __name__ == "__main__":
    unittest.main()
