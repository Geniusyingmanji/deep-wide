#!/usr/bin/env python3
"""Final aggregate-only repair of full-220 visible authority scope."""

from __future__ import annotations

import copy
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24320_forward_contract import payload_sha256  # noqa: E402
from deepwide_agent.v24635_exact220_contract import (  # noqa: E402
    FORWARD_CONTRACT,
    SOURCE_MANIFEST,
    selected_tasks,
    sha256,
    validate_forward_contract,
)
from deepwide_agent.v24705_visible_authority_scope_repair import (  # noqa: E402
    AUTHORITY_PATTERNS,
    validate_signature,
    visible_authority_signature,
)


DATE = "20260806"
OUTPUT = Path(f"results/v24706_full220_visible_authority_scope_audit_v1_{DATE}.json")
PREDECESSOR = Path(
    f"results/v24704_full220_visible_authority_coverage_repair_audit_v1_{DATE}.json"
)
EXPECTED_NAMESPACE_COUNTS = {"world_bank": 1}
EXPECTED_MULTIPLICITY = {"0": 219, "1": 1}


def read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("V2.47.06 expected ordinary object")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.47.06 expected object")
    return value


def sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def _histogram(values: Counter[int]) -> dict[str, int]:
    return {str(key): values[key] for key in sorted(values)}


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    tasks = selected_tasks(ROOT, validate_forward_contract(ROOT, FORWARD_CONTRACT))
    predecessor = read(ROOT / PREDECESSOR)
    if (
        predecessor.get("role")
        != "v24704_full220_visible_authority_coverage_repair_audit"
        or not sealed(predecessor, "audit_payload_sha256")
        or predecessor.get("audit_valid") is not True
        or predecessor.get("coverage", {}).get("adapter_route_eligible_task_count") != 3
        or predecessor.get("authorization", {}).get("runtime_adapter_implementation")
        is not False
        or predecessor.get("authorization", {}).get("exact220") is not False
    ):
        raise RuntimeError("V2.47.06 predecessor drifted")
    namespace_counts: Counter[str] = Counter()
    multiplicity: Counter[int] = Counter()
    eligible = ambiguous = 0
    for task in tasks:
        if set(task) != {"opaque_id", "question"}:
            raise RuntimeError("V2.47.06 visible boundary drifted")
        signature = validate_signature(visible_authority_signature(task["question"]))
        multiplicity[signature["namespace_count"]] += 1
        ambiguous += int(signature["namespace_count"] > 1)
        if signature["unique_namespace"] is not None:
            namespace_counts[signature["unique_namespace"]] += 1
        eligible += int(signature["adapter_route_eligible"])
    namespace_output = {
        name: namespace_counts[name]
        for name, _pattern in AUTHORITY_PATTERNS
        if namespace_counts[name]
    }
    findings: list[str] = []
    if len(tasks) != 220:
        findings.append("visible_task_denominator_drifted")
    if namespace_output != EXPECTED_NAMESPACE_COUNTS:
        findings.append("authority_scope_counts_drifted")
    if _histogram(multiplicity) != EXPECTED_MULTIPLICITY:
        findings.append("authority_scope_multiplicity_drifted")
    if (eligible, ambiguous) != (1, 0):
        findings.append("authority_scope_totals_drifted")
    value = {
        "artifact_version": 1,
        "role": "v24706_full220_visible_authority_scope_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "repair": {
            "predecessor_path": str(PREDECESSOR),
            "predecessor_sha256": sha256(ROOT / PREDECESSOR),
            "predecessor_authorized_runtime_or_benchmark": False,
            "semantic_false_positive_task_count_removed": 2,
            "false_positive_types": [
                "github_discovery_clue_not_answer_authority",
                "camera_ISO_field_not_ISO_authority",
            ],
            "only_signature_change": "explicit_answer_authority_scope_required",
            "predecessor_superseded": True,
        },
        "parents": {
            "v24635_visible_forward_contract_sha256": sha256(ROOT / FORWARD_CONTRACT),
            "visible_manifest_sha256": sha256(ROOT / SOURCE_MANIFEST),
        },
        "coverage": {
            "fixed_visible_task_denominator": len(tasks),
            "explicit_answer_authority_task_count": sum(namespace_counts.values()),
            "adapter_route_eligible_task_count": eligible,
            "adapter_route_eligible_fraction": round(eligible / len(tasks), 12),
            "ambiguous_multi_authority_task_count": ambiguous,
            "authority_namespace_task_counts": namespace_output,
            "authority_multiplicity_histogram": _histogram(multiplicity),
        },
        "decision": {
            "hardcoded_multi_namespace_bridge_reachability_sufficient": False,
            "worldbank_only_treatment_task_count": namespace_counts["world_bank"],
            "worldbank_only_candidate_cannot_plausibly_raise_full220_whole_table_by_more_than_one": True,
            "generic_unknown_target_predecessor_dev64_admission_count": 0,
            "expanded_parser_predecessor_dev64_whole_table_gain": 0,
            "new_benchmark_forward_or_evaluator_warranted": False,
            "status": "deepwidebench_transfer_no_go_before_forward",
            "next_candidate_requirement": "generic_identity_and_target_value_binding_with_pre_forward_nonzero_safe_intervention evidence, not namespace hardcoding",
        },
        "source_policy": {
            "runtime_input_keys": ["opaque_id", "question"],
            "only_visible_manifest_read": True,
            "aggregate_counts_only": True,
            "question_column_name_namespace_per_task_or_opaque_id_persisted_or_emitted": False,
            "mapping_category_split_gold_prediction_score_reward_or_evaluator_read": False,
            "network_model_search_fetch_benchmark_or_evaluator_called": False,
            "credential_read_hashed_persisted_or_emitted": False,
        },
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "generic_target_value_candidate_design": not findings,
            "namespace_adapter_runtime_implementation": False,
            "fresh_dev64_protocol_or_launch": False,
            "evaluator": False,
            "exact220": False,
            "leaderboard_or_sota": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("audit_payload_sha256", None)
    if (
        copied.get("role") != "v24706_full220_visible_authority_scope_audit"
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or copied.get("coverage", {}).get("adapter_route_eligible_task_count") != 1
        or copied.get("decision", {}).get("new_benchmark_forward_or_evaluator_warranted")
        is not False
        or copied.get("authorization")
        != {
            "generic_target_value_candidate_design": True,
            "namespace_adapter_runtime_implementation": False,
            "fresh_dev64_protocol_or_launch": False,
            "evaluator": False,
            "exact220": False,
            "leaderboard_or_sota": False,
        }
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.47.06 authority scope audit drifted")
    return copied


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
    audit = validate_audit(build_audit())
    publish_new(ROOT / OUTPUT, audit)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "audit_valid": audit["audit_valid"],
                "eligible": audit["coverage"]["adapter_route_eligible_task_count"],
                "namespace_counts": audit["coverage"]["authority_namespace_task_counts"],
                "status": audit["decision"]["status"],
            },
            sort_keys=True,
        )
    )
