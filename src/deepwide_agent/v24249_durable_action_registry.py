"""Durable content-free action allocation for the V2.42.48 facade.

V2.42.48 accepts a caller-supplied content-free action reference.  That keeps
prompt/query/URL bytes out of durable invocation identity, but a caller can
still choose a new scope, stage, or ordinal.  This isolated candidate removes
that choice *inside one registry instance*: initialization samples a random
instance domain, derives one fixed stage per operation, and every public
effect method durably appends the next global ordinal before calling the exact
V2.42.48 facade.

The registry is deliberately content blind.  It cannot identify two equal
prompts, queries, or URLs, so two caller invocations remain two distinct
actions.  It also cannot prove that a caller created only one registry for a
logical task.  Local ``flock``, create-exclusive files, and ``fsync`` cover
cooperating processes on one local POSIX filesystem only.  They do not attest
adapter code identity, exclude malicious same-user resealing, or authorize
active clients, provider traffic, benchmark execution, or evaluation.
"""

from __future__ import annotations

import copy
import dataclasses
import fcntl
import json
import os
import re
import secrets
import stat
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Mapping

from deepwide_agent.v24232_webswarm_total_budget import object_sha256
from deepwide_agent.v24248_candidate_client_facade import (
    OPERATION_KINDS,
    CandidateClientFacade,
    CandidateClientFacadeResult,
    CandidateFacadeActionRef,
    derive_candidate_facade_action_ref,
    validate_candidate_client_facade_contract,
    validate_candidate_client_facade_receipt,
)


POLICY_ID = "v24249_durable_action_registry_v1"
INITIAL_ROLE = "v24249_durable_action_registry_initial"
CLAIM_ROLE = "v24249_durable_action_claim"
RECEIPT_ROLE = "v24249_registered_facade_receipt"
STATUS_ROLE = "v24249_durable_action_registry_status"

PRODUCTION_PACKAGE_AUTHORIZED = False
ACTIVE_FORWARD_INTEGRATION_AUTHORIZED = False
ACTIVE_PROVIDER_TRAFFIC_AUTHORIZED = False
EXTERNAL_SIDE_EFFECT_AUTHORIZED = False
BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED = False
DEV64_OR_EXACT220_LAUNCH_AUTHORIZED = False
SHARED_API_LEASE_ACQUIRE_AUTHORIZED = False
LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED = False

OS_CSPRNG_INSTANCE_DOMAIN_IMPLEMENTED = True
FIXED_OPERATION_STAGE_REFS_IMPLEMENTED = True
GLOBAL_MONOTONIC_ACTION_ORDINAL_IMPLEMENTED = True
DURABLE_CLAIM_BEFORE_FACADE_EFFECT_IMPLEMENTED = True
LOCAL_POSIX_ADVISORY_LOCK_IMPLEMENTED = True
FILE_AND_DIRECTORY_FSYNC_IMPLEMENTED = True
CALLER_SUPPLIED_ACTION_REF_ACCEPTED = False
EPHEMERAL_REQUEST_CONTENT_USED_FOR_ACTION_IDENTITY = False
EQUAL_EPHEMERAL_REQUEST_DEDUPLICATION_IMPLEMENTED = False
CALLER_SINGLE_REGISTRY_OWNERSHIP_INDEPENDENTLY_VERIFIED = False
DIRECT_PARENT_FACADE_BYPASS_GLOBALLY_EXCLUDED = False
ACTION_CLAIM_ORDER_EQUALS_EFFECT_COMPLETION_ORDER_VERIFIED = False
CLAIM_TO_EFFECT_OUTCOME_DURABLE_BINDING_IMPLEMENTED = False
CLAIMED_BUT_UNSTARTED_ACTION_RECOVERY_IMPLEMENTED = False
INITIALIZATION_CRASH_AUTOMATIC_RECOVERY_IMPLEMENTED = False
ADAPTER_CODE_IDENTITY_INDEPENDENTLY_ATTESTED = False
MALICIOUS_SAME_USER_RESEALING_EXCLUDED = False
NETWORK_OR_DISTRIBUTED_FILESYSTEM_SEMANTICS_PROVEN = False
SEARCH_LEADS_OR_PAGE_TEXT_ACTIVE_EVIDENCE_ELIGIBILITY_GRANTED = False

