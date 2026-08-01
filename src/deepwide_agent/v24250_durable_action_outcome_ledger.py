"""Single-inflight durable success ledger above the V2.42.49 registry.

V2.42.49 durably allocates an action claim before invoking the candidate
facade, but a crash after that claim leaves no durable statement about the
effect outcome.  This isolated candidate adds a second local-POSIX ledger.  A
cooperative process holds one ``flock`` from the clean-prefix check through
claim allocation, facade execution, and create-exclusive success publication.
Consequently claim order and successful outcome order are identical inside one
ledger, and a later action cannot overtake an unresolved claim.

Only successful, fully validated content-free receipts are settled.  Any
exception, crash, partial outcome file, direct parent-registry claim, or other
claim/outcome mismatch permanently blocks automatic progress as uncertain.
The wrapper neither retries nor labels an unknown effect as failed.  It cannot
identify a repeated prompt/query/URL, prove that callers use only one ledger,
or globally prevent calls to the parent registry/facade.  Local advisory locks
and fsync do not prove NFS/distributed semantics, hardware durability, adapter
code identity, or protection from a malicious same-user writer.  No active
client, provider, benchmark, evaluator, or leaderboard authority is granted.
"""

from __future__ import annotations

import copy
import dataclasses
import fcntl
import json
import os
import re
import stat
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Mapping

from deepwide_agent.v24232_webswarm_total_budget import object_sha256
from deepwide_agent.v24248_candidate_client_facade import (
    CandidateClientFacade,
    CandidateClientFacadeResult,
    validate_candidate_client_facade_contract,
)
from deepwide_agent.v24249_durable_action_registry import (
    DurableCandidateActionRegistry,
    DurableRegisteredFacadeResult,
    validate_durable_action_registry_initial,
    validate_registered_facade_receipt,
)


POLICY_ID = "v24250_durable_action_outcome_ledger_v1"
INITIAL_ROLE = "v24250_durable_action_outcome_initial"
OUTCOME_ROLE = "v24250_durable_action_success_outcome"
STATUS_ROLE = "v24250_durable_action_outcome_status"

PRODUCTION_PACKAGE_AUTHORIZED = False
ACTIVE_FORWARD_INTEGRATION_AUTHORIZED = False
ACTIVE_PROVIDER_TRAFFIC_AUTHORIZED = False
EXTERNAL_SIDE_EFFECT_AUTHORIZED = False
BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED = False
DEV64_OR_EXACT220_LAUNCH_AUTHORIZED = False
SHARED_API_LEASE_ACQUIRE_AUTHORIZED = False
LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED = False

SINGLE_INFLIGHT_LOCAL_POSIX_EFFECT_IMPLEMENTED = True
DURABLE_CLAIM_BEFORE_EFFECT_IMPLEMENTED = True
DURABLE_SUCCESS_OUTCOME_AFTER_EFFECT_IMPLEMENTED = True
CLAIM_TO_SUCCESS_OUTCOME_DURABLE_BINDING_IMPLEMENTED = True
ACTION_CLAIM_ORDER_EQUALS_SUCCESS_OUTCOME_ORDER_VERIFIED = True
UNCERTAIN_CLAIM_QUARANTINE_IMPLEMENTED = True
AUTOMATIC_RETRY_OR_RESUME_IMPLEMENTED = False
FAILURE_OUTCOME_DURABLE_BINDING_IMPLEMENTED = False
CLAIMED_BUT_UNSTARTED_ACTION_RECOVERY_IMPLEMENTED = False
OUTCOME_PUBLICATION_CRASH_AUTOMATIC_RECOVERY_IMPLEMENTED = False
CALLER_SINGLE_LEDGER_OWNERSHIP_INDEPENDENTLY_VERIFIED = False
DIRECT_PARENT_REGISTRY_OR_FACADE_BYPASS_GLOBALLY_EXCLUDED = False
EQUAL_EPHEMERAL_REQUEST_DEDUPLICATION_IMPLEMENTED = False
EPHEMERAL_REQUEST_CONTENT_USED_FOR_OUTCOME_IDENTITY = False
ADAPTER_CODE_IDENTITY_INDEPENDENTLY_ATTESTED = False
MALICIOUS_SAME_USER_RESEALING_EXCLUDED = False
NETWORK_OR_DISTRIBUTED_FILESYSTEM_SEMANTICS_PROVEN = False
SEARCH_LEADS_OR_PAGE_TEXT_ACTIVE_EVIDENCE_ELIGIBILITY_GRANTED = False

