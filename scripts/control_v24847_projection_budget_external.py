#!/usr/bin/env python3
"""Build and authorize the V2.48.47 shared-prefix external gate."""

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

from deepwide_agent import v24847_projection_budget_external_contract as contract  # noqa: E402


POPULATION_PRIVATE = Path(
    "evaluation/v24829_target_cell_disjoint_worldbank_population_private_v1_20260807.json"
)
POPULATION_DESIGN = Path(
    "results/v24829_target_cell_disjoint_worldbank_population_design_v1_20260807.json"
)
POPULATION_AUDIT = Path(
    "results/v24829_population_publication_audit_v1_20260807.json"
)
PROFILE_AUDIT = Path(
    "results/v24846_atomic_table_header_30k_profile_build_audit_v1_20260808.json"
)


FORWARD_SOURCES = (
    Path("src/deepwide_agent/v24847_projection_budget_external_contract.py"),
    Path("src/deepwide_agent/v24846_atomic_table_header_30k_profile.py"),
    Path("src/deepwide_agent/v24842_atomic_table_header_closure.py"),
    Path("src/deepwide_agent/v24839_structure_preserving_projector.py"),
    Path("scripts/run_v24847_projection_budget_external_forward.py"),
    Path("scripts/run_v24847_projection_budget_external_task.py"),
    Path("scripts/deepwide_api_lease.py"),
)
CONTROL_SOURCES = (
    Path("scripts/control_v24847_projection_budget_external.py"),
    Path("tests/test_v24847_projection_budget_external.py"),
)
TESTS = (
    (Path("tests/test_v24847_projection_budget_external.py"), 10),
    (Path("tests/test_v24846_atomic_table_header_30k_profile.py"), 9),
    (Path("tests/test_v24842_atomic_table_header_closure.py"), 11),
)
PRIVILEGED = frozenset(
    {"category", "question_type", "task_category", "split", "ground_truth", "gold", "answer_key", "mapping", "evaluator", "score", "reward"}
)
SECRET = re.compile(r"(?<![A-Za-z0-9])(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}")


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
        timeout=20, check=True,
    ).stdout.strip()


def _clean_pushed() -> None:
    if _git("status", "--porcelain") or _git("rev-parse", "HEAD") != _git("rev-parse", "target/main"):
        raise RuntimeError("V2.48.47 requires clean pushed HEAD")


def _read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(ROOT.resolve()):
        raise RuntimeError(f"V2.48.47 expected ordinary object: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.48.47 expected object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == contract.payload_sha256(unsigned)


def _publish(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def _visible_question(group: list[Mapping[str, Any]]) -> str:
    countries = "\n".join(
        f"{index}. {item['name']} [{item['iso3']}]" for index, item in enumerate(group, 1)
    )
    columns = " | ".join(
        ["Country", *(f"{target['label']} [{target['indicator']}] @{target['year']}" for target in contract.TARGETS)]
    )
    return (
        "Use public web sources to return one Markdown table about these countries:\n"
        f"<COUNTRIES>\n{countries}\n</COUNTRIES>\n"
        "Please output one Markdown table with the columns, in this exact order:\n"
        f"{columns}\n"
        "Use the World Bank API values. Preserve the decimal representation returned by the official API. "
        "Use Unknown when unavailable. Return one table only."
    )


def project_tasks(private: Mapping[str, Any]) -> list[dict[str, str]]:
    groups = private.get("groups")
    if not isinstance(groups, list) or len(groups) != contract.SELECTED_COUNT:
        raise RuntimeError("V2.48.47 private denominator drifted")
    tasks = []
    for index, group in enumerate(groups, 1):
        if not isinstance(group, list) or len(group) != 4:
            raise RuntimeError("V2.48.47 private group drifted")
        visible = []
        for item in group:
            if not isinstance(item, Mapping) or not isinstance(item.get("name"), str) or not isinstance(item.get("iso3"), str):
                raise RuntimeError("V2.48.47 private identity drifted")
            visible.append({"name": item["name"], "iso3": item["iso3"]})
        tasks.append(
            {"opaque_id": f"task_{0x248470 + index:024x}", "question": _visible_question(visible)}
        )
    return contract.validate_task_vector(tasks)


def dependency_manifest() -> dict[str, str]:
    output = {}
    for relative in (*FORWARD_SOURCES, *CONTROL_SOURCES):
        path = ROOT / relative
        tracked = subprocess.run(
            ["git", "ls-files", "--error-unmatch", str(relative)], cwd=ROOT,
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, timeout=20, check=False,
        ).returncode == 0
        if (
            relative.is_absolute() or ".." in relative.parts
            or relative.parts[:1] in {("evaluation",), ("outputs",)}
            or path.is_symlink() or not path.is_file()
            or not path.resolve().is_relative_to(ROOT.resolve()) or not tracked
        ):
            raise RuntimeError(f"V2.48.47 runtime dependency drifted: {relative}")
        output[str(relative)] = contract.sha256(path)
    return dict(sorted(output.items()))


def _run_tests() -> tuple[int, bool, list[dict[str, Any]]]:
    environment = {
        "HOME": os.environ.get("HOME", str(Path.home())), "USER": os.environ.get("USER", "azureuser"),
        "LOGNAME": os.environ.get("LOGNAME", "azureuser"),
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1", "PYTHONSAFEPATH": "1",
    }
    rows = []
    for path, expected in TESTS:
        completed = subprocess.run(
            [str(ROOT / ".venv-eval/bin/python"), "-I", "-B", "-m", "unittest", "discover", "-s", "tests", "-p", path.name, "-v"],
            cwd=ROOT, env=environment, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=300, check=False,
        )
        match = re.search(r"Ran (\d+) tests?", completed.stdout)
        observed = int(match.group(1)) if match else 0
        rows.append({"path": str(path), "expected": expected, "observed": observed, "passed": completed.returncode == 0 and observed == expected, "output_sha256": contract.payload_sha256(completed.stdout)})
    return sum(row["observed"] for row in rows), all(row["passed"] for row in rows), rows


def _ast_findings() -> tuple[list[str], list[str]]:
    fields: list[str] = []
    secrets: list[str] = []
    for relative in FORWARD_SOURCES:
        source = (ROOT / relative).read_text(encoding="utf-8")
        if SECRET.search(source):
            secrets.append(str(relative))
        tree = ast.parse(source)
        for node in ast.walk(tree):
            key = None
            if (
                isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr in {"get", "pop", "setdefault"} and node.args
                and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str)
            ):
                key = node.args[0].value.casefold()
            elif isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str):
                key = node.slice.value.casefold()
            if key in PRIVILEGED:
                fields.append(f"{relative}:{node.lineno}:{key}")
    return sorted(fields), sorted(secrets)


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


