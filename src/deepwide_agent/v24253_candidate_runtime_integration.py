"""Label-blind DeepWide runtime integration for the V2.42.52 package.

V2.42.52 exposes runner-compatible model/search clients but does not prove
that the production-shaped ``DeepWideRuntime`` can consume them safely.  This
isolated successor supplies that missing constructor and task boundary.  It
binds one exact package contract, runtime configuration, transport limits,
source closure, and prospective same-dev64 engineering-gate identity.  Only
``opaque_id`` and the visible ``question`` may enter ``run_task``.

Every task and search-stage entry revalidates the integration source manifest
and the parent package.  After the inherited ingestion path returns, every new
page (including structured chunks) must retain the V2.42.51 admission-derived
``source_type``; the integration annotates the persisted evidence as untrusted
data with zero instruction authority.  Every checkpoint is bound to the
package, ready receipt, integration contract, and source manifest.

This module is still an isolated candidate.  It is not imported by the active
runner, launcher, benchmark, or evaluator.  It does not read credentials,
manifests, ID files, mappings, gold, evaluator output, or scores, and it does
not create a dev64 run, acquire a lease, call a provider, open an evaluator,
or authorize exact-220/leaderboard activity.  The prospective dev64 contract
requires two fresh cold arms, the same opaque partition and execution budget,
both forwards terminal before evaluator access, failure-as-zero, and no
resume/selective rerun; a later create-exclusive launcher must enforce it.
"""

from __future__ import annotations

import copy
import dataclasses
import hashlib
import json
import os
import re
import stat
from pathlib import Path
from typing import Any, Mapping

from deepwide_agent.runtime import DeepWideRuntime, MANIFEST_KEYS, RuntimeConfig
from deepwide_agent.v24232_webswarm_total_budget import object_sha256
from deepwide_agent.v24252_candidate_runner_package import (
    CandidateRunnerPackage,
    validate_candidate_runner_package_contract,
)
from deepwide_agent.v24251_runner_compatible_evidence_bridge import (
    validate_runner_search_batch,
)


POLICY_ID = "v24253_candidate_runtime_integration_v1"
SOURCE_MANIFEST_ROLE = "v24253_candidate_runtime_integration_source_manifest"
CONTRACT_ROLE = "v24253_candidate_runtime_integration_contract"
STATUS_ROLE = "v24253_candidate_runtime_integration_status"

PRODUCTION_PACKAGE_AUTHORIZED = False
ACTIVE_FORWARD_INTEGRATION_AUTHORIZED = False
ACTIVE_PROVIDER_TRAFFIC_AUTHORIZED = False
EXTERNAL_SIDE_EFFECT_AUTHORIZED = False
BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED = False
DEV64_GATE_LAUNCH_AUTHORIZED = False
DEV64_OR_EXACT220_LAUNCH_AUTHORIZED = False
SHARED_API_LEASE_ACQUIRE_AUTHORIZED = False
LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED = False

CANDIDATE_DEEPWIDE_RUNTIME_CONSTRUCTOR_IMPLEMENTED = True
EXACT_VISIBLE_TASK_SCHEMA_ENFORCED = True
PACKAGE_PREFLIGHT_BEFORE_TASK_AND_SEARCH_STAGE = True
GLOBAL_ADMISSION_DERIVED_PAGE_SOURCE_ENFORCED = True
CHECKPOINT_PACKAGE_AND_SOURCE_BINDING_IMPLEMENTED = True
OUTPUT_ROOT_PRISTINE_AT_CONSTRUCTION_REQUIRED = True
RUNTIME_RESUME_OR_SELECTIVE_RERUN_IMPLEMENTED = False
ACTIVE_RUNNER_CONSTRUCTOR_PATCH_IMPLEMENTED = False
PROSPECTIVE_DEV64_GATE_CONTRACT_FROZEN = True
PROSPECTIVE_DEV64_PAIR_MATERIALIZED = False
OFFICIAL_EVALUATOR_OPENED = False
FAILURE_USAGE_ACCOUNTING_EXACT = False
PARALLEL_PROVIDER_EXECUTION_IMPLEMENTED = False