INITIAL_FILE = "initial.json"
LOCK_FILE = "registry.lock"
CLAIMS_DIRECTORY = "claims"
CLAIM_NAME = re.compile(r"^(?P<ordinal>[0-9]{20})\.json$")
MAX_FILE_BYTES = 4_000_000
MAX_CLAIMS = 1_000_000

INITIAL_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "facade_contract_sha256",
        "instance_nonce_sha256",
        "task_scope_ref_sha256",
        "fixed_stage_refs",
        "os_csprng_instance_domain_used",
        "ephemeral_request_content_used_for_action_identity",
        "caller_single_registry_ownership_independently_verified",
        "direct_parent_facade_bypass_globally_excluded",
        "action_claim_order_equals_effect_completion_order_verified",
        "adapter_code_identity_independently_attested",
        "malicious_same_user_resealing_excluded",
        "network_or_distributed_filesystem_semantics_proven",
        "active_forward_integration_authorized",
        "benchmark_forward_or_evaluator_authorized",
        "initial_sha256",
    }
)
CLAIM_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "registry_initial_sha256",
        "facade_contract_sha256",
        "task_scope_ref_sha256",
        "operation_kind",
        "stage_ref_sha256",
        "action_ordinal",
        "previous_claim_sha256",
        "action_ref",
        "action_ref_sha256",
        "global_monotonic_action_ordinal",
        "durable_claim_before_facade_effect",
        "file_and_directory_fsync_attempted",
        "ephemeral_request_content_used_for_action_identity",
        "caller_supplied_action_ref_accepted",
        "equal_ephemeral_request_deduplication_implemented",
        "active_forward_integration_authorized",
        "benchmark_forward_or_evaluator_authorized",
        "claim_sha256",
    }
)
ACTION_REF_KEYS = frozenset(
    {
        "task_scope_ref_sha256",
        "stage_ref_sha256",
        "operation_kind",
        "action_ordinal",
        "action_ref_sha256",
    }
)
RECEIPT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "registry_initial",
        "registry_initial_sha256",
        "action_claim",
        "action_claim_sha256",
        "facade_receipt",
        "facade_receipt_sha256",
        "facade_contract_sha256",
        "operation_kind",
        "durable_claim_before_facade_effect",
        "claim_prefix_replayed_from_store_when_receipt_validated",
        "raw_prompt_query_url_provider_value_or_projected_output_entered_receipt",
        "ephemeral_request_content_used_for_action_identity",
        "caller_supplied_action_ref_accepted",
        "equal_ephemeral_request_deduplication_implemented",
        "caller_single_registry_ownership_independently_verified",
        "direct_parent_facade_bypass_globally_excluded",
        "action_claim_order_equals_effect_completion_order_verified",
        "adapter_code_identity_independently_attested",
        "malicious_same_user_resealing_excluded",
        "search_leads_or_page_text_active_evidence_eligibility_granted",
        "active_forward_integration_authorized",
        "benchmark_forward_or_evaluator_authorized",
        "registered_receipt_sha256",
    }
)


class DurableActionRegistryError(RuntimeError):
    """Sanitized durable registry error without request content."""


class DurableActionRegistryPoisoned(DurableActionRegistryError):
    """Unexpected or partial durable bytes block further allocation."""


@dataclasses.dataclass(frozen=True)
class DurableRegisteredFacadeResult:
    receipt: Mapping[str, Any]
    value: Any


