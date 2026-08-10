"""Frozen contract for a shared-output single-column normalization gate.

The population is benchmark-external and consists of previously unused PyPI
project identities.  Each task performs one exact public-page fetch and one
production-prompt GPT-5.6 synthesis.  The raw model output is shared by both
arms; the only arm difference is the frozen V2.42.59 normalizer versus the
append-only V2.50.32 single-column successor.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Any

DATE = "20260810"
PROTOCOL_ID = "v25035_fresh_shared_output_single_column_pypi_gate_v1"
POPULATION_SELECTION_PARENT_COMMIT = (
    "bdb7f4f5f8dadacb02f02551710605bd16825b1c"
)
BUILD_AUDIT = Path(f"results/v25035_single_column_external_build_audit_v1_{DATE}.json")
PROTOCOL = Path(f"results/v25035_single_column_external_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v25035_single_column_external_preactivation_audit_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v25035_single_column_external_execution_start_v1_{DATE}.json")
READINESS = Path(f"results/v25035_single_column_external_readiness_v1_{DATE}.json")
FORWARD_RESULT = Path(f"results/v25035_single_column_external_forward_result_v1_{DATE}.json")
FORWARD_AUDIT = Path(f"results/v25035_single_column_external_forward_audit_v1_{DATE}.json")
EVALUATOR_PROTOCOL = Path(f"results/v25035_single_column_external_evaluator_preregistration_v1_{DATE}.json")
RESULT = Path(f"results/v25035_single_column_external_result_v1_{DATE}.json")
POSTAUDIT = Path(f"results/v25035_single_column_external_postresult_audit_v1_{DATE}.json")

OUTPUT_ROOT = Path(f"outputs/v25035_single_column_external_v1_{DATE}")
TASK_ROWS = OUTPUT_ROOT / "frozen_task_results.jsonl"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
GOLD_SNAPSHOT = OUTPUT_ROOT / "postfreeze_pypi_gold.jsonl"
LEASE_PATH = Path("outputs/deepwide_benchmark_api.lease.lock")

SOURCE = Path("src/deepwide_agent/v25035_single_column_external_contract.py")
NORMALIZER = Path("src/deepwide_agent/v25032_single_column_table_normalizer.py")
SUCCESSOR_RUNTIME = Path("src/deepwide_agent/v25033_single_column_evidence_conditioned_runtime.py")
PARENT_NORMALIZER = Path("src/deepwide_agent/v24259_deterministic_table_normalizer.py")
TABLE_RUNTIME = Path("src/deepwide_agent/v24257_score_first_runtime.py")
RUNNER = Path("scripts/run_v25035_single_column_external.py")
CONTROL = Path("scripts/control_v25035_single_column_external.py")
FINALIZER = Path("scripts/finalize_v25035_single_column_external.py")
TEST = Path("tests/test_v25035_single_column_external.py")
BUILD_PARENT = Path(f"results/v25034_single_column_build_audit_v1_{DATE}.json")

LOCAL_SOURCES = (
    SOURCE,
    NORMALIZER,
    SUCCESSOR_RUNTIME,
    PARENT_NORMALIZER,
    TABLE_RUNTIME,
    RUNNER,
    CONTROL,
    FINALIZER,
    TEST,
    BUILD_PARENT,
)
FORWARD_SOURCES = (
    SOURCE,
    NORMALIZER,
    PARENT_NORMALIZER,
    TABLE_RUNTIME,
    RUNNER,
)

CONTROL_ARM = "frozen_v24259_normalizer"
CANDIDATE_ARM = "v25032_single_column_normalizer"
ARMS = (CONTROL_ARM, CANDIDATE_ARM)
TASK_COUNT = 40
ENGLISH_TASK_COUNT = 20
CHINESE_TASK_COUNT = 20
EXECUTOR_CONCURRENCY = 20
MODEL_CONCURRENCY = 8
FETCH_TARGETS_PER_TASK = 1
MODEL_CALLS_PER_TASK = 1
MODEL_OUTPUT_TOKENS = 1_200
TASK_DEADLINE_SECONDS = 120.0
MAX_RESPONSE_BYTES = 32_000_000
FETCH_CONNECT_TIMEOUT_SECONDS = 5.0
FETCH_READ_TIMEOUT_SECONDS = 45.0
ENDPOINT = "http://127.0.0.1:9878/responses"
MODEL = "gpt-5.6-sol"
REASONING_EFFORT = "low"
SERVICE_TIER = "priority"
MODEL_TIMEOUT_SECONDS = 65.0
MINIMUM_NATURAL_RECOVERIES = 1
LEASE_OWNER = "v25035_single_column_external_forward_v1"
LEASE_PURPOSE = "fresh_shared_model_output_single_column_normalizer_gate"

COLUMN_EN = "Current published PyPI package version (verbatim)"
COLUMN_ZH = "PyPI 当前发布版本（保留原始拼写）"
FALLBACK_EN = "Unknown"
FALLBACK_ZH = "未知"

PROJECTS = (
    "cycler",
    "fonttools",
    "kiwisolver",
    "contourpy",
    "rfc3986",
    "fqdn",
    "isoduration",
    "jsonpointer",
    "uri-template",
    "webcolors",
    "pandocfilters",
    "bleach",
    "tinycss2",
    "webencodings",
    "fastjsonschema",
    "prometheus-client",
    "argon2-cffi",
    "argon2-cffi-bindings",
    "jupyter-events",
    "jupyter-lsp",
    "jupyterlab-pygments",
    "nbclassic",
    "notebook-shim",
    "async-lru",
    "jupyter-server-terminals",
    "python-json-logger",
    "rfc3339-validator",
    "rfc3987-syntax",
    "json5",
    "debugpy",
    "ipykernel",
    "ipywidgets",
    "widgetsnbextension",
    "jupyterlab-widgets",
    "jupyter-console",
    "jupyterlab-server",
    "jsonschema-specifications",
    "mdurl",
    "propcache",
    "aiohappyeyeballs",
)

# Freshness is proved against the complete repository tree at
# POPULATION_SELECTION_PARENT_COMMIT, not by an incomplete hand-maintained
# project allow/block list.  Keeping this set empty also avoids importing any
# historical external/evaluator contract into the forward dependency closure.
PRIOR_PROJECTS: frozenset[str] = frozenset()
OPAQUE = re.compile(r"task_[0-9a-f]{24}")
EXPECTED_WATCHERS = (
    (795336, 713986317, "scripts/watch_v2415_r1_checkpoint_liveness.py"),
    (3061652, 747569004, "scripts/watch_v24218_exact220_executor.py"),
    (2808901, 746680268, "scripts/watch_v24215_joint_package_recovery.py"),
    (2889939, 746969965, "scripts/watch_v24216_package_gate.py"),
)


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def seal(value: Mapping[str, Any], field: str) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    copied.pop(field, None)
    copied[field] = payload_sha256(copied)
    return copied


def sealed(value: Mapping[str, Any], field: str) -> bool:
    copied = copy.deepcopy(dict(value))
    observed = copied.pop(field, None)
    return isinstance(observed, str) and observed == payload_sha256(copied)


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=20,
        check=True,
    ).stdout.strip()


def ordinary(root: Path, relative: Path, *, tracked: bool) -> Path:
    path = root / relative
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(root.resolve())
    ):
        raise RuntimeError(f"V2.50.35 expected ordinary repository file: {relative}")
    if tracked:
        completed = subprocess.run(
            ["git", "ls-files", "--error-unmatch", str(relative)],
            cwd=root,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=20,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(f"V2.50.35 expected tracked file: {relative}")
    return path


def proc_start_ticks(pid: int, proc_root: Path = Path("/proc")) -> int:
    raw = (proc_root / str(pid) / "stat").read_text(encoding="utf-8")
    suffix = raw[raw.rfind(")") + 2 :].split()
    if len(suffix) <= 19:
        raise RuntimeError("V2.50.35 malformed process stat")
    return int(suffix[19])


def watcher_snapshot(proc_root: Path = Path("/proc")) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for pid, expected_ticks, marker in EXPECTED_WATCHERS:
        command = (
            (proc_root / str(pid) / "cmdline")
            .read_bytes()
            .replace(b"\0", b" ")
            .decode("utf-8", errors="replace")
        )
        ticks = proc_start_ticks(pid, proc_root)
        if ticks != expected_ticks or marker not in command:
            raise RuntimeError("V2.50.35 protected watcher drifted")
        rows.append({"pid": pid, "start_ticks": ticks, "marker": marker})
    return rows


def column_for_index(index: int) -> str:
    if not 0 <= index < TASK_COUNT:
        raise ValueError("V2.50.35 task index drifted")
    return COLUMN_EN if index < ENGLISH_TASK_COUNT else COLUMN_ZH


def marker_for_index(index: int) -> str:
    return FALLBACK_EN if index < ENGLISH_TASK_COUNT else FALLBACK_ZH


def task_vector() -> list[dict[str, str]]:
    if (
        len(PROJECTS) != TASK_COUNT
        or len(set(PROJECTS)) != TASK_COUNT
        or set(PROJECTS) & PRIOR_PROJECTS
        or ENGLISH_TASK_COUNT + CHINESE_TASK_COUNT != TASK_COUNT
    ):
        raise RuntimeError("V2.50.35 fresh population drifted")
    rows: list[dict[str, str]] = []
    for index, project in enumerate(PROJECTS):
        opaque_id = "task_" + hashlib.sha256(
            f"v25035:{index}:{project}".encode("utf-8")
        ).hexdigest()[:24]
        if index < ENGLISH_TASK_COUNT:
            question = (
                "Using only the supplied public page, return exactly one fenced "
                "Markdown table and no prose. Include exactly one data row. "
                f"The visible PyPI package is <PACKAGE>{project}</PACKAGE>.\n"
                f"Column names: {COLUMN_EN}.\n"
                "Put only the current published version string in the cell; do "
                "not include the package name. Preserve spelling, punctuation, "
                "and letter case. Use Unknown only when the supplied page does "
                "not establish the version."
            )
        else:
            question = (
                "仅使用所提供的公开页面，输出且只输出一个带代码围栏的 Markdown "
                "表格。表格必须恰好包含一行数据，不要附加说明。可见的 PyPI 软件包为 "
                f"<PACKAGE>{project}</PACKAGE>。\n"
                f"列名依次为：{COLUMN_ZH}。\n"
                "单元格中只能填写当前公开版本号，不要填写软件包名称；保留版本号的原始"
                "拼写、标点和大小写。只有页面无法确定版本时才填写“未知”。"
            )
        rows.append({"opaque_id": opaque_id, "question": question})
    if any(set(row) != {"opaque_id", "question"} for row in rows):
        raise RuntimeError("V2.50.35 runtime boundary drifted")
    return rows


def endpoint_vector() -> list[str]:
    return [f"https://pypi.org/pypi/{project}/json" for project in PROJECTS]


def gates() -> dict[str, Any]:
    return {
        "mechanism": {
            "fixed_denominator": TASK_COUNT,
            "fetch_successes": TASK_COUNT,
            "model_successes": TASK_COUNT,
            "shared_raw_model_outputs": TASK_COUNT,
            "model_provider_attempts": TASK_COUNT,
            "minimum_candidate_natural_recoveries": MINIMUM_NATURAL_RECOVERIES,
            "candidate_fallback_strictly_less": True,
            "nonempty_factual_cell_rewrite_count": 0,
            "additional_model_search_or_fetch_calls": 0,
            "multi_column_or_extra_row_admission_count": 0,
        },
        "quality": {
            "fixed_denominator": TASK_COUNT,
            "candidate_exact_strictly_greater": True,
            "candidate_cell_accuracy_nonregression": True,
            "candidate_schema_validity_nonregression": True,
            "candidate_evaluator_invalid_nonincrease": True,
            "candidate_fallback_strictly_less": True,
        },
    }


def source_policy() -> dict[str, Any]:
    return {
        "runtime_boundary": [
            "opaque_id",
            "question",
            "same_forward_public_pypi_json",
        ],
        "population_selected_after_repository_literal_zero_probe": True,
        "population_url_model_or_evaluator_probed_before_freeze": False,
        "all_pages_fetched_before_any_model_call": True,
        "readiness_failure_stops_before_model_and_prediction_output": True,
        "one_exact_page_fetch_per_task": True,
        "one_model_call_per_task": True,
        "same_raw_model_output_for_both_arms": True,
        "only_arm_difference_is_deterministic_normalizer": True,
        "production_synthesis_system_and_user_template_used": True,
        "mapping_gold_category_question_type_split_answer_evaluator_score_reward_or_historical_quality_used_for_forward": False,
        "prediction_freeze_before_evaluator_or_gold_refetch": True,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "public_deepwidebench_dev64_exact220_leaderboard_or_sota_authorized": False,
    }


def dependency_manifest(root: Path, *, tracked: bool) -> dict[str, str]:
    return {
        str(relative): sha256(ordinary(root, relative, tracked=tracked))
        for relative in LOCAL_SOURCES
    }


def _build_audit(root: Path, *, tracked: bool) -> dict[str, Any]:
    path = ordinary(root, BUILD_AUDIT, tracked=tracked)
    value = json.loads(path.read_text(encoding="utf-8"))
    if (
        not isinstance(value, dict)
        or value.get("role") != "v25035_single_column_external_build_audit"
        or value.get("audit_valid") is not True
        or value.get("findings") != []
        or not sealed(value, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.50.35 build audit drifted")
    return value


def build_protocol(root: Path, *, now: int, tracked: bool) -> dict[str, Any]:
    build = _build_audit(root, tracked=tracked)
    tasks = task_vector()
    endpoints = endpoint_vector()
    manifest = dependency_manifest(root, tracked=tracked)
    value = {
        "artifact_version": 1,
        "role": "v25035_single_column_external_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(now),
        "build_audit": {
            "path": str(BUILD_AUDIT),
            "sha256": sha256(root / BUILD_AUDIT),
            "payload_sha256": build["audit_payload_sha256"],
        },
        "dependency_manifest": manifest,
        "dependency_manifest_sha256": payload_sha256(manifest),
        "population": {
            "task_count": TASK_COUNT,
            "english_tasks": ENGLISH_TASK_COUNT,
            "chinese_tasks": CHINESE_TASK_COUNT,
            "task_vector_sha256": payload_sha256(tasks),
            "opaque_id_vector_sha256": payload_sha256(
                [row["opaque_id"] for row in tasks]
            ),
            "visible_question_vector_sha256": payload_sha256(
                [row["question"] for row in tasks]
            ),
            "endpoint_vector_sha256": payload_sha256(endpoints),
            "project_vector_sha256": payload_sha256(list(PROJECTS)),
            "prior_population_overlap_count": len(set(PROJECTS) & PRIOR_PROJECTS),
            "final_population_url_model_or_evaluator_probe_count": 0,
        },
        "execution": {
            "executor_concurrency": EXECUTOR_CONCURRENCY,
            "model_concurrency": MODEL_CONCURRENCY,
            "fetch_targets_per_task": FETCH_TARGETS_PER_TASK,
            "model_calls_per_task": MODEL_CALLS_PER_TASK,
            "model_output_tokens": MODEL_OUTPUT_TOKENS,
            "task_deadline_seconds": TASK_DEADLINE_SECONDS,
            "max_response_bytes": MAX_RESPONSE_BYTES,
            "model": MODEL,
            "reasoning_effort": REASONING_EFFORT,
            "service_tier": SERVICE_TIER,
            "failure_as_zero": True,
            "retry_resume_skip_or_population_replacement": False,
        },
        "arms": {
            "control": CONTROL_ARM,
            "candidate": CANDIDATE_ARM,
            "shared_raw_model_output": True,
            "only_difference": "deterministic_table_normalizer",
        },
        "gates": gates(),
        "source_policy": source_policy(),
        "protected_watchers": watcher_snapshot(),
        "future_surfaces": {
            "output_root": str(OUTPUT_ROOT),
            "readiness": str(READINESS),
            "forward_result": str(FORWARD_RESULT),
            "forward_audit": str(FORWARD_AUDIT),
            "evaluator_protocol": str(EVALUATOR_PROTOCOL),
            "result": str(RESULT),
            "postaudit": str(POSTAUDIT),
        },
        "authorization": {
            "preactivation_audit_generation": True,
            "external_forward": False,
            "postfreeze_evaluator": False,
            "new_deepwidebench_exact220": False,
            "leaderboard_or_sota": False,
        },
    }
    return seal(value, "protocol_payload_sha256")


def validate_protocol(root: Path, value: Mapping[str, Any], *, tracked: bool) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    tasks = task_vector()
    expected_manifest = dependency_manifest(root, tracked=tracked)
    population = copied.get("population") or {}
    execution = copied.get("execution") or {}
    arms = copied.get("arms") or {}
    authorization = copied.get("authorization") or {}
    if (
        copied.get("artifact_version") != 1
        or copied.get("role") != "v25035_single_column_external_preregistration"
        or copied.get("protocol_id") != PROTOCOL_ID
        or not sealed(copied, "protocol_payload_sha256")
        or copied.get("dependency_manifest") != expected_manifest
        or copied.get("dependency_manifest_sha256") != payload_sha256(expected_manifest)
        or population.get("task_count") != TASK_COUNT
        or population.get("english_tasks") != ENGLISH_TASK_COUNT
        or population.get("chinese_tasks") != CHINESE_TASK_COUNT
        or population.get("task_vector_sha256") != payload_sha256(tasks)
        or population.get("endpoint_vector_sha256") != payload_sha256(endpoint_vector())
        or population.get("prior_population_overlap_count") != 0
        or population.get("final_population_url_model_or_evaluator_probe_count") != 0
        or execution
        != {
            "executor_concurrency": EXECUTOR_CONCURRENCY,
            "model_concurrency": MODEL_CONCURRENCY,
            "fetch_targets_per_task": 1,
            "model_calls_per_task": 1,
            "model_output_tokens": MODEL_OUTPUT_TOKENS,
            "task_deadline_seconds": TASK_DEADLINE_SECONDS,
            "max_response_bytes": MAX_RESPONSE_BYTES,
            "model": MODEL,
            "reasoning_effort": REASONING_EFFORT,
            "service_tier": SERVICE_TIER,
            "failure_as_zero": True,
            "retry_resume_skip_or_population_replacement": False,
        }
        or arms.get("control") != CONTROL_ARM
        or arms.get("candidate") != CANDIDATE_ARM
        or arms.get("shared_raw_model_output") is not True
        or copied.get("gates") != gates()
        or copied.get("source_policy") != source_policy()
        or copied.get("protected_watchers") != watcher_snapshot()
        or authorization
        != {
            "preactivation_audit_generation": True,
            "external_forward": False,
            "postfreeze_evaluator": False,
            "new_deepwidebench_exact220": False,
            "leaderboard_or_sota": False,
        }
    ):
        raise RuntimeError("V2.50.35 protocol drifted")
    _build_audit(root, tracked=tracked)
    return copied


__all__ = [name for name in globals() if name.isupper()] + [
    "build_protocol",
    "column_for_index",
    "dependency_manifest",
    "endpoint_vector",
    "gates",
    "git",
    "marker_for_index",
    "ordinary",
    "payload_sha256",
    "proc_start_ticks",
    "seal",
    "sealed",
    "sha256",
    "source_policy",
    "task_vector",
    "validate_protocol",
    "watcher_snapshot",
]
