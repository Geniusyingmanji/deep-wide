#!/usr/bin/env python3
"""Narrow post-result audit erratum for V2.42.75.

The frozen auditor calls ``_sealed`` from ``_sealed_file`` but does not define
that helper.  Its preactivation path never reaches the call, so the omission
was exposed only after both fresh full64 evaluator arms had completed.  This
module keeps every frozen file and result byte-identical, verifies the exact
omission and exact completed artifact graph, injects only the standard pure
payload-seal predicate into the imported frozen module, and executes its
unchanged post-result report builder.

No forward, evaluator, model, search, fetch, lease, or benchmark effect is
performed here.  The original post-result audit and this disclosure are both
create-exclusive; a crash after publishing the original-format audit can be
recovered by rerunning only this zero-effect publisher.
"""

from __future__ import annotations

import ast
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from scripts import audit_v24275_two_wave_dev64 as frozen  # noqa: E402
from scripts.preregister_v24275_two_wave_dev64 import (  # noqa: E402
    POSTAUDIT,
    publish_new,
)
from scripts.run_v24257_score_first_smoke import (  # noqa: E402
    payload_sha256,
    read_object,
    sha256,
)


FROZEN_AUDITOR = Path("scripts/audit_v24275_two_wave_dev64.py")
ERRATUM_OUTPUT = Path(
    "results/v24275_two_wave_dev64_postresult_audit_erratum_v1_20260802.json"
)
EXPECTED_HASHES = {
    "frozen_auditor": (
        FROZEN_AUDITOR,
        "5e3fdfb2d736ca58fe7de7d30a2198ceccad07504d3b5bbb90a2d962bdfbaa9f",
    ),
    "preregistration": (
        Path("results/v24275_two_wave_dev64_preregistration_v2_20260802.json"),
        "d93e80642c787d02de55f0487d541f223bc938f68a03efaf40f9a912a69cf2e9",
    ),
    "forward_contract": (
        Path("results/v24275_two_wave_dev64_forward_contract_v2_20260802.json"),
        "f18045d8a1906ed08ebe8afc0945e938f3bd3b965db2faf468180dc5f3d404d4",
    ),
    "preactivation_audit": (
        Path("results/v24275_two_wave_dev64_preactivation_audit_v2_20260802.json"),
        "48c4a137c6c5d1b0408c4c660c7505065af3707b2c24288653873434527e4826",
    ),
    "activation": (
        Path("results/v24275_two_wave_dev64_activation_v2_20260802.json"),
        "ce633d8978aa9d263b33f63349a41378e99d5ca083f9b4d06f9e7bfc626cd020",
    ),
    "execution_start": (
        Path("results/v24275_two_wave_dev64_execution_start_v2_20260802.json"),
        "7cf230f57830db1f6a1b1739139e82c1080bd1a6457f53d7b5e526293a9388ae",
    ),
    "forward_result": (
        Path("results/v24275_two_wave_dev64_forward_result_v2_20260802.json"),
        "c7d2428f01690919bdb3cc91c0ae76b9987029de58c6b96fbdbc999512460f10",
    ),
    "prediction_freeze": (
        Path(
            "outputs/v24275_two_wave_dev64_v2_20260802/"
            "candidate_prediction_freeze.json"
        ),
        "8b964ffceda44491b907bc711861f5c2115ebba268146eab3e0c83b0c87b1e7b",
    ),
    "final_result": (
        Path("results/v24275_two_wave_dev64_result_v2_20260802.json"),
        "f70ee9ca9619e2b3c72fdfd1831e377eff9380f6fc8d28d7f312bd00cb9e36a1",
    ),
}
ERRATUM_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "created_at_unix",
        "status",
        "frozen_failure",
        "bound_artifacts",
        "postresult_audit",
        "result",
        "execution_closure",
        "network_model_search_fetch_evaluator_or_api_called_by_erratum",
        "forward_or_evaluator_restarted_resumed_or_rerun",
        "frozen_files_modified_or_relaxed",
        "invalid_result_path",
        "findings",
        "valid",
        "erratum_payload_sha256",
    }
)


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    """The standard pure seal predicate omitted from the frozen auditor."""

    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def verify_exact_frozen_defect(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve()
    bound: dict[str, dict[str, str]] = {}
    for name, (relative, expected) in EXPECTED_HASHES.items():
        path = root / relative
        if path.is_symlink() or not path.is_file() or sha256(path) != expected:
            raise RuntimeError(f"V2.42.75 erratum artifact drifted: {name}")
        bound[name] = {"path": str(relative), "sha256": expected}

    tree = ast.parse((root / FROZEN_AUDITOR).read_text(encoding="utf-8"))
    definitions = [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == "_sealed"
    ]
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "_sealed"
    ]
    sealed_files = [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == "_sealed_file"
    ]
    if definitions or len(calls) != 1 or len(sealed_files) != 1:
        raise RuntimeError("V2.42.75 frozen missing-helper defect is not exact")
    return {
        "bound_artifacts": bound,
        "missing_symbol": "_sealed",
        "definition_count": len(definitions),
        "call_count": len(calls),
        "call_line": calls[0].lineno,
        "call_is_inside_sealed_file": calls[0].lineno
        in range(sealed_files[0].lineno, sealed_files[0].end_lineno + 1),
    }


