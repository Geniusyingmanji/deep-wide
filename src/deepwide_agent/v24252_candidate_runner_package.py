"""Restartable, source-bound package for the isolated candidate runner chain.

V2.42.51 supplies runner-shaped clients, but constructing its V2.42.31--51
parents still required test-only manual wiring.  This module freezes that
wiring below one pristine local-POSIX package root.  Initialization publishes
a create-exclusive package reservation, creates distinct journal, registry,
and outcome stores, and publishes a ready receipt only after every parent can
be replayed.  Opening a package reconstructs the exact chain and preserves the
durable global action ordinal.

The package contract binds a byte-exact manifest of the candidate source
closure, all guidance/budget/facade contracts, parser/projection settings,
provider endpoint/model choices, and resource limits.  The manifest and
receipts are revalidated before every exposed runner operation.  Provider
credentials and transport callables are supplied only as ephemeral runtime
objects: they are never added to a canonical object, hashed, persisted, or
emitted.  Omitting a transport bundle selects the adapters' hardened default
transports; tests must inject a bundle explicitly.

This remains a build-only candidate.  It is not imported by active clients,
runtime, runner, launcher, benchmark, or evaluator code.  It grants no real
traffic, shared-lease, dev64, exact-220, evaluator, submission, or SOTA
authority.  Unkeyed receipts do not exclude a malicious same-user reseal, and
local flock/fsync semantics do not prove network-filesystem or hardware-stable
durability.
"""

from __future__ import annotations

import copy
import dataclasses
import hashlib
import json
import os
import stat
import time
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from deepwide_agent.v24231_webswarm_guidance_baseline import (
    reject_privileged_metadata,
    validate_guidance_arm,
    validate_guidance_policy,
    validate_scout_process_trace,
    validate_sibling_process_experience,
    validate_web_probe_receipt,
)
from deepwide_agent.v24232_webswarm_total_budget import (
    object_sha256,
    validate_shared_total_budget_contract,
)
from deepwide_agent.v24233_webswarm_effect_preauthorization import (
    validate_effect_preauthorization_state,
)
from deepwide_agent.v24236_azure_responses_single_attempt import (
    ALLOWED_ENDPOINT as MODEL_ENDPOINT,
    ALLOWED_MODEL as MODEL_NAME,
    AzureResponsesSingleAttemptAdapter,
)
from deepwide_agent.v24237_tavily_search_single_attempt import (
    ALLOWED_ENDPOINT as TAVILY_ENDPOINT,
    TavilySearchSingleAttemptAdapter,
)
from deepwide_agent.v24239_azure_hosted_search_single_attempt import (
    ALLOWED_ENDPOINT as AZURE_SEARCH_ENDPOINT,
    ALLOWED_MODEL as AZURE_SEARCH_MODEL,
    AzureHostedSearchSingleAttemptAdapter,
)
from deepwide_agent.v24240_anthropic_server_search_single_attempt import (
    ALLOWED_ANTHROPIC_VERSION,
    ALLOWED_ENDPOINT as ANTHROPIC_ENDPOINT,
    ALLOWED_MODEL as ANTHROPIC_MODEL,
    AnthropicServerSearchSingleAttemptAdapter,
)
from deepwide_agent.v24242_durable_effect_coordinator import (
    DurablePreauthorizedEffectCoordinator,
)
from deepwide_agent.v24243_retry_deadline_scheduler import (
    RetryDeadlineEffectScheduler,
)
from deepwide_agent.v24245_pinned_native_http_fetch import (
    PinnedNativeHttpFetchAdapter,
)
from deepwide_agent.v24247_candidate_runtime_assembly import (
    CandidateRuntimeAssembly,
)
from deepwide_agent.v24248_candidate_client_facade import (
    CandidateClientFacade,
    validate_candidate_client_facade_contract,
)
from deepwide_agent.v24249_durable_action_registry import (
    DurableCandidateActionRegistry,
)
from deepwide_agent.v24250_durable_action_outcome_ledger import (
    DurableActionOutcomeLedger,
)
from deepwide_agent.v24251_runner_compatible_evidence_bridge import (
    RunnerCompatibleModelClient,
    RunnerCompatibleSearchClient,
)


POLICY_ID = "v24252_candidate_runner_package_v1"
SOURCE_MANIFEST_ROLE = "v24252_candidate_runner_source_manifest"
CONTRACT_ROLE = "v24252_candidate_runner_package_contract"
INITIAL_ROLE = "v24252_candidate_runner_package_initial"
READY_ROLE = "v24252_candidate_runner_package_ready"
STATUS_ROLE = "v24252_candidate_runner_package_status"

PRODUCTION_PACKAGE_AUTHORIZED = False
ACTIVE_FORWARD_INTEGRATION_AUTHORIZED = False
ACTIVE_PROVIDER_TRAFFIC_AUTHORIZED = False
EXTERNAL_SIDE_EFFECT_AUTHORIZED = False
BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED = False
DEV64_OR_EXACT220_LAUNCH_AUTHORIZED = False
SHARED_API_LEASE_ACQUIRE_AUTHORIZED = False
LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED = False

PRISTINE_SINGLE_PACKAGE_ROOT_IMPLEMENTED = True
CREATE_EXCLUSIVE_INITIAL_AND_READY_RECEIPTS_IMPLEMENTED = True
RESTARTABLE_PARENT_RECONSTRUCTION_IMPLEMENTED = True
SOURCE_MANIFEST_REVALIDATED_BEFORE_EACH_RUNNER_OPERATION = True
INTRA_OPERATION_SOURCE_TO_EFFECT_ATOMICITY_PROVEN = False
GLOBAL_DURABLE_ACTION_ORDINAL_CONTINUES_AFTER_RESTART = True
EPHEMERAL_CREDENTIAL_RUNTIME_ARGUMENTS_IMPLEMENTED = True
CREDENTIAL_PERSISTED_HASHED_OR_EMITTED = False
CREDENTIAL_RETAINED_IN_ADAPTER_MEMORY = True
DEFAULT_HARDENED_REAL_TRANSPORT_CONSTRUCTION_IMPLEMENTED = True
EXPLICIT_FAKE_TRANSPORT_INJECTION_IMPLEMENTED = True
UNRESOLVED_OUTCOME_AUTOMATIC_RETRY_OR_RESUME_IMPLEMENTED = False
LOADED_CODE_IDENTITY_INDEPENDENTLY_ATTESTED = False
DIRECT_PARENT_CHAIN_BYPASS_GLOBALLY_EXCLUDED = False
MALICIOUS_SAME_USER_RESEALING_EXCLUDED = False
NETWORK_OR_DISTRIBUTED_FILESYSTEM_SEMANTICS_PROVEN = False

