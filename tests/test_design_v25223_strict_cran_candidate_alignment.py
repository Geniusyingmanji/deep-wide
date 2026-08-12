from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import design_v25223_strict_cran_candidate_alignment as target  # noqa: E402


class V25223StrictCranCandidateAlignmentDesignTests(unittest.TestCase):
    def test_all_parent_hash_and_authority_barriers_hold(self) -> None:
        self.assertTrue(target._hash_barrier())
        self.assertTrue(target._parent_barrier())

    def test_three_synthetic_mismatches_are_exact(self) -> None:
        value = target.build_design(now=1)
        observation = value["synthetic_alignment_observation"]
        self.assertEqual(observation["synthetic_case_count"], 3)
        self.assertEqual(observation["legacy_accept_count"], 3)
        self.assertEqual(observation["strict_reject_count"], 3)
        self.assertEqual(
            [row["strict_failure_stage"] for row in observation["cases"]],
            ["minimum_candidate_coverage", "dcf_syntax", "newline"],
        )
        self.assertFalse(
            observation["synthetic_body_identity_record_field_or_value_persisted"]
        )

    def test_existing_parser_composition_is_no_go(self) -> None:
        decision = target.build_design(now=1)["alignment_decision"]
        self.assertFalse(
            decision["v25215_candidate_parser_and_v25222_attestor_semantics_aligned"]
        )
        self.assertEqual(
            decision["compose_existing_parser_after_strict_attestation"], "no_go"
        )
        self.assertTrue(decision["strict_candidate_extractor_build_required"])

    def test_successor_requires_one_strict_semantic_path(self) -> None:
        constraints = target.build_design(now=1)["successor_constraints"]
        self.assertTrue(
            constraints[
                "candidate_extraction_uses_same_frozen_record_parser_and_predicate_as_attestation"
            ]
        )
        self.assertTrue(
            constraints["predicate_valid_and_distinct_candidate_counts_must_match_parent"]
        )
        self.assertTrue(constraints["known_safe_alternate_mime_allowlist_remains_empty"])
        self.assertTrue(constraints["v25219_population_claim_or_result_not_reused"])

    def test_only_strict_extractor_build_is_authorized(self) -> None:
        authorization = target.build_design(now=1)["authorization"]
        self.assertTrue(
            authorization["strict_cran_candidate_extractor_implementation_build_only"]
        )
        self.assertFalse(authorization["transport_or_content_type_acceptance_change"])
        self.assertFalse(authorization["public_snapshot_network_access_or_execution_start"])
        self.assertFalse(authorization["real_identity_selection_or_population_freeze"])
        self.assertFalse(
            authorization["evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota"]
        )

    def test_resealed_decision_constraint_authority_hash_or_hidden_tamper_fails(self) -> None:
        value = target.build_design(now=1)
        locations = (
            (),
            ("synthetic_alignment_observation",),
            ("synthetic_alignment_observation", "cases", 0),
            ("alignment_decision",),
            ("successor_constraints",),
            ("authorization",),
        )
        for location in locations:
            changed = copy.deepcopy(value)
            container = changed
            for component in location:
                container = container[component]
            container["hidden_runtime_authority"] = True
            changed.pop("design_payload_sha256")
            changed["design_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(location=location), self.assertRaises(ValueError):
                target.validate_design(changed)
        for kind in ("decision", "constraint", "authority", "hash", "network"):
            changed = copy.deepcopy(value)
            if kind == "decision":
                changed["alignment_decision"][
                    "v25215_candidate_parser_and_v25222_attestor_semantics_aligned"
                ] = True
            elif kind == "constraint":
                changed["successor_constraints"][
                    "known_safe_alternate_mime_allowlist_remains_empty"
                ] = False
            elif kind == "authority":
                changed["authorization"][
                    "public_snapshot_network_access_or_execution_start"
                ] = True
            elif kind == "hash":
                changed["fixed_artifact_hashes"][str(target.STRICT_SOURCE)] = "0" * 64
            else:
                changed["network_model_search_fetch_evaluator_benchmark_or_api_called"] = True
            changed.pop("design_payload_sha256")
            changed["design_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_design(changed)

    def test_design_source_is_secret_free_and_has_no_effect_entrypoint(self) -> None:
        source = (ROOT / target.SOURCE).read_text(encoding="utf-8")
        for forbidden in (
            "requests",
            "httpx",
            "openai",
            "subprocess",
            "socket",
            "gh" + "p_",
            "tvly-" + "dev-",
            "/mnt",
            "/data",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
