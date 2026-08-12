#!/usr/bin/env python3
"""Append-only correction for the V2.51.82 identity-vector typo.

V2.51.82 was generated with ``adnutes`` at vector position 13 while the
V2.51.83 visible task contract and the completed forward used ``adnuts``.
Both spellings had zero history hits at the original frozen parent.  This
audit binds that fact to the immutable protocol/forward chain without
rewriting or rerunning any completed artifact.
"""

from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25183_quote_aware_external_contract as contract  # noqa: E402
from scripts import audit_v25182_quote_aware_population_selection as original  # noqa: E402


DATE = "20260812"
ROLE = "v25184_v25182_population_typo_correction_audit"
OUTPUT = Path(
    f"results/v25184_v25182_population_typo_correction_audit_v1_{DATE}.json"
)
ORIGINAL_AUDIT = contract.POPULATION_AUDIT
PROTOCOL = contract.PROTOCOL
EXECUTION_START = contract.EXECUTION_START
FORWARD_RESULT = contract.FORWARD_RESULT
FORWARD_AUDIT = contract.FORWARD_AUDIT
TASK_ROWS = contract.TASK_ROWS
PREDICTION_FREEZE = contract.PREDICTION_FREEZE

PARENT_COMMIT = "9429d72790e060bcd041034f03f4beb399c78072"
ORIGINAL_AUDIT_SHA256 = (
    "927e84bda363ea38f6b9d0ccd8ae63ae610ebc55c1c413ff07df3ef10d41af38"
)
TYPO_IDENTITY_VECTOR_SHA256 = (
    "074db8b82176a9176a2cd0c6a5f4d02ee4354f36e02c4369795a4d1b3b8791b5"
)
CORRECT_IDENTITY_VECTOR_SHA256 = (
    "ad8f22292d594f2067735c80b8a4d171972b9608b041d15ea83f628313327999"
)
TASK_ROWS_SHA256 = (
    "804e85f63d5b032c046d7600bb0e04c0005888c2866dc2a54a115bdcb65b3c9c"
)
PREDICTION_FREEZE_SHA256 = (
    "487c34b58ab434bf1944116a207b3ba5473ddd417e3d87c3f135457f433f6571"
)
FORWARD_RESULT_SHA256 = (
    "8a3398ff8f0470577a92004d0ab82e75906d552e77b3d5e73a4f169462eab897"
)
FORWARD_AUDIT_SHA256 = (
    "a19cdc0d75f7b8dac244e7730c293732e8312950eea60609b7d1b2b42ae49267"
)

CORRECT_IDENTITIES = tuple(contract.PACKAGES)
TYPO_IDENTITIES = tuple(
    "adnutes" if value == "adnuts" else value for value in CORRECT_IDENTITIES
)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=30,
        check=True,
    ).stdout.strip()


def _normalized(values: Sequence[str]) -> list[str]:
    return ["-".join(str(value).casefold().split()) for value in values]


def _history_hits(identity: str, *, parent_commit: str) -> int:
    completed = subprocess.run(
        [
            "git",
            "log",
            parent_commit,
            "-i",
            "-S",
            identity,
            "--format=%H",
            "--",
            "src",
            "evaluation",
            "scripts",
            "tests",
            "results",
            "outputs",
        ],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=30,
        check=True,
    )
    return sum(bool(line.strip()) for line in completed.stdout.splitlines())


def _read(relative: Path) -> dict[str, Any]:
    path = contract.ordinary(ROOT, relative, tracked=True)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.51.84 expected JSON object")
    return value


def _clean_pushed() -> tuple[str, str]:
    head = _git("rev-parse", "HEAD")
    target = _git("rev-parse", "target/main")
    if _git("status", "--porcelain") or head != target:
        raise RuntimeError("V2.51.84 requires clean pushed HEAD")
    return head, target