INITIAL_FILE = "package.initial.json"
READY_FILE = "package.ready.json"
JOURNAL_DIRECTORY = "journal"
REGISTRY_DIRECTORY = "registry"
OUTCOME_DIRECTORY = "outcome"
MAX_PACKAGE_FILE_BYTES = 64_000_000
MAX_SOURCE_FILE_BYTES = 8_000_000
MAX_SOURCE_TOTAL_BYTES = 96_000_000

SOURCE_RELATIVE_PATHS = tuple(
    f"deepwide_agent/v242{version}_{name}.py"
    for version, name in (
        (31, "webswarm_guidance_baseline"),
        (32, "webswarm_total_budget"),
        (33, "webswarm_effect_preauthorization"),
        (34, "provider_cost_meter"),
        (35, "preauthorized_effect_harness"),
        (36, "azure_responses_single_attempt"),
        (37, "tavily_search_single_attempt"),
        (38, "native_http_fetch_single_attempt"),
        (39, "azure_hosted_search_single_attempt"),
        (40, "anthropic_server_search_single_attempt"),
        (41, "durable_preauthorization_journal"),
        (42, "durable_effect_coordinator"),
        (43, "retry_deadline_scheduler"),
        (44, "strict_json_parser_boundary"),
        (45, "pinned_native_http_fetch"),
        (46, "search_page_projection"),
        (47, "candidate_runtime_assembly"),
        (48, "candidate_client_facade"),
        (49, "durable_action_registry"),
        (50, "durable_action_outcome_ledger"),
        (51, "runner_compatible_evidence_bridge"),
        (52, "candidate_runner_package"),
    )
)
LOADED_SOURCE_ROOT = Path(__file__).resolve().parents[1]

SOURCE_FILE_KEYS = frozenset({"path", "size_bytes", "sha256"})
SOURCE_MANIFEST_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "files",
        "file_count",
        "total_bytes",
        "ordinary_regular_single_link_files",
        "source_manifest_sha256",
    }
)
PROVIDER_CONFIGURATION_KEYS = frozenset(
    {
        "model_endpoint",
        "model_name",
        "search_provider_kind",
        "search_endpoint",
        "search_model",
        "search_api_version",
        "fetch_adapter_kind",
        "model_timeout_seconds",
        "search_timeout_seconds",
        "fetch_timeout_seconds",
        "model_max_attempts",
        "search_max_attempts",
        "fetch_max_attempts",
        "model_maximum_prompt_utf8_bytes",
        "model_maximum_output_tokens",
        "search_maximum_query_utf8_bytes",
        "search_maximum_output_tokens",
        "search_maximum_provider_tool_calls_per_attempt",
        "search_maximum_results",
        "fetch_maximum_response_bytes",
        "model_parser_contract_sha256",
        "search_page_projection_contract_sha256",
    }
)
CONTRACT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "candidate_package",
        "source_manifest",
        "source_manifest_sha256",
        "guidance_contract_sha256",
        "guidance_policy_sha256",
        "guidance_arm_name",
        "guidance_arm_sha256",
        "scout_trace_sha256s",
        "probe_receipt_sha256",
        "experience_sha256",
        "pristine_initial_state_sha256",
        "journal_namespace_sha256",
        "facade_contract",
        "facade_contract_sha256",
        "provider_configuration",
        "package_layout",
        "credentials_are_ephemeral_runtime_arguments",
        "credential_persisted_hashed_or_emitted",
        "credential_retained_in_adapter_memory",
        "default_hardened_real_transports_supported",
        "explicit_fake_transport_bundle_supported",
        "source_manifest_revalidated_before_each_runner_operation",
        "intra_operation_source_to_effect_atomicity_proven",
        "loaded_code_identity_independently_attested",
        "direct_parent_chain_bypass_globally_excluded",
        "malicious_same_user_resealing_excluded",
        "network_or_distributed_filesystem_semantics_proven",
        "label_blind_runtime",
        "benchmark_or_evaluator_metadata_used_for_routing",
        "active_provider_traffic_authorized",
        "active_forward_integration_authorized",
        "benchmark_forward_or_evaluator_authorized",
        "dev64_or_exact220_launch_authorized",
        "package_contract_sha256",
    }
)
INITIAL_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "package_contract",
        "package_contract_sha256",
        "package_initial_published_create_exclusive",
        "substores_pristine_before_initialization",
        "credential_persisted_hashed_or_emitted",
        "active_provider_traffic_authorized",
        "active_forward_integration_authorized",
        "benchmark_forward_or_evaluator_authorized",
        "package_initial_sha256",
    }
)
READY_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "package_contract_sha256",
        "package_initial_sha256",
        "source_manifest_sha256",
        "journal_initial_sha256",
        "registry_initial_sha256",
        "outcome_initial_sha256",
        "facade_contract_sha256",
        "initial_journal_generation",
        "initial_registry_claim_count",
        "initial_success_outcome_count",
        "exact_parent_chain_replayed",
        "restartable_open_supported",
        "credential_persisted_hashed_or_emitted",
        "automatic_retry_or_resume_authorized",
        "active_provider_traffic_authorized",
        "active_forward_integration_authorized",
        "benchmark_forward_or_evaluator_authorized",
        "dev64_or_exact220_launch_authorized",
        "package_ready_sha256",
    }
)


class CandidateRunnerPackageError(RuntimeError):
    """Sanitized package failure without credential or provider content."""


class CandidateRunnerPackagePoisoned(CandidateRunnerPackageError):
    """The local package layout or a frozen binding is no longer exact."""


@dataclasses.dataclass(frozen=True)
class CandidateRunnerFrozenInputs:
    guidance_contract: Mapping[str, Any]
    guidance_policy: Mapping[str, Any]
    guidance_arm: Mapping[str, Any]
    scouts: Sequence[Mapping[str, Any]]
    probe: Mapping[str, Any] | None
    experience: Mapping[str, Any] | None
    pristine_initial_state: Mapping[str, Any]
    facade_contract: Mapping[str, Any]


@dataclasses.dataclass(frozen=True)
class CandidateRunnerCredentials:
    """Ephemeral provider secrets; this object is never canonicalized."""

    tavily_credentials: tuple[str, ...] = ()
    anthropic_credential: str | None = None


@dataclasses.dataclass(frozen=True)
class CandidateRunnerTransportBundle:
    """Explicit test transport hooks; all-None selects hardened defaults."""

    model_post: Callable[..., Any] | None = None
    search_post: Callable[..., Any] | None = None
    fetch_resolve: Callable[[str, int], Sequence[str]] | None = None
    fetch_pool_factory: Callable[..., Any] | None = None
    monotonic_ns: Callable[[], int] | None = None
    sleeper: Callable[[float], None] | None = None


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
        raise ValueError(f"V2.42.52 {label} schema is not exact")
    return dict(value)


def _sealed(value: Mapping[str, Any], *, key: str) -> bool:
    seal = value.get(key)
    if not _is_sha256(seal):
        return False
    unsigned = dict(value)
    unsigned.pop(key)
    return seal == object_sha256(unsigned)


