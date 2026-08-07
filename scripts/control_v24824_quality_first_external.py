#!/usr/bin/env python3
"""Build audit, protocol, and staged activation for V2.48.24."""

from __future__ import annotations

import argparse
import ast
import fcntl
import json
import os
import re
import socket
import subprocess
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24824_quality_first_external_contract as contract  # noqa: E402


TESTS = (
    (Path("tests/test_v24819_quality_first_controller.py"), 11),
    (Path("tests/test_v24823_quality_first_accounting.py"), 5),
    (Path("tests/test_v24824_quality_first_external.py"), 6),
)
EXPECTED_TESTS = 22
PRIVILEGED = frozenset(
    {
        "benchmark_question_type",
        "question_type",
        "task_category",
        "category",
        "split",
        "ground_truth",
        "gold",
        "answer_key",
        "mapping",
        "evaluator",
        "reward",
        "score",
    }
)
EVALUATOR_MARKERS = (
    "official_eval",
    "official_evaluator",
    "external_evaluator",
    "evaluator_mapping",
    "finalize_v24",
)
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}"
)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
        check=True,
    ).stdout.strip()


def _clean_pushed() -> None:
    if _git("status", "--porcelain") or _git("rev-parse", "HEAD") != _git(
        "rev-parse", "target/main"
    ):
        raise RuntimeError("V2.48.24 control requires clean pushed HEAD")


def _read(path: Path) -> dict[str, Any]:
    if (
        path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(ROOT.resolve())
    ):
        raise RuntimeError(f"V2.48.24 expected ordinary object: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.48.24 expected object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == contract.payload_sha256(unsigned)


def _publish(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def _run_tests() -> tuple[int, bool, list[dict[str, Any]]]:
    environment = {
        "HOME": os.environ.get("HOME", str(Path.home())),
        "USER": os.environ.get("USER", "azureuser"),
        "LOGNAME": os.environ.get("LOGNAME", "azureuser"),
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "PYTHONSAFEPATH": "1",
    }
    rows = []
    for path, expected in TESTS:
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
                path.name,
                "-v",
            ],
            cwd=ROOT,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=300,
            check=False,
        )
        match = re.search(r"Ran (\d+) tests?", completed.stdout)
        observed = int(match.group(1)) if match else 0
        rows.append(
            {
                "path": str(path),
                "expected": expected,
                "observed": observed,
                "passed": completed.returncode == 0 and observed == expected,
                "output_sha256": contract.payload_sha256(completed.stdout),
            }
        )
    total = sum(row["observed"] for row in rows)
    return total, total == EXPECTED_TESTS and all(row["passed"] for row in rows), rows


def _ast_findings() -> tuple[list[str], list[str], list[str]]:
    fields: list[str] = []
    imports: list[str] = []
    secrets: list[str] = []
    for relative in contract.RUNTIME_SOURCES:
        source = (ROOT / relative).read_text(encoding="utf-8")
        if SECRET.search(source):
            secrets.append(str(relative))
        tree = ast.parse(source)
        for node in ast.walk(tree):
            key = None
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in {"get", "pop", "setdefault"}
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                key = node.args[0].value.casefold()
            elif (
                isinstance(node, ast.Subscript)
                and isinstance(node.slice, ast.Constant)
                and isinstance(node.slice.value, str)
            ):
                key = node.slice.value.casefold()
            if key in PRIVILEGED and not (
                key == "score"
                and relative == Path("src/deepwide_agent/clients.py")
            ):
                fields.append(f"{relative}:{node.lineno}:{key}")
            names = (
                [alias.name for alias in node.names]
                if isinstance(node, ast.Import)
                else [node.module or "", *(alias.name for alias in node.names)]
                if isinstance(node, ast.ImportFrom)
                else []
            )
            for name in names:
                if any(marker in name.casefold() for marker in EVALUATOR_MARKERS):
                    imports.append(f"{relative}:{node.lineno}:{name}")
    return sorted(fields), sorted(imports), sorted(secrets)


def _endpoint() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", 9878), timeout=0.5):
            return True
    except OSError:
        return False


def _lease_inactive() -> bool:
    path = ROOT / contract.LEASE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("a+", encoding="utf-8") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        return True
    except (BlockingIOError, OSError):
        return False