def _clone(value: Any) -> Any:
    return copy.deepcopy(value)


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _exact(value: Mapping[str, Any], *, keys: frozenset[str], label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != keys:
        raise DurableActionRegistryPoisoned(f"V2.42.49 {label} schema drifted")
    return dict(value)


def _sealed(value: Mapping[str, Any], *, key: str) -> bool:
    seal = value.get(key)
    if not _is_sha256(seal):
        return False
    unsigned = dict(value)
    unsigned.pop(key)
    return seal == object_sha256(unsigned)


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise DurableActionRegistryPoisoned("V2.42.49 duplicate JSON key rejected")
        value[key] = item
    return value


def _reject_constant(value: str) -> None:
    raise DurableActionRegistryPoisoned("V2.42.49 non-finite JSON constant rejected")


def _encoded(value: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def _ordinary_directory(path: Path, *, label: str) -> Path:
    candidate = path.absolute()
    try:
        metadata = path.lstat()
    except FileNotFoundError as error:
        raise ValueError(f"V2.42.49 {label} is absent") from error
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or path.is_symlink()
        or path.resolve(strict=True) != candidate
    ):
        raise ValueError(f"V2.42.49 {label} is not an ordinary directory")
    return candidate


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _publish_new(path: Path, value: Mapping[str, Any]) -> None:
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(_encoded(value))
            handle.flush()
            os.fsync(handle.fileno())
        _fsync_directory(path.parent)
    except BaseException:
        try:
            os.close(descriptor)
        except OSError:
            pass
        raise


def _read_object(path: Path) -> dict[str, Any]:
    try:
        metadata = path.lstat()
    except FileNotFoundError as error:
        raise DurableActionRegistryPoisoned("V2.42.49 required file is absent") from error
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_nlink != 1
        or metadata.st_size > MAX_FILE_BYTES
    ):
        raise DurableActionRegistryPoisoned("V2.42.49 durable file is nonordinary")
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    payload = bytearray()
    try:
        opened = os.fstat(descriptor)
        if (
            not stat.S_ISREG(opened.st_mode)
            or opened.st_nlink != 1
            or opened.st_dev != metadata.st_dev
            or opened.st_ino != metadata.st_ino
            or opened.st_size != metadata.st_size
            or opened.st_mtime_ns != metadata.st_mtime_ns
            or opened.st_ctime_ns != metadata.st_ctime_ns
        ):
            raise DurableActionRegistryPoisoned("V2.42.49 durable file changed during open")
        while len(payload) <= MAX_FILE_BYTES:
            chunk = os.read(descriptor, min(65_536, MAX_FILE_BYTES + 1 - len(payload)))
            if not chunk:
                break
            payload.extend(chunk)
        if len(payload) > MAX_FILE_BYTES or os.read(descriptor, 1):
            raise DurableActionRegistryPoisoned("V2.42.49 durable file exceeds size cap")
        final = os.fstat(descriptor)
        if (
            final.st_dev != opened.st_dev
            or final.st_ino != opened.st_ino
            or final.st_size != opened.st_size
            or final.st_mtime_ns != opened.st_mtime_ns
            or final.st_ctime_ns != opened.st_ctime_ns
        ):
            raise DurableActionRegistryPoisoned("V2.42.49 durable file changed during read")
    finally:
        os.close(descriptor)
    try:
        value = json.loads(
            bytes(payload).decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise DurableActionRegistryPoisoned("V2.42.49 durable JSON is invalid") from error
    if not isinstance(value, dict):
        raise DurableActionRegistryPoisoned("V2.42.49 durable value is not an object")
    return value


def _action_mapping(action: CandidateFacadeActionRef) -> dict[str, Any]:
    return {
        "task_scope_ref_sha256": action.task_scope_ref_sha256,
        "stage_ref_sha256": action.stage_ref_sha256,
        "operation_kind": action.operation_kind,
        "action_ordinal": action.action_ordinal,
        "action_ref_sha256": action.action_ref_sha256,
    }


def _derive_initial(*, facade_contract_sha256: str, nonce: bytes) -> dict[str, Any]:
    if not _is_sha256(facade_contract_sha256) or type(nonce) is not bytes or len(nonce) != 32:
        raise ValueError("V2.42.49 initialization inputs are invalid")
    nonce_sha256 = object_sha256(
        {"policy_id": POLICY_ID, "random_instance_nonce_hex": nonce.hex()}
    )
    task_scope = object_sha256(
        {
            "policy_id": POLICY_ID,
            "facade_contract_sha256": facade_contract_sha256,
            "instance_nonce_sha256": nonce_sha256,
            "ephemeral_request_content_used": False,
        }
    )
    stages = {
        operation: object_sha256(
            {
                "policy_id": POLICY_ID,
                "task_scope_ref_sha256": task_scope,
                "operation_kind": operation,
                "fixed_operation_stage": True,
                "ephemeral_request_content_used": False,
            }
        )
        for operation in sorted(OPERATION_KINDS)
    }
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": INITIAL_ROLE,
        "policy_id": POLICY_ID,
        "facade_contract_sha256": facade_contract_sha256,
        "instance_nonce_sha256": nonce_sha256,
        "task_scope_ref_sha256": task_scope,
        "fixed_stage_refs": stages,
        "os_csprng_instance_domain_used": True,
        "ephemeral_request_content_used_for_action_identity": False,
        "caller_single_registry_ownership_independently_verified": False,
        "direct_parent_facade_bypass_globally_excluded": False,
        "action_claim_order_equals_effect_completion_order_verified": False,
        "adapter_code_identity_independently_attested": False,
        "malicious_same_user_resealing_excluded": False,
        "network_or_distributed_filesystem_semantics_proven": False,
        "active_forward_integration_authorized": False,
        "benchmark_forward_or_evaluator_authorized": False,
    }
    value["initial_sha256"] = object_sha256(value)
    return value


