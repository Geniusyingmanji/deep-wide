#!/usr/bin/env python3
"""Synthetic-only build audit for the V2.47.09 sparse World Bank adapter.

The mechanism probe uses 53 invented countries and four in-memory ZIP files.
It does not open benchmark questions or prediction rows and makes no network,
model, search, forward, evaluator, or Azure call.  Real visible tasks and
official World Bank downloads remain behind a later protocol and activation.
"""

from __future__ import annotations

import ast
import csv
import fcntl
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import time
import zipfile
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24709_sparse_worldbank_adapter as runtime  # noqa: E402


DATE = "20260806"
AUDIT = Path(f"results/v24710_sparse_worldbank_build_audit_v1_{DATE}.json")
DESIGN = Path(f"results/v24708_sparse_full220_exploratory_design_v1_{DATE}.json")
INCIDENT = Path(
    f"results/v24707_preimplementation_probe_contamination_audit_v1_{DATE}.json"
)
AUTHORITY = Path(f"results/v24706_full220_visible_authority_scope_audit_v1_{DATE}.json")
VISIBLE_MANIFEST = Path("outputs/runtime_manifest_v1_repro/manifest.jsonl")
CONTROL_PREDICTIONS = Path(
    "outputs/v24267_exact220_v1_20260802/runtime_predictions.jsonl"
)
CONTROL_FREEZE = Path("outputs/v24267_exact220_v1_20260802/prediction_freeze.json")
RUNTIME_SOURCE = Path("src/deepwide_agent/v24709_sparse_worldbank_adapter.py")
RUNTIME_TEST = Path("tests/test_v24709_sparse_worldbank_adapter.py")
AUDIT_SOURCE = Path("scripts/audit_v24710_sparse_worldbank_build.py")
AUDIT_TEST = Path("tests/test_audit_v24710_sparse_worldbank_build.py")
SOURCES = (
    RUNTIME_SOURCE,
    RUNTIME_TEST,
    AUDIT_SOURCE,
    AUDIT_TEST,
    DESIGN,
    INCIDENT,
    AUTHORITY,
)
EXPECTED_TEST_COUNT = 16
EXPECTED_WATCHERS = (
    (795336, 713986317, "scripts/watch_v2415_r1_checkpoint_liveness.py"),
    (3061652, 747569004, "scripts/watch_v24218_exact220_executor.py"),
)
LEASE = Path("outputs/deepwide_benchmark_api.lease.lock")
PRIVILEGED = frozenset(
    {
        "answer",
        "answer_key",
        "category",
        "evaluation",
        "evaluator",
        "evaluator_mapping",
        "gold",
        "ground_truth",
        "instance_id",
        "question_type",
        "reward",
        "score",
        "split",
        "task_category",
        "topic",
    }
)
EVALUATOR_IMPORT_MARKERS = (
    "official_eval",
    "official_evaluator",
    "finalize_v24",
    "evaluator_mapping",
)
SECRET_PREFIXES = ("gh" + "p_", "github_" + "pat_", "tvly-" + "dev-", "s" + "k-")
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:"
    + "|".join(re.escape(value) for value in SECRET_PREFIXES)
    + r")[A-Za-z0-9_-]{16,}"
)


def _ordinary(relative: Path) -> Path:
    path = ROOT / relative
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(ROOT.resolve())
    ):
        raise RuntimeError(f"V2.47.10 expected repository file: {relative}")
    return path


def _sha256(relative: Path) -> str:
    digest = hashlib.sha256()
    with _ordinary(relative).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read(relative: Path) -> dict[str, Any]:
    value = json.loads(_ordinary(relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.47.10 expected JSON object")
    return value


def _read_jsonl(relative: Path) -> list[dict[str, Any]]:
    rows = [
        json.loads(line)
        for line in _ordinary(relative).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if any(not isinstance(row, dict) for row in rows):
        raise RuntimeError("V2.47.10 expected JSONL objects")
    return rows


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
    ).stdout.strip()


def _tracked(relative: Path) -> bool:
    return subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(relative)],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=20,
        check=False,
    ).returncode == 0


