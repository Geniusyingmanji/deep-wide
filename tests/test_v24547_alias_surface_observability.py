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
from deepwide_agent.v24547_alias_surface_observability import (  # noqa: E402
    AliasSurfaceObservability,
    _select_surface_seeded_leads,
    classify_alias_surface,
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


class V24547AliasSurfaceObservabilityTests(unittest.TestCase):
    def test_title_modes_distinguish_full_core_and_initialism(self) -> None:
        full = classify_alias_surface(
            {
                "url": "https://example.org/history",
                "title": "University of Southern Queensland history",
                "query": "generic",
            },
            ROW,
        )
        initialism = classify_alias_surface(
            {
                "url": "https://example.org/history",
                "title": "USQ institutional history",
                "query": "generic",
            },
            ROW,
        )
        self.assertIn("normalized_full_surface", full["title_modes"])
        self.assertIn("distinctive_core_surface", full["title_modes"])
        self.assertNotIn("visible_row_initialism", full["title_modes"])
        self.assertEqual(
            initialism["title_modes"], frozenset({"visible_row_initialism"})
        )

    def test_url_hostname_and_path_match_but_query_fragment_and_userinfo_do_not(self) -> None:
        hostname = classify_alias_surface(
            {"url": "https://usq.edu.au/history", "title": "History", "query": ""},
            ROW,
        )
        path = classify_alias_surface(
            {
                "url": "https://example.org/university-of-southern-queensland/history",
                "title": "History",
                "query": "",
            },
            ROW,
        )
        excluded = classify_alias_surface(
            {
                "url": "https://usq@example.org/history?next=usq#usq",
                "title": "History",
                "query": "generic",
            },
            ROW,
        )
        self.assertIn("visible_row_initialism", hostname["url_modes"])
        self.assertIn("normalized_full_surface", path["url_modes"])
        self.assertFalse(excluded["surface_hit"])

    def test_query_only_alias_is_counted_but_never_establishes_surface_hit(self) -> None:
        value = classify_alias_surface(
            {
                "url": "https://generic.example/history",
                "title": "Institutional history",
                "query": '"USQ" founding year',
            },
            ROW,
        )
        self.assertFalse(value["surface_hit"])
        self.assertTrue(value["query_only"])

    def test_surface_hit_ranks_before_query_only_hit_under_same_budget(self) -> None:
        current = plan()
        leads = [
            {
                "url": "https://generic.example/history?alias=usq",
                "query": '"USQ" founding year',
                "title": "Official institutional history",
            },
            {
                "url": "https://usq.edu.au/history",
                "query": "generic",
                "title": "Official institutional history",
            },
            {
                "url": "https://full.example/university-of-southern-queensland/history",
                "query": "generic",
                "title": "History",
            },
        ]
        selected = _select_surface_seeded_leads(
            leads, current, excluded_sources=set()
        )
        self.assertLessEqual(len(selected), current["maximum_targeted_fetches"])
        self.assertEqual(selected[0]["url"], "https://full.example/university-of-southern-queensland/history")
        self.assertEqual(selected[1]["url"], "https://usq.edu.au/history")

    def test_context_records_mode_and_union_counts_then_restores(self) -> None:
        originals = (
            targeted._query_vector,
            neutral._discovery_query_vector,
            targeted._select_targeted_leads,
        )
        current = plan()
        with AliasSurfaceObservability() as acquisition:
            neutral._discovery_query_vector(ROW, "Founding year")
            targeted._select_targeted_leads(
                [
                    {
                        "url": "https://usq.edu.au/history",
                        "query": current["query_vector"][0],
                        "title": "USQ history",
                    },
                    {
                        "url": "https://generic.example/history?alias=usq",
                        "query": '"USQ" founding year',
                        "title": "History",
                    },
                ],
                current,
                excluded_sources=set(),
            )
        self.assertIs(targeted._query_vector, originals[0])
        self.assertIs(neutral._discovery_query_vector, originals[1])
        self.assertIs(targeted._select_targeted_leads, originals[2])
        receipt = validate_receipt(acquisition.content_free_receipt())
        self.assertEqual(receipt["alias_surface_hit_lead_count"], 1)
        self.assertEqual(receipt["title_initialism_hit_lead_count"], 1)
        self.assertEqual(receipt["url_initialism_hit_lead_count"], 1)
        self.assertEqual(receipt["query_only_alias_surface_lead_count"], 1)
        self.assertFalse(receipt["query_text_used_to_establish_alias_hit"])

    def test_receipt_coordinated_tamper_and_binding_drift_fail_closed(self) -> None:
        with AliasSurfaceObservability() as acquisition:
            neutral._discovery_query_vector(ROW, "Founding year")
        receipt = acquisition.content_free_receipt()
        for name, value in (
            ("query_text_used_to_establish_alias_hit", True),
            ("selected_alias_surface_hit_lead_count", 1),
            ("url_full_surface_hit_lead_count", 1),
        ):
            changed = copy.deepcopy(receipt)
            changed[name] = value
            with self.assertRaises(ValueError):
                validate_receipt(changed)
        with patch.object(targeted, "_query_vector", lambda *_args: []):
            with self.assertRaisesRegex(RuntimeError, "binding drifted"):
                AliasSurfaceObservability().__enter__()

    def test_runtime_source_is_label_blind(self) -> None:
        from scripts import audit_v24495_targeted_conversion_projection_build as audit

        accesses, imports = audit.ast_findings(
            Path("src/deepwide_agent/v24547_alias_surface_observability.py")
        )
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])


if __name__ == "__main__":
    unittest.main()