def validate_postaudit(value: Mapping[str, Any]) -> None:
    closure = value.get("execution_closure")
    authorization = value.get("authorization")
    if (
        value.get("role") != "v24275_two_wave_dev64_postresult_audit"
        or value.get("label_blind") is not True
        or value.get("findings") != []
        or value.get("audit_valid") is not True
        or not _sealed(value, "audit_payload_sha256")
        or not isinstance(closure, Mapping)
        or closure.get("runner_process_present_after_result") is not False
        or closure.get("child_process_present_after_result") is not False
        or closure.get("finalizer_process_present_after_result") is not False
        or closure.get("shared_api_lease_active") is not False
        or closure.get(
            "process_signal_restart_skip_selective_retry_or_error_revaluation"
        )
        is not False
        or closure.get("active_run_killed_or_quarantined") is not False
        or closure.get("invalid_result_path") is not None
        or not isinstance(authorization, Mapping)
        or authorization.get("exact220_design") is not False
        or authorization.get("new_exact220_launch") is not False
        or authorization.get("leaderboard_submission_or_sota_claim") is not False
    ):
        raise RuntimeError("V2.42.75 erratum post-result audit drifted")


def build_postaudit(root: Path = ROOT) -> dict[str, Any]:
    verify_exact_frozen_defect(root)
    # Deliberately patch only the imported module namespace.  The frozen file
    # and every artifact remain byte-identical and hash-bound above.
    frozen._sealed = _sealed
    value = frozen.build_postresult_report(root=root)
    validate_postaudit(value)
    return value


def build_erratum(
    root: Path, post: Mapping[str, Any], *, now: int | None = None
) -> dict[str, Any]:
    defect = verify_exact_frozen_defect(root)
    validate_postaudit(post)
    result = post["result"]
    closure = post["execution_closure"]
    value = {
        "artifact_version": 1,
        "role": "v24275_two_wave_dev64_postresult_audit_missing_seal_helper_erratum",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "valid_zero_effect_in_memory_helper_compatibility",
        "frozen_failure": {
            "exception_class": "NameError",
            "message": "name '_sealed' is not defined",
            "missing_symbol": defect["missing_symbol"],
            "definition_count": defect["definition_count"],
            "call_count": defect["call_count"],
            "call_line": defect["call_line"],
            "call_is_inside_sealed_file": defect[
                "call_is_inside_sealed_file"
            ],
            "observed_before_postaudit_write": True,
        },
        "bound_artifacts": defect["bound_artifacts"],
        "postresult_audit": {
            "path": str(POSTAUDIT),
            "sha256": sha256(root / POSTAUDIT),
            "audit_payload_sha256": post["audit_payload_sha256"],
        },
        "result": {
            "status": result["status"],
            "selected_per_arm": result["selected_per_arm"],
            "decision_passed": result["decision"]["passed"],
            "public_full220_result": result["claims"]["public_full220_result"],
            "sota": result["claims"]["sota"],
        },
        "execution_closure": dict(closure),
        "network_model_search_fetch_evaluator_or_api_called_by_erratum": False,
        "forward_or_evaluator_restarted_resumed_or_rerun": False,
        "frozen_files_modified_or_relaxed": False,
        "invalid_result_path": None,
        "findings": [],
        "valid": True,
    }
    value["erratum_payload_sha256"] = payload_sha256(value)
    validate_erratum(value)
    return value


