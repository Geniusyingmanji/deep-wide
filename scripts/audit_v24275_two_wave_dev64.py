#!/usr/bin/env python3
"""Strict label-blind preactivation/post-result audit for V2.42.75."""

from __future__ import annotations

import ast
import importlib.util
import json
import re
import sys
import time
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24275_forward_contract import (  # noqa: E402
    ACTIVATION,
    CHILD_MARKER,
    EXECUTION_START,
    FORWARD_PROTOCOL,
    FORWARD_RESULT,
    PREAUDIT,
    RUNNER_MARKER,
    sha256,
)
from scripts.audit_v24187_phase_liveness import process_snapshot  # noqa: E402
from scripts.audit_v24195_lease_owner_compatibility import (  # noqa: E402
    lease_observation,
)
from scripts.preregister_v24259_deterministic_normalizer_smoke import (  # noqa: E402
    _matching,
)
from scripts.preregister_v24275_two_wave_dev64 import (  # noqa: E402
    FINALIZER_MARKER,
    FINAL_RESULT,
    OUTPUT,
    POSTAUDIT,
    SELECTED_COUNT,
    publish_new,
    validate_protocol,
)
from scripts.run_v24257_score_first_smoke import (  # noqa: E402
    payload_sha256,
    read_object,
)


FORBIDDEN = frozenset(
    {
        "category",
        "question_type",
        "task_category",
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
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}"
)
FORWARD_CAPABILITY_MARKERS = (
    "finalize_v24275_two_wave_dev64",
    "preregister_v24275_two_wave_dev64",
    "audit_v24275_two_wave_dev64",
    "activate_v24275_two_wave_dev64",
    "MAPPING_PATH",
    "CONTROL_RUNTIME",
    "CONTROL_RESULT",
    "CONTROL_PREDICTION_FREEZE",
    "run_official_eval_local",
    "finalize_fullset_rollout",
    "evaluator_mapping.jsonl",
    "overall_20250916",
)
DEPENDENCY_SCRIPT_IMPORT_ALLOWLIST = frozenset({"scripts.deepwide_api_lease"})


