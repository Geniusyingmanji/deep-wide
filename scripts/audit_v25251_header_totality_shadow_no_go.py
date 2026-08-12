#!/usr/bin/env python3
"""Publish a valid audit for the frozen V2.52.48 mechanism NO-GO."""

from __future__ import annotations

import copy
import json
import re
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25248_header_totality_shadow_external_contract as contract  # noqa: E402
from scripts import audit_v25250_header_totality_shadow_forward as parent  # noqa: E402
from scripts import control_v25248_header_totality_shadow_external as build_control  # noqa: E402
from scripts import run_v25248_header_totality_shadow_external as runner  # noqa: E402


SOURCE = Path("scripts/audit_v25251_header_totality_shadow_no_go.py")
TEST = Path("tests/test_audit_v25251_header_totality_shadow_no_go.py")
PARENT_AUDITOR_SHA256 = "dac2d1e23046a7204f49efd0531269a0b84a5c0aba41f80312c73db53932cc32"
PARENT_TEST_SHA256 = "7b0c0e588eff3caad801b53730e67c9b6531fa6d450ed259ae0c4685d3d2469f"
FROZEN_FORWARD_COMMIT = "359d21a4e957b50abfb66a7ec5d896d5a2c64c30"
FROZEN_START_COMMIT = "35d445d819ddd65f5cc27ed5884724493a477348"
FROZEN_HASHES = {
    contract.PROTOCOL: "09bd7d6276c137dc20e1ff3e6a653b2e39c50d8b99f1e5393c0a16c67f007695",
    contract.EXECUTION_START: "447c596d566b76ae68b3d27bbcff215dc0210d797721a1c2e21ee6c234f9a338",
    contract.ATTEMPT_CLAIM: "c1362b5216231430c1acba9ba34142ec222f60121c21cd328e9d5ac3538ec133",
    contract.FORWARD_RESULT: "41c5d604c247d05c2087859eafd70efbe1e03a4e41e53476aedee13cba5d0507",
    contract.TASK_ROWS: "aa65b9bf1cccc34c687f38e282c9273a11c7af43096408eb27a0edfe442d46c5",
    contract.PREDICTION_FREEZE: "c1968f3b4abe31bdb196534a684f5e1a8891d8293d96365be94f20dbef4297ed",
    contract.SAFE_PROGRESS: "44cb8956664540d93b7faffd24a4260a54cf4f4a23714b5bbd7d09ad983415d8",
}
INTEGRITY_CHECK_NAMES = {
    name for name in parent.AUDIT_CHECK_NAMES if name != "physical_effect_within_preregistered_caps"
}
MECHANISM_CHECK_NAMES = {"physical_effect_within_preregistered_caps"}


def _hashes_exact() -> bool:
    try:
        return bool(
            contract.sha256(ROOT / parent.SOURCE) == PARENT_AUDITOR_SHA256
            and contract.sha256(ROOT / parent.TEST) == PARENT_TEST_SHA256
            and all(contract.sha256(ROOT / path) == expected for path, expected in FROZEN_HASHES.items())
        )
    except BaseException:
        return False


