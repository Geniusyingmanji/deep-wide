"""Fresh exact-220 contract for the parser-total production seam."""

from __future__ import annotations

import copy
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from . import v24895_control_binding_exact220_contract as parent
from .v24900_revision_parser_total_runtime import POLICY_ID as RUNTIME_POLICY_ID
from .v24901_revision_parser_total_mapping_bundle import POLICY_ID as BUNDLE_POLICY_ID
from .v24902_revision_parser_total_child_runtime import POLICY_ID as CHILD_POLICY_ID
from .v24903_revision_parser_total_subprocess_gate import POLICY_ID as GATE_POLICY_ID


DATE = "20260808"
ROLE = "v24905_revision_parser_total_exact220_preregistration"
PROTOCOL_ID = "v24905_revision_parser_total_fixed_budget_exact220_v1"
PROTOCOL = Path(f"results/v24905_revision_parser_total_exact220_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v24905_revision_parser_total_exact220_preactivation_audit_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v24905_revision_parser_total_exact220_execution_start_v1_{DATE}.json")
FORWARD_RESULT = Path(f"results/v24905_revision_parser_total_exact220_forward_result_v1_{DATE}.json")
FORWARD_AUDIT = Path(f"results/v24905_revision_parser_total_exact220_forward_audit_v1_{DATE}.json")
OUTPUT_ROOT = Path(f"outputs/v24905_revision_parser_total_exact220_v1_{DATE}")
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
TASK_ROOT = OUTPUT_ROOT / "tasks"
RUNTIME_PREDICTIONS = OUTPUT_ROOT / "runtime_predictions.jsonl"
RUN_SUMMARY = OUTPUT_ROOT / "run_summary.json"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
SAFE_PROGRESS = OUTPUT_ROOT / "safe_forward_progress.json"
LEASE_PATH = parent.LEASE_PATH
LEASE_OWNER = "v24905_revision_parser_total_exact220_forward_v1"
LEASE_PURPOSE = "fresh_label_blind_revision_parser_total_exact220"
RUNNER_MARKER = "scripts/run_v24905_revision_parser_total_exact220.py"
CHILD_MARKER = "scripts/run_v24905_revision_parser_total_exact220_task.py"

SELECTED_COUNT = parent.SELECTED_COUNT
EXECUTOR_CONCURRENCY = parent.EXECUTOR_CONCURRENCY
MODEL_SLOT_CAP = parent.MODEL_SLOT_CAP
LIMITS = copy.deepcopy(parent.LIMITS)
MODEL = copy.deepcopy(parent.MODEL)
SEARCH = copy.deepcopy(parent.SEARCH)
TWO_WAVE_POLICY = copy.deepcopy(parent.TWO_WAVE_POLICY)
PROTECTED_WATCHERS = parent.PROTECTED_WATCHERS
PARENT_PROTOCOL = parent.PROTOCOL
SOURCE = Path("src/deepwide_agent/v24905_revision_parser_total_exact220_contract.py")
CONTROL = Path("scripts/control_v24905_revision_parser_total_exact220.py")
RUNNER = Path(RUNNER_MARKER)
CHILD = Path(CHILD_MARKER)
FINALIZER = Path("scripts/finalize_v24905_revision_parser_total_exact220.py")
TEST = Path("tests/test_v24905_revision_parser_total_exact220.py")
V24904_RESULT = Path("results/v24904_revision_parser_total_reliability_result_v1_20260808.json")
V24904_POSTAUDIT = Path("results/v24904_revision_parser_total_reliability_postresult_audit_v1_20260808.json")
CORRECTED_SOURCES = tuple(
    Path(f"src/deepwide_agent/v{version}_{name}.py")
    for version, name in (
        ("24897", "revision_parser_totality"),
        ("24898", "revision_parser_total_integration"),
        ("24899", "revision_parser_total_exact_task"),
        ("24900", "revision_parser_total_runtime"),
        ("24901", "revision_parser_total_mapping_bundle"),
        ("24902", "revision_parser_total_child_runtime"),
        ("24903", "revision_parser_total_subprocess_gate"),
    )
)
CORRECTED_TESTS = (
    Path("tests/test_v24897_revision_parser_totality.py"),
    Path("tests/test_v24898_revision_parser_total_integration.py"),
    Path("tests/test_v24903_revision_parser_total_production_seam.py"),
)
SEAM_SOURCES = tuple(dict.fromkeys((*parent.SEAM_SOURCES, *CORRECTED_SOURCES)))
SEAM_TESTS = tuple(dict.fromkeys((*parent.SEAM_TESTS, *CORRECTED_TESTS)))
LOCAL_SOURCES = (SOURCE, CONTROL, RUNNER, CHILD, FINALIZER, TEST)