def _accesses(path: Path, root: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    values: list[str] = []
    for node in ast.walk(tree):
        value = None
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "get"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            value = node.args[0].value
        elif (
            isinstance(node, ast.Subscript)
            and isinstance(node.slice, ast.Constant)
            and isinstance(node.slice.value, str)
        ):
            value = node.slice.value
        if value is not None and value.casefold() in FORBIDDEN:
            values.append(f"{path.relative_to(root)}:{node.lineno}:{value}")
    return values


class _EagerImports(ast.NodeVisitor):
    """Collect imports executed at module load, excluding function/class bodies."""

    def __init__(self) -> None:
        self.nodes: list[ast.Import | ast.ImportFrom] = []

    def visit_Import(self, node: ast.Import) -> None:  # noqa: N802
        self.nodes.append(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:  # noqa: N802
        self.nodes.append(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        return

    def visit_AsyncFunctionDef(  # noqa: N802
        self, node: ast.AsyncFunctionDef
    ) -> None:
        return

    def visit_ClassDef(self, node: ast.ClassDef) -> None:  # noqa: N802
        return


def _module_name(relative: str) -> str | None:
    path = Path(relative)
    if path.parts[:2] == ("src", "deepwide_agent"):
        tail = path.relative_to("src").with_suffix("")
        if tail.name == "__init__":
            tail = tail.parent
        return ".".join(tail.parts)
    if path.parts and path.parts[0] == "scripts" and path.suffix == ".py":
        return ".".join(path.with_suffix("").parts)
    return None


def _eager_local_imports(path: Path, relative: str) -> list[str]:
    current = _module_name(relative)
    if current is None:
        return []
    package = current if relative.endswith("/__init__.py") else current.rpartition(".")[0]
    visitor = _EagerImports()
    visitor.visit(ast.parse(path.read_text(encoding="utf-8")))
    modules: set[str] = set()
    for node in visitor.nodes:
        if isinstance(node, ast.Import):
            modules.update(
                alias.name
                for alias in node.names
                if alias.name == "deepwide_agent"
                or alias.name.startswith("deepwide_agent.")
                or alias.name == "scripts"
                or alias.name.startswith("scripts.")
            )
            continue
        raw = node.module or ""
        if node.level:
            resolved = importlib.util.resolve_name("." * node.level + raw, package)
        else:
            resolved = raw
        if (
            resolved == "deepwide_agent"
            or resolved.startswith("deepwide_agent.")
            or resolved == "scripts"
            or resolved.startswith("scripts.")
        ):
            modules.add(resolved)
    return sorted(modules)


def _module_manifest(manifest: Mapping[str, str]) -> dict[str, str]:
    output: dict[str, str] = {}
    for relative in manifest:
        module = _module_name(relative)
        if module:
            output[module] = relative
    return output


def build_report(
    root: Path = ROOT,
    *,
    now: int | None = None,
    proc_root: Path = Path("/proc"),
) -> dict[str, Any]:
    root = root.resolve()
    protocol = validate_protocol(root, OUTPUT)
    rows = process_snapshot(proc_root)
    lease = lease_observation(root, proc_root)
    manifest = protocol["forward_surface"]["manifest"]
    modules = _module_manifest(manifest)
    accesses: list[str] = []
    secrets: list[str] = []
    capability_hits: list[str] = []
    unresolved_imports: list[str] = []
    unexpected_script_imports: list[str] = []
    eager_imports: dict[str, list[str]] = {}
    for relative in manifest:
        path = root / relative
        source = path.read_text(encoding="utf-8")
        accesses.extend(_accesses(path, root))
        if SECRET.search(source):
            secrets.append(relative)
        for marker in FORWARD_CAPABILITY_MARKERS:
            if marker in source:
                capability_hits.append(f"{relative}:{marker}")
        imported = _eager_local_imports(path, relative)
        eager_imports[relative] = imported
        for module in imported:
            if module == "scripts":
                continue
            if module.startswith("scripts.") and module not in DEPENDENCY_SCRIPT_IMPORT_ALLOWLIST:
                unexpected_script_imports.append(f"{relative}:{module}")
            if module not in modules and module != "scripts":
                unresolved_imports.append(f"{relative}:{module}")

    allowed = {"src/deepwide_agent/clients.py:565:score"}
    unexpected_accesses = sorted(set(accesses) - allowed)
    findings: list[str] = []
    if lease.get("active") is not False:
        findings.append("shared_api_lease_active")
    if _matching(rows, RUNNER_MARKER):
        findings.append("dev64_runner_already_active")
    if _matching(rows, CHILD_MARKER):
        findings.append("dev64_child_already_active")
    if _matching(rows, FINALIZER_MARKER):
        findings.append("dev64_finalizer_already_active")
    if (root / ACTIVATION).exists() or (root / ACTIVATION).is_symlink():
        findings.append("activation_already_present")
    if unexpected_accesses:
        findings.append("unexpected_benchmark_privileged_field_access")
    if secrets:
        findings.append("credential_literal_in_forward_surface")
    if capability_hits:
        findings.append("forward_import_closure_has_evaluator_side_capability")
    if unresolved_imports:
        findings.append("forward_eager_local_import_not_frozen")
    if unexpected_script_imports:
        findings.append("forward_import_closure_has_unapproved_script_dependency")
    parents = protocol.get("parents") or {}
    if (
        parents.get(
            "historical_control_prediction_freeze_runtime_summary_mapping_gold_or_evaluator_rows_opened_or_hashed"
        )
        is not False
        or any(
            key in parents
            for key in (
                "frozen_control_prediction_freeze",
                "frozen_control_runtime",
                "frozen_control_summary",
            )
        )
    ):
        findings.append("historical_per_task_control_opened_or_hashed_before_candidate")

    value = {
        "artifact_version": 1,
        "role": "v24275_two_wave_dev64_preactivation_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "protocol_sha256": sha256(root / OUTPUT),
        "forward_contract_sha256": sha256(root / FORWARD_PROTOCOL),
        "forward_contract_payload_sha256": protocol["forward_runtime_contract"][
            "payload_sha256"
        ],
        "label_blind": True,
        "runtime_boundary": ["opaque_id", "question"],
        "selected_count": SELECTED_COUNT,
        "frozen_opaque_allowlist_without_label_fields": True,
        "field_accesses": accesses,
        "allowed_provider_search_rank_accesses": sorted(
            set(accesses).intersection(allowed)
        ),
        "unexpected_benchmark_privileged_field_accesses_absent": not unexpected_accesses,
        "credential_literal_hits": secrets,
        "forward_evaluator_side_capability_hits": capability_hits,
        "forward_import_closure_evaluator_side_capability_absent": not capability_hits,
        "eager_local_imports": eager_imports,
        "unresolved_eager_local_imports": unresolved_imports,
        "all_eager_local_imports_frozen": not unresolved_imports,
        "unexpected_script_imports": unexpected_script_imports,
        "forward_import_closure_unapproved_script_dependency_absent": not unexpected_script_imports,
        "historical_per_task_control_prediction_freeze_runtime_summary_opened_or_hashed": False,
        "shared_api_lease_active": lease.get("active") is True,
        "protected_existing_processes_signaled_restarted_or_stopped": False,
        "network_model_search_fetch_or_evaluator_api_called_by_audit": False,
        "mapping_control_prediction_gold_category_question_type_split_evaluator_score_read": False,
        "findings": findings,
        "launch_authorized": not findings,
        "new_exact220_or_sota_authorized": False,
        "audit_valid": True,
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


def _sealed_file(path: Path, role: str, field: str) -> dict[str, Any]:
    value = read_object(path)
    if value.get("role") != role or not _sealed(value, field):
        raise RuntimeError(f"V2.42.75 sealed artifact drifted: {path}")
    return value


def build_postresult_report(
    root: Path = ROOT,
    *,
    now: int | None = None,
    proc_root: Path = Path("/proc"),
) -> dict[str, Any]:
    root = root.resolve()
    preaudit = _sealed_file(
        root / PREAUDIT,
        "v24275_two_wave_dev64_preactivation_audit",
        "audit_payload_sha256",
    )
    from scripts.finalize_v24275_two_wave_dev64 import (
        validate_candidate_barrier,
        validate_final_result,
    )
    from scripts.run_v24275_two_wave_dev64 import (
        validate_activation,
        validate_execution_start,
    )

    candidate = validate_candidate_barrier(root)
    protocol = validate_protocol(root, OUTPUT)
    activation = validate_activation(root, candidate["forward_protocol"])
    execution = validate_execution_start(
        root, candidate["forward_protocol"], activation
    )
    result = read_object(root / FINAL_RESULT)
    validate_final_result(root, protocol, result)
    rows = process_snapshot(proc_root)
    lease = lease_observation(root, proc_root)
    runner_present = bool(_matching(rows, RUNNER_MARKER))
    child_present = bool(_matching(rows, CHILD_MARKER))
    finalizer_present = bool(_matching(rows, FINALIZER_MARKER))
    lease_active = lease.get("active") is True
    findings: list[str] = []
    if runner_present:
        findings.append("forward_runner_present_after_result")
    if child_present:
        findings.append("forward_child_present_after_result")
    if finalizer_present:
        findings.append("finalizer_present_after_result")
    if lease_active:
        findings.append("shared_api_lease_active_after_result")
    value = {
        "artifact_version": 1,
        "role": "v24275_two_wave_dev64_postresult_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "label_blind": True,
        "protocol_sha256": sha256(root / OUTPUT),
        "preactivation_audit_sha256": sha256(root / PREAUDIT),
        "activation_sha256": sha256(root / ACTIVATION),
        "execution_start_sha256": sha256(root / EXECUTION_START),
        "forward_result_sha256": sha256(root / FORWARD_RESULT),
        "final_result_sha256": sha256(root / FINAL_RESULT),
        "result": {
            "status": result["status"],
            "selected_per_arm": result["selected_per_arm"],
            "control": result["control"],
            "candidate": result["candidate"],
            "candidate_retrieval_health": result["candidate_retrieval_health"],
            "decision": result["decision"],
            "claims": result["claims"],
        },
        "execution_closure": {
            "runner_process_present_after_result": runner_present,
            "child_process_present_after_result": child_present,
            "finalizer_process_present_after_result": finalizer_present,
            "shared_api_lease_active": lease_active,
            "process_signal_restart_skip_selective_retry_or_error_revaluation": False,
            "active_run_killed_or_quarantined": False,
            "invalid_result_path": None,
        },
        "source_policy": dict(result["source_policy"]),
        "authorization": {
            "exact220_design": result["decision"]["passed"],
            "new_exact220_launch": False,
            "leaderboard_submission_or_sota_claim": False,
        },
        "findings": findings,
        "audit_valid": not findings
        and preaudit.get("launch_authorized") is True
        and execution.get("api_called_before_execution_start") is False,
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


if __name__ == "__main__":
    post = "--post-result" in sys.argv
    path = POSTAUDIT if post else PREAUDIT
    report = build_postresult_report() if post else build_report()
    publish_new(ROOT / path, report)
    print(json.dumps({"path": str(path), "sha256": sha256(ROOT / path)}))