def _frozen_commit_boundary() -> bool:
    try:
        parents = contract.git(
            ROOT, "rev-list", "--parents", "-n", "1", FROZEN_FORWARD_COMMIT
        ).split()
        changed = tuple(
            sorted(
                line.strip()
                for line in contract.git(
                    ROOT, "diff-tree", "--no-commit-id", "--name-only", "-r",
                    FROZEN_FORWARD_COMMIT,
                ).splitlines()
                if line.strip()
            )
        )
        return bool(
            parents == [FROZEN_FORWARD_COMMIT, FROZEN_START_COMMIT]
            and changed == parent.EXPECTED_FORWARD_COMMIT_PATHS
        )
    except BaseException:
        return False


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    head = contract.git(ROOT, "rev-parse", "HEAD")
    target = contract.git(ROOT, "rev-parse", "target/main")
    if contract.git(ROOT, "status", "--porcelain") or head != target:
        raise RuntimeError("V2.52.51 requires clean pushed HEAD")
    base = parent.build_audit(now=now, tracked=True)
    base_checks = dict(base["checks"])
    base_checks["forward_commit_is_single_pushed_fixed_surface_child_of_start"] = (
        _frozen_commit_boundary()
    )
    integrity_checks = {name: base_checks[name] for name in sorted(INTEGRITY_CHECK_NAMES)}
    mechanism_checks = {name: base_checks[name] for name in sorted(MECHANISM_CHECK_NAMES)}
    integrity_checks.update(
        {
            "frozen_parent_auditor_and_forward_surface_hashes_exact": _hashes_exact(),
            "frozen_forward_commit_is_exact_start_child_with_fixed21_paths": _frozen_commit_boundary(),
            "current_head_is_descendant_of_frozen_forward_without_surface_mutation": (
                contract.git(ROOT, "merge-base", "--is-ancestor", FROZEN_FORWARD_COMMIT, head) == ""
                and all(contract.sha256(ROOT / path) == expected for path, expected in FROZEN_HASHES.items())
            ),
            "forward_audit_surface_pristine": (
                not (ROOT / contract.FORWARD_AUDIT).exists()
                and not (ROOT / contract.FORWARD_AUDIT).is_symlink()
            ),
        }
    )
    integrity_findings = sorted(name for name, passed in integrity_checks.items() if not passed)
    mechanism_failed = sorted(name for name, passed in mechanism_checks.items() if not passed)
    decision = copy.deepcopy(base["mechanism_decision"])
    if (
        decision.get("mechanism_gate_passed") is not False
        or decision.get("failed_checks")
        != [
            "all_runtime_tasks_completed",
            "fetch_budget_preserved",
            "model_budget_preserved",
            "natural_shadow_entry_nonzero",
            "safe_shadow_candidate_nonzero",
        ]
        or mechanism_failed != ["physical_effect_within_preregistered_caps"]
    ):
        integrity_findings.append("frozen_mechanism_no_go_shape_drifted")
        integrity_findings.sort()
    value = {
        "artifact_version": 1,
        "role": "v25251_header_totality_shadow_forward_no_go_audit",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git": {
            "head": head,
            "target_main": target,
            "equal": head == target,
            "frozen_forward_commit": FROZEN_FORWARD_COMMIT,
            "frozen_start_commit": FROZEN_START_COMMIT,
        },
        "frozen_hashes": {str(path): expected for path, expected in FROZEN_HASHES.items()},
        "aggregate": copy.deepcopy(base["aggregate"]),
        "mechanism_decision": decision,
        "integrity_checks": integrity_checks,
        "mechanism_checks": mechanism_checks,
        "integrity_findings": integrity_findings,
        "mechanism_failed_checks": mechanism_failed,
        "audit_valid": not integrity_findings,
        "mechanism_gate_passed": False,
        "status": "audited_mechanism_no_go",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "evaluator_or_quality_metric_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "authorization": {
            "independent_activation_and_quality_design": False,
            "candidate_activation_or_prediction_change": False,
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
            "retry_resume_skip_replacement_or_selective_rerun": False,
            "content_free_successor_diagnosis_only": not integrity_findings,
        },
    }
    return contract.seal(value, "audit_payload_sha256")


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    aggregate = copied.get("aggregate")
    decision = copied.get("mechanism_decision") or {}
    integrity = copied.get("integrity_checks") or {}
    mechanism = copied.get("mechanism_checks") or {}
    frozen = copied.get("frozen_hashes") or {}
    git_value = copied.get("git") or {}
    if (
        set(copied)
        != {
            "artifact_version", "role", "protocol_id", "created_at_unix", "git",
            "frozen_hashes", "aggregate", "mechanism_decision", "integrity_checks",
            "mechanism_checks", "integrity_findings", "mechanism_failed_checks",
            "audit_valid", "mechanism_gate_passed", "status",
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
            "evaluator_or_quality_metric_called",
            "entropy_or_information_gain_assigns_signed_credit", "authorization",
            "audit_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != "v25251_header_totality_shadow_forward_no_go_audit"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or not isinstance(copied.get("created_at_unix"), int)
        or set(git_value)
        != {"head", "target_main", "equal", "frozen_forward_commit", "frozen_start_commit"}
        or git_value.get("head") != git_value.get("target_main")
        or git_value.get("equal") is not True
        or git_value.get("frozen_forward_commit") != FROZEN_FORWARD_COMMIT
        or git_value.get("frozen_start_commit") != FROZEN_START_COMMIT
        or frozen != {str(path): expected for path, expected in FROZEN_HASHES.items()}
        or not isinstance(aggregate, Mapping)
        or runner.validate_aggregate(aggregate) != dict(aggregate)
        or decision != runner.mechanism_decision(aggregate)
        or decision.get("mechanism_gate_passed") is not False
        or not isinstance(integrity, Mapping)
        or not all(integrity.values())
        or mechanism != {"physical_effect_within_preregistered_caps": False}
        or copied.get("integrity_findings") != []
        or copied.get("mechanism_failed_checks") != ["physical_effect_within_preregistered_caps"]
        or copied.get("audit_valid") is not True
        or copied.get("mechanism_gate_passed") is not False
        or copied.get("status") != "audited_mechanism_no_go"
        or copied.get("mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read") is not False
        or copied.get("evaluator_or_quality_metric_called") is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit") is not False
        or copied.get("authorization")
        != {
            "independent_activation_and_quality_design": False,
            "candidate_activation_or_prediction_change": False,
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
            "retry_resume_skip_replacement_or_selective_rerun": False,
            "content_free_successor_diagnosis_only": True,
        }
        or not contract.sealed(copied, "audit_payload_sha256")
    ):
        raise ValueError("V2.52.51 no-go audit drifted")
    return copied


def main() -> None:
    value = validate_audit(build_audit())
    runner._publish_json(ROOT / contract.FORWARD_AUDIT, value)
    print(json.dumps({"path": str(contract.FORWARD_AUDIT), "status": value["status"]}, sort_keys=True))


if __name__ == "__main__":
    main()
