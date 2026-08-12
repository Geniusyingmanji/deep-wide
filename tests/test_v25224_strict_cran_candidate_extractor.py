from __future__ import annotations

import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent import v25222_strict_cran_dcf_attestation as parent  # noqa: E402
from deepwide_agent import v25224_strict_cran_candidate_extractor as target  # noqa: E402


def body(count: int = 64, *, newline: str = "\n") -> bytes:
    records = []
    for index in range(count):
        records.append(
            newline.join(
                (
                    f"Package: Pkg{index}",
                    "Version: 1.0",
                    "License: MIT",
                    "Suggests: alpha,",
                    " beta",
                )
            )
        )
    return (newline * 2).join(records).encode("utf-8")


def extract(value: object, *, expected: bytes | None = None):
    frozen = value if expected is None and isinstance(value, bytes) else expected
    if frozen is None:
        frozen = b"x"
    return target.extract_strict_cran_candidates(
        value,
        expected_body_bytes=len(frozen),
        expected_body_sha256=hashlib.sha256(frozen).hexdigest(),
    )


class V25224StrictCranCandidateExtractorTests(unittest.TestCase):
    def test_exact_64_candidates_return_in_memory_with_count_parity(self) -> None:
        candidates, receipt = extract(body())
        self.assertEqual(candidates, [f"pkg{index}" for index in range(64)])
        self.assertTrue(receipt["extraction_completed"])
        self.assertTrue(receipt["parent_attestation_passed"])
        self.assertTrue(receipt["candidate_count_parity"])
        self.assertEqual(receipt["parsed_record_count"], 64)
        self.assertEqual(receipt["predicate_valid_record_count"], 64)
        self.assertEqual(receipt["parent_distinct_candidate_count"], 64)
        self.assertEqual(receipt["extracted_candidate_count"], 64)
        rendered = json.dumps(receipt, sort_keys=True)
        self.assertNotIn("pkg0", rendered)
        self.assertNotIn("License", rendered)
        self.assertNotIn("Suggests", rendered)

    def test_crlf_and_system_requirements_use_same_parent_semantics(self) -> None:
        snapshot = body(newline="\r\n").replace(
            b"Suggests: alpha,\r\n beta", b"SystemRequirements: libx"
        )
        candidates, receipt = extract(snapshot)
        self.assertEqual(len(candidates), 64)
        self.assertTrue(receipt["candidate_count_parity"])

    def test_parent_binding_and_parse_failures_return_no_candidates(self) -> None:
        valid = body()
        cases = (
            (valid + b"\n", valid, "body_length_binding"),
            (bytes([valid[0] ^ 1]) + valid[1:], valid, "body_sha256_binding"),
            (b"Package:X\nVersion:1\nLicense:MIT\nSuggests:a\n", None, "dcf_syntax"),
            (b"Package: X\rVersion: 1\rLicense: MIT\rSuggests: a\r", None, "newline"),
            (b"Package: X\nLicense: MIT\nSuggests: a\n", None, "minimum_candidate_coverage"),
        )
        for snapshot, expected, stage in cases:
            candidates, receipt = extract(snapshot, expected=expected)
            with self.subTest(stage=stage):
                self.assertEqual(candidates, [])
                self.assertEqual(receipt["failure_stage"], stage)
                self.assertFalse(receipt["extraction_completed"])

    def test_parent_predicate_is_invoked_per_record_without_local_approximation(self) -> None:
        snapshot = body()
        original = parent._candidate_counts
        calls: list[int] = []

        def observed(records):
            calls.append(len(records))
            return original(records)

        with mock.patch.object(parent, "_candidate_counts", side_effect=observed):
            candidates, receipt = extract(snapshot)
        self.assertEqual(len(candidates), 64)
        self.assertTrue(receipt["candidate_count_parity"])
        self.assertEqual(calls, [64] + [1] * 64)

    def test_count_parity_drift_fails_closed_without_candidates(self) -> None:
        snapshot = body()
        original = parent._candidate_counts
        calls = 0

        def drift(records):
            nonlocal calls
            calls += 1
            if calls == 1:
                return original(records)
            if calls == 2:
                return (0, 0)
            return original(records)

        with mock.patch.object(parent, "_candidate_counts", side_effect=drift):
            candidates, receipt = extract(snapshot)
        self.assertEqual(candidates, [])
        self.assertEqual(receipt["failure_stage"], "candidate_count_parity")
        self.assertFalse(receipt["candidate_count_parity"])

    def test_invalid_expected_binding_shape_raises_before_extraction(self) -> None:
        for expected_bytes, expected_hash in (
            (True, "0" * 64),
            (0, "0" * 64),
            (1, "bad"),
            (1, "G" * 64),
        ):
            with self.subTest(expected_bytes=expected_bytes), self.assertRaises(ValueError):
                target.extract_strict_cran_candidates(
                    b"x",
                    expected_body_bytes=expected_bytes,
                    expected_body_sha256=expected_hash,
                )

    def test_resealed_schema_state_count_credit_or_authority_tamper_fails(self) -> None:
        _candidates, value = extract(body())
        for kind in (
            "schema",
            "stage",
            "count",
            "credit",
            "authority",
            "parent",
            "parent_seal",
        ):
            changed = copy.deepcopy(value)
            if kind == "schema":
                changed["hidden_identity"] = "private"
            elif kind == "stage":
                changed["failure_stage"] = "candidate_count_parity"
                changed["extraction_completed"] = False
            elif kind == "count":
                changed["extracted_candidate_count"] = 63
            elif kind == "credit":
                changed["entropy_or_information_gain_assigns_signed_credit"] = True
            elif kind == "authority":
                changed[
                    "population_freeze_external_forward_runtime_compatibility_or_benchmark_authorized"
                ] = True
            elif kind == "parent":
                changed["parent_policy_id"] = "different"
            else:
                changed["parent_attestation_payload_sha256"] = "0" * 64
            changed.pop("observation_payload_sha256")
            changed["observation_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_observation(changed)

    def test_source_is_pure_label_blind_secret_free_and_evaluator_free(self) -> None:
        source = (
            ROOT / "src/deepwide_agent/v25224_strict_cran_candidate_extractor.py"
        ).read_text(encoding="utf-8")
        for forbidden in (
            "requests",
            "socket",
            "subprocess",
            "pathlib",
            "openai",
            "httpx",
            "gh" + "p_",
            "tvly-" + "dev-",
            "run_official_eval_local",
            "/mnt",
            "/data",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