def _watcher(pid: int, ticks: int, marker: str) -> bool:
    stat = Path("/proc") / str(pid) / "stat"
    command = Path("/proc") / str(pid) / "cmdline"
    try:
        raw = stat.read_text(encoding="utf-8")
        suffix = raw[raw.rfind(")") + 2 :].split()
        actual_ticks = int(suffix[19])
        actual_command = command.read_bytes().replace(b"\x00", b" ").decode(
            errors="replace"
        )
    except (OSError, UnicodeError, ValueError):
        return False
    return actual_ticks == ticks and marker in actual_command


def _lease_inactive() -> bool:
    path = ROOT / LEASE
    if path.is_symlink():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("a+", encoding="utf-8") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        return True
    except (BlockingIOError, OSError):
        return False


def _active() -> bool:
    completed = subprocess.run(
        ["ps", "-eo", "cmd="],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
        check=False,
    )
    return any(
        "run_v247" in line or "v24709_sparse_worldbank_adapter" in line
        for line in completed.stdout.splitlines()
        if "ps -eo" not in line
        and "audit_v24710_sparse_worldbank_build.py" not in line
        and "test_audit_v24710_sparse_worldbank_build.py" not in line
    )


def ast_findings(relative: Path = RUNTIME_SOURCE) -> tuple[list[str], list[str]]:
    tree = ast.parse(_ordinary(relative).read_text(encoding="utf-8"))
    accesses: list[str] = []
    imports: list[str] = []
    for node in ast.walk(tree):
        key: str | None = None
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in {"get", "pop", "setdefault"}
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
            accesses.append(f"{relative}:{node.lineno}:{key}")
        names: list[str] = []
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            names = [node.module or "", *(alias.name for alias in node.names)]
        for name in names:
            if any(marker in name.casefold() for marker in EVALUATOR_IMPORT_MARKERS):
                imports.append(f"{relative}:{node.lineno}:{name}")
    return sorted(accesses), sorted(imports)


def _run_tests() -> tuple[bool, int]:
    environment = {
        "HOME": os.environ.get("HOME", str(Path.home())),
        "USER": os.environ.get("USER", "azureuser"),
        "LOGNAME": os.environ.get("LOGNAME", "azureuser"),
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "PYTHONSAFEPATH": "1",
    }
    total = 0
    passed = True
    for test in (RUNTIME_TEST, AUDIT_TEST):
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
                test.name,
            ],
            cwd=ROOT,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=60,
            check=False,
        )
        match = re.search(r"Ran (\d+) tests?", completed.stdout)
        observed = int(match.group(1)) if match else 0
        total += observed
        passed = passed and completed.returncode == 0 and observed > 0
    return passed and total == EXPECTED_TEST_COUNT, total


def _parents_valid() -> bool:
    design = _read(DESIGN)
    incident = _read(INCIDENT)
    authority = _read(AUTHORITY)
    freeze = _read(CONTROL_FREEZE)
    return bool(
        design.get("role") == "v24708_sparse_full220_exploratory_design"
        and design.get("status") == "build_only_authorized"
        and design.get("authorization")
        == {
            "activation_or_benchmark_forward": False,
            "build_only_runtime_and_tests": True,
            "evaluator": False,
            "leaderboard_or_sota": False,
        }
        and design.get("baseline", {}).get("runtime_predictions_sha256")
        == _sha256(CONTROL_PREDICTIONS)
        and design.get("baseline", {}).get("prediction_freeze_sha256")
        == _sha256(CONTROL_FREEZE)
        and design.get("parents", {}).get("visible_manifest_sha256")
        == _sha256(VISIBLE_MANIFEST)
        and design.get("contamination_limit", {}).get("incident_sha256")
        == _sha256(INCIDENT)
        and incident.get("role")
        == "v24707_preimplementation_probe_contamination_audit"
        and incident.get("authorization", {}).get(
            "benchmark_forward_or_evaluator_launch"
        )
        is False
        and incident.get("authorization", {}).get(
            "exploratory_label_blind_runtime_build"
        )
        is True
        and authority.get("role")
        == "v24706_full220_visible_authority_scope_audit"
        and authority.get("audit_valid") is True
        and authority.get("coverage", {}).get("adapter_route_eligible_task_count")
        == 1
        and freeze.get("terminal") == 220
        and freeze.get("mapping_query_answer_gold_or_evaluator_opened_or_hashed")
        is False
    )


