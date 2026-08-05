from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24323_shared_prefix_cell_entropy import payload_sha256  # noqa: E402
from deepwide_agent.v24502_record_bound_title_projection import (  # noqa: E402
    build_record_bound_title_projection,
    validate_record_bound_title_projection,
)


BASELINE = """```markdown
| Name | Founding year |
| --- | --- |
| Alpha | 2024 |
| Beta | 2024 |
```"""


def page(content: str, *, title: str = "Alpha official history", host: str = "one.example") -> dict:
    return {
        "host": host,
        "title": title,
        "content": content,
        "fetch_integrity": True,
    }


def values(catalog: dict, row: str = "Alpha") -> set[str]:
    return {
        str(item["value"])
        for item in catalog["observations"]
        if item["row_key"] == row
    }


class V24502RecordBoundTitleProjectionTests(unittest.TestCase):
    def test_split_exact_label_and_year_is_record_bound(self) -> None:
        catalog = build_record_bound_title_projection(
            BASELINE, [page("Established\n2025")]
        )
        self.assertEqual(values(catalog), {"2025"})
        self.assertEqual(catalog["record_bound_projection_count"], 1)
        self.assertEqual(catalog["novel_record_bound_observation_count"], 1)

    def test_date_value_and_single_blank_gap_are_supported(self) -> None:
        catalog = build_record_bound_title_projection(
            BASELINE, [page("Founding year\n\n5 April 2025 [1]")]
        )
        self.assertEqual(values(catalog), {"2025"})

    def test_bare_year_without_exact_label_remains_rejected(self) -> None:
        catalog = build_record_bound_title_projection(BASELINE, [page("2025")])
        self.assertEqual(values(catalog), set())
        self.assertFalse(catalog["bare_year_used_as_observation"])

    def test_nonvisible_foreign_named_subject_is_rejected(self) -> None:
        catalog = build_record_bound_title_projection(
            BASELINE, [page("Gamma was founded in 2025.")]
        )
        self.assertEqual(values(catalog), set())
        self.assertEqual(catalog["parent_narrative_projection_count"], 1)
        self.assertEqual(catalog["admitted_parent_narrative_projection_count"], 0)
        self.assertEqual(catalog["rejected_parent_narrative_projection_count"], 1)

    def test_explicit_target_and_generic_subject_narratives_are_preserved(self) -> None:
        catalog = build_record_bound_title_projection(
            BASELINE,
            [
                page("Alpha was founded in 2025.", host="target.example"),
                page("The institution was established in 2025.", host="generic.example"),
                page("Founded in 2025.", host="implicit.example"),
            ],
        )
        self.assertEqual(values(catalog), {"2025"})
        self.assertEqual(catalog["admitted_parent_narrative_projection_count"], 3)
        self.assertEqual(catalog["rejected_parent_narrative_projection_count"], 0)

    def test_other_visible_row_stops_record_and_narrative_scope(self) -> None:
        catalog = build_record_bound_title_projection(
            BASELINE, [page("Beta\nEstablished\n2025")]
        )
        self.assertEqual(values(catalog), set())

    def test_multiple_distinct_record_years_fail_closed(self) -> None:
        catalog = build_record_bound_title_projection(
            BASELINE, [page("Established\n2025\nFounding year\n2026")]
        )
        self.assertEqual(values(catalog), set())
        self.assertEqual(catalog["record_bound_projection_count"], 0)

    def test_existing_same_line_structured_observation_is_preserved(self) -> None:
        catalog = build_record_bound_title_projection(
            BASELINE, [page("Established | 2025")]
        )
        self.assertEqual(values(catalog), {"2025"})
        self.assertGreaterEqual(catalog["base_non_narrative_observation_count"], 1)

    def test_selected_identity_limits_projection(self) -> None:
        catalog = build_record_bound_title_projection(
            BASELINE,
            [page("Established\n2025")],
            selected_identities={("beta", "foundingyear")},
        )
        self.assertEqual(values(catalog), set())

    def test_projection_page_and_claim_tamper_fail_replay(self) -> None:
        catalog = build_record_bound_title_projection(
            BASELINE, [page("Established\n2025")]
        )
        cases = (
            lambda item: item["record_bound_projections"][0].__setitem__(
                "value", "2026"
            ),
            lambda item: item["pages"][0].__setitem__("content", "Established\n2026"),
            lambda item: item.__setitem__("bare_year_used_as_observation", True),
        )
        for alter in cases:
            changed = copy.deepcopy(catalog)
            alter(changed)
            changed.pop("catalog_payload_sha256")
            changed["catalog_payload_sha256"] = payload_sha256(changed)
            with self.assertRaises(ValueError):
                validate_record_bound_title_projection(changed)

    def test_runtime_source_is_label_blind(self) -> None:
        sys.path.insert(0, str(ROOT))
        from scripts import audit_v24398_failure_observability_build as audit

        accesses, imports = audit._ast_findings(
            Path("src/deepwide_agent/v24502_record_bound_title_projection.py")
        )
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])


if __name__ == "__main__":
    unittest.main()
