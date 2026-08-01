"""Pure RSA-PSS verification for a signed V2.42.28 graph declaration.

V2.42.28 binds an unpredictable launch challenge into every compatibility
envelope, but its executor declaration is unsigned.  This build-only module
adds a deterministic statement format and verifies a detached RSA-PSS/SHA-256
signature against a protocol-frozen SubjectPublicKeyInfo key.

The boundary is intentionally strict.  This module accepts a public key and a
signature, never a private key.  It has no file, environment, subprocess,
network, model, search, fetch, evaluator or benchmark-launch surface.  A valid
signature proves only that the holder of the corresponding private key signed
the exact statement bytes.  It does not prove who controlled the key, that the
signer belongs to an independent trust domain, that the statement is true,
that launch preceded execution, or that an old payload was not wrapped after
the challenge.  All such claims and all production/training/Gate-2B authority
remain frozen false.

RSA verification follows RFC 8017 EMSA-PSS with SHA-256, MGF1-SHA-256, a
32-byte salt, trailer byte 0xbc, a 2048--8192-bit modulus and exponent 65537.
Only canonical DER ``rsaEncryption`` SubjectPublicKeyInfo keys are accepted.
"""

from __future__ import annotations

import base64
import copy
import hashlib
import hmac
import json
from collections.abc import Mapping
from typing import Any

from .v24123_release import is_sha256
from .v24223_sign_preserving_credit import object_sha256
from .v24228_challenge_bound_outer_graph import (
    validate_challenge_bound_outer_pair,
    validate_challenge_execution_request,
    validate_challenge_graph_protocol,
    validate_unsigned_executor_declaration,
)


POLICY_ID = "v24229_signed_outer_graph_attestation_v1"
PROTOCOL_ROLE = "v24229_signed_attestation_protocol"
STATEMENT_ROLE = "v24229_outer_graph_signing_statement"
RECEIPT_ROLE = "v24229_verified_detached_signature_receipt"

SIGNATURE_SCHEME = "rsassa-pss-sha256"
HASH_ALGORITHM = "sha256"
MGF_ALGORITHM = "mgf1-sha256"
SALT_LENGTH = 32
TRAILER_BYTE = 0xBC
PUBLIC_EXPONENT = 65537
MIN_MODULUS_BITS = 2048
MAX_MODULUS_BITS = 8192
MAX_PUBLIC_KEY_DER_BYTES = 2048
MAX_SIGNATURE_BYTES = MAX_MODULUS_BITS // 8
SIGNING_DOMAIN = b"OWIC-V2.42.29-RSA-PSS-SHA256\x00"

PRODUCTION_PACKAGE_AUTHORIZED = False
CREDIT_TRAINING_AUTHORIZED = False
GATE2B_PASS_AUTHORIZED = False
FORMAL_GATE2B_EVALUATION_AUTHORIZED = False
OUTER_CAMPAIGN_EXECUTION_AUTHORIZED = False
BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED = False
INDEPENDENT_SIGNER_IDENTITY_VERIFIED = False
INDEPENDENT_TRUST_DOMAIN_VERIFIED = False
APPEND_ONLY_TRANSPARENCY_SERVICE_USED = False
TRUSTED_TIMESTAMP_VERIFIED = False
STATEMENT_TRUTH_INDEPENDENTLY_VERIFIED = False
LAUNCH_BEFORE_EXECUTION_INDEPENDENTLY_ATTESTED = False
EXTERNAL_TARGET_PRECOMPUTATION_EXCLUDED = False

RSA_ENCRYPTION_OID_DER = bytes.fromhex("06092a864886f70d010101")
NULL_DER = b"\x05\x00"

COMMON_SAFETY_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "label_blind_control",
        "mapping_gold_category_question_type_or_raw_evaluator_payload_available_to_control",
        "active_benchmark_forward_imported",
        "production_package_authorized",
        "credit_training_authorized",
        "gate2b_pass_authorized",
        "formal_gate2b_evaluation_authorized",
        "outer_campaign_execution_authorized",
        "benchmark_forward_or_evaluator_authorized",
    }
)

PROTOCOL_KEYS = COMMON_SAFETY_KEYS | frozenset(
    {
        "challenge_graph_protocol_sha256",
        "graph_namespace_sha256",
        "sequence_protocol_sha256",
        "outer_target_protocol_sha256",
        "signed_attestation_namespace_sha256",
        "signer_identity_sha256",
        "signer_trust_domain_sha256",
        "public_key_spki_sha256",
        "public_key_modulus_bits",
        "public_key_exponent",
        "signature_scheme",
        "hash_algorithm",
        "mgf_algorithm",
        "salt_length_bytes",
        "trailer_byte_hex",
        "signing_domain_hex",
        "canonical_json_sort_keys",
        "canonical_json_separators",
        "signature_verification_only",
        "private_key_input_accepted_or_read",
        "protocol_freezes_public_key_before_statement_verification",
        "signature_proves_only_possession_of_corresponding_private_key",
        "independent_signer_identity_verified",
        "independent_trust_domain_verified",
        "append_only_transparency_service_used",
        "trusted_timestamp_verified",
        "statement_truth_independently_verified",
        "launch_before_execution_independently_attested",
        "external_target_precomputation_excluded",
        "protocol_sha256",
    }
)