payload_sha256 = parent.payload_sha256
sha256 = parent.sha256
_git = parent._git
_ordinary_tracked = parent._ordinary_tracked
protected_watcher_snapshot = parent.protected_watcher_snapshot


def _read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"V2.49.05 expected ordinary object: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.49.05 expected object")
    return value


def parent_contract(root: Path, *, frozen: bool = False) -> dict[str, Any]:
    value = _read(root / PARENT_PROTOCOL)
    return (
        parent.validate_frozen_protocol(root, value)
        if frozen else parent.validate_protocol(root, value)
    )


def task_vector(
    root: Path, protocol: Mapping[str, Any] | None = None
) -> list[dict[str, str]]:
    tasks = parent.task_vector(root)
    if len(tasks) != 220 or any(
        set(task) != {"opaque_id", "question"} for task in tasks
    ):
        raise RuntimeError("V2.49.05 visible exact-220 vector drifted")
    if protocol is not None:
        expected = {
            "runtime_input_keys": ["opaque_id", "question"],
            "selected_count": 220,
            "opaque_id_vector_sha256": payload_sha256(
                [task["opaque_id"] for task in tasks]
            ),
            "visible_question_vector_sha256": payload_sha256(
                [task["question"] for task in tasks]
            ),
        }
        if protocol.get("task_contract") != expected:
            raise RuntimeError("V2.49.05 visible task binding drifted")
    return tasks


def coverage_policy() -> dict[str, Any]:
    value = copy.deepcopy(parent.coverage_policy())
    value.update(
        {
            "runtime_policy_id": RUNTIME_POLICY_ID,
            "bundle_policy_id": BUNDLE_POLICY_ID,
            "child_policy_id": CHILD_POLICY_ID,
            "subprocess_gate_policy_id": GATE_POLICY_ID,
            "parent_valid_revision_parser_mismatch_identity_passthrough": True,
            "parser_mismatch_third_model_slot_admitted": False,
            "parser_mismatch_parent_prediction_byte_preserved": True,
            "collector_exact_task_envelope_binding_corrected": True,
        }
    )
    return value


def validate_reliability_gate(root: Path) -> dict[str, Any]:
    result = _read(root / V24904_RESULT)
    audit = _read(root / V24904_POSTAUDIT)
    ru = dict(result)
    rs = ru.pop("result_payload_sha256", None)
    au = dict(audit)
    aseal = au.pop("audit_payload_sha256", None)
    if (
        result.get("role") != "v24904_revision_parser_total_reliability_result"
        or result.get("protocol_id")
        != "v24904_neutral_revision_parser_total_reliability_gate_v1"
        or result.get("status") != "go"
        or result.get("gate_passed") is not True
        or result.get("task_count") != 20
        or result.get("valid_bundles") != 20
        or result.get("invalid_bundles") != 0
        or result.get("hard_timeouts") != 0
        or result.get("subprocess_exceptions") != 0
        or result.get("terminal_stage_counts") != {"bundle_committed": 20}
        or result.get("benchmark_task_or_evaluator_used") is not False
        or result.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_read"
        ) is not False
        or rs != payload_sha256(ru)
        or audit.get("role")
        != "v24904_revision_parser_total_reliability_postresult_audit"
        or audit.get("audit_valid") is not True
        or audit.get("findings") != []
        or not all(value is True for value in (audit.get("checks") or {}).values())
        or audit.get("result_sha256") != sha256(root / V24904_RESULT)
        or aseal != payload_sha256(au)
    ):
        raise RuntimeError("V2.49.05 reliability gate is not strict GO")
    return {
        "result": str(V24904_RESULT),
        "result_sha256": sha256(root / V24904_RESULT),
        "postresult_audit": str(V24904_POSTAUDIT),
        "postresult_audit_sha256": sha256(root / V24904_POSTAUDIT),
        "status": "go",
        "valid_bundles": 20,
        "task_count": 20,
        "hard_timeouts": 0,
        "subprocess_exceptions": 0,
        "benchmark_task_or_evaluator_used": False,
    }