INITIAL_FILE = "initial.json"
LOCK_FILE = "outcome.lock"
OUTCOMES_DIRECTORY = "outcomes"
OUTCOME_NAME = re.compile(r"^(?P<ordinal>[0-9]{20})\.json$")
MAX_FILE_BYTES = 32_000_000
MAX_OUTCOMES = 1_000_000

INITIAL_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "registry_initial",
        "registry_initial_sha256",
        "facade_contract_sha256",
        "single_inflight_local_posix_effect",
        "automatic_retry_or_resume_implemented",
        "failure_outcome_durable_binding_implemented",
        "caller_single_ledger_ownership_independently_verified",
        "direct_parent_registry_or_facade_bypass_globally_excluded",
        "ephemeral_request_content_used_for_outcome_identity",
        "adapter_code_identity_independently_attested",
        "malicious_same_user_resealing_excluded",
        "network_or_distributed_filesystem_semantics_proven",
        "active_forward_integration_authorized",
        "benchmark_forward_or_evaluator_authorized",
        "initial_sha256",
    }
)
OUTCOME_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "ledger_initial",
        "ledger_initial_sha256",
        "facade_contract_sha256",
        "action_ordinal",
        "operation_kind",
        "previous_outcome_sha256",
        "action_claim_sha256",
        "action_ref_sha256",
        "registered_facade_receipt",
        "registered_facade_receipt_sha256",
        "facade_receipt_sha256",
        "terminal_status",
        "single_inflight_lock_held_through_claim_effect_and_outcome_publish",
        "claim_to_success_outcome_durable_binding",
        "action_claim_order_equals_success_outcome_order",
        "file_and_directory_fsync_attempted",
        "raw_prompt_query_url_provider_value_or_projected_output_entered_outcome",
        "ephemeral_request_content_used_for_outcome_identity",
        "automatic_retry_or_resume_implemented",
        "failure_outcome_durable_binding_implemented",
        "caller_single_ledger_ownership_independently_verified",
        "direct_parent_registry_or_facade_bypass_globally_excluded",
        "equal_ephemeral_request_deduplication_implemented",
        "adapter_code_identity_independently_attested",
        "malicious_same_user_resealing_excluded",
        "search_leads_or_page_text_active_evidence_eligibility_granted",
        "active_forward_integration_authorized",
        "benchmark_forward_or_evaluator_authorized",
        "outcome_sha256",
    }
)


class DurableActionOutcomeError(RuntimeError):
    """Sanitized outcome-ledger error without request or provider content."""


class DurableActionOutcomePoisoned(DurableActionOutcomeError):
    """Malformed, partial, or ambiguous durable state blocks progress."""


class DurableActionOutcomeQuarantined(DurableActionOutcomeError):
    """A durable claim lacks a durable success outcome; retry is forbidden."""


@dataclasses.dataclass(frozen=True)
class DurableOutcomeBoundFacadeResult:
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
        raise DurableActionOutcomePoisoned(f"V2.42.50 {label} schema drifted")
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
            raise DurableActionOutcomePoisoned("V2.42.50 duplicate JSON key rejected")
        value[key] = item
    return value