STATEMENT_KEYS = COMMON_SAFETY_KEYS | frozenset(
    {
        "signed_attestation_protocol_sha256",
        "signed_attestation_namespace_sha256",
        "signer_identity_sha256",
        "signer_trust_domain_sha256",
        "public_key_spki_sha256",
        "challenge_graph_protocol_sha256",
        "graph_namespace_sha256",
        "sequence_protocol_sha256",
        "outer_target_protocol_sha256",
        "launch_challenge_sha256",
        "execution_request_sha256",
        "challenge_prediction_freeze_sha256",
        "unsigned_executor_declaration_sha256",
        "execution_trace_sha256",
        "challenge_evaluator_provenance_sha256",
        "challenge_terminal_sha256s",
        "challenge_contribution_sha256s",
        "challenge_replicate_aggregate_sha256",
        "challenge_bound_outer_pair_sha256",
        "legacy_outer_pair_sha256",
        "statement_nonce_sha256",
        "statement_stage",
        "complete_compatibility_graph_validated_before_statement",
        "executor_declares_challenge_consumed_before_execution",
        "signature_timing_or_launch_order_claimed",
        "native_executor_challenge_consumption_independently_observed",
        "independent_signer_identity_verified",
        "independent_trust_domain_verified",
        "append_only_transparency_service_used",
        "trusted_timestamp_verified",
        "statement_truth_independently_verified",
        "launch_before_execution_independently_attested",
        "historical_payload_after_wrapping_possible",
        "external_target_precomputation_excluded",
        "statement_sha256",
    }
)

RECEIPT_KEYS = COMMON_SAFETY_KEYS | frozenset(
    {
        "signed_attestation_protocol_sha256",
        "signed_attestation_namespace_sha256",
        "signer_identity_sha256",
        "signer_trust_domain_sha256",
        "statement",
        "statement_sha256",
        "signing_message_sha256",
        "public_key_spki_der_base64",
        "public_key_spki_sha256",
        "public_key_modulus_bits",
        "public_key_exponent",
        "detached_signature_base64",
        "detached_signature_sha256",
        "signature_length_bytes",
        "signature_scheme",
        "hash_algorithm",
        "mgf_algorithm",
        "salt_length_bytes",
        "trailer_byte_hex",
        "canonical_statement_bytes_recomputed",
        "public_key_matches_frozen_protocol",
        "cryptographic_signature_verified",
        "signature_proves_only_possession_of_corresponding_private_key",
        "private_key_input_accepted_or_read",
        "independent_signer_identity_verified",
        "independent_trust_domain_verified",
        "append_only_transparency_service_used",
        "trusted_timestamp_verified",
        "statement_truth_independently_verified",
        "launch_before_execution_independently_attested",
        "historical_payload_after_wrapping_possible",
        "external_target_precomputation_excluded",
        "receipt_sha256",
    }
)


def _exact_mapping(
    value: object, *, keys: frozenset[str], label: str
) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != keys:
        raise ValueError(f"V2.42.29 {label} schema is not exact")
    return value


def _sealed(value: Mapping[str, Any], *, seal_key: str) -> bool:
    unsigned = copy.deepcopy(dict(value))
    seal = unsigned.pop(seal_key, None)
    return is_sha256(seal) and seal == object_sha256(unsigned)


def _sha256(value: object, *, label: str) -> str:
    if not is_sha256(value):
        raise ValueError(f"V2.42.29 {label} is not a SHA-256")
    return str(value)


def _bytes(value: object, *, label: str, maximum: int) -> bytes:
    if not isinstance(value, bytes) or not value or len(value) > maximum:
        raise ValueError(f"V2.42.29 {label} bytes are invalid")
    return value


def _hash_list(value: object, *, label: str, length: int) -> list[str]:
    if (
        not isinstance(value, list)
        or len(value) != length
        or len(set(value)) != length
        or any(not is_sha256(item) for item in value)
    ):
        raise ValueError(f"V2.42.29 {label} is invalid")
    return list(value)


def _base(*, role: str) -> dict[str, Any]:
    return {
        "artifact_version": 1,
        "role": role,
        "policy_id": POLICY_ID,
        "label_blind_control": True,
        "mapping_gold_category_question_type_or_raw_evaluator_payload_available_to_control": False,
        "active_benchmark_forward_imported": False,
        "production_package_authorized": PRODUCTION_PACKAGE_AUTHORIZED,
        "credit_training_authorized": CREDIT_TRAINING_AUTHORIZED,
        "gate2b_pass_authorized": GATE2B_PASS_AUTHORIZED,
        "formal_gate2b_evaluation_authorized": FORMAL_GATE2B_EVALUATION_AUTHORIZED,
        "outer_campaign_execution_authorized": OUTER_CAMPAIGN_EXECUTION_AUTHORIZED,
        "benchmark_forward_or_evaluator_authorized": BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED,
    }


def _validate_common(
    value: object,
    *,
    keys: frozenset[str],
    role: str,
    seal_key: str,
    label: str,
) -> Mapping[str, Any]:
    artifact = _exact_mapping(value, keys=keys, label=label)
    if (
        artifact.get("artifact_version") != 1
        or artifact.get("role") != role
        or artifact.get("policy_id") != POLICY_ID
        or artifact.get("label_blind_control") is not True
        or artifact.get(
            "mapping_gold_category_question_type_or_raw_evaluator_payload_available_to_control"
        )
        is not False
        or artifact.get("active_benchmark_forward_imported") is not False
        or artifact.get("production_package_authorized") is not False
        or artifact.get("credit_training_authorized") is not False
        or artifact.get("gate2b_pass_authorized") is not False
        or artifact.get("formal_gate2b_evaluation_authorized") is not False
        or artifact.get("outer_campaign_execution_authorized") is not False
        or artifact.get("benchmark_forward_or_evaluator_authorized") is not False
        or not _sealed(artifact, seal_key=seal_key)
    ):
        raise ValueError(f"V2.42.29 {label} safety boundary drifted")
    return artifact