def _active_conflicts() -> list[int]:
    completed = subprocess.run(
        ["ps", "-eo", "pid=,comm=,args="],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
        check=False,
    )
    markers = (
        contract.RUNNER_MARKER,
        contract.CHILD_MARKER,
        "scripts/run_official_eval_local.py",
    )
    output = []
    for line in completed.stdout.splitlines():
        parts = line.split(None, 2)
        if (
            len(parts) >= 3
            and "python" in parts[1].casefold()
            and any(marker in parts[2] for marker in markers)
        ):
            output.append(int(parts[0]))
    return sorted(output)


def _future_pristine(paths: tuple[Path, ...]) -> bool:
    return all(
        not (ROOT / path).exists() and not (ROOT / path).is_symlink()
        for path in paths
    )


def _visible_question(group: list[dict[str, str]]) -> str:
    countries = "\n".join(
        f"{index}. {item['name']} [{item['iso3']}]"
        for index, item in enumerate(group, 1)
    )
    columns = " | ".join(
        [
            "Country",
            *(
                f"{target['label']} [{target['indicator']}] @{target['year']}"
                for target in contract.TARGETS
            ),
        ]
    )
    return (
        "Use public web sources to return one Markdown table about these countries:\n"
        f"<COUNTRIES>\n{countries}\n</COUNTRIES>\n"
        "Please output one Markdown table with the columns, in this exact order:\n"
        f"{columns}\n"
        "Use the World Bank API values. Preserve the decimal representation returned by "
        "the official API. Use Unknown when unavailable. Return one table only."
    )


def _project_tasks(private: Mapping[str, Any]) -> list[dict[str, str]]:
    groups = private.get("groups")
    if not isinstance(groups, list) or len(groups) != contract.SELECTED_COUNT:
        raise RuntimeError("V2.48.24 private denominator drifted")
    tasks = []
    for index, group in enumerate(groups, 1):
        if not isinstance(group, list) or len(group) != 4:
            raise RuntimeError("V2.48.24 private group drifted")
        visible = []
        for item in group:
            if (
                not isinstance(item, Mapping)
                or not isinstance(item.get("name"), str)
                or not isinstance(item.get("iso3"), str)
            ):
                raise RuntimeError("V2.48.24 private identity drifted")
            visible.append({"name": item["name"], "iso3": item["iso3"]})
        tasks.append(
            {
                "opaque_id": f"task_{0x248240 + index:024x}",
                "question": _visible_question(visible),
            }
        )
    return contract.validate_task_vector(tasks)