def _reject_constant(value: str) -> None:
    raise DurableActionOutcomePoisoned("V2.42.50 non-finite JSON constant rejected")


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
        raise ValueError(f"V2.42.50 {label} is absent") from error
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or path.is_symlink()
        or path.resolve(strict=True) != candidate
    ):
        raise ValueError(f"V2.42.50 {label} is not an ordinary directory")
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
        raise DurableActionOutcomePoisoned("V2.42.50 required file is absent") from error
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_nlink != 1
        or metadata.st_size > MAX_FILE_BYTES
    ):
        raise DurableActionOutcomePoisoned("V2.42.50 durable file is nonordinary")
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
            raise DurableActionOutcomePoisoned("V2.42.50 durable file changed during open")
        while len(payload) <= MAX_FILE_BYTES:
            chunk = os.read(descriptor, min(65_536, MAX_FILE_BYTES + 1 - len(payload)))
            if not chunk:
                break
            payload.extend(chunk)
        if len(payload) > MAX_FILE_BYTES or os.read(descriptor, 1):
            raise DurableActionOutcomePoisoned("V2.42.50 durable file exceeds size cap")
        final = os.fstat(descriptor)
        if (
            final.st_dev != opened.st_dev
            or final.st_ino != opened.st_ino
            or final.st_size != opened.st_size
            or final.st_mtime_ns != opened.st_mtime_ns
            or final.st_ctime_ns != opened.st_ctime_ns
        ):
            raise DurableActionOutcomePoisoned("V2.42.50 durable file changed during read")
    finally:
        os.close(descriptor)
    try:
        value = json.loads(
            bytes(payload).decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise DurableActionOutcomePoisoned("V2.42.50 durable JSON is invalid") from error
    if not isinstance(value, dict):
        raise DurableActionOutcomePoisoned("V2.42.50 durable value is not an object")
    return value


def _build_initial(registry_initial: Mapping[str, Any]) -> dict[str, Any]:
    frozen = _clone(dict(registry_initial))
    validate_durable_action_registry_initial(frozen)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": INITIAL_ROLE,
        "policy_id": POLICY_ID,
        "registry_initial": frozen,
        "registry_initial_sha256": frozen["initial_sha256"],
        "facade_contract_sha256": frozen["facade_contract_sha256"],
        "single_inflight_local_posix_effect": True,
        "automatic_retry_or_resume_implemented": False,
        "failure_outcome_durable_binding_implemented": False,
        "caller_single_ledger_ownership_independently_verified": False,
        "direct_parent_registry_or_facade_bypass_globally_excluded": False,
        "ephemeral_request_content_used_for_outcome_identity": False,
        "adapter_code_identity_independently_attested": False,
        "malicious_same_user_resealing_excluded": False,
        "network_or_distributed_filesystem_semantics_proven": False,
        "active_forward_integration_authorized": False,
        "benchmark_forward_or_evaluator_authorized": False,
    }
    value["initial_sha256"] = object_sha256(value)
    return value


def validate_durable_action_outcome_initial(value: Mapping[str, Any]) -> None:
    initial = _exact(value, keys=INITIAL_KEYS, label="initial record")
    registry = initial.get("registry_initial")
    if not isinstance(registry, Mapping):
        raise DurableActionOutcomePoisoned("V2.42.50 registry initial is invalid")
    try:
        validate_durable_action_registry_initial(registry)
    except (KeyError, TypeError, ValueError, RuntimeError):
        raise DurableActionOutcomePoisoned("V2.42.50 registry initial drifted") from None
    if (
        initial.get("artifact_version") != 1
        or initial.get("role") != INITIAL_ROLE
        or initial.get("policy_id") != POLICY_ID
        or initial.get("registry_initial_sha256") != registry.get("initial_sha256")
        or initial.get("facade_contract_sha256") != registry.get("facade_contract_sha256")
        or initial.get("single_inflight_local_posix_effect") is not True
        or initial.get("automatic_retry_or_resume_implemented") is not False
        or initial.get("failure_outcome_durable_binding_implemented") is not False
        or initial.get("caller_single_ledger_ownership_independently_verified") is not False
        or initial.get("direct_parent_registry_or_facade_bypass_globally_excluded") is not False
        or initial.get("ephemeral_request_content_used_for_outcome_identity") is not False
        or initial.get("adapter_code_identity_independently_attested") is not False
        or initial.get("malicious_same_user_resealing_excluded") is not False
        or initial.get("network_or_distributed_filesystem_semantics_proven") is not False
        or initial.get("active_forward_integration_authorized") is not False
        or initial.get("benchmark_forward_or_evaluator_authorized") is not False
        or not _sealed(initial, key="initial_sha256")
    ):
        raise DurableActionOutcomePoisoned("V2.42.50 initial record drifted")


