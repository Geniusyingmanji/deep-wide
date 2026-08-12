from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import design_v25227_cran_claim_scope_no_go as target  # noqa: E402


class V25227CranClaimScopeNoGoTests(unittest.TestCase):
    def test_all_hash_and_parent_barriers_hold(self) -> None:
        self.assertTrue(target._hash_barrier())
        self.assertTrue(target._parent_barrier())

    def test_same_endpoint_and_prior_attempt_are_exact(self) -> None:
        evidence = target.build_decision(now=1)["same_endpoint_evidence"]
        self.assertEqual(
            evidence["v25219_cran_url_sha256"], target.CRAN_ENDPOINT_SHA256
        )
        self.assertEqual(
            evidence["v25226_cran_url_sha256"], target.CRAN_ENDPOINT_SHA256
        )
        self.assertTrue(evidence["same_physical_endpoint"])
        self.assertEqual(evidence["v25219_provider_attempt_count"], 1)
        self.assertTrue(evidence["v25219_public_snapshot_network_or_api_called"])

    def test_new_namespace_does_not_evade_permanent_claim(self) -> None:
        scope = target.build_decision(now=1)["claim_scope"]
        self.assertTrue(scope["v25219_claim_is_permanent"])
        self.assertFalse(
            scope[
                "v25219_retry_refetch_backfill_replacement_or_second_batch_authorized"
            ]
        )
        self.assertTrue(
            scope["new_version_or_namespace_does_not_change_same_endpoint_physical_effect"]
        )
        self.assertTrue(scope["another_GET_to_same_endpoint_would_be_refetch"])

    def test_old_control_failures_are_frozen_stage_sensitive_not_regression(self) -> None:
        stage = target.build_decision(now=1)["historical_stage_evidence"]
        self.assertTrue(stage["frozen_preactivation_audit_valid"])
        self.assertEqual(stage["frozen_preactivation_tests_observed"], 47)
        self.assertEqual(stage["current_old_control_suite_stage_sensitive_errors_observed"], 3)
        self.assertEqual(stage["v25219_runner_semantic_tests_currently_passed"], 13)
        self.assertTrue(
            stage["rebuilding_old_preactivation_after_consumed_effect_is_stage_invalid"]
        )
        self.assertFalse(stage["v25227_regression"])

    def test_same_endpoint_effect_is_no_go_and_build_remains_valid(self) -> None:
        decision = target.build_decision(now=1)["decision"]
        self.assertEqual(decision["v25226_same_endpoint_effect"], "no_go")
        self.assertFalse(decision["v25219_endpoint_refetch"])
        self.assertTrue(
            decision["v25226_build_artifact_remains_valid_synthetic_evidence"]
        )
        self.assertTrue(decision["return_to_non_endpoint_reliability_work"])

    def test_no_network_population_runtime_or_benchmark_is_authorized(self) -> None:
        authorization = target.build_decision(now=1)["authorization"]
        self.assertFalse(
            authorization["same_cran_endpoint_protocol_preactivation_or_execution_start"]
        )
        self.assertFalse(authorization["public_snapshot_network_access"])
        self.assertFalse(authorization["real_identity_selection_or_population_freeze"])
        self.assertFalse(
            authorization["evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota"]
        )

    def test_resealed_scope_decision_authority_hash_network_or_hidden_tamper_fails(self) -> None:
        value = target.build_decision(now=1)
        locations = (
            (),
            ("same_endpoint_evidence",),
            ("historical_stage_evidence",),
            ("claim_scope",),
            ("decision",),
            ("authorization",),
        )
        for location in locations:
            changed = copy.deepcopy(value)
            container = changed
            for component in location:
                container = container[component]
            container["hidden_runtime_authority"] = True
            changed.pop("decision_payload_sha256")
            changed["decision_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(location=location), self.assertRaises(ValueError):
                target.validate_decision(changed)
        for kind in ("scope", "decision", "authority", "hash", "network"):
            changed = copy.deepcopy(value)
            if kind == "scope":
                changed["claim_scope"]["another_GET_to_same_endpoint_would_be_refetch"] = False
            elif kind == "decision":
                changed["decision"]["v25226_same_endpoint_effect"] = "go"
            elif kind == "authority":
                changed["authorization"]["public_snapshot_network_access"] = True
            elif kind == "hash":
                changed["fixed_artifact_hashes"][str(target.ATTEMPT_CLAIM)] = "0" * 64
            else:
                changed["network_model_search_fetch_evaluator_benchmark_or_api_called"] = True
            changed.pop("decision_payload_sha256")
            changed["decision_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_decision(changed)

    def test_source_has_no_network_process_or_secret_capability(self) -> None:
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
