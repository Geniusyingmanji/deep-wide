#!/usr/bin/env python3
"""Strict label-blind preactivation audit for V2.46.35 exact-220."""

from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24635_exact220_contract import (  # noqa: E402
    ACTIVATION, CAPACITY_AUDIT, CAPACITY_DECISION, CAPACITY_RESULT,
    CHILD_MARKER, EXECUTION_START, FORWARD_CONTRACT, FORWARD_RESULT,
    OUTPUT_ROOT, PREAUDIT, PREDECESSOR_FORWARD_CONTRACT, PREDECESSOR_PREAUDIT,
    PROTOCOL_ID, RUNNER_MARKER, payload_sha256, protected_watcher_snapshot,
    read_object, sha256, validate_forward_contract,
)
from scripts.audit_v24195_lease_owner_compatibility import lease_observation  # noqa: E402
from scripts.preregister_v24635_exact220 import publish_new  # noqa: E402


FORBIDDEN = frozenset(
    {"category", "question_type", "task_category", "split", "ground_truth",
     "gold", "answer_key", "mapping", "evaluator", "score", "reward"}
)
SECRET = re.compile(r"(?<![A-Za-z0-9])(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}")
TESTS = (
    "test_v24635_exact220.py",
    "test_v24630_thin_backfill_search.py",
    "test_v24629_backfill_runner_integration.py",
    "test_v24628_backfill_search_integration.py",
    "test_v24627_same_response_citation_title_backfill.py",
    "test_v24319_runner_integration.py",
    "test_v24468_total_wall_transport.py",
)

EVALUATOR_TARGETS = (
    "run_official_eval_local",
    "evaluator_mapping",
    "finalize_fullset_rollout",
)
PROCESS_CALLS = frozenset(
    {
        "subprocess.run",
        "subprocess.popen",
        "subprocess.call",
        "subprocess.check_call",
        "subprocess.check_output",
        "os.system",
        "os.popen",
        "os.execl",
        "os.execle",
        "os.execlp",
        "os.execlpe",
        "os.execv",
        "os.execve",
        "os.execvp",
        "os.execvpe",
        "os.spawnl",
        "os.spawnle",
        "os.spawnlp",
        "os.spawnlpe",
        "os.spawnv",
        "os.spawnve",
        "os.spawnvp",
        "os.spawnvpe",
        "asyncio.create_subprocess_exec",
        "asyncio.create_subprocess_shell",
    }
)
DYNAMIC_IMPORT_CALLS = frozenset(
    {"importlib.import_module", "builtins.__import__", "__import__", "runpy.run_module", "runpy.run_path"}
)
RESOURCE_CALL_SUFFIXES = frozenset(
    {"open", "read_text", "read_bytes", "write_text", "write_bytes", "unlink", "rename", "replace"}
)