def _valid_authority(path: Path, role: str) -> dict[str, Any]:
    value = _read(ROOT / path)
    if (
        value.get("role") != role
        or value.get("audit_valid") is not True
        or value.get("findings") != []
        or not _sealed(value, "audit_payload_sha256")
    ):
        raise RuntimeError(f"V2.48.24 authority drifted: {path}")
    return value


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    fields, imports, secrets = _ast_findings()
    observed, passed, suites = _run_tests()
    population = _valid_authority(
        contract.POPULATION_AUDIT, "v24822_population_publication_audit"
    )
    controller = _valid_authority(
        contract.CONTROLLER_AUDIT,
        "v24819_quality_first_controller_build_audit",
    )
    checks = {
        "population_audit_authorizes_protocol_design": population.get(
            "authorization", {}
        ).get("fresh_external_protocol_design")
        is True
        and population.get("authorization", {}).get("external_launch") is False,
        "controller_audit_authorizes_protocol_design": controller.get(
            "authorization", {}
        ).get("fresh_external_population_and_protocol_design")
        is True
        and controller.get("authorization", {}).get("external_launch") is False,
        "population_artifacts_present": (ROOT / contract.POPULATION_PRIVATE).is_file()
        and (ROOT / contract.POPULATION_DESIGN).is_file(),
        "focused_tests_passed": passed and observed == EXPECTED_TESTS,
        "runtime_label_blind": not fields and not imports and not secrets,
        "runtime_manifest_has_no_evaluation_path": all(
            path.parts[:1] != ("evaluation",) for path in contract.RUNTIME_SOURCES
        ),
        "quality_first_policy_has_no_calibration_or_entropy_weight": contract.policy_dict()
        == {
            "calibration_binding": {
                "artifact_path": "",
                "declared_artifact_sha256": "",
                "observed_artifact_sha256": "",
                "artifact_payload_sha256": "",
                "calibration_task_count": 0,
                "terminal_utility_observed": False,
                "heldout_validation_passed": False,
                "external_artifact_verified_before_runtime": False,
                "quality_cost_exchange_rate": 0.0,
            },
            "per_lookup_resource_units": 1.0,
            "minimum_net_value": 0.0,
            "information_gain_feature_weight": 0.0,
        },
        "future_surface_pristine": _future_pristine(
            (
                contract.BUILD_AUDIT,
                contract.PROTOCOL,
                contract.PREAUDIT,
                contract.ACTIVATION,
                contract.EXECUTION_START,
                contract.FORWARD_RESULT,
                contract.FORWARD_AUDIT,
                contract.OUTPUT_ROOT,
            )
        ),
    }
    value = {
        "artifact_version": 1,
        "role": "v24824_quality_first_external_build_audit",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git_head": _git("rev-parse", "HEAD"),
        "population_audit_sha256": contract.sha256(
            ROOT / contract.POPULATION_AUDIT
        ),
        "controller_audit_sha256": contract.sha256(
            ROOT / contract.CONTROLLER_AUDIT
        ),
        "source_manifest": {
            str(path): contract.sha256(ROOT / path)
            for path in (
                *contract.RUNTIME_SOURCES,
                Path("scripts/control_v24824_quality_first_external.py"),
                Path("tests/test_v24824_quality_first_external.py"),
                Path("scripts/audit_v24824_quality_first_external_forward.py"),
            )
        },
        "tests": {
            "expected": EXPECTED_TESTS,
            "observed": observed,
            "passed": passed,
            "suites": suites,
        },
        "label_blind_audit": {
            "privileged_accesses": fields,
            "evaluator_imports": imports,
            "credential_literal_hits": secrets,
            "passed": not fields and not imports and not secrets,
        },
        "checks": checks,
        "private_population_opened": False,
        "network_model_search_fetch_or_evaluator_called": False,
        "findings": sorted(name for name, okay in checks.items() if not okay),
        "authorization": {
            "protocol_generation": all(checks.values()),
            "preactivation_audit_generation": False,
            "single_external_forward": False,
            "evaluator": False,
            "public_dev64_or_exact220": False,
        },
    }
    value["audit_valid"] = not value["findings"]
    value["audit_payload_sha256"] = contract.payload_sha256(value)
    return value