def _ordinary_directory(path: Path, *, label: str) -> Path:
    candidate = path.absolute()
    try:
        metadata = path.lstat()
    except FileNotFoundError as error:
        raise ValueError(f"V2.42.52 {label} is absent") from error
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or path.is_symlink()
        or path.resolve(strict=True) != candidate
    ):
        raise ValueError(f"V2.42.52 {label} is not an ordinary directory")
    return candidate


def _separate_roots(package_root: Path, source_root: Path) -> None:
    if (
        package_root == source_root
        or package_root.is_relative_to(source_root)
        or source_root.is_relative_to(package_root)
    ):
        raise ValueError("V2.42.52 package and source roots overlap")


def _require_loaded_source_root(source_root: Path) -> None:
    if source_root != LOADED_SOURCE_ROOT:
        raise ValueError(
            "V2.42.52 source root does not contain the executing candidate modules"
        )


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _encoded(value: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


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


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise CandidateRunnerPackagePoisoned(
                "V2.42.52 duplicate JSON key rejected"
            )
        value[key] = item
    return value


def _reject_constant(_value: str) -> None:
    raise CandidateRunnerPackagePoisoned("V2.42.52 non-finite JSON rejected")


def _stable_stat(value: os.stat_result) -> tuple[int, ...]:
    """Compare identity/content metadata while allowing read-induced atime."""

    return (
        value.st_dev,
        value.st_ino,
        value.st_mode,
        value.st_nlink,
        value.st_uid,
        value.st_gid,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


def _read_object(path: Path) -> dict[str, Any]:
    try:
        metadata = path.lstat()
    except FileNotFoundError as error:
        raise CandidateRunnerPackagePoisoned(
            "V2.42.52 required package file is absent"
        ) from error
    if (
        not stat.S_ISREG(metadata.st_mode)
        or path.is_symlink()
        or metadata.st_nlink != 1
        or metadata.st_size > MAX_PACKAGE_FILE_BYTES
    ):
        raise CandidateRunnerPackagePoisoned(
            "V2.42.52 package file is nonordinary or oversized"
        )
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(descriptor)
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(
                descriptor,
                min(1_048_576, MAX_PACKAGE_FILE_BYTES + 1 - total),
            )
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > MAX_PACKAGE_FILE_BYTES:
                raise CandidateRunnerPackagePoisoned(
                    "V2.42.52 package file exceeds the frozen cap"
                )
        payload = b"".join(chunks)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    if _stable_stat(before) != _stable_stat(after) or len(payload) > MAX_PACKAGE_FILE_BYTES:
        raise CandidateRunnerPackagePoisoned("V2.42.52 package file changed while read")
    try:
        value = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise CandidateRunnerPackagePoisoned("V2.42.52 package JSON is invalid") from error
    if not isinstance(value, dict):
        raise CandidateRunnerPackagePoisoned("V2.42.52 package JSON is not an object")
    return value


def _read_source_file(source_root: Path, relative: str) -> tuple[int, str]:
    path = source_root / relative
    if path.resolve(strict=False) != path.absolute() or not path.is_relative_to(source_root):
        raise ValueError("V2.42.52 source path is noncanonical")
    try:
        metadata = path.lstat()
    except FileNotFoundError as error:
        raise ValueError("V2.42.52 required source file is absent") from error
    if (
        not stat.S_ISREG(metadata.st_mode)
        or path.is_symlink()
        or metadata.st_nlink != 1
        or metadata.st_size > MAX_SOURCE_FILE_BYTES
    ):
        raise ValueError("V2.42.52 source file is nonordinary or oversized")
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(descriptor)
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, min(1_048_576, MAX_SOURCE_FILE_BYTES + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > MAX_SOURCE_FILE_BYTES:
                raise ValueError("V2.42.52 source file exceeds the frozen cap")
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    if _stable_stat(before) != _stable_stat(after) or total != metadata.st_size:
        raise ValueError("V2.42.52 source file changed while hashed")
    return total, hashlib.sha256(b"".join(chunks)).hexdigest()


def build_candidate_runner_source_manifest(*, source_root: Path) -> dict[str, Any]:
    root = _ordinary_directory(source_root, label="source root")
    _require_loaded_source_root(root)
    files: list[dict[str, Any]] = []
    total = 0
    for relative in SOURCE_RELATIVE_PATHS:
        size, digest = _read_source_file(root, relative)
        total += size
        if total > MAX_SOURCE_TOTAL_BYTES:
            raise ValueError("V2.42.52 source closure exceeds the frozen cap")
        files.append({"path": relative, "size_bytes": size, "sha256": digest})
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": SOURCE_MANIFEST_ROLE,
        "policy_id": POLICY_ID,
        "files": files,
        "file_count": len(files),
        "total_bytes": total,
        "ordinary_regular_single_link_files": True,
    }
    value["source_manifest_sha256"] = object_sha256(value)
    validate_candidate_runner_source_manifest(value)
    return value


def validate_candidate_runner_source_manifest(value: Mapping[str, Any]) -> None:
    manifest = _exact(value, keys=SOURCE_MANIFEST_KEYS, label="source manifest")
    files = manifest.get("files")
    if not isinstance(files, list) or len(files) != len(SOURCE_RELATIVE_PATHS):
        raise ValueError("V2.42.52 source manifest file set drifted")
    normalized: list[dict[str, Any]] = []
    total = 0
    for expected, supplied in zip(SOURCE_RELATIVE_PATHS, files, strict=True):
        row = _exact(supplied, keys=SOURCE_FILE_KEYS, label="source file row")
        size = row.get("size_bytes")
        if (
            row.get("path") != expected
            or isinstance(size, bool)
            or not isinstance(size, int)
            or not 0 <= size <= MAX_SOURCE_FILE_BYTES
            or not _is_sha256(row.get("sha256"))
        ):
            raise ValueError("V2.42.52 source manifest row drifted")
        total += size
        normalized.append(dict(row))
    if (
        total > MAX_SOURCE_TOTAL_BYTES
        or manifest.get("role") != SOURCE_MANIFEST_ROLE
        or manifest.get("policy_id") != POLICY_ID
        or manifest.get("artifact_version") != 1
        or manifest.get("files") != normalized
        or manifest.get("file_count") != len(SOURCE_RELATIVE_PATHS)
        or manifest.get("total_bytes") != total
        or manifest.get("ordinary_regular_single_link_files") is not True
        or not _sealed(manifest, key="source_manifest_sha256")
    ):
        raise ValueError("V2.42.52 source manifest drifted")


def _shared(frozen: CandidateRunnerFrozenInputs) -> dict[str, Any]:
    return {
        "contract": frozen.guidance_contract,
        "guidance_policy": frozen.guidance_policy,
        "guidance_arm": frozen.guidance_arm,
        "scouts": frozen.scouts,
        "probe": frozen.probe,
        "experience": frozen.experience,
    }


def _coordinator_shared(frozen: CandidateRunnerFrozenInputs) -> dict[str, Any]:
    return {
        "guidance_contract": frozen.guidance_contract,
        "guidance_policy": frozen.guidance_policy,
        "guidance_arm": frozen.guidance_arm,
        "scouts": frozen.scouts,
        "probe": frozen.probe,
        "experience": frozen.experience,
    }


def _validate_frozen_inputs(frozen: CandidateRunnerFrozenInputs) -> None:
    if type(frozen) is not CandidateRunnerFrozenInputs:
        raise ValueError("V2.42.52 frozen input type is invalid")
    validate_shared_total_budget_contract(frozen.guidance_contract)
    validate_guidance_policy(frozen.guidance_policy)
    if isinstance(frozen.scouts, (str, bytes)) or not isinstance(frozen.scouts, Sequence):
        raise ValueError("V2.42.52 scout collection is invalid")
    for scout in frozen.scouts:
        validate_scout_process_trace(scout, policy=frozen.guidance_policy)
    if frozen.probe is not None:
        validate_web_probe_receipt(frozen.probe, policy=frozen.guidance_policy)
    if frozen.experience is not None:
        validate_sibling_process_experience(
            frozen.experience,
            policy=frozen.guidance_policy,
            scouts=frozen.scouts,
        )
    validate_guidance_arm(
        frozen.guidance_arm,
        policy=frozen.guidance_policy,
        scouts=frozen.scouts,
        probe=frozen.probe,
        experience=frozen.experience,
    )
    validate_effect_preauthorization_state(
        frozen.pristine_initial_state,
        **_shared(frozen),
    )
    if (
        frozen.pristine_initial_state.get("event_count") != 0
        or frozen.pristine_initial_state.get("events") != []
        or frozen.pristine_initial_state.get("pending_permit_refs") != []
    ):
        raise ValueError("V2.42.52 initial effect state is not pristine")
    validate_candidate_client_facade_contract(frozen.facade_contract)
    for artifact in (
        frozen.guidance_contract,
        frozen.guidance_policy,
        frozen.guidance_arm,
        frozen.scouts,
        frozen.probe,
        frozen.experience,
        frozen.pristine_initial_state,
        frozen.facade_contract,
    ):
        reject_privileged_metadata(artifact)


def _provider_configuration(facade: Mapping[str, Any]) -> dict[str, Any]:
    provider = facade["search_provider_kind"]
    assembly = facade["assembly_contract"]
    if provider == "tavily_search_api":
        endpoint, model, version = TAVILY_ENDPOINT, "", ""
    elif provider == "azure_responses_web_search":
        endpoint, model, version = AZURE_SEARCH_ENDPOINT, AZURE_SEARCH_MODEL, ""
    elif provider == "anthropic_server_web_search":
        endpoint, model, version = (
            ANTHROPIC_ENDPOINT,
            ANTHROPIC_MODEL,
            ALLOWED_ANTHROPIC_VERSION,
        )
    else:
        raise ValueError("V2.42.52 search provider is invalid")
    return {
        "model_endpoint": MODEL_ENDPOINT,
        "model_name": MODEL_NAME,
        "search_provider_kind": provider,
        "search_endpoint": endpoint,
        "search_model": model,
        "search_api_version": version,
        "fetch_adapter_kind": "PinnedNativeHttpFetchAdapter",
        "model_timeout_seconds": facade["model_timeout_seconds"],
        "search_timeout_seconds": facade["search_timeout_seconds"],
        "fetch_timeout_seconds": facade["fetch_timeout_seconds"],
        "model_max_attempts": facade["model_max_attempts"],
        "search_max_attempts": facade["search_max_attempts"],
        "fetch_max_attempts": facade["fetch_max_attempts"],
        "model_maximum_prompt_utf8_bytes": facade[
            "model_maximum_prompt_utf8_bytes"
        ],
        "model_maximum_output_tokens": facade["model_maximum_output_tokens"],
        "search_maximum_query_utf8_bytes": facade[
            "search_maximum_query_utf8_bytes"
        ],
        "search_maximum_output_tokens": facade["search_maximum_output_tokens"],
        "search_maximum_provider_tool_calls_per_attempt": facade[
            "search_maximum_provider_tool_calls_per_attempt"
        ],
        "search_maximum_results": facade["search_maximum_results"],
        "fetch_maximum_response_bytes": facade["fetch_maximum_response_bytes"],
        "model_parser_contract_sha256": assembly[
            "model_parser_contract_sha256"
        ],
        "search_page_projection_contract_sha256": assembly[
            "search_page_projection_contract_sha256"
        ],
    }


def build_candidate_runner_package_contract(
    *,
    source_root: Path,
    frozen: CandidateRunnerFrozenInputs,
    journal_namespace_sha256: str,
) -> dict[str, Any]:
    _validate_frozen_inputs(frozen)
    if not _is_sha256(journal_namespace_sha256):
        raise ValueError("V2.42.52 journal namespace is invalid")
    manifest = build_candidate_runner_source_manifest(source_root=source_root)
    probe_sha = None if frozen.probe is None else frozen.probe["probe_receipt_sha256"]
    experience_sha = (
        None if frozen.experience is None else frozen.experience["experience_sha256"]
    )
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": CONTRACT_ROLE,
        "policy_id": POLICY_ID,
        "candidate_package": True,
        "source_manifest": manifest,
        "source_manifest_sha256": manifest["source_manifest_sha256"],
        "guidance_contract_sha256": frozen.guidance_contract["contract_sha256"],
        "guidance_policy_sha256": frozen.guidance_policy["policy_sha256"],
        "guidance_arm_name": frozen.guidance_arm["arm_name"],
        "guidance_arm_sha256": frozen.guidance_arm["arm_sha256"],
        "scout_trace_sha256s": [
            scout["scout_trace_sha256"] for scout in frozen.scouts
        ],
        "probe_receipt_sha256": probe_sha,
        "experience_sha256": experience_sha,
        "pristine_initial_state_sha256": frozen.pristine_initial_state[
            "state_sha256"
        ],
        "journal_namespace_sha256": journal_namespace_sha256,
        "facade_contract": _clone(dict(frozen.facade_contract)),
        "facade_contract_sha256": frozen.facade_contract["contract_sha256"],
        "provider_configuration": _provider_configuration(frozen.facade_contract),
        "package_layout": {
            "initial_file": INITIAL_FILE,
            "ready_file": READY_FILE,
            "journal_directory": JOURNAL_DIRECTORY,
            "registry_directory": REGISTRY_DIRECTORY,
            "outcome_directory": OUTCOME_DIRECTORY,
        },
        "credentials_are_ephemeral_runtime_arguments": True,
        "credential_persisted_hashed_or_emitted": False,
        "credential_retained_in_adapter_memory": True,
        "default_hardened_real_transports_supported": True,
        "explicit_fake_transport_bundle_supported": True,
        "source_manifest_revalidated_before_each_runner_operation": True,
        "intra_operation_source_to_effect_atomicity_proven": False,
        "loaded_code_identity_independently_attested": False,
        "direct_parent_chain_bypass_globally_excluded": False,
        "malicious_same_user_resealing_excluded": False,
        "network_or_distributed_filesystem_semantics_proven": False,
        "label_blind_runtime": True,
        "benchmark_or_evaluator_metadata_used_for_routing": False,
        "active_provider_traffic_authorized": False,
        "active_forward_integration_authorized": False,
        "benchmark_forward_or_evaluator_authorized": False,
        "dev64_or_exact220_launch_authorized": False,
    }
    value["package_contract_sha256"] = object_sha256(value)
    validate_candidate_runner_package_contract(value)
    return value


def validate_candidate_runner_package_contract(value: Mapping[str, Any]) -> None:
    contract = _exact(value, keys=CONTRACT_KEYS, label="package contract")
    manifest = contract.get("source_manifest")
    facade = contract.get("facade_contract")
    provider = contract.get("provider_configuration")
    if not isinstance(manifest, Mapping) or not isinstance(facade, Mapping):
        raise ValueError("V2.42.52 package contract parent is invalid")
    validate_candidate_runner_source_manifest(manifest)
    validate_candidate_client_facade_contract(facade)
    provider_value = _exact(
        provider, keys=PROVIDER_CONFIGURATION_KEYS, label="provider configuration"
    )
    layout = contract.get("package_layout")
    if (
        contract.get("artifact_version") != 1
        or contract.get("role") != CONTRACT_ROLE
        or contract.get("policy_id") != POLICY_ID
        or contract.get("candidate_package") is not True
        or contract.get("source_manifest_sha256")
        != manifest.get("source_manifest_sha256")
        or not _is_sha256(contract.get("guidance_contract_sha256"))
        or not _is_sha256(contract.get("guidance_policy_sha256"))
        or not isinstance(contract.get("guidance_arm_name"), str)
        or not _is_sha256(contract.get("guidance_arm_sha256"))
        or not isinstance(contract.get("scout_trace_sha256s"), list)
        or any(not _is_sha256(item) for item in contract["scout_trace_sha256s"])
        or contract.get("probe_receipt_sha256") is not None
        and not _is_sha256(contract.get("probe_receipt_sha256"))
        or contract.get("experience_sha256") is not None
        and not _is_sha256(contract.get("experience_sha256"))
        or not _is_sha256(contract.get("pristine_initial_state_sha256"))
        or not _is_sha256(contract.get("journal_namespace_sha256"))
        or contract.get("facade_contract_sha256") != facade.get("contract_sha256")
        or provider_value != _provider_configuration(facade)
        or layout
        != {
            "initial_file": INITIAL_FILE,
            "ready_file": READY_FILE,
            "journal_directory": JOURNAL_DIRECTORY,
            "registry_directory": REGISTRY_DIRECTORY,
            "outcome_directory": OUTCOME_DIRECTORY,
        }
        or contract.get("credentials_are_ephemeral_runtime_arguments") is not True
        or contract.get("credential_persisted_hashed_or_emitted") is not False
        or contract.get("credential_retained_in_adapter_memory") is not True
        or contract.get("default_hardened_real_transports_supported") is not True
        or contract.get("explicit_fake_transport_bundle_supported") is not True
        or contract.get("source_manifest_revalidated_before_each_runner_operation")
        is not True
        or contract.get("intra_operation_source_to_effect_atomicity_proven")
        is not False
        or contract.get("loaded_code_identity_independently_attested") is not False
        or contract.get("direct_parent_chain_bypass_globally_excluded") is not False
        or contract.get("malicious_same_user_resealing_excluded") is not False
        or contract.get("network_or_distributed_filesystem_semantics_proven")
        is not False
        or contract.get("label_blind_runtime") is not True
        or contract.get("benchmark_or_evaluator_metadata_used_for_routing") is not False
        or contract.get("active_provider_traffic_authorized") is not False
        or contract.get("active_forward_integration_authorized") is not False
        or contract.get("benchmark_forward_or_evaluator_authorized") is not False
        or contract.get("dev64_or_exact220_launch_authorized") is not False
        or not _sealed(contract, key="package_contract_sha256")
    ):
        raise ValueError("V2.42.52 package contract drifted")


def _require_contract_binding(
    contract: Mapping[str, Any],
    *,
    source_root: Path,
    frozen: CandidateRunnerFrozenInputs,
) -> dict[str, Any]:
    validate_candidate_runner_package_contract(contract)
    _validate_frozen_inputs(frozen)
    current = build_candidate_runner_source_manifest(source_root=source_root)
    probe_sha = None if frozen.probe is None else frozen.probe["probe_receipt_sha256"]
    experience_sha = (
        None if frozen.experience is None else frozen.experience["experience_sha256"]
    )
    expected = {
        "source_manifest": current,
        "source_manifest_sha256": current["source_manifest_sha256"],
        "guidance_contract_sha256": frozen.guidance_contract["contract_sha256"],
        "guidance_policy_sha256": frozen.guidance_policy["policy_sha256"],
        "guidance_arm_name": frozen.guidance_arm["arm_name"],
        "guidance_arm_sha256": frozen.guidance_arm["arm_sha256"],
        "scout_trace_sha256s": [
            scout["scout_trace_sha256"] for scout in frozen.scouts
        ],
        "probe_receipt_sha256": probe_sha,
        "experience_sha256": experience_sha,
        "pristine_initial_state_sha256": frozen.pristine_initial_state[
            "state_sha256"
        ],
        "facade_contract": dict(frozen.facade_contract),
        "facade_contract_sha256": frozen.facade_contract["contract_sha256"],
        "provider_configuration": _provider_configuration(frozen.facade_contract),
    }
    if any(contract.get(key) != value for key, value in expected.items()):
        raise CandidateRunnerPackagePoisoned(
            "V2.42.52 source, configuration, or frozen parent binding drifted"
        )
    return current


def _validate_runtime_arguments(
    credentials: CandidateRunnerCredentials,
    transports: CandidateRunnerTransportBundle,
) -> None:
    if type(credentials) is not CandidateRunnerCredentials:
        raise ValueError("V2.42.52 credential container exact type is invalid")
    if type(transports) is not CandidateRunnerTransportBundle:
        raise ValueError("V2.42.52 transport bundle exact type is invalid")
    for field in dataclasses.fields(transports):
        value = getattr(transports, field.name)
        if value is not None and not callable(value):
            raise ValueError("V2.42.52 transport hook is not callable")


def _build_adapters(
    *,
    contract: Mapping[str, Any],
    credentials: CandidateRunnerCredentials,
    transports: CandidateRunnerTransportBundle,
) -> tuple[Any, Any, Any]:
    _validate_runtime_arguments(credentials, transports)
    facade = contract["facade_contract"]
    provider = facade["search_provider_kind"]
    if provider == "tavily_search_api":
        if credentials.anthropic_credential is not None:
            raise ValueError("V2.42.52 credential/provider pairing is invalid")
        search_adapter: Any = TavilySearchSingleAttemptAdapter(
            endpoint=TAVILY_ENDPOINT,
            credentials=credentials.tavily_credentials,
            timeout_seconds=facade["search_timeout_seconds"],
            post=transports.search_post,
        )
    elif provider == "azure_responses_web_search":
        if credentials.tavily_credentials or credentials.anthropic_credential is not None:
            raise ValueError("V2.42.52 hosted-search credential container must be empty")
        search_adapter = AzureHostedSearchSingleAttemptAdapter(
            endpoint=AZURE_SEARCH_ENDPOINT,
            model=AZURE_SEARCH_MODEL,
            timeout_seconds=facade["search_timeout_seconds"],
            post=transports.search_post,
        )
    elif provider == "anthropic_server_web_search":
        if credentials.tavily_credentials or credentials.anthropic_credential is None:
            raise ValueError("V2.42.52 credential/provider pairing is invalid")
        search_adapter = AnthropicServerSearchSingleAttemptAdapter(
            endpoint=ANTHROPIC_ENDPOINT,
            model=ANTHROPIC_MODEL,
            anthropic_version=ALLOWED_ANTHROPIC_VERSION,
            credential=credentials.anthropic_credential,
            timeout_seconds=facade["search_timeout_seconds"],
            post=transports.search_post,
        )
    else:
        raise ValueError("V2.42.52 search provider is invalid")
    model_adapter = AzureResponsesSingleAttemptAdapter(
        endpoint=MODEL_ENDPOINT,
        model=MODEL_NAME,
        timeout_seconds=facade["model_timeout_seconds"],
        post=transports.model_post,
    )
    fetch_adapter = PinnedNativeHttpFetchAdapter(
        timeout_seconds=facade["fetch_timeout_seconds"],
        max_response_bytes=facade["fetch_maximum_response_bytes"],
        resolve=transports.fetch_resolve,
        pool_factory=transports.fetch_pool_factory,
    )
    return model_adapter, search_adapter, fetch_adapter


def _initial_receipt(contract: Mapping[str, Any]) -> dict[str, Any]:
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": INITIAL_ROLE,
        "policy_id": POLICY_ID,
        "package_contract": _clone(dict(contract)),
        "package_contract_sha256": contract["package_contract_sha256"],
        "package_initial_published_create_exclusive": True,
        "substores_pristine_before_initialization": True,
        "credential_persisted_hashed_or_emitted": False,
        "active_provider_traffic_authorized": False,
        "active_forward_integration_authorized": False,
        "benchmark_forward_or_evaluator_authorized": False,
    }
    value["package_initial_sha256"] = object_sha256(value)
    validate_candidate_runner_package_initial(value)
    return value