def _accesses(path: Path, root: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    output: list[str] = []
    for node in ast.walk(tree):
        key = None
        if (
            isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and node.func.attr in {"get", "pop", "setdefault"} and node.args
            and isinstance(node.args[0], ast.Constant)
        ):
            key = node.args[0].value
        elif isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
            key = node.slice.value
        if isinstance(key, str) and key.casefold() in FORBIDDEN:
            output.append(f"{path.relative_to(root)}:{node.lineno}:{key}")
    return output


def _dotted_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _dotted_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    return None


def _literal_strings(node: ast.AST, bindings: dict[str, set[str]]) -> set[str]:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return {node.value}
    if isinstance(node, ast.Name):
        return set(bindings.get(node.id, set()))
    if isinstance(node, ast.JoinedStr):
        values = {
            part.value
            for part in node.values
            if isinstance(part, ast.Constant) and isinstance(part.value, str)
        }
        return {"".join(values)} if values else set()
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        return set().union(*(_literal_strings(item, bindings) for item in node.elts)) if node.elts else set()
    if isinstance(node, ast.Dict):
        parts = [item for item in (*node.keys, *node.values) if item is not None]
        return set().union(*(_literal_strings(item, bindings) for item in parts)) if parts else set()
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = _literal_strings(node.left, bindings)
        right = _literal_strings(node.right, bindings)
        if left and right:
            return {a + b for a in left for b in right}
    if isinstance(node, ast.Call):
        parts = [*node.args, *(item.value for item in node.keywords)]
        return set().union(*(_literal_strings(item, bindings) for item in parts)) if parts else set()
    return set()


def _is_evaluator_target(value: str) -> bool:
    normalized = value.casefold().replace("\\", "/").replace("-", "_")
    return any(marker in normalized for marker in EVALUATOR_TARGETS)


def _evaluator_capabilities(path: Path, root: Path) -> list[str]:
    """Report semantic evaluator imports/effects, not inert process-marker literals."""

    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    aliases: dict[str, str] = {}
    bindings: dict[str, set[str]] = {}
    findings: list[str] = []
    relative = path.relative_to(root)

    def emit(node: ast.AST, kind: str, target: str) -> None:
        findings.append(f"{relative}:{getattr(node, 'lineno', 0)}:{kind}:{target}")

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for item in node.names:
                aliases[item.asname or item.name.split(".")[0]] = item.name
                if _is_evaluator_target(item.name):
                    emit(node, "import", item.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for item in node.names:
                target = f"{module}.{item.name}".strip(".")
                aliases[item.asname or item.name] = target
                if _is_evaluator_target(target):
                    emit(node, "import_from", target)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            value_node = node.value
            if value_node is None:
                continue
            values = _literal_strings(value_node, bindings)
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Name) and values:
                    bindings[target.id] = values

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        raw_name = _dotted_name(node.func) or ""
        first, separator, suffix = raw_name.partition(".")
        resolved_name = (
            f"{aliases[first]}.{suffix}" if separator and first in aliases
            else aliases.get(raw_name, raw_name)
        ).casefold()
        arguments = [*node.args, *(item.value for item in node.keywords)]
        strings = set().union(*(_literal_strings(item, bindings) for item in arguments)) if arguments else set()
        targets = sorted(value for value in strings if _is_evaluator_target(value))
        if resolved_name in DYNAMIC_IMPORT_CALLS:
            for target in targets:
                emit(node, "dynamic_import", target)
        if resolved_name in PROCESS_CALLS:
            for target in targets:
                emit(node, "process_launch", target)
        terminal = resolved_name.rsplit(".", 1)[-1]
        if terminal in RESOURCE_CALL_SUFFIXES:
            receiver_strings = (
                _literal_strings(node.func.value, bindings)
                if isinstance(node.func, ast.Attribute)
                else set()
            )
            for target in sorted(
                value for value in strings.union(receiver_strings)
                if _is_evaluator_target(value)
            ):
                emit(node, "evaluator_resource_access", target)
        if _is_evaluator_target(resolved_name):
            emit(node, "evaluator_call", resolved_name)
    return sorted(set(findings))


def _test(filename: str) -> bool:
    completed = subprocess.run(
        [str(ROOT / ".venv-eval/bin/python"), "-I", "-B", "-m", "unittest",
         "discover", "-s", "tests", "-p", filename],
        cwd=ROOT,
        env={"HOME": str(Path.home()), "USER": "azureuser", "LOGNAME": "azureuser",
             "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
             "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1", "PYTHONSAFEPATH": "1"},
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        timeout=300, check=False,
    )
    return completed.returncode == 0


def _active(marker: str) -> bool:
    completed = subprocess.run(
        ["ps", "-eo", "cmd="], text=True, stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL, check=False,
    )
    return any(marker in line for line in completed.stdout.splitlines() if "ps -eo" not in line)


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=root, text=True, stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL, check=True, timeout=20,
    ).stdout.strip()


def _tracked(root: Path, relative: str | Path) -> bool:
    return subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(relative)], cwd=root,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        check=False, timeout=20,
    ).returncode == 0