ADMISSION_SOURCE_PREFIX = "v24251_explicit_page_ingress:"
OPAQUE_ID = re.compile(r"task_[0-9a-f]{24}")
MAX_SOURCE_FILE_BYTES = 8_000_000
MAX_SOURCE_TOTAL_BYTES = 40_000_000
SOURCE_RELATIVE_PATHS = (
    "src/deepwide_agent/runtime.py",
    "src/deepwide_agent/v24252_candidate_runner_package.py",
    "src/deepwide_agent/v24253_candidate_runtime_integration.py",
    "scripts/run_deepwide_agent.py",
)
LOADED_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]

MODEL_TOKEN_FIELDS = (
    "plan_tokens",
    "belief_tokens",
    "anchor_tokens",
    "scope_tokens",
    "candidate_tokens",
    "row_tokens",
    "row_refinement_tokens",
    "draft_tokens",
    "audit_tokens",
    "revision_tokens",
    "final_tokens",
)
CONTEXT_CHARACTER_FIELDS = tuple(
    field.name
    for field in dataclasses.fields(RuntimeConfig)
    if field.name.endswith("_chars")
)
RUNTIME_CONFIG_KEYS = frozenset(field.name for field in dataclasses.fields(RuntimeConfig))

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
LAUNCH_LIMIT_KEYS = frozenset(
    {
        "model_timeout_seconds",
        "model_max_attempts",
        "search_timeout_seconds",
        "search_max_attempts",
        "fetch_timeout_seconds",
        "fetch_max_attempts",
        "minimum_model_prompt_utf8_bytes",
        "provider_execution_parallelism",
    }
)
DEV64_IDENTITY_KEYS = frozenset(
    {
        "selected_count",
        "opaque_id_file_sha256",
        "runtime_manifest_sha256",
        "runtime_manifest_schema",
        "raw_opaque_ids_embedded",
        "questions_embedded",
        "mapping_gold_evaluator_or_score_read",
        "consumed_development_partition",
    }
)
CONTRACT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "candidate_runtime_integration",
        "source_manifest",
        "source_manifest_sha256",
        "package_contract",
        "package_contract_sha256",
        "runtime_config",
        "runtime_config_sha256",
        "launch_limits",
        "search_provider_mapping",
        "maximum_runtime_model_output_tokens",
        "maximum_runtime_context_characters",
        "dev64_identity",
        "task_input_exact_keys",
        "task_input_visible_question_only",
        "runtime_label_routing_used",
        "global_admission_derived_page_source_required",
        "checkpoint_package_and_source_binding_required",
        "output_root_pristine_at_construction_required",
        "runtime_resume_or_selective_rerun_allowed",
        "paired_dev64_gate_contract",
        "active_runner_constructor_patch_implemented",
        "active_provider_traffic_authorized",
        "active_forward_integration_authorized",
        "benchmark_forward_or_evaluator_authorized",
        "dev64_gate_launch_authorized",
        "exact220_launch_authorized",
        "shared_api_lease_acquire_authorized",
        "leaderboard_submission_or_sota_claim_authorized",
        "integration_contract_sha256",
    }
)


class CandidateRuntimeIntegrationError(RuntimeError):
    """Sanitized integration failure without task or provider content."""


class CandidateRuntimeIntegrationPoisoned(CandidateRuntimeIntegrationError):
    """A frozen source, package, configuration, or checkpoint binding drifted."""


@dataclasses.dataclass(frozen=True)
class CandidateRuntimeLaunchLimits:
    model_timeout_seconds: int
    model_max_attempts: int
    search_timeout_seconds: int
    search_max_attempts: int
    fetch_timeout_seconds: int
    fetch_max_attempts: int
    minimum_model_prompt_utf8_bytes: int
    provider_execution_parallelism: int = 1


@dataclasses.dataclass(frozen=True)
class CandidateDev64Identity:
    selected_count: int
    opaque_id_file_sha256: str
    runtime_manifest_sha256: str
    runtime_manifest_schema: tuple[str, ...] = ("opaque_id", "question")
    raw_opaque_ids_embedded: bool = False
    questions_embedded: bool = False
    mapping_gold_evaluator_or_score_read: bool = False
    consumed_development_partition: bool = True


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
        raise ValueError(f"V2.42.53 {label} schema is not exact")
    return dict(value)


def _sealed(value: Mapping[str, Any], *, key: str) -> bool:
    seal = value.get(key)
    if not _is_sha256(seal):
        return False
    unsigned = dict(value)
    unsigned.pop(key)
    return seal == object_sha256(unsigned)