def validate_durable_action_registry_initial(value: Mapping[str, Any]) -> None:
    initial = _exact(value, keys=INITIAL_KEYS, label="initial record")
    stages = initial.get("fixed_stage_refs")
    if not isinstance(stages, Mapping) or set(stages) != OPERATION_KINDS:
        raise DurableActionRegistryPoisoned("V2.42.49 fixed stages drifted")
    task_scope = initial.get("task_scope_ref_sha256")
    expected_task_scope = object_sha256(
        {
            "policy_id": POLICY_ID,
            "facade_contract_sha256": initial.get("facade_contract_sha256"),
            "instance_nonce_sha256": initial.get("instance_nonce_sha256"),
            "ephemeral_request_content_used": False,
        }
    )
    if (
        initial.get("artifact_version") != 1
        or initial.get("role") != INITIAL_ROLE
        or initial.get("policy_id") != POLICY_ID
        or not _is_sha256(initial.get("facade_contract_sha256"))
        or not _is_sha256(initial.get("instance_nonce_sha256"))
        or not _is_sha256(task_scope)
        or task_scope != expected_task_scope
        or any(not _is_sha256(stages.get(operation)) for operation in OPERATION_KINDS)
        or initial.get("os_csprng_instance_domain_used") is not True
        or initial.get("ephemeral_request_content_used_for_action_identity") is not False
        or initial.get("caller_single_registry_ownership_independently_verified") is not False
        or initial.get("direct_parent_facade_bypass_globally_excluded") is not False
        or initial.get("action_claim_order_equals_effect_completion_order_verified") is not False
        or initial.get("adapter_code_identity_independently_attested") is not False
        or initial.get("malicious_same_user_resealing_excluded") is not False
        or initial.get("network_or_distributed_filesystem_semantics_proven") is not False
        or initial.get("active_forward_integration_authorized") is not False
        or initial.get("benchmark_forward_or_evaluator_authorized") is not False
        or not _sealed(initial, key="initial_sha256")
    ):
        raise DurableActionRegistryPoisoned("V2.42.49 initial record drifted")
    expected_stages = {
        operation: object_sha256(
            {
                "policy_id": POLICY_ID,
                "task_scope_ref_sha256": task_scope,
                "operation_kind": operation,
                "fixed_operation_stage": True,
                "ephemeral_request_content_used": False,
            }
        )
        for operation in sorted(OPERATION_KINDS)
    }
    if dict(stages) != expected_stages:
        raise DurableActionRegistryPoisoned("V2.42.49 fixed stages drifted")


def _validate_claim(
    value: Mapping[str, Any],
    *,
    initial: Mapping[str, Any],
    expected_ordinal: int,
    expected_previous_claim_sha256: str | None,
) -> CandidateFacadeActionRef:
    claim = _exact(value, keys=CLAIM_KEYS, label="action claim")
    operation = claim.get("operation_kind")
    if operation not in OPERATION_KINDS:
        raise DurableActionRegistryPoisoned("V2.42.49 claim operation drifted")
    try:
        action = derive_candidate_facade_action_ref(
            task_scope_ref_sha256=str(initial["task_scope_ref_sha256"]),
            stage_ref_sha256=str(initial["fixed_stage_refs"][operation]),
            operation_kind=str(operation),
            action_ordinal=expected_ordinal,
        )
    except (KeyError, TypeError, ValueError) as error:
        raise DurableActionRegistryPoisoned("V2.42.49 claim action replay failed") from error
    action_mapping = claim.get("action_ref")
    if (
        claim.get("artifact_version") != 1
        or claim.get("role") != CLAIM_ROLE
        or claim.get("policy_id") != POLICY_ID
        or claim.get("registry_initial_sha256") != initial.get("initial_sha256")
        or claim.get("facade_contract_sha256") != initial.get("facade_contract_sha256")
        or claim.get("task_scope_ref_sha256") != initial.get("task_scope_ref_sha256")
        or claim.get("stage_ref_sha256") != initial["fixed_stage_refs"][operation]
        or claim.get("action_ordinal") != expected_ordinal
        or claim.get("previous_claim_sha256") != expected_previous_claim_sha256
        or not isinstance(action_mapping, Mapping)
        or set(action_mapping) != ACTION_REF_KEYS
        or dict(action_mapping) != _action_mapping(action)
        or claim.get("action_ref_sha256") != action.action_ref_sha256
        or claim.get("global_monotonic_action_ordinal") is not True
        or claim.get("durable_claim_before_facade_effect") is not True
        or claim.get("file_and_directory_fsync_attempted") is not True
        or claim.get("ephemeral_request_content_used_for_action_identity") is not False
        or claim.get("caller_supplied_action_ref_accepted") is not False
        or claim.get("equal_ephemeral_request_deduplication_implemented") is not False
        or claim.get("active_forward_integration_authorized") is not False
        or claim.get("benchmark_forward_or_evaluator_authorized") is not False
        or not _sealed(claim, key="claim_sha256")
    ):
        raise DurableActionRegistryPoisoned("V2.42.49 action claim drifted")
    return action


