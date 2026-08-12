from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import design_v25225_cran_semantic_transport as target  # noqa: E402


class V25225CranSemanticTransportDesignTests(unittest.TestCase):
    def test_all_parent_hash_and_authority_barriers_hold(self) -> None:
        self.assertTrue(target._hash_barrier())
        self.assertTrue(target._parent_barrier())

    def test_endpoint_and_transport_safety_are_fixed(self) -> None:
        value = target.build_design(now=1)
        endpoint = value["fixed_endpoint"]
        transport = value["transport_safety_contract"]
        self.assertEqual(endpoint["url"], target.ENDPOINT)
        self.assertEqual(endpoint["url_sha256"], target.ENDPOINT_SHA256)
        self.assertTrue(transport["literal_endpoint_only_no_runtime_url_input"])
        self.assertEqual(transport["maximum_provider_attempts"], 1)
        self.assertEqual(transport["redirect_count"], 0)
        self.assertEqual(transport["retry_count"], 0)
        self.assertTrue(transport["tls_verification_and_hostname_verification_required"])
        self.assertTrue(transport["independent_fork_hard_deadline_controller_required"])

    def test_policy_change_is_explicit_without_alternate_mime_allowlist(self) -> None:
        policy = target.build_design(now=1)["policy_change"]
        self.assertTrue(
            policy["new_policy_acceptance_differs_from_v25217_for_missing_or_unknown_mime"]
        )
        self.assertFalse(policy["old_v25217_text_plain_only_acceptance_modified"])
        self.assertTrue(policy["known_safe_alternate_mime_allowlist_remains_empty"])
        self.assertTrue(policy["missing_or_unknown_mime_is_not_relabelled_as_text_plain"])
        self.assertTrue(policy["mime_alone_never_establishes_success"])

    def test_semantic_gate_requires_strict_same_body_binding(self) -> None:
        gate = target.build_design(now=1)["semantic_gate_contract"]
        self.assertTrue(gate["v25224_strict_extractor_required"])
        self.assertTrue(gate["candidate_count_parity_required"])
        self.assertEqual(gate["minimum_distinct_candidate_count"], 64)
        self.assertTrue(
            gate["transport_and_semantic_receipts_must_bind_same_body_length_and_sha256"]
        )
        self.assertFalse(gate["known_safe_alternate_disposition_reachable"])

    def test_residual_dns_risk_is_not_overclaimed(self) -> None:
        value = target.build_design(now=1)
        self.assertFalse(
            value["transport_safety_contract"]["dns_preflight_result_pinned_to_transport"]
        )
        self.assertTrue(value["residual_risks"]["dns_preflight_not_connection_pinned"])
        self.assertTrue(
            value["residual_risks"][
                "fixed_hostname_tls_verification_remains_security_boundary"
            ]
        )

    def test_only_implementation_build_is_authorized(self) -> None:
        authorization = target.build_design(now=1)["authorization"]
        self.assertTrue(authorization["cran_semantic_transport_implementation_build_only"])
        self.assertFalse(authorization["fresh_semantic_transport_protocol_design"])
        self.assertFalse(authorization["public_snapshot_network_access_or_execution_start"])
        self.assertFalse(authorization["real_identity_selection_or_population_freeze"])
        self.assertFalse(
            authorization["evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota"]
        )

    def test_resealed_policy_transport_gate_risk_authority_hash_or_hidden_tamper_fails(self) -> None:
        value = target.build_design(now=1)
        locations = (
            (),
            ("fixed_endpoint",),
            ("policy_change",),
            ("transport_safety_contract",),
            ("semantic_gate_contract",),
            ("failure_policy",),
            ("residual_risks",),
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
        for kind in ("policy", "transport", "gate", "risk", "authority", "hash", "network"):
            changed = copy.deepcopy(value)
            if kind == "policy":
                changed["policy_change"]["known_safe_alternate_mime_allowlist_remains_empty"] = False
            elif kind == "transport":
                changed["transport_safety_contract"]["retry_count"] = 1
            elif kind == "gate":
                changed["semantic_gate_contract"]["minimum_distinct_candidate_count"] = 1
            elif kind == "risk":
                changed["residual_risks"]["dns_preflight_not_connection_pinned"] = False
            elif kind == "authority":
                changed["authorization"]["public_snapshot_network_access_or_execution_start"] = True
            elif kind == "hash":
                changed["fixed_artifact_hashes"][str(target.EXTRACTOR_AUDIT)] = "0" * 64
            else:
                changed["network_model_search_fetch_evaluator_benchmark_or_api_called"] = True
            changed.pop("design_payload_sha256")
            changed["design_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_design(changed)

    def test_design_source_has_no_network_or_secret_capability(self) -> None:
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
