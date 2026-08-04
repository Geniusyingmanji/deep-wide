from __future__ import annotations

import copy
import math
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24323_shared_prefix_cell_entropy import payload_sha256  # noqa: E402
from deepwide_agent.v24388_uncertainty_credit import (  # noqa: E402
    apply_active_evidence,
    build_uncertainty_catalog,
    validate_active_evidence_result,
    validate_uncertainty_catalog,
)


BASELINE = """```markdown
| Software | Initial release year |
| --- | --- |
| Alpha | 2020 |
```"""
UNKNOWN_BASELINE = """```markdown
| Software | Initial release year |
| --- | --- |
| Alpha | Unknown |
```"""


def observation(value: str, host: str) -> dict:
    return {
        "row_key": "Alpha",
        "column": "Initial release year",
        "value": value,
        "source_host": host,
        "fetch_integrity": True,
    }


class V24388UncertaintyCreditTests(unittest.TestCase):
    def test_no_candidate_is_required_to_select_active_target(self) -> None:
        catalog = build_uncertainty_catalog(BASELINE, [])
        validate_uncertainty_catalog(catalog)
        self.assertEqual(len(catalog["selected_target_binding_sha256s"]), 1)
        self.assertEqual(len(catalog["active_queries"]), 1)
        self.assertIn("Alpha", catalog["active_queries"][0])
        self.assertIn("Initial release year", catalog["active_queries"][0])
        self.assertNotIn("2020", catalog["active_queries"][0])
        self.assertFalse(
            catalog["target_selection_requires_preexisting_candidate_change"]
        )

    def test_runtime_can_narrow_selection_under_global_two_target_cap(self) -> None:
        baseline = """```markdown
| Software | Initial release year | Country |
| --- | --- | --- |
| Alpha | 2020 | Unknown |
```"""
        catalog = build_uncertainty_catalog(
            baseline, [], maximum_selected_targets=1
        )
        validate_uncertainty_catalog(catalog)
        self.assertEqual(catalog["maximum_selected_targets"], 1)
        self.assertEqual(len(catalog["selected_target_binding_sha256s"]), 1)
        self.assertEqual(len(catalog["active_queries"]), 1)

    def test_baseline_confirmation_gets_epistemic_not_decision_credit(self) -> None:
        catalog = build_uncertainty_catalog(BASELINE, [])
        result = apply_active_evidence(
            catalog,
            [
                observation("2020", "one.example"),
                observation("2020", "two.example"),
            ],
        )
        receipt = result["receipt"]
        self.assertEqual(result["final_prediction"], BASELINE)
        self.assertEqual(receipt["baseline_confirmed_count"], 1)
        self.assertGreater(receipt["epistemic_credit_total_nats"], 0)
        self.assertEqual(receipt["decision_credit_total_nats"], 0)
        self.assertAlmostEqual(
            sum(
                item["epistemic_credit_nats"]
                for item in result["resolutions"][0]["source_credit_records"]
            ),
            receipt["epistemic_credit_total_nats"],
            places=11,
        )

    def test_independent_supported_alternative_gets_both_credits(self) -> None:
        catalog = build_uncertainty_catalog(
            BASELINE, [observation("2021", "proposal.example")]
        )
        result = apply_active_evidence(
            catalog,
            [
                observation("2021", "active-one.example"),
                observation("2021", "active-two.example"),
            ],
        )
        receipt = result["receipt"]
        self.assertEqual(receipt["safe_change_count"], 1)
        self.assertIn("| Alpha | 2021 |", result["final_prediction"])
        self.assertGreater(receipt["epistemic_credit_total_nats"], 0)
        self.assertEqual(
            receipt["decision_credit_total_nats"],
            receipt["epistemic_credit_total_nats"],
        )

    def test_known_cell_rejects_only_two_alternative_sources(self) -> None:
        catalog = build_uncertainty_catalog(
            BASELINE, [observation("2021", "proposal.example")]
        )
        result = apply_active_evidence(
            catalog, [observation("2021", "active.example")]
        )
        self.assertEqual(result["final_prediction"], BASELINE)
        self.assertEqual(result["receipt"]["safe_change_count"], 0)
        self.assertEqual(result["receipt"]["decision_credit_total_nats"], 0)

    def test_unknown_cell_needs_two_sources_and_one_active_source(self) -> None:
        catalog = build_uncertainty_catalog(
            UNKNOWN_BASELINE, [observation("2022", "proposal.example")]
        )
        result = apply_active_evidence(
            catalog, [observation("2022", "active.example")]
        )
        self.assertEqual(result["receipt"]["safe_change_count"], 1)
        self.assertIn("| Alpha | 2022 |", result["final_prediction"])

    def test_new_active_value_refines_frozen_other_without_rebuilding_prior(self) -> None:
        catalog = build_uncertainty_catalog(BASELINE, [])
        target = catalog["targets"][0]
        self.assertEqual(target["hypotheses"], ["__current__", "__other__"])
        result = apply_active_evidence(
            catalog,
            [
                observation("2021", "one.example"),
                observation("2021", "two.example"),
                observation("2021", "three.example"),
            ],
        )
        resolution = result["resolutions"][0]
        # The known-cell current prior remains 0.65; only frozen OTHER=0.35
        # is refined into the materialized alternative and residual OTHER.
        expected_pre_entropy = -(
            0.65 * math.log(0.65) + 2 * 0.175 * math.log(0.175)
        )
        self.assertAlmostEqual(
            resolution["pre_active_entropy_nats"], expected_pre_entropy, places=11
        )
        self.assertEqual(resolution["status"], "safe_change")

    def test_conflicting_active_evidence_gets_no_positive_credit_or_change(self) -> None:
        catalog = build_uncertainty_catalog(
            BASELINE, [observation("2020", "proposal.example")]
        )
        result = apply_active_evidence(
            catalog,
            [
                observation("2021", "active-one.example"),
                observation("2022", "active-two.example"),
            ],
        )
        self.assertEqual(result["final_prediction"], BASELINE)
        self.assertEqual(result["receipt"]["safe_change_count"], 0)
        self.assertEqual(result["receipt"]["decision_credit_total_nats"], 0)

    def test_many_source_credit_allocation_conserves_rounded_total(self) -> None:
        catalog = build_uncertainty_catalog(BASELINE, [])
        result = apply_active_evidence(
            catalog,
            [observation("2020", f"source-{ordinal}.example") for ordinal in range(31)],
        )
        resolution = result["resolutions"][0]
        self.assertEqual(len(resolution["source_credit_records"]), 31)
        self.assertEqual(
            round(
                sum(
                    item["epistemic_credit_nats"]
                    for item in resolution["source_credit_records"]
                ),
                12,
            ),
            result["receipt"]["epistemic_credit_total_nats"],
        )

    def test_source_overlap_and_replay_tamper_fail_closed(self) -> None:
        catalog = build_uncertainty_catalog(
            BASELINE, [observation("2021", "same.example")]
        )
        with self.assertRaises(ValueError):
            apply_active_evidence(catalog, [observation("2021", "same.example")])

        result = apply_active_evidence(
            catalog,
            [
                observation("2021", "active-one.example"),
                observation("2021", "active-two.example"),
            ],
        )
        for field in ("catalog", "observation", "credit", "prediction"):
            with self.subTest(field=field):
                altered = copy.deepcopy(result)
                if field == "catalog":
                    target = altered["catalog"]["targets"][0]
                    target["selection_score"] += 0.1
                    altered["catalog"].pop("catalog_payload_sha256")
                    altered["catalog"]["catalog_payload_sha256"] = payload_sha256(
                        altered["catalog"]
                    )
                elif field == "observation":
                    altered["active_observations"][0]["value"] = "2023"
                elif field == "credit":
                    altered["resolutions"][0]["source_credit_records"][0][
                        "epistemic_credit_nats"
                    ] += 0.1
                else:
                    altered["final_prediction"] = altered["final_prediction"].replace(
                        "2021", "2024"
                    )
                altered.pop("result_sha256")
                altered["result_sha256"] = payload_sha256(altered)
                with self.assertRaises(ValueError):
                    validate_active_evidence_result(altered)


if __name__ == "__main__":
    unittest.main()