def _read_der_length(data: bytes, offset: int) -> tuple[int, int]:
    if offset >= len(data):
        raise ValueError("V2.42.29 truncated DER length")
    first = data[offset]
    offset += 1
    if first < 0x80:
        return first, offset
    count = first & 0x7F
    if count == 0 or count > 4 or offset + count > len(data):
        raise ValueError("V2.42.29 invalid DER long length")
    encoded = data[offset : offset + count]
    if encoded[0] == 0:
        raise ValueError("V2.42.29 noncanonical DER length")
    length = int.from_bytes(encoded, "big")
    if length < 0x80:
        raise ValueError("V2.42.29 nonminimal DER length")
    return length, offset + count


def _read_der_tlv(
    data: bytes, offset: int, *, expected_tag: int
) -> tuple[bytes, int]:
    if offset >= len(data) or data[offset] != expected_tag:
        raise ValueError("V2.42.29 unexpected DER tag")
    length, content_offset = _read_der_length(data, offset + 1)
    end = content_offset + length
    if end > len(data):
        raise ValueError("V2.42.29 truncated DER value")
    return data[content_offset:end], end


def _read_positive_der_integer(data: bytes, offset: int) -> tuple[int, int]:
    encoded, end = _read_der_tlv(data, offset, expected_tag=0x02)
    if not encoded or encoded[0] & 0x80:
        raise ValueError("V2.42.29 DER integer is not positive")
    if len(encoded) > 1 and encoded[0] == 0 and encoded[1] & 0x80 == 0:
        raise ValueError("V2.42.29 DER integer is not minimal")
    return int.from_bytes(encoded, "big"), end


def parse_rsa_public_key_spki(public_key_spki_der: bytes) -> tuple[int, int]:
    """Parse one canonical ``rsaEncryption`` SPKI and return ``(n, e)``."""

    der = _bytes(
        public_key_spki_der,
        label="public key SPKI DER",
        maximum=MAX_PUBLIC_KEY_DER_BYTES,
    )
    outer, outer_end = _read_der_tlv(der, 0, expected_tag=0x30)
    if outer_end != len(der):
        raise ValueError("V2.42.29 public key DER has trailing bytes")
    algorithm, algorithm_end = _read_der_tlv(outer, 0, expected_tag=0x30)
    if algorithm != RSA_ENCRYPTION_OID_DER + NULL_DER:
        raise ValueError("V2.42.29 public key algorithm is not canonical RSA")
    bit_string, bit_string_end = _read_der_tlv(
        outer, algorithm_end, expected_tag=0x03
    )
    if bit_string_end != len(outer) or not bit_string or bit_string[0] != 0:
        raise ValueError("V2.42.29 public key BIT STRING is invalid")
    rsa_der = bit_string[1:]
    rsa_sequence, rsa_end = _read_der_tlv(rsa_der, 0, expected_tag=0x30)
    if rsa_end != len(rsa_der):
        raise ValueError("V2.42.29 RSA key has trailing bytes")
    modulus, offset = _read_positive_der_integer(rsa_sequence, 0)
    exponent, offset = _read_positive_der_integer(rsa_sequence, offset)
    if offset != len(rsa_sequence):
        raise ValueError("V2.42.29 RSA key contains extra fields")
    modulus_bits = modulus.bit_length()
    if (
        modulus_bits < MIN_MODULUS_BITS
        or modulus_bits > MAX_MODULUS_BITS
        or exponent != PUBLIC_EXPONENT
        or modulus % 2 == 0
    ):
        raise ValueError("V2.42.29 RSA public key policy failed")
    return modulus, exponent


def _mgf1_sha256(seed: bytes, length: int) -> bytes:
    if length < 0 or length > MAX_SIGNATURE_BYTES:
        raise ValueError("V2.42.29 MGF1 length is invalid")
    output = bytearray()
    counter = 0
    while len(output) < length:
        output.extend(
            hashlib.sha256(seed + counter.to_bytes(4, "big")).digest()
        )
        counter += 1
    return bytes(output[:length])


def verify_rsa_pss_sha256(
    *,
    public_key_spki_der: bytes,
    message: bytes,
    signature: bytes,
) -> bool:
    """Verify the frozen RSA-PSS/SHA-256 profile without private-key access."""

    modulus, exponent = parse_rsa_public_key_spki(public_key_spki_der)
    payload = _bytes(message, label="signing message", maximum=2_000_000)
    sig = _bytes(signature, label="detached signature", maximum=MAX_SIGNATURE_BYTES)
    modulus_bits = modulus.bit_length()
    modulus_bytes = (modulus_bits + 7) // 8
    if len(sig) != modulus_bytes:
        return False
    signature_integer = int.from_bytes(sig, "big")
    if signature_integer >= modulus:
        return False
    encoded = pow(signature_integer, exponent, modulus).to_bytes(
        modulus_bytes, "big"
    )
    encoded_bits = modulus_bits - 1
    encoded_length = (encoded_bits + 7) // 8
    if len(encoded) != encoded_length:
        return False
    digest_length = hashlib.sha256().digest_size
    if encoded_length < digest_length + SALT_LENGTH + 2:
        return False
    if encoded[-1] != TRAILER_BYTE:
        return False
    masked_db = encoded[: encoded_length - digest_length - 1]
    digest = encoded[encoded_length - digest_length - 1 : -1]
    unused_bits = 8 * encoded_length - encoded_bits
    if unused_bits and masked_db[0] >> (8 - unused_bits):
        return False
    mask = _mgf1_sha256(digest, len(masked_db))
    database = bytearray(left ^ right for left, right in zip(masked_db, mask))
    if unused_bits:
        database[0] &= 0xFF >> unused_bits
    padding_length = encoded_length - digest_length - SALT_LENGTH - 2
    if (
        any(database[:padding_length])
        or database[padding_length] != 0x01
    ):
        return False
    salt = bytes(database[-SALT_LENGTH:])
    message_hash = hashlib.sha256(payload).digest()
    expected = hashlib.sha256(
        b"\x00" * 8 + message_hash + salt
    ).digest()
    return hmac.compare_digest(digest, expected)


