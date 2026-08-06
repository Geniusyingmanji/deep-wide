#!/usr/bin/env python3
"""Build physically separated V2.46.71 visible and evaluator surfaces."""

from __future__ import annotations

import ast
import csv
import hashlib
import io
import json
import os
import pprint
import re
import subprocess
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24320_forward_contract import payload_sha256  # noqa: E402


DATE = "20260806"
PRIVATE = Path(f"evaluation/v24670_ror_population_private_v1_{DATE}.json")
POPULATION = Path(f"results/v24670_ror_population_design_v1_{DATE}.json")
CONTRACT = Path("src/deepwide_agent/v24671_ror_external_contract.py")
GOLD = Path("evaluation/v24671_ror_gold_v1.csv")
PROVENANCE = Path("evaluation/v24671_ror_gold_provenance_v1.json")
RECORD_ID = re.compile(r"0[0-9a-z]{8}")


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
    ).stdout.strip()


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.46.71 expected object")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def _validate_parents() -> tuple[dict[str, Any], dict[str, Any]]:
    private = _read(ROOT / PRIVATE)
    population = _read(ROOT / POPULATION)
    records = private.get("records")
    if (
        private.get("role") != "v24670_ror_evaluator_only_population"
        or not _sealed(private, "private_payload_sha256")
        or population.get("role") != "v24670_ror_population_design"
        or not _sealed(population, "design_sha256")
        or population.get("selected_count") != 48
        or population.get("historical_entity_count") != 4_576
        or population.get("historical_canonical_count") != 4_576
        or population.get("excluded_v24664_entity_count") != 48
        or population.get("authorization", {}).get(
            "visible_contract_and_evaluator_gold_design"
        )
        is not True
        or population.get("authorization", {}).get("activation_or_launch") is not False
        or population.get("authorization", {}).get("evaluator_access") is not False
        or population.get("private_population_file_sha256") != _sha256(ROOT / PRIVATE)
        or not isinstance(records, Sequence)
        or isinstance(records, (str, bytes))
        or len(records) != 48
    ):
        raise RuntimeError("V2.46.71 population parent drifted")
    for raw in records:
        if not isinstance(raw, Mapping):
            raise RuntimeError("V2.46.71 private record drifted")
        if (
            not str(raw.get("label", ""))
            or any(character in str(raw.get("label")) for character in '|\\"\r\n')
            or RECORD_ID.fullmatch(str(raw.get("record_id", ""))) is None
            or re.fullmatch(r"[A-Z]{2}", str(raw.get("country", ""))) is None
            or re.fullmatch(r"[0-9a-f]{40}", str(raw.get("git_blob_sha1", "")))
            is None
            or re.fullmatch(
                r"[0-9a-f]{64}", str(raw.get("record_bytes_sha256", ""))
            )
            is None
        ):
            raise RuntimeError("V2.46.71 private record field drifted")
    return private, population


def _question(group: Sequence[str]) -> str:
    rows = "\n".join(f"{index}. {entity}" for index, entity in enumerate(group, 1))
    return (
        "Use public web sources to return one Markdown table about these organizations:\n"
        f"<ENTITIES>\n{rows}\n</ENTITIES>\n"
        "The column names are: Organization, ROR ID, Country code. "
        "Use the 9-character ROR ID suffix, not the full URL, and the ISO 3166-1 alpha-2 country code. "
        "Return one table only."
    )


