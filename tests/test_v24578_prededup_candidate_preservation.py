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
from deepwide_agent import v24572_validator_aligned_alias_lead_selection as aligned  # noqa: E402
from deepwide_agent import v24578_prededup_candidate_preservation as target  # noqa: E402


BASELINE = """```markdown
| University | Founding year |
| --- | --- |
| University of Southern Queensland | Unknown |
| Beta College | Unknown |
```"""


def plan() -> dict:
    state = credit.apply_active_evidence(
        credit.build_uncertainty_catalog(BASELINE, []), []
    )
    value = neutral.build_target_plan(state)
    assert value is not None
    return value


def raw_batches() -> list[dict]:
    return [
        {
            "results": [
                {
                    "url": "https://usq.example.edu/url-only-history",
                    "title": "Institutional history",
                },
                {
                    "url": "https://www.usq.example.edu/title-history",
                    "title": "USQ institutional history",
                },
                {
                    "url": "https://www.usq.example.edu/title-history#duplicate",
                    "title": "USQ institutional history duplicate URL form",
                },
                {
                    "url": "https://archive.example.org/usq",
                    "title": "University of Southern Queensland archive",
                },
            ]
        }
    ]


class V24578PrededupCandidatePreservationTests(unittest.TestCase):
    def test_exact_url_distinct_same_source_candidates_survive_projection(self) -> None:
        old = target.ORIGINAL_UNIQUE_HOST_LEADS(raw_batches(), batch_ordinal=4)
        new = target.preserve_exact_url_distinct_leads(
            raw_batches(), batch_ordinal=4
        )
        self.assertEqual(len(old), 2)
        self.assertEqual(len(new), 3)
        self.assertEqual(
            sum("example.edu" in item["url"] for item in new), 2
        )

    def test_unique_source_vector_exactly_preserves_predecessor(self) -> None:
        raw = [
            {
                "results": [
                    {"url": "https://one.example/a", "title": "One"},
                    {"url": "https://two.example/b", "title": "Two"},
                ]
            }
        ]
        self.assertEqual(
            target.preserve_exact_url_distinct_leads(raw, batch_ordinal=4),
            target.ORIGINAL_UNIQUE_HOST_LEADS(raw, batch_ordinal=4),
        )

    def test_real_order_exposes_candidate_to_validator_aligned_selection(self) -> None:
        with target.PrededupCandidatePreservation() as preservation:
            with aligned.ValidatorAlignedAliasLeadSelection() as selection:
                leads = targeted._unique_host_leads(
                    raw_batches(), batch_ordinal=4
                )
                selected = surface._select_surface_seeded_leads(
                    leads, plan(), excluded_sources=set()
                )
        usq = next(item for item in selected if "example.edu" in item["url"])
        self.assertEqual(usq["url"], "https://www.usq.example.edu/title-history")
        preservation_receipt = target.validate_receipt(
            preservation.content_free_receipt()
        )
        selection_receipt = aligned.validate_receipt(
            selection.content_free_receipt()
        )
        self.assertEqual(preservation_receipt["preserved_candidate_count"], 1)
        self.assertEqual(selection_receipt["duplicate_source_lead_count"], 1)
        self.assertEqual(
            selection_receipt["validator_aligned_title_replacement_count"], 1
        )
        self.assertLessEqual(len(selected), plan()["maximum_targeted_fetches"])

    def test_context_is_targeted_only_restores_and_receipt_is_content_free(self) -> None:
        original = targeted._unique_host_leads
        with target.PrededupCandidatePreservation() as preservation:
            targeted._unique_host_leads(raw_batches(), batch_ordinal=4)
            with self.assertRaises(ValueError):
                targeted._unique_host_leads(raw_batches(), batch_ordinal=3)
        self.assertIs(targeted._unique_host_leads, original)
        receipt = target.validate_receipt(preservation.content_free_receipt())
        self.assertEqual(receipt["projection_calls"], 1)
        self.assertEqual(receipt["exact_url_distinct_lead_count"], 3)
        self.assertEqual(receipt["registrable_source_count"], 2)
        self.assertTrue(receipt["bindings_restored"])
        self.assertFalse(
            receipt[
                "preserved_url_receives_evidence_source_entropy_epistemic_or_decision_credit"
            ]
        )

    def test_receipt_tamper_and_binding_drift_fail_closed(self) -> None:
        with target.PrededupCandidatePreservation() as preservation:
            targeted._unique_host_leads(raw_batches(), batch_ordinal=4)
        receipt = preservation.content_free_receipt()
        for name, value in (
            ("bindings_restored", False),
            ("preserved_candidate_count", 2),
            (
                "preserved_url_receives_evidence_source_entropy_epistemic_or_decision_credit",
                True,
            ),
        ):
            changed = copy.deepcopy(receipt)
            changed[name] = value
            with self.assertRaises(ValueError):
                target.validate_receipt(changed)
        with patch.object(target.targeted, "_unique_host_leads", lambda *_args, **_kwargs: []):
            with self.assertRaisesRegex(RuntimeError, "binding drifted"):
                target.PrededupCandidatePreservation().__enter__()

    def test_runtime_source_is_label_blind(self) -> None:
        from scripts import audit_v24495_targeted_conversion_projection_build as audit

        accesses, imports = audit.ast_findings(
            Path(
                "src/deepwide_agent/"
                "v24578_prededup_candidate_preservation.py"
            )
        )
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])


if __name__ == "__main__":
    unittest.main()
