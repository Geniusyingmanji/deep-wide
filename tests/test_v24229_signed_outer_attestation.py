from __future__ import annotations

import base64
import copy
import hashlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from deepwide_agent.v24223_sign_preserving_credit import object_sha256  # noqa: E402
from deepwide_agent.v24229_signed_outer_attestation import (  # noqa: E402
    APPEND_ONLY_TRANSPARENCY_SERVICE_USED,
    BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED,
    CREDIT_TRAINING_AUTHORIZED,
    EXTERNAL_TARGET_PRECOMPUTATION_EXCLUDED,
    FORMAL_GATE2B_EVALUATION_AUTHORIZED,
    GATE2B_PASS_AUTHORIZED,
    INDEPENDENT_SIGNER_IDENTITY_VERIFIED,
    INDEPENDENT_TRUST_DOMAIN_VERIFIED,
    LAUNCH_BEFORE_EXECUTION_INDEPENDENTLY_ATTESTED,
    OUTER_CAMPAIGN_EXECUTION_AUTHORIZED,
    PRODUCTION_PACKAGE_AUTHORIZED,
    STATEMENT_TRUTH_INDEPENDENTLY_VERIFIED,
    TRUSTED_TIMESTAMP_VERIFIED,
    build_outer_graph_signing_statement,
    build_signed_attestation_protocol,
    build_verified_signature_receipt,
    canonical_attestation_message,
    parse_rsa_public_key_spki,
    validate_outer_graph_signing_statement,
    validate_signed_attestation_protocol,
    validate_verified_signature_receipt,
    verify_rsa_pss_sha256,
)
from tests.test_v24226_credit_outer_target_firewall import digest  # noqa: E402
from tests import test_v24228_challenge_bound_outer_graph as v24228_fixture  # noqa: E402


def reseal(value: dict[str, object], field: str) -> None:
    value.pop(field, None)
    value[field] = object_sha256(value)