def _canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def canonical_attestation_message(statement: Mapping[str, Any]) -> bytes:
    """Return the exact domain-separated bytes that an external signer signs."""

    validate_outer_graph_signing_statement(statement)
    return SIGNING_DOMAIN + _canonical_json_bytes(statement)


def _canonical_base64(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")


def _decode_canonical_base64(
    value: object, *, label: str, maximum: int
) -> bytes:
    if not isinstance(value, str) or not value:
        raise ValueError(f"V2.42.29 {label} base64 is invalid")
    try:
        decoded = base64.b64decode(value, validate=True)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"V2.42.29 {label} base64 is invalid") from exc
    if (
        not decoded
        or len(decoded) > maximum
        or _canonical_base64(decoded) != value
    ):
        raise ValueError(f"V2.42.29 {label} base64 is noncanonical")
    return decoded


def build_signed_attestation_protocol(
    *,
    challenge_graph_protocol: Mapping[str, Any],
    signed_attestation_namespace_sha256: str,
    signer_identity_sha256: str,
    signer_trust_domain_sha256: str,
    public_key_spki_der: bytes,
) -> dict[str, Any]:
    """Freeze a public verification key and exact signature parameters."""

    validate_challenge_graph_protocol(challenge_graph_protocol)
    key = _bytes(
        public_key_spki_der,
        label="public key SPKI DER",
        maximum=MAX_PUBLIC_KEY_DER_BYTES,
    )
    modulus, exponent = parse_rsa_public_key_spki(key)
    value = _base(role=PROTOCOL_ROLE)
    value.update(
        {
            "challenge_graph_protocol_sha256": challenge_graph_protocol[
                "protocol_sha256"
            ],
            "graph_namespace_sha256": challenge_graph_protocol[
                "graph_namespace_sha256"
            ],
            "sequence_protocol_sha256": challenge_graph_protocol[
                "sequence_protocol_sha256"
            ],
            "outer_target_protocol_sha256": challenge_graph_protocol[
                "outer_target_protocol_sha256"
            ],
            "signed_attestation_namespace_sha256": _sha256(
                signed_attestation_namespace_sha256,
                label="signed attestation namespace",
            ),
            "signer_identity_sha256": _sha256(
                signer_identity_sha256, label="signer identity"
            ),
            "signer_trust_domain_sha256": _sha256(
                signer_trust_domain_sha256, label="signer trust domain"
            ),
            "public_key_spki_sha256": hashlib.sha256(key).hexdigest(),
            "public_key_modulus_bits": modulus.bit_length(),
            "public_key_exponent": exponent,
            "signature_scheme": SIGNATURE_SCHEME,
            "hash_algorithm": HASH_ALGORITHM,
            "mgf_algorithm": MGF_ALGORITHM,
            "salt_length_bytes": SALT_LENGTH,
            "trailer_byte_hex": f"{TRAILER_BYTE:02x}",
            "signing_domain_hex": SIGNING_DOMAIN.hex(),
            "canonical_json_sort_keys": True,
            "canonical_json_separators": [",", ":"],
            "signature_verification_only": True,
            "private_key_input_accepted_or_read": False,
            "protocol_freezes_public_key_before_statement_verification": True,
            "signature_proves_only_possession_of_corresponding_private_key": True,
            "independent_signer_identity_verified": INDEPENDENT_SIGNER_IDENTITY_VERIFIED,
            "independent_trust_domain_verified": INDEPENDENT_TRUST_DOMAIN_VERIFIED,
            "append_only_transparency_service_used": APPEND_ONLY_TRANSPARENCY_SERVICE_USED,
            "trusted_timestamp_verified": TRUSTED_TIMESTAMP_VERIFIED,
            "statement_truth_independently_verified": STATEMENT_TRUTH_INDEPENDENTLY_VERIFIED,
            "launch_before_execution_independently_attested": LAUNCH_BEFORE_EXECUTION_INDEPENDENTLY_ATTESTED,
            "external_target_precomputation_excluded": EXTERNAL_TARGET_PRECOMPUTATION_EXCLUDED,
        }
    )
    value["protocol_sha256"] = object_sha256(value)
    validate_signed_attestation_protocol(
        value, challenge_graph_protocol=challenge_graph_protocol
    )
    return value