def _integer(
    value: object,
    *,
    label: str,
    minimum: int,
    maximum: int = 1_000_000_000_000,
) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < minimum
        or value > maximum
    ):
        raise ValueError(f"V2.42.53 {label} is outside the frozen range")
    return value


def _stable_stat(value: os.stat_result) -> tuple[int, ...]:
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


def _ordinary_directory(path: Path, *, label: str) -> Path:
    candidate = path.absolute()
    try:
        metadata = path.lstat()
    except FileNotFoundError as error:
        raise ValueError(f"V2.42.53 {label} is absent") from error
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or path.is_symlink()
        or path.resolve(strict=True) != candidate
    ):
        raise ValueError(f"V2.42.53 {label} is not an ordinary directory")
    return candidate


def _read_source_file(root: Path, relative: str) -> tuple[int, str]:
    path = root / relative
    if path.resolve(strict=False) != path.absolute() or not path.is_relative_to(root):
        raise ValueError("V2.42.53 source path is noncanonical")
    try:
        metadata = path.lstat()
    except FileNotFoundError as error:
        raise ValueError("V2.42.53 required source file is absent") from error
    if (
        not stat.S_ISREG(metadata.st_mode)
        or path.is_symlink()
        or metadata.st_nlink != 1
        or metadata.st_size > MAX_SOURCE_FILE_BYTES
    ):
        raise ValueError("V2.42.53 source file is nonordinary or oversized")
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(descriptor)
        digest = hashlib.sha256()
        total = 0
        while True:
            chunk = os.read(
                descriptor,
                min(1_048_576, MAX_SOURCE_FILE_BYTES + 1 - total),
            )
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_SOURCE_FILE_BYTES:
                raise ValueError("V2.42.53 source file exceeds the frozen cap")
            digest.update(chunk)
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    if _stable_stat(before) != _stable_stat(after) or total != metadata.st_size:
        raise ValueError("V2.42.53 source file changed while hashed")
    return total, digest.hexdigest()


def build_candidate_runtime_integration_source_manifest(
    *, repository_root: Path
) -> dict[str, Any]:
    root = _ordinary_directory(repository_root, label="repository root")
    if root != LOADED_REPOSITORY_ROOT:
        raise ValueError("V2.42.53 repository root does not contain executing modules")
    files: list[dict[str, Any]] = []
    total = 0
    for relative in SOURCE_RELATIVE_PATHS:
        size, digest = _read_source_file(root, relative)
        total += size
        if total > MAX_SOURCE_TOTAL_BYTES:
            raise ValueError("V2.42.53 source closure exceeds the frozen cap")
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
    validate_candidate_runtime_integration_source_manifest(value)
    return value


def validate_candidate_runtime_integration_source_manifest(
    value: Mapping[str, Any]
) -> None:
    manifest = _exact(value, keys=SOURCE_MANIFEST_KEYS, label="source manifest")
    files = manifest.get("files")
    if not isinstance(files, list) or len(files) != len(SOURCE_RELATIVE_PATHS):
        raise ValueError("V2.42.53 source manifest file set drifted")
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
            raise ValueError("V2.42.53 source manifest row drifted")
        total += size
    if (
        total > MAX_SOURCE_TOTAL_BYTES
        or manifest.get("artifact_version") != 1
        or manifest.get("role") != SOURCE_MANIFEST_ROLE
        or manifest.get("policy_id") != POLICY_ID
        or manifest.get("file_count") != len(SOURCE_RELATIVE_PATHS)
        or manifest.get("total_bytes") != total
        or manifest.get("ordinary_regular_single_link_files") is not True
        or not _sealed(manifest, key="source_manifest_sha256")
    ):
        raise ValueError("V2.42.53 source manifest drifted")


def _launch_limits(value: CandidateRuntimeLaunchLimits) -> dict[str, int]:
    if type(value) is not CandidateRuntimeLaunchLimits:
        raise ValueError("V2.42.53 launch-limit exact type is invalid")
    mapping = dataclasses.asdict(value)
    _exact(mapping, keys=LAUNCH_LIMIT_KEYS, label="launch limits")
    for key in (
        "model_timeout_seconds",
        "model_max_attempts",
        "search_timeout_seconds",
        "search_max_attempts",
        "fetch_timeout_seconds",
        "fetch_max_attempts",
        "minimum_model_prompt_utf8_bytes",
        "provider_execution_parallelism",
    ):
        _integer(mapping[key], label=key, minimum=1)
    if mapping["provider_execution_parallelism"] != 1:
        raise ValueError("V2.42.53 parent package supports only serial provider effects")
    return mapping


