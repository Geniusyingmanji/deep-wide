#!/usr/bin/env python3
"""Audit the pure V2.42.02 label-blind WebSwarm adapter prototype."""

from __future__ import annotations

import argparse
import ast
import dataclasses
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.prototype_v24202_label_blind_webswarm_adapter import (  # noqa: E402
    DelegationLimits,
    EvidenceRecord,
    RootScope,
    build_planner_context,
    compile_label_blind_payload,
    validate_child_envelope,
)


ROLE = "v24202_label_blind_webswarm_adapter_audit"
OUTPUT = Path(
    "results/v24202_label_blind_webswarm_adapter_audit_v1_20260731.json"
)
MODULE = Path("scripts/prototype_v24202_label_blind_webswarm_adapter.py")
MODULE_TEST = Path("tests/test_prototype_v24202_label_blind_webswarm_adapter.py")
AUDIT = Path("scripts/audit_v24202_label_blind_webswarm_adapter.py")
AUDIT_TEST = Path("tests/test_audit_v24202_label_blind_webswarm_adapter.py")
CONTROL_FILES = (MODULE, MODULE_TEST, AUDIT, AUDIT_TEST)

ALLOWED_IMPORT_ROOTS = frozenset(
    {
        "__future__",
        "collections",
        "dataclasses",
        "hashlib",
        "json",
        "re",
        "typing",
        "unicodedata",
    }
)
FORBIDDEN_CALL_NAMES = frozenset(
    {
        "__import__",
        "breakpoint",
        "compile",
        "eval",
        "exec",
        "input",
        "open",
    }
)
FORBIDDEN_ATTRIBUTE_ROOTS = frozenset(
    {
        "aiohttp",
        "anyio",
        "asyncio",
        "builtins",
        "http",
        "httpx",
        "importlib",
        "os",
        "pathlib",
        "requests",
        "shutil",
        "socket",
        "subprocess",
        "urllib",
    }
)
REQUIRED_PUBLIC_FUNCTIONS = frozenset(
    {
        "build_planner_context",
        "classify_web_topology",
        "compile_delegations",
        "compile_label_blind_payload",
        "infer_visible_mode",
        "reject_privileged_metadata",
        "validate_child_envelope",
    }
)
SECRET_LITERAL = re.compile(
    r"(?:ghp_|github_pat_|tvly-(?:dev-)?|sk-)[A-Za-z0-9_-]{16,}"
)
OPAQUE_ID = re.compile(r"task_[0-9a-f]{24}")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def ordinary(root: Path, relative: Path) -> Path:
    if relative.is_absolute() or ".." in relative.parts:
        raise RuntimeError("V2.42.02 path is noncanonical")
    path = root / relative
    if (
        path.resolve(strict=False) != path.absolute()
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(root)
    ):
        raise RuntimeError(f"V2.42.02 expected an ordinary repository file: {relative}")
    return path


def _attribute_root(node: ast.Attribute) -> str | None:
    current: ast.expr = node
    while isinstance(current, ast.Attribute):
        current = current.value
    return current.id if isinstance(current, ast.Name) else None