def _relatives(root: Path, *, frozen: bool) -> set[Path]:
    base = parent_contract(root, frozen=frozen)
    relatives = {Path(name) for name in base["dependency_manifest"]}
    relatives.update((PARENT_PROTOCOL, V24904_RESULT, V24904_POSTAUDIT))
    relatives.update(LOCAL_SOURCES)
    relatives.update(CORRECTED_SOURCES)
    relatives.update(CORRECTED_TESTS)
    relatives.update(
        (
            Path("scripts/run_v24877_keyless_coverage_exact220.py"),
            Path("scripts/run_v24877_keyless_coverage_exact220_task.py"),
            Path("scripts/control_v24877_keyless_coverage_exact220.py"),
            Path("scripts/finalize_v24877_keyless_coverage_exact220.py"),
        )
    )
    return relatives


def dependency_manifest(root: Path) -> dict[str, str]:
    return {
        str(path): sha256(_ordinary_tracked(root, path))
        for path in sorted(_relatives(root, frozen=False), key=str)
    }


def frozen_dependency_manifest(root: Path) -> dict[str, str]:
    return {
        str(path): sha256(_ordinary_tracked(root, path))
        for path in sorted(_relatives(root, frozen=True), key=str)
    }


def _static_bindings() -> dict[str, str]:
    return {
        "runner_validate_envelope": "v24899_revision_parser_total_exact_task.validate_envelope",
        "runner_validate_integration_receipt": "v24898_revision_parser_total_integration.validate_integration_receipt",
        "runner_coverage_result_role": "v24898_revision_parser_total_integration.RESULT_ROLE",
        "runner_validate_bundle": "v24901_revision_parser_total_mapping_bundle.validate_bundle",
        "runner_validate_effect_receipt": "v24901_revision_parser_total_mapping_bundle.validate_effect_receipt",
        "runner_run_observed_bundle_subprocess": "v24903_revision_parser_total_subprocess_gate.run_observed_bundle_subprocess",
        "child_run_child_bundle": "v24902_revision_parser_total_child_runtime.run_child_bundle",
        "collector_validate_scheduler_result": "parser_total_isolated",
        "collector_coverage_totals": "parser_total_isolated",
        "collector_effect_totals": "parser_total_isolated",
    }


def _single_change() -> dict[str, Any]:
    return {
        "parent": parent.PROTOCOL_ID,
        "change": "revision_parser_totality_and_collector_binding",
        "runtime_policy_id": RUNTIME_POLICY_ID,
        "bundle_policy_id": BUNDLE_POLICY_ID,
        "child_policy_id": CHILD_POLICY_ID,
        "subprocess_gate_policy_id": GATE_POLICY_ID,
        "all_task_vector_model_search_budget_controller_and_concurrency_values_unchanged": True,
        "retry_resume_skip_or_selective_rerun": False,
    }


def _patch(root: Path, base: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(base))
    manifest = dependency_manifest(root)
    copied["role"] = ROLE
    copied["protocol_id"] = PROTOCOL_ID
    copied["parent_algorithm"] = {
        "path": str(PARENT_PROTOCOL),
        "sha256": sha256(root / PARENT_PROTOCOL),
        "protocol_id": parent.PROTOCOL_ID,
        "dependency_manifest_sha256": base["dependency_manifest_sha256"],
        "prior_prediction_result_score_or_evaluator_reused_by_forward": False,
    }
    copied["production_seam"] = {
        **copy.deepcopy(dict(base["production_seam"])),
        "coverage_policy": coverage_policy(),
        "reliability_gate": validate_reliability_gate(root),
    }
    copied["execution"]["output_root"] = str(OUTPUT_ROOT)
    copied["execution"]["parser_total_static_bindings"] = _static_bindings()
    copied["execution"]["parent_valid_parser_mismatch_identity_passthrough"] = True
    copied["single_change"] = _single_change()
    copied["dependency_manifest"] = manifest
    copied["dependency_manifest_sha256"] = payload_sha256(manifest)
    copied["authorization"] = {
        "preactivation_audit_generation": True,
        "execution_start_generation": False,
        "single_fresh_exact220_forward": False,
        "evaluator_call": False,
        "retry_resume_skip_or_selective_rerun": False,
    }
    copied.pop("protocol_payload_sha256", None)
    copied["protocol_payload_sha256"] = payload_sha256(copied)
    return copied


