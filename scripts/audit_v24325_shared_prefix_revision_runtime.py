#!/usr/bin/env python3
"""Freeze the benchmark-external V2.43.25 shared-prefix revision runtime."""

from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24320_forward_contract import (  # noqa: E402
    payload_sha256,
    protected_watcher_snapshot,
    sha256,
)
from deepwide_agent.v24325_shared_prefix_revision_runtime import (  # noqa: E402
    run_v24325_task,
    run_v24325_total_task,
    validate_result,
)
from scripts.audit_v24187_phase_liveness import process_snapshot  # noqa: E402
from scripts.preregister_v24259_deterministic_normalizer_smoke import (  # noqa: E402
    _matching,
)
from test_v24325_shared_prefix_revision_runtime import (  # noqa: E402
    BASELINE_KNOWN,
    BASELINE_UNKNOWN,
    PLAN,
    TASK,
    Clock,
    FakeModel,
    FakeSearch,
    candidate,
    limits,
    proposal,
)


DATE = "20260803"
ROLE = "v24325_shared_prefix_revision_runtime_build_audit"
OUTPUT = Path(
    f"results/v24325_shared_prefix_revision_runtime_build_audit_v1_{DATE}.json"
)
PARENT = Path(
    f"results/v24324_shared_prefix_subprocess_build_audit_v1_{DATE}.json"
)
SOURCE_FILES = (
    "src/deepwide_agent/clients.py",
    "src/deepwide_agent/v24257_score_first_runtime.py",
    "src/deepwide_agent/v24259_deterministic_table_normalizer.py",
    "src/deepwide_agent/v24269_task_union_discovery.py",
    "src/deepwide_agent/v24286_visible_schema_runtime.py",
    "src/deepwide_agent/v24308_child_exit_observability.py",
    "src/deepwide_agent/v24323_shared_prefix_cell_entropy.py",
    "src/deepwide_agent/v24324_shared_prefix_runner.py",
    "src/deepwide_agent/v24325_shared_prefix_revision_runtime.py",
    "tests/test_v24325_shared_prefix_revision_runtime.py",
    "scripts/audit_v24325_shared_prefix_revision_runtime.py",
)
RUNTIME = Path("src/deepwide_agent/v24325_shared_prefix_revision_runtime.py")
TESTS = (
    ("test_v24325_shared_prefix_revision_runtime.py", 13),
    ("test_v24324_shared_prefix_subprocess.py", 5),
    ("test_v24323_shared_prefix_cell_entropy.py", 8),
    ("test_v24286_visible_schema_runtime.py", 6),
    ("test_v24269_task_union_discovery.py", 5),
    ("test_v24257_score_first_runtime.py", 11),
)
PRIVILEGED = frozenset(
    {
        "question_type",
        "task_category",
        "category",
        "split",
        "ground_truth",
        "gold",
        "answer_key",
        "mapping",
        "evaluator",
        "score",
        "reward",
    }
)
NETWORK_CONSTRUCTORS = frozenset(
    {
        "aiohttp",
        "httpx",
        "openai",
        "requests",
        "socket",
        "urllib3",
    }
)
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}"
)


def _ordinary(root: Path, relative: str | Path) -> Path:
    relative = Path(relative)
    path = root / relative
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(root)
    ):
        raise RuntimeError("V2.43.25 expected an ordinary repository file")
    return path