def build_protocol(*, now: int | None = None) -> dict[str, Any]:
    private = _read(ROOT / POPULATION_PRIVATE)
    public = _read(ROOT / POPULATION_DESIGN)
    population_audit = _read(ROOT / POPULATION_AUDIT)
    profile_audit = _read(ROOT / PROFILE_AUDIT)
    if (
        population_audit.get("audit_valid") is not True or population_audit.get("findings") != []
        or profile_audit.get("audit_valid") is not True or profile_audit.get("findings") != []
        or public.get("selected_gold_cell_overlap_count") != 0
        or public.get("selected_target_pair_overlap_count") != 0
    ):
        raise RuntimeError("V2.48.47 authority drifted")
    tasks = project_tasks(private)
    manifest = dependency_manifest()
    value = {
        "artifact_version": 1, "role": "v24847_projection_budget_external_preregistration",
        "protocol_id": contract.PROTOCOL_ID, "created_at_unix": int(time.time()) if now is None else int(now),
        "git_head": _git("rev-parse", "HEAD"),
        "visible_tasks": tasks,
        "task_contract": {
            "runtime_input_keys": ["opaque_id", "question"], "selected_count": 32,
            "opaque_id_vector_sha256": contract.payload_sha256([task["opaque_id"] for task in tasks]),
            "visible_question_vector_sha256": contract.payload_sha256([task["question"] for task in tasks]),
        },
        "population_binding": {
            "public_design_sha256": contract.sha256(ROOT / POPULATION_DESIGN),
            "publication_audit_sha256": contract.sha256(ROOT / POPULATION_AUDIT),
            "private_population_sha256": contract.sha256(ROOT / POPULATION_PRIVATE),
            "tasks": 32, "entities": 128, "gold_cells": 256,
            "target_cell_overlap": 0, "target_pair_overlap": 0, "entity_overlap": 128,
            "target_cell_disjoint": True, "entity_disjoint": False,
        },
        "shared_prefix": {
            "source_urls": [target["indicator"] + "@" + target["year"] for target in contract.TARGETS],
            "source_url_literals_absent_from_forward_protocol": True,
            "two_official_snapshots_fetched_once_before_arm_branch": True,
            "raw_snapshot_bytes_frozen_before_arm_branch": True,
            "same_raw_page_vector_for_every_arm": True,
        },
        "execution": {
            "arms": list(contract.ARMS), "executor_concurrency": 16, "model_slot_cap": 8,
            "task_wall_seconds": 180, "model": contract.MODEL,
            "control_total_character_cap": 16_000, "candidate_total_character_cap": 30_000,
            "maximum_page_chars_both_arms": 5_000,
            "same_model_prompt_output_cap_and_concurrency": True,
            "prediction_freeze_before_private_evaluator": True,
            "failure_as_zero_no_resume_retry_skip_or_selective_rerun": True,
            "protected_watchers": contract.protected_watcher_snapshot(),
        },
        "dependency_manifest": manifest,
        "dependency_manifest_sha256": contract.payload_sha256(manifest),
        "forward_dependency_manifest": {
            str(path): manifest[str(path)] for path in FORWARD_SOURCES
        },
        "evaluator_source_physically_absent_from_forward_dependency_manifest": True,
        "source_policy": {
            "runtime_reads_only_opaque_id_question_and_frozen_raw_pages": True,
            "private_population_values_provenance_gold_or_evaluator_absent_from_forward": True,
            "mapping_category_question_type_split_score_reward_read_by_forward": False,
            "entropy_or_information_gain_assigns_credit": False,
        },
        "authorization": {
            "preactivation_audit_generation": True, "single_external_forward": False,
            "evaluator": False, "public_dev64_or_exact220": False,
        },
    }
    value["protocol_payload_sha256"] = contract.payload_sha256(value)
    return value


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    protocol = _read(ROOT / contract.PROTOCOL)
    fields, secrets = _ast_findings()
    observed, passed, suites = _run_tests()
    checks = {
        "protocol_sealed": _sealed(protocol, "protocol_payload_sha256"),
        "focused_tests_exact30": passed and observed == 30,
        "forward_privileged_field_access_zero": not fields,
        "credential_literal_zero": not secrets,
        "gpt56_endpoint_reachable_without_provider_request": _endpoint(),
        "shared_api_lease_inactive": _lease_inactive(),
        "protected_watchers_unchanged": contract.protected_watcher_snapshot() == protocol["execution"]["protected_watchers"],
        "future_surface_pristine": all(
            not (ROOT / path).exists() and not (ROOT / path).is_symlink()
            for path in (contract.PREAUDIT, contract.EXECUTION_START, contract.FORWARD_RESULT, contract.FORWARD_AUDIT, contract.OUTPUT_ROOT)
        ),
    }
    value = {
        "artifact_version": 1, "role": "v24847_projection_budget_external_preactivation_audit",
        "protocol_id": contract.PROTOCOL_ID, "created_at_unix": int(time.time()) if now is None else int(now),
        "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
        "tests": {"expected": 30, "observed": observed, "passed": passed, "suites": suites},
        "label_blind_audit": {"privileged_runtime_field_accesses": fields, "credential_literal_hits": secrets, "passed": not fields and not secrets},
        "checks": checks, "findings": sorted(name for name, okay in checks.items() if not okay),
        "authorization": {"execution_start_generation": all(checks.values()), "single_external_forward": False, "evaluator": False, "public_dev64_or_exact220": False},
    }
    value["audit_valid"] = not value["findings"]
    value["audit_payload_sha256"] = contract.payload_sha256(value)
    return value


