from __future__ import annotations

import ast
import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent import v25215_offline_candidate_discovery as target  # noqa: E402


class V25215OfflineCandidateDiscoveryTests(unittest.TestCase):
    def test_crates_json_predicate_and_receipt_are_content_free(self) -> None:
        snapshot = json.dumps(
            {
                "crates": [
                    {"id": "Secret-Crate", "max_version": "1.2", "description": "x"},
                    {"id": "missing-version", "max_version": "", "description": "x"},
                    {"id": "missing-description", "max_version": "1", "description": ""},
                    {"id": "secret-crate", "max_version": "2", "description": "duplicate"},
                ]
            }
        ).encode()
        candidates, receipt = target.discover_candidates(
            snapshot, stratum=target.STRATA[0]
        )
        self.assertEqual(candidates, ["secret-crate"])
        self.assertEqual(receipt["parsed_record_count"], 4)
        self.assertEqual(receipt["predicate_valid_record_count"], 2)
        self.assertEqual(receipt["distinct_candidate_count"], 1)
        self.assertNotIn("secret-crate", json.dumps(receipt))

    def test_cran_dcf_continuation_and_multivalue_predicate(self) -> None:
        snapshot = (
            "Package: SecretPkg\nVersion: 1\nLicense: GPL-2 |\n GPL-3\nSuggests: a, b\n\n"
            "Package: NoMulti\nVersion: 1\nLicense: MIT\n\n"
            "Package: HasSystem\nLicense: BSD\nSystemRequirements: libx\n"
        ).encode()
        candidates, receipt = target.discover_candidates(
            snapshot, stratum=target.STRATA[1]
        )
        self.assertEqual(candidates, ["secretpkg", "hassystem"])
        self.assertEqual(receipt["parsed_record_count"], 3)
        self.assertEqual(receipt["predicate_valid_record_count"], 2)
        self.assertNotIn("secretpkg", json.dumps(receipt))

    def test_crossref_json_requires_all_single_snapshot_fields(self) -> None:
        snapshot = json.dumps(
            {
                "message": {
                    "items": [
                        {
                            "DOI": "10.1/Secret",
                            "title": ["Title"],
                            "publisher": "Publisher",
                            "container-title": ["Venue"],
                        },
                        {
                            "DOI": "10.1/missing",
                            "title": [],
                            "publisher": "Publisher",
                            "container-title": ["Venue"],
                        },
                    ]
                }
            }
        ).encode()
        candidates, receipt = target.discover_candidates(
            snapshot, stratum=target.STRATA[2]
        )
        self.assertEqual(candidates, ["10.1/secret"])
        self.assertEqual(receipt["parsed_record_count"], 2)
        self.assertEqual(receipt["predicate_valid_record_count"], 1)
        self.assertNotIn("10.1/secret", json.dumps(receipt))

    def test_pypi_simple_anchor_is_pep503_bound_and_short(self) -> None:
        snapshot = (
            '<!doctype html><a href="/simple/Ab.C/">Ab.C</a>'
            '<a href="/simple/wrong/">Other</a>'
            '<a href="/simple/xy/">xy</a>'
            '<a href="/simple/LongProject/">LongProject</a>'
            '<a href="/simple/ab-c/">ab_c</a>'
        ).encode()
        candidates, receipt = target.discover_candidates(
            snapshot, stratum=target.STRATA[3]
        )
        self.assertEqual(candidates, ["ab-c"])
        self.assertEqual(receipt["parsed_record_count"], 5)
        self.assertEqual(receipt["predicate_valid_record_count"], 2)
        self.assertEqual(receipt["distinct_candidate_count"], 1)
        self.assertNotIn("ab-c", json.dumps(receipt))

    def test_exact_64_candidates_meet_minimum_without_persisting_values(self) -> None:
        rows = [
            {"id": f"private-{index}", "max_version": "1", "description": "x"}
            for index in range(64)
        ]
        candidates, receipt = target.discover_candidates(
            json.dumps({"crates": rows}).encode(), stratum=target.STRATA[0]
        )
        self.assertEqual(len(candidates), 64)
        self.assertTrue(receipt["minimum_candidate_count_met"])
        self.assertNotIn("private-0", json.dumps(receipt))

    def test_failure_stages_are_finite_and_content_free(self) -> None:
        cases = (
            (None, target.STRATA[0], "snapshot_type_or_size"),
            (b"\xff", target.STRATA[0], "decode"),
            (b"{", target.STRATA[0], "json_parse"),
            (b"{}", target.STRATA[0], "schema"),
            (b" secret-value", target.STRATA[1], "dcf_parse"),
        )
        for snapshot, stratum, stage in cases:
            candidates, receipt = target.discover_candidates(snapshot, stratum=stratum)
            with self.subTest(stage=stage):
                self.assertEqual(candidates, [])
                self.assertEqual(receipt["failure_stage"], stage)
                self.assertEqual(receipt["parsed_record_count"], 0)
                self.assertNotIn("secret-value", json.dumps(receipt))

    def test_unknown_stratum_and_observation_tamper_fail_closed(self) -> None:
        with self.assertRaises(ValueError):
            target.discover_candidates(b"{}", stratum="unknown")
        value = target.observation(
            stratum=target.STRATA[0],
            snapshot_sha256="0" * 64,
            snapshot_byte_count=1,
            parsed_record_count=1,
            predicate_valid_record_count=1,
            distinct_candidate_count=1,
            failure_stage=None,
        )
        for field in (
            "contains_identity_item_hash_record_field_value_page_question_prediction_evidence_or_credential",
            "population_freeze_external_protocol_or_benchmark_authorized",
            "entropy_or_information_gain_assigns_signed_credit",
        ):
            changed = copy.deepcopy(value)
            changed[field] = True
            changed.pop("observation_payload_sha256")
            changed["observation_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(field=field), self.assertRaises(ValueError):
                target.validate_observation(changed)

    def test_module_is_label_blind_and_has_no_effect_capability(self) -> None:
        path = ROOT / "src/deepwide_agent/v25215_offline_candidate_discovery.py"
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        imports = {
            node.names[0].name if isinstance(node, ast.Import) else node.module or ""
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
        }
        calls = {
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }
        privileged = {
            "category",
            "question_type",
            "task_category",
            "split",
            "ground_truth",
            "gold",
            "answer_key",
            "score",
            "reward",
        }
        accesses = {
            str(node.slice.value)
            for node in ast.walk(tree)
            if isinstance(node, ast.Subscript)
            and isinstance(node.slice, ast.Constant)
            and node.slice.value in privileged
        }
        self.assertTrue(
            imports.isdisjoint(
                {"os", "pathlib", "subprocess", "socket", "requests", "httpx", "openai"}
            )
        )
        self.assertTrue(
            calls.isdisjoint(
                {"open", "read_text", "write_text", "run", "complete", "search_many", "fetch_urls"}
            )
        )
        self.assertEqual(accesses, set())
        for forbidden in ("ghp_", "tvly-dev-"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