def validate_registered_facade_receipt(value: Mapping[str, Any]) -> None:
    receipt = _exact(value, keys=RECEIPT_KEYS, label="registered facade receipt")
    initial = receipt.get("registry_initial")
    claim = receipt.get("action_claim")
    facade = receipt.get("facade_receipt")
    if not isinstance(initial, Mapping) or not isinstance(claim, Mapping) or not isinstance(facade, Mapping):
        raise ValueError("V2.42.49 registered receipt drifted")
    try:
        validate_durable_action_registry_initial(initial)
        ordinal = claim.get("action_ordinal")
        if not isinstance(ordinal, int) or isinstance(ordinal, bool) or ordinal < 1:
            raise ValueError("ordinal")
        previous = claim.get("previous_claim_sha256")
        if (ordinal == 1 and previous is not None) or (
            ordinal > 1 and not _is_sha256(previous)
        ):
            raise ValueError("previous claim")
        _validate_claim(
            claim,
            initial=initial,
            expected_ordinal=ordinal,
            expected_previous_claim_sha256=previous,
        )
        validate_candidate_client_facade_receipt(facade)
    except (KeyError, TypeError, ValueError, DurableActionRegistryPoisoned):
        raise ValueError("V2.42.49 registered receipt drifted") from None
    if (
        receipt.get("artifact_version") != 1
        or receipt.get("role") != RECEIPT_ROLE
        or receipt.get("policy_id") != POLICY_ID
        or receipt.get("registry_initial_sha256") != initial.get("initial_sha256")
        or receipt.get("action_claim_sha256") != claim.get("claim_sha256")
        or receipt.get("facade_receipt_sha256") != facade.get("facade_receipt_sha256")
        or receipt.get("facade_contract_sha256") != initial.get("facade_contract_sha256")
        or receipt.get("facade_contract_sha256") != facade.get("facade_contract_sha256")
        or receipt.get("operation_kind") != claim.get("operation_kind")
        or receipt.get("operation_kind") != facade.get("operation_kind")
        or facade.get("action_ref") != claim.get("action_ref")
        or receipt.get("durable_claim_before_facade_effect") is not True
        or receipt.get("claim_prefix_replayed_from_store_when_receipt_validated") is not False
        or receipt.get("raw_prompt_query_url_provider_value_or_projected_output_entered_receipt") is not False
        or receipt.get("ephemeral_request_content_used_for_action_identity") is not False
        or receipt.get("caller_supplied_action_ref_accepted") is not False
        or receipt.get("equal_ephemeral_request_deduplication_implemented") is not False
        or receipt.get("caller_single_registry_ownership_independently_verified") is not False
        or receipt.get("direct_parent_facade_bypass_globally_excluded") is not False
        or receipt.get("action_claim_order_equals_effect_completion_order_verified") is not False
        or receipt.get("adapter_code_identity_independently_attested") is not False
        or receipt.get("malicious_same_user_resealing_excluded") is not False
        or receipt.get("search_leads_or_page_text_active_evidence_eligibility_granted") is not False
        or receipt.get("active_forward_integration_authorized") is not False
        or receipt.get("benchmark_forward_or_evaluator_authorized") is not False
        or not _sealed(receipt, key="registered_receipt_sha256")
    ):
        raise ValueError("V2.42.49 registered receipt drifted")