def audit_python_source(source: str) -> dict[str, Any]:
    tree = ast.parse(source)
    imports: set[str] = set()
    defined_functions: set[str] = set()
    forbidden_calls: list[str] = []
    forbidden_attributes: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module.split(".", 1)[0])
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            defined_functions.add(node.name)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_CALL_NAMES:
                forbidden_calls.append(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                root = _attribute_root(node.func)
                if root in FORBIDDEN_ATTRIBUTE_ROOTS:
                    forbidden_attributes.append(f"{root}.{node.func.attr}")
    disallowed_imports = sorted(imports - ALLOWED_IMPORT_ROOTS)
    missing_functions = sorted(REQUIRED_PUBLIC_FUNCTIONS - defined_functions)
    if disallowed_imports or forbidden_calls or forbidden_attributes or missing_functions:
        raise RuntimeError(
            "V2.42.02 prototype capability boundary failed: "
            f"imports={disallowed_imports}, calls={sorted(forbidden_calls)}, "
            f"attributes={sorted(forbidden_attributes)}, missing={missing_functions}"
        )
    return {
        "ast_node_count": sum(1 for _ in ast.walk(tree)),
        "import_roots": sorted(imports),
        "defined_function_count": len(defined_functions),
        "required_public_functions_present": sorted(REQUIRED_PUBLIC_FUNCTIONS),
        "disallowed_import_count": 0,
        "forbidden_call_count": 0,
        "forbidden_attribute_call_count": 0,
        "file_environment_network_process_or_dynamic_code_capability": False,
    }


def _page(
    evidence_id: str,
    source_id: str,
    query_id: str,
    *,
    rows: list[str] | None = None,
    columns: list[str] | None = None,
    page_backed: bool = True,
    contradicted: bool = False,
) -> dict[str, Any]:
    return {
        "evidence_id": evidence_id,
        "source_id": source_id,
        "query_id": query_id,
        "row_keys": rows or [],
        "column_keys": columns or [],
        "page_backed": page_backed,
        "contradicted": contradicted,
    }


def _payload(
    question: str,
    *,
    columns: list[str] | None = None,
    rows: list[str] | None = None,
    evidence: list[dict[str, Any]] | None = None,
    proposals: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    visible = {
        "visible_question": question,
        "output_columns": columns or [],
        "visible_known_rows": rows or [],
    }
    evidence_values = evidence or []
    context = build_planner_context(
        RootScope.from_mapping(visible),
        [EvidenceRecord.from_mapping(item) for item in evidence_values],
    )
    proposal_values = proposals or [
        {"objective": question, "mode": None, "evidence_ids": []}
    ]
    return {
        "visible_input": visible,
        "current_trace": {"evidence": evidence_values},
        "proposals": [
            {**item, "planner_context_sha256": context.planner_context_sha256}
            for item in proposal_values
        ],
    }


def _must_reject(value: dict[str, Any], *, match: str, **kwargs: Any) -> None:
    try:
        compile_label_blind_payload(value, depth=0, **kwargs)
    except ValueError as error:
        if match not in str(error):
            raise RuntimeError(
                f"V2.42.02 rejection had the wrong reason: {error}"
            ) from error
    else:
        raise RuntimeError("V2.42.02 unsafe payload was accepted")


def replay_synthetic_contracts() -> dict[str, Any]:
    modes: dict[str, str] = {}
    cases = {
        "atom": _payload("Return the official launch date for Alpha"),
        "deep": _payload(
            "Identify the unknown organization that satisfies the visible constraints"
        ),
        "entity_collect": _payload(
            "List all visible-scope members as a complete list"
        ),
        "wide": _payload(
            "Fill the requested table for each supplied organization",
            columns=["Name", "Year", "Value"],
            rows=["Alpha", "Beta"],
        ),
    }
    for expected, value in cases.items():
        batch = compile_label_blind_payload(value, depth=0)
        if len(batch.contracts) != 1 or batch.contracts[0].mode != expected:
            raise RuntimeError(f"V2.42.02 mode replay drifted: {expected}")
        modes[expected] = batch.contracts[0].mode

    centralized_payload = _payload(
        "Fill the requested table",
        columns=["Name", "Year"],
        rows=["Alpha", "Beta"],
        evidence=[
            _page(
                "E0001",
                "S1",
                "Q1",
                rows=["Alpha", "Beta"],
                columns=["Name", "Year"],
            )
        ],
        proposals=[
            {"objective": "Fill visible rows", "mode": "wide", "evidence_ids": ["E0001"]}
        ],
    )
    centralized = compile_label_blind_payload(centralized_payload, depth=0)
    if centralized.topology.topology != "centralized":
        raise RuntimeError("V2.42.02 centralized topology replay drifted")

    distributed_payload = _payload(
        "Fill the requested table",
        columns=["Name", "Year"],
        rows=["Alpha", "Beta"],
        evidence=[
            _page("E0001", "S1", "Q1", rows=["Alpha"], columns=["Name"]),
            _page("E0002", "S2", "Q2", rows=["Beta"], columns=["Year"]),
        ],
        proposals=[
            {"objective": "Fill visible rows", "mode": "wide", "evidence_ids": ["E0001"]}
        ],
    )
    distributed = compile_label_blind_payload(distributed_payload, depth=0)
    if distributed.topology.topology != "distributed":
        raise RuntimeError("V2.42.02 distributed topology replay drifted")

    duplicate_proposal = {
        "objective": "Collect visible attributes",
        "mode": "wide",
        "evidence_ids": ["E0001"],
    }
    duplicate_payload = _payload(
        "Build the requested table",
        evidence=[_page("E0001", "S1", "Q1")],
        proposals=[
            duplicate_proposal,
            dict(duplicate_proposal),
            {**duplicate_proposal, "objective": "Verify visible attributes"},
        ],
    )
    duplicate = compile_label_blind_payload(duplicate_payload, depth=0)
    if (
        len(duplicate.contracts) != 2
        or duplicate.exact_contract_duplicates_removed != 1
        or duplicate.unique_evidence_set_count != 1
    ):
        raise RuntimeError("V2.42.02 equivalence replay drifted")

    ablation_modes: dict[str, str] = {}
    for policy, expected in (
        ("all_to_deep", "deep"),
        ("all_to_wide", "wide"),
        ("no_recursive", "entity_collect"),
    ):
        batch = compile_label_blind_payload(cases["entity_collect"], depth=0, policy=policy)
        contract = batch.contracts[0]
        if contract.mode != expected or (
            policy == "no_recursive" and (contract.may_delegate or contract.max_children)
        ):
            raise RuntimeError(f"V2.42.02 ablation replay drifted: {policy}")
        ablation_modes[policy] = contract.mode

    privilege_rejections = 0
    for key in (
        "benchmark",
        "subset",
        "category",
        "question_type",
        "ground_truth",
        "answerKey",
        "mapping",
        "evaluator",
        "score",
        "prediction",
        "reward",
        "task_id",
    ):
        value = _payload("Return the requested fact")
        value["current_trace"]["evidence"] = [{key: "forbidden"}]
        _must_reject(value, match="privileged metadata")
        privilege_rejections += 1

    stale = _payload("Return the requested fact")
    stale["proposals"][0]["planner_context_sha256"] = "0" * 64
    _must_reject(stale, match="does not match")

    search_answer = _payload(
        "Build the requested table",
        evidence=[_page("E0001", "S1", "Q1", page_backed=False)],
        proposals=[
            {"objective": "Fill visible rows", "mode": "wide", "evidence_ids": ["E0001"]}
        ],
    )
    _must_reject(search_answer, match="inactive page evidence")

    contradicted = _payload(
        "Build the requested table",
        evidence=[_page("E0001", "S1", "Q1", contradicted=True)],
        proposals=[
            {"objective": "Fill visible rows", "mode": "wide", "evidence_ids": ["E0001"]}
        ],
    )
    _must_reject(contradicted, match="inactive page evidence")

    over_batch = _payload(
        "Return the requested facts",
        proposals=[
            {"objective": f"Return visible fact {index}", "mode": "atom", "evidence_ids": []}
            for index in range(3)
        ],
    )
    _must_reject(
        over_batch,
        match="batch exceeds",
        limits=DelegationLimits(max_batch_children=2),
    )

    contract = centralized.contracts[0]
    child_tamper = validate_child_envelope(
        contract,
        {
            "root_scope_sha256": "0" * 64,
            "objective_sha256": contract.objective_sha256,
            "evidence_ids": ["E9999"],
            "generated_child_count": contract.max_children + 1,
            "status": "completed",
        },
        active_evidence_ids=["E0001"],
    )
    expected_errors = {
        "root_scope_anchor_mismatch",
        "inactive_evidence_returned",
        "generated_child_cap_exceeded",
    }
    if child_tamper.valid or set(child_tamper.errors) != expected_errors:
        raise RuntimeError("V2.42.02 child-envelope tamper replay drifted")

    repeat = compile_label_blind_payload(centralized_payload, depth=0)
    if dataclasses.asdict(repeat) != dataclasses.asdict(centralized):
        raise RuntimeError("V2.42.02 deterministic replay drifted")
    audit = centralized.audit()
    forbidden_true = [
        key
        for key, value in audit.items()
        if key.endswith("_read")
        or key.endswith("_called")
        or key.endswith("_granted")
        or key.endswith("_allowed")
        if value is not False
    ]
    if forbidden_true:
        raise RuntimeError(f"V2.42.02 audit authorization drifted: {forbidden_true}")

    return {
        "adapter_payload_replay_count": 27,
        "child_envelope_replay_count": 1,
        "total_synthetic_replay_count": 28,
        "fallback_modes_observed": sorted(modes),
        "fallback_mode_count": len(modes),
        "ablation_policies_observed": sorted(ablation_modes),
        "ablation_policy_count": len(ablation_modes),
        "topologies_observed": ["centralized", "distributed"],
        "topology_count": 2,
        "privileged_key_rejection_count": privilege_rejections,
        "stale_planner_context_rejected": True,
        "search_answer_only_provenance_rejected": True,
        "contradicted_provenance_rejected": True,
        "batch_cap_enforced": True,
        "root_scope_tamper_rejected": True,
        "inactive_child_provenance_rejected": True,
        "child_cap_tamper_rejected": True,
        "exact_contract_duplicate_removed": True,
        "distinct_objective_on_same_evidence_preserved": True,
        "deterministic_replay": True,
        "content_values_emitted": False,
    }


def build_audit(
    root: Path = ROOT, *, created_at_unix: int | None = None
) -> dict[str, Any]:
    root = root.resolve()
    if root != ROOT.resolve():
        raise RuntimeError("V2.42.02 audit may only use the canonical workspace")
    manifest = {
        str(relative): sha256(ordinary(root, relative))
        for relative in CONTROL_FILES
    }
    module_source = ordinary(root, MODULE).read_text(encoding="utf-8")
    static = audit_python_source(module_source)
    replay = replay_synthetic_contracts()
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if created_at_unix is None else int(created_at_unix),
        "label_blind": True,
        "build_only": True,
        "prototype_policy": "v24202_label_blind_webswarm_adapter_v1",
        "control_surface": {
            "file_count": len(manifest),
            "manifest": manifest,
            "manifest_sha256": payload_sha256(manifest),
        },
        "static_capability_audit": static,
        "synthetic_contract_replay": replay,
        "scientific_scope": {
            "webswarm_style_modes": ["atom", "deep", "wide", "entity_collect"],
            "observed_topology_only": True,
            "unseen_mass_or_open_world_completeness_estimated": False,
            "planner_context_bound_to_visible_state": True,
            "root_scope_anchor_required": True,
            "active_page_provenance_closure_required": True,
            "contradicted_pages_excluded_from_routing": True,
            "exact_contract_duplicates_removed": True,
            "same_evidence_distinct_objectives_preserved": True,
            "sibling_trajectory_experience_injected": False,
            "topology_derived_content_free_tactic_only": True,
            "entropy_or_information_gain_used": False,
            "answer_evidence_membership_row_cell_predicate_or_task_credit_granted": False,
            "quality_cost_or_sota_effect_claimed": False,
        },
        "source_policy": {
            "synthetic_visible_input_and_content_free_provenance_only": True,
            "runtime_task_state_question_answer_evidence_text_url_or_prediction_opened": False,
            "benchmark_subset_category_question_type_label_or_split_read": False,
            "mapping_gold_answer_key_evaluator_score_reward_or_result_read": False,
            "credential_environment_keyring_or_secret_value_read": False,
            "network_model_search_fetch_subprocess_or_api_called": False,
        },
        "authorization": {
            "active_forward_code_prompt_model_search_budget_or_controller_change": False,
            "process_signal_restart_resume_rerun_skip_or_selective_retry": False,
            "candidate_build_materialization_or_quality_gate": False,
            "benchmark_forward_full220_or_evaluator_launch": False,
            "leaderboard_submission_or_sota_claim": False,
        },
        "claims": {
            "benchmark_score_available": False,
            "benchmark_improvement_observed": False,
            "avg_at_4_available": False,
            "entropy_or_credit_effect_observed": False,
            "webswarm_adapter_quality_effect_observed": False,
            "leaderboard_submission_performed": False,
            "sota": False,
        },
        "audit_valid": True,
    }
    encoded = json.dumps(value, ensure_ascii=False)
    if SECRET_LITERAL.search(encoded) or OPAQUE_ID.search(encoded):
        raise RuntimeError("V2.42.02 audit would expose forbidden content")
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


def validate_audit(root: Path = ROOT, path: Path = OUTPUT) -> dict[str, Any]:
    root = root.resolve()
    target = path if path.is_absolute() else root / path
    if (
        target.resolve(strict=False) != (root / OUTPUT).resolve(strict=False)
        or target.is_symlink()
        or not target.is_file()
    ):
        raise RuntimeError("V2.42.02 audit path is noncanonical")
    value = json.loads(target.read_text(encoding="utf-8"))
    unsigned = dict(value)
    seal = unsigned.pop("audit_payload_sha256", None)
    manifest = value.get("control_surface", {}).get("manifest")
    if (
        value.get("role") != ROLE
        or value.get("audit_valid") is not True
        or seal != payload_sha256(unsigned)
        or not isinstance(manifest, dict)
        or set(manifest) != {str(path) for path in CONTROL_FILES}
        or value["control_surface"].get("manifest_sha256")
        != payload_sha256(manifest)
    ):
        raise RuntimeError("V2.42.02 audit receipt is invalid")
    for relative, digest in manifest.items():
        if sha256(ordinary(root, Path(relative))) != digest:
            raise RuntimeError("V2.42.02 audit control bytes drifted")
    return value


def publish_new(path: Path, value: dict[str, Any]) -> None:
    target = path.resolve(strict=False)
    if target != (ROOT / OUTPUT).resolve(strict=False) or not target.is_relative_to(ROOT / "results"):
        raise RuntimeError("V2.42.02 output path is noncanonical")
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        target.unlink(missing_ok=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(OUTPUT))
    args = parser.parse_args()
    target = Path(args.output)
    target = target if target.is_absolute() else ROOT / target
    value = build_audit()
    publish_new(target, value)
    print(
        json.dumps(
            {
                "path": str(target),
                "sha256": sha256(target),
                "synthetic_replays": value["synthetic_contract_replay"]["total_synthetic_replay_count"],
            }
        )
    )


if __name__ == "__main__":
    main()
