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

from deepwide_agent import v25499_generic_mechanical_field_candidate as target  # noqa: E402


COLUMNS = ("Package", "Version", "Authors", "Status")
BASE = (
    "```markdown\n"
    "| Package | Version | Authors | Status |\n"
    "| --- | --- | --- | --- |\n"
    "| alpha | 1.0 | Unknown | Pending |\n"
    "```"
)


def page(content: str, *, suffix: str = "metadata") -> dict[str, str]:
    return {
        "url": f"https://registry.example/packages/alpha/{suffix}",
        "title": "alpha package record",
        "content": f"alpha package record\n{content}",
    }


class V25499GenericMechanicalFieldCandidateTests(unittest.TestCase):
    def test_fused_pipe_qualified_labelled_and_adjacent_fields_apply(self) -> None:
        pages = [
            page(
                "pkgVersion | 2.0\n"
                "Package Authors: Alice; Bob\n"
                "Status\n\nStable"
            )
        ]
        value = target.build_application(BASE, columns=COLUMNS, pages=pages)
        self.assertIn(
            "| alpha | 2.0 | Alice; Bob | Stable |",
            value["candidate_prediction"],
        )
        receipt = value["private_candidate_registry"]["content_free_receipt"]
        self.assertEqual(receipt["applied_coordinate_count"], 3)
        self.assertEqual(receipt["generic_mechanical_observation_count"], 3)
        self.assertEqual(receipt["positive_signed_credit_count"], 0)

    def test_parent_exact_and_separate_pipe_candidates_are_preserved(self) -> None:
        for content in ("Version: 2.0", "Package Version | 2.0"):
            with self.subTest(content=content):
                value = target.build_application(
                    BASE, columns=COLUMNS, pages=[page(content)]
                )
                self.assertIn("| alpha | 2.0 |", value["candidate_prediction"])

    def test_same_grammar_is_page_agnostic_for_parent_or_detail_inputs(self) -> None:
        content = "pkgVersion | 2.0\nStatus\n\nStable"
        parent_page = page(content, suffix="index/alpha")
        detail_page = page(content, suffix="detail")
        for supplied in ([parent_page], [detail_page]):
            with self.subTest(url=supplied[0]["url"]):
                value = target.build_application(
                    BASE, columns=COLUMNS, pages=supplied
                )
                self.assertIn("| alpha | 2.0 | Unknown | Stable |", value["candidate_prediction"])

    def test_two_qualifiers_partial_suffix_unknown_or_unbound_fail_closed(self) -> None:
        fixtures = {
            "two_qualifiers": [page("Official Package Version: 2.0")],
            "partial_suffix": [page("Vers: 2.0")],
            "unknown": [page("pkgVersion | Unknown")],
            "unbound": [
                {
                    "url": "https://registry.example/packages/beta/metadata",
                    "title": "beta package record",
                    "content": "beta package record\npkgVersion | 2.0",
                }
            ],
        }
        for name, pages in fixtures.items():
            with self.subTest(name=name):
                value = target.build_application(BASE, columns=COLUMNS, pages=pages)
                self.assertEqual(value["candidate_prediction"], BASE)

    def test_duplicate_or_conflicting_coordinate_fails_closed(self) -> None:
        for content in (
            "pkgVersion | 2.0\npkgVersion | 2.0",
            "pkgVersion | 2.0\npkgVersion | 3.0",
        ):
            with self.subTest(content=content):
                value = target.build_application(
                    BASE, columns=COLUMNS, pages=[page(content)]
                )
                self.assertEqual(value["candidate_prediction"], BASE)

    def test_replay_and_resealed_candidate_or_credit_tamper_fail(self) -> None:
        pages = [page("pkgVersion | 2.0")]
        value = target.build_application(BASE, columns=COLUMNS, pages=pages)
        self.assertEqual(
            target.validate_application(
                value, base_prediction=BASE, columns=COLUMNS, pages=pages
            ),
            value,
        )
        for kind in ("candidate", "credit"):
            changed = copy.deepcopy(value)
            if kind == "candidate":
                item = changed["private_candidate_registry"]["candidates"][0]
                item["source_kind"] = "generic_qualified_same_line_labelled_record"
                item.pop("candidate_payload_sha256")
                item["candidate_payload_sha256"] = target.payload_sha256(item)
                registry = changed["private_candidate_registry"]
                registry.pop("artifact_payload_sha256")
                registry["artifact_payload_sha256"] = target.payload_sha256(registry)
            else:
                changed["private_candidate_registry"]["content_free_receipt"][
                    "positive_signed_credit_count"
                ] = 1
            changed.pop("artifact_payload_sha256")
            changed["artifact_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_application(changed)

    def test_pure_module_is_label_blind_and_has_no_effect_capability(self) -> None:
        source = Path(target.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
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
                name == bad or name.startswith(bad + ".")
                for bad in ("os", "pathlib", "subprocess", "socket", "requests", "httpx")
                for name in imports
            )
        )
        self.assertNotIn("model.complete", source)
        self.assertNotIn("search_many", source)
        self.assertNotIn("fetch_urls", source)


if __name__ == "__main__":
    unittest.main()
