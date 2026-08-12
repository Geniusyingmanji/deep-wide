from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import design_v25221_cran_repository_format_evidence as target  # noqa: E402


class V25221CranRepositoryFormatEvidenceTests(unittest.TestCase):
    def test_parent_observer_build_audit_is_exactly_bound(self) -> None:
        self.assertTrue(target._parent_barrier())

    def test_official_document_and_section_hashes_are_frozen(self) -> None:
        value = target.build_design(now=1)
        self.assertEqual(value["official_documents"], target.OFFICIAL_DOCUMENTS)
        for document in value["official_documents"].values():
            self.assertTrue(document["url"].startswith("https://"))
            hashes = [item for key, item in document.items() if key.endswith("sha256")]
            self.assertTrue(hashes)
            self.assertTrue(all(len(digest) == 64 for digest in hashes))

    def test_body_format_supported_but_specific_alternate_mime_not_supported(self) -> None:
        value = target.build_design(now=1)
        self.assertTrue(
            value["evidence_limits"][
                "official_documentation_establishes_repository_body_format"
            ]
        )
        self.assertFalse(
            value["evidence_limits"][
                "official_documentation_establishes_specific_alternate_http_mime"
            ]
        )
        self.assertEqual(
            value["official_evidence"][
                "repository_format_section_explicit_http_content_type_or_mime_contract_count"
            ],
            0,
        )
        self.assertTrue(value["official_documentation_https_network_called"])
        self.assertFalse(value["public_snapshot_endpoint_or_api_called"])
        self.assertFalse(
            value["model_hosted_search_tavily_evaluator_or_benchmark_called"]
        )

    def test_successor_is_strict_dcf_attestation_not_mime_relaxation(self) -> None:
        value = target.build_design(now=1)
        constraints = value["successor_design_constraints"]
        self.assertTrue(constraints["known_safe_alternate_mime_allowlist_remains_empty"])
        self.assertTrue(constraints["candidate_may_require_strict_DCF_body_attestation"])
        self.assertTrue(constraints["candidate_may_not_accept_body_on_mime_or_magic_bytes_alone"])
        self.assertEqual(
            constraints["redirect_retry_refetch_backfill_replacement_and_second_batch"],
            0,
        )

    def test_only_body_attestation_build_is_authorized(self) -> None:
        value = target.build_design(now=1)
        self.assertEqual(
            value["authorization"],
            {
                "strict_cran_dcf_body_attestation_implementation_build_only": True,
                "known_safe_alternate_mime_allowlist_change": False,
                "fresh_transport_observability_protocol_design": False,
                "public_snapshot_network_access_or_execution_start": False,
                "v25219_retry_refetch_backfill_replacement_or_second_batch": False,
                "real_identity_selection_or_population_freeze": False,
                "probe_runtime_integration_external_forward_or_activation": False,
                "runtime_compatibility_validator_relaxation_or_prediction_change": False,
                "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
            },
        )

    def test_resealed_mime_claim_constraint_authority_or_hash_tamper_fails(self) -> None:
        value = target.build_design(now=1)
        for kind in (
            "mime",
            "constraint",
            "authority",
            "hash",
            "network",
            "top_hidden",
            "doc_hidden",
            "limit_hidden",
            "constraint_hidden",
            "authorization_hidden",
        ):
            changed = copy.deepcopy(value)
            if kind == "mime":
                changed["evidence_limits"][
                    "official_documentation_establishes_specific_alternate_http_mime"
                ] = True
            elif kind == "constraint":
                changed["successor_design_constraints"][
                    "known_safe_alternate_mime_allowlist_remains_empty"
                ] = False
            elif kind == "authority":
                changed["authorization"]["fresh_transport_observability_protocol_design"] = True
            elif kind == "hash":
                changed["official_documents"]["r_admin"]["whole_document_sha256"] = "0" * 64
            elif kind == "network":
                changed["public_snapshot_endpoint_or_api_called"] = True
            elif kind == "top_hidden":
                changed["hidden_runtime_authority"] = True
            elif kind == "doc_hidden":
                changed["official_documents"]["r_admin"]["hidden"] = True
            elif kind == "limit_hidden":
                changed["evidence_limits"]["hidden"] = True
            elif kind == "constraint_hidden":
                changed["successor_design_constraints"]["hidden"] = True
            else:
                changed["authorization"]["hidden"] = True
            changed.pop("design_payload_sha256")
            changed["design_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_design(changed)


if __name__ == "__main__":
    unittest.main()
