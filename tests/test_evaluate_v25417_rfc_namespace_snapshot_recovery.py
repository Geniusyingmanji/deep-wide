from __future__ import annotations

import copy
import gzip
import inspect
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25415_paired_rfc_route_external_contract as contract  # noqa: E402
from scripts import evaluate_v25416_paired_rfc_route_quality as parent  # noqa: E402
from scripts import evaluate_v25417_rfc_namespace_snapshot_recovery as target  # noqa: E402


def fixture_xml(numbers=tuple(range(9320, 9400)), *, namespace=target.RFC_INDEX_NAMESPACE) -> bytes:
    entries = []
    for offset, number in enumerate(numbers):
        entries.append(
            f"""
            <rfc-entry>
              <doc-id>RFC{number:04d}</doc-id>
              <title>Title {offset}</title>
              <author><name>A. Author{offset}</name></author>
              <author><name>B. Editor{offset}, Ed.</name></author>
              <date><month>March</month><year>2022</year></date>
              <current-status>PROPOSED STANDARD</current-status>
              <publication-status>PROPOSED STANDARD</publication-status>
              <stream>IETF</stream>
            </rfc-entry>
            """
        )
    return (
        f'<rfc-index xmlns="{namespace}">' + "".join(entries) + "</rfc-index>"
    ).encode()


class V25417RfcNamespaceSnapshotRecoveryTests(unittest.TestCase):
    def test_namespaced_parser_extracts_all_fixed_records_and_fields(self) -> None:
        raw = fixture_xml()
        value = target.parse_namespaced_rfc_index(raw, tuple(range(9320, 9400)))
        self.assertEqual(len(value), 80)
        self.assertEqual(value["RFC 9320"]["Title"], "Title 0")
        self.assertEqual(value["RFC 9320"]["Authors"], "A. Author0; B. Editor0, Ed.")
        self.assertEqual(value["RFC 9320"]["Published"], "March 2022")

    def test_parent_namespace_failure_is_reproduced_and_recovery_is_total(self) -> None:
        numbers = (9320, 9321, 9322, 9323)
        raw = fixture_xml(numbers)
        self.assertEqual(parent.parse_rfc_index(raw, numbers), {})
        self.assertEqual(len(target.parse_namespaced_rfc_index(raw, numbers)), 4)

    def test_parser_rejects_wrong_namespace_duplicate_and_missing_record(self) -> None:
        with self.assertRaises(ValueError):
            target.parse_namespaced_rfc_index(
                fixture_xml((9320,), namespace="urn:wrong"), (9320,)
            )
        with self.assertRaises(ValueError):
            target.parse_namespaced_rfc_index(fixture_xml((9320, 9320)), (9320,))
        with self.assertRaises(ValueError):
            target.parse_namespaced_rfc_index(fixture_xml((9320,)), (9320, 9321))

    def test_offline_guard_denies_parent_fetch_and_restores_it(self) -> None:
        original = parent._fetch_once
        with target._offline_parent_guard():
            with self.assertRaises(RuntimeError):
                parent._fetch_once()
        self.assertIs(parent._fetch_once, original)

    def test_source_has_no_network_import_or_call_and_paths_are_append_only(self) -> None:
        self.assertTrue(target._source_has_zero_network_surface(ROOT / target.SOURCE))
        source = inspect.getsource(target.replay)
        self.assertNotIn("_fetch_once(", source)
        self.assertNotEqual(target.RECOVERY_TRUTH, parent.TRUTH)
        self.assertNotEqual(target.RESULT, contract.QUALITY_RESULT)
        self.assertNotEqual(target.AUDIT, contract.QUALITY_AUDIT)

    def test_build_audit_authorizes_only_protocol_generation(self) -> None:
        test_result = {
            "pattern": target.TEST.name,
            "expected": target.EXPECTED_TESTS,
            "observed": target.EXPECTED_TESTS,
            "returncode": 0,
            "passed": True,
            "output_sha256": "a" * 64,
        }
        with mock.patch.object(target.base_audit, "_test", return_value=test_result), mock.patch.object(
            target.base_audit, "_tracked", return_value=True
        ), mock.patch.object(target, "_future_pristine", return_value=True):
            value = target.build_audit(now=1, require_clean=False)
        self.assertEqual(target.validate_build_audit(value), value)
        self.assertTrue(value["authorization"]["offline_recovery_protocol_generation"])
        self.assertFalse(value["authorization"]["snapshot_replay_or_quality_evaluation"])
        self.assertFalse(value["authorization"]["new_truth_fetch_model_search_or_deepwidebench"])

    def test_truth_artifact_replays_same_snapshot_and_tamper_fails(self) -> None:
        raw = fixture_xml()
        compressed = gzip.compress(raw, mtime=0)
        records = target.parse_namespaced_rfc_index(raw, tuple(range(9320, 9400)))
        with mock.patch.object(target, "RAW_SNAPSHOT_SHA256", target.hashlib.sha256(compressed).hexdigest()), mock.patch.object(
            target, "RAW_RESPONSE_SHA256", target.hashlib.sha256(raw).hexdigest()
        ):
            value = target._truth_artifact(raw, records, now=1)
            self.assertEqual(target.validate_truth(value, compressed), value)
            changed = copy.deepcopy(value)
            changed["valid_record_count"] = 79
            changed.pop("truth_payload_sha256")
            changed = contract.seal(changed, "truth_payload_sha256")
            with self.assertRaises(ValueError):
                target.validate_truth(changed, compressed)

    def test_recovery_uses_parent_quality_gate_and_zero_signed_credit(self) -> None:
        branch = {
            "tasks": 20,
            "valid_tasks": 20,
            "invalid_tasks": 0,
            "fallback_tasks": 0,
            "exact_table_successes": 1,
            **{name: 0.5 for name in parent.METRICS},
        }
        metrics = {
            "branches": {
                parent.route.STABLE_BRANCH: branch,
                parent.route.MEMBERSHIP_BRANCH: {**branch, "exact_table_successes": 2},
            },
            "membership_present_minus_absent": {
                "exact_table_successes": 1,
                "valid_tasks": 0,
                "invalid_tasks": 0,
                "fallback_tasks": 0,
                **{name: 0.0 for name in parent.METRICS},
            },
        }
        self.assertTrue(parent.quality_decision(metrics)["quality_gate_passed"])
        self.assertEqual(contract.quality_gate()["positive_signed_credit_count"], 0)


if __name__ == "__main__":
    unittest.main()