def _contract_text(groups: tuple[tuple[str, ...], ...]) -> str:
    groups_text = pprint.pformat(groups, width=100, sort_dicts=False)
    questions_text = pprint.pformat(
        tuple(_question(group) for group in groups), width=100, sort_dicts=False
    )
    return f'''"""Visible-only contract for V2.46.71 information-gain acquisition."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .v24639_ror_objective_runtime import extract_visible_entities


DATE = "{DATE}"
PROTOCOL_ID = "v24671_visible_surface_information_gain_ror_external_v1"
PROTOCOL = Path(f"results/v24671_information_gain_preregistration_v1_{{DATE}}.json")
PREAUDIT = Path(f"results/v24671_information_gain_preactivation_audit_v1_{{DATE}}.json")
ACTIVATION = Path(f"results/v24671_information_gain_activation_v1_{{DATE}}.json")
EXECUTION_START = Path(f"results/v24671_information_gain_execution_start_v1_{{DATE}}.json")
FORWARD_RESULT = Path(f"results/v24671_information_gain_forward_result_v1_{{DATE}}.json")
FORWARD_AUDIT = Path(f"results/v24671_information_gain_forward_audit_v1_{{DATE}}.json")
OUTPUT_ROOT = Path(f"outputs/v24671_information_gain_v1_{{DATE}}")
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
TASK_ROOT = OUTPUT_ROOT / "tasks"
PREDICTIONS = OUTPUT_ROOT / "frozen_predictions.jsonl"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
RUN_SUMMARY = OUTPUT_ROOT / "run_summary.json"
LEASE_PATH = Path("outputs/deepwide_benchmark_api.lease.lock")
LEASE_OWNER = PROTOCOL_ID
LEASE_PURPOSE = "fresh_external_visible_surface_information_gain_ror"
SELECTED_COUNT = 12
ARM_COUNT = 2
EXECUTOR_CONCURRENCY = 12
MODEL_SLOT_CAP = 8
MODEL_SLOT_POOL_ID = "v24263_score_first_global_model_slots_v1"
TASK_WALL_SECONDS = 180
PARENT_TIMEOUT_SECONDS = 200
CLEANUP_RESERVE_SECONDS = 5.0
MINIMUM_ATTEMPT_SECONDS = 0.05
PROTECTED_WATCHERS = (
    (795336, "scripts/watch_v2415_r1_checkpoint_liveness.py"),
    (3061652, "scripts/watch_v24218_exact220_executor.py"),
)
MODEL = {{
    "proxy_url": "http://127.0.0.1:9878/responses",
    "name": "gpt-5.6-sol",
    "reasoning_effort": "low",
    "service_tier": "priority",
    "timeout_seconds": 180,
    "max_retries": 2,
}}
SEARCH = {{
    "proxy_url": "http://127.0.0.1:9878/responses",
    "model": "gpt-5.6-sol",
    "workers": 1,
    "batch_size": 8,
    "context_size": "medium",
    "max_output_tokens": 7_000,
    "timeout_seconds": 180,
    "max_retries": 2,
    "fetch_workers": 8,
    "fetch_timeout_seconds": 20,
    "hard_fetch_deadline_seconds": 25,
}}
LIMITS = {{
    "wall_seconds": 180,
    "model_calls": 3,
    "search_queries": 4,
    "fetch_targets": 10,
    "search_results_per_query": 3,
    "evidence_chars": 60_000,
    "page_chars": 5_000,
    "plan_output_tokens": 4_000,
    "synthesis_output_tokens": 30_000,
    "repair_output_tokens": 12_000,
}}
TREATMENT = {{
    "generic_query_cap": 2,
    "generic_fetch_cap": 6,
    "unknown_target_cell_cap": 1,
    "targeted_query_cap": 1,
    "targeted_fetch_cap": 4,
    "targeted_fetch_capacity_concentrated_on_one_target": True,
    "visible_title_and_normalized_url_path_information_gain_priority": True,
    "query_text_cannot_self_prove_surface_alignment": True,
    "fetched_page_text_is_only_active_support": True,
    "minimum_independent_local_exact_support_sources": 2,
    "strict_support_closure_preserves_all_declared_evidence_ids": True,
    "proposal_value_changed": False,
    "support_threshold_relaxed": False,
    "epistemic_action_credit_may_be_positive": True,
    "decision_credit_before_safe_change_and_postfreeze_outer_utility": False,
}}

ENTITY_GROUPS = {groups_text}
QUESTIONS = {questions_text}


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def protected_watcher_snapshot(proc_root: Path = Path("/proc")) -> list[dict[str, object]]:
    output = []
    for pid, marker in PROTECTED_WATCHERS:
        stat = proc_root / str(pid) / "stat"
        cmdline = proc_root / str(pid) / "cmdline"
        if not stat.is_file() or not cmdline.is_file():
            raise RuntimeError("V2.46.71 protected watcher is absent")
        raw = stat.read_text(encoding="utf-8")
        suffix = raw[raw.rfind(")") + 2 :].split()
        command = cmdline.read_bytes().replace(b"\\0", b" ").decode(errors="replace")
        if len(suffix) <= 19 or marker not in command:
            raise RuntimeError("V2.46.71 protected watcher identity drifted")
        output.append({{"pid": pid, "marker": marker, "start_ticks": int(suffix[19])}})
    return output


def visible_task(ordinal: int) -> dict[str, str]:
    if isinstance(ordinal, bool) or not isinstance(ordinal, int) or not 1 <= ordinal <= SELECTED_COUNT:
        raise ValueError("V2.46.71 task ordinal drifted")
    value = {{
        "opaque_id": f"task_{{0x246710 + ordinal:024x}}",
        "question": QUESTIONS[ordinal - 1],
    }}
    if extract_visible_entities(value["question"]) != list(ENTITY_GROUPS[ordinal - 1]):
        raise ValueError("V2.46.71 visible task round trip drifted")
    return value


def task_vector() -> list[dict[str, str]]:
    return [visible_task(index) for index in range(1, SELECTED_COUNT + 1)]


__all__ = [name for name in tuple(globals()) if name.isupper()] + [
    "payload_sha256", "protected_watcher_snapshot", "sha256", "task_vector", "visible_task",
]
'''


