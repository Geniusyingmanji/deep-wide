"""Atomic shared-byte external gate for V2.50.47 representation."""

from __future__ import annotations

import ast
import copy
import hashlib
import json
import re
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Any

DATE = "20260811"
PROTOCOL_ID = "v25048_atomic_shared_pypi_current_record_quality_v1"
BUILD_AUDIT = Path(f"results/v25048_atomic_pypi_build_audit_v1_{DATE}.json")
PROTOCOL = Path(f"results/v25048_atomic_pypi_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v25048_atomic_pypi_preactivation_audit_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v25048_atomic_pypi_execution_start_v1_{DATE}.json")
PARSER_READINESS = Path(f"results/v25048_atomic_pypi_parser_readiness_v1_{DATE}.json")
FORWARD_RESULT = Path(f"results/v25048_atomic_pypi_forward_result_v1_{DATE}.json")
FORWARD_AUDIT = Path(f"results/v25048_atomic_pypi_forward_audit_v1_{DATE}.json")
EVALUATOR = Path("scripts/evaluate_v25048_atomic_pypi_representation.py")
EVALUATOR_TEST = Path("tests/test_evaluate_v25048_atomic_pypi_representation.py")
EVALUATOR_PROTOCOL = Path(f"results/v25048_atomic_pypi_evaluator_preregistration_v1_{DATE}.json")
RESULT = Path(f"results/v25048_atomic_pypi_result_v1_{DATE}.json")
POSTAUDIT = Path(f"results/v25048_atomic_pypi_postresult_audit_v1_{DATE}.json")
OUTPUT_ROOT = Path(f"outputs/v25048_atomic_pypi_representation_v1_{DATE}")
TASK_ROWS = OUTPUT_ROOT / "frozen_task_results.jsonl"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
PUBLIC_SNAPSHOT = OUTPUT_ROOT / "postprediction_public_pypi_snapshot.jsonl"

SOURCE = Path("src/deepwide_agent/v25047_pypi_current_record_representation.py")
CONTRACT = Path("src/deepwide_agent/v25048_atomic_pypi_representation_contract.py")
RUNNER = Path("scripts/run_v25048_atomic_pypi_representation.py")
CONTROL = Path("scripts/control_v25048_atomic_pypi_representation.py")
TEST = Path("tests/test_v25048_atomic_pypi_representation.py")
FORWARD_SOURCES = (SOURCE, CONTRACT, RUNNER)
LOCAL_SOURCES = (SOURCE, CONTRACT, RUNNER, CONTROL, TEST)

ARMS = ("raw_pypi_json_prefix", "identity_bound_current_release_record")
CONTROL_ARM, CANDIDATE_ARM = ARMS
TASK_COUNT = 20
EXECUTOR_CONCURRENCY = 20
MODEL_CONCURRENCY = 8
EVIDENCE_CHARS = 12_000
MODEL_OUTPUT_TOKENS = 2_400
TASK_DEADLINE_SECONDS = 180.0
FETCH_TIMEOUT = (5.0, 60.0)
MAX_RESPONSE_BYTES = 64 * 1024 * 1024
MINIMUM_PREDICTION_CHANGES = 8
ENDPOINT = "http://127.0.0.1:9878/responses"
MODEL = "gpt-5.6-sol"
LEASE_PATH = Path("outputs/deepwide_benchmark_api.lease.lock")
EXPECTED_WATCHERS = (
    (795336, 713986317, "scripts/watch_v2415_r1_checkpoint_liveness.py"),
    (3061652, 747569004, "scripts/watch_v24218_exact220_executor.py"),
    (2808901, 746680268, "scripts/watch_v24215_joint_package_recovery.py"),
    (2889939, 746969965, "scripts/watch_v24216_package_gate.py"),
)
FRESHNESS_PARENT_COMMIT = "4a0017d81a105e10fae0778dcef858725771a136"

PROJECTS = (
    "gunicorn", "granian", "waitress", "pyramid", "litestar", "starlite",
    "connexion", "fastapi-utils", "fastapi-pagination", "starlette-context",
    "asgiref", "chameleon", "celery", "dramatiq", "huey", "apscheduler",
    "taskiq", "kombu", "amqp", "billiard",
)
COLUMNS = (
    "Package",
    "Latest version",
    "Latest release date (YYYY-MM-DD)",
    "Requires-Python",
)
FALLBACK_TABLE = (
    "| Package | Latest version | Latest release date (YYYY-MM-DD) | Requires-Python |\n"
    "| --- | --- | --- | --- |\n"
    "| Unknown | Unknown | Unknown | Unknown |"
)
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}"
)


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
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
        raise RuntimeError("V2.50.48 expected ordinary repository file")
    if tracked and subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(relative)],
        cwd=root,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=20,
        check=False,
    ).returncode != 0:
        raise RuntimeError("V2.50.48 expected tracked repository file")
    return path


