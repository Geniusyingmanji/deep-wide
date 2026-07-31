from __future__ import annotations

import unittest

from deepwide_agent.v24219_search_time_contamination import (
    MIN_QCL_CHARS,
    aggregate_task_scans,
    longest_common_contiguous_span,
    scan_evidence_item,
    scan_task,
)


OPAQUE_ID = "task_0123456789abcdef01234567"


class V24219SearchTimeContaminationTests(unittest.TestCase):
    def test_long_contiguous_english_and_cjk_matches(self) -> None:
        english = "Which institutions satisfy every stated condition in the year 2025? " * 3
        value = longest_common_contiguous_span(
            english, f"preface {english} answer discussion"
        )
        self.assertEqual(value["longest_contiguous_ratio"], 1.0)
        self.assertGreater(value["longest_contiguous_chars"], MIN_QCL_CHARS)
        self.assertNotIn("institutions", str(value))

        cjk = "请列出所有满足这些公开条件的机构，并为每一个机构给出可核验的来源。" * 4
        cjk_value = longest_common_contiguous_span(cjk, f"网页转载：{cjk}随后是讨论")
        self.assertEqual(cjk_value["longest_contiguous_ratio"], 1.0)
        self.assertGreater(cjk_value["longest_contiguous_chars"], MIN_QCL_CHARS)

    def test_similar_keywords_without_long_span_are_not_qcl(self) -> None:
        question = (
            "List every institution founded before 1950, located in Europe, and still open "
            "in 2025, with its address and admission price."
        )
        content = (
            "A European institution may publish an address, price, founding year, and opening "
            "status. This is general background rather than the evaluation question."
        )
        result = scan_evidence_item(
            question=question,
            opaque_id=OPAQUE_ID,
            evidence={
                "id": "E1",
                "kind": "page",
                "url": "https://example.org/article",
                "text": content,
            },
            item_index=1,
        )
        self.assertFalse(result["qcl_primary_candidate"])
        self.assertFalse(result["eal_candidate_unconfirmed"])

    def test_query_overlap_is_not_an_accepted_input_signal(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "unapproved"):
            scan_evidence_item(
                question="visible question " * 20,
                opaque_id=OPAQUE_ID,
                evidence={"query": "visible question"},
                item_index=1,
            )

    def test_bml_and_eal_candidate_remain_unconfirmed(self) -> None:
        question = "Identify all matching public records and provide every requested field. " * 3
        result = scan_evidence_item(
            question=question,
            opaque_id=OPAQUE_ID,
            evidence={
                "id": "E2",
                "kind": "page",
                "url": "https://github.com/example/deepwidesearch/answers.json",
                "title": "Answer key",
                "text": f"{question}\nCorrect answer: a table follows.",
            },
            item_index=2,
        )
        self.assertTrue(result["bml_candidate"])
        self.assertTrue(result["qcl_primary_candidate"])
        self.assertTrue(result["eal_candidate_unconfirmed"])
        self.assertIsNone(result["confirmed_eal"])
        self.assertNotIn(question, str(result))
        self.assertNotIn("github.com/example", str(result))

    def test_snippet_is_not_treated_as_visited_page_qcl(self) -> None:
        question = "A long exact benchmark question that should not count in a snippet. " * 3
        result = scan_evidence_item(
            question=question,
            opaque_id=OPAQUE_ID,
            evidence={
                "kind": "snippet",
                "url": "https://example.org",
                "text": question,
            },
            item_index=1,
        )
        self.assertFalse(result["page_content_scanned_for_qcl"])
        self.assertFalse(result["qcl_primary_candidate"])

    def test_task_and_aggregate_emit_only_hashed_identity(self) -> None:
        question = "Which records meet all listed constraints? " * 4
        task = scan_task(
            opaque_id=OPAQUE_ID,
            question=question,
            evidence=[
                {
                    "id": "E1",
                    "kind": "page",
                    "url": "https://example.org/a",
                    "text": question,
                }
            ],
        )
        self.assertNotIn("opaque_id", task)
        self.assertEqual(len(task["opaque_id_sha256"]), 64)
        aggregate = aggregate_task_scans([task])
        self.assertEqual(aggregate["tasks_scanned"], 1)
        self.assertIsNone(aggregate["confirmed_eal"])
        self.assertNotIn(OPAQUE_ID, str(task))
        self.assertNotIn(question, str(task))


if __name__ == "__main__":
    unittest.main()
