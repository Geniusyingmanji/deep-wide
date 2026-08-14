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

from deepwide_agent import v25483_row_key_iana_detail_candidate as target  # noqa: E402


COLUMNS = ("Domain", "Type", "TLD Manager")
QUESTION = (
    "Use public web search and the official IANA Root Zone Database to return "
    "one table. Columns exactly: Domain | Type | TLD Manager."
)
BASE = (
    "```markdown\n"
    "| Domain | Type | TLD Manager |\n"
    "| --- | --- | --- |\n"
    "| .af | Unknown | Old Manager |\n"
    "```"
)


def page(
    content: str,
    *,
    url: str = "https://www.iana.org/domains/root/db/af.html",
    title: str = ".af Domain Delegation Data",
) -> dict[str, str]:
    return {"url": url, "title": title, "content": content}


class V25483RowKeyIanaDetailCandidateTests(unittest.TestCase):
    def test_request_is_derived_from_completed_row_key_and_visible_authority(self) -> None:
        requests = target.request_vector(BASE, columns=COLUMNS, question=QUESTION)
        self.assertEqual(len(requests), 1)
        self.assertEqual(
            requests[0]["url"], "https://www.iana.org/domains/root/db/af.html"
        )
        self.assertNotIn("afghanistan", str(requests).casefold())

    def test_pipe_and_fused_adjacent_fields_apply_without_model_inference(self) -> None:
        content = (
            ".af Domain Delegation Data\n"
            "TLD Type | country-code top-level domain\n"
            "ccTLD Manager\n\nAfghanistan Network Information Center"
        )
        value = target.build_candidate(
            BASE, columns=COLUMNS, question=QUESTION, pages=[page(content)]
        )
        self.assertTrue(value["candidate_prediction_changed"])
        self.assertIn(
            "| .af | country-code top-level domain | Afghanistan Network Information Center |",
            value["candidate_prediction"],
        )
        receipt = value["content_free_receipt"]
        self.assertEqual(receipt["applied_coordinate_count"], 2)
        self.assertEqual(receipt["positive_signed_credit_count"], 0)

    def test_exact_labelled_field_and_replay_are_supported(self) -> None:
        pages = [page(".af Domain Delegation Data\nType: country-code")]
        value = target.build_candidate(
            BASE, columns=COLUMNS, question=QUESTION, pages=pages
        )
        self.assertEqual(
            target.validate_candidate(
                value,
                base_prediction=BASE,
                columns=COLUMNS,
                question=QUESTION,
                pages=pages,
            ),
            value,
        )
        self.assertIn("| .af | country-code | Old Manager |", value["candidate_prediction"])

    def test_missing_authority_invalid_row_redirect_unbound_or_unknown_fail_closed(self) -> None:
        fixtures = {
            "authority": (
                QUESTION.replace("IANA Root Zone Database", "public registry"),
                [page(".af Domain Delegation Data\nTLD Type | country-code")],
            ),
            "redirect": (
                QUESTION,
                [
                    page(
                        ".af Domain Delegation Data\nTLD Type | country-code",
                        url="https://www.iana.org/domains/root/db/af.html?redirect=1",
                    )
                ],
            ),
            "unbound": (
                QUESTION,
                [
                    page(
                        ".bh Domain Delegation Data\nTLD Type | country-code",
                        url="https://www.iana.org/domains/root/db/bh.html",
                        title=".bh Domain Delegation Data",
                    )
                ],
            ),
            "unknown": (
                QUESTION,
                [page(".af Domain Delegation Data\nTLD Type | Unknown")],
            ),
        }
        for name, (question, pages) in fixtures.items():
            with self.subTest(name=name):
                value = target.build_candidate(
                    BASE, columns=COLUMNS, question=question, pages=pages
                )
                self.assertEqual(value["candidate_prediction"], BASE)

    def test_duplicate_or_conflicting_coordinate_fails_closed(self) -> None:
        for content in (
            ".af Domain Delegation Data\nTLD Type | country-code\nTLD Type | country-code",
            ".af Domain Delegation Data\nTLD Type | country-code\nTLD Type | generic",
        ):
            value = target.build_candidate(
                BASE, columns=COLUMNS, question=QUESTION, pages=[page(content)]
            )
            self.assertEqual(value["candidate_prediction"], BASE)

    def test_resealed_page_observation_or_credit_tamper_fails(self) -> None:
        value = target.build_candidate(
            BASE,
            columns=COLUMNS,
            question=QUESTION,
            pages=[page(".af Domain Delegation Data\nTLD Type | country-code")],
        )
        for kind in ("page", "observation", "credit"):
            changed = copy.deepcopy(value)
            if kind == "page":
                changed["private_pages"][0]["url"] += "?x=1"
            elif kind == "observation":
                changed["private_observations"][0]["exact_value"] += "x"
            else:
                changed["content_free_receipt"]["positive_signed_credit_count"] = 1
            changed.pop("artifact_payload_sha256")
            changed["artifact_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_candidate(changed)

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
                name == forbidden_name or name.startswith(forbidden_name + ".")
                for forbidden_name in (
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
