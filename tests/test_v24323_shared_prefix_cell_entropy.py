from __future__ import annotations

import copy
import json
import re
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24323_shared_prefix_cell_entropy import (  # noqa: E402
    AnonymousCellBelief,
    ReserveEvidenceSignal,
    admit_reserve_evidence,
    build_pair_contract,
    build_shared_prefix_receipt,
    payload_sha256,
    validate_admission_receipt,
    validate_pair_contract,
)


def belief() -> AnonymousCellBelief:
    return AnonymousCellBelief((0.55, 0.30, 0.15), 0)


def signal(**overrides) -> ReserveEvidenceSignal:
    values = {
        "likelihood_ratios": (8.0, 1.0, 0.5),
        "source_reliability": 0.95,
        "source_independence": 0.95,
        "fetch_integrity": True,
        "independent_sources": 3,
        "corroborating_sources": 3,
        "conflicting_sources": 0,
        "evidence_chars": 1200,
    }
    values.update(overrides)
    return ReserveEvidenceSignal(**values)


def prefix():
    return build_shared_prefix_receipt(
        visible_plan_sha256="1" * 64,
        planned_query_vector_sha256="2" * 64,
        first_wave_search_receipt_sha256="3" * 64,
        core_evidence_vector_sha256="4" * 64,
        plan_model_effects=1,
        first_wave_search_effects=1,
        first_wave_fetch_effects=6,
        core_usable_pages=5,
    )


class V24323SharedPrefixCellEntropyTests(unittest.TestCase):
    def test_reliable_corroborated_support_is_admitted(self) -> None:
        value = admit_reserve_evidence(belief(), signal())
        self.assertEqual(value["disposition"], "admit_support")
        self.assertEqual(value["context_action"], "append_reserve_support")
        self.assertGreater(value["conditional_entropy_reduction_nats"], 0)

    def test_novel_but_unreliable_or_single_source_evidence_is_quarantined(self) -> None:
        unreliable = admit_reserve_evidence(
            belief(),
            signal(
                source_reliability=0.20,
                source_independence=0.20,
                evidence_chars=1_000_000,
            ),
        )
        single = admit_reserve_evidence(
            belief(), signal(independent_sources=1, corroborating_sources=1)
        )
        self.assertEqual(unreliable["context_action"], "core_only")
        self.assertEqual(single["disposition"], "quarantine_insufficient_independence")
        self.assertFalse(
            unreliable["raw_page_novelty_or_character_count_used_as_task_value"]
        )
        self.assertEqual(unreliable["context_action"], "core_only")

    def test_weak_conflict_cannot_override_core(self) -> None:
        value = admit_reserve_evidence(
            belief(),
            signal(
                likelihood_ratios=(0.2, 8.0, 0.5),
                source_reliability=0.80,
                source_independence=0.80,
                corroborating_sources=2,
            ),
        )
        self.assertTrue(value["reserve_conflicts_with_core_map"])
        self.assertEqual(value["disposition"], "quarantine_conflict")

    def test_strong_independent_conflict_can_corroborated_override(self) -> None:
        value = admit_reserve_evidence(
            belief(), signal(likelihood_ratios=(0.05, 20.0, 0.1))
        )
        self.assertEqual(value["disposition"], "admit_corroborated_override")
        self.assertEqual(
            value["context_action"], "replace_core_after_corroborated_override"
        )

    def test_entropy_increasing_evidence_is_quarantined(self) -> None:
        prior = AnonymousCellBelief((0.90, 0.10), 0)
        value = admit_reserve_evidence(
            prior,
            signal(
                likelihood_ratios=(1.0, 9.0),
                independent_sources=3,
                corroborating_sources=3,
            ),
        )
        self.assertLess(value["conditional_entropy_reduction_nats"], 0)
        self.assertEqual(
            value["disposition"], "quarantine_nonpositive_conditional_gain"
        )

    def test_admission_receipt_is_replay_sealed_and_content_free(self) -> None:
        value = admit_reserve_evidence(belief(), signal())
        validate_admission_receipt(value)
        serialized = json.dumps(value, ensure_ascii=False)
        self.assertIsNone(re.search(r"task_[0-9a-f]{24}", serialized))
        for forbidden in ("deep2wide_result_", '"question":', '"prediction":'):
            self.assertNotIn(forbidden, serialized)
        altered = copy.deepcopy(value)
        altered["reliability"] = 0.1
        altered["receipt_sha256"] = payload_sha256(
            {name: item for name, item in altered.items() if name != "receipt_sha256"}
        )
        with self.assertRaises(ValueError):
            validate_admission_receipt(altered)

    def test_pair_requires_exact_shared_prefix_and_discloses_rng_limit(self) -> None:
        shared = prefix()
        admission = admit_reserve_evidence(belief(), signal())
        pair = build_pair_contract(
            shared_prefix=shared,
            baseline_prefix_sha256=shared["receipt_sha256"],
            candidate_prefix_sha256=shared["receipt_sha256"],
            synthesis_prompt_template_sha256="5" * 64,
            model_configuration_sha256="6" * 64,
            candidate_admission=admission,
        )
        validate_pair_contract(pair)
        self.assertTrue(pair["strict_shared_upstream_prefix_ablation"])
        self.assertFalse(pair["synthesis_randomness_shared"])
        self.assertFalse(pair["reserve_effect_fully_causally_identified"])

    def test_prefix_mismatch_fails_before_pair_contract(self) -> None:
        shared = prefix()
        admission = admit_reserve_evidence(belief(), signal())
        with self.assertRaisesRegex(ValueError, "prefix identity"):
            build_pair_contract(
                shared_prefix=shared,
                baseline_prefix_sha256=shared["receipt_sha256"],
                candidate_prefix_sha256="7" * 64,
                synthesis_prompt_template_sha256="5" * 64,
                model_configuration_sha256="6" * 64,
                candidate_admission=admission,
            )


if __name__ == "__main__":
    unittest.main()
