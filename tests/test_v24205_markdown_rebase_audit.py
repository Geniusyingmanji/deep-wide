from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24200_successor import build_decision_manifest  # noqa: E402
from deepwide_agent.v24205_markdown_rebase_audit import (  # noqa: E402
    build_markdown_rebase_manifest,
    classify_markdown_rebase_decision,
)


class V24205MarkdownRebaseAuditTests(unittest.TestCase):
    def test_all_36_decisions_have_expected_disposition_counts(self) -> None:
        value = build_markdown_rebase_manifest()
        summary = value["summary"]
        self.assertEqual(summary["decision_count"], 36)
        self.assertEqual(summary["identity_ready_count"], 3)
        self.assertEqual(summary["historical_p12_binding_required_count"], 2)
        self.assertEqual(summary["mainline_markdown_hook_compatible_count"], 4)
        self.assertEqual(summary["scope_namespace_alias_required_count"], 2)
        self.assertEqual(summary["search_or_entropy_authority_blocked_count"], 27)
        self.assertEqual(summary["selected_package_publication_count"], 0)
        self.assertEqual(summary["benchmark_launch_authorized_count"], 0)

    def test_search_or_entropy_always_blocks_markdown_publication_path(self) -> None:
        for row in build_markdown_rebase_manifest()["rows"].values():
            components = row["eligible_components"]
            if (
                "search_yield_shared_query" in components
                or "entropy_credit_controller" in components
            ):
                self.assertEqual(
                    row["disposition"],
                    "blocked_by_search_or_entropy_implementation_authority",
                )
                self.assertFalse(row["component_implementation_authority_granted"])

    def test_mainline_scope_decisions_require_namespace_alias_not_duplicate_patch(self) -> None:
        rows = [
            row
            for row in build_markdown_rebase_manifest()["rows"].values()
            if row["disposition"]
            == "mainline_markdown_rebase_plus_scope_namespace_alias_required"
        ]
        self.assertEqual({row["baseline_name"] for row in rows}, {"schema76", "schema77"})
        for row in rows:
            self.assertIn(
                "mainline_scope_to_markdown_branch_scope_namespace_alias_attestation",
                row["future_artifacts_required"],
            )

    def test_unregistered_or_tampered_decision_fails_closed(self) -> None:
        digest, row = next(iter(build_decision_manifest().items()))
        tampered = copy.deepcopy(row)
        tampered["eligible_components"] = []
        with self.assertRaisesRegex(RuntimeError, "frozen manifest row"):
            classify_markdown_rebase_decision(digest, tampered)
        with self.assertRaisesRegex(RuntimeError, "frozen manifest row"):
            classify_markdown_rebase_decision("0" * 64, row)


if __name__ == "__main__":
    unittest.main()
