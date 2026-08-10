"""Fresh label-blind external contract for split-2+2 versus one-shot-4 search.

The forward population and query vector are frozen without opening any final
PyPI endpoint.  Gold construction and quality evaluation live in a separate
future module that must not physically exist before prediction freeze and the
content-free forward audit are committed and pushed.
"""

from __future__ import annotations

import ast
import copy
import hashlib
import json
import re
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .v25038_source_only_batching import ARMS


DATE = "20260810"
PROTOCOL_ID = "v25038_source_only_split2_vs_oneshot4_external_v1"
BUILD_AUDIT = Path(f"results/v25038_batching_external_build_audit_v1_{DATE}.json")
PROTOCOL = Path(f"results/v25038_batching_external_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v25038_batching_external_preactivation_audit_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v25038_batching_external_execution_start_v1_{DATE}.json")
FORWARD_RESULT = Path(f"results/v25038_batching_external_forward_result_v1_{DATE}.json")
FORWARD_AUDIT = Path(f"results/v25038_batching_external_forward_audit_v1_{DATE}.json")
EVALUATOR_PROTOCOL = Path(
    f"results/v25038_batching_external_evaluator_preregistration_v1_{DATE}.json"
)
RESULT = Path(f"results/v25038_batching_external_result_v1_{DATE}.json")
POSTAUDIT = Path(f"results/v25038_batching_external_postresult_audit_v1_{DATE}.json")
OUTPUT_ROOT = Path(f"outputs/v25038_batching_external_v1_{DATE}")
TASK_ROWS = OUTPUT_ROOT / "frozen_task_results.jsonl"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
GOLD_SNAPSHOT = OUTPUT_ROOT / "postfreeze_pypi_gold.json"
LEASE_PATH = Path("outputs/deepwide_benchmark_api.lease.lock")

SOURCE = Path("src/deepwide_agent/v25038_source_only_batching.py")
CONTRACT = Path("src/deepwide_agent/v25038_batching_external_contract.py")
RUNNER = Path("scripts/run_v25038_batching_external.py")
CONTROL = Path("scripts/control_v25038_batching_external.py")
TEST = Path("tests/test_v25038_batching_external.py")
EVALUATOR = Path("scripts/evaluate_v25038_batching_external.py")
LOCAL_SOURCES = (SOURCE, CONTRACT, RUNNER, CONTROL, TEST)
FORWARD_SOURCES = (SOURCE, CONTRACT, RUNNER)

TASK_COUNT = 20
EXECUTOR_CONCURRENCY = 20
MODEL_SLOT_CAP = 8
MODEL_OUTPUT_TOKENS = 2_400
TASK_DEADLINE_SECONDS = 240.0
EVIDENCE_CHARS = 12_000
MINIMUM_USABLE_PAGES = 2
MINIMUM_RAW_CHARACTERS = 12_000
LEAD_CAP = 10
CONTROL_ARM, CANDIDATE_ARM = ARMS
MODEL = {
    "proxy_url": "http://127.0.0.1:9878/responses",
    "name": "gpt-5.6-sol",
    "reasoning_effort": "low",
    "service_tier": "priority",
    "timeout_seconds": 90,
    "max_retries": 1,
}
SEARCH = {
    "proxy_url": "http://127.0.0.1:9878/responses",
    "model": "gpt-5.6-sol",
    "context_size": "medium",
    "timeout_seconds": 65,
    "max_retries": 1,
    "fetch_workers": 8,
    "fetch_timeout_seconds": 20,
    "hard_fetch_deadline_seconds": 25,
    "max_page_chars": 20_000,
}
EXPECTED_WATCHERS = (
    (795336, 713986317, "scripts/watch_v2415_r1_checkpoint_liveness.py"),
    (3061652, 747569004, "scripts/watch_v24218_exact220_executor.py"),
    (2808901, 746680268, "scripts/watch_v24215_joint_package_recovery.py"),
    (2889939, 746969965, "scripts/watch_v24216_package_gate.py"),
)
FRESHNESS_PARENT_COMMIT = "c246e9012fd6eab5a387400418848b4879470b65"
PROJECTS = (
    "dnspython", "questionary", "inquirer", "cyclopts", "pyproject-hooks",
    "setuptools-scm", "dunamai", "hatch-vcs", "pdm-backend", "flit-core",
    "editables", "python-rapidjson", "cbor2", "ormsgpack", "httptools",
    "watchfiles", "wsproto", "hyperframe", "hpack", "rtoml",
)
QUERY_PATTERNS = (
    "{project} PyPI latest version release date Requires-Python",
    "site:pypi.org/project/{project} {project} latest version",
    "{project} official Python package metadata Requires-Python",
    "{project} PyPI release history latest upload date",
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
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
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
        ["git", *args], cwd=root, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        timeout=20, check=True,
    ).stdout.strip()