class V24229SignedOuterAttestationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        openssl = shutil.which("openssl")
        if openssl is None:
            raise unittest.SkipTest("OpenSSL is unavailable")
        cls.openssl = openssl
        cls.temp = tempfile.TemporaryDirectory(
            prefix="v24229-test-", dir=ROOT
        )
        cls.directory = Path(cls.temp.name)
        cls.private_key = cls.directory / "signer-private.pem"
        cls.public_key = cls.directory / "signer-public.pem"
        cls.public_der = cls.directory / "signer-public.der"
        cls.other_private_key = cls.directory / "other-private.pem"
        cls.other_public_key = cls.directory / "other-public.pem"
        cls.other_public_der = cls.directory / "other-public.der"
        cls.short_private_key = cls.directory / "short-private.pem"
        cls.short_public_der = cls.directory / "short-public.der"
        cls.ec_private_key = cls.directory / "ec-private.pem"
        cls.ec_public_der = cls.directory / "ec-public.der"
        cls._generate_rsa(
            cls.private_key, cls.public_key, cls.public_der, bits=2048
        )
        cls._generate_rsa(
            cls.other_private_key,
            cls.other_public_key,
            cls.other_public_der,
            bits=2048,
        )
        cls._generate_rsa(
            cls.short_private_key,
            cls.directory / "short-public.pem",
            cls.short_public_der,
            bits=1024,
        )
        cls._run(
            "genpkey",
            "-algorithm",
            "EC",
            "-pkeyopt",
            "ec_paramgen_curve:P-256",
            "-out",
            str(cls.ec_private_key),
        )
        cls._run(
            "pkey",
            "-in",
            str(cls.ec_private_key),
            "-pubout",
            "-outform",
            "DER",
            "-out",
            str(cls.ec_public_der),
        )
        v24228_fixture.V24228ChallengeBoundOuterGraphTests.setUpClass()
        cls.graph_case = v24228_fixture.V24228ChallengeBoundOuterGraphTests(
            methodName="runTest"
        )
        cls.graph = cls.graph_case.build_graph()
        cls.public_der_bytes = cls.public_der.read_bytes()
        cls.protocol = build_signed_attestation_protocol(
            challenge_graph_protocol=cls.graph_case.protocol,
            signed_attestation_namespace_sha256=digest("1"),
            signer_identity_sha256=digest("2"),
            signer_trust_domain_sha256=digest("3"),
            public_key_spki_der=cls.public_der_bytes,
        )
        cls.statement = build_outer_graph_signing_statement(
            protocol=cls.protocol,
            challenge_graph_protocol=cls.graph_case.protocol,
            execution_request=cls.graph["request"],  # type: ignore[arg-type]
            unsigned_executor_declaration=cls.graph["attestation"],  # type: ignore[arg-type]
            challenge_bound_outer_pair=cls.graph["pair"],  # type: ignore[arg-type]
            statement_nonce_sha256=digest("4"),
        )
        cls.message = canonical_attestation_message(cls.statement)
        cls.signature = cls._sign(cls.private_key, cls.message, salt_length=32)
        cls.receipt = build_verified_signature_receipt(
            protocol=cls.protocol,
            statement=cls.statement,
            public_key_spki_der=cls.public_der_bytes,
            detached_signature=cls.signature,
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temp.cleanup()

    @classmethod
    def _run(cls, *arguments: str) -> None:
        subprocess.run(
            [cls.openssl, *arguments],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=20,
        )

    @classmethod
    def _generate_rsa(
        cls,
        private_key: Path,
        public_key: Path,
        public_der: Path,
        *,
        bits: int,
    ) -> None:
        cls._run(
            "genpkey",
            "-algorithm",
            "RSA",
            "-pkeyopt",
            f"rsa_keygen_bits:{bits}",
            "-out",
            str(private_key),
        )
        cls._run(
            "pkey",
            "-in",
            str(private_key),
            "-pubout",
            "-out",
            str(public_key),
        )
        cls._run(
            "pkey",
            "-in",
            str(private_key),
            "-pubout",
            "-outform",
            "DER",
            "-out",
            str(public_der),
        )

    @classmethod
    def _sign(
        cls, private_key: Path, message: bytes, *, salt_length: int
    ) -> bytes:
        message_path = cls.directory / f"message-{hashlib.sha256(message).hexdigest()}"
        signature_path = cls.directory / (
            f"signature-{hashlib.sha256(message).hexdigest()}-{salt_length}"
        )
        message_path.write_bytes(message)
        cls._run(
            "dgst",
            "-sha256",
            "-sign",
            str(private_key),
            "-sigopt",
            "rsa_padding_mode:pss",
            "-sigopt",
            f"rsa_pss_saltlen:{salt_length}",
            "-out",
            str(signature_path),
            str(message_path),
        )
        signature = signature_path.read_bytes()
        message_path.unlink()
        signature_path.unlink()
        return signature

    def test_openssl_signature_cross_verifies_and_receipt_is_self_contained(self) -> None:
        self.assertTrue(
            verify_rsa_pss_sha256(
                public_key_spki_der=self.public_der_bytes,
                message=self.message,
                signature=self.signature,
            )
        )
        validate_signed_attestation_protocol(
            self.protocol,
            challenge_graph_protocol=self.graph_case.protocol,
            public_key_spki_der=self.public_der_bytes,
        )
        validate_outer_graph_signing_statement(
            self.statement,
            protocol=self.protocol,
            challenge_graph_protocol=self.graph_case.protocol,
            execution_request=self.graph["request"],  # type: ignore[arg-type]
            unsigned_executor_declaration=self.graph["attestation"],  # type: ignore[arg-type]
            challenge_bound_outer_pair=self.graph["pair"],  # type: ignore[arg-type]
        )
        validate_verified_signature_receipt(
            self.receipt, protocol=self.protocol
        )
        self.assertTrue(self.receipt["cryptographic_signature_verified"])
        self.assertEqual(
            base64.b64decode(self.receipt["public_key_spki_der_base64"]),
            self.public_der_bytes,
        )
        self.assertEqual(
            base64.b64decode(self.receipt["detached_signature_base64"]),
            self.signature,
        )

    def test_all_authority_and_trust_claims_remain_false(self) -> None:
        constants = (
            PRODUCTION_PACKAGE_AUTHORIZED,
            CREDIT_TRAINING_AUTHORIZED,
            GATE2B_PASS_AUTHORIZED,
            FORMAL_GATE2B_EVALUATION_AUTHORIZED,
            OUTER_CAMPAIGN_EXECUTION_AUTHORIZED,
            BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED,
            INDEPENDENT_SIGNER_IDENTITY_VERIFIED,
            INDEPENDENT_TRUST_DOMAIN_VERIFIED,
            APPEND_ONLY_TRANSPARENCY_SERVICE_USED,
            TRUSTED_TIMESTAMP_VERIFIED,
            STATEMENT_TRUTH_INDEPENDENTLY_VERIFIED,
            LAUNCH_BEFORE_EXECUTION_INDEPENDENTLY_ATTESTED,
            EXTERNAL_TARGET_PRECOMPUTATION_EXCLUDED,
        )
        self.assertEqual(constants, (False,) * len(constants))
        self.assertTrue(
            self.receipt[
                "signature_proves_only_possession_of_corresponding_private_key"
            ]
        )
        self.assertFalse(self.receipt["private_key_input_accepted_or_read"])
        self.assertTrue(self.receipt["historical_payload_after_wrapping_possible"])
        for field in (
            "independent_signer_identity_verified",
            "independent_trust_domain_verified",
            "append_only_transparency_service_used",
            "trusted_timestamp_verified",
            "statement_truth_independently_verified",
            "launch_before_execution_independently_attested",
            "external_target_precomputation_excluded",
            "formal_gate2b_evaluation_authorized",
            "credit_training_authorized",
            "benchmark_forward_or_evaluator_authorized",
        ):
            self.assertFalse(self.receipt[field], field)

    def test_wrong_key_tampered_signature_and_wrong_salt_fail(self) -> None:
        other_key = self.other_public_der.read_bytes()
        self.assertFalse(
            verify_rsa_pss_sha256(
                public_key_spki_der=other_key,
                message=self.message,
                signature=self.signature,
            )
        )
        tampered_signature = bytearray(self.signature)
        tampered_signature[-1] ^= 1
        self.assertFalse(
            verify_rsa_pss_sha256(
                public_key_spki_der=self.public_der_bytes,
                message=self.message,
                signature=bytes(tampered_signature),
            )
        )
        wrong_salt = self._sign(self.private_key, self.message, salt_length=20)
        self.assertFalse(
            verify_rsa_pss_sha256(
                public_key_spki_der=self.public_der_bytes,
                message=self.message,
                signature=wrong_salt,
            )
        )

    def test_resealed_statement_tamper_cannot_reuse_signature(self) -> None:
        statement = copy.deepcopy(self.statement)
        statement["execution_trace_sha256"] = digest("5")
        reseal(statement, "statement_sha256")
        validate_outer_graph_signing_statement(statement, protocol=self.protocol)
        self.assertFalse(
            verify_rsa_pss_sha256(
                public_key_spki_der=self.public_der_bytes,
                message=canonical_attestation_message(statement),
                signature=self.signature,
            )
        )
        with self.assertRaisesRegex(ValueError, "verification failed"):
            build_verified_signature_receipt(
                protocol=self.protocol,
                statement=statement,
                public_key_spki_der=self.public_der_bytes,
                detached_signature=self.signature,
            )

    def test_swapped_pair_and_challenge_fail_statement_binding(self) -> None:
        pair_value = copy.deepcopy(self.graph["pair"])
        pair_value["launch_challenge_sha256"] = digest("6")
        reseal(pair_value, "pair_sha256")
        with self.assertRaises(ValueError):
            build_outer_graph_signing_statement(
                protocol=self.protocol,
                challenge_graph_protocol=self.graph_case.protocol,
                execution_request=self.graph["request"],  # type: ignore[arg-type]
                unsigned_executor_declaration=self.graph["attestation"],  # type: ignore[arg-type]
                challenge_bound_outer_pair=pair_value,
                statement_nonce_sha256=digest("4"),
            )

    def test_public_key_policy_rejects_short_ec_and_trailing_der(self) -> None:
        modulus, exponent = parse_rsa_public_key_spki(self.public_der_bytes)
        self.assertGreaterEqual(modulus.bit_length(), 2048)
        self.assertEqual(exponent, 65537)
        for value in (
            self.short_public_der.read_bytes(),
            self.ec_public_der.read_bytes(),
            self.public_der_bytes + b"\x00",
        ):
            with self.subTest(length=len(value)):
                with self.assertRaises(ValueError):
                    parse_rsa_public_key_spki(value)

    def test_receipt_rechecks_signature_after_reseal(self) -> None:
        receipt = copy.deepcopy(self.receipt)
        signature = bytearray(
            base64.b64decode(receipt["detached_signature_base64"])
        )
        signature[0] ^= 1
        receipt["detached_signature_base64"] = base64.b64encode(
            signature
        ).decode("ascii")
        receipt["detached_signature_sha256"] = hashlib.sha256(
            signature
        ).hexdigest()
        reseal(receipt, "receipt_sha256")
        with self.assertRaisesRegex(ValueError, "receipt drifted"):
            validate_verified_signature_receipt(receipt, protocol=self.protocol)

    def test_noncanonical_base64_and_extra_privileged_fields_fail(self) -> None:
        receipt = copy.deepcopy(self.receipt)
        receipt["public_key_spki_der_base64"] += "\n"
        reseal(receipt, "receipt_sha256")
        with self.assertRaisesRegex(ValueError, "base64"):
            validate_verified_signature_receipt(receipt, protocol=self.protocol)
        for validator, value, seal in (
            (
                validate_signed_attestation_protocol,
                self.protocol,
                "protocol_sha256",
            ),
            (
                validate_outer_graph_signing_statement,
                self.statement,
                "statement_sha256",
            ),
            (
                validate_verified_signature_receipt,
                self.receipt,
                "receipt_sha256",
            ),
        ):
            with self.subTest(validator=validator.__name__):
                changed = copy.deepcopy(value)
                changed["question_type"] = "forbidden"
                reseal(changed, seal)
                with self.assertRaisesRegex(ValueError, "schema is not exact"):
                    validator(changed)

    def test_canonical_message_is_deterministic_and_domain_separated(self) -> None:
        first = canonical_attestation_message(self.statement)
        second = canonical_attestation_message(copy.deepcopy(self.statement))
        self.assertEqual(first, second)
        self.assertNotEqual(first, str(self.statement).encode("utf-8"))
        self.assertEqual(hashlib.sha256(first).hexdigest(), self.receipt["signing_message_sha256"])


if __name__ == "__main__":
    unittest.main()