def validate_signed_attestation_protocol(
    value: object,
    *,
    challenge_graph_protocol: Mapping[str, Any] | None = None,
    public_key_spki_der: bytes | None = None,
) -> None:
    protocol = _validate_common(
        value,
        keys=PROTOCOL_KEYS,
        role=PROTOCOL_ROLE,
        seal_key="protocol_sha256",
        label="signed attestation protocol",
    )
    hashes = (
        "challenge_graph_protocol_sha256",
        "graph_namespace_sha256",
        "sequence_protocol_sha256",
        "outer_target_protocol_sha256",
        "signed_attestation_namespace_sha256",
        "signer_identity_sha256",
        "signer_trust_domain_sha256",
        "public_key_spki_sha256",
    )
    true_fields = (
        "canonical_json_sort_keys",
        "signature_verification_only",
        "protocol_freezes_public_key_before_statement_verification",
        "signature_proves_only_possession_of_corresponding_private_key",
    )
    false_fields = (
        "private_key_input_accepted_or_read",
        "independent_signer_identity_verified",
        "independent_trust_domain_verified",
        "append_only_transparency_service_used",
        "trusted_timestamp_verified",
        "statement_truth_independently_verified",
        "launch_before_execution_independently_attested",
        "external_target_precomputation_excluded",
    )
    modulus_bits = protocol.get("public_key_modulus_bits")
    if (
        any(not is_sha256(protocol.get(key)) for key in hashes)
        or isinstance(modulus_bits, bool)
        or not isinstance(modulus_bits, int)
        or not MIN_MODULUS_BITS <= modulus_bits <= MAX_MODULUS_BITS
        or protocol.get("public_key_exponent") != PUBLIC_EXPONENT
        or protocol.get("signature_scheme") != SIGNATURE_SCHEME
        or protocol.get("hash_algorithm") != HASH_ALGORITHM
        or protocol.get("mgf_algorithm") != MGF_ALGORITHM
        or protocol.get("salt_length_bytes") != SALT_LENGTH
        or protocol.get("trailer_byte_hex") != f"{TRAILER_BYTE:02x}"
        or protocol.get("signing_domain_hex") != SIGNING_DOMAIN.hex()
        or protocol.get("canonical_json_separators") != [",", ":"]
        or any(protocol.get(key) is not True for key in true_fields)
        or any(protocol.get(key) is not False for key in false_fields)
    ):
        raise ValueError("V2.42.29 signed attestation protocol drifted")
    if challenge_graph_protocol is not None:
        validate_challenge_graph_protocol(challenge_graph_protocol)
        bindings = {
            "challenge_graph_protocol_sha256": "protocol_sha256",
            "graph_namespace_sha256": "graph_namespace_sha256",
            "sequence_protocol_sha256": "sequence_protocol_sha256",
            "outer_target_protocol_sha256": "outer_target_protocol_sha256",
        }
        if any(
            protocol[left] != challenge_graph_protocol[right]
            for left, right in bindings.items()
        ):
            raise ValueError("V2.42.29 challenge protocol binding drifted")
    if public_key_spki_der is not None:
        key = _bytes(
            public_key_spki_der,
            label="public key SPKI DER",
            maximum=MAX_PUBLIC_KEY_DER_BYTES,
        )
        modulus, exponent = parse_rsa_public_key_spki(key)
        if (
            hashlib.sha256(key).hexdigest()
            != protocol["public_key_spki_sha256"]
            or modulus.bit_length() != modulus_bits
            or exponent != protocol["public_key_exponent"]
        ):
            raise ValueError("V2.42.29 frozen public key binding drifted")


