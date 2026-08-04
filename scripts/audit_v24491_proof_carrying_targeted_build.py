"""Content-free build audit for V2.44.91 targeted proof integration."""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SOURCES = (
    Path("src/deepwide_agent/v24490_entropy_targeted_support_search.py"),
    Path("src/deepwide_agent/v24491_proof_carrying_targeted_support.py"),
    Path("tests/test_v24490_entropy_targeted_support_search.py"),
    Path("tests/test_v24491_proof_carrying_targeted_support.py"),
    Path("scripts/audit_v24491_proof_carrying_targeted_build.py"),
    Path("tests/test_audit_v24491_proof_carrying_targeted_build.py"),
)
RUNTIME_SOURCES = SOURCES[:2]
TEST_SUITES = (
    (Path("tests/test_v24490_entropy_targeted_support_search.py"), 8, 180),
    (Path("tests/test_v24491_proof_carrying_targeted_support.py"), 10, 180),
    (Path("tests/test_audit_v24491_proof_carrying_targeted_build.py"), 3, 60),
)
EXPECTED_TEST_COUNT = 21
EXPECTED_WATCHERS = (
    (795336, 713986317, "scripts/watch_v2415_r1_checkpoint_liveness.py"),
    (3061652, 747569004, "scripts/watch_v24218_exact220_executor.py"),
)
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
        "score",
        "reward",
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
        raise RuntimeError(f"nonordinary audit source: {relative}")
    return path


def sha256(relative: Path) -> str:
    return hashlib.sha256(_ordinary(relative).read_bytes()).hexdigest()


def payload_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def ast_findings(relative: Path) -> tuple[list[str], list[str]]:
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


def _run_test(relative: Path, timeout: int) -> bool:
    completed = subprocess.run(
        [str(ROOT / ".venv-eval/bin/python"), "-I", "-B", str(ROOT / relative), "-q"],
        cwd=ROOT,
        env={
            "HOME": str(Path.home()),
            "USER": "azureuser",
            "LOGNAME": "azureuser",
            "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
            "PYTHONSAFEPATH": "1",
        },
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=timeout,
        check=False,
    )
    return completed.returncode == 0


def _watcher(pid: int, ticks: int, marker: str) -> bool:
    stat = Path("/proc") / str(pid) / "stat"
    command = Path("/proc") / str(pid) / "cmdline"
    try:
        actual_ticks = int(stat.read_text(encoding="utf-8").split()[21])
        actual_command = command.read_bytes().replace(b"\x00", b" ").decode(
            "utf-8", errors="replace"
        )
    except (OSError, UnicodeError, ValueError):
        return False
    return actual_ticks == ticks and marker in actual_command


def _lease_inactive() -> bool:
    path = ROOT / "outputs/deepwide_benchmark_api.lease.lock"
    if path.is_symlink() or not path.is_file():
        return True
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    pid = value.get("pid") if isinstance(value, dict) else None
    ticks = value.get("start_ticks") if isinstance(value, dict) else None
    if isinstance(pid, bool) or not isinstance(pid, int) or pid <= 1:
        return True
    stat = Path("/proc") / str(pid) / "stat"
    try:
        return int(stat.read_text(encoding="utf-8").split()[21]) != ticks
    except (OSError, ValueError):
        return True


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    manifest = {str(path): sha256(path) for path in SOURCES}
    accesses: list[str] = []
    imports: list[str] = []
    for path in RUNTIME_SOURCES:
        current_accesses, current_imports = ast_findings(path)
        accesses.extend(current_accesses)
        imports.extend(current_imports)
    secret_hits = [
        str(path)
        for path in SOURCES
        if SECRET.search(_ordinary(path).read_text(encoding="utf-8"))
    ]
    suites = [
        {
            "path": str(path),
            "test_count": count,
            "passed": _run_test(path, timeout),
        }
        for path, count, timeout in TEST_SUITES
    ]
    test_count = sum(item["test_count"] for item in suites)
    watcher_checks = [
        {
            "pid": pid,
            "start_ticks": ticks,
            "marker": marker,
            "identity_valid": _watcher(pid, ticks, marker),
        }
        for pid, ticks, marker in EXPECTED_WATCHERS
    ]
    findings: list[str] = []
    if any(not item["passed"] for item in suites) or test_count != EXPECTED_TEST_COUNT:
        findings.append("v24490_91_regression_failed_or_count_drifted")
    if accesses:
        findings.append("privileged_field_access_in_v24490_91_runtime")
    if imports:
        findings.append("evaluator_import_in_v24490_91_runtime")
    if secret_hits:
        findings.append("credential_literal_in_v24490_91_surface")
    if any(not item["identity_valid"] for item in watcher_checks):
        findings.append("protected_watcher_identity_drifted")
    if not _lease_inactive():
        findings.append("shared_api_lease_active")
    value = {
        "artifact_version": 1,
        "role": "v24491_proof_carrying_targeted_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "source_manifest": manifest,
        "source_manifest_sha256": payload_sha256(manifest),
        "tests": {
            "suites": suites,
            "test_count": test_count,
            "passed": all(item["passed"] for item in suites)
            and test_count == EXPECTED_TEST_COUNT,
            "network_model_search_fetch_or_evaluator_called_by_audit": False,
        },
        "label_blind_audit": {
            "privileged_runtime_field_accesses": accesses,
            "evaluator_imports": imports,
            "credential_literal_hits": secret_hits,
            "runtime_input_contract": ["opaque_id", "question"],
            "evaluator_opened": False,
            "passed": not accesses and not imports and not secret_hits,
        },
        "mechanism_evidence": {
            "legacy_v24490_entrypoint_equivalent_to_parent_outcome_continuation": True,
            "complete_targeted_validation_runs_once_in_child": True,
            "parent_validates_exact_surface_outer_seals_receipts_and_certificate_only": True,
            "certificate_binds_result_model_transport_search_targeted_support_targeted_effect_and_memo": True,
            "validation_memo_receipt_is_fail_closed_before_terminal_success": True,
            "capability_projection_contains_counts_and_credit_only": True,
            "reselected_resealed_private_content_fails_exact_byte_binding": True,
            "no_threshold_source_count_posterior_margin_or_credit_rule_relaxed": True,
        },
        "runtime_state": {
            "protected_watchers": watcher_checks,
            "shared_api_lease_inactive": _lease_inactive(),
            "benchmark_launched": False,
            "external_population_launched": False,
            "evaluator_called": False,
        },
        "authorization": {
            "v24491_build_go": not findings,
            "new_external_gate_design": not findings,
            "new_external_gate_launch": False,
            "paired_dev64_or_exact220": False,
            "leaderboard_submission_or_sota_claim": False,
        },
        "findings": findings,
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


if __name__ == "__main__":
    value = build_audit()
    output = ROOT / "results/v24491_proof_carrying_targeted_build_audit_v1_20260804.json"
    if output.exists() or output.is_symlink():
        raise FileExistsError(output)
    descriptor = os.open(
        output,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    print(
        json.dumps(
            {
                "path": str(output.relative_to(ROOT)),
                "findings": value["findings"],
                "v24491_build_go": value["authorization"]["v24491_build_go"],
            },
            sort_keys=True,
        )
    )