def validate_erratum(value: Mapping[str, Any]) -> None:
    failure = value.get("frozen_failure")
    result = value.get("result")
    closure = value.get("execution_closure")
    if (
        set(value) != ERRATUM_KEYS
        or value.get("role")
        != "v24275_two_wave_dev64_postresult_audit_missing_seal_helper_erratum"
        or value.get("status")
        != "valid_zero_effect_in_memory_helper_compatibility"
        or not isinstance(failure, Mapping)
        or failure.get("exception_class") != "NameError"
        or failure.get("missing_symbol") != "_sealed"
        or failure.get("definition_count") != 0
        or failure.get("call_count") != 1
        or failure.get("call_is_inside_sealed_file") is not True
        or failure.get("observed_before_postaudit_write") is not True
        or value.get("bound_artifacts")
        != verify_exact_frozen_defect(ROOT)["bound_artifacts"]
        or not isinstance(result, Mapping)
        or result.get("status") != "development_gate_no_go"
        or result.get("selected_per_arm") != 64
        or result.get("decision_passed") is not False
        or result.get("public_full220_result") is not False
        or result.get("sota") is not False
        or not isinstance(closure, Mapping)
        or any(
            closure.get(name) is not False
            for name in (
                "runner_process_present_after_result",
                "child_process_present_after_result",
                "finalizer_process_present_after_result",
                "shared_api_lease_active",
                "process_signal_restart_skip_selective_retry_or_error_revaluation",
                "active_run_killed_or_quarantined",
            )
        )
        or closure.get("invalid_result_path") is not None
        or value.get(
            "network_model_search_fetch_evaluator_or_api_called_by_erratum"
        )
        is not False
        or value.get("forward_or_evaluator_restarted_resumed_or_rerun") is not False
        or value.get("frozen_files_modified_or_relaxed") is not False
        or value.get("invalid_result_path") is not None
        or value.get("findings") != []
        or value.get("valid") is not True
        or not _sealed(value, "erratum_payload_sha256")
    ):
        raise RuntimeError("V2.42.75 post-result audit erratum drifted")


def publish(root: Path = ROOT) -> tuple[dict[str, Any], dict[str, Any]]:
    root = root.resolve()
    if (root / ERRATUM_OUTPUT).exists() or (root / ERRATUM_OUTPUT).is_symlink():
        raise FileExistsError(root / ERRATUM_OUTPUT)
    if (root / POSTAUDIT).exists() or (root / POSTAUDIT).is_symlink():
        post = read_object(root / POSTAUDIT)
        validate_postaudit(post)
    else:
        post = build_postaudit(root)
        publish_new(root / POSTAUDIT, post)
    erratum = build_erratum(root, post)
    publish_new(root / ERRATUM_OUTPUT, erratum)
    return post, erratum


if __name__ == "__main__":
    post, erratum = publish()
    print(
        json.dumps(
            {
                "postresult_audit": str(POSTAUDIT),
                "postresult_audit_sha256": sha256(ROOT / POSTAUDIT),
                "erratum": str(ERRATUM_OUTPUT),
                "erratum_sha256": sha256(ROOT / ERRATUM_OUTPUT),
                "audit_valid": post["audit_valid"],
                "erratum_valid": erratum["valid"],
            },
            sort_keys=True,
        )
    )