def watcher_snapshot(proc_root: Path = Path("/proc")) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for pid, expected_ticks, marker in EXPECTED_WATCHERS:
        stat = proc_root / str(pid) / "stat"
        cmdline = proc_root / str(pid) / "cmdline"
        if not stat.is_file() or not cmdline.is_file():
            raise RuntimeError("V2.50.48 protected watcher absent")
        raw = stat.read_text(encoding="utf-8")
        suffix = raw[raw.rfind(")") + 2 :].split()
        command = cmdline.read_bytes().replace(b"\0", b" ").decode(errors="replace")
        if (
            len(suffix) <= 19
            or int(suffix[19]) != expected_ticks
            or marker not in command
        ):
            raise RuntimeError("V2.50.48 protected watcher identity drifted")
        rows.append({"pid": pid, "start_ticks": expected_ticks, "marker": marker})
    return rows


def task_vector() -> list[dict[str, str]]:
    if len(PROJECTS) != TASK_COUNT or len(set(PROJECTS)) != TASK_COUNT:
        raise RuntimeError("V2.50.48 project vector drifted")
    rows = []
    for project in PROJECTS:
        opaque = "task_" + hashlib.sha256(
            f"v25048:{project}".encode()
        ).hexdigest()[:24]
        question = (
            "Using only the supplied public PyPI response, return exactly one "
            "Markdown table and no prose. Include exactly one row for the Python "
            f"package {project}. Columns exactly: " + " | ".join(COLUMNS)
            + ". Use the canonical PyPI project name in Package. Latest release "
            "date means the earliest file upload date under releases[info.version], "
            "in YYYY-MM-DD form. Preserve the Requires-Python expression while "
            "collapsing whitespace. Use Unknown only when the response does not "
            "establish a value."
        )
        rows.append({"opaque_id": opaque, "question": question})
    return rows


def endpoint_vector() -> list[str]:
    return [f"https://pypi.org/pypi/{project}/json" for project in PROJECTS]