def _dev64_identity(value: CandidateDev64Identity) -> dict[str, Any]:
    if type(value) is not CandidateDev64Identity:
        raise ValueError("V2.42.53 dev64 identity exact type is invalid")
    mapping = dataclasses.asdict(value)
    mapping["runtime_manifest_schema"] = list(value.runtime_manifest_schema)
    _exact(mapping, keys=DEV64_IDENTITY_KEYS, label="dev64 identity")
    if (
        mapping["selected_count"] != 64
        or not _is_sha256(mapping["opaque_id_file_sha256"])
        or not _is_sha256(mapping["runtime_manifest_sha256"])
        or mapping["runtime_manifest_schema"] != sorted(MANIFEST_KEYS)
        or mapping["raw_opaque_ids_embedded"] is not False
        or mapping["questions_embedded"] is not False
        or mapping["mapping_gold_evaluator_or_score_read"] is not False
        or mapping["consumed_development_partition"] is not True
    ):
        raise ValueError("V2.42.53 dev64 identity drifted")
    return mapping


def _runtime_configuration(value: RuntimeConfig) -> dict[str, Any]:
    if type(value) is not RuntimeConfig:
        raise ValueError("V2.42.53 runtime config exact type is invalid")
    mapping = dataclasses.asdict(value)
    _exact(mapping, keys=RUNTIME_CONFIG_KEYS, label="runtime config")
    return mapping


def _provider_mapping(provider: str) -> str:
    mapping = {
        "tavily_search_api": "tavily",
        "azure_responses_web_search": "azure-native",
        "anthropic_server_web_search": "anthropic",
    }
    if provider not in mapping:
        raise ValueError("V2.42.53 package search provider is invalid")
    return mapping[provider]


def _maximum_runtime_model_tokens(config: Mapping[str, Any]) -> int:
    values = [
        _integer(config[field], label=field, minimum=1)
        for field in MODEL_TOKEN_FIELDS
    ]
    return max(values)


def _maximum_runtime_context_characters(config: Mapping[str, Any]) -> int:
    values = [
        _integer(config[field], label=field, minimum=1)
        for field in CONTEXT_CHARACTER_FIELDS
    ]
    return max(values)


def _validate_compatibility(
    *,
    package_contract: Mapping[str, Any],
    runtime_config: Mapping[str, Any],
    launch_limits: Mapping[str, Any],
) -> tuple[str, int, int]:
    facade = package_contract["facade_contract"]
    assembly = facade["assembly_contract"]
    provider = _provider_mapping(str(facade["search_provider_kind"]))
    maximum_tokens = _maximum_runtime_model_tokens(runtime_config)
    maximum_context = _maximum_runtime_context_characters(runtime_config)
    if (
        runtime_config["model_name"] != "gpt-5.6-sol"
        or runtime_config["model_reasoning_effort"] != facade["model_reasoning_effort"]
        or runtime_config["model_service_tier"] != facade["model_service_tier"]
        or runtime_config["search_provider"] != provider
        or runtime_config["search_workers"] != 1
        or runtime_config["native_fetch_workers"] != 1
        or runtime_config["tavily_results"] > facade["search_maximum_results"]
        or maximum_tokens > facade["model_maximum_output_tokens"]
        or maximum_context
        > assembly["search_page_projection_contract"][
            "maximum_page_text_characters"
        ]
        or facade["model_maximum_prompt_utf8_bytes"]
        < launch_limits["minimum_model_prompt_utf8_bytes"]
        or facade["model_timeout_seconds"] != launch_limits["model_timeout_seconds"]
        or facade["model_max_attempts"] != launch_limits["model_max_attempts"]
        or facade["search_timeout_seconds"] != launch_limits["search_timeout_seconds"]
        or facade["search_max_attempts"] != launch_limits["search_max_attempts"]
        or facade["fetch_timeout_seconds"] != launch_limits["fetch_timeout_seconds"]
        or facade["fetch_max_attempts"] != launch_limits["fetch_max_attempts"]
        or launch_limits["provider_execution_parallelism"] != 1
    ):
        raise ValueError("V2.42.53 runtime/package execution compatibility drifted")
    if provider == "anthropic" and (
        runtime_config["anthropic_search_model"]
        != package_contract["provider_configuration"]["search_model"]
        or runtime_config["anthropic_search_max_uses"]
        != facade["search_maximum_provider_tool_calls_per_attempt"]
        or runtime_config["anthropic_search_max_output_tokens"]
        != facade["search_maximum_output_tokens"]
    ):
        raise ValueError("V2.42.53 Anthropic runtime/package compatibility drifted")
    return provider, maximum_tokens, maximum_context


