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
from deepwide_agent import v24490_entropy_targeted_support_search as targeted  # noqa: E402
from deepwide_agent import v24515_neutral_cell_discovery_planner as neutral  # noqa: E402
from deepwide_agent import v24547_alias_surface_observability as surface  # noqa: E402
from deepwide_agent.v24572_validator_aligned_alias_lead_selection import (  # noqa: E402
    ValidatorAlignedAliasLeadSelection,
    select_validator_aligned_leads,
    validate_receipt,
)


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


def same_source_leads() -> list[dict[str, str]]:
    return [
        {
            "url": "https://usq.example.edu/url-only-history",
            "query": '"USQ" founding year',
            "title": "Institutional history",
        },
        {
            "url": "https://usq.example.edu/title-history",
            "query": '"USQ" founding year',
            "title": "USQ institutional history",
        },
        {
            "url": "https://archive.example.org/usq",
            "query": '"USQ" founding year',
            "title": "University of Southern Queensland archive",
        },
    ]


class V24572ValidatorAlignedAliasLeadSelectionTests(unittest.TestCase):
    def test_same_source_title_validatable_lead_replaces_url_only_first_lead(self) -> None:
        current = plan()
        old = surface._select_surface_seeded_leads(
            same_source_leads(), current, excluded_sources=set()
        )
        new = select_validator_aligned_leads(
            same_source_leads(), current, excluded_sources=set()
        )
        old_source = next(
            item for item in old if "usq.example.edu" in item["url"]
        )
        new_source = next(
            item for item in new if "usq.example.edu" in item["url"]
        )
        self.assertEqual(
            old_source["url"], "https://usq.example.edu/url-only-history"
        )
        self.assertEqual(
            new_source["url"], "https://usq.example.edu/title-history"
        )
        self.assertTrue(
            surface.classify_alias_surface(new_source, ROW)["title_modes"]
        )

    def test_within_source_choice_is_input_order_invariant(self) -> None:
        current = plan()
        forward = select_validator_aligned_leads(
            same_source_leads(), current, excluded_sources=set()
        )
        reverse = select_validator_aligned_leads(
            list(reversed(same_source_leads())), current, excluded_sources=set()
        )
        self.assertEqual(forward, reverse)

    def test_unique_source_vector_exactly_preserves_predecessor_selection(self) -> None:
        current = plan()
        leads = [
            same_source_leads()[0],
            {
                "url": "https://archive.example.org/usq",
                "query": '"USQ" founding year',
                "title": "University of Southern Queensland archive",
            },
            {
                "url": "https://history.example.net/usq",
                "query": "generic",
                "title": "USQ institutional history",
            },
            {
                "url": "https://generic.example.com/history",
                "query": "generic",
                "title": "Institutional history",
            },
        ]
        expected = surface._select_surface_seeded_leads(
            leads, current, excluded_sources=set()
        )
        observed = select_validator_aligned_leads(
            leads, current, excluded_sources=set()
        )
        self.assertEqual(observed, expected)

    def test_source_exclusion_and_frozen_fetch_cap_are_preserved(self) -> None:
        current = plan()
        selected = select_validator_aligned_leads(
            [
                *same_source_leads(),
                {
                    "url": "https://one.example.net/history",
                    "query": "generic",
                    "title": "USQ history",
                },
                {
                    "url": "https://two.example.com/history",
                    "query": "generic",
                    "title": "USQ history",
                },
                {
                    "url": "https://three.example.io/history",
                    "query": "generic",
                    "title": "USQ history",
                },
            ],
            current,
            excluded_sources={"example.net"},
        )
        self.assertLessEqual(len(selected), current["maximum_targeted_fetches"])
        self.assertNotIn("one.example.net", {item["url"].split("/")[2] for item in selected})

    def test_context_composes_inside_surface_observability_and_restores(self) -> None:
        original_helper = surface._select_surface_seeded_leads
        original_targeted = targeted._select_targeted_leads
        current = plan()
        with ValidatorAlignedAliasLeadSelection() as aligned:
            with surface.AliasSurfaceObservability() as acquisition:
                selected = targeted._select_targeted_leads(
                    same_source_leads(), current, excluded_sources=set()
                )
            surface.validate_receipt(acquisition.content_free_receipt())
        self.assertIs(surface._select_surface_seeded_leads, original_helper)
        self.assertIs(targeted._select_targeted_leads, original_targeted)
        selected_source = next(
            item for item in selected if "usq.example.edu" in item["url"]
        )
        self.assertEqual(
            selected_source["url"], "https://usq.example.edu/title-history"
        )
        receipt = validate_receipt(aligned.content_free_receipt())
        self.assertEqual(receipt["selection_calls"], 1)
        self.assertEqual(receipt["visible_input_lead_count"], 3)
        self.assertEqual(receipt["excluded_lead_count"], 0)
        self.assertEqual(receipt["duplicate_source_lead_count"], 1)
        self.assertEqual(receipt["validator_aligned_title_replacement_count"], 1)
        self.assertEqual(receipt["url_only_first_representative_avoided_count"], 1)
        self.assertFalse(
            receipt[
                "url_alias_hint_receives_evidence_source_entropy_or_decision_credit"
            ]
        )

    def test_excluded_title_and_url_only_hits_are_diagnosed_content_free(self) -> None:
        current = plan()
        with ValidatorAlignedAliasLeadSelection() as aligned:
            surface._select_surface_seeded_leads(
                same_source_leads(),
                current,
                excluded_sources={"example.edu"},
            )
        receipt = validate_receipt(aligned.content_free_receipt())
        self.assertEqual(receipt["visible_input_lead_count"], 3)
        self.assertEqual(receipt["excluded_lead_count"], 2)
        self.assertEqual(
            receipt["excluded_title_alias_surface_hit_lead_count"], 1
        )
        self.assertEqual(
            receipt["excluded_url_only_alias_surface_hit_lead_count"], 1
        )

    def test_receipt_tamper_and_binding_drift_fail_closed(self) -> None:
        with ValidatorAlignedAliasLeadSelection() as aligned:
            surface._select_surface_seeded_leads(
                same_source_leads(), plan(), excluded_sources=set()
            )
        receipt = aligned.content_free_receipt()
        for name, value in (
            ("bindings_restored", False),
            ("validator_aligned_title_replacement_count", 3),
            (
                "url_alias_hint_receives_evidence_source_entropy_or_decision_credit",
                True,
            ),
        ):
            changed = copy.deepcopy(receipt)
            changed[name] = value
            with self.assertRaises(ValueError):
                validate_receipt(changed)
        with patch.object(surface, "_select_surface_seeded_leads", lambda *_args, **_kwargs: []):
            with self.assertRaisesRegex(RuntimeError, "binding drifted"):
                ValidatorAlignedAliasLeadSelection().__enter__()

    def test_runtime_source_is_label_blind(self) -> None:
        from scripts import audit_v24398_failure_observability_build as audit

        accesses, imports = audit._ast_findings(
            Path(
                "src/deepwide_agent/"
                "v24572_validator_aligned_alias_lead_selection.py"
            )
        )
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])


if __name__ == "__main__":
    unittest.main()