def validate_durable_action_success_outcome(value: Mapping[str, Any]) -> None:
    outcome = _exact(value, keys=OUTCOME_KEYS, label="success outcome")
    initial = outcome.get("ledger_initial")
    registered = outcome.get("registered_facade_receipt")
    if not isinstance(initial, Mapping) or not isinstance(registered, Mapping):
        raise ValueError("V2.42.50 success outcome drifted")
    try:
        validate_durable_action_outcome_initial(initial)
        validate_registered_facade_receipt(registered)
    except (KeyError, TypeError, ValueError, RuntimeError):
        raise ValueError("V2.42.50 success outcome drifted") from None
    claim = registered["action_claim"]
    ordinal = outcome.get("action_ordinal")
    previous = outcome.get("previous_outcome_sha256")
    if (
        not isinstance(ordinal, int)
        or isinstance(ordinal, bool)
        or not 1 <= ordinal <= MAX_OUTCOMES
        or (ordinal == 1 and previous is not None)
        or (ordinal > 1 and not _is_sha256(previous))
        or outcome.get("artifact_version") != 1
        or outcome.get("role") != OUTCOME_ROLE
        or outcome.get("policy_id") != POLICY_ID
        or outcome.get("ledger_initial_sha256") != initial.get("initial_sha256")
        or outcome.get("facade_contract_sha256") != initial.get("facade_contract_sha256")
        or outcome.get("facade_contract_sha256") != registered.get("facade_contract_sha256")
        or outcome.get("action_ordinal") != claim.get("action_ordinal")
        or outcome.get("operation_kind") != claim.get("operation_kind")
        or outcome.get("action_claim_sha256") != claim.get("claim_sha256")
        or outcome.get("action_ref_sha256") != claim.get("action_ref_sha256")
        or outcome.get("registered_facade_receipt_sha256") != registered.get("registered_receipt_sha256")
        or outcome.get("facade_receipt_sha256") != registered.get("facade_receipt_sha256")
        or outcome.get("terminal_status") != "success"
        or outcome.get("single_inflight_lock_held_through_claim_effect_and_outcome_publish") is not True
        or outcome.get("claim_to_success_outcome_durable_binding") is not True
        or outcome.get("action_claim_order_equals_success_outcome_order") is not True
        or outcome.get("file_and_directory_fsync_attempted") is not True
        or outcome.get("raw_prompt_query_url_provider_value_or_projected_output_entered_outcome") is not False
        or outcome.get("ephemeral_request_content_used_for_outcome_identity") is not False
        or outcome.get("automatic_retry_or_resume_implemented") is not False
        or outcome.get("failure_outcome_durable_binding_implemented") is not False
        or outcome.get("caller_single_ledger_ownership_independently_verified") is not False
        or outcome.get("direct_parent_registry_or_facade_bypass_globally_excluded") is not False
        or outcome.get("equal_ephemeral_request_deduplication_implemented") is not False
        or outcome.get("adapter_code_identity_independently_attested") is not False
        or outcome.get("malicious_same_user_resealing_excluded") is not False
        or outcome.get("search_leads_or_page_text_active_evidence_eligibility_granted") is not False
        or outcome.get("active_forward_integration_authorized") is not False
        or outcome.get("benchmark_forward_or_evaluator_authorized") is not False
        or not _sealed(outcome, key="outcome_sha256")
    ):
        raise ValueError("V2.42.50 success outcome drifted")


