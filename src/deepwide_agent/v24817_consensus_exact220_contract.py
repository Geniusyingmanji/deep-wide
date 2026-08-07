"""Contract for a label-blind consensus over three frozen exact-220 rollouts."""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from . import v24800_exact220_contract as source00
from . import v24807_exact220_contract as source07
from . import v24810_exact220_contract as source10


DATE = "20260807"
PROTOCOL_ID = "v24817_three_rollout_label_blind_consensus_exact220_v1"
BUILD_AUDIT = Path(f"results/v24817_consensus_exact220_build_audit_v1_{DATE}.json")
PROTOCOL = Path(f"results/v24817_consensus_exact220_preregistration_v1_{DATE}.json")
PREDICTION_FREEZE = Path(f"outputs/v24817_consensus_exact220_v1_{DATE}/prediction_freeze.json")
RUNTIME_PREDICTIONS = Path(f"outputs/v24817_consensus_exact220_v1_{DATE}/runtime_predictions.jsonl")
RUN_SUMMARY = Path(f"outputs/v24817_consensus_exact220_v1_{DATE}/run_summary.json")
OUTPUT_ROOT = Path(f"outputs/v24817_consensus_exact220_v1_{DATE}")
FORWARD_RESULT = Path(f"results/v24817_consensus_exact220_forward_result_v1_{DATE}.json")
FORWARD_AUDIT = Path(f"results/v24817_consensus_exact220_forward_audit_v1_{DATE}.json")
SELECTED_COUNT = 220
PROTECTED_WATCHERS = source00.PROTECTED_WATCHERS
LEASE_PATH = source00.LEASE_PATH
GENERATOR_MARKER = "scripts/generate_v24817_consensus_exact220.py"
SOURCE_RUNS = (
    {
        "name": "v24800",
        "contract": source00,
        "protocol": source00.PROTOCOL,
        "forward_result": source00.FORWARD_RESULT,
        "prediction_freeze": source00.PREDICTION_FREEZE,
        "runtime_predictions": source00.RUNTIME_PREDICTIONS,
        "expected_forward_role": "v24800_exact220_forward_result",
        "expected_freeze_role": "v24800_exact220_prediction_freeze",
    },
    {
        "name": "v24807",
        "contract": source07,
        "protocol": source07.PROTOCOL,
        "forward_result": source07.FORWARD_RESULT,
        "prediction_freeze": source07.PREDICTION_FREEZE,
        "runtime_predictions": source07.RUNTIME_PREDICTIONS,
        "expected_forward_role": "v24807_exact220_forward_result",
        "expected_freeze_role": "v24807_exact220_prediction_freeze",
    },
    {
        "name": "v24810",
        "contract": source10,
        "protocol": source10.PROTOCOL,
        "forward_result": source10.FORWARD_RESULT,
        "prediction_freeze": source10.PREDICTION_FREEZE,
        "runtime_predictions": source10.RUNTIME_PREDICTIONS,
        "expected_forward_role": "v24807_exact220_forward_result",
        "expected_freeze_role": "v24807_exact220_prediction_freeze",
    },
)
LOCAL_SOURCES = (
    Path("src/deepwide_agent/v24816_label_blind_consensus.py"),
    Path("src/deepwide_agent/v24817_consensus_exact220_contract.py"),
    Path("scripts/control_v24817_consensus_exact220.py"),
    Path("scripts/generate_v24817_consensus_exact220.py"),
    Path("scripts/audit_v24817_consensus_exact220_forward.py"),
    Path("tests/test_v24816_label_blind_consensus.py"),
    Path("tests/test_v24817_consensus_exact220.py"),
)


payload_sha256 = source00.payload_sha256
sha256 = source00.sha256
protected_watcher_snapshot = source00.protected_watcher_snapshot


def _read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"V2.48.17 expected ordinary object: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.48.17 expected JSON object")
    return value


def _jsonl(path: Path) -> list[dict[str, Any]]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"V2.48.17 expected ordinary JSONL: {path}")
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if any(not isinstance(row, dict) for row in rows):
        raise RuntimeError("V2.48.17 expected JSONL objects")
    return rows


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=root, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
        timeout=20, check=True,
    ).stdout.strip()


def _ordinary_tracked(root: Path, relative: Path) -> Path:
    path = root / relative
    tracked = subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(relative)], cwd=root,
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, timeout=20, check=False,
    ).returncode == 0
    if (
        relative.is_absolute() or ".." in relative.parts
        or relative.parts[:1] in {("evaluation",), ("outputs",)}
        or path.is_symlink() or not path.is_file()
        or not path.resolve().is_relative_to(root.resolve()) or not tracked
    ):
        raise RuntimeError(f"V2.48.17 expected tracked source: {relative}")
    return path


def task_vector(root: Path) -> list[dict[str, str]]:
    tasks = source00.task_vector(root)
    if len(tasks) != SELECTED_COUNT or any(
        set(task) != {"opaque_id", "question"} for task in tasks
    ):
        raise RuntimeError("V2.48.17 visible task vector drifted")
    return tasks


