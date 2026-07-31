from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24204_postdecision_work_order import (  # noqa: E402
    build_work_order_manifest,
)
from deepwide_agent.v24206_markdown_publisher import (  # noqa: E402
    build_markdown_publication_manifest,
    build_markdown_publication_order,
)


class V24206MarkdownPublisherTests(unittest.TestCase):
    def test_all_36_orders_have_exact_disposition_counts(self) -> None:
        summary = build_markdown_publication_manifest()["summary"]
        self.assertEqual(summary["decision_count"], 36)
        self.assertEqual(summary["markdown_selected_count"], 24)
        self.assertEqual(summary["no_markdown_noop_count"], 12)
        self.assertEqual(summary["p12_historical_binding_count"], 8)
        self.assertEqual(summary["mainline_rebase_count"], 16)
        self.assertEqual(summary["joint_package_materialized_count"], 0)
        self.assertEqual(summary["benchmark_launch_authorized_count"], 0)

    def test_scope_never_appears_without_markdown_parent(self) -> None:
        rows = build_markdown_publication_manifest()["rows"].values()
        for row in rows:
            components = row["eligible_components"]
            if "markdown_branch_scope_open_fallback" in components:
                self.assertIn("markdown_rank_slot", components)
                self.assertIn(
                    "markdown_branch_scope_open_fallback",
                    row["unowned_components_preserved_as_blockers"],
                )
                self.assertFalse(row["branch_scope_alias_or_publication_created"])

    def test_only_markdown_is_owned_by_this_publisher(self) -> None:
        for row in build_markdown_publication_manifest()["rows"].values():
            self.assertFalse(row["search_yield_published_or_implemented"])
            self.assertFalse(row["entropy_controller_published_or_implemented"])
            self.assertFalse(row["joint_package_built_or_materialized"])
            self.assertFalse(row["package_gate_evaluated_or_launched"])
            self.assertFalse(row["benchmark_forward_or_full220_launch_allowed"])

    def test_tampered_or_unknown_work_order_fails_closed(self) -> None:
        digest, row = next(iter(build_work_order_manifest()["rows"].items()))
        tampered = copy.deepcopy(row)
        tampered["eligible_components"] = []
        with self.assertRaisesRegex(RuntimeError, "bytes drifted"):
            build_markdown_publication_order(tampered)
        tampered = copy.deepcopy(row)
        tampered["decision_sha256"] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "not registered"):
            build_markdown_publication_order(tampered)
        self.assertEqual(row["decision_sha256"], digest)


if __name__ == "__main__":
    unittest.main()
