from __future__ import annotations

import ast
import hashlib
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import design_v24779_staged_fallback_population as target  # noqa: E402


def record(record_id: str, label: str, country_code: str, established: int):
    value = {
        "id": f"https://ror.org/{record_id}",
        "status": "active",
        "types": ["education"],
        "names": [{"value": label, "types": ["ror_display"]}],
        "locations": [
            {
                "geonames_details": {
                    "country_name": f"Country {country_code}",
                    "country_code": country_code,
                }
            }
        ],
        "established": established,
    }
    raw = json.dumps(value, sort_keys=True).encode()
    blob = hashlib.sha1(
        f"blob {len(raw)}\0".encode("ascii") + raw,
        usedforsecurity=False,
    ).hexdigest()
    return f"{record_id}.json", blob, raw, value


class V24779StagedFallbackPopulationTests(unittest.TestCase):
    def test_diagnosis_parent_authorizes_design_only(self) -> None:
        self.assertTrue(target._parent_valid())
        parent = target._read(ROOT / target.PARENT)
        self.assertTrue(
            parent["authorization"]["append_only_fresh_population_design"]
        )
        self.assertFalse(
            parent["authorization"]["fresh_external_activation_or_launch"]
        )
        self.assertFalse(parent["authorization"]["exact220"])

    def test_history_adds_v24774_visible_contract_without_private_truth(self) -> None:
        visible, canonical = target.historical_entities()
        self.assertEqual(len(visible), 4_752)
        self.assertEqual(len(canonical), 4_752)
        v24774 = {
            entity
            for group in target.v24774_contract.ENTITY_GROUPS
            for entity in group
        }
        self.assertEqual(len(v24774), 32)
        self.assertTrue(v24774.issubset(visible))

    def test_new_seed_changes_rank_without_changing_eligibility(self) -> None:
        row = record("01abc0001", "Fresh Staged Institute", "US", 1900)
        canonical = lambda value: value.casefold()
        old = target.base.record_candidate(
            *row, historical_canonical=set(), canonical=canonical
        )
        new = target.record_candidate(
            *row, historical_canonical=set(), canonical=canonical
        )
        self.assertIsNotNone(old)
        self.assertIsNotNone(new)
        self.assertEqual(
            {key: value for key, value in old.items() if key != "rank"},
            {key: value for key, value in new.items() if key != "rank"},
        )
        self.assertNotEqual(old["rank"], new["rank"])

    def test_country_cap16_selects_fixed_32_and_excludes_history(self) -> None:
        rows = [
            record(f"0{index:08d}", f"Institute {index}", "US", 1800 + index)
            for index in range(1, 23)
        ] + [
            record(f"1{index:08d}", f"College {index}", "CA", 1850 + index)
            for index in range(1, 23)
        ]
        selected, metrics = target.select_records(
            rows,
            historical_canonical={"institute 1"},
            canonical=lambda value: value.casefold(),
        )
        self.assertEqual(len(selected), 32)
        self.assertEqual(metrics["selected_country_count"], 2)
        self.assertEqual(metrics["selected_country_max"], 16)
        self.assertNotIn("Institute 1", {item["label"] for item in selected})
        with self.assertRaises(ValueError):
            target.select_records(
                rows,
                historical_canonical=set(),
                canonical=lambda value: value.casefold(),
                country_cap=15,
            )

    def test_visible_contract_excludes_evaluator_values(self) -> None:
        rows = [
            {
                "label": f"Visible Staged Institute {index}",
                "record_id": f"0{index:08d}",
                "founded": str(1700 + index),
                "country": f"Private Country {index}",
                "country_code": "ZZ",
            }
            for index in range(1, target.SELECTED_COUNT + 1)
        ]
        raw = target.contract_source(rows)
        text = raw.decode()
        ast.parse(text)
        self.assertIn("v24779", text)
        self.assertNotIn(rows[0]["record_id"], text)
        self.assertNotIn(rows[0]["founded"], text)
        self.assertNotIn(rows[0]["country"], text)

    def test_public_validator_rejects_activation_or_overlap_tamper(self) -> None:
        public = {
            "role": "v24779_staged_fallback_population_design",
            "freshness": {
                "historical_visible_entity_count": 4_752,
                "historical_canonical_entity_count": 4_752,
                "historical_breakdown": {"through_v24760": 4_720, "v24774": 32},
                "selected_entity_count": 32,
                "literal_overlap_with_history": 0,
                "canonical_overlap_with_history": 0,
                "selected_country_max": 16,
            },
            "task_shape": {"task_count": 8, "rows_per_task": 4},
            "population_limitations": {
                "country_cap": 16,
                "geographically_balanced_quality_population": False,
            },
            "selection_timing": {
                "rank_and_eligibility_frozen_before_search_or_model_outcome": True,
                "prior_search_query_url_page_prediction_or_quality_read": False,
                "deepwidebench_manifest_mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
                "v24774_private_population_opened_or_hashed": False,
            },
            "network": {"model_search_benchmark_forward_or_evaluator_calls": 0},
            "authorization": {
                "inert_external_protocol_publication": True,
                "preactivation_audit": False,
                "activation_or_external_launch": False,
                "quality_or_evaluator_surface_open": False,
                "same_population_retry_resume_or_selective_rerun": False,
                "paired_dev64": False,
                "exact220": False,
                "entropy_or_credit_experiment": False,
                "leaderboard_or_sota": False,
            },
        }
        public["design_payload_sha256"] = target.payload_sha256(public)
        target.validate_public(public)
        for section, name, replacement in (
            ("authorization", "activation_or_external_launch", True),
            ("freshness", "canonical_overlap_with_history", 1),
        ):
            changed = json.loads(json.dumps(public))
            changed[section][name] = replacement
            unsigned = dict(changed)
            unsigned.pop("design_payload_sha256")
            changed["design_payload_sha256"] = target.payload_sha256(unsigned)
            with self.assertRaises(ValueError):
                target.validate_public(changed)


if __name__ == "__main__":
    unittest.main()