def validate_candidate_runner_package_initial(value: Mapping[str, Any]) -> None:
    initial = _exact(value, keys=INITIAL_KEYS, label="package initial")
    contract = initial.get("package_contract")
    if not isinstance(contract, Mapping):
        raise ValueError("V2.42.52 package initial contract is invalid")
    validate_candidate_runner_package_contract(contract)
    if (
        initial.get("artifact_version") != 1
        or initial.get("role") != INITIAL_ROLE
        or initial.get("policy_id") != POLICY_ID
        or initial.get("package_contract_sha256")
        != contract.get("package_contract_sha256")
        or initial.get("package_initial_published_create_exclusive") is not True
        or initial.get("substores_pristine_before_initialization") is not True
        or initial.get("credential_persisted_hashed_or_emitted") is not False
        or initial.get("active_provider_traffic_authorized") is not False
        or initial.get("active_forward_integration_authorized") is not False
        or initial.get("benchmark_forward_or_evaluator_authorized") is not False
        or not _sealed(initial, key="package_initial_sha256")
    ):
        raise ValueError("V2.42.52 package initial drifted")


def _ready_receipt(
    *,
    contract: Mapping[str, Any],
    initial: Mapping[str, Any],
    coordinator: DurablePreauthorizedEffectCoordinator,
    registry: DurableCandidateActionRegistry,
    ledger: DurableActionOutcomeLedger,
) -> dict[str, Any]:
    journal_initial = _read_object(coordinator.journal.initial_path)
    journal_status = coordinator.journal.status()
    registry_status = registry.status()
    ledger_status = ledger.status()
    if (
        journal_status["generation"] != 0
        or registry_status["allocated_action_count"] != 0
        or ledger_status["durable_success_outcome_count"] != 0
        or ledger_status["unresolved_claim_count"] != 0
    ):
        raise CandidateRunnerPackageError("V2.42.52 parent stores are not pristine")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": READY_ROLE,
        "policy_id": POLICY_ID,
        "package_contract_sha256": contract["package_contract_sha256"],
        "package_initial_sha256": initial["package_initial_sha256"],
        "source_manifest_sha256": contract["source_manifest_sha256"],
        "journal_initial_sha256": journal_initial["initial_sha256"],
        "registry_initial_sha256": registry._initial["initial_sha256"],
        "outcome_initial_sha256": ledger._initial["initial_sha256"],
        "facade_contract_sha256": contract["facade_contract_sha256"],
        "initial_journal_generation": 0,
        "initial_registry_claim_count": 0,
        "initial_success_outcome_count": 0,
        "exact_parent_chain_replayed": True,
        "restartable_open_supported": True,
        "credential_persisted_hashed_or_emitted": False,
        "automatic_retry_or_resume_authorized": False,
        "active_provider_traffic_authorized": False,
        "active_forward_integration_authorized": False,
        "benchmark_forward_or_evaluator_authorized": False,
        "dev64_or_exact220_launch_authorized": False,
    }
    value["package_ready_sha256"] = object_sha256(value)
    validate_candidate_runner_package_ready(value)
    return value