def build_start(*, now: int | None = None) -> dict[str, Any]:
    protocol = _read(ROOT / contract.PROTOCOL)
    audit = _read(ROOT / contract.PREAUDIT)
    checks = {
        "protocol_sealed": _sealed(protocol, "protocol_payload_sha256"),
        "preactivation_audit_valid": audit.get("audit_valid") is True and audit.get("findings") == [] and _sealed(audit, "audit_payload_sha256"),
        "endpoint_reachable": _endpoint(), "lease_inactive": _lease_inactive(),
        "protected_watchers_unchanged": contract.protected_watcher_snapshot() == protocol["execution"]["protected_watchers"],
        "future_surface_pristine": all(
            not (ROOT / path).exists() and not (ROOT / path).is_symlink()
            for path in (contract.EXECUTION_START, contract.FORWARD_RESULT, contract.FORWARD_AUDIT, contract.OUTPUT_ROOT)
        ),
    }
    value = {
        "artifact_version": 1, "role": "v24847_projection_budget_external_execution_start",
        "protocol_id": contract.PROTOCOL_ID, "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "authorized_not_started" if all(checks.values()) else "rejected",
        "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
        "preactivation_audit_sha256": contract.sha256(ROOT / contract.PREAUDIT),
        "protected_watchers": contract.protected_watcher_snapshot(),
        "checks": checks, "findings": sorted(name for name, okay in checks.items() if not okay),
        "first_network_model_fetch_effect_started": False,
        "authorization": {"single_external_forward": all(checks.values()), "evaluator": False, "public_dev64_or_exact220": False, "retry_resume_skip_or_selective_rerun": False},
    }
    value["execution_start_payload_sha256"] = contract.payload_sha256(value)
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("protocol", "audit", "start"))
    args = parser.parse_args()
    _clean_pushed()
    if args.command == "protocol":
        value, path = build_protocol(), contract.PROTOCOL
    elif args.command == "audit":
        value, path = build_audit(), contract.PREAUDIT
    else:
        value, path = build_start(), contract.EXECUTION_START
    if value.get("findings"):
        raise RuntimeError(f"V2.48.47 {args.command} rejected: {value['findings']}")
    _publish(ROOT / path, value)
    print(json.dumps({"path": str(path), "role": value["role"], "authorization": value["authorization"]}, sort_keys=True))


if __name__ == "__main__":
    main()