def build_surfaces() -> dict[Path, str]:
    private, population = _validate_parents()
    records = list(private["records"])
    groups = tuple(
        tuple(str(records[offset + index]["label"]) for index in range(4))
        for offset in range(0, 48, 4)
    )
    source = _contract_text(groups)
    tree = ast.parse(source)
    assignments = {
        target.id: ast.literal_eval(node.value)
        for node in tree.body
        if isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance((target := node.targets[0]), ast.Name)
        and target.id in {"ENTITY_GROUPS", "QUESTIONS"}
    }
    if assignments.get("ENTITY_GROUPS") != groups or assignments.get(
        "QUESTIONS"
    ) != tuple(_question(group) for group in groups):
        raise RuntimeError("V2.46.71 generated visible vectors drifted")
    record_ids = {str(record["record_id"]) for record in records}
    private_hashes = {
        str(record[key])
        for record in records
        for key in ("git_blob_sha1", "record_bytes_sha256")
    }
    if (
        any(record_id in source for record_id in record_ids)
        or any(value in source for value in private_hashes)
        or str(PRIVATE) in source
        or "external_evaluator" in source
        or "evaluation/" in source
    ):
        raise RuntimeError("V2.46.71 visible contract contains evaluator-only data")

    output = io.StringIO(newline="")
    writer = csv.DictWriter(
        output,
        fieldnames=["opaque_id", "Organization", "ROR ID", "Country code"],
        lineterminator="\n",
    )
    writer.writeheader()
    provenance_records = []
    for ordinal, group in enumerate(groups, 1):
        opaque_id = f"task_{0x246710 + ordinal:024x}"
        for entity, record in zip(
            group, records[(ordinal - 1) * 4 : ordinal * 4], strict=True
        ):
            writer.writerow(
                {
                    "opaque_id": opaque_id,
                    "Organization": entity,
                    "ROR ID": record["record_id"],
                    "Country code": record["country"],
                }
            )
            provenance_records.append(
                {
                    "record_id": record["record_id"],
                    "git_blob_sha1": record["git_blob_sha1"],
                    "record_bytes_sha256": record["record_bytes_sha256"],
                }
            )
    provenance = {
        "artifact_version": 1,
        "role": "v24671_ror_gold_provenance",
        "commit": private["commit"],
        "version": private["version"],
        "directory_tree_sha1": private["directory_tree_sha1"],
        "selection_rule": private["selection_rule"],
        "population_design_sha256": _sha256(ROOT / POPULATION),
        "private_population_sha256": _sha256(ROOT / PRIVATE),
        "records": provenance_records,
        "forward_import_or_runtime_read_authorized": False,
        "gold_open_before_prediction_freeze_authorized": False,
    }
    provenance["provenance_payload_sha256"] = payload_sha256(provenance)
    return {
        CONTRACT: source,
        GOLD: output.getvalue(),
        PROVENANCE: json.dumps(
            provenance, ensure_ascii=False, indent=2, sort_keys=True
        )
        + "\n",
    }


def _publish(relative: Path, data: str) -> None:
    path = ROOT / relative
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def main() -> None:
    if _git("status", "--porcelain") or _git("rev-parse", "HEAD") != _git(
        "rev-parse", "target/main"
    ):
        raise RuntimeError("V2.46.71 surface builder requires clean pushed HEAD")
    surfaces = build_surfaces()
    for path, data in surfaces.items():
        _publish(path, data)
    print(
        json.dumps(
            {
                "contract": str(CONTRACT),
                "gold_rows": 48,
                "surface_sha256": {
                    str(path): _sha256(ROOT / path) for path in surfaces
                },
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