def _build_success_outcome(
    *,
    initial: Mapping[str, Any],
    registered: Mapping[str, Any],
    previous_outcome_sha256: str | None,
) -> dict[str, Any]:
    frozen = _clone(dict(registered))
    validate_registered_facade_receipt(frozen)
    claim = frozen["action_claim"]
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": OUTCOME_ROLE,
        "policy_id": POLICY_ID,
        "ledger_initial": _clone(dict(initial)),
        "ledger_initial_sha256": initial["initial_sha256"],
        "facade_contract_sha256": initial["facade_contract_sha256"],
        "action_ordinal": claim["action_ordinal"],
        "operation_kind": claim["operation_kind"],
        "previous_outcome_sha256": previous_outcome_sha256,
        "action_claim_sha256": claim["claim_sha256"],
        "action_ref_sha256": claim["action_ref_sha256"],
        "registered_facade_receipt": frozen,
        "registered_facade_receipt_sha256": frozen["registered_receipt_sha256"],
        "facade_receipt_sha256": frozen["facade_receipt_sha256"],
        "terminal_status": "success",
        "single_inflight_lock_held_through_claim_effect_and_outcome_publish": True,
        "claim_to_success_outcome_durable_binding": True,
        "action_claim_order_equals_success_outcome_order": True,
        "file_and_directory_fsync_attempted": True,
        "raw_prompt_query_url_provider_value_or_projected_output_entered_outcome": False,
        "ephemeral_request_content_used_for_outcome_identity": False,
        "automatic_retry_or_resume_implemented": False,
        "failure_outcome_durable_binding_implemented": False,
        "caller_single_ledger_ownership_independently_verified": False,
        "direct_parent_registry_or_facade_bypass_globally_excluded": False,
        "equal_ephemeral_request_deduplication_implemented": False,
        "adapter_code_identity_independently_attested": False,
        "malicious_same_user_resealing_excluded": False,
        "search_leads_or_page_text_active_evidence_eligibility_granted": False,
        "active_forward_integration_authorized": False,
        "benchmark_forward_or_evaluator_authorized": False,
    }
    value["outcome_sha256"] = object_sha256(value)
    validate_durable_action_success_outcome(value)
    return value