def source_bundle(root: Path) -> dict[str, Any]:
    tasks = task_vector(root)
    expected_ids = [task["opaque_id"] for task in tasks]
    bundles = []
    for specification in SOURCE_RUNS:
        module = specification["contract"]
        protocol = module.validate_protocol(root, _read(root / specification["protocol"]))
        source_tasks = module.task_vector(root, protocol)
        forward = _read(root / specification["forward_result"])
        freeze = _read(root / specification["prediction_freeze"])
        rows = _jsonl(root / specification["runtime_predictions"])
        if (
            source_tasks != tasks
            or forward.get("role") != specification["expected_forward_role"]
            or forward.get("protocol_id") != module.PROTOCOL_ID
            or forward.get("selected") != SELECTED_COUNT
            or forward.get("terminal_predictions") != SELECTED_COUNT
            or forward.get("all_220_predictions_terminal_before_mapping_or_evaluator_open")
            is not True
            or forward.get("mapping_gold_category_question_type_split_evaluator_score_reward_read")
            is not False
            or forward.get("official_evaluator_called") is not False
            or not _sealed(forward, "result_payload_sha256")
            or freeze.get("role") != specification["expected_freeze_role"]
            or freeze.get("protocol_id") != module.PROTOCOL_ID
            or freeze.get("selected") != SELECTED_COUNT
            or freeze.get("terminal") != SELECTED_COUNT
            or freeze.get("mapping_gold_or_evaluator_opened_or_hashed") is not False
            or freeze.get("runtime_predictions_sha256")
            != sha256(root / specification["runtime_predictions"])
            or not _sealed(freeze, "freeze_payload_sha256")
            or len(rows) != SELECTED_COUNT
            or [row.get("opaque_id") for row in rows] != expected_ids
            or any(
                row.get("status") != "completed"
                or row.get("label_blind") is not True
                or row.get(
                    "mapping_gold_category_question_type_split_evaluator_score_read"
                ) is not False
                or not isinstance(row.get("prediction"), str)
                or not row["prediction"].strip()
                or row.get("prediction_sha256")
                != hashlib.sha256(row["prediction"].encode()).hexdigest()
                for row in rows
            )
        ):
            raise RuntimeError(
                f"V2.48.17 source bundle drifted: {specification['name']}"
            )
        bundles.append(
            {
                "name": specification["name"],
                "protocol_sha256": sha256(root / specification["protocol"]),
                "forward_result_sha256": sha256(
                    root / specification["forward_result"]
                ),
                "prediction_freeze_sha256": sha256(
                    root / specification["prediction_freeze"]
                ),
                "runtime_predictions_sha256": sha256(
                    root / specification["runtime_predictions"]
                ),
                "rows": rows,
            }
        )
    return {
        "task_vector": tasks,
        "sources": bundles,
        "source_prediction_files": SELECTED_COUNT * len(bundles),
    }


def dependency_manifest(root: Path) -> dict[str, str]:
    return {
        str(relative): sha256(_ordinary_tracked(root, relative))
        for relative in sorted(LOCAL_SOURCES, key=str)
    }


def validate_protocol(root: Path, value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("protocol_payload_sha256", None)
    tasks = task_vector(root)
    sources = source_bundle(root)["sources"]
    source_bindings = [
        {key: item[key] for key in item if key != "rows"} for item in sources
    ]
    manifest = dependency_manifest(root)
    if (
        copied.get("role") != "v24817_consensus_exact220_preregistration"
        or copied.get("protocol_id") != PROTOCOL_ID
        or seal != payload_sha256(unsigned)
        or copied.get("build_audit_sha256") != sha256(root / BUILD_AUDIT)
        or copied.get("task_contract") != {
            "runtime_input_keys": ["opaque_id", "question"],
            "selected_count": SELECTED_COUNT,
            "opaque_id_vector_sha256": payload_sha256(
                [task["opaque_id"] for task in tasks]
            ),
            "visible_question_vector_sha256": payload_sha256(
                [task["question"] for task in tasks]
            ),
        }
        or copied.get("source_rollouts") != source_bindings
        or copied.get("dependency_manifest") != manifest
        or copied.get("dependency_manifest_sha256") != payload_sha256(manifest)
        or copied.get("protected_watchers") != protected_watcher_snapshot()
        or copied.get("authorization") != {
            "one_label_blind_consensus_generation": True,
            "mapping_gold_or_evaluator_access": False,
            "selective_task_generation": False,
            "leaderboard_or_sota_claim": False,
        }
    ):
        raise RuntimeError("V2.48.17 protocol drifted")
    return copied


__all__ = [name for name in globals() if name.isupper()] + [
    "dependency_manifest", "payload_sha256", "protected_watcher_snapshot",
    "sha256", "source_bundle", "task_vector", "validate_protocol",
]