def build_protocol(*, now: int | None = None) -> dict[str, Any]:
    build = _read(ROOT / contract.BUILD_AUDIT)
    if (
        build.get("audit_valid") is not True
        or build.get("findings") != []
        or not _sealed(build, "audit_payload_sha256")
        or build.get("authorization", {}).get("protocol_generation") is not True
    ):
        raise RuntimeError("V2.48.24 build authority drifted")
    private = _read(ROOT / contract.POPULATION_PRIVATE)
    public = _read(ROOT / contract.POPULATION_DESIGN)
    publication = _read(ROOT / contract.POPULATION_AUDIT)
    tasks = _project_tasks(private)
    manifest = contract.dependency_manifest(ROOT)
    counts = publication["counts"]
    value = {
        "artifact_version": 1,
        "role": "v24824_quality_first_external_preregistration",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git_head": _git("rev-parse", "HEAD"),
        "build_audit_sha256": contract.sha256(ROOT / contract.BUILD_AUDIT),
        "controller_build_audit_sha256": contract.sha256(
            ROOT / contract.CONTROLLER_AUDIT
        ),
        "population_binding": {
            "public_design_path": str(contract.POPULATION_DESIGN),
            "public_design_sha256": contract.sha256(
                ROOT / contract.POPULATION_DESIGN
            ),
            "publication_audit_path": str(contract.POPULATION_AUDIT),
            "publication_audit_sha256": contract.sha256(
                ROOT / contract.POPULATION_AUDIT
            ),
            "private_population_file_sha256": contract.sha256(
                ROOT / contract.POPULATION_PRIVATE
            ),
            "selected_tasks": counts["tasks"],
            "selected_entities": counts["selected_entities"],
            "selected_gold_cells": counts["selected_gold_cells"],
            "selected_target_pair_overlap": counts[
                "selected_target_pair_overlap"
            ],
            "selected_gold_cell_overlap": counts["selected_gold_cell_overlap"],
            "selected_entity_overlap": counts["selected_entity_overlap"],
            "entity_disjoint_claim": public["scope"]["entity_disjoint_claim"],
            "target_cell_disjoint_claim": public["scope"][
                "target_cell_disjoint_claim"
            ],
            "private_population_opened_only_by_protocol_builder": True,
            "private_record_or_value_projected_to_visible_tasks": False,
        },
        "visible_tasks": tasks,
        "task_contract": {
            "runtime_input_keys": ["opaque_id", "question"],
            "selected_count": contract.SELECTED_COUNT,
            "arm_count": contract.ARM_COUNT,
            "opaque_id_vector_sha256": contract.payload_sha256(
                [task["opaque_id"] for task in tasks]
            ),
            "visible_question_vector_sha256": contract.payload_sha256(
                [task["question"] for task in tasks]
            ),
        },
        "execution": {
            "executor_concurrency": contract.EXECUTOR_CONCURRENCY,
            "model_slot_cap": contract.MODEL_SLOT_CAP,
            "model": contract.MODEL,
            "search": contract.SEARCH,
            "limits": contract.LIMITS,
            "quality_first_policy": contract.policy_dict(),
            "three_arms": [
                "first_wave_only",
                "fixed_full_budget",
                "coverage_risk_adaptive",
            ],
            "shared_prefix_hard_barrier": True,
            "prefix_failure_projects_all_arms_to_same_failure": True,
            "mandatory_visible_cell_coverage_precedes_cost_stopping": True,
            "expected_adaptive_decision": "expand",
            "expected_adaptive_decision_count": contract.SELECTED_COUNT,
            "expected_adaptive_prediction_equals_fixed_full_count": contract.SELECTED_COUNT,
            "entropy_information_gain_feature_weight": 0.0,
            "entropy_assigns_signed_credit": False,
            "no_resume_retry_skip_or_selective_rerun": True,
            "protected_watchers": contract.protected_watcher_snapshot(),
        },
        "dependency_manifest": manifest,
        "dependency_manifest_sha256": contract.payload_sha256(manifest),
        "source_policy": {
            "runtime_reads_only_opaque_id_and_question": True,
            "runtime_dependency_manifest_contains_evaluation_path": False,
            "mapping_gold_category_question_type_split_evaluator_score_reward_read_by_forward": False,
            "private_population_gold_values_absent_from_protocol": True,
            "country_entity_overlap_disclosed_not_used_for_routing": True,
            "same_task_evaluator_feedback_used_for_forward": False,
            "entropy_or_signed_credit_validated_by_this_run": False,
        },
        "authorization": {
            "preactivation_audit_generation": True,
            "activation": False,
            "single_external_forward": False,
            "evaluator": False,
            "public_dev64_or_exact220": False,
        },
    }
    value["protocol_payload_sha256"] = contract.payload_sha256(value)
    return contract.validate_protocol(ROOT, value)