def _registered_receipt(
    *,
    initial: Mapping[str, Any],
    claim: Mapping[str, Any],
    facade_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "registry_initial": _clone(dict(initial)),
        "registry_initial_sha256": initial["initial_sha256"],
        "action_claim": _clone(dict(claim)),
        "action_claim_sha256": claim["claim_sha256"],
        "facade_receipt": _clone(dict(facade_receipt)),
        "facade_receipt_sha256": facade_receipt["facade_receipt_sha256"],
        "facade_contract_sha256": initial["facade_contract_sha256"],
        "operation_kind": claim["operation_kind"],
        "durable_claim_before_facade_effect": True,
        "claim_prefix_replayed_from_store_when_receipt_validated": False,
        "raw_prompt_query_url_provider_value_or_projected_output_entered_receipt": False,
        "ephemeral_request_content_used_for_action_identity": False,
        "caller_supplied_action_ref_accepted": False,
        "equal_ephemeral_request_deduplication_implemented": False,
        "caller_single_registry_ownership_independently_verified": False,
        "direct_parent_facade_bypass_globally_excluded": False,
        "action_claim_order_equals_effect_completion_order_verified": False,
        "adapter_code_identity_independently_attested": False,
        "malicious_same_user_resealing_excluded": False,
        "search_leads_or_page_text_active_evidence_eligibility_granted": False,
        "active_forward_integration_authorized": False,
        "benchmark_forward_or_evaluator_authorized": False,
    }
    value["registered_receipt_sha256"] = object_sha256(value)
    validate_registered_facade_receipt(value)
    return value