class DurableActionOutcomeLedger:
    """Serialize one registry and durably settle validated success receipts."""

    def __init__(
        self,
        *,
        root: Path,
        registry: DurableCandidateActionRegistry,
        initial: Mapping[str, Any],
    ) -> None:
        self.root = _ordinary_directory(root, label="outcome root")
        if type(registry) is not DurableCandidateActionRegistry:
            raise ValueError("V2.42.50 registry exact type is invalid")
        frozen = _clone(dict(initial))
        validate_durable_action_outcome_initial(frozen)
        if frozen["registry_initial"] != registry._initial:
            raise ValueError("V2.42.50 registry initial binding drifted")
        registry._require_facade_binding()
        if (
            self.root == registry.root
            or self.root.is_relative_to(registry.root)
            or registry.root.is_relative_to(self.root)
        ):
            raise ValueError("V2.42.50 outcome and registry roots overlap")
        self._registry = registry
        self._registry_identity = id(registry)
        self._registry_root = registry.root
        self._facade_identity = id(registry._facade)
        self._initial = frozen
        self.initial_path = self.root / INITIAL_FILE
        self.lock_path = self.root / LOCK_FILE
        self.outcomes_directory = self.root / OUTCOMES_DIRECTORY

    @classmethod
    def initialize(
        cls,
        *,
        root: Path,
        registry: DurableCandidateActionRegistry,
    ) -> "DurableActionOutcomeLedger":
        outcome_root = _ordinary_directory(root, label="outcome root")
        if type(registry) is not DurableCandidateActionRegistry:
            raise ValueError("V2.42.50 registry exact type is invalid")
        registry._require_facade_binding()
        if registry.status()["allocated_action_count"] != 0:
            raise ValueError("V2.42.50 registry is not pristine at initialization")
        if (
            outcome_root == registry.root
            or outcome_root.is_relative_to(registry.root)
            or registry.root.is_relative_to(outcome_root)
        ):
            raise ValueError("V2.42.50 outcome and registry roots overlap")
        if any(outcome_root.iterdir()):
            raise FileExistsError("V2.42.50 outcome root is not pristine")
        initial = _build_initial(registry._initial)
        os.mkdir(outcome_root / OUTCOMES_DIRECTORY, 0o700)
        descriptor = os.open(
            outcome_root / LOCK_FILE,
            os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
        )
        os.close(descriptor)
        _publish_new(outcome_root / INITIAL_FILE, initial)
        _fsync_directory(outcome_root)
        return cls(root=outcome_root, registry=registry, initial=initial)

    @classmethod
    def open(
        cls,
        *,
        root: Path,
        registry: DurableCandidateActionRegistry,
    ) -> "DurableActionOutcomeLedger":
        outcome_root = _ordinary_directory(root, label="outcome root")
        initial = _read_object(outcome_root / INITIAL_FILE)
        return cls(root=outcome_root, registry=registry, initial=initial)

    def _require_layout(self) -> None:
        _ordinary_directory(self.root, label="outcome root")
        _ordinary_directory(self.outcomes_directory, label="outcomes directory")
        expected = {self.initial_path, self.lock_path, self.outcomes_directory}
        if set(self.root.iterdir()) != expected:
            raise DurableActionOutcomePoisoned("V2.42.50 outcome layout contains residue")
        initial = _read_object(self.initial_path)
        validate_durable_action_outcome_initial(initial)
        if initial != self._initial:
            raise DurableActionOutcomePoisoned("V2.42.50 outcome initial bytes drifted")

    def _require_registry_binding(self) -> None:
        if (
            type(self._registry) is not DurableCandidateActionRegistry
            or id(self._registry) != self._registry_identity
            or self._registry.root != self._registry_root
            or id(self._registry._facade) != self._facade_identity
            or self._registry._initial != self._initial["registry_initial"]
        ):
            raise DurableActionOutcomeError("V2.42.50 registry binding drifted")
        try:
            self._registry._require_facade_binding()
        except (KeyError, TypeError, ValueError, RuntimeError):
            raise DurableActionOutcomeError(
                "V2.42.50 parent registry or facade binding drifted"
            ) from None

    @contextmanager
    def _locked(self) -> Iterator[None]:
        self._require_layout()
        try:
            descriptor = os.open(self.lock_path, os.O_RDWR | os.O_NOFOLLOW)
        except OSError as error:
            raise DurableActionOutcomePoisoned("V2.42.50 lock cannot be opened safely") from error
        try:
            metadata = os.fstat(descriptor)
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
                raise DurableActionOutcomePoisoned("V2.42.50 lock is nonordinary")
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            self._require_layout()
            yield
        finally:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
            finally:
                os.close(descriptor)

    def _scan_outcomes_locked(self) -> list[dict[str, Any]]:
        paths: dict[int, Path] = {}
        for path in self.outcomes_directory.iterdir():
            match = OUTCOME_NAME.fullmatch(path.name)
            if match is None:
                raise DurableActionOutcomePoisoned("V2.42.50 outcomes directory contains residue")
            ordinal = int(match.group("ordinal"))
            if not 1 <= ordinal <= MAX_OUTCOMES or ordinal in paths:
                raise DurableActionOutcomePoisoned("V2.42.50 outcome filename is invalid")
            paths[ordinal] = path
        if sorted(paths) != list(range(1, len(paths) + 1)):
            raise DurableActionOutcomePoisoned("V2.42.50 outcomes are not contiguous")
        outcomes: list[dict[str, Any]] = []
        previous: str | None = None
        for ordinal in range(1, len(paths) + 1):
            outcome = _read_object(paths[ordinal])
            try:
                validate_durable_action_success_outcome(outcome)
            except ValueError:
                raise DurableActionOutcomePoisoned("V2.42.50 outcome replay failed") from None
            if (
                outcome["ledger_initial"] != self._initial
                or outcome["action_ordinal"] != ordinal
                or outcome["previous_outcome_sha256"] != previous
            ):
                raise DurableActionOutcomePoisoned("V2.42.50 outcome prefix drifted")
            outcomes.append(outcome)
            previous = str(outcome["outcome_sha256"])
        return outcomes

    def _snapshot_locked(self) -> tuple[list[Mapping[str, Any]], list[dict[str, Any]]]:
        self._require_registry_binding()
        claims = list(self._registry.load_claims())
        outcomes = self._scan_outcomes_locked()
        if len(outcomes) > len(claims):
            raise DurableActionOutcomePoisoned("V2.42.50 outcomes exceed claims")
        for index, outcome in enumerate(outcomes):
            if outcome["action_claim_sha256"] != claims[index]["claim_sha256"]:
                raise DurableActionOutcomePoisoned("V2.42.50 claim/outcome prefix drifted")
        if len(claims) != len(outcomes):
            raise DurableActionOutcomeQuarantined(
                "V2.42.50 unresolved durable action claim forbids automatic progress"
            )
        return claims, outcomes

    def load_outcomes(self) -> tuple[Mapping[str, Any], ...]:
        with self._locked():
            _, outcomes = self._snapshot_locked()
            return tuple(_clone(outcome) for outcome in outcomes)

    def status(self) -> dict[str, Any]:
        self._require_registry_binding()
        with self._locked():
            claims = list(self._registry.load_claims())
            outcomes = self._scan_outcomes_locked()
            prefix_matches = len(outcomes) <= len(claims) and all(
                outcome["action_claim_sha256"] == claims[index]["claim_sha256"]
                for index, outcome in enumerate(outcomes)
            )
            if not prefix_matches or len(outcomes) > len(claims):
                raise DurableActionOutcomePoisoned("V2.42.50 status prefix drifted")
            unresolved = len(claims) - len(outcomes)
            return {
                "artifact_version": 1,
                "role": STATUS_ROLE,
                "policy_id": POLICY_ID,
                "ledger_initial_sha256": self._initial["initial_sha256"],
                "registry_claim_count": len(claims),
                "durable_success_outcome_count": len(outcomes),
                "unresolved_claim_count": unresolved,
                "state": "clean" if unresolved == 0 else "quarantined_uncertain_effect",
                "automatic_retry_or_resume_allowed": False,
                "single_inflight_local_posix_effect": True,
                "clean_contiguous_success_prefix": True,
                "ephemeral_request_content_read": False,
                "active_forward_integration_authorized": False,
                "benchmark_forward_or_evaluator_authorized": False,
            }

    def validate_outcome_against_ledger(self, value: Mapping[str, Any]) -> dict[str, Any]:
        validate_durable_action_success_outcome(value)
        outcome = dict(value)
        if outcome["ledger_initial"] != self._initial:
            raise DurableActionOutcomePoisoned("V2.42.50 outcome ledger initial drifted")
        ordinal = int(outcome["action_ordinal"])
        with self._locked():
            _, outcomes = self._snapshot_locked()
            if ordinal > len(outcomes) or outcomes[ordinal - 1] != outcome:
                raise DurableActionOutcomePoisoned("V2.42.50 outcome is absent from durable prefix")
            return {
                "artifact_version": 1,
                "role": "v24250_durable_action_outcome_store_validation",
                "policy_id": POLICY_ID,
                "ledger_initial_sha256": self._initial["initial_sha256"],
                "outcome_sha256": outcome["outcome_sha256"],
                "action_claim_sha256": outcome["action_claim_sha256"],
                "action_ordinal": ordinal,
                "durable_success_prefix_length": len(outcomes),
                "outcome_exactly_present_in_durable_prefix": True,
                "claim_to_success_outcome_durable_binding_replayed": True,
                "ephemeral_request_content_read": False,
                "active_forward_integration_authorized": False,
                "benchmark_forward_or_evaluator_authorized": False,
            }

    def _settle_success_locked(
        self,
        *,
        registered: DurableRegisteredFacadeResult,
        outcomes: list[dict[str, Any]],
    ) -> DurableOutcomeBoundFacadeResult:
        if type(registered) is not DurableRegisteredFacadeResult:
            raise DurableActionOutcomeError("V2.42.50 registered result type drifted")
        self._registry.validate_receipt_against_registry(registered.receipt)
        ordinal = len(outcomes) + 1
        if registered.receipt["action_claim"]["action_ordinal"] != ordinal:
            raise DurableActionOutcomePoisoned("V2.42.50 settled ordinal drifted")
        outcome = _build_success_outcome(
            initial=self._initial,
            registered=registered.receipt,
            previous_outcome_sha256=(
                None if not outcomes else outcomes[-1]["outcome_sha256"]
            ),
        )
        _publish_new(
            self.outcomes_directory / f"{ordinal:020d}.json",
            outcome,
        )
        return DurableOutcomeBoundFacadeResult(
            receipt=outcome,
            value=registered.value,
        )

    def _claim_locked(self, operation_kind: str):
        claims, outcomes = self._snapshot_locked()
        action, claim = self._registry._claim(operation_kind)
        if (
            len(claims) != len(outcomes)
            or claim["action_ordinal"] != len(outcomes) + 1
            or (
                claim["previous_claim_sha256"]
                != (None if not claims else claims[-1]["claim_sha256"])
            )
        ):
            raise DurableActionOutcomePoisoned("V2.42.50 newly allocated claim drifted")
        return action, claim, outcomes

    def run_model_json(
        self,
        *,
        system: str,
        user: str,
        max_output_tokens: int,
    ) -> DurableOutcomeBoundFacadeResult:
        with self._locked():
            action, claim, outcomes = self._claim_locked("model_json")
            facade_result: CandidateClientFacadeResult = type(
                self._registry._facade
            ).run_model_json(
                self._registry._facade,
                action_ref=action,
                system=system,
                user=user,
                max_output_tokens=max_output_tokens,
            )
            registered = self._registry._result(claim=claim, result=facade_result)
            return self._settle_success_locked(registered=registered, outcomes=outcomes)

    def run_search_leads(
        self,
        *,
        query: str,
        max_results: int,
    ) -> DurableOutcomeBoundFacadeResult:
        with self._locked():
            action, claim, outcomes = self._claim_locked("search_leads")
            facade_result: CandidateClientFacadeResult = type(
                self._registry._facade
            ).run_search_leads(
                self._registry._facade,
                action_ref=action,
                query=query,
                max_results=max_results,
            )
            registered = self._registry._result(claim=claim, result=facade_result)
            return self._settle_success_locked(registered=registered, outcomes=outcomes)

    def run_fetched_page(
        self,
        *,
        url: str,
    ) -> DurableOutcomeBoundFacadeResult:
        with self._locked():
            action, claim, outcomes = self._claim_locked("fetched_page")
            facade_result: CandidateClientFacadeResult = type(
                self._registry._facade
            ).run_fetched_page(
                self._registry._facade,
                action_ref=action,
                url=url,
            )
            registered = self._registry._result(claim=claim, result=facade_result)
            return self._settle_success_locked(registered=registered, outcomes=outcomes)