def _stage(kind: str, *, now: int | None = None) -> tuple[dict[str, Any], Path]:
    protocol = contract.validate_protocol(ROOT, _read(ROOT / contract.PROTOCOL))
    findings: list[str] = []
    if contract.protected_watcher_snapshot() != protocol["execution"][
        "protected_watchers"
    ]:
        findings.append("protected_watcher_drifted")
    if not _endpoint() or not _lease_inactive() or _active_conflicts():
        findings.append("runtime_not_ready")
    if kind == "audit":
        fields, imports, secrets = _ast_findings()
        observed, passed, suites = _run_tests()
        if not passed or observed != EXPECTED_TESTS or fields or imports or secrets:
            findings.append("tests_or_label_blind_audit_failed")
        if not _future_pristine(
            (
                contract.PREAUDIT,
                contract.ACTIVATION,
                contract.EXECUTION_START,
                contract.FORWARD_RESULT,
                contract.FORWARD_AUDIT,
                contract.OUTPUT_ROOT,
            )
        ):
            findings.append("future_surface_not_pristine")
        value = {
            "artifact_version": 1,
            "role": "v24824_quality_first_external_preactivation_audit",
            "protocol_id": contract.PROTOCOL_ID,
            "created_at_unix": int(time.time()) if now is None else int(now),
            "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
            "tests": {
                "expected": EXPECTED_TESTS,
                "observed": observed,
                "passed": passed,
                "suites": suites,
            },
            "label_blind_audit": {
                "privileged_accesses": fields,
                "evaluator_imports": imports,
                "credential_literal_hits": secrets,
            },
            "runtime": {
                "endpoint_reachable_without_request": _endpoint(),
                "shared_api_lease_inactive": _lease_inactive(),
                "active_conflicts": _active_conflicts(),
                "protected_watchers": contract.protected_watcher_snapshot(),
            },
            "private_population_gold_provenance_or_evaluator_opened_or_hashed": False,
            "network_model_search_fetch_or_evaluator_called": False,
            "findings": findings,
            "audit_valid": not findings,
            "authorization": {
                "activation_generation": not findings,
                "single_external_forward": False,
                "evaluator": False,
                "public_dev64_or_exact220": False,
            },
        }
        value["audit_payload_sha256"] = contract.payload_sha256(value)
        return value, contract.PREAUDIT
    audit = _read(ROOT / contract.PREAUDIT)
    if (
        audit.get("audit_valid") is not True
        or audit.get("findings") != []
        or not _sealed(audit, "audit_payload_sha256")
    ):
        findings.append("preactivation_chain_invalid")
    if kind == "activate":
        if not _future_pristine(
            (
                contract.ACTIVATION,
                contract.EXECUTION_START,
                contract.FORWARD_RESULT,
                contract.FORWARD_AUDIT,
                contract.OUTPUT_ROOT,
            )
        ):
            findings.append("future_surface_not_pristine")
        value = {
            "artifact_version": 1,
            "role": "v24824_quality_first_external_activation",
            "protocol_id": contract.PROTOCOL_ID,
            "created_at_unix": int(time.time()) if now is None else int(now),
            "status": "activated_not_started" if not findings else "rejected",
            "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
            "preactivation_audit_sha256": contract.sha256(ROOT / contract.PREAUDIT),
            "protected_watchers": contract.protected_watcher_snapshot(),
            "findings": findings,
            "private_population_gold_provenance_or_evaluator_opened_or_hashed": False,
            "network_model_search_fetch_or_evaluator_called": False,
            "authorization": {
                "execution_start_generation": not findings,
                "single_external_forward": False,
                "evaluator": False,
                "public_dev64_or_exact220": False,
            },
        }
        value["activation_payload_sha256"] = contract.payload_sha256(value)
        return value, contract.ACTIVATION
    activation = _read(ROOT / contract.ACTIVATION)
    if (
        activation.get("status") != "activated_not_started"
        or not _sealed(activation, "activation_payload_sha256")
    ):
        findings.append("activation_chain_invalid")
    if not _future_pristine(
        (
            contract.EXECUTION_START,
            contract.FORWARD_RESULT,
            contract.FORWARD_AUDIT,
            contract.OUTPUT_ROOT,
        )
    ):
        findings.append("future_surface_not_pristine")
    value = {
        "artifact_version": 1,
        "role": "v24824_quality_first_external_execution_start",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "authorized_not_started" if not findings else "rejected",
        "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
        "preactivation_audit_sha256": contract.sha256(ROOT / contract.PREAUDIT),
        "activation_sha256": contract.sha256(ROOT / contract.ACTIVATION),
        "protected_watchers": contract.protected_watcher_snapshot(),
        "findings": findings,
        "first_network_model_search_or_fetch_effect_started": False,
        "private_population_gold_provenance_or_evaluator_opened_or_hashed": False,
        "authorization": {
            "single_external_forward": not findings,
            "evaluator": False,
            "public_dev64_or_exact220": False,
            "retry_resume_skip_or_selective_rerun": False,
        },
    }
    value["execution_start_payload_sha256"] = contract.payload_sha256(value)
    return value, contract.EXECUTION_START


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command", choices=("build", "protocol", "audit", "activate", "start")
    )
    args = parser.parse_args()
    _clean_pushed()
    if args.command == "build":
        value, path = build_audit(), contract.BUILD_AUDIT
    elif args.command == "protocol":
        value, path = build_protocol(), contract.PROTOCOL
    else:
        value, path = _stage(args.command)
    if value.get("findings"):
        raise RuntimeError(
            f"V2.48.24 {args.command} rejected: {value['findings']}"
        )
    _publish(ROOT / path, value)
    print(
        json.dumps(
            {
                "path": str(path),
                "role": value["role"],
                "authorization": value["authorization"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