def ordinary(root: Path, relative: Path, *, tracked: bool) -> Path:
    path = root / relative
    if (
        relative.is_absolute() or ".." in relative.parts or path.is_symlink()
        or not path.is_file() or not path.resolve().is_relative_to(root.resolve())
    ):
        raise RuntimeError("V2.50.38 expected ordinary repository file")
    if tracked and subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(relative)], cwd=root,
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, timeout=20, check=False,
    ).returncode != 0:
        raise RuntimeError("V2.50.38 expected tracked repository file")
    return path


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
                        candidates.append(
                            Path("src") / Path(*item.name.split(".")).with_suffix(".py")
                        )
                    elif item.name.startswith("scripts."):
                        candidates.append(Path(*item.name.split(".")).with_suffix(".py"))
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if node.level and relative.parts[:2] == ("src", "deepwide_agent"):
                    if module:
                        candidates.append(
                            Path("src/deepwide_agent")
                            / Path(*module.split(".")).with_suffix(".py")
                        )
                    else:
                        candidates.extend(
                            Path("src/deepwide_agent") / f"{item.name}.py"
                            for item in node.names
                        )
                elif module == "deepwide_agent":
                    candidates.extend(
                        Path("src/deepwide_agent") / f"{item.name}.py"
                        for item in node.names
                    )
                elif module.startswith("deepwide_agent."):
                    candidates.append(
                        Path("src") / Path(*module.split(".")).with_suffix(".py")
                    )
                elif module == "scripts":
                    candidates.extend(
                        Path("scripts") / f"{item.name}.py" for item in node.names
                    )
                elif module.startswith("scripts."):
                    candidates.append(Path(*module.split(".")).with_suffix(".py"))
            for candidate in candidates:
                if (root / candidate).is_file() and not (root / candidate).is_symlink():
                    pending.append(candidate)
    return tuple(sorted(observed, key=str))


def dependency_manifest(root: Path, *, tracked: bool) -> dict[str, str]:
    output: dict[str, str] = {}
    relatives = {*forward_dependency_closure(root), CONTROL, TEST}
    for relative in sorted(relatives, key=str):
        path = ordinary(root, relative, tracked=tracked)
        if SECRET.search(path.read_text(encoding="utf-8")):
            raise RuntimeError("V2.50.38 credential literal in source manifest")
        output[str(relative)] = sha256(path)
    return output


def watcher_snapshot(proc_root: Path = Path("/proc")) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for pid, expected_ticks, marker in EXPECTED_WATCHERS:
        stat = proc_root / str(pid) / "stat"
        cmdline = proc_root / str(pid) / "cmdline"
        if not stat.is_file() or not cmdline.is_file():
            raise RuntimeError("V2.50.38 protected watcher absent")
        raw = stat.read_text(encoding="utf-8")
        suffix = raw[raw.rfind(")") + 2 :].split()
        command = cmdline.read_bytes().replace(b"\0", b" ").decode(errors="replace")
        if (
            len(suffix) <= 19
            or int(suffix[19]) != expected_ticks
            or marker not in command
        ):
            raise RuntimeError("V2.50.38 protected watcher identity drifted")
        rows.append({"pid": pid, "start_ticks": expected_ticks, "marker": marker})
    return rows