def _read(root: Path, relative: str | Path) -> dict[str, Any]:
    value = json.loads(_ordinary(root, relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.43.25 expected a JSON object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _field_accesses(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    output: list[str] = []
    for node in ast.walk(tree):
        key = None
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "get"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            key = node.args[0].value
        elif (
            isinstance(node, ast.Subscript)
            and isinstance(node.slice, ast.Constant)
            and isinstance(node.slice.value, str)
        ):
            key = node.slice.value
        if key is not None and key.casefold() in PRIVILEGED:
            output.append(f"{path.relative_to(ROOT)}:{node.lineno}:{key}")
    return output


def _network_constructor_imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    output: list[str] = []
    for node in ast.walk(tree):
        names: list[str] = []
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            names = [node.module]
        for name in names:
            if name.split(".", 1)[0] in NETWORK_CONSTRUCTORS:
                output.append(f"{path.relative_to(ROOT)}:{node.lineno}:{name}")
    return output


def _run_test(filename: str) -> bool:
    completed = subprocess.run(
        [
            str(ROOT / ".venv-eval/bin/python"),
            "-I",
            "-B",
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests",
            "-p",
            filename,
        ],
        cwd=ROOT,
        env={
            "HOME": str(Path.home()),
            "USER": os.environ.get("USER", "azureuser"),
            "LOGNAME": os.environ.get("LOGNAME", "azureuser"),
            "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
            "PYTHONSAFEPATH": "1",
        },
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=180,
        check=False,
    )
    return completed.returncode == 0


def _run(
    model: FakeModel,
    search: FakeSearch,
) -> dict[str, Any]:
    value = run_v24325_task(
        TASK,
        model=model,
        search=search,
        limits=limits(),
        monotonic=Clock(),
    )
    validate_result(value)
    return value


def _behavior_observation() -> dict[str, Any]:
    support = _run(
        FakeModel(
            [
                PLAN,
                BASELINE_UNKNOWN,
                proposal(candidate("2025"), ["R0001", "R0002"]),
            ]
        ),
        FakeSearch(),
    )
    support_receipt = support["shared_prefix_revision_receipt"]
    override = _run(
        FakeModel(
            [
                PLAN,
                BASELINE_KNOWN,
                proposal(
                    candidate("2025"), ["R0001", "R0002", "R0003"]
                ),
            ]
        ),
        FakeSearch(),
    )
    override_receipt = override["shared_prefix_revision_receipt"]
    fake_id = _run(
        FakeModel(
            [
                PLAN,
                BASELINE_UNKNOWN,
                proposal(candidate("2025"), ["R9998", "R9999"]),
            ]
        ),
        FakeSearch(),
    )
    same_host = _run(
        FakeModel(
            [
                PLAN,
                BASELINE_UNKNOWN,
                proposal(
                    candidate("2025"), ["R0001", "R0002", "R0003"]
                ),
            ]
        ),
        FakeSearch(one_reserve_host=True),
    )
    no_entity = _run(
        FakeModel(
            [
                PLAN,
                BASELINE_UNKNOWN,
                proposal(
                    candidate("2025"), ["R0001", "R0002", "R0003"]
                ),
            ]
        ),
        FakeSearch(reserve_mentions_entity=False),
    )
    recovery = _run(
        FakeModel([PLAN, RuntimeError("private"), BASELINE_KNOWN]),
        FakeSearch(),
    )
    recovery_receipt = recovery["shared_prefix_revision_receipt"]
    pre_provider = _run(
        FakeModel([PLAN, BASELINE_UNKNOWN], reject_index=3),
        FakeSearch(),
    )
    pre_provider_receipt = pre_provider["shared_prefix_revision_receipt"]
    total_model = FakeModel([KeyboardInterrupt()])
    total = run_v24325_total_task(
        TASK,
        model=total_model,
        search=FakeSearch(),
        limits=limits(),
        monotonic=Clock(),
    )
    validate_result(total)
    total_receipt = total["shared_prefix_revision_receipt"]
    return {
        "support_fill_unknown": {
            "candidate_changed": support["candidate_prediction_sha256"]
            != support["baseline_prediction_sha256"],
            "admitted_cell_changes": support_receipt["admitted_cell_changes"],
            "credited_entropy_positive": support_receipt[
                "credited_conditional_entropy_reduction_nats"
            ]
            > 0,
            "context_action": support_receipt["cell_admissions"][0][
                "admission_receipt"
            ]["context_action"],
        },
        "corroborated_override": {
            "candidate_changed": override["candidate_prediction_sha256"]
            != override["baseline_prediction_sha256"],
            "admitted_cell_changes": override_receipt[
                "admitted_cell_changes"
            ],
            "context_action": override_receipt["cell_admissions"][0][
                "admission_receipt"
            ]["context_action"],
        },
        "identity_quarantine": {
            "nonexistent_citations": fake_id["candidate_prediction_sha256"]
            == fake_id["baseline_prediction_sha256"],
            "same_host_repetition": same_host["candidate_prediction_sha256"]
            == same_host["baseline_prediction_sha256"],
            "value_without_local_entity": no_entity[
                "candidate_prediction_sha256"
            ]
            == no_entity["baseline_prediction_sha256"],
        },
        "single_shared_prefix_effects": {
            "prefix_producer_execution_count": support_receipt[
                "prefix_bundle"
            ]["producer_execution_count"],
            "logical_queries": support_receipt["core_logical_queries"]
            + support_receipt["reserve_logical_queries"],
            "search_client_calls": support_receipt[
                "core_search_provider_effects"
            ]
            + support_receipt["reserve_search_provider_effects"],
            "core_fetch_targets": support_receipt["core_fetch_targets"],
            "reserve_fetch_targets": support_receipt[
                "reserve_fetch_targets"
            ],
            "repeated_plan_search_fetch_effects": sum(
                support_receipt[name]
                for name in (
                    "repeated_plan_model_effects_by_branches",
                    "repeated_core_search_effects_by_branches",
                    "repeated_core_fetch_effects_by_branches",
                )
            ),
        },
        "baseline_recovery": {
            "model_effect_stages": recovery_receipt["model_effect_stages"],
            "reserve_fetch_targets": recovery_receipt[
                "reserve_fetch_targets"
            ],
            "candidate_identity_handoff": recovery_receipt[
                "candidate_identity_handoff"
            ],
        },
        "pre_provider_rejection": {
            "logical_model_admissions": pre_provider_receipt[
                "logical_model_admissions"
            ],
            "provider_model_requests": pre_provider_receipt[
                "provider_model_requests"
            ],
            "pre_provider_model_rejections": pre_provider_receipt[
                "pre_provider_model_rejections"
            ],
            "candidate_identity_handoff": pre_provider_receipt[
                "candidate_identity_handoff"
            ],
        },
        "total_fallback": {
            "effect_accounting_complete": total_receipt[
                "effect_accounting_complete"
            ],
            "unattributed_model_effects_lower_bound": total_receipt[
                "unattributed_model_effects_lower_bound"
            ],
            "candidate_identity_handoff": total_receipt[
                "candidate_identity_handoff"
            ],
        },
    }


def build(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    parent = _read(root, PARENT)
    if (
        parent.get("role") != "v24324_shared_prefix_subprocess_build_audit"
        or parent.get("audit_valid") is not True
        or parent.get("findings") != []
        or parent.get("authorization", {}).get(
            "fresh_uncontaminated_paired_benchmark_design"
        )
        is not True
        or parent.get("authorization", {}).get("benchmark_launch") is not False
        or not _sealed(parent, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.43.25 parent audit drifted")

    manifest = {
        relative: sha256(_ordinary(root, relative)) for relative in SOURCE_FILES
    }
    source_text = {
        relative: _ordinary(root, relative).read_text(encoding="utf-8")
        for relative in SOURCE_FILES
    }
    runtime_path = _ordinary(root, RUNTIME)
    accesses = sorted(_field_accesses(runtime_path))
    network_constructors = sorted(_network_constructor_imports(runtime_path))
    secret_hits = sorted(
        relative for relative, text in source_text.items() if SECRET.search(text)
    )
    test_results = [
        {"file": filename, "test_count": count, "passed": _run_test(filename)}
        for filename, count in TESTS
    ]
    behavior = _behavior_observation()
    watchers = protected_watcher_snapshot()
    process_present = bool(
        _matching(
            process_snapshot(),
            "test_v24325_shared_prefix_revision_runtime.py",
        )
    )
    findings: list[str] = []
    if accesses:
        findings.append("privileged_field_access_in_runtime")
    if network_constructors:
        findings.append("network_client_constructor_import_in_runtime")
    if secret_hits:
        findings.append("credential_literal_in_source_surface")
    if not all(item["passed"] for item in test_results):
        findings.append("focused_or_dependency_regression_failed")
    if watchers != parent.get("protected_watchers"):
        findings.append("protected_watcher_identity_drifted")
    if process_present:
        findings.append("test_or_runtime_process_remained_active")
    if behavior != {
        "support_fill_unknown": {
            "candidate_changed": True,
            "admitted_cell_changes": 1,
            "credited_entropy_positive": True,
            "context_action": "append_reserve_support",
        },
        "corroborated_override": {
            "candidate_changed": True,
            "admitted_cell_changes": 1,
            "context_action": "replace_core_after_corroborated_override",
        },
        "identity_quarantine": {
            "nonexistent_citations": True,
            "same_host_repetition": True,
            "value_without_local_entity": True,
        },
        "single_shared_prefix_effects": {
            "prefix_producer_execution_count": 1,
            "logical_queries": 4,
            "search_client_calls": 1,
            "core_fetch_targets": 7,
            "reserve_fetch_targets": 3,
            "repeated_plan_search_fetch_effects": 0,
        },
        "baseline_recovery": {
            "model_effect_stages": [
                "plan",
                "baseline_synthesis",
                "baseline_recovery",
            ],
            "reserve_fetch_targets": 0,
            "candidate_identity_handoff": True,
        },
        "pre_provider_rejection": {
            "logical_model_admissions": 3,
            "provider_model_requests": 2,
            "pre_provider_model_rejections": 1,
            "candidate_identity_handoff": True,
        },
        "total_fallback": {
            "effect_accounting_complete": False,
            "unattributed_model_effects_lower_bound": 1,
            "candidate_identity_handoff": True,
        },
    }:
        findings.append("behavior_observation_drifted")

    value = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parent_audit": {"path": str(PARENT), "sha256": sha256(root / PARENT)},
        "source_manifest": manifest,
        "source_manifest_sha256": payload_sha256(manifest),
        "focused_and_dependency_tests": test_results,
        "test_count": sum(count for _, count in TESTS),
        "behavior_observation": behavior,
        "privileged_field_accesses": accesses,
        "network_client_constructor_imports": network_constructors,
        "credential_literal_hits": secret_hits,
        "test_or_runtime_process_present": process_present,
        "protected_watchers": watchers,
        "external_effect_ledger": {
            "remote_network": 0,
            "model_provider": 0,
            "hosted_search": 0,
            "fetch": 0,
            "evaluator": 0,
        },
        "source_policy": {
            "runtime_boundary": ["opaque_id", "question"],
            "injected_model_and_search_clients_only": True,
            "runtime_constructs_no_network_client": True,
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
            "active_benchmark_or_watcher_signaled_restarted_or_modified": False,
        },
        "claim_scope": {
            "one_plan_and_one_shared_search_prefix_per_task": True,
            "seven_core_plus_three_reserve_fetch_target_partition": True,
            "baseline_recovery_and_candidate_revision_share_three_model_admission_cap": True,
            "candidate_cell_changes_bound_to_entity_local_independent_source_evidence": True,
            "conditional_entropy_reduction_used_as_admitted_cell_credit": True,
            "unsupported_or_failed_revision_is_byte_identical_handoff": True,
            "real_model_or_search_transport_tested": False,
            "production_subprocess_runner_integrated": False,
            "benchmark_quality_improvement": False,
            "reserve_effect_fully_causally_identified": False,
        },
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "production_runner_integration_design": not findings,
            "benchmark_launch": False,
            "additional_dev64_or_exact220": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    validate(value)
    return value


def validate(value: Mapping[str, Any]) -> None:
    if (
        value.get("artifact_version") != 1
        or value.get("role") != ROLE
        or value.get("findings") != []
        or value.get("audit_valid") is not True
        or value.get("test_count") != 48
        or not all(
            item.get("passed") is True
            for item in value.get("focused_and_dependency_tests", [])
        )
        or value.get("privileged_field_accesses") != []
        or value.get("network_client_constructor_imports") != []
        or value.get("credential_literal_hits") != []
        or value.get("test_or_runtime_process_present") is not False
        or value.get("external_effect_ledger")
        != {
            "remote_network": 0,
            "model_provider": 0,
            "hosted_search": 0,
            "fetch": 0,
            "evaluator": 0,
        }
        or value.get("authorization", {}).get(
            "production_runner_integration_design"
        )
        is not True
        or value.get("authorization", {}).get("benchmark_launch") is not False
        or not _sealed(value, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.43.25 audit drifted")


def publish(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    report = build()
    publish(ROOT / OUTPUT, report)
    print(
        json.dumps(
            {"path": str(OUTPUT), "audit_valid": report["audit_valid"]},
            sort_keys=True,
        )
    )