def _synthetic_code(index: int) -> str:
    return "".join(
        chr(ord("A") + value)
        for value in (index // (26 * 26), (index // 26) % 26, index % 26)
    )


def _synthetic_archive(spec: runtime.TargetSpec) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(["Data Source", "World Development Indicators", ""])
    writer.writerow([])
    writer.writerow(["Last Updated Date", "2026-01-01", ""])
    writer.writerow([])
    writer.writerow(
        [
            "Country Name",
            "Country Code",
            "Indicator Name",
            "Indicator Code",
            spec.year,
            "",
        ]
    )
    values = {
        "AG.SRF.TOTL.K2": "1000.5",
        "EN.POP.DNST": "50.5",
        "SP.POP.TOTL": "1500500",
        "TG.VAL.TOTL.GD.ZS": "25.25",
    }
    for index in range(runtime.EXPECTED_ROW_COUNT):
        writer.writerow(
            [
                f"Synthetic Nation {index + 1}",
                _synthetic_code(index),
                "Synthetic indicator",
                spec.indicator,
                values[spec.indicator],
                "",
            ]
        )
    raw = io.BytesIO()
    with zipfile.ZipFile(raw, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            f"API_{spec.indicator}_DS2_en_csv_v2_1.csv", output.getvalue()
        )
    return raw.getvalue()


def synthetic_mechanism_probe() -> dict[str, Any]:
    question = (
        "According to the statistics of the World Bank, return surface area using "
        "2022 statistics rounded to an integer, population density using 2022 "
        "statistics rounded to an integer, total population in thousand using 2023 "
        "statistics rounded to an integer, and merchandise trade using 2023 "
        "statistics rounded to one decimal place.\n\n"
        "Please output one Markdown table. The column names in the table are: "
        + ", ".join(runtime.EXPECTED_COLUMNS)
        + "."
    )
    rows = [
        [
            f"Synthetic Nation {index + 1}",
            f"Synthetic Capital {index + 1}",
            "Unknown",
            "Unknown",
            "Unknown",
            "Unknown",
        ]
        for index in range(runtime.EXPECTED_ROW_COUNT)
    ]
    control = (
        "```markdown\n| "
        + " | ".join(runtime.EXPECTED_COLUMNS)
        + " |\n| "
        + " | ".join("---" for _ in runtime.EXPECTED_COLUMNS)
        + " |\n"
        + "\n".join("| " + " | ".join(row) + " |" for row in rows)
        + "\n```"
    )
    bundle = {spec.url: _synthetic_archive(spec) for spec in runtime.TARGETS}
    callback_count = 0

    def fetch(requested: tuple[str, ...]) -> Mapping[str, bytes]:
        nonlocal callback_count
        if requested != tuple(spec.url for spec in runtime.TARGETS):
            raise RuntimeError("V2.47.10 synthetic request vector drifted")
        callback_count += 1
        return bundle

    result = runtime.run_sparse_adapter(
        {"opaque_id": "task_" + "0" * 24, "question": question},
        control,
        fetch,
    )
    return {
        "population": "benchmark_external_synthetic",
        "synthetic_tasks": 1,
        "route_eligible_tasks": int(result["route_eligible"]),
        "applied_tasks": int(result["applied"]),
        "official_target_value_count": int(result["target_value_count"]),
        "changed_numeric_cell_count": int(result["changed_cell_count"]),
        "adapter_bulk_callback_invocations": callback_count,
        "caller_supplied_archive_count": len(bundle),
        "network_bulk_download_count": 0,
        "task_question_opaque_id_country_capital_value_prediction_or_candidate_persisted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "network_model_search_benchmark_forward_evaluator_or_azure_called": False,
    }


def probe_valid(probe: Mapping[str, Any]) -> bool:
    return bool(
        probe.get("population") == "benchmark_external_synthetic"
        and probe.get("synthetic_tasks") == 1
        and probe.get("route_eligible_tasks") == 1
        and probe.get("applied_tasks") == 1
        and probe.get("official_target_value_count") == 212
        and probe.get("changed_numeric_cell_count") == 212
        and probe.get("adapter_bulk_callback_invocations") == 1
        and probe.get("caller_supplied_archive_count") == 4
        and probe.get("network_bulk_download_count") == 0
        and probe.get(
            "task_question_opaque_id_country_capital_value_prediction_or_candidate_persisted"
        )
        is False
        and probe.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is False
        and probe.get(
            "network_model_search_benchmark_forward_evaluator_or_azure_called"
        )
        is False
    )


def build_audit(
    *,
    now: int | None = None,
    probe_fn: Callable[[], dict[str, Any]] = synthetic_mechanism_probe,
) -> dict[str, Any]:
    manifest = {str(path): _sha256(path) for path in SOURCES}
    accesses, imports = ast_findings()
    secret_hits = [
        str(path)
        for path in SOURCES
        if SECRET.search(_ordinary(path).read_text(encoding="utf-8"))
    ]
    tests_passed, test_count = _run_tests()
    head = _git("rev-parse", "HEAD")
    remote = _git("rev-parse", "target/main")
    clean = _git("status", "--porcelain") == ""
    tracked = all(_tracked(path) for path in SOURCES)
    parents = _parents_valid()
    watchers = [
        {
            "pid": pid,
            "start_ticks": ticks,
            "marker": marker,
            "identity_valid": _watcher(pid, ticks, marker),
        }
        for pid, ticks, marker in EXPECTED_WATCHERS
    ]
    lease_inactive = _lease_inactive()
    active = _active()
    probe: dict[str, Any]
    try:
        probe = probe_fn()
    except Exception as exc:
        probe = {
            "probe_failed": True,
            "coarse_exception_type": type(exc).__name__,
            "task_question_opaque_id_country_capital_value_prediction_or_candidate_persisted": False,
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
            "network_model_search_benchmark_forward_evaluator_or_azure_called": False,
        }
    mechanism_valid = probe_valid(probe)
    findings: list[str] = []
    if head != remote:
        findings.append("source_commit_not_pushed")
    if not clean:
        findings.append("source_worktree_not_clean")
    if not tracked:
        findings.append("source_or_parent_not_tracked")
    if not parents:
        findings.append("v24706_v24707_v24708_or_control_parent_drifted")
    if not tests_passed or test_count != EXPECTED_TEST_COUNT:
        findings.append("v24709_regression_failed")
    if accesses:
        findings.append("privileged_runtime_field_access")
    if imports:
        findings.append("evaluator_import_in_runtime")
    if secret_hits:
        findings.append("credential_literal_in_build_surface")
    if any(not item["identity_valid"] for item in watchers):
        findings.append("protected_watcher_identity_drifted")
    if not lease_inactive:
        findings.append("shared_api_lease_active")
    if active:
        findings.append("v247_forward_process_active")
    if not mechanism_valid:
        findings.append("synthetic_mechanism_probe_failed")
    value = {
        "artifact_version": 1,
        "role": "v24710_sparse_worldbank_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parents": {
            "design_path": str(DESIGN),
            "design_sha256": _sha256(DESIGN),
            "incident_path": str(INCIDENT),
            "incident_sha256": _sha256(INCIDENT),
            "authority_scope_path": str(AUTHORITY),
            "authority_scope_sha256": _sha256(AUTHORITY),
            "control_prediction_freeze_sha256": _sha256(CONTROL_FREEZE),
            "valid": parents,
        },
        "mechanism": {
            "runtime_policy": runtime.POLICY_ID,
            "fixed_full_denominator": 220,
            "maximum_treated_tasks": 1,
            "official_bulk_download_cap": 4,
            "per_country_target_requests": 0,
            "model_or_search_calls": 0,
            "all_212_target_values_required_before_task_application": True,
            "country_and_capital_cells_preserved": True,
            "entropy_credit_assigned": False,
            "synthetic_probe": probe,
            "synthetic_probe_valid": mechanism_valid,
        },
        "source_manifest": manifest,
        "source_manifest_sha256": runtime.payload_sha256(manifest),
        "git": {
            "head": head,
            "target_main": remote,
            "head_equals_target_main": head == remote,
            "worktree_clean": clean,
            "all_sources_and_parents_tracked": tracked,
        },
        "tests": {
            "expected": EXPECTED_TEST_COUNT,
            "observed": test_count,
            "passed": tests_passed and test_count == EXPECTED_TEST_COUNT,
            "synthetic_only": True,
        },
        "label_blind_audit": {
            "runtime_input_contract": ["opaque_id", "question"],
            "privileged_runtime_field_accesses": accesses,
            "evaluator_imports": imports,
            "credential_literal_hits": secret_hits,
            "raw_benchmark_dataset_in_dependency_manifest": False,
            "mapping_gold_evaluator_score_or_reward_in_dependency_manifest": False,
            "passed": not accesses and not imports and not secret_hits,
        },
        "runtime_state": {
            "protected_watchers": watchers,
            "protected_watchers_unchanged": all(
                item["identity_valid"] for item in watchers
            ),
            "shared_api_lease_inactive": lease_inactive,
            "v247_forward_process_active": active,
        },
        "source_policy": {
            "visible_manifest_or_frozen_control_prediction_rows_opened_by_audit": False,
            "visible_manifest_and_control_prediction_files_hashed_only": True,
            "raw_benchmark_dataset_mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
            "candidate_prediction_or_candidate_value_persisted": False,
            "official_worldbank_or_other_network_called": False,
            "model_search_benchmark_forward_evaluator_or_azure_called": False,
            "exploratory_due_to_v24707_preimplementation_incident": True,
        },
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "sparse_full220_forward_contract_and_protocol_design": not findings,
            "activation_or_forward_launch": False,
            "evaluator": False,
            "avg_at_4": False,
            "leaderboard_or_sota": False,
        },
    }
    value["audit_payload_sha256"] = runtime.payload_sha256(value)
    return value


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    unsigned = dict(value)
    seal = unsigned.pop("audit_payload_sha256", None)
    if (
        value.get("role") != "v24710_sparse_worldbank_build_audit"
        or value.get("audit_valid") is not True
        or value.get("findings") != []
        or value.get("parents", {}).get("valid") is not True
        or value.get("mechanism", {}).get("synthetic_probe_valid") is not True
        or not probe_valid(value.get("mechanism", {}).get("synthetic_probe", {}))
        or value.get("tests", {}).get("passed") is not True
        or value.get("tests", {}).get("observed") != EXPECTED_TEST_COUNT
        or value.get("label_blind_audit", {}).get("passed") is not True
        or value.get("runtime_state", {}).get("protected_watchers_unchanged")
        is not True
        or value.get("runtime_state", {}).get("shared_api_lease_inactive")
        is not True
        or value.get("runtime_state", {}).get("v247_forward_process_active")
        is not False
        or value.get("authorization")
        != {
            "sparse_full220_forward_contract_and_protocol_design": True,
            "activation_or_forward_launch": False,
            "evaluator": False,
            "avg_at_4": False,
            "leaderboard_or_sota": False,
        }
        or seal != runtime.payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.47.10 build audit drifted")
    return dict(value)


def publish_new(path: Path, value: Mapping[str, Any]) -> None:
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


if __name__ == "__main__":
    audit = build_audit()
    validate_audit(audit)
    publish_new(ROOT / AUDIT, audit)
    print(
        json.dumps(
            {
                "path": str(AUDIT),
                "audit_valid": audit["audit_valid"],
                "findings": audit["findings"],
                "synthetic_probe": {
                    key: audit["mechanism"]["synthetic_probe"][key]
                    for key in (
                        "synthetic_tasks",
                        "route_eligible_tasks",
                        "applied_tasks",
                        "official_target_value_count",
                        "changed_numeric_cell_count",
                    )
                },
            },
            sort_keys=True,
        )
    )