def arm_order_vector() -> list[list[str]]:
    ranked = sorted(
        range(TASK_COUNT),
        key=lambda index: hashlib.sha256(
            f"v25048-arm-order:{task_vector()[index]['opaque_id']}".encode()
        ).hexdigest(),
    )
    candidate_first = set(ranked[: TASK_COUNT // 2])
    return [
        [CANDIDATE_ARM, CONTROL_ARM]
        if index in candidate_first
        else [CONTROL_ARM, CANDIDATE_ARM]
        for index in range(TASK_COUNT)
    ]


def source_policy() -> dict[str, Any]:
    return {
        "runtime_boundary": ["opaque_id", "question", "same_forward_public_pypi_bytes"],
        "final_population_endpoint_page_answer_model_or_evaluator_not_probed_before_freeze": True,
        "all_twenty_responses_fetched_and_parsed_before_any_model_call": True,
        "parser_readiness_failure_stops_before_output_root_and_model": True,
        "same_exact_response_bytes_underlie_both_arms": True,
        "control_is_fixed_raw_json_prefix": True,
        "candidate_is_identity_bound_current_record_then_same_raw_prefix": True,
        "same_evidence_chars_prompt_model_output_cap_attempt_count_and_deadline": True,
        "only_treatment_is_evidence_representation": True,
        "public_snapshot_published_only_after_both_arm_predictions": True,
        "prediction_freeze_before_evaluator_module_or_quality_decision": True,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read_by_forward": False,
        "entropy_or_information_gain_assigns_credit_or_routes": False,
        "deepwidebench_dev64_exact220_leaderboard_or_sota_authorized": False,
    }


def gates() -> dict[str, Any]:
    return {
        "readiness": {
            "tasks": TASK_COUNT,
            "fetch_attempts": TASK_COUNT,
            "fetch_successes": TASK_COUNT,
            "parser_ready_tasks": TASK_COUNT,
            "bound_fields": TASK_COUNT * 4,
            "maximum_unknown_bound_fields": TASK_COUNT,
            "model_calls_before_go": 0,
        },
        "mechanism": {
            "terminal_tasks": TASK_COUNT,
            "completed_tasks": TASK_COUNT,
            "fallback_tasks": 0,
            "model_successes_per_arm": TASK_COUNT,
            "model_attempts_per_arm": TASK_COUNT,
            "evidence_chars_per_arm": TASK_COUNT * EVIDENCE_CHARS,
            "minimum_prediction_changed_tasks": MINIMUM_PREDICTION_CHANGES,
        },
        "quality": {
            "fixed_denominator": TASK_COUNT,
            "candidate_exact_strict_gain": True,
            "entity_row_item_column_composite_nonregression": True,
            "invalid_and_fallback_nonincrease": True,
        },
    }


def forward_dependency_closure(root: Path) -> tuple[Path, ...]:
    pending = list(FORWARD_SOURCES)
    observed: set[Path] = set()
    while pending:
        relative = pending.pop()
        if relative in observed:
            continue
        path = ordinary(root, relative, tracked=False)
        observed.add(relative)
        if path.suffix != ".py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            candidates: list[Path] = []
            if isinstance(node, ast.Import):
                for item in node.names:
                    if item.name.startswith("deepwide_agent."):
                        candidates.append(Path("src") / Path(*item.name.split(".")).with_suffix(".py"))
                    elif item.name.startswith("scripts."):
                        candidates.append(Path(*item.name.split(".")).with_suffix(".py"))
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if node.level and relative.parts[:2] == ("src", "deepwide_agent"):
                    if module:
                        candidates.append(Path("src/deepwide_agent") / Path(*module.split(".")).with_suffix(".py"))
                    else:
                        candidates.extend(Path("src/deepwide_agent") / f"{item.name}.py" for item in node.names)
                elif module == "deepwide_agent":
                    candidates.extend(Path("src/deepwide_agent") / f"{item.name}.py" for item in node.names)
                elif module.startswith("deepwide_agent."):
                    candidates.append(Path("src") / Path(*module.split(".")).with_suffix(".py"))
                elif module == "scripts":
                    candidates.extend(Path("scripts") / f"{item.name}.py" for item in node.names)
                elif module.startswith("scripts."):
                    candidates.append(Path(*module.split(".")).with_suffix(".py"))
            for candidate in candidates:
                if (root / candidate).is_file() and not (root / candidate).is_symlink():
                    pending.append(candidate)
    return tuple(sorted(observed, key=str))


def dependency_manifest(root: Path, *, tracked: bool) -> dict[str, str]:
    relatives = {*forward_dependency_closure(root), CONTROL, TEST}
    output: dict[str, str] = {}
    for relative in sorted(relatives, key=str):
        path = ordinary(root, relative, tracked=tracked)
        if SECRET.search(path.read_text(encoding="utf-8")):
            raise RuntimeError("V2.50.48 credential literal in source manifest")
        output[str(relative)] = sha256(path)
    return output


def build_protocol(
    root: Path,
    *,
    now: int,
    tracked: bool,
    require_pristine: bool,
    build_audit_sha256: str,
) -> dict[str, Any]:
    future = (
        PROTOCOL, PREAUDIT, EXECUTION_START, PARSER_READINESS, FORWARD_RESULT,
        FORWARD_AUDIT, EVALUATOR, EVALUATOR_TEST, EVALUATOR_PROTOCOL, RESULT,
        POSTAUDIT, OUTPUT_ROOT,
    )
    if require_pristine and any((root / path).exists() or (root / path).is_symlink() for path in future):
        raise RuntimeError("V2.50.48 future surface is not pristine")
    manifest = dependency_manifest(root, tracked=tracked)
    value = {
        "artifact_version": 1,
        "role": "v25048_atomic_pypi_representation_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(now),
        "build_audit_sha256": build_audit_sha256,
        "freshness": {
            "parent_commit": FRESHNESS_PARENT_COMMIT,
            "parent_history_literal_zero_hit_projects": list(PROJECTS),
            "endpoint_page_answer_model_or_evaluator_opened_during_selection": False,
        },
        "population": {
            "task_count": TASK_COUNT,
            "project_vector_sha256": payload_sha256(PROJECTS),
            "task_vector_sha256": payload_sha256(task_vector()),
            "endpoint_vector_sha256": payload_sha256(endpoint_vector()),
            "arm_order_vector_sha256": payload_sha256(arm_order_vector()),
        },
        "execution": {
            "arms": list(ARMS),
            "only_treatment": "raw_prefix_vs_identity_bound_current_record_representation",
            "executor_concurrency": EXECUTOR_CONCURRENCY,
            "model_concurrency": MODEL_CONCURRENCY,
            "fetches_per_task": 1,
            "evidence_chars_per_arm": EVIDENCE_CHARS,
            "model_calls_per_arm": 1,
            "model_output_tokens": MODEL_OUTPUT_TOKENS,
            "task_deadline_seconds": TASK_DEADLINE_SECONDS,
            "fetch_timeout": list(FETCH_TIMEOUT),
            "max_response_bytes": MAX_RESPONSE_BYTES,
            "model_endpoint": ENDPOINT,
            "model": MODEL,
        },
        "gates": gates(),
        "protected_watchers": watcher_snapshot(),
        "source_manifest": manifest,
        "source_manifest_sha256": payload_sha256(manifest),
        "source_policy": source_policy(),
        "authorization": {
            "one_atomic_readiness_then_external_forward_after_clean_pushed_start": True,
            "evaluator_only_after_prediction_freeze_and_pushed_forward_audit": True,
            "deepwidebench_dev64_exact220_or_sota": False,
            "retry_resume_population_replacement_or_selective_revaluation": False,
        },
    }
    return seal(value, "protocol_payload_sha256")


def validate_protocol(root: Path, value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    manifest = dependency_manifest(root, tracked=True)
    expected_top = {
        "artifact_version", "role", "protocol_id", "created_at_unix",
        "build_audit_sha256", "freshness", "population", "execution",
        "gates", "protected_watchers", "source_manifest",
        "source_manifest_sha256", "source_policy", "authorization",
        "protocol_payload_sha256",
    }
    expected_population = {
        "task_count", "project_vector_sha256", "task_vector_sha256",
        "endpoint_vector_sha256", "arm_order_vector_sha256",
    }
    expected_authorization = {
        "one_atomic_readiness_then_external_forward_after_clean_pushed_start": True,
        "evaluator_only_after_prediction_freeze_and_pushed_forward_audit": True,
        "deepwidebench_dev64_exact220_or_sota": False,
        "retry_resume_population_replacement_or_selective_revaluation": False,
    }
    expected_freshness = {
        "parent_commit": FRESHNESS_PARENT_COMMIT,
        "parent_history_literal_zero_hit_projects": list(PROJECTS),
        "endpoint_page_answer_model_or_evaluator_opened_during_selection": False,
    }
    expected_execution = {
        "arms": list(ARMS),
        "only_treatment": "raw_prefix_vs_identity_bound_current_record_representation",
        "executor_concurrency": EXECUTOR_CONCURRENCY,
        "model_concurrency": MODEL_CONCURRENCY,
        "fetches_per_task": 1,
        "evidence_chars_per_arm": EVIDENCE_CHARS,
        "model_calls_per_arm": 1,
        "model_output_tokens": MODEL_OUTPUT_TOKENS,
        "task_deadline_seconds": TASK_DEADLINE_SECONDS,
        "fetch_timeout": list(FETCH_TIMEOUT),
        "max_response_bytes": MAX_RESPONSE_BYTES,
        "model_endpoint": ENDPOINT,
        "model": MODEL,
    }
    if (
        set(copied) != expected_top
        or copied.get("artifact_version") != 1
        or copied.get("role") != "v25048_atomic_pypi_representation_preregistration"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("build_audit_sha256") != sha256(root / BUILD_AUDIT)
        or copied.get("freshness") != expected_freshness
        or set(copied.get("population") or {}) != expected_population
        or copied.get("population", {}).get("task_count") != TASK_COUNT
        or copied.get("population", {}).get("project_vector_sha256")
        != payload_sha256(PROJECTS)
        or copied.get("population", {}).get("task_vector_sha256") != payload_sha256(task_vector())
        or copied.get("population", {}).get("endpoint_vector_sha256") != payload_sha256(endpoint_vector())
        or copied.get("population", {}).get("arm_order_vector_sha256") != payload_sha256(arm_order_vector())
        or copied.get("execution") != expected_execution
        or copied.get("gates") != gates()
        or copied.get("protected_watchers") != watcher_snapshot()
        or copied.get("source_manifest") != manifest
        or copied.get("source_manifest_sha256") != payload_sha256(manifest)
        or copied.get("source_policy") != source_policy()
        or copied.get("authorization") != expected_authorization
        or not sealed(copied, "protocol_payload_sha256")
    ):
        raise RuntimeError("V2.50.48 protocol drifted")
    return copied


__all__ = [name for name in globals() if name.isupper()] + [
    "arm_order_vector", "build_protocol", "dependency_manifest", "endpoint_vector",
    "forward_dependency_closure", "gates", "git", "ordinary", "payload_sha256",
    "seal", "sealed", "sha256", "source_policy", "task_vector",
    "validate_protocol", "watcher_snapshot",
]
