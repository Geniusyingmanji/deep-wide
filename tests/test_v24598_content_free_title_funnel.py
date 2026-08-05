from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24388_uncertainty_credit as credit  # noqa: E402
from deepwide_agent import v24515_neutral_cell_discovery_planner as neutral  # noqa: E402
from deepwide_agent import v24572_validator_aligned_alias_lead_selection as selection  # noqa: E402
from deepwide_agent import v24598_content_free_title_funnel as target  # noqa: E402


BASELINE = """```markdown
| University | Founding year |
| --- | --- |
| University of Southern Queensland | Unknown |
| Beta College | Unknown |
```"""
ROW = "University of Southern Queensland"


def plan() -> dict:
    state = credit.apply_active_evidence(
        credit.build_uncertainty_catalog(BASELINE, []), []
    )
    value = neutral.build_target_plan(state)
    assert value is not None
    return value


class V24598ContentFreeTitleFunnelTests(unittest.TestCase):
    def test_classifier_separates_empty_absent_late_type_and_strict(self) -> None:
        empty = target.classify_title_funnel({"title": ""}, ROW)
        absent = target.classify_title_funnel(
            {"title": "Generic institutional history"}, ROW
        )
        late = target.classify_title_funnel(
            {
                "title": " ".join(
                    ["archive"] * 20
                    + ["University", "of", "Southern", "Queensland", "history"]
                )
            },
            ROW,
        )
        incompatible = target.classify_title_funnel(
            {"title": "College Southern Queensland history"}, ROW
        )
        strict = target.classify_title_funnel(
            {"title": "Official University of Southern Queensland history"}, ROW
        )
        self.assertTrue(empty["empty_title"])
        self.assertTrue(absent["nonempty_title_without_canonical_row_token"])
        self.assertTrue(late["surface_rejected_only_by_maximum_start"])
        self.assertTrue(incompatible["surface_rejected_only_by_type_compatibility"])
        self.assertTrue(strict["strict_validator_aligned_title"])

    def test_wrapper_preserves_exact_selection_and_records_each_input_once(self) -> None:
        current = plan()
        leads = [
            {
                "url": "https://empty.example/history",
                "query": "history",
                "title": "",
            },
            {
                "url": "https://late.example/history",
                "query": "history",
                "title": " ".join(
                    ["archive"] * 20
                    + ["University", "of", "Southern", "Queensland"]
                ),
            },
            {
                "url": "https://strict.example/history",
                "query": "history",
                "title": "University of Southern Queensland history",
            },
        ]
        expected = selection._selection(leads, current, excluded_sources=set())
        with target.ContentFreeTitleFunnel() as funnel:
            observed = selection._selection(
                leads, current, excluded_sources=set()
            )
        self.assertEqual(observed, expected)
        receipt = target.validate_receipt(funnel.content_free_receipt())
        self.assertEqual(receipt["selection_calls"], 1)
        self.assertEqual(receipt["visible_input_lead_count"], 3)
        self.assertEqual(receipt["distinct_visible_lead_count"], 3)
        self.assertEqual(receipt["empty_title_lead_count"], 1)
        self.assertEqual(receipt["nonempty_title_lead_count"], 2)
        self.assertEqual(receipt["strict_validator_aligned_title_lead_count"], 1)
        self.assertEqual(
            receipt["surface_rejected_only_by_maximum_start_lead_count"], 1
        )

    def test_duplicate_input_is_visible_but_not_distinct(self) -> None:
        current = plan()
        lead = {
            "url": "https://same.example/history",
            "query": "history",
            "title": "Institutional history",
        }
        with target.ContentFreeTitleFunnel() as funnel:
            selection._selection([lead, lead], current, excluded_sources=set())
        receipt = target.validate_receipt(funnel.content_free_receipt())
        self.assertEqual(receipt["visible_input_lead_count"], 2)
        self.assertEqual(receipt["distinct_visible_lead_count"], 1)

    def test_receipt_tamper_and_binding_drift_fail_closed(self) -> None:
        with target.ContentFreeTitleFunnel() as funnel:
            pass
        receipt = funnel.content_free_receipt()
        cases = (
            ("raw_row_title_query_url_source_page_value_prediction_or_credential_emitted", True),
            ("strict_validator_aligned_title_lead_count", 1),
            ("empty_title_lead_count", 1),
        )
        for name, value in cases:
            changed = copy.deepcopy(receipt)
            changed[name] = value
            with self.assertRaises(ValueError):
                target.validate_receipt(changed)
        with patch.object(selection, "_selection", lambda *_args, **_kwargs: ([], {})):
            with self.assertRaisesRegex(RuntimeError, "binding drifted"):
                target.ContentFreeTitleFunnel().__enter__()

    def test_nested_context_fails_closed_and_binding_restores(self) -> None:
        before = selection._selection
        with target.ContentFreeTitleFunnel():
            with self.assertRaisesRegex(RuntimeError, "already active"):
                target.ContentFreeTitleFunnel().__enter__()
        self.assertIs(selection._selection, before)

    def test_receipt_is_content_free_and_changes_no_effect_surface(self) -> None:
        with target.ContentFreeTitleFunnel() as funnel:
            pass
        receipt = target.validate_receipt(funnel.content_free_receipt())
        self.assertTrue(receipt["selection_output_preserved_exactly"])
        self.assertFalse(
            receipt[
                "query_search_fetch_ranking_validator_evidence_posterior_entropy_and_credit_changed"
            ]
        )
        self.assertFalse(
            receipt[
                "raw_row_title_query_url_source_page_value_prediction_or_credential_emitted"
            ]
        )

    def test_runtime_source_is_label_blind(self) -> None:
        from scripts import audit_v24495_targeted_conversion_projection_build as audit

        accesses, imports = audit.ast_findings(
            Path("src/deepwide_agent/v24598_content_free_title_funnel.py")
        )
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])


if __name__ == "__main__":
    unittest.main()