def task_vector() -> list[dict[str, str]]:
    if len(PROJECTS) != TASK_COUNT or len(set(PROJECTS)) != TASK_COUNT:
        raise RuntimeError("V2.50.38 project vector drifted")
    rows: list[dict[str, str]] = []
    for project in PROJECTS:
        opaque = "task_" + hashlib.sha256(
            f"v25038:{project}".encode()
        ).hexdigest()[:24]
        question = (
            "Using only the supplied fetched public pages, return exactly one "
            "Markdown table and no prose. Include exactly one row for the Python "
            f"package {project}. Columns exactly: " + " | ".join(COLUMNS)
            + ". Use the canonical PyPI project name in Package. Latest release "
            "date means the earliest file upload date in the latest release, in "
            "YYYY-MM-DD form. Preserve the Requires-Python expression while "
            "collapsing whitespace. Use Unknown only when the supplied pages do "
            "not establish a value."
        )
        rows.append({"opaque_id": opaque, "question": question})
    return validate_task_vector(rows)


def validate_task_vector(values: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
    if isinstance(values, (str, bytes)) or len(values) != TASK_COUNT:
        raise ValueError("V2.50.38 task denominator drifted")
    output: list[dict[str, str]] = []
    for value, project in zip(values, PROJECTS, strict=True):
        if (
            not isinstance(value, Mapping)
            or set(value) != {"opaque_id", "question"}
            or not isinstance(value.get("opaque_id"), str)
            or not re.fullmatch(r"task_[0-9a-f]{24}", value["opaque_id"])
            or not isinstance(value.get("question"), str)
            or project not in value["question"]
            or any(column not in value["question"] for column in COLUMNS)
            or "https://" in value["question"]
        ):
            raise ValueError("V2.50.38 visible task drifted")
        output.append({"opaque_id": value["opaque_id"], "question": value["question"]})
    if len({row["opaque_id"] for row in output}) != TASK_COUNT:
        raise ValueError("V2.50.38 opaque identity collision")
    return output


def query_vector() -> list[list[str]]:
    return [
        [pattern.format(project=project) for pattern in QUERY_PATTERNS]
        for project in PROJECTS
    ]


def arm_order_vector() -> list[list[str]]:
    ranked = sorted(
        range(TASK_COUNT),
        key=lambda index: hashlib.sha256(
            f"v25038-order:{task_vector()[index]['opaque_id']}".encode()
        ).hexdigest(),
    )
    candidate_first = set(ranked[: TASK_COUNT // 2])
    return [
        [CANDIDATE_ARM, CONTROL_ARM] if index in candidate_first
        else [CONTROL_ARM, CANDIDATE_ARM]
        for index in range(TASK_COUNT)
    ]


def source_policy() -> dict[str, Any]:
    return {
        "runtime_boundary": ["opaque_id", "question", "same_forward_public_pages"],
        "freshness_checked_against_all_history_reachable_from_parent_commit": True,
        "predeclared_evaluator_endpoint_vector_absent_and_not_directly_opened_before_freeze": True,
        "same_four_visible_queries_per_arm": True,
        "only_treatment_split_2_plus_2_vs_one_shot_4": True,
        "control_split_wave_lead_caps": [6, 4],
        "candidate_one_shot_lead_cap": LEAD_CAP,
        "search_and_model_arm_first_position_balanced_by_preoutcome_opaque_hash": True,
        "shared_fetch_union_uses_same_preoutcome_arm_order": True,
        "source_only_hosted_search_medium_context": True,
        "provider_narrative_or_snippet_used_as_active_evidence": False,
        "shared_task_local_union_fetch_for_both_arms": True,
        "same_fixed_evidence_budget_prompt_model_output_cap_and_deadline": True,
        "prediction_freeze_before_gold_or_evaluator": True,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read_by_forward": False,
        "entropy_or_information_gain_assigns_credit_or_routes": False,
        "deepwidebench_dev64_exact220_leaderboard_or_sota_authorized": False,
    }


def mechanism_gate() -> dict[str, Any]:
    return {
        "fixed_task_denominator": TASK_COUNT,
        "all_tasks_terminal": True,
        "maximum_failure_as_zero_tasks": 2,
        "exact_logical_queries_per_arm_per_task": 4,
        "exact_control_provider_calls_per_task": 2,
        "exact_candidate_provider_calls_per_task": 1,
        "maximum_provider_attempts_equal_calls": True,
        "exact_action_query_coverage_all_arms": True,
        "maximum_candidate_over_control_search_input_tokens": 0.85,
        "maximum_candidate_over_control_search_total_tokens": 0.85,
        "minimum_candidate_over_control_selected_leads": 0.85,
        "minimum_candidate_over_control_usable_pages": 0.85,
        "minimum_candidate_over_control_raw_characters": 0.85,
        "minimum_shared_fetch_success_rate": 0.85,
        "fixed_evidence_budget_all_completed_arms": EVIDENCE_CHARS,
        "exact_model_attempts_per_completed_arm": 1,
        "maximum_transport_unrecoverable_recursive_or_hard_timeout": 0,
        "maximum_hard_fetch_deadline_or_helper_failure": 0,
    }


def quality_gate() -> dict[str, Any]:
    return {
        "fixed_denominator": TASK_COUNT,
        "candidate_exact_nonregression": True,
        "candidate_composite_nonregression": True,
        "entity_row_item_column_nonregression": True,
        "invalid_or_fallback_nonincrease": True,
        "strict_cost_gain_required": True,
    }


def build_protocol(
    root: Path,
    *,
    now: int,
    tracked: bool,
    require_pristine: bool,
    build_audit_sha256: str,
) -> dict[str, Any]:
    if tracked and git(root, "rev-parse", FRESHNESS_PARENT_COMMIT) != FRESHNESS_PARENT_COMMIT:
        raise RuntimeError("V2.50.38 freshness parent absent")
    future = (
        PROTOCOL, PREAUDIT, EXECUTION_START, FORWARD_RESULT, FORWARD_AUDIT,
        EVALUATOR_PROTOCOL, RESULT, POSTAUDIT, OUTPUT_ROOT, EVALUATOR,
    )
    if require_pristine and any(
        (root / path).exists() or (root / path).is_symlink() for path in future
    ):
        raise RuntimeError("V2.50.38 future surface is not pristine")
    manifest = dependency_manifest(root, tracked=tracked)
    value = {
        "artifact_version": 1,
        "role": "v25038_batching_external_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(now),
        "build_audit_sha256": build_audit_sha256,
        "freshness": {
            "parent_commit": FRESHNESS_PARENT_COMMIT,
            "parent_reachable_history_literal_zero_hit_projects": list(PROJECTS),
            "endpoint_or_answer_opened_during_selection": False,
        },
        "population": {
            "task_count": TASK_COUNT,
            "project_vector_sha256": payload_sha256(PROJECTS),
            "task_vector_sha256": payload_sha256(task_vector()),
            "query_vector_sha256": payload_sha256(query_vector()),
            "arm_order_vector_sha256": payload_sha256(arm_order_vector()),
        },
        "execution": {
            "arms": list(ARMS),
            "only_treatment": "physical_query_grouping_split_2_plus_2_vs_one_shot_4",
            "executor_concurrency": EXECUTOR_CONCURRENCY,
            "model_slot_cap": MODEL_SLOT_CAP,
            "lead_cap_per_arm": LEAD_CAP,
            "control_split_wave_lead_caps": [6, 4],
            "evidence_chars_per_arm": EVIDENCE_CHARS,
            "minimum_usable_pages": MINIMUM_USABLE_PAGES,
            "minimum_raw_characters": MINIMUM_RAW_CHARACTERS,
            "model_output_tokens": MODEL_OUTPUT_TOKENS,
            "task_deadline_seconds": TASK_DEADLINE_SECONDS,
            "model": MODEL,
            "search": SEARCH,
        },
        "mechanism_gate": mechanism_gate(),
        "quality_gate": quality_gate(),
        "protected_watchers": watcher_snapshot(),
        "source_manifest": manifest,
        "source_manifest_sha256": payload_sha256(manifest),
        "source_policy": source_policy(),
        "authorization": {
            "one_external_forward_after_separate_clean_pushed_start": True,
            "evaluator_only_after_prediction_freeze_and_pushed_forward_audit": True,
            "deepwidebench_dev64_exact220_or_sota": False,
            "retry_resume_selective_rerun_or_revaluation": False,
        },
    }
    return seal(value, "protocol_payload_sha256")


def validate_protocol(root: Path, value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    population = copied.get("population") or {}
    execution = copied.get("execution") or {}
    manifest = dependency_manifest(root, tracked=True)
    build_path = root / BUILD_AUDIT
    expected_build = sha256(build_path) if build_path.is_file() and not build_path.is_symlink() else None
    if (
        copied.get("role") != "v25038_batching_external_preregistration"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("build_audit_sha256") != expected_build
        or copied.get("freshness", {}).get("parent_commit") != FRESHNESS_PARENT_COMMIT
        or copied.get("freshness", {}).get(
            "parent_reachable_history_literal_zero_hit_projects"
        )
        != list(PROJECTS)
        or population.get("task_count") != TASK_COUNT
        or population.get("project_vector_sha256") != payload_sha256(PROJECTS)
        or population.get("task_vector_sha256") != payload_sha256(task_vector())
        or population.get("query_vector_sha256") != payload_sha256(query_vector())
        or population.get("arm_order_vector_sha256")
        != payload_sha256(arm_order_vector())
        or execution.get("arms") != list(ARMS)
        or execution.get("only_treatment")
        != "physical_query_grouping_split_2_plus_2_vs_one_shot_4"
        or execution.get("evidence_chars_per_arm") != EVIDENCE_CHARS
        or copied.get("mechanism_gate") != mechanism_gate()
        or copied.get("quality_gate") != quality_gate()
        or copied.get("protected_watchers") != watcher_snapshot()
        or copied.get("source_manifest") != manifest
        or copied.get("source_manifest_sha256") != payload_sha256(manifest)
        or copied.get("source_policy") != source_policy()
        or copied.get("authorization", {}).get(
            "deepwidebench_dev64_exact220_or_sota"
        )
        is not False
        or not sealed(copied, "protocol_payload_sha256")
    ):
        raise RuntimeError("V2.50.38 protocol drifted")
    return copied


__all__ = [
    "ARMS", "BUILD_AUDIT", "CANDIDATE_ARM", "COLUMNS", "CONTRACT",
    "CONTROL", "CONTROL_ARM", "EVALUATOR", "EVALUATOR_PROTOCOL",
    "EVIDENCE_CHARS", "EXECUTION_START", "EXECUTOR_CONCURRENCY",
    "FALLBACK_TABLE", "FORWARD_AUDIT", "FORWARD_RESULT", "FORWARD_SOURCES",
    "EXPECTED_WATCHERS", "FRESHNESS_PARENT_COMMIT", "GOLD_SNAPSHOT", "LEAD_CAP", "LEASE_PATH",
    "LOCAL_SOURCES", "MINIMUM_RAW_CHARACTERS", "MINIMUM_USABLE_PAGES",
    "MODEL", "MODEL_OUTPUT_TOKENS", "MODEL_SLOT_CAP", "OUTPUT_ROOT",
    "POSTAUDIT", "PREAUDIT", "PROJECTS", "PROTOCOL", "PROTOCOL_ID",
    "PREDICTION_FREEZE", "QUERY_PATTERNS", "RESULT", "RUNNER", "SEARCH",
    "SOURCE", "TASK_COUNT", "TASK_DEADLINE_SECONDS", "TASK_ROWS", "TEST",
    "arm_order_vector", "build_protocol", "dependency_manifest", "forward_dependency_closure", "git",
    "mechanism_gate", "ordinary", "payload_sha256", "quality_gate", "seal",
    "sealed", "sha256", "source_policy", "task_vector", "query_vector",
    "validate_protocol", "validate_task_vector", "watcher_snapshot",
]
