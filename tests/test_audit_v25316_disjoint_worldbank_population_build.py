from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import audit_v25316_disjoint_worldbank_population_build as target  # noqa: E402


REAL_GIT = target.base._git


class V25316DisjointWorldBankPopulationBuildTests(unittest.TestCase):
    @staticmethod
    def _fake_tests() -> dict:
        return {
            "expected": target.EXPECTED_TESTS,
            "observed": target.EXPECTED_TESTS,
            "passed": True,
            "suites": [
                {
                    "pattern": pattern,
                    "expected": expected,
                    "observed": expected,
                    "returncode": 0,
                    "passed": True,
                    "output_sha256": "a" * 64,
                }
                for pattern, expected in target.TEST_SUITES
            ],
        }

    @staticmethod
    def _clean_git(*args: str) -> str:
        if args in {("rev-parse", "HEAD"), ("rev-parse", "target/main")}:
            return target.IMPLEMENTATION_COMMIT
        if args == ("status", "--porcelain"):
            return ""
        return REAL_GIT(*args)

    def _audit(self) -> dict:
        with mock.patch.object(
            target.base, "_git", side_effect=self._clean_git
        ), mock.patch.object(target, "_tests", return_value=self._fake_tests()):
            return target.build_audit(now=1, tracked=False)

    def test_parent_sources_commit_and_closure_are_exact(self) -> None:
        self.assertTrue(target._parent_barrier())
        self.assertEqual(
            {str(path): target.base.sha256(path) for path in target.FIXED},
            {str(path): digest for path, digest in target.FIXED.items()},
        )
        self.assertEqual(
            target._changed_paths(target.IMPLEMENTATION_COMMIT),
            target.IMPLEMENTATION_PATHS,
        )
        closure, vector = target._closure()
        self.assertEqual(len(closure), target.EXPECTED_CLOSURE_COUNT)
        self.assertEqual(
            target.old_runner.payload_sha256(vector),
            target.EXPECTED_CLOSURE_VECTOR_SHA256,
        )
        self.assertEqual(
            target.old_runner.payload_sha256([row["path"] for row in vector]),
            target.EXPECTED_CLOSURE_PATH_SHA256,
        )

    def test_consumed_manifest_binds_exact_24_144_and_48(self) -> None:
        value = target._consumed_manifest()
        self.assertTrue(all(value["checks"].values()))
        self.assertEqual(len(value["target_keys"]), 24)
        self.assertEqual(len(value["entity_codes"]), 144)
        self.assertEqual(len(value["response_sha256"]), 48)
        self.assertEqual(
            value["target_keys_sha256"], target.EXPECTED_TARGET_VECTOR_SHA256
        )
        self.assertEqual(
            value["entity_codes_sha256"], target.EXPECTED_ENTITY_VECTOR_SHA256
        )
        self.assertEqual(
            value["response_vector_sha256"],
            target.EXPECTED_RESPONSE_VECTOR_SHA256,
        )
        self.assertEqual(
            value["response_receipt_vector_sha256"],
            target.EXPECTED_RESPONSE_RECEIPT_VECTOR_SHA256,
        )

    def test_closure_is_label_blind_without_evaluator_or_credentials(self) -> None:
        closure, _vector = target._closure()
        semantic = target.base._semantic_findings(closure)
        self.assertEqual(semantic["privileged_runtime_field_accesses"], [])
        self.assertEqual(semantic["evaluator_capabilities"], [])
        self.assertEqual(semantic["credential_literal_hits"], [])
        self.assertEqual(
            semantic["allowed_provider_rank_access"],
            ["src/deepwide_agent/clients.py:565:score"],
        )

    def test_selector_contract_is_twelve_task_108_then96_and_zero_overlap(self) -> None:
        value = target._selector_contract()
        self.assertEqual(value["task_count"], 12)
        self.assertEqual(value["preferred_entity_count"], 108)
        self.assertEqual(value["minimum_entity_count"], 96)
        self.assertTrue(value["old_24_targets_must_be_excluded_before_ranking"])
        self.assertTrue(value["old_144_entities_must_be_excluded_before_ranking"])
        self.assertTrue(value["old_48_response_hashes_must_have_zero_overlap"])

    def test_build_audit_authorizes_supervisor_build_only(self) -> None:
        value = self._audit()
        self.assertEqual(target.validate_audit(value), value)
        self.assertTrue(value["audit_valid"])
        authorization = value["authorization"]
        self.assertTrue(
            authorization["fresh_disjoint_worldbank_population_supervisor_build_only"]
        )
        self.assertFalse(authorization["network_population_selection_or_freeze"])
        self.assertFalse(authorization["external_activation_or_launch"])
        self.assertFalse(authorization["postfreeze_evaluator"])

    def test_resealed_consumed_contract_or_authority_tamper_fails(self) -> None:
        value = self._audit()
        for kind in (
            "target",
            "entity",
            "response",
            "contract",
            "network",
            "credit",
            "hidden",
        ):
            changed = copy.deepcopy(value)
            if kind == "target":
                changed["consumed_manifest"]["target_keys"][0] = "ZZ.FAKE@2022"
            elif kind == "entity":
                changed["consumed_manifest"]["entity_codes"][0] = "ZZZ"
            elif kind == "response":
                changed["consumed_manifest"]["response_sha256"][0] = "0" * 64
            elif kind == "contract":
                changed["selector_contract"]["minimum_entity_count"] = 95
            elif kind == "network":
                changed["authorization"]["network_population_selection_or_freeze"] = True
            elif kind == "credit":
                changed["entropy_or_information_gain_assigns_signed_credit"] = True
            else:
                changed["checks"]["hidden"] = True
            changed.pop("audit_payload_sha256")
            changed["audit_payload_sha256"] = target.old_runner.payload_sha256(
                changed
            )
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_audit(changed)

    def test_auditor_has_no_live_provider_or_evaluator_constructor(self) -> None:
        source = (ROOT / target.SOURCE).read_text(encoding="utf-8")
        for forbidden in (
            "HardTotalWallResponsesClient(",
            "AzureNativeSearchClient(",
            "requests.",
            "urlopen(",
            "run_official_eval_local",
            ".complete(system",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