def validate_candidate_runner_package_ready(value: Mapping[str, Any]) -> None:
    ready = _exact(value, keys=READY_KEYS, label="package ready")
    if (
        ready.get("artifact_version") != 1
        or ready.get("role") != READY_ROLE
        or ready.get("policy_id") != POLICY_ID
        or any(
            not _is_sha256(ready.get(key))
            for key in (
                "package_contract_sha256",
                "package_initial_sha256",
                "source_manifest_sha256",
                "journal_initial_sha256",
                "registry_initial_sha256",
                "outcome_initial_sha256",
                "facade_contract_sha256",
            )
        )
        or ready.get("initial_journal_generation") != 0
        or ready.get("initial_registry_claim_count") != 0
        or ready.get("initial_success_outcome_count") != 0
        or ready.get("exact_parent_chain_replayed") is not True
        or ready.get("restartable_open_supported") is not True
        or ready.get("credential_persisted_hashed_or_emitted") is not False
        or ready.get("automatic_retry_or_resume_authorized") is not False
        or ready.get("active_provider_traffic_authorized") is not False
        or ready.get("active_forward_integration_authorized") is not False
        or ready.get("benchmark_forward_or_evaluator_authorized") is not False
        or ready.get("dev64_or_exact220_launch_authorized") is not False
        or not _sealed(ready, key="package_ready_sha256")
    ):
        raise ValueError("V2.42.52 package ready receipt drifted")