def build_protocol(
    root: Path, *, now: int, require_clean: bool = True,
    require_pristine: bool = True,
) -> dict[str, Any]:
    if require_clean and (
        _git(root, "status", "--porcelain")
        or _git(root, "rev-parse", "HEAD") != _git(root, "rev-parse", "target/main")
    ):
        raise RuntimeError("V2.49.05 protocol requires clean pushed HEAD")
    future = (PROTOCOL, PREAUDIT, EXECUTION_START, FORWARD_RESULT, FORWARD_AUDIT, OUTPUT_ROOT)
    if require_pristine and any(
        (root / path).exists() or (root / path).is_symlink() for path in future
    ):
        raise FileExistsError("V2.49.05 future surface exists")
    value = _patch(root, parent_contract(root))
    value["created_at_unix"] = int(now)
    value["git_head"] = _git(root, "rev-parse", "HEAD")
    value.pop("protocol_payload_sha256", None)
    value["protocol_payload_sha256"] = payload_sha256(value)
    return validate_protocol(root, value)


def _validate_common(
    root: Path, value: Mapping[str, Any], *, frozen: bool
) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("protocol_payload_sha256", None)
    base = parent_contract(root, frozen=frozen)
    manifest = frozen_dependency_manifest(root) if frozen else dependency_manifest(root)
    execution = copied.get("execution") or {}
    production = copied.get("production_seam") or {}
    if (
        copied.get("role") != ROLE
        or copied.get("protocol_id") != PROTOCOL_ID
        or seal != payload_sha256(unsigned)
        or copied.get("parent_algorithm") != {
            "path": str(PARENT_PROTOCOL),
            "sha256": sha256(root / PARENT_PROTOCOL),
            "protocol_id": parent.PROTOCOL_ID,
            "dependency_manifest_sha256": base["dependency_manifest_sha256"],
            "prior_prediction_result_score_or_evaluator_reused_by_forward": False,
        }
        or copied.get("task_contract", {}).get("runtime_input_keys")
        != ["opaque_id", "question"]
        or copied.get("task_contract", {}).get("selected_count") != 220
        or copied.get("dependency_manifest") != manifest
        or copied.get("dependency_manifest_sha256") != payload_sha256(manifest)
        or production.get("coverage_policy") != coverage_policy()
        or production.get("reliability_gate") != validate_reliability_gate(root)
        or execution.get("executor_concurrency") != 20
        or execution.get("model_slot_cap") != 8
        or execution.get("task_wall_seconds") != 240
        or execution.get("model") != MODEL
        or execution.get("search") != SEARCH
        or execution.get("two_wave_policy") != TWO_WAVE_POLICY
        or execution.get("protected_watchers") != protected_watcher_snapshot()
        or execution.get("output_root") != str(OUTPUT_ROOT)
        or execution.get("parser_total_static_bindings") != _static_bindings()
        or execution.get("parent_valid_parser_mismatch_identity_passthrough") is not True
        or copied.get("single_change") != _single_change()
        or copied.get("authorization") != {
            "preactivation_audit_generation": True,
            "execution_start_generation": False,
            "single_fresh_exact220_forward": False,
            "evaluator_call": False,
            "retry_resume_skip_or_selective_rerun": False,
        }
    ):
        raise RuntimeError("V2.49.05 protocol drifted")
    if not frozen:
        task_vector(root, copied)
    return copied


def validate_protocol(root: Path, value: Mapping[str, Any]) -> dict[str, Any]:
    return _validate_common(root, value, frozen=False)


def validate_frozen_protocol(root: Path, value: Mapping[str, Any]) -> dict[str, Any]:
    return _validate_common(root, value, frozen=True)


__all__ = [name for name in globals() if name.isupper()] + [
    "build_protocol", "coverage_policy", "dependency_manifest",
    "frozen_dependency_manifest", "parent_contract", "payload_sha256",
    "protected_watcher_snapshot", "sha256", "task_vector",
    "validate_frozen_protocol", "validate_protocol", "validate_reliability_gate",
]