def build_outer_graph_signing_statement(
    *,
    protocol: Mapping[str, Any],
    challenge_graph_protocol: Mapping[str, Any],
    execution_request: Mapping[str, Any],
    unsigned_executor_declaration: Mapping[str, Any],
    challenge_bound_outer_pair: Mapping[str, Any],
    statement_nonce_sha256: str,
) -> dict[str, Any]:
    """Bind the completed compatibility graph into one signable declaration."""

    validate_signed_attestation_protocol(
        protocol, challenge_graph_protocol=challenge_graph_protocol
    )
    validate_challenge_execution_request(
        execution_request, protocol=challenge_graph_protocol
    )
    validate_unsigned_executor_declaration(
        unsigned_executor_declaration,
        protocol=challenge_graph_protocol,
        request=execution_request,
    )
    validate_challenge_bound_outer_pair(
        challenge_bound_outer_pair,
        protocol=challenge_graph_protocol,
        request=execution_request,
        executor_attestation=unsigned_executor_declaration,
    )
    if (
        challenge_bound_outer_pair["execution_request_sha256"]
        != execution_request["request_sha256"]
        or challenge_bound_outer_pair["executor_attestation_sha256"]
        != unsigned_executor_declaration["attestation_sha256"]
    ):
        raise ValueError("V2.42.29 completed graph parent binding drifted")
    value = _base(role=STATEMENT_ROLE)
    value.update(
        {
            "signed_attestation_protocol_sha256": protocol["protocol_sha256"],
            "signed_attestation_namespace_sha256": protocol[
                "signed_attestation_namespace_sha256"
            ],
            "signer_identity_sha256": protocol["signer_identity_sha256"],
            "signer_trust_domain_sha256": protocol[
                "signer_trust_domain_sha256"
            ],
            "public_key_spki_sha256": protocol["public_key_spki_sha256"],
            "challenge_graph_protocol_sha256": challenge_graph_protocol[
                "protocol_sha256"
            ],
            "graph_namespace_sha256": challenge_graph_protocol[
                "graph_namespace_sha256"
            ],
            "sequence_protocol_sha256": challenge_graph_protocol[
                "sequence_protocol_sha256"
            ],
            "outer_target_protocol_sha256": challenge_graph_protocol[
                "outer_target_protocol_sha256"
            ],
            "launch_challenge_sha256": execution_request[
                "launch_challenge_sha256"
            ],
            "execution_request_sha256": execution_request["request_sha256"],
            "challenge_prediction_freeze_sha256": challenge_bound_outer_pair[
                "challenge_prediction_freeze_sha256"
            ],
            "unsigned_executor_declaration_sha256": unsigned_executor_declaration[
                "attestation_sha256"
            ],
            "execution_trace_sha256": unsigned_executor_declaration[
                "execution_trace_sha256"
            ],
            "challenge_evaluator_provenance_sha256": challenge_bound_outer_pair[
                "challenge_evaluator_provenance_sha256"
            ],
            "challenge_terminal_sha256s": challenge_bound_outer_pair[
                "challenge_terminal_sha256s"
            ],
            "challenge_contribution_sha256s": challenge_bound_outer_pair[
                "challenge_contribution_sha256s"
            ],
            "challenge_replicate_aggregate_sha256": challenge_bound_outer_pair[
                "challenge_replicate_aggregate_sha256"
            ],
            "challenge_bound_outer_pair_sha256": challenge_bound_outer_pair[
                "pair_sha256"
            ],
            "legacy_outer_pair_sha256": challenge_bound_outer_pair[
                "legacy_outer_pair_sha256"
            ],
            "statement_nonce_sha256": _sha256(
                statement_nonce_sha256, label="statement nonce"
            ),
            "statement_stage": "post_graph_compatibility_declaration",
            "complete_compatibility_graph_validated_before_statement": True,
            "executor_declares_challenge_consumed_before_execution": True,
            "signature_timing_or_launch_order_claimed": False,
            "native_executor_challenge_consumption_independently_observed": False,
            "independent_signer_identity_verified": INDEPENDENT_SIGNER_IDENTITY_VERIFIED,
            "independent_trust_domain_verified": INDEPENDENT_TRUST_DOMAIN_VERIFIED,
            "append_only_transparency_service_used": APPEND_ONLY_TRANSPARENCY_SERVICE_USED,
            "trusted_timestamp_verified": TRUSTED_TIMESTAMP_VERIFIED,
            "statement_truth_independently_verified": STATEMENT_TRUTH_INDEPENDENTLY_VERIFIED,
            "launch_before_execution_independently_attested": LAUNCH_BEFORE_EXECUTION_INDEPENDENTLY_ATTESTED,
            "historical_payload_after_wrapping_possible": True,
            "external_target_precomputation_excluded": EXTERNAL_TARGET_PRECOMPUTATION_EXCLUDED,
        }
    )
    value["statement_sha256"] = object_sha256(value)
    validate_outer_graph_signing_statement(
        value,
        protocol=protocol,
        challenge_graph_protocol=challenge_graph_protocol,
        execution_request=execution_request,
        unsigned_executor_declaration=unsigned_executor_declaration,
        challenge_bound_outer_pair=challenge_bound_outer_pair,
    )
    return value


