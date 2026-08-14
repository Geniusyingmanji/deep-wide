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

from deepwide_agent import v25520_multirow_iana_detail_candidate as target  # noqa: E402


COLUMNS = ("Domain", "Type", "TLD Manager")
BASE = (
    "```markdown\n"
    "| Domain | Type | TLD Manager |\n"
    "| --- | --- | --- |\n"
    "| .amex | legacy sponsored domain | Former Registry One |\n"
    "| .americanfamily | retired country-code domain | Former Registry Two |\n"
    "```"
)


def page(
    content: str,
    *,
    identity: str = ".americanfamily",
    url: str | None = None,
    title: str | None = None,
) -> dict[str, str]:
    label = identity.removeprefix(".")
    return {
        "url": url or f"https://www.iana.org/domains/root/db/{label}.html",
        "title": title or f"{identity} Domain Delegation Data",
        "content": content,
    }


class V25520MultirowIanaDetailCandidateTests(unittest.TestCase):
    def test_long_key_page_changes_only_exactly_bound_row(self) -> None:
        pages = [
            page(
                ".americanfamily Domain Delegation Data\n"
                "TLD Type | generic top-level domain\n"
                "TLD Manager\n\nAmerican Family Mutual Insurance Company"
            )
        ]
        value = target.build_candidate(BASE, columns=COLUMNS, pages=pages)
        self.assertTrue(value["candidate_prediction_changed"])
        self.assertIn(
            "| .amex | legacy sponsored domain | Former Registry One |",
            value["candidate_prediction"],
        )
        self.assertIn(
            "| .americanfamily | generic top-level domain | American Family Mutual Insurance Company |",
            value["candidate_prediction"],
        )
        receipt = value["content_free_receipt"]
        self.assertEqual(receipt["identity_surface_bound_page_count"], 1)
        self.assertEqual(receipt["applied_coordinate_count"], 2)

    def test_hyphenated_arbitrary_length_key_and_labelled_shape_replay(self) -> None:
        base = BASE.replace(".americanfamily", ".xn--example-long")
        pages = [
            page(
                ".xn--example-long Domain Delegation Data\n"
                "Type: generic top-level domain",
                identity=".xn--example-long",
            )
        ]
        value = target.build_candidate(base, columns=COLUMNS, pages=pages)
        self.assertEqual(target.validate_candidate(value), value)
        self.assertIn(
            "| .xn--example-long | generic top-level domain | Former Registry Two |",
            value["candidate_prediction"],
        )

    def test_wrong_url_row_redirect_or_unbound_surface_fail_closed(self) -> None:
        fixtures = {
            "wrong_row": page(
                ".amex Domain Delegation Data\nType: generic top-level domain",
                identity=".amex",
                url="https://www.iana.org/domains/root/db/americanfamily.html",
            ),
            "redirect": page(
                ".americanfamily Domain Delegation Data\nType: generic top-level domain",
                url="https://www.iana.org/domains/root/db/americanfamily.html?redirect=1",
            ),
            "unbound": page(
                ".other Domain Delegation Data\nType: generic top-level domain",
                title=".other Domain Delegation Data",
            ),
        }
        for name, raw in fixtures.items():
            with self.subTest(name=name):
                value = target.build_candidate(BASE, columns=COLUMNS, pages=[raw])
                self.assertEqual(value["candidate_prediction"], BASE)
                self.assertEqual(
                    value["content_free_receipt"]["applied_coordinate_count"], 0
                )

    def test_duplicate_conflict_and_unknown_fail_closed_with_stage_counts(self) -> None:
        contents = {
            "duplicate": (
                ".americanfamily Domain Delegation Data\n"
                "TLD Type | generic\nTLD Type | generic"
            ),
            "conflict": (
                ".americanfamily Domain Delegation Data\n"
                "TLD Type | generic\nTLD Type | sponsored"
            ),
            "unknown": (
                ".americanfamily Domain Delegation Data\nTLD Type | Unknown"
            ),
        }
        expected = {
            "duplicate": "nonunique_or_unbound_quote_rejected_surface_count",
            "conflict": "conflicting_value_coordinate_count",
            "unknown": "unsafe_value_rejected_surface_count",
        }
        for name, content in contents.items():
            with self.subTest(name=name):
                value = target.build_candidate(
                    BASE, columns=COLUMNS, pages=[page(content)]
                )
                receipt = value["content_free_receipt"]
                self.assertFalse(value["candidate_prediction_changed"])
                self.assertEqual(receipt["available_candidate_count"], 0)
                self.assertGreaterEqual(receipt[expected[name]], 1)

    def test_unchanged_observation_is_counted_separately_from_parser_miss(self) -> None:
        value = target.build_candidate(
            BASE,
            columns=COLUMNS,
            pages=[
                page(
                    ".americanfamily Domain Delegation Data\n"
                    "Type: retired country-code domain"
                )
            ],
        )
        receipt = value["content_free_receipt"]
        self.assertEqual(receipt["raw_field_surface_count"], 1)
        self.assertEqual(receipt["evidence_closed_observation_count"], 1)
        self.assertEqual(receipt["unchanged_coordinate_count"], 1)
        self.assertEqual(receipt["available_candidate_count"], 0)

    def test_resealed_page_observation_receipt_or_credit_tamper_fails(self) -> None:
        value = target.build_candidate(
            BASE,
            columns=COLUMNS,
            pages=[
                page(
                    ".americanfamily Domain Delegation Data\n"
                    "Type: generic top-level domain"
                )
            ],
        )
        for kind in ("page", "observation", "receipt", "credit"):
            changed = copy.deepcopy(value)
            if kind == "page":
                changed["private_pages"][0]["url"] += "?x=1"
            elif kind == "observation":
                changed["private_observations"][0]["exact_value"] += "x"
            elif kind == "receipt":
                changed["content_free_receipt"]["raw_field_surface_count"] += 1
            else:
                changed["content_free_receipt"]["positive_signed_credit_count"] = 1
            changed["content_free_receipt"].pop("receipt_payload_sha256", None)
            changed["content_free_receipt"][
                "receipt_payload_sha256"
            ] = target.payload_sha256(changed["content_free_receipt"])
            changed.pop("artifact_payload_sha256")
            changed["artifact_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_candidate(changed)

    def test_pure_module_is_label_blind_and_has_no_effect_capability(self) -> None:
        contract = target.integration_contract()
        self.assertTrue(contract["multirow_arbitrary_length_tld_binding"])
        source_text = Path(target.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source_text)
        imports: list[str] = []
        privileged: list[str] = []
        forbidden = {
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
                and node.slice.value in forbidden
            ):
                privileged.append(str(node.slice.value))
        self.assertEqual(privileged, [])
        self.assertFalse(
            any(
                name == blocked or name.startswith(blocked + ".")
                for blocked in (
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
        self.assertNotIn("model.complete", source_text)
        self.assertNotIn("search_many", source_text)
        self.assertNotIn("fetch_urls", source_text)


if __name__ == "__main__":
    unittest.main()
