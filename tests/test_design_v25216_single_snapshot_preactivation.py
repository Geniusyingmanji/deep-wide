from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import design_v25216_single_snapshot_preactivation as target  # noqa: E402


class V25216SingleSnapshotPreactivationDesignTests(unittest.TestCase):
    def test_parent_offline_discovery_audit_is_exactly_bound(self) -> None:
        self.assertTrue(target._parent_barrier())

    def test_four_https_endpoints_have_unique_hosts_and_fixed_hashes(self) -> None:
        rows = target._endpoint_rows()
        self.assertEqual(set(rows), set(target.ENDPOINTS))
        hosts = []
        for row in rows.values():
            parsed = urlsplit(row["url"])
            self.assertEqual(parsed.scheme, "https")
            self.assertIsNone(parsed.username)
            self.assertIsNone(parsed.password)
            self.assertEqual(parsed.fragment, "")
            self.assertEqual(len(row["url_sha256"]), 64)
            hosts.append(parsed.hostname)
        self.assertEqual(len(set(hosts)), 4)

    def test_transport_is_exactly_one_get_zero_redirect_retry_or_refetch(self) -> None:
        contract = target.build_design(now=1)["transport_contract"]
        self.assertEqual(contract["method"], "GET")
        self.assertEqual(contract["snapshot_count"], 4)
        self.assertEqual(contract["snapshot_concurrency"], 4)
        self.assertEqual(contract["attempts_per_endpoint"], 1)
        self.assertEqual(contract["redirects_per_endpoint"], 0)
        self.assertEqual(contract["retries_per_endpoint"], 0)
        self.assertEqual(contract["conditional_refetches_per_endpoint"], 0)
        self.assertTrue(contract["requests_trust_env_disabled"])
        self.assertTrue(contract["tls_verification_required"])

    def test_byte_caps_sum_and_fit_offline_parser_limit(self) -> None:
        contract = target.build_design(now=1)["transport_contract"]
        caps = [row["maximum_response_bytes"] for row in target.ENDPOINTS.values()]
        self.assertEqual(contract["maximum_total_response_bytes"], sum(caps))
        self.assertEqual(max(caps), 128 * 1024 * 1024)

    def test_design_authorizes_transport_build_only(self) -> None:
        authorization = target.build_design(now=1)["authorization"]
        self.assertTrue(authorization["single_snapshot_transport_implementation_build_only"])
        self.assertTrue(authorization["public_snapshot_preactivation_audit_design"])
        self.assertFalse(authorization["public_snapshot_network_access_or_execution_start"])
        self.assertFalse(authorization["real_identity_selection_or_population_freeze"])
        self.assertFalse(
            authorization["probe_runtime_integration_external_forward_or_activation"]
        )

    def test_resealed_endpoint_transport_execution_or_authority_tamper_fails(self) -> None:
        value = target.build_design(now=1)
        for kind in ("endpoint", "retry", "persistence", "authority", "credit"):
            changed = copy.deepcopy(value)
            if kind == "endpoint":
                changed["endpoints"]["single_authority_exact_record"]["url"] = "https://example.org/"
            elif kind == "retry":
                changed["transport_contract"]["retries_per_endpoint"] = 1
            elif kind == "persistence":
                changed["execution_contract"]["raw_snapshot_file_persistence"] = True
            elif kind == "authority":
                changed["authorization"]["public_snapshot_network_access_or_execution_start"] = True
            else:
                changed["entropy_or_information_gain_assigns_signed_credit"] = True
            changed.pop("design_payload_sha256")
            changed["design_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_design(changed)


if __name__ == "__main__":
    unittest.main()