def build_audit(
    *,
    now: int | None = None,
    require_clean: bool = True,
    require_pristine: bool = True,
) -> dict[str, Any]:
    head, target = (
        _clean_pushed() if require_clean else ("build-only", "build-only")
    )
    if require_pristine and (
        (ROOT / OUTPUT).exists() or (ROOT / OUTPUT).is_symlink()
    ):
        raise FileExistsError(OUTPUT)

    resolved_parent = _git("rev-parse", "--verify", PARENT_COMMIT + "^{commit}")
    if resolved_parent != PARENT_COMMIT:
        raise RuntimeError("V2.51.84 original parent drifted")

    original_path = contract.ordinary(ROOT, ORIGINAL_AUDIT, tracked=True)
    original_value = original.validate_audit(_read(ORIGINAL_AUDIT))
    protocol = contract.validate_protocol(ROOT, _read(PROTOCOL))
    start = _read(EXECUTION_START)
    forward = _read(FORWARD_RESULT)
    audit = _read(FORWARD_AUDIT)
    freeze = _read(PREDICTION_FREEZE)

    correct_vector = _normalized(CORRECT_IDENTITIES)
    typo_vector = _normalized(TYPO_IDENTITIES)
    correct_hash = contract.payload_sha256(correct_vector)
    typo_hash = contract.payload_sha256(typo_vector)
    correct_hits = _history_hits("adnuts", parent_commit=resolved_parent)
    typo_hits = _history_hits("adnutes", parent_commit=resolved_parent)
    tasks = contract.task_vector()
    task_hash = contract.payload_sha256(tasks)
    opaque_hash = contract.payload_sha256(
        [row["opaque_id"] for row in tasks]
    )

    chain_checks = {
        "original_audit_hash_and_seal_valid": contract.sha256(original_path)
        == ORIGINAL_AUDIT_SHA256
        and original_value["audit_valid"] is True,
        "original_audit_bound_typo_vector": original_value[
            "ordered_identity_vector_sha256"
        ]
        == typo_hash
        == TYPO_IDENTITY_VECTOR_SHA256,
        "correct_runtime_vector_hash_recomputed": correct_hash
        == CORRECT_IDENTITY_VECTOR_SHA256,
        "vectors_differ_only_at_position_13": len(correct_vector)
        == len(typo_vector)
        == 20
        and [
            index
            for index, (left, right) in enumerate(
                zip(correct_vector, typo_vector, strict=True), start=1
            )
            if left != right
        ]
        == [13]
        and correct_vector[12] == "adnuts"
        and typo_vector[12] == "adnutes",
        "correct_and_typo_spellings_both_zero_hit_at_original_parent": correct_hits
        == typo_hits
        == 0,
        "protocol_binds_correct_visible_task_vector": protocol["population"][
            "task_vector_sha256"
        ]
        == task_hash
        and protocol["population"]["opaque_id_vector_sha256"]
        == opaque_hash,
        "execution_start_binds_protocol": start.get("protocol_sha256")
        == contract.sha256(ROOT / PROTOCOL),
        "forward_chain_artifact_hashes_unchanged": contract.sha256(
            ROOT / TASK_ROWS
        )
        == TASK_ROWS_SHA256
        and contract.sha256(ROOT / PREDICTION_FREEZE)
        == PREDICTION_FREEZE_SHA256
        and contract.sha256(ROOT / FORWARD_RESULT) == FORWARD_RESULT_SHA256
        and contract.sha256(ROOT / FORWARD_AUDIT) == FORWARD_AUDIT_SHA256,
        "forward_and_freeze_bind_task_rows": forward.get("task_rows_sha256")
        == freeze.get("task_rows_sha256")
        == TASK_ROWS_SHA256,
        "forward_audit_valid_and_mechanism_only": audit.get("audit_valid") is True
        and audit.get("findings") == []
        and audit.get("authorization", {}).get("external_evaluator") is False
        and audit.get("authorization", {}).get(
            "deepwidebench_dev64_exact220_or_sota"
        )
        is False,
        "no_forward_evaluator_or_quality_reexecution": True,
    }
    findings = sorted(name for name, passed in chain_checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git": {"head": head, "target_main": target, "equal": head == target},
        "parents": {
            "original_selection_audit_path": str(ORIGINAL_AUDIT),
            "original_selection_audit_sha256": ORIGINAL_AUDIT_SHA256,
            "v25183_protocol_sha256": contract.sha256(ROOT / PROTOCOL),
            "v25183_execution_start_sha256": contract.sha256(
                ROOT / EXECUTION_START
            ),
            "v25183_forward_result_sha256": FORWARD_RESULT_SHA256,
            "v25183_forward_audit_sha256": FORWARD_AUDIT_SHA256,
            "v25183_task_rows_sha256": TASK_ROWS_SHA256,
            "v25183_prediction_freeze_sha256": PREDICTION_FREEZE_SHA256,
        },
        "correction": {
            "original_parent_commit": resolved_parent,
            "vector_position_one_based": 13,
            "original_mistyped_visible_identity": "adnutes",
            "actual_forward_visible_identity": "adnuts",
            "original_typo_vector_sha256": typo_hash,
            "correct_runtime_vector_sha256": correct_hash,
            "original_typo_history_hit_count": typo_hits,
            "correct_identity_history_hit_count": correct_hits,
            "other_vector_positions_changed": 0,
            "actual_forward_task_vector_or_prediction_bytes_changed": False,
            "mechanism_result_or_aggregate_changed": False,
        },
        "checks": chain_checks,
        "findings": findings,
        "audit_valid": not findings,
        "source_policy": {
            "repository_history_and_frozen_artifact_chain_only": True,
            "network_model_search_fetch_or_api_called": False,
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read": False,
            "frozen_prediction_content_used_for_selection_or_quality": False,
            "credential_value_read_hashed_persisted_or_emitted": False,
            "entropy_or_information_gain_assigns_signed_credit": False,
        },
        "supersession": {
            "original_selection_audit_deleted_or_rewritten": False,
            "original_identity_vector_disjointness_claim_valid_for_actual_forward": False,
            "corrected_identity_vector_disjointness_claim_valid": not findings,
            "completed_v25183_forward_replayed_or_reexecuted": False,
            "v25183_mechanism_and_reliability_result_recertified": not findings,
            "v25183_quality_effect_established": False,
        },
        "authorization": {
            "independent_fresh_natural_quality_gate_design": not findings,
            "external_forward_or_evaluator": False,
            "deepwidebench_dev64_exact220_avg4_leaderboard_or_sota": False,
            "retry_resume_skip_population_replacement_or_selective_rerun": False,
        },
    }
    value["audit_payload_sha256"] = contract.payload_sha256(value)
    return validate_audit(value)


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("audit_payload_sha256", None)
    correction = copied.get("correction", {})
    source = copied.get("source_policy", {})
    supersession = copied.get("supersession", {})
    authorization = copied.get("authorization", {})
    if (
        copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("findings") != []
        or copied.get("audit_valid") is not True
        or not copied.get("checks")
        or not all(copied["checks"].values())
        or correction.get("vector_position_one_based") != 13
        or correction.get("original_mistyped_visible_identity") != "adnutes"
        or correction.get("actual_forward_visible_identity") != "adnuts"
        or correction.get("original_typo_vector_sha256")
        != TYPO_IDENTITY_VECTOR_SHA256
        or correction.get("correct_runtime_vector_sha256")
        != CORRECT_IDENTITY_VECTOR_SHA256
        or correction.get("original_typo_history_hit_count") != 0
        or correction.get("correct_identity_history_hit_count") != 0
        or correction.get("other_vector_positions_changed") != 0
        or correction.get("actual_forward_task_vector_or_prediction_bytes_changed")
        is not False
        or correction.get("mechanism_result_or_aggregate_changed") is not False
        or source
        != {
            "repository_history_and_frozen_artifact_chain_only": True,
            "network_model_search_fetch_or_api_called": False,
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read": False,
            "frozen_prediction_content_used_for_selection_or_quality": False,
            "credential_value_read_hashed_persisted_or_emitted": False,
            "entropy_or_information_gain_assigns_signed_credit": False,
        }
        or supersession
        != {
            "original_selection_audit_deleted_or_rewritten": False,
            "original_identity_vector_disjointness_claim_valid_for_actual_forward": False,
            "corrected_identity_vector_disjointness_claim_valid": True,
            "completed_v25183_forward_replayed_or_reexecuted": False,
            "v25183_mechanism_and_reliability_result_recertified": True,
            "v25183_quality_effect_established": False,
        }
        or authorization
        != {
            "independent_fresh_natural_quality_gate_design": True,
            "external_forward_or_evaluator": False,
            "deepwidebench_dev64_exact220_avg4_leaderboard_or_sota": False,
            "retry_resume_skip_population_replacement_or_selective_rerun": False,
        }
        or seal != contract.payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.51.84 typo correction audit drifted")
    return copied


def _publish(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def main() -> None:
    value = build_audit()
    _publish(ROOT / OUTPUT, value)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "audit_valid": value["audit_valid"],
                "corrected_disjointness": value["supersession"][
                    "corrected_identity_vector_disjointness_claim_valid"
                ],
                "forward_reexecuted": value["supersession"][
                    "completed_v25183_forward_replayed_or_reexecuted"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