def validate_outer_graph_signing_statement(
    value: object,
    *,
    protocol: Mapping[str, Any] | None = None,
    challenge_graph_protocol: Mapping[str, Any] | None = None,
    execution_request: Mapping[str, Any] | None = None,
    unsigned_executor_declaration: Mapping[str, Any] | None = None,
    challenge_bound_outer_pair: Mapping[str, Any] | None = None,
) -> None:
    statement = _validate_common(
        value,
        keys=STATEMENT_KEYS,
        role=STATEMENT_ROLE,
        seal_key="statement_sha256",
        label="outer graph signing statement",
    )
    hashes = (
        "signed_attestation_protocol_sha256",
        "signed_attestation_namespace_sha256",
        "signer_identity_sha256",
        "signer_trust_domain_sha256",
        "public_key_spki_sha256",
        "challenge_graph_protocol_sha256",
        "graph_namespace_sha256",
        "sequence_protocol_sha256",
        "outer_target_protocol_sha256",
        "launch_challenge_sha256",
        "execution_request_sha256",
        "challenge_prediction_freeze_sha256",
        "unsigned_executor_declaration_sha256",
        "execution_trace_sha256",
        "challenge_evaluator_provenance_sha256",
        "challenge_replicate_aggregate_sha256",
        "challenge_bound_outer_pair_sha256",
        "legacy_outer_pair_sha256",
        "statement_nonce_sha256",
    )
    _hash_list(
        statement.get("challenge_terminal_sha256s"),
        label="challenge terminals",
        length=6,
    )
    _hash_list(
        statement.get("challenge_contribution_sha256s"),
        label="challenge contributions",
        length=3,
    )
    true_fields = (
        "complete_compatibility_graph_validated_before_statement",
        "executor_declares_challenge_consumed_before_execution",
        "historical_payload_after_wrapping_possible",
    )
    false_fields = (
        "signature_timing_or_launch_order_claimed",
        "native_executor_challenge_consumption_independently_observed",
        "independent_signer_identity_verified",
        "independent_trust_domain_verified",
        "append_only_transparency_service_used",
        "trusted_timestamp_verified",
        "statement_truth_independently_verified",
        "launch_before_execution_independently_attested",
        "external_target_precomputation_excluded",
    )
    if (
        any(not is_sha256(statement.get(key)) for key in hashes)
        or statement.get("statement_stage")
        != "post_graph_compatibility_declaration"
        or any(statement.get(key) is not True for key in true_fields)
        or any(statement.get(key) is not False for key in false_fields)
    ):
        raise ValueError("V2.42.29 signing statement drifted")
    if protocol is not None:
        validate_signed_attestation_protocol(
            protocol, challenge_graph_protocol=challenge_graph_protocol
        )
        bindings = {
            "signed_attestation_protocol_sha256": "protocol_sha256",
            "signed_attestation_namespace_sha256": "signed_attestation_namespace_sha256",
            "signer_identity_sha256": "signer_identity_sha256",
            "signer_trust_domain_sha256": "signer_trust_domain_sha256",
            "public_key_spki_sha256": "public_key_spki_sha256",
        }
        if any(statement[left] != protocol[right] for left, right in bindings.items()):
            raise ValueError("V2.42.29 statement protocol binding drifted")
    if challenge_graph_protocol is not None:
        validate_challenge_graph_protocol(challenge_graph_protocol)
        bindings = {
            "challenge_graph_protocol_sha256": "protocol_sha256",
            "graph_namespace_sha256": "graph_namespace_sha256",
            "sequence_protocol_sha256": "sequence_protocol_sha256",
            "outer_target_protocol_sha256": "outer_target_protocol_sha256",
        }
        if any(
            statement[left] != challenge_graph_protocol[right]
            for left, right in bindings.items()
        ):
            raise ValueError("V2.42.29 statement challenge protocol binding drifted")
    if execution_request is not None:
        validate_challenge_execution_request(
            execution_request, protocol=challenge_graph_protocol
        )
        if (
            statement["execution_request_sha256"]
            != execution_request["request_sha256"]
            or statement["launch_challenge_sha256"]
            != execution_request["launch_challenge_sha256"]
        ):
            raise ValueError("V2.42.29 statement request binding drifted")
    if unsigned_executor_declaration is not None:
        validate_unsigned_executor_declaration(
            unsigned_executor_declaration,
            protocol=challenge_graph_protocol,
            request=execution_request,
        )
        if (
            statement["unsigned_executor_declaration_sha256"]
            != unsigned_executor_declaration["attestation_sha256"]
            or statement["execution_trace_sha256"]
            != unsigned_executor_declaration["execution_trace_sha256"]
        ):
            raise ValueError("V2.42.29 statement executor binding drifted")
    if challenge_bound_outer_pair is not None:
        validate_challenge_bound_outer_pair(
            challenge_bound_outer_pair,
            protocol=challenge_graph_protocol,
            request=execution_request,
            executor_attestation=unsigned_executor_declaration,
        )
        bindings = {
            "challenge_prediction_freeze_sha256": "challenge_prediction_freeze_sha256",
            "challenge_evaluator_provenance_sha256": "challenge_evaluator_provenance_sha256",
            "challenge_replicate_aggregate_sha256": "challenge_replicate_aggregate_sha256",
            "challenge_bound_outer_pair_sha256": "pair_sha256",
            "legacy_outer_pair_sha256": "legacy_outer_pair_sha256",
        }
        if (
            any(
                statement[left] != challenge_bound_outer_pair[right]
                for left, right in bindings.items()
            )
            or statement["challenge_terminal_sha256s"]
            != challenge_bound_outer_pair["challenge_terminal_sha256s"]
            or statement["challenge_contribution_sha256s"]
            != challenge_bound_outer_pair["challenge_contribution_sha256s"]
        ):
            raise ValueError("V2.42.29 statement outer pair binding drifted")


def build_verified_signature_receipt(
    *,
    protocol: Mapping[str, Any],
    statement: Mapping[str, Any],
    public_key_spki_der: bytes,
    detached_signature: bytes,
) -> dict[str, Any]:
    """Verify a detached signature and return a self-contained public receipt."""

    key = _bytes(
        public_key_spki_der,
        label="public key SPKI DER",
        maximum=MAX_PUBLIC_KEY_DER_BYTES,
    )
    signature = _bytes(
        detached_signature,
        label="detached signature",
        maximum=MAX_SIGNATURE_BYTES,
    )
    validate_signed_attestation_protocol(
        protocol, public_key_spki_der=key
    )
    validate_outer_graph_signing_statement(statement, protocol=protocol)
    message = canonical_attestation_message(statement)
    if not verify_rsa_pss_sha256(
        public_key_spki_der=key,
        message=message,
        signature=signature,
    ):
        raise ValueError("V2.42.29 detached signature verification failed")
    modulus, exponent = parse_rsa_public_key_spki(key)
    value = _base(role=RECEIPT_ROLE)
    value.update(
        {
            "signed_attestation_protocol_sha256": protocol["protocol_sha256"],
            "signed_attestation_namespace_sha256": protocol[
                "signed_attestation_namespace_sha256"
            ],
            "signer_identity_sha256": protocol["signer_identity_sha256"],
            "signer_trust_domain_sha256": protocol[
                "signer_trust_domain_sha256"
            ],
            "statement": copy.deepcopy(dict(statement)),
            "statement_sha256": statement["statement_sha256"],
            "signing_message_sha256": hashlib.sha256(message).hexdigest(),
            "public_key_spki_der_base64": _canonical_base64(key),
            "public_key_spki_sha256": hashlib.sha256(key).hexdigest(),
            "public_key_modulus_bits": modulus.bit_length(),
            "public_key_exponent": exponent,
            "detached_signature_base64": _canonical_base64(signature),
            "detached_signature_sha256": hashlib.sha256(signature).hexdigest(),
            "signature_length_bytes": len(signature),
            "signature_scheme": SIGNATURE_SCHEME,
            "hash_algorithm": HASH_ALGORITHM,
            "mgf_algorithm": MGF_ALGORITHM,
            "salt_length_bytes": SALT_LENGTH,
            "trailer_byte_hex": f"{TRAILER_BYTE:02x}",
            "canonical_statement_bytes_recomputed": True,
            "public_key_matches_frozen_protocol": True,
            "cryptographic_signature_verified": True,
            "signature_proves_only_possession_of_corresponding_private_key": True,
            "private_key_input_accepted_or_read": False,
            "independent_signer_identity_verified": INDEPENDENT_SIGNER_IDENTITY_VERIFIED,
            "independent_trust_domain_verified": INDEPENDENT_TRUST_DOMAIN_VERIFIED,
            "append_only_transparency_service_used": APPEND_ONLY_TRANSPARENCY_SERVICE_USED,
            "trusted_timestamp_verified": TRUSTED_TIMESTAMP_VERIFIED,
            "statement_truth_independently_verified": STATEMENT_TRUTH_INDEPENDENTLY_VERIFIED,
            "launch_before_execution_independently_attested": LAUNCH_BEFORE_EXECUTION_INDEPENDENTLY_ATTESTED,
            "historical_payload_after_wrapping_possible": True,
            "external_target_precomputation_excluded": EXTERNAL_TARGET_PRECOMPUTATION_EXCLUDED,
        }
    )
    value["receipt_sha256"] = object_sha256(value)
    validate_verified_signature_receipt(value, protocol=protocol)
    return value


