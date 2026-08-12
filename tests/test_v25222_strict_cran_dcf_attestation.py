from __future__ import annotations

import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent import v25222_strict_cran_dcf_attestation as target  # noqa: E402


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


def attest(value: object, *, expected: bytes | None = None):
    frozen = value if expected is None and isinstance(value, bytes) else expected
    if frozen is None:
        frozen = b"x"
    return target.attest_cran_packages_body(
        value,
        expected_body_bytes=len(frozen),
        expected_body_sha256=hashlib.sha256(frozen).hexdigest(),
    )


class V25222StrictCranDcfAttestationTests(unittest.TestCase):
    def test_exact_64_lf_records_pass_with_content_free_counts(self) -> None:
        snapshot = body()
        value = attest(snapshot)
        self.assertTrue(value["attestation_passed"])
        self.assertTrue(value["parse_completed"])
        self.assertIsNone(value["failure_stage"])
        self.assertEqual(value["parsed_record_count"], 64)
        self.assertEqual(value["predicate_valid_record_count"], 64)
        self.assertEqual(value["distinct_candidate_count"], 64)
        self.assertFalse(value["attestation_alone_authorizes_transport_acceptance"])

    def test_crlf_and_continuation_lines_are_supported(self) -> None:
        snapshot = body(newline="\r\n")
        value = attest(snapshot)
        self.assertTrue(value["attestation_passed"])
        self.assertEqual(value["distinct_candidate_count"], 64)

    def test_length_and_sha_binding_fail_before_parse(self) -> None:
        snapshot = body()
        longer = snapshot + b"\n"
        length = attest(snapshot, expected=longer)
        self.assertEqual(length["failure_stage"], "body_length_binding")
        self.assertFalse(length["parse_completed"])
        same_length = bytes([snapshot[0] ^ 1]) + snapshot[1:]
        digest = attest(same_length, expected=snapshot)
        self.assertEqual(digest["failure_stage"], "body_sha256_binding")
        self.assertFalse(digest["parse_completed"])

    def test_invalid_input_or_expected_binding_fails_closed(self) -> None:
        value = attest("not-bytes", expected=b"x")
        self.assertEqual(value["failure_stage"], "body_type_or_size")
        oversized = b"x" * (target.MAXIMUM_BODY_BYTES + 1)
        oversize_value = attest(oversized, expected=b"x")
        self.assertEqual(oversize_value["failure_stage"], "body_type_or_size")
        self.assertEqual(
            oversize_value["body_byte_count"], target.MAXIMUM_BODY_BYTES + 1
        )
        self.assertFalse(oversize_value["parse_completed"])
        for expected_bytes, expected_hash in (
            (True, "0" * 64),
            (0, "0" * 64),
            (1, "bad"),
            (1, "G" * 64),
        ):
            with self.subTest(expected_bytes=expected_bytes, expected_hash=expected_hash), self.assertRaises(
                ValueError
            ):
                target.attest_cran_packages_body(
                    b"x",
                    expected_body_bytes=expected_bytes,
                    expected_body_sha256=expected_hash,
                )

    def test_utf8_control_and_bare_cr_fail_with_finite_stages(self) -> None:
        cases = (
            (b"\xff", "utf8_decode"),
            (b"Package: A\x00", "control_character"),
            (b"Package: A\rVersion: 1", "newline"),
        )
        for snapshot, expected in cases:
            value = attest(snapshot)
            with self.subTest(expected=expected):
                self.assertEqual(value["failure_stage"], expected)
                self.assertFalse(value["parse_completed"])

    def test_malformed_continuation_field_and_duplicate_fail_closed(self) -> None:
        cases = (
            (b" continuation", "dcf_syntax"),
            (b"Package:A", "dcf_syntax"),
            (b"Package: A\nPackage: B", "duplicate_field"),
            (b"Package: A\n \nVersion: 1", "dcf_syntax"),
        )
        for snapshot, expected in cases:
            value = attest(snapshot)
            with self.subTest(expected=expected):
                self.assertEqual(value["failure_stage"], expected)
                self.assertEqual(value["parsed_record_count"], 0)

    def test_fewer_or_nonqualifying_records_are_coverage_failure(self) -> None:
        fewer = attest(body(63))
        self.assertEqual(fewer["failure_stage"], "minimum_candidate_coverage")
        self.assertTrue(fewer["parse_completed"])
        self.assertEqual(fewer["distinct_candidate_count"], 63)
        snapshot = body().replace(b"License: MIT", b"License: ")
        invalid = attest(snapshot)
        self.assertEqual(invalid["failure_stage"], "minimum_candidate_coverage")
        self.assertEqual(invalid["predicate_valid_record_count"], 0)

    def test_duplicate_candidate_identity_does_not_inflate_distinct_coverage(self) -> None:
        snapshot = body().replace(b"Package: Pkg63", b"Package: Pkg0")
        value = attest(snapshot)
        self.assertEqual(value["parsed_record_count"], 64)
        self.assertEqual(value["predicate_valid_record_count"], 64)
        self.assertEqual(value["distinct_candidate_count"], 63)
        self.assertFalse(value["attestation_passed"])

    def test_observation_persists_no_identity_field_value_or_body(self) -> None:
        snapshot = body()
        value = attest(snapshot)
        rendered = json.dumps(value, sort_keys=True)
        self.assertNotIn("Pkg0", rendered)
        self.assertNotIn("License", rendered)
        self.assertNotIn("Suggests", rendered)
        self.assertFalse(
            value[
                "identity_record_field_value_body_question_prediction_evidence_or_credential_persisted"
            ]
        )

    def test_resealed_schema_state_count_credit_or_authority_tamper_fails(self) -> None:
        value = attest(body())
        for kind in ("schema", "stage", "count", "credit", "authority", "binding"):
            changed = copy.deepcopy(value)
            if kind == "schema":
                changed["hidden_identity"] = "private"
            elif kind == "stage":
                changed["failure_stage"] = "minimum_candidate_coverage"
                changed["attestation_passed"] = False
            elif kind == "count":
                changed["distinct_candidate_count"] = 63
                changed["minimum_distinct_candidate_count_met"] = False
            elif kind == "credit":
                changed["entropy_or_information_gain_assigns_signed_credit"] = True
            elif kind == "authority":
                changed[
                    "population_freeze_external_forward_runtime_compatibility_or_benchmark_authorized"
                ] = True
            else:
                changed["body_sha256_matches_expected"] = False
            changed.pop("observation_payload_sha256")
            changed["observation_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_observation(changed)

    def test_source_is_pure_label_blind_secret_free_and_evaluator_free(self) -> None:
        source = (
            ROOT / "src/deepwide_agent/v25222_strict_cran_dcf_attestation.py"
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