def build_report(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    contract = validate_forward_contract(root)
    predecessor = read_object(root / PREDECESSOR_PREAUDIT)
    predecessor_unsigned = dict(predecessor)
    predecessor_seal = predecessor_unsigned.pop("audit_payload_sha256", None)
    predecessor_no_go_valid = (
        predecessor.get("role") == "v24634_exact220_preactivation_audit"
        and predecessor.get("protocol_id")
        == "v24634_capacity_validated_bounded_title_backfill_exact220_v1"
        and predecessor.get("audit_valid") is False
        and predecessor.get("launch_authorized") is False
        and predecessor.get("findings") == ["forward_evaluator_capability_present"]
        and predecessor.get("authorization")
        == {"activation_design": False, "exact220_launch": False, "evaluator_call": False}
        and predecessor.get("forward_contract_sha256")
        == sha256(root / PREDECESSOR_FORWARD_CONTRACT)
        and predecessor_seal == payload_sha256(predecessor_unsigned)
        and contract.get("predecessor_no_go_binding")
        == {
            "forward_contract_path": str(PREDECESSOR_FORWARD_CONTRACT),
            "forward_contract_sha256": sha256(root / PREDECESSOR_FORWARD_CONTRACT),
            "preactivation_audit_path": str(PREDECESSOR_PREAUDIT),
            "preactivation_audit_sha256": sha256(root / PREDECESSOR_PREAUDIT),
        }
    )
    accesses: list[str] = []
    secrets: list[str] = []
    evaluator_capabilities: list[str] = []
    evaluator_modules_in_manifest: list[str] = []
    for relative in contract["dependency_manifest"]:
        path = root / relative
        accesses.extend(_accesses(path, root))
        source = path.read_text(encoding="utf-8")
        if SECRET.search(source):
            secrets.append(relative)
        if _is_evaluator_target(relative):
            evaluator_modules_in_manifest.append(relative)
        if path.suffix == ".py":
            evaluator_capabilities.extend(_evaluator_capabilities(path, root))
    allowed = {"src/deepwide_agent/clients.py:565:score"}
    unexpected = sorted(set(accesses) - allowed)
    lease = lease_observation(root, Path("/proc"))
    findings: list[str] = []
    head = _git(root, "rev-parse", "HEAD")
    remote = _git(root, "rev-parse", "target/main")
    tracked = all(
        _tracked(root, relative)
        for relative in (
            FORWARD_CONTRACT,
            PREDECESSOR_FORWARD_CONTRACT,
            PREDECESSOR_PREAUDIT,
            CAPACITY_RESULT,
            CAPACITY_DECISION,
            CAPACITY_AUDIT,
            *contract["dependency_manifest"],
        )
    )
    try:
        protected = protected_watcher_snapshot()
    except RuntimeError:
        protected = []
        findings.append("protected_watcher_identity_drifted")
    if lease.get("active") is not False:
        findings.append("shared_api_lease_active")
    if head != remote:
        findings.append("forward_contract_commit_not_pushed")
    if not tracked:
        findings.append("forward_contract_or_dependency_not_tracked")
    if not predecessor_no_go_valid:
        findings.append("predecessor_no_go_binding_invalid")
    if _active(RUNNER_MARKER) or _active(CHILD_MARKER):
        findings.append("v24635_forward_process_already_active")
    for marker in (
        "scripts/run_v24630_exact220.py",
        "scripts/finalize_v24630_exact220.py",
        "scripts/run_official_eval_local.py",
    ):
        if _active(marker):
            findings.append("conflicting_benchmark_or_evaluator_process_active")
            break
    if any(
        (root / path).exists() or (root / path).is_symlink()
        for path in (PREAUDIT, ACTIVATION, EXECUTION_START, FORWARD_RESULT, OUTPUT_ROOT)
    ):
        findings.append("future_surface_not_pristine")
    if unexpected:
        findings.append("privileged_runtime_field_access")
    if secrets:
        findings.append("credential_literal_in_forward_surface")
    if evaluator_modules_in_manifest:
        findings.append("evaluator_module_in_forward_dependency_manifest")
    if evaluator_capabilities:
        findings.append("forward_evaluator_capability_present")
    tests = [{"file": name, "passed": _test(name)} for name in TESTS]
    if not all(item["passed"] for item in tests):
        findings.append("focused_tests_failed")
    value = {
        "artifact_version": 1,
        "role": "v24635_exact220_preactivation_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "forward_contract_sha256": sha256(root / FORWARD_CONTRACT),
        "dependency_manifest_sha256": contract["dependency_manifest_sha256"],
        "runtime_boundary": ["opaque_id", "question"],
        "selected": 220,
        "predecessor_no_go": {
            "forward_contract_sha256": sha256(root / PREDECESSOR_FORWARD_CONTRACT),
            "preactivation_audit_sha256": sha256(root / PREDECESSOR_PREAUDIT),
            "binding_valid": predecessor_no_go_valid,
            "activation_execution_or_forward_reused": False,
        },
        "field_accesses": sorted(set(accesses)),
        "allowed_provider_result_rank_accesses": sorted(set(accesses).intersection(allowed)),
        "unexpected_privileged_runtime_field_accesses": unexpected,
        "credential_literal_hits": sorted(secrets),
        "evaluator_capability_detection": {
            "method": "python_ast_import_dynamic_import_process_launch_call_and_resource_access_v1",
            "inert_conflict_process_marker_literals_allowed": True,
            "literal_substring_scan_used_as_capability_test": False,
        },
        "evaluator_modules_in_forward_dependency_manifest": sorted(evaluator_modules_in_manifest),
        "evaluator_capabilities_in_forward_surface": sorted(set(evaluator_capabilities)),
        "focused_tests": tests,
        "git": {
            "head": head,
            "target_main": remote,
            "head_equals_target_main": head == remote,
            "forward_contract_and_dependencies_tracked": tracked,
        },
        "shared_api_lease_active": lease.get("active") is True,
        "protected_watchers": protected,
        "protected_existing_processes_signaled_restarted_or_stopped": False,
        "fixed_denominator_fallback_allows_postfreeze_evaluation": True,
        "network_model_search_fetch_or_evaluator_called_by_audit": False,
        "mapping_gold_category_question_type_split_evaluator_score_read": False,
        "findings": findings,
        "launch_authorized": False,
        "audit_valid": not findings,
        "authorization": {
            "activation_design": not findings,
            "exact220_launch": False,
            "evaluator_call": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


if __name__ == "__main__":
    report = build_report()
    publish_new(ROOT / PREAUDIT, report)
    print(json.dumps({"path": str(PREAUDIT), "launch_authorized": report["launch_authorized"], "findings": report["findings"]}, sort_keys=True))