def _paired_dev64_gate_contract() -> dict[str, Any]:
    return {
        "gate_kind": "prospective_engineering_runtime_integration_same_dev64",
        "candidate_and_legacy_control_both_fresh_cold_roots_required": True,
        "same_opaque_dev64_ids_required": True,
        "same_runtime_manifest_required": True,
        "same_model_search_fetch_prompt_output_and_total_budget_required": True,
        "same_provider_execution_parallelism_required": True,
        "both_forwards_exact_terminal_before_mapping_or_evaluator": True,
        "conservative_denominator": 64,
        "failure_as_zero": True,
        "forward_or_evaluator_resume_allowed": False,
        "selective_rerun_allowed": False,
        "single_shared_api_lease_required": True,
        "existing_v24216_to_v24220_chain_has_priority": True,
        "quality_gate_thresholds_frozen_by_future_create_exclusive_launcher": False,
        "gate_result_available": False,
        "go_authorizes_exact220": False,
        "dev64_launch_authorized": False,
        "exact220_launch_authorized": False,
        "leaderboard_submission_or_sota_claim_authorized": False,
    }


def build_candidate_runtime_integration_contract(
    *,
    repository_root: Path,
    package_contract: Mapping[str, Any],
    runtime_config: RuntimeConfig,
    launch_limits: CandidateRuntimeLaunchLimits,
    dev64_identity: CandidateDev64Identity,
) -> dict[str, Any]:
    frozen_package = _clone(dict(package_contract))
    validate_candidate_runner_package_contract(frozen_package)
    source = build_candidate_runtime_integration_source_manifest(
        repository_root=repository_root
    )
    config = _runtime_configuration(runtime_config)
    limits = _launch_limits(launch_limits)
    identity = _dev64_identity(dev64_identity)
    provider, maximum_tokens, maximum_context = _validate_compatibility(
        package_contract=frozen_package,
        runtime_config=config,
        launch_limits=limits,
    )
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": CONTRACT_ROLE,
        "policy_id": POLICY_ID,
        "candidate_runtime_integration": True,
        "source_manifest": source,
        "source_manifest_sha256": source["source_manifest_sha256"],
        "package_contract": frozen_package,
        "package_contract_sha256": frozen_package["package_contract_sha256"],
        "runtime_config": config,
        "runtime_config_sha256": object_sha256(config),
        "launch_limits": limits,
        "search_provider_mapping": {
            "package": frozen_package["facade_contract"]["search_provider_kind"],
            "runtime": provider,
        },
        "maximum_runtime_model_output_tokens": maximum_tokens,
        "maximum_runtime_context_characters": maximum_context,
        "dev64_identity": identity,
        "task_input_exact_keys": sorted(MANIFEST_KEYS),
        "task_input_visible_question_only": True,
        "runtime_label_routing_used": False,
        "global_admission_derived_page_source_required": True,
        "checkpoint_package_and_source_binding_required": True,
        "output_root_pristine_at_construction_required": True,
        "runtime_resume_or_selective_rerun_allowed": False,
        "paired_dev64_gate_contract": _paired_dev64_gate_contract(),
        "active_runner_constructor_patch_implemented": False,
        "active_provider_traffic_authorized": False,
        "active_forward_integration_authorized": False,
        "benchmark_forward_or_evaluator_authorized": False,
        "dev64_gate_launch_authorized": False,
        "exact220_launch_authorized": False,
        "shared_api_lease_acquire_authorized": False,
        "leaderboard_submission_or_sota_claim_authorized": False,
    }
    value["integration_contract_sha256"] = object_sha256(value)
    validate_candidate_runtime_integration_contract(value)
    return value