class DurableCandidateActionRegistry:
    """Allocate content-free action refs and invoke one exact frozen facade."""

    def __init__(
        self,
        *,
        root: Path,
        facade: CandidateClientFacade,
        initial: Mapping[str, Any],
    ) -> None:
        self.root = _ordinary_directory(root, label="registry root")
        if type(facade) is not CandidateClientFacade:
            raise ValueError("V2.42.49 facade exact type is invalid")
        validate_candidate_client_facade_contract(facade._contract)
        frozen_initial = _clone(dict(initial))
        validate_durable_action_registry_initial(frozen_initial)
        if frozen_initial["facade_contract_sha256"] != facade._contract["contract_sha256"]:
            raise ValueError("V2.42.49 facade contract binding drifted")
        self._facade = facade
        self._facade_identity = id(facade)
        self._facade_contract_sha256 = facade._contract["contract_sha256"]
        self._initial = frozen_initial
        self.initial_path = self.root / INITIAL_FILE
        self.lock_path = self.root / LOCK_FILE
        self.claims_directory = self.root / CLAIMS_DIRECTORY

    @classmethod
    def initialize(
        cls,
        *,
        root: Path,
        facade: CandidateClientFacade,
    ) -> "DurableCandidateActionRegistry":
        registry_root = _ordinary_directory(root, label="registry root")
        if any(registry_root.iterdir()):
            raise FileExistsError("V2.42.49 registry root is not pristine")
        if type(facade) is not CandidateClientFacade:
            raise ValueError("V2.42.49 facade exact type is invalid")
        validate_candidate_client_facade_contract(facade._contract)
        initial = _derive_initial(
            facade_contract_sha256=facade._contract["contract_sha256"],
            nonce=secrets.token_bytes(32),
        )
        os.mkdir(registry_root / CLAIMS_DIRECTORY, 0o700)
        descriptor = os.open(
            registry_root / LOCK_FILE,
            os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
        )
        os.close(descriptor)
        _publish_new(registry_root / INITIAL_FILE, initial)
        _fsync_directory(registry_root)
        return cls(root=registry_root, facade=facade, initial=initial)

    @classmethod
    def open(
        cls,
        *,
        root: Path,
        facade: CandidateClientFacade,
    ) -> "DurableCandidateActionRegistry":
        registry_root = _ordinary_directory(root, label="registry root")
        initial = _read_object(registry_root / INITIAL_FILE)
        return cls(root=registry_root, facade=facade, initial=initial)

    def _require_layout(self) -> None:
        _ordinary_directory(self.root, label="registry root")
        _ordinary_directory(self.claims_directory, label="claims directory")
        expected = {self.initial_path, self.lock_path, self.claims_directory}
        if set(self.root.iterdir()) != expected:
            raise DurableActionRegistryPoisoned("V2.42.49 registry layout contains residue")
        initial = _read_object(self.initial_path)
        validate_durable_action_registry_initial(initial)
        if initial != self._initial:
            raise DurableActionRegistryPoisoned("V2.42.49 registry initial bytes drifted")

    @contextmanager
    def _locked(self) -> Iterator[None]:
        self._require_layout()
        try:
            descriptor = os.open(self.lock_path, os.O_RDWR | os.O_NOFOLLOW)
        except OSError as error:
            raise DurableActionRegistryPoisoned("V2.42.49 lock cannot be opened safely") from error
        try:
            metadata = os.fstat(descriptor)
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
                raise DurableActionRegistryPoisoned("V2.42.49 lock is nonordinary")
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            self._require_layout()
            yield
        finally:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
            finally:
                os.close(descriptor)

    def _scan_claims_locked(self) -> list[dict[str, Any]]:
        paths: dict[int, Path] = {}
        for path in self.claims_directory.iterdir():
            match = CLAIM_NAME.fullmatch(path.name)
            if match is None:
                raise DurableActionRegistryPoisoned("V2.42.49 claims directory contains residue")
            ordinal = int(match.group("ordinal"))
            if not 1 <= ordinal <= MAX_CLAIMS or ordinal in paths:
                raise DurableActionRegistryPoisoned("V2.42.49 claim filename is invalid")
            paths[ordinal] = path
        if sorted(paths) != list(range(1, len(paths) + 1)):
            raise DurableActionRegistryPoisoned("V2.42.49 claims are not contiguous")
        claims: list[dict[str, Any]] = []
        previous: str | None = None
        for ordinal in range(1, len(paths) + 1):
            claim = _read_object(paths[ordinal])
            _validate_claim(
                claim,
                initial=self._initial,
                expected_ordinal=ordinal,
                expected_previous_claim_sha256=previous,
            )
            claims.append(claim)
            previous = str(claim["claim_sha256"])
        return claims

    def load_claims(self) -> tuple[Mapping[str, Any], ...]:
        with self._locked():
            return tuple(_clone(claim) for claim in self._scan_claims_locked())

    def status(self) -> dict[str, Any]:
        with self._locked():
            claims = self._scan_claims_locked()
            return {
                "artifact_version": 1,
                "role": STATUS_ROLE,
                "policy_id": POLICY_ID,
                "registry_initial_sha256": self._initial["initial_sha256"],
                "facade_contract_sha256": self._initial["facade_contract_sha256"],
                "allocated_action_count": len(claims),
                "last_claim_sha256": None if not claims else claims[-1]["claim_sha256"],
                "clean_contiguous_prefix": True,
                "local_posix_advisory_lock_used": True,
                "ephemeral_request_content_read": False,
                "active_forward_integration_authorized": False,
                "benchmark_forward_or_evaluator_authorized": False,
            }

    def validate_receipt_against_registry(
        self, value: Mapping[str, Any]
    ) -> dict[str, Any]:
        """Replay the durable prefix and bind one receipt to its exact claim."""

        validate_registered_facade_receipt(value)
        receipt = dict(value)
        if receipt["registry_initial"] != self._initial:
            raise DurableActionRegistryPoisoned(
                "V2.42.49 receipt registry initial drifted"
            )
        claim = dict(receipt["action_claim"])
        ordinal = int(claim["action_ordinal"])
        with self._locked():
            claims = self._scan_claims_locked()
            if ordinal > len(claims) or claims[ordinal - 1] != claim:
                raise DurableActionRegistryPoisoned(
                    "V2.42.49 receipt claim is absent from durable prefix"
                )
            return {
                "artifact_version": 1,
                "role": "v24249_registered_facade_receipt_store_validation",
                "policy_id": POLICY_ID,
                "registry_initial_sha256": self._initial["initial_sha256"],
                "registered_receipt_sha256": receipt["registered_receipt_sha256"],
                "action_claim_sha256": claim["claim_sha256"],
                "action_ordinal": ordinal,
                "durable_claim_prefix_length": len(claims),
                "claim_prefix_replayed_from_store": True,
                "claim_exactly_present_in_durable_prefix": True,
                "ephemeral_request_content_read": False,
                "active_forward_integration_authorized": False,
                "benchmark_forward_or_evaluator_authorized": False,
            }

    def _require_facade_binding(self) -> None:
        if type(self._facade) is not CandidateClientFacade or id(self._facade) != self._facade_identity:
            raise DurableActionRegistryError("V2.42.49 facade identity drifted")
        try:
            validate_candidate_client_facade_contract(self._facade._contract)
        except (KeyError, TypeError, ValueError):
            raise DurableActionRegistryError("V2.42.49 facade contract drifted") from None
        if self._facade._contract["contract_sha256"] != self._facade_contract_sha256:
            raise DurableActionRegistryError("V2.42.49 facade contract binding drifted")

    def _claim(self, operation_kind: str) -> tuple[CandidateFacadeActionRef, dict[str, Any]]:
        if operation_kind not in OPERATION_KINDS:
            raise DurableActionRegistryError("V2.42.49 operation kind is invalid")
        self._require_facade_binding()
        with self._locked():
            claims = self._scan_claims_locked()
            ordinal = len(claims) + 1
            if ordinal > MAX_CLAIMS:
                raise DurableActionRegistryError("V2.42.49 action capacity exhausted")
            action = derive_candidate_facade_action_ref(
                task_scope_ref_sha256=self._initial["task_scope_ref_sha256"],
                stage_ref_sha256=self._initial["fixed_stage_refs"][operation_kind],
                operation_kind=operation_kind,
                action_ordinal=ordinal,
            )
            claim: dict[str, Any] = {
                "artifact_version": 1,
                "role": CLAIM_ROLE,
                "policy_id": POLICY_ID,
                "registry_initial_sha256": self._initial["initial_sha256"],
                "facade_contract_sha256": self._initial["facade_contract_sha256"],
                "task_scope_ref_sha256": self._initial["task_scope_ref_sha256"],
                "operation_kind": operation_kind,
                "stage_ref_sha256": self._initial["fixed_stage_refs"][operation_kind],
                "action_ordinal": ordinal,
                "previous_claim_sha256": None if not claims else claims[-1]["claim_sha256"],
                "action_ref": _action_mapping(action),
                "action_ref_sha256": action.action_ref_sha256,
                "global_monotonic_action_ordinal": True,
                "durable_claim_before_facade_effect": True,
                "file_and_directory_fsync_attempted": True,
                "ephemeral_request_content_used_for_action_identity": False,
                "caller_supplied_action_ref_accepted": False,
                "equal_ephemeral_request_deduplication_implemented": False,
                "active_forward_integration_authorized": False,
                "benchmark_forward_or_evaluator_authorized": False,
            }
            claim["claim_sha256"] = object_sha256(claim)
            _validate_claim(
                claim,
                initial=self._initial,
                expected_ordinal=ordinal,
                expected_previous_claim_sha256=claim["previous_claim_sha256"],
            )
            path = self.claims_directory / f"{ordinal:020d}.json"
            _publish_new(path, claim)
            return action, _clone(claim)

    def _result(
        self,
        *,
        claim: Mapping[str, Any],
        result: CandidateClientFacadeResult,
    ) -> DurableRegisteredFacadeResult:
        if type(result) is not CandidateClientFacadeResult:
            raise DurableActionRegistryError("V2.42.49 facade result type drifted")
        receipt = _registered_receipt(
            initial=self._initial,
            claim=claim,
            facade_receipt=result.receipt,
        )
        return DurableRegisteredFacadeResult(receipt=receipt, value=result.value)

    def run_model_json(
        self,
        *,
        system: str,
        user: str,
        max_output_tokens: int,
    ) -> DurableRegisteredFacadeResult:
        action, claim = self._claim("model_json")
        result = type(self._facade).run_model_json(
            self._facade,
            action_ref=action,
            system=system,
            user=user,
            max_output_tokens=max_output_tokens,
        )
        return self._result(claim=claim, result=result)

    def run_search_leads(
        self,
        *,
        query: str,
        max_results: int,
    ) -> DurableRegisteredFacadeResult:
        action, claim = self._claim("search_leads")
        result = type(self._facade).run_search_leads(
            self._facade,
            action_ref=action,
            query=query,
            max_results=max_results,
        )
        return self._result(claim=claim, result=result)

    def run_fetched_page(
        self,
        *,
        url: str,
    ) -> DurableRegisteredFacadeResult:
        action, claim = self._claim("fetched_page")
        result = type(self._facade).run_fetched_page(
            self._facade,
            action_ref=action,
            url=url,
        )
        return self._result(claim=claim, result=result)
