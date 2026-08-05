from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24323_shared_prefix_cell_entropy import payload_sha256  # noqa: E402
from deepwide_agent.v24523_conservative_alias_title_projection import (  # noqa: E402
    REASONS,
    build_conservative_alias_title_projection,
    validate_conservative_alias_title_projection,
)


BASELINE = """```markdown
| University | Founding year |
| --- | --- |
| State University of New York at Geneseo | Unknown |
| State University of New York at New Paltz | Unknown |
| Saint Joseph's University | Unknown |
| University of Southern Queensland | Unknown |
```"""


def page(title: str, content: str, host: str = "one.example") -> dict:
    return {
        "host": host,
        "title": title,
        "content": content,
        "fetch_integrity": True,
    }


def values(catalog: dict, row: str) -> set[str]:
    return {
        str(item["value"])
        for item in catalog["observations"]
        if item["row_key"] == row
    }


class V24523ConservativeAliasTitleProjectionTests(unittest.TestCase):
    def test_distinctive_core_alias_with_exact_label_projects(self) -> None:
        catalog = build_conservative_alias_title_projection(
            BASELINE,
            [page("SUNY Geneseo - facts", "Established | 1871")],
        )
        self.assertEqual(
            values(catalog, "State University of New York at Geneseo"),
            {"1871"},
        )
        self.assertEqual(catalog["alias_projection_count"], 1)
        self.assertEqual(catalog["novel_alias_observation_count"], 1)
        self.assertEqual(catalog["reason_counts"]["alias_projection_emitted"], 1)

    def test_initialism_alias_with_subject_safe_narrative_projects(self) -> None:
        catalog = build_conservative_alias_title_projection(
            BASELINE,
            [
                page(
                    "USQ institutional history",
                    "The university was founded in 1967.",
                )
            ],
        )
        self.assertEqual(
            values(catalog, "University of Southern Queensland"), {"1967"}
        )
        projection = catalog["alias_title_projections"][0]
        self.assertEqual(projection["alias_mode"], "visible_row_initialism")
        self.assertEqual(
            projection["evidence_kind"], "subject_safe_narrative_relation"
        )

    def test_normalized_saint_alias_and_split_record_project(self) -> None:
        catalog = build_conservative_alias_title_projection(
            BASELINE,
            [page("St Joseph's University history", "Founding year\n1851")],
        )
        self.assertEqual(values(catalog, "Saint Joseph's University"), {"1851"})
        self.assertIn(
            catalog["alias_title_projections"][0]["evidence_kind"],
            {"split_exact_label_year_record", "exact_label_value"},
        )

    def test_cross_row_core_collision_fails_closed(self) -> None:
        catalog = build_conservative_alias_title_projection(
            BASELINE,
            [page("State University of New York history", "Founded | 1900")],
        )
        self.assertEqual(catalog["alias_projection_count"], 0)
        self.assertEqual(
            catalog["reason_counts"]["alias_anchor_absent_or_ambiguous"], 4
        )

    def test_short_generic_or_organization_type_conflict_fails_closed(self) -> None:
        for title_text in (
            "New York history",
            "Geneseo College history",
            "Southern school history",
        ):
            with self.subTest(title=title_text):
                catalog = build_conservative_alias_title_projection(
                    BASELINE, [page(title_text, "Founded | 1900")]
                )
                self.assertEqual(catalog["alias_projection_count"], 0)

    def test_bare_year_and_unsafe_named_subject_remain_rejected(self) -> None:
        bare = build_conservative_alias_title_projection(
            BASELINE,
            [page("USQ institutional history", "1967")],
        )
        self.assertEqual(bare["alias_projection_count"], 0)
        unsafe = build_conservative_alias_title_projection(
            BASELINE,
            [page("USQ institutional history", "Gamma College was founded in 1967.")],
        )
        self.assertEqual(unsafe["alias_projection_count"], 0)
        self.assertGreater(
            unsafe["reason_counts"]["alias_anchor_subject_safety_rejected"], 0
        )

    def test_multiple_distinct_candidate_years_reject_pair(self) -> None:
        catalog = build_conservative_alias_title_projection(
            BASELINE,
            [
                page(
                    "USQ institutional history",
                    "The university was founded in 1967.\nEstablished | 1990",
                )
            ],
        )
        self.assertEqual(catalog["alias_projection_count"], 0)
        self.assertGreater(
            catalog["reason_counts"][
                "alias_anchor_multiple_distinct_candidate_years"
            ],
            0,
        )

    def test_exact_parent_title_anchor_is_never_overridden(self) -> None:
        catalog = build_conservative_alias_title_projection(
            BASELINE,
            [
                page(
                    "University of Southern Queensland official history",
                    "The university was founded in 1967.",
                )
            ],
        )
        self.assertEqual(catalog["alias_projection_count"], 0)
        self.assertEqual(
            catalog["reason_counts"]["exact_title_anchor_owned_by_parent"], 4
        )
        self.assertEqual(
            values(catalog, "University of Southern Queensland"), {"1967"}
        )

    def test_other_visible_row_stops_alias_title_scope(self) -> None:
        catalog = build_conservative_alias_title_projection(
            BASELINE,
            [
                page(
                    "USQ institutional history",
                    "Saint Joseph's University was founded in 1851.\n"
                    "The university was founded in 1967.",
                )
            ],
        )
        self.assertEqual(catalog["alias_projection_count"], 0)

    def test_selected_identity_limits_alias_projection(self) -> None:
        catalog = build_conservative_alias_title_projection(
            BASELINE,
            [page("USQ institutional history", "Founded | 1967")],
            selected_identities={
                ("stateuniversityofnewyorkatgeneseo", "foundingyear")
            },
        )
        self.assertEqual(catalog["alias_projection_count"], 0)

    def test_reason_partition_is_exact_and_parent_is_preserved(self) -> None:
        catalog = build_conservative_alias_title_projection(
            BASELINE,
            [
                page("USQ institutional history", "Founded | 1967"),
                page("Unrelated page", "Founded | 1900", "two.example"),
            ],
        )
        self.assertEqual(catalog["page_target_pair_count"], 8)
        self.assertEqual(
            sum(catalog["reason_counts"][name] for name in REASONS), 8
        )
        self.assertTrue(catalog["parent_artifact_preserved"])
        self.assertTrue(catalog["reason_partition_exact"])

    def test_projection_page_and_claim_tamper_fail_replay(self) -> None:
        catalog = build_conservative_alias_title_projection(
            BASELINE,
            [page("USQ institutional history", "Founded | 1967")],
        )
        cases = (
            lambda item: item["alias_title_projections"][0].__setitem__(
                "value", "1990"
            ),
            lambda item: item["pages"][0].__setitem__(
                "content", "Founded | 1990"
            ),
            lambda item: item.__setitem__(
                "organization_type_conflict_rejected", False
            ),
        )
        for alter in cases:
            changed = copy.deepcopy(catalog)
            alter(changed)
            changed.pop("catalog_payload_sha256")
            changed["catalog_payload_sha256"] = payload_sha256(changed)
            with self.assertRaises(ValueError):
                validate_conservative_alias_title_projection(changed)

    def test_runtime_source_is_label_blind(self) -> None:
        from scripts import audit_v24495_targeted_conversion_projection_build as audit

        accesses, imports = audit.ast_findings(
            Path("src/deepwide_agent/v24523_conservative_alias_title_projection.py")
        )
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])


if __name__ == "__main__":
    unittest.main()