def validate_candidate_runtime_integration_contract(value: Mapping[str, Any]) -> None:
    contract = _exact(value, keys=CONTRACT_KEYS, label="integration contract")
    source = contract.get("source_manifest")
    package = contract.get("package_contract")
    config = contract.get("runtime_config")
    limits = contract.get("launch_limits")
    identity = contract.get("dev64_identity")
    if not all(isinstance(item, Mapping) for item in (source, package, config, limits, identity)):
        raise ValueError("V2.42.53 integration contract parent is invalid")
    validate_candidate_runtime_integration_source_manifest(source)
    validate_candidate_runner_package_contract(package)
    config_value = _exact(config, keys=RUNTIME_CONFIG_KEYS, label="runtime config")
    limit_value = _exact(limits, keys=LAUNCH_LIMIT_KEYS, label="launch limits")
    identity_value = _exact(identity, keys=DEV64_IDENTITY_KEYS, label="dev64 identity")
    provider, maximum_tokens, maximum_context = _validate_compatibility(
        package_contract=package,
        runtime_config=config_value,
        launch_limits=limit_value,
    )
    if (
        contract.get("artifact_version") != 1
        or contract.get("role") != CONTRACT_ROLE
        or contract.get("policy_id") != POLICY_ID
        or contract.get("candidate_runtime_integration") is not True
        or contract.get("source_manifest_sha256")
        != source.get("source_manifest_sha256")
        or contract.get("package_contract_sha256")
        != package.get("package_contract_sha256")
        or contract.get("runtime_config_sha256") != object_sha256(config_value)
        or contract.get("search_provider_mapping")
        != {
            "package": package["facade_contract"]["search_provider_kind"],
            "runtime": provider,
        }
        or contract.get("maximum_runtime_model_output_tokens") != maximum_tokens
        or contract.get("maximum_runtime_context_characters") != maximum_context
        or identity_value.get("selected_count") != 64
        or identity_value.get("runtime_manifest_schema") != sorted(MANIFEST_KEYS)
        or not _is_sha256(identity_value.get("opaque_id_file_sha256"))
        or not _is_sha256(identity_value.get("runtime_manifest_sha256"))
        or any(
            identity_value.get(field) is not False
            for field in (
                "raw_opaque_ids_embedded",
                "questions_embedded",
                "mapping_gold_evaluator_or_score_read",
            )
        )
        or identity_value.get("consumed_development_partition") is not True
        or contract.get("task_input_exact_keys") != sorted(MANIFEST_KEYS)
        or contract.get("task_input_visible_question_only") is not True
        or contract.get("runtime_label_routing_used") is not False
        or contract.get("global_admission_derived_page_source_required") is not True
        or contract.get("checkpoint_package_and_source_binding_required") is not True
        or contract.get("output_root_pristine_at_construction_required") is not True
        or contract.get("runtime_resume_or_selective_rerun_allowed") is not False
        or contract.get("paired_dev64_gate_contract") != _paired_dev64_gate_contract()
        or contract.get("active_runner_constructor_patch_implemented") is not False
        or any(
            contract.get(field) is not False
            for field in (
                "active_provider_traffic_authorized",
                "active_forward_integration_authorized",
                "benchmark_forward_or_evaluator_authorized",
                "dev64_gate_launch_authorized",
                "exact220_launch_authorized",
                "shared_api_lease_acquire_authorized",
                "leaderboard_submission_or_sota_claim_authorized",
            )
        )
        or not _sealed(contract, key="integration_contract_sha256")
    ):
        raise ValueError("V2.42.53 integration contract drifted")


def validate_visible_runtime_task(value: Mapping[str, Any]) -> dict[str, str]:
    task = _exact(value, keys=frozenset(MANIFEST_KEYS), label="visible task")
    opaque_id = task.get("opaque_id")
    question = task.get("question")
    if (
        not isinstance(opaque_id, str)
        or OPAQUE_ID.fullmatch(opaque_id) is None
        or not isinstance(question, str)
        or not question.strip()
        or question != question.strip()
    ):
        raise ValueError("V2.42.53 visible task is invalid")
    return {"opaque_id": opaque_id, "question": question}


