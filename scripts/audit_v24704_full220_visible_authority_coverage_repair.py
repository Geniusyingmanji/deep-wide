#!/usr/bin/env python3
"""Append-only repair of the V2.47.02 full-220 authority coverage audit."""

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
from deepwide_agent.v24703_visible_authority_namespace_repair import (  # noqa: E402
    NAMESPACE_PATTERNS,
    validate_signature,
    visible_authority_signature,
)


DATE = "20260806"
OUTPUT = Path(
    f"results/v24704_full220_visible_authority_coverage_repair_audit_v1_{DATE}.json"
)
INVALID_PREDECESSOR = Path(
    f"results/v24702_full220_visible_authority_coverage_audit_v1_{DATE}.json"
)
EXPECTED_NAMESPACE_COUNTS = {
    "github": 1,
    "iso": 1,
    "wikipedia": 1,
    "world_bank": 1,
}
EXPECTED_ELIGIBLE_COUNTS = {"github": 1, "iso": 1, "world_bank": 1}
EXPECTED_MULTIPLICITY = {"0": 216, "1": 4}


def read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("V2.47.04 expected ordinary object")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.47.04 expected object")
    return value


def sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def _histogram(values: Counter[int]) -> dict[str, int]:
    return {str(key): values[key] for key in sorted(values)}


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    contract = validate_forward_contract(ROOT, FORWARD_CONTRACT)
    tasks = selected_tasks(ROOT, contract)
    predecessor = read(ROOT / INVALID_PREDECESSOR)
    if (
        predecessor.get("role")
        != "v24702_full220_visible_authority_coverage_audit"
        or not sealed(predecessor, "audit_payload_sha256")
        or predecessor.get("audit_valid") is not True
        or predecessor.get("coverage", {}).get("visible_namespace_task_counts", {}).get("who")
        != 19
        or predecessor.get("authorization", {}).get("fresh_dev64_protocol_or_launch")
        is not False
        or predecessor.get("authorization", {}).get("exact220") is not False
    ):
        raise RuntimeError("V2.47.04 invalid predecessor drifted")
    namespace_counts: Counter[str] = Counter()
    eligible_counts: Counter[str] = Counter()
    multiplicity: Counter[int] = Counter()
    schema_widths: Counter[int] = Counter()
    eligible = ambiguous = namespace_without_address = 0
    for task in tasks:
        if set(task) != {"opaque_id", "question"}:
            raise RuntimeError("V2.47.04 visible boundary drifted")
        signature = validate_signature(visible_authority_signature(task["question"]))
        count = signature["namespace_count"]
        multiplicity[count] += 1
        schema_widths[signature["visible_schema_width"]] += 1
        ambiguous += int(count > 1)
        namespace = signature["unique_namespace"]
        if namespace is not None:
            namespace_counts[namespace] += 1
            if signature["adapter_route_eligible"]:
                eligible_counts[namespace] += 1
                eligible += 1
            else:
                namespace_without_address += 1
    namespace_output = {
        name: namespace_counts[name]
        for name, _pattern in NAMESPACE_PATTERNS
        if namespace_counts[name]
    }
    eligible_output = {
        name: eligible_counts[name]
        for name, _pattern in NAMESPACE_PATTERNS
        if eligible_counts[name]
    }
    findings: list[str] = []
    if len(tasks) != 220:
        findings.append("visible_task_denominator_drifted")
    if namespace_output != EXPECTED_NAMESPACE_COUNTS:
        findings.append("namespace_counts_drifted")
    if eligible_output != EXPECTED_ELIGIBLE_COUNTS:
        findings.append("eligible_namespace_counts_drifted")
    if _histogram(multiplicity) != EXPECTED_MULTIPLICITY:
        findings.append("namespace_multiplicity_drifted")
    if (eligible, ambiguous, namespace_without_address) != (3, 0, 1):
        findings.append("coverage_totals_drifted")
    value = {
        "artifact_version": 1,
        "role": "v24704_full220_visible_authority_coverage_repair_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "repair": {
            "invalid_predecessor_path": str(INVALID_PREDECESSOR),
            "invalid_predecessor_sha256": sha256(ROOT / INVALID_PREDECESSOR),
            "invalid_predecessor_authorized_or_launched_benchmark": False,
            "bug": "case_insensitive_WHO_acronym_matched_ordinary_interrogative_who",
            "observed_false_positive_task_count": 19,
            "exact_uppercase_WHO_or_full_name_task_count": 0,
            "only_signature_change": "case_safe_WHO_matching",
            "predecessor_superseded": True,
        },
        "parents": {
            "v24635_visible_forward_contract_sha256": sha256(ROOT / FORWARD_CONTRACT),
            "visible_manifest_sha256": sha256(ROOT / SOURCE_MANIFEST),
        },
        "coverage": {
            "fixed_visible_task_denominator": len(tasks),
            "unique_visible_namespace_task_count": sum(namespace_counts.values()),
            "ambiguous_multi_namespace_task_count": ambiguous,
            "unique_namespace_without_address_signature_task_count": namespace_without_address,
            "adapter_route_eligible_task_count": eligible,
            "adapter_route_eligible_fraction": round(eligible / len(tasks), 12),
            "visible_namespace_task_counts": namespace_output,
            "adapter_route_eligible_namespace_counts": eligible_output,
            "namespace_multiplicity_histogram": _histogram(multiplicity),
            "visible_schema_width_histogram": _histogram(schema_widths),
        },
        "interpretation": {
            "worldbank_specific_adapter_natural_coverage_task_count": namespace_counts["world_bank"],
            "who_adapter_natural_coverage_task_count": namespace_counts["who"],
            "single_worldbank_adapter_is_sufficient_for_deepwidebench_transfer": False,
            "current_preregistered_multi_namespace_bridge_coverage_is_low": eligible < 8,
            "coverage_is_quality_score_or_adapter_correctness_evidence": False,
            "coverage_authorizes_runtime_or_benchmark_implementation": False,
            "fresh_dev64_or_exact220_launch_authorized_by_coverage": False,
            "next_action": "expand_case_safe_visible_namespace_grammar_or_test_generic_target_value_binding_without_namespace_shortcuts",
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
            "new_visible_namespace_grammar_design": not findings,
            "runtime_adapter_implementation": False,
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
        copied.get("role")
        != "v24704_full220_visible_authority_coverage_repair_audit"
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or copied.get("repair", {}).get("predecessor_superseded") is not True
        or copied.get("coverage", {}).get("adapter_route_eligible_task_count") != 3
        or copied.get("coverage", {}).get("visible_namespace_task_counts", {}).get("who", 0)
        != 0
        or copied.get("authorization")
        != {
            "new_visible_namespace_grammar_design": True,
            "runtime_adapter_implementation": False,
            "fresh_dev64_protocol_or_launch": False,
            "evaluator": False,
            "exact220": False,
            "leaderboard_or_sota": False,
        }
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.47.04 coverage repair audit drifted")
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
                "namespace_counts": audit["coverage"]["visible_namespace_task_counts"],
                "supersedes": str(INVALID_PREDECESSOR),
            },
            sort_keys=True,
        )
    )