class _PackageModelClient:
    def __init__(self, package: "CandidateRunnerPackage", inner: RunnerCompatibleModelClient):
        self._package = package
        self._inner = inner

    def complete_json(
        self,
        system: str,
        user: str,
        *,
        max_output_tokens: int,
        repair_tokens: int = 4096,
        max_parse_attempts: int = 3,
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        self._package._require_ready()
        return self._inner.complete_json(
            system,
            user,
            max_output_tokens=max_output_tokens,
            repair_tokens=repair_tokens,
            max_parse_attempts=max_parse_attempts,
        )

    def __getattr__(self, name: str) -> Any:
        if name not in {
            "requests",
            "calls",
            "failures",
            "attempts",
            "input_tokens",
            "output_tokens",
            "total_tokens",
        }:
            raise AttributeError(name)
        return getattr(self._inner, name)


class _PackageSearchClient:
    def __init__(self, package: "CandidateRunnerPackage", inner: RunnerCompatibleSearchClient):
        self._package = package
        self._inner = inner

    def search_many(
        self,
        queries: Sequence[str],
        *,
        max_results: int,
        search_depth: str = "advanced",
        include_raw_content: bool = True,
    ) -> list[dict[str, Any]]:
        self._package._require_ready()
        return self._inner.search_many(
            queries,
            max_results=max_results,
            search_depth=search_depth,
            include_raw_content=include_raw_content,
        )

    def search(
        self,
        query: str,
        *,
        max_results: int,
        search_depth: str = "advanced",
        include_raw_content: bool = True,
    ) -> dict[str, Any]:
        self._package._require_ready()
        return self._inner.search(
            query,
            max_results=max_results,
            search_depth=search_depth,
            include_raw_content=include_raw_content,
        )

    def fetch_urls(self, requests_: Sequence[dict[str, str]]) -> list[dict[str, Any]]:
        self._package._require_ready()
        return self._inner.fetch_urls(requests_)

    def __getattr__(self, name: str) -> Any:
        if name not in {
            "calls",
            "failures",
            "tool_calls",
            "fetch_calls",
            "fetch_failures",
            "input_tokens",
            "output_tokens",
            "total_tokens",
            "ingress_rejections",
        }:
            raise AttributeError(name)
        return getattr(self._inner, name)


class CandidateRunnerPackage:
    """One source-bound, restartable instance of the V2.42.31--51 chain."""

    def __init__(
        self,
        *,
        root: Path,
        source_root: Path,
        contract: Mapping[str, Any],
        frozen: CandidateRunnerFrozenInputs,
        coordinator: DurablePreauthorizedEffectCoordinator,
        facade: CandidateClientFacade,
        registry: DurableCandidateActionRegistry,
        ledger: DurableActionOutcomeLedger,
        initial: Mapping[str, Any],
        ready: Mapping[str, Any],
    ) -> None:
        self.root = _ordinary_directory(root, label="package root")
        self.source_root = _ordinary_directory(source_root, label="source root")
        _separate_roots(self.root, self.source_root)
        self._contract = _clone(dict(contract))
        self._frozen = CandidateRunnerFrozenInputs(
            guidance_contract=_clone(dict(frozen.guidance_contract)),
            guidance_policy=_clone(dict(frozen.guidance_policy)),
            guidance_arm=_clone(dict(frozen.guidance_arm)),
            scouts=_clone(list(frozen.scouts)),
            probe=_clone(frozen.probe),
            experience=_clone(frozen.experience),
            pristine_initial_state=_clone(dict(frozen.pristine_initial_state)),
            facade_contract=_clone(dict(frozen.facade_contract)),
        )
        self._coordinator = coordinator
        self._facade = facade
        self._registry = registry
        self._ledger = ledger
        self._initial = _clone(dict(initial))
        self._ready = _clone(dict(ready))
        self.initial_path = self.root / INITIAL_FILE
        self.ready_path = self.root / READY_FILE
        self.journal_root = self.root / JOURNAL_DIRECTORY
        self.registry_root = self.root / REGISTRY_DIRECTORY
        self.outcome_root = self.root / OUTCOME_DIRECTORY
        inner_model = RunnerCompatibleModelClient(ledger=ledger)
        inner_search = RunnerCompatibleSearchClient(ledger=ledger)
        self.model_client = _PackageModelClient(self, inner_model)
        self.search_client = _PackageSearchClient(self, inner_search)

    @staticmethod
    def _runtime_chain(
        *,
        journal_root: Path,
        contract: Mapping[str, Any],
        frozen: CandidateRunnerFrozenInputs,
        credentials: CandidateRunnerCredentials,
        transports: CandidateRunnerTransportBundle,
        initialize: bool,
    ) -> tuple[DurablePreauthorizedEffectCoordinator, CandidateClientFacade]:
        model_adapter, search_adapter, fetch_adapter = _build_adapters(
            contract=contract,
            credentials=credentials,
            transports=transports,
        )
        coordinator_arguments = {
            "root": journal_root,
            "journal_namespace_sha256": contract["journal_namespace_sha256"],
            **_coordinator_shared(frozen),
        }
        if initialize:
            coordinator = DurablePreauthorizedEffectCoordinator.initialize(
                initial_state=frozen.pristine_initial_state,
                **coordinator_arguments,
            )
        else:
            coordinator = DurablePreauthorizedEffectCoordinator(**coordinator_arguments)
        scheduler = RetryDeadlineEffectScheduler(
            coordinator=coordinator,
            monotonic_ns=(
                time.monotonic_ns
                if transports.monotonic_ns is None
                else transports.monotonic_ns
            ),
            sleeper=time.sleep if transports.sleeper is None else transports.sleeper,
        )
        assembly = CandidateRuntimeAssembly(
            scheduler=scheduler,
            assembly_contract=frozen.facade_contract["assembly_contract"],
        )
        facade = CandidateClientFacade(
            assembly=assembly,
            facade_contract=frozen.facade_contract,
            model_adapter=model_adapter,
            search_adapter=search_adapter,
            fetch_adapter=fetch_adapter,
        )
        return coordinator, facade

    @classmethod
    def initialize(
        cls,
        *,
        root: Path,
        source_root: Path,
        contract: Mapping[str, Any],
        frozen: CandidateRunnerFrozenInputs,
        credentials: CandidateRunnerCredentials,
        transports: CandidateRunnerTransportBundle | None = None,
    ) -> "CandidateRunnerPackage":
        package_root = _ordinary_directory(root, label="package root")
        source = _ordinary_directory(source_root, label="source root")
        _separate_roots(package_root, source)
        if any(package_root.iterdir()):
            raise FileExistsError("V2.42.52 package root is not pristine")
        transport_bundle = transports or CandidateRunnerTransportBundle()
        _require_contract_binding(contract, source_root=source, frozen=frozen)
        # Validate provider/credential/transport pairing before reserving the root.
        _build_adapters(
            contract=contract,
            credentials=credentials,
            transports=transport_bundle,
        )
        initial = _initial_receipt(contract)
        _publish_new(package_root / INITIAL_FILE, initial)
        for name in (JOURNAL_DIRECTORY, REGISTRY_DIRECTORY, OUTCOME_DIRECTORY):
            os.mkdir(package_root / name, 0o700)
            _fsync_directory(package_root)
        coordinator, facade = cls._runtime_chain(
            journal_root=package_root / JOURNAL_DIRECTORY,
            contract=contract,
            frozen=frozen,
            credentials=credentials,
            transports=transport_bundle,
            initialize=True,
        )
        registry = DurableCandidateActionRegistry.initialize(
            root=package_root / REGISTRY_DIRECTORY,
            facade=facade,
        )
        ledger = DurableActionOutcomeLedger.initialize(
            root=package_root / OUTCOME_DIRECTORY,
            registry=registry,
        )
        ready = _ready_receipt(
            contract=contract,
            initial=initial,
            coordinator=coordinator,
            registry=registry,
            ledger=ledger,
        )
        _publish_new(package_root / READY_FILE, ready)
        package = cls(
            root=package_root,
            source_root=source,
            contract=contract,
            frozen=frozen,
            coordinator=coordinator,
            facade=facade,
            registry=registry,
            ledger=ledger,
            initial=initial,
            ready=ready,
        )
        package._require_ready()
        return package

    @classmethod
    def open(
        cls,
        *,
        root: Path,
        source_root: Path,
        contract: Mapping[str, Any],
        frozen: CandidateRunnerFrozenInputs,
        credentials: CandidateRunnerCredentials,
        transports: CandidateRunnerTransportBundle | None = None,
    ) -> "CandidateRunnerPackage":
        package_root = _ordinary_directory(root, label="package root")
        source = _ordinary_directory(source_root, label="source root")
        _separate_roots(package_root, source)
        transport_bundle = transports or CandidateRunnerTransportBundle()
        _require_contract_binding(contract, source_root=source, frozen=frozen)
        initial = _read_object(package_root / INITIAL_FILE)
        ready = _read_object(package_root / READY_FILE)
        validate_candidate_runner_package_initial(initial)
        validate_candidate_runner_package_ready(ready)
        if initial["package_contract"] != dict(contract):
            raise CandidateRunnerPackagePoisoned("V2.42.52 persisted contract drifted")
        coordinator, facade = cls._runtime_chain(
            journal_root=package_root / JOURNAL_DIRECTORY,
            contract=contract,
            frozen=frozen,
            credentials=credentials,
            transports=transport_bundle,
            initialize=False,
        )
        registry = DurableCandidateActionRegistry.open(
            root=package_root / REGISTRY_DIRECTORY,
            facade=facade,
        )
        ledger = DurableActionOutcomeLedger.open(
            root=package_root / OUTCOME_DIRECTORY,
            registry=registry,
        )
        package = cls(
            root=package_root,
            source_root=source,
            contract=contract,
            frozen=frozen,
            coordinator=coordinator,
            facade=facade,
            registry=registry,
            ledger=ledger,
            initial=initial,
            ready=ready,
        )
        package._require_ready()
        return package

    def _require_layout(self) -> None:
        root = _ordinary_directory(self.root, label="package root")
        expected = {
            root / INITIAL_FILE,
            root / READY_FILE,
            root / JOURNAL_DIRECTORY,
            root / REGISTRY_DIRECTORY,
            root / OUTCOME_DIRECTORY,
        }
        if set(root.iterdir()) != expected:
            raise CandidateRunnerPackagePoisoned(
                "V2.42.52 package root contains residue or is partial"
            )
        for directory in (
            self.journal_root,
            self.registry_root,
            self.outcome_root,
        ):
            _ordinary_directory(directory, label="package substore")

    def _require_ready(self) -> None:
        self._require_layout()
        initial = _read_object(self.initial_path)
        ready = _read_object(self.ready_path)
        try:
            validate_candidate_runner_package_initial(initial)
            validate_candidate_runner_package_ready(ready)
            _require_contract_binding(
                self._contract,
                source_root=self.source_root,
                frozen=self._frozen,
            )
            self._facade._snapshot_contract()
            self._ledger._require_registry_binding()
        except (KeyError, TypeError, ValueError, RuntimeError):
            raise CandidateRunnerPackagePoisoned(
                "V2.42.52 package pre-effect binding validation failed"
            ) from None
        journal_initial = _read_object(self._coordinator.journal.initial_path)
        if (
            initial != self._initial
            or ready != self._ready
            or initial["package_contract"] != self._contract
            or ready["package_contract_sha256"]
            != self._contract["package_contract_sha256"]
            or ready["package_initial_sha256"] != initial["package_initial_sha256"]
            or ready["source_manifest_sha256"]
            != self._contract["source_manifest_sha256"]
            or ready["journal_initial_sha256"] != journal_initial.get("initial_sha256")
            or ready["registry_initial_sha256"]
            != self._registry._initial["initial_sha256"]
            or ready["outcome_initial_sha256"]
            != self._ledger._initial["initial_sha256"]
            or ready["facade_contract_sha256"]
            != self._facade._contract["contract_sha256"]
        ):
            raise CandidateRunnerPackagePoisoned(
                "V2.42.52 ready or parent-initial binding drifted"
            )

    def preflight(self) -> dict[str, Any]:
        self._require_ready()
        journal = self._coordinator.journal.status()
        ledger = self._ledger.status()
        value = {
            "artifact_version": 1,
            "role": STATUS_ROLE,
            "policy_id": POLICY_ID,
            "package_contract_sha256": self._contract["package_contract_sha256"],
            "package_ready_sha256": self._ready["package_ready_sha256"],
            "source_manifest_sha256": self._contract["source_manifest_sha256"],
            "search_provider_kind": self._contract["facade_contract"][
                "search_provider_kind"
            ],
            "journal_generation": journal["generation"],
            "registry_claim_count": ledger["registry_claim_count"],
            "durable_success_outcome_count": ledger[
                "durable_success_outcome_count"
            ],
            "unresolved_claim_count": ledger["unresolved_claim_count"],
            "state": ledger["state"],
            "source_manifest_revalidated": True,
            "credential_persisted_hashed_or_emitted": False,
            "automatic_retry_or_resume_authorized": False,
            "benchmark_or_evaluator_metadata_used_for_routing": False,
            "active_provider_traffic_authorized": False,
            "active_forward_integration_authorized": False,
            "benchmark_forward_or_evaluator_authorized": False,
            "dev64_or_exact220_launch_authorized": False,
        }
        value["status_sha256"] = object_sha256(value)
        return value