class _IntegrationSearchClient:
    """Validate admission-bearing batches before inherited state ingestion."""

    def __init__(self, package: CandidateRunnerPackage) -> None:
        self._package = package

    def search_many(
        self,
        queries: list[str],
        *,
        max_results: int,
        search_depth: str,
        include_raw_content: bool,
    ) -> list[dict[str, Any]]:
        self._package.preflight()
        batches = self._package.search_client.search_many(
            queries,
            max_results=max_results,
            search_depth=search_depth,
            include_raw_content=include_raw_content,
        )
        return [validate_runner_search_batch(batch) for batch in batches]

    def fetch_urls(self, requests_: list[dict[str, str]]) -> list[dict[str, Any]]:
        self._package.preflight()
        batches = self._package.search_client.fetch_urls(requests_)
        return [validate_runner_search_batch(batch) for batch in batches]

    def __getattr__(self, name: str) -> Any:
        return getattr(self._package.search_client, name)


class CandidatePackageDeepWideRuntime(DeepWideRuntime):
    """Bind the existing DeepWide task state machine to one exact package."""

    def __init__(
        self,
        *,
        package: CandidateRunnerPackage,
        runtime_config: RuntimeConfig,
        launch_limits: CandidateRuntimeLaunchLimits,
        integration_contract: Mapping[str, Any],
        out_dir: Path,
    ) -> None:
        if type(package) is not CandidateRunnerPackage:
            raise ValueError("V2.42.53 package exact type is invalid")
        contract = _clone(dict(integration_contract))
        validate_candidate_runtime_integration_contract(contract)
        config = _runtime_configuration(runtime_config)
        limits = _launch_limits(launch_limits)
        if (
            contract["package_contract"] != package._contract
            or contract["runtime_config"] != config
            or contract["launch_limits"] != limits
            or package.source_root.parent != LOADED_REPOSITORY_ROOT
        ):
            raise ValueError("V2.42.53 runtime constructor binding drifted")
        output = _ordinary_directory(out_dir, label="output root")
        if any(output.iterdir()):
            raise FileExistsError("V2.42.53 output root is not pristine")
        for protected in (package.root, package.source_root):
            if (
                output == protected
                or output.is_relative_to(protected)
                or protected.is_relative_to(output)
            ):
                raise ValueError("V2.42.53 output root overlaps protected roots")
        status = package.preflight()
        if status["state"] != "clean" or status["unresolved_claim_count"] != 0:
            raise CandidateRuntimeIntegrationPoisoned(
                "V2.42.53 package is not clean at runtime construction"
            )
        self._candidate_package = package
        self._integration_contract = contract
        self._integration_source_manifest = _clone(contract["source_manifest"])
        self._package_ready_sha256 = package._ready["package_ready_sha256"]
        self._seen_task_ids: set[str] = set()
        super().__init__(
            package.model_client,
            _IntegrationSearchClient(package),
            runtime_config,
            output,
        )
        if self.config_sha256 != contract["runtime_config_sha256"]:
            raise CandidateRuntimeIntegrationPoisoned(
                "V2.42.53 inherited runtime config binding drifted"
            )

    def _require_integration(self) -> dict[str, Any]:
        try:
            validate_candidate_runtime_integration_contract(
                self._integration_contract
            )
            current = build_candidate_runtime_integration_source_manifest(
                repository_root=LOADED_REPOSITORY_ROOT
            )
            package_status = self._candidate_package.preflight()
        except (KeyError, TypeError, ValueError, RuntimeError):
            raise CandidateRuntimeIntegrationPoisoned(
                "V2.42.53 source, contract, or package preflight failed"
            ) from None
        if (
            current != self._integration_source_manifest
            or self._integration_contract["package_contract"]
            != self._candidate_package._contract
            or self._package_ready_sha256
            != self._candidate_package._ready["package_ready_sha256"]
            or package_status["state"] != "clean"
            or package_status["unresolved_claim_count"] != 0
        ):
            raise CandidateRuntimeIntegrationPoisoned(
                "V2.42.53 live integration binding drifted"
            )
        return package_status

    def _save(self, state: dict[str, Any]) -> None:
        self._require_integration()
        # The parent runtime checkpoints from inside search/fetch stages, including
        # exception paths.  Validate the complete evidence store here so no page can
        # become durable during the interval before the stage-level postcondition.
        self._validate_new_pages(state, before=0)
        state["candidate_package_contract_sha256"] = self._integration_contract[
            "package_contract_sha256"
        ]
        state["candidate_package_ready_sha256"] = self._package_ready_sha256
        state["candidate_runtime_integration_contract_sha256"] = (
            self._integration_contract["integration_contract_sha256"]
        )
        state["candidate_runtime_integration_source_manifest_sha256"] = (
            self._integration_contract["source_manifest_sha256"]
        )
        state["candidate_page_evidence_requires_explicit_admission"] = True
        state["benchmark_or_evaluator_metadata_used_for_routing"] = False
        super()._save(state)

    def _search_stage(
        self,
        state: dict[str, Any],
        name: str,
        queries: list[str],
    ) -> None:
        self._require_integration()
        before = len(state.get("evidence") or [])
        super()._search_stage(state, name, queries)
        self._validate_new_pages(state, before=before)
        self._save(state)

    def _directory_fetch_stage(
        self,
        state: dict[str, Any],
        contract: dict[str, Any],
    ) -> None:
        self._require_integration()
        before = len(state.get("evidence") or [])
        super()._directory_fetch_stage(state, contract)
        self._validate_new_pages(state, before=before)
        self._save(state)

    def _validate_new_pages(self, state: dict[str, Any], *, before: int) -> None:
        evidence = state.get("evidence", [])
        if not isinstance(evidence, list):
            raise CandidateRuntimeIntegrationPoisoned(
                "V2.42.53 inherited evidence store drifted"
            )
        if (
            isinstance(before, bool)
            or not isinstance(before, int)
            or not 0 <= before <= len(evidence)
        ):
            raise CandidateRuntimeIntegrationPoisoned(
                "V2.42.53 evidence validation boundary drifted"
            )
        for item in evidence[before:]:
            if not isinstance(item, dict):
                raise CandidateRuntimeIntegrationPoisoned(
                    "V2.42.53 inherited evidence item drifted"
                )
            if item.get("kind") == "page":
                source_type = item.get("source_type")
                if (
                    not isinstance(source_type, str)
                    or not source_type.startswith(ADMISSION_SOURCE_PREFIX)
                    or not _is_sha256(source_type.removeprefix(ADMISSION_SOURCE_PREFIX))
                ):
                    raise CandidateRuntimeIntegrationPoisoned(
                        "V2.42.53 page lacks explicit admission provenance"
                    )
                item["untrusted_data"] = True
                item["instruction_authority"] = False
                item["active_evidence_eligible"] = True

    def run_task(self, task: dict[str, str]) -> dict[str, Any]:
        self._require_integration()
        visible = validate_visible_runtime_task(task)
        opaque_id = visible["opaque_id"]
        if opaque_id in self._seen_task_ids or self._state_path(opaque_id).exists():
            raise CandidateRuntimeIntegrationError(
                "V2.42.53 resume or selective rerun is forbidden"
            )
        self._seen_task_ids.add(opaque_id)
        return super().run_task(visible)

    def integration_status(self) -> dict[str, Any]:
        package = self._require_integration()
        value = {
            "artifact_version": 1,
            "role": STATUS_ROLE,
            "policy_id": POLICY_ID,
            "integration_contract_sha256": self._integration_contract[
                "integration_contract_sha256"
            ],
            "source_manifest_sha256": self._integration_contract[
                "source_manifest_sha256"
            ],
            "package_contract_sha256": self._integration_contract[
                "package_contract_sha256"
            ],
            "package_ready_sha256": self._package_ready_sha256,
            "package_state": package["state"],
            "package_unresolved_claim_count": package["unresolved_claim_count"],
            "tasks_started_in_this_process": len(self._seen_task_ids),
            "task_input_exact_keys": sorted(MANIFEST_KEYS),
            "global_admission_derived_page_source_required": True,
            "runtime_resume_or_selective_rerun_allowed": False,
            "mapping_gold_evaluator_or_score_read": False,
            "active_provider_traffic_authorized": False,
            "active_forward_integration_authorized": False,
            "benchmark_forward_or_evaluator_authorized": False,
            "dev64_gate_launch_authorized": False,
            "exact220_launch_authorized": False,
            "leaderboard_submission_or_sota_claim_authorized": False,
        }
        value["status_sha256"] = object_sha256(value)
        return value
