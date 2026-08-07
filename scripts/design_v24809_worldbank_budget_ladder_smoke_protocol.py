#!/usr/bin/env python3
"""Project V2.48.06 private identities into a visible-only V2.48.09 protocol."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24809_worldbank_budget_ladder_smoke_contract as contract  # noqa: E402
from scripts import design_v24806_worldbank_budget_ladder_smoke_population as population  # noqa: E402
from scripts import audit_v24806_worldbank_budget_ladder_smoke_population_publication as population_audit  # noqa: E402


POPULATION_AUDIT = population_audit.OUTPUT


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
        timeout=20, check=True,
    ).stdout.strip()


def _read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(ROOT.resolve()):
        raise RuntimeError(f"V2.48.09 expected ordinary object: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.48.09 expected JSON object")
    return value


def visible_question(group: list[dict[str, Any]]) -> str:
    countries = "\n".join(
        f"{index}. {item['name']} [{item['iso3']}]"
        for index, item in enumerate(group, 1)
    )
    columns = " | ".join(
        [
            "Country",
            *(
                f"{target['label']} [{target['indicator']}] @{target['year']}"
                for target in contract.TARGETS
            ),
        ]
    )
    return (
        "Use public web sources to return one Markdown table about these countries:\n"
        f"<COUNTRIES>\n{countries}\n</COUNTRIES>\n"
        "Please output one Markdown table with the columns, in this exact order:\n"
        f"{columns}\n"
        "Use the World Bank API values. Preserve the decimal representation returned by "
        "the official API. Use Unknown when unavailable. Return one table only."
    )


def project_visible_tasks(private: dict[str, Any]) -> list[dict[str, str]]:
    groups = private.get("groups")
    if not isinstance(groups, list) or len(groups) != contract.SELECTED_COUNT:
        raise RuntimeError("V2.48.09 private population denominator drifted")
    tasks: list[dict[str, str]] = []
    for index, group in enumerate(groups, 1):
        if not isinstance(group, list) or len(group) != 4:
            raise RuntimeError("V2.48.09 private group drifted")
        visible_group = []
        for item in group:
            if not isinstance(item, dict) or not isinstance(item.get("name"), str) or not isinstance(item.get("iso3"), str):
                raise RuntimeError("V2.48.09 private identity drifted")
            visible_group.append({"name": item["name"], "iso3": item["iso3"]})
        tasks.append({
            "opaque_id": f"task_{0x248090 + index:024x}",
            "question": visible_question(visible_group),
        })
    return contract.validate_task_vector(tasks)


def build_protocol(*, now: int | None = None, require_clean: bool = True) -> dict[str, Any]:
    if require_clean and (
        _git("status", "--porcelain")
        or _git("rev-parse", "HEAD") != _git("rev-parse", "target/main")
    ):
        raise RuntimeError("V2.48.09 protocol requires clean pushed HEAD")
    if any(
        (ROOT / path).exists() or (ROOT / path).is_symlink()
        for path in (
            contract.PROTOCOL, contract.PREAUDIT,
            contract.ACTIVATION, contract.EXECUTION_START, contract.FORWARD_RESULT,
            contract.FORWARD_AUDIT, contract.OUTPUT_ROOT,
        )
    ):
        raise RuntimeError("V2.48.09 future surface is not pristine")
    audit = _read(ROOT / POPULATION_AUDIT)
    population_audit.validate_audit(audit)
    build_audit = _read(ROOT / contract.BUILD_AUDIT)
    unsigned_build = dict(build_audit)
    build_seal = unsigned_build.pop("audit_payload_sha256", None)
    if (
        build_audit.get("role")
        != "v24809_worldbank_budget_ladder_smoke_build_audit"
        or build_audit.get("audit_valid") is not True
        or build_audit.get("findings") != []
        or build_audit.get("authorization", {}).get("protocol_generation")
        is not True
        or build_seal != contract.payload_sha256(unsigned_build)
    ):
        raise RuntimeError("V2.48.09 build audit authority drifted")
    private = _read(ROOT / population.PRIVATE)
    tasks = project_visible_tasks(private)
    manifest = contract.dependency_manifest(ROOT)
    value = {
        "artifact_version": 1,
        "role": "v24809_worldbank_budget_ladder_smoke_preregistration",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git_head": _git("rev-parse", "HEAD"),
        "build_audit_sha256": contract.sha256(ROOT / contract.BUILD_AUDIT),
        "population_binding": {
            "public_design_sha256": contract.sha256(ROOT / population.OUTPUT),
            "publication_audit_sha256": contract.sha256(ROOT / POPULATION_AUDIT),
            "private_population_file_sha256": contract.sha256(ROOT / population.PRIVATE),
            "private_population_opened_only_by_protocol_builder": True,
            "private_record_or_value_projected_to_visible_tasks": False,
        },
        "visible_tasks": tasks,
        "task_contract": {
            "runtime_input_keys": ["opaque_id", "question"],
            "selected_count": contract.SELECTED_COUNT,
            "arm_count": contract.ARM_COUNT,
            "opaque_id_vector_sha256": contract.payload_sha256([task["opaque_id"] for task in tasks]),
            "visible_question_vector_sha256": contract.payload_sha256([task["question"] for task in tasks]),
        },
        "execution": {
            "executor_concurrency": contract.EXECUTOR_CONCURRENCY,
            "model_slot_cap": contract.MODEL_SLOT_CAP,
            "model": contract.MODEL,
            "search": contract.SEARCH,
            "limits": contract.LIMITS,
            "adaptive_policy": vars(contract.ADAPTIVE_POLICY),
            "three_arms": [
                "first_wave_only", "fixed_full_budget", "coverage_risk_adaptive"
            ],
            "shared_prefix_hard_barrier": True,
            "prefix_failure_projects_all_arms_to_same_failure": True,
            "no_resume_retry_skip_or_selective_rerun": True,
            "protected_watchers": contract.protected_watcher_snapshot(),
        },
        "dependency_manifest": manifest,
        "dependency_manifest_sha256": contract.payload_sha256(manifest),
        "source_policy": {
            "runtime_reads_only_opaque_id_and_question": True,
            "runtime_dependency_manifest_contains_evaluation_path": False,
            "mapping_gold_category_question_type_split_evaluator_score_reward_read_by_forward": False,
            "entropy_information_gain_feature_weight": 0.0,
            "entropy_assigns_signed_credit": False,
            "smoke_not_main_calibration_lock_validation_or_confirmatory": True,
        },
        "authorization": {
            "preactivation_audit_generation": True,
            "activation": False,
            "single_smoke_forward": False,
            "evaluator": False,
            "main_calibration_lock_validation_or_confirmatory": False,
            "public_dev64_or_exact220": False,
        },
    }
    value["protocol_payload_sha256"] = contract.payload_sha256(value)
    return contract.validate_protocol(ROOT, value)


def publish(path: Path, value: dict[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    protocol = build_protocol()
    publish(ROOT / contract.PROTOCOL, protocol)
    print(json.dumps({
        "path": str(contract.PROTOCOL),
        "selected": contract.SELECTED_COUNT,
        "arms": contract.ARM_COUNT,
        "authorization": protocol["authorization"],
    }, sort_keys=True))
