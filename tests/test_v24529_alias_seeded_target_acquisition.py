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
from deepwide_agent.v24523_conservative_alias_title_projection import (  # noqa: E402
    build_conservative_alias_title_projection,
)
from deepwide_agent.v24529_alias_seeded_target_acquisition import (  # noqa: E402
    AliasSeededTargetAcquisition,
    _select_alias_seeded_leads,
    alias_seeded_query_vector,
    primary_alias_surface,
    validate_receipt,
)


BASELINE = """```markdown
| University | Founding year |
| --- | --- |
| University of Southern Queensland | Unknown |
| Beta College | Unknown |
```"""


def empty_state() -> dict:
    return credit.apply_active_evidence(
        credit.build_uncertainty_catalog(BASELINE, []), []
    )


def plan() -> dict:
    value = neutral.build_target_plan(empty_state())
    assert value is not None
    return value


class V24529AliasSeededTargetAcquisitionTests(unittest.TestCase):
    def test_visible_row_alias_derivation_covers_initialism_and_hybrid(self) -> None:
        self.assertEqual(
            primary_alias_surface("University of Southern Queensland"), "usq"
        )
        aliases = alias_seeded_query_vector(
            "State University of New York at Geneseo", "Founding year"
        )
        self.assertEqual(len(aliases), 2)
        self.assertTrue(any("sunyg" in query.casefold() or "suny" in query.casefold() for query in aliases))

    def test_alias_queries_keep_exact_two_query_budget_and_visible_inputs(self) -> None:
        queries = alias_seeded_query_vector(
            "University of Southern Queensland", "Founding year"
        )
        self.assertEqual(len(queries), targeted.MAXIMUM_TARGETED_LOGICAL_QUERIES)
        self.assertEqual(len({item.casefold() for item in queries}), 2)
        self.assertTrue(all("usq" in item.casefold() for item in queries))
        self.assertTrue(all("founding year" in item.casefold() for item in queries))

    def test_row_without_safe_alias_preserves_discovery_and_targeted_fallbacks(self) -> None:
        row = "Beta College"
        column = "Founding year"
        alternative = "1967"
        self.assertIsNone(primary_alias_surface(row))
        self.assertEqual(
            alias_seeded_query_vector(row, column),
            neutral._discovery_query_vector(row, column),
        )
        self.assertEqual(
            alias_seeded_query_vector(row, column, alternative),
            targeted._query_vector(row, column, alternative),
        )

    def test_alias_title_leads_rank_first_while_overlap_and_cap_hold(self) -> None:
        current = plan()
        leads = [
            {
                "url": "https://generic-one.example/record",
                "query": current["query_vector"][0],
                "title": "University founding year official record",
            },
            {
                "url": "https://alias-one.example/record",
                "query": current["query_vector"][1],
                "title": "USQ institutional history",
            },
            {
                "url": "https://alias-two.example/record",
                "query": current["query_vector"][0],
                "title": "USQ facts and history",
            },
            {
                "url": "https://excluded.example/record",
                "query": current["query_vector"][0],
                "title": "USQ official history",
            },
        ]
        selected = _select_alias_seeded_leads(
            leads, current, excluded_sources={"excluded.example"}
        )
        self.assertLessEqual(len(selected), current["maximum_targeted_fetches"])
        self.assertEqual(selected[0]["title"], "USQ institutional history")
        self.assertEqual(selected[1]["title"], "USQ facts and history")
        self.assertNotIn("excluded.example", " ".join(item["url"] for item in selected))

    def test_context_patches_query_replay_and_selection_then_restores(self) -> None:
        originals = (
            targeted._query_vector,
            neutral._discovery_query_vector,
            targeted._select_targeted_leads,
        )
        state = empty_state()
        with AliasSeededTargetAcquisition() as acquisition:
            current = neutral.build_target_plan(state)
            self.assertIsNotNone(current)
            assert current is not None
            self.assertTrue(all("usq" in item.casefold() for item in current["query_vector"]))
            neutral.validate_target_plan(current, active_result=state)
            targeted._select_targeted_leads(
                [
                    {
                        "url": "https://alias.example/record",
                        "query": current["query_vector"][0],
                        "title": "USQ history",
                    }
                ],
                current,
                excluded_sources=set(),
            )
        self.assertIs(targeted._query_vector, originals[0])
        self.assertIs(neutral._discovery_query_vector, originals[1])
        self.assertIs(targeted._select_targeted_leads, originals[2])
        receipt = validate_receipt(acquisition.content_free_receipt())
        self.assertGreater(receipt["alias_seeded_query_vector_calls"], 0)
        self.assertEqual(receipt["selected_alias_title_hit_lead_count"], 1)

    def test_alias_hint_alone_never_becomes_evidence_or_credit(self) -> None:
        catalog = build_conservative_alias_title_projection(
            BASELINE,
            [
                {
                    "host": "alias.example",
                    "title": "USQ institutional history",
                    "content": "1967",
                    "fetch_integrity": True,
                }
            ],
        )
        self.assertEqual(catalog["unique_alias_anchor_page_count"], 1)
        self.assertEqual(catalog["alias_projection_count"], 0)
        self.assertEqual(catalog["novel_alias_observation_count"], 0)

    def test_receipt_tamper_and_binding_drift_fail_closed(self) -> None:
        with AliasSeededTargetAcquisition() as acquisition:
            neutral._discovery_query_vector(
                "University of Southern Queensland", "Founding year"
            )
        receipt = acquisition.content_free_receipt()
        changed = copy.deepcopy(receipt)
        changed["alias_hint_receives_vote_or_source_entropy_or_decision_credit"] = True
        with self.assertRaises(ValueError):
            validate_receipt(changed)
        with patch.object(targeted, "_query_vector", lambda *_args: []):
            with self.assertRaisesRegex(RuntimeError, "binding drifted"):
                AliasSeededTargetAcquisition().__enter__()

    def test_runtime_source_is_label_blind(self) -> None:
        from scripts import audit_v24495_targeted_conversion_projection_build as audit

        accesses, imports = audit.ast_findings(
            Path("src/deepwide_agent/v24529_alias_seeded_target_acquisition.py")
        )
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])


if __name__ == "__main__":
    unittest.main()