def validate_verified_signature_receipt(
    value: object, *, protocol: Mapping[str, Any] | None = None
) -> None:
    receipt = _validate_common(
        value,
        keys=RECEIPT_KEYS,
        role=RECEIPT_ROLE,
        seal_key="receipt_sha256",
        label="verified signature receipt",
    )
    key = _decode_canonical_base64(
        receipt.get("public_key_spki_der_base64"),
        label="public key SPKI DER",
        maximum=MAX_PUBLIC_KEY_DER_BYTES,
    )
    signature = _decode_canonical_base64(
        receipt.get("detached_signature_base64"),
        label="detached signature",
        maximum=MAX_SIGNATURE_BYTES,
    )
    modulus, exponent = parse_rsa_public_key_spki(key)
    statement = receipt.get("statement")
    validate_outer_graph_signing_statement(statement, protocol=protocol)
    message = canonical_attestation_message(statement)
    hashes = (
        "signed_attestation_protocol_sha256",
        "signed_attestation_namespace_sha256",
        "signer_identity_sha256",
        "signer_trust_domain_sha256",
        "statement_sha256",
        "signing_message_sha256",
        "public_key_spki_sha256",
        "detached_signature_sha256",
    )
    true_fields = (
        "canonical_statement_bytes_recomputed",
        "public_key_matches_frozen_protocol",
        "cryptographic_signature_verified",
        "signature_proves_only_possession_of_corresponding_private_key",
        "historical_payload_after_wrapping_possible",
    )
    false_fields = (
        "private_key_input_accepted_or_read",
        "independent_signer_identity_verified",
        "independent_trust_domain_verified",
        "append_only_transparency_service_used",
        "trusted_timestamp_verified",
        "statement_truth_independently_verified",
        "launch_before_execution_independently_attested",
        "external_target_precomputation_excluded",
    )
    if (
        any(not is_sha256(receipt.get(key)) for key in hashes)
        or receipt["statement_sha256"] != statement["statement_sha256"]
        or receipt["signing_message_sha256"]
        != hashlib.sha256(message).hexdigest()
        or receipt["public_key_spki_sha256"]
        != hashlib.sha256(key).hexdigest()
        or receipt["detached_signature_sha256"]
        != hashlib.sha256(signature).hexdigest()
        or receipt.get("public_key_modulus_bits") != modulus.bit_length()
        or receipt.get("public_key_exponent") != exponent
        or receipt.get("signature_length_bytes") != len(signature)
        or receipt.get("signature_scheme") != SIGNATURE_SCHEME
        or receipt.get("hash_algorithm") != HASH_ALGORITHM
        or receipt.get("mgf_algorithm") != MGF_ALGORITHM
        or receipt.get("salt_length_bytes") != SALT_LENGTH
        or receipt.get("trailer_byte_hex") != f"{TRAILER_BYTE:02x}"
        or any(receipt.get(key) is not True for key in true_fields)
        or any(receipt.get(key) is not False for key in false_fields)
        or not verify_rsa_pss_sha256(
            public_key_spki_der=key,
            message=message,
            signature=signature,
        )
    ):
        raise ValueError("V2.42.29 verified signature receipt drifted")
    if protocol is not None:
        validate_signed_attestation_protocol(
            protocol, public_key_spki_der=key
        )
        bindings = {
            "signed_attestation_protocol_sha256": "protocol_sha256",
            "signed_attestation_namespace_sha256": "signed_attestation_namespace_sha256",
            "signer_identity_sha256": "signer_identity_sha256",
            "signer_trust_domain_sha256": "signer_trust_domain_sha256",
            "public_key_spki_sha256": "public_key_spki_sha256",
            "public_key_modulus_bits": "public_key_modulus_bits",
            "public_key_exponent": "public_key_exponent",
        }
        if any(receipt[left] != protocol[right] for left, right in bindings.items()):
            raise ValueError("V2.42.29 receipt protocol binding drifted")
