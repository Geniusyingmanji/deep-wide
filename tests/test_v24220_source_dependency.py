from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24220_source_dependency import (
    aggregate_tasks,
    analyze_task,
    canonical_domain,
)


OPAQUE_ID = "task_0123456789abcdef01234567"


def page(url: str, text: str, *, family: str | None = None) -> dict:
    value = {"kind": "page", "url": url, "text": text}
    if family is not None:
        value["source_family"] = family
    return value


class V24220SourceDependencyTests(unittest.TestCase):
    def test_exact_cross_host_mirror_collapses(self) -> None:
        body = "Official record with a stable date, address, status, and identifier. " * 12
        value = analyze_task(
            opaque_id=OPAQUE_ID,
            evidence=[
                page("https://primary.example/record/alpha", body),
                page("https://mirror.test/copied/alpha", body),
            ],
        )
        self.assertEqual(value["nominal_evidence_width"], 2)
        self.assertEqual(value["hard_dependency_cluster_width"], 1)
        self.assertEqual(value["dependency_adjusted_effective_width"], 1.0)
        self.assertEqual(value["hard_edge_reason_counts"]["exact_content"], 1)

    def test_near_duplicate_english_and_cjk_collapse(self) -> None:
        english = (
            "The archive lists the institution, its opening date, location, public status, "
            "and the supporting catalogue identifier. " * 18
        )
        cjk = "档案列出机构名称、开放日期、所在地点、当前状态以及公开目录编号。" * 35
        for left, right in (
            (english, english + " A short syndication footer."),
            (cjk, cjk + "转载页面附加说明。"),
        ):
            with self.subTest(language=left[:4]):
                value = analyze_task(
                    opaque_id=OPAQUE_ID,
                    evidence=[
                        page("https://one.example/a", left),
                        page("https://two.test/b", right),
                    ],
                )
                self.assertEqual(value["hard_dependency_cluster_width"], 1)
                self.assertIn("near_duplicate_content", value["hard_edge_reason_counts"])

    def test_same_host_independent_pages_are_not_hard_merged(self) -> None:
        first = "Museum admission policy and opening calendar for the northern campus. " * 10
        second = "University laboratory staff directory and research programme history. " * 10
        value = analyze_task(
            opaque_id=OPAQUE_ID,
            evidence=[
                page("https://records.example/a", first),
                page("https://records.example/b", second),
            ],
        )
        self.assertEqual(value["nominal_evidence_width"], 2)
        self.assertEqual(value["hard_dependency_cluster_width"], 2)
        self.assertLess(value["dependency_adjusted_effective_width"], 2.0)
        self.assertEqual(value["soft_edge_reason_counts"]["same_source_family"], 1)
        self.assertTrue(value["same_family_alone_never_forms_a_hard_cluster"])

    def test_cross_host_path_and_content_mirror_collapses(self) -> None:
        common = "Canonical public register entry with designation, year, address, and status. " * 20
        left = common + "Publisher navigation alpha alpha alpha."
        right = common + "Mirror navigation beta beta beta."
        value = analyze_task(
            opaque_id=OPAQUE_ID,
            evidence=[
                page("https://origin.example/public-record/register-alpha", left),
                page("https://copy.test/public-record/register-alpha", right),
            ],
        )
        self.assertEqual(value["hard_dependency_cluster_width"], 1)
        self.assertIn(
            "cross_family_path_content_mirror", value["hard_edge_reason_counts"]
        )

    def test_redirect_target_equivalence_collapses(self) -> None:
        left = page(
            "https://redirect.example/out?url=https%3A%2F%2Fsource.test%2Frecords%2Falpha",
            "Redirect landing evidence A with a provenance note. " * 7,
        )
        right = page(
            "https://source.test/records/alpha",
            "Independent target rendering B with a different summary. " * 7,
        )
        value = analyze_task(opaque_id=OPAQUE_ID, evidence=[left, right])
        self.assertEqual(value["hard_dependency_cluster_width"], 1)
        self.assertEqual(value["hard_edge_reason_counts"]["redirect_equivalent"], 1)

    def test_shared_quote_and_structured_record_are_soft_dependencies(self) -> None:
        quote = "This catalogue statement is reproduced verbatim with its full provenance marker. " * 3
        first = (
            "Independent archival analysis discussing northern collections, accession policy, "
            "curatorial history, cataloguing practice, and public opening schedules. " * 8
            + quote
            + "\nname: alpha; date: 2026; status: open"
        )
        second = (
            "Separate municipal analysis discussing southern planning records, budget notices, "
            "committee minutes, transport access, and statutory reporting cycles. " * 8
            + quote
            + "\nname: alpha; date: 2026; status: open"
        )
        value = analyze_task(
            opaque_id=OPAQUE_ID,
            evidence=[
                page("https://alpha.example/source/a", first),
                page("https://beta.test/other/b", second),
            ],
        )
        self.assertEqual(value["hard_dependency_cluster_width"], 2)
        self.assertLess(value["dependency_adjusted_effective_width"], 2.0)
        self.assertIn("shared_quoted_span", value["soft_edge_reason_counts"])
        self.assertIn("shared_structured_record", value["soft_edge_reason_counts"])

    def test_tracking_url_and_repeated_ledger_row_do_not_inflate_nominal_width(self) -> None:
        body = "A sufficiently long page body that identifies one stable source record. " * 8
        value = analyze_task(
            opaque_id=OPAQUE_ID,
            evidence=[
                page("http://www.example.org/a?utm_source=x", body),
                page("https://example.org/a?utm_medium=y", body),
                {"kind": "snippet", "url": "https://search.test", "text": body},
            ],
        )
        self.assertEqual(value["raw_evidence_items"], 3)
        self.assertEqual(value["eligible_page_items"], 2)
        self.assertEqual(value["nominal_evidence_width"], 1)

    def test_unapproved_or_forbidden_identity_inputs_are_rejected(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "unapproved"):
            analyze_task(
                opaque_id=OPAQUE_ID,
                evidence=[{"kind": "page", "query": "must not enter"}],
            )
        with self.assertRaisesRegex(RuntimeError, "malformed"):
            analyze_task(opaque_id="visible-task-name", evidence=[])

    def test_domain_and_aggregate_emit_no_content_or_identifiers(self) -> None:
        self.assertEqual(canonical_domain("news.example.co.uk"), "example.co.uk")
        secret = "UNIQUE_PRIVATE_PAGE_SENTENCE"
        url = "https://private.example/hidden/raw/path"
        task = analyze_task(
            opaque_id=OPAQUE_ID,
            evidence=[page(url, secret * 20)],
        )
        aggregate = aggregate_tasks([task])
        rendered = str({"task": task, "aggregate": aggregate})
        self.assertNotIn(OPAQUE_ID, rendered)
        self.assertNotIn(secret, rendered)
        self.assertNotIn(url, rendered)
        self.assertFalse(aggregate["official_score_or_prediction_recomputed"])


if __name__ == "__main__":
    unittest.main()
