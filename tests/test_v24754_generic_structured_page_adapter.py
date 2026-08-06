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

from deepwide_agent import v24754_generic_structured_page_adapter as target  # noqa: E402


BASELINE = """```markdown
| Organization | Founded | Country |
| --- | --- | --- |
| Alpha Institute | Unknown | Existing |
| Beta Labs | Unknown | Unknown |
```"""


def page(host: str, content: str, path: str = "/record") -> dict[str, object]:
    return {
        "final_url": f"https://{host}{path}",
        "content": content,
        "fetch_integrity": True,
    }


class V24754GenericStructuredPageAdapterTests(unittest.TestCase):
    def test_two_independent_exact_tables_fill_only_unknown(self) -> None:
        content = """| Organization | Founded | Country |
| --- | --- | --- |
| Alpha Institute | 1999 | Changed |
| Beta Labs | 2001 | Canada |"""
        value = target.build_generic_structured_page_binding(
            BASELINE,
            [page("records.example", content), page("data.example.org", content)],
        )
        self.assertIn("| Alpha Institute | 1999 | Existing |", value["candidate"])
        self.assertIn("| Beta Labs | 2001 | Canada |", value["candidate"])
        receipt = value["receipt"]
        self.assertEqual(receipt["exact_markdown_table_count"], 2)
        self.assertEqual(receipt["binding_receipt"]["changed_cell_count"], 3)
        self.assertEqual(
            receipt["binding_receipt"]["nonunknown_immutable_proposal_count"], 1
        )
        self.assertEqual(
            target.validate_result(value, baseline=BASELINE, pages=[
                page("records.example", content),
                page("data.example.org", content),
            ]),
            value,
        )

    def test_one_source_abstains_and_same_registrable_domain_is_not_two(self) -> None:
        content = """Beta Labs
Founded: 2001"""
        one = target.build_generic_structured_page_binding(
            BASELINE, [page("one.example.org", content)]
        )
        same = target.build_generic_structured_page_binding(
            BASELINE,
            [page("one.example.org", content), page("two.example.org", content)],
        )
        self.assertEqual(one["candidate"], BASELINE)
        self.assertEqual(same["candidate"], BASELINE)
        self.assertEqual(
            same["receipt"]["binding_receipt"][
                "insufficient_corroboration_cell_count"
            ],
            1,
        )

    def test_empty_page_vector_is_identity_and_zero_effect(self) -> None:
        value = target.build_generic_structured_page_binding(BASELINE, [])
        self.assertEqual(value["candidate"], BASELINE)
        receipt = value["receipt"]
        self.assertEqual(receipt["ordinary_record_count"], 0)
        self.assertEqual(receipt["binding_receipt"]["changed_cell_count"], 0)
        for name in (
            "additional_model_requests",
            "additional_logical_queries",
            "additional_search_batches",
            "additional_provider_search_calls",
            "additional_fetch_calls",
        ):
            self.assertEqual(receipt[name], 0)
        self.assertFalse(receipt["positive_entropy_or_task_credit_assigned"])

    def test_exact_entity_blocks_from_independent_hosts_bind(self) -> None:
        content = """Beta Labs
Founded: 2001
Country | Canada"""
        value = target.build_generic_structured_page_binding(
            BASELINE,
            [page("one.example", content), page("two.example.net", content)],
        )
        self.assertIn("| Beta Labs | 2001 | Canada |", value["candidate"])
        self.assertEqual(value["receipt"]["exact_entity_block_count"], 2)
        self.assertEqual(value["receipt"]["binding_receipt"]["changed_cell_count"], 2)

    def test_conflict_case_drift_and_nearby_values_abstain(self) -> None:
        first = """Beta Labs
Founded: 2001
The nearby organization was founded in 1990."""
        second = """Beta Labs
Founded: 2002"""
        value = target.build_generic_structured_page_binding(
            BASELINE,
            [page("one.example", first), page("two.example.net", second)],
        )
        self.assertEqual(value["candidate"], BASELINE)
        self.assertEqual(value["receipt"]["binding_receipt"]["conflicting_cell_count"], 1)
        drift = """beta labs
founded: 2001"""
        rejected = target.build_generic_structured_page_binding(
            BASELINE,
            [page("one.example", drift), page("two.example.net", drift)],
        )
        self.assertEqual(rejected["candidate"], BASELINE)
        self.assertEqual(rejected["receipt"]["ordinary_record_count"], 0)
        interrupted = """Beta Labs
This paragraph is not a structured field record.
Founded: 2001"""
        stopped = target.build_generic_structured_page_binding(
            BASELINE,
            [page("one.example", interrupted), page("two.example.net", interrupted)],
        )
        self.assertEqual(stopped["candidate"], BASELINE)
        self.assertEqual(stopped["receipt"]["ordinary_record_count"], 0)

    def test_same_page_ambiguity_remains_a_global_conflict(self) -> None:
        ambiguous = """Beta Labs
Founded: 2001
Founded: 2002"""
        agreeing = """Beta Labs
Founded: 2001"""
        value = target.build_generic_structured_page_binding(
            BASELINE,
            [page("one.example", ambiguous), page("two.example.net", agreeing)],
        )
        self.assertEqual(value["candidate"], BASELINE)
        self.assertEqual(value["receipt"]["ambiguous_same_page_field_count"], 1)
        self.assertEqual(value["receipt"]["binding_receipt"]["conflicting_cell_count"], 1)

    def test_page_requires_integrity_bound_final_url_and_exact_schema(self) -> None:
        valid = page("one.example", "Beta Labs\nFounded: 2001")
        for altered in (
            {**valid, "fetch_integrity": False},
            {**valid, "final_url": "http://one.example/record"},
            {**valid, "requested_url": valid["final_url"]},
        ):
            with self.assertRaises(ValueError):
                target.build_generic_structured_page_binding(BASELINE, [altered])

    def test_resealed_record_or_candidate_tamper_fails(self) -> None:
        content = "Beta Labs\nFounded: 2001"
        value = target.build_generic_structured_page_binding(
            BASELINE,
            [page("one.example", content), page("two.example.net", content)],
        )
        altered = copy.deepcopy(value)
        altered["candidate"] = BASELINE
        altered["candidate_sha256"] = target.hashlib.sha256(BASELINE.encode()).hexdigest()
        altered.pop("result_payload_sha256")
        altered["result_payload_sha256"] = target.payload_sha256(altered)
        with self.assertRaises(ValueError):
            target.validate_result(altered, baseline=BASELINE)
        nested = copy.deepcopy(value)
        nested["binding_result"]["candidate_sha256"] = "0" * 64
        nested.pop("result_payload_sha256")
        nested["result_payload_sha256"] = target.payload_sha256(nested)
        with self.assertRaises(ValueError):
            target.validate_result(nested)

    def test_runtime_has_no_external_or_privileged_capability(self) -> None:
        path = Path(target.__file__)
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = {
            alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        } | {
            (node.module or "").split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        }
        self.assertTrue(
            imports.isdisjoint(
                {"os", "pathlib", "subprocess", "requests", "socket", "httpx"}
            )
        )
        privileged = {
            "answer",
            "answer_key",
            "category",
            "evaluator",
            "gold",
            "ground_truth",
            "question_type",
            "reward",
            "score",
            "split",
            "task_category",
        }
        accesses = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
                if str(node.slice.value).casefold() in privileged:
                    accesses.append(node.lineno)
        self.assertEqual(accesses, [])


if __name__ == "__main__":
    unittest.main()
