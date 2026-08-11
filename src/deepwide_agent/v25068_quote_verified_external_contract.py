"""Frozen external gate contract for V2.50.65/66.

Twenty PyPI package identities were selected only by local brainstorming and
literal-zero scans against ``FRESHNESS_PARENT_COMMIT``.  Their pages, endpoint
values, model outputs, and evaluator values were not opened during selection.
Runtime input is exactly ``opaque_id`` and ``question``.  One visible-only
planner creates four queries shared by both arms; both arms also share the
same fetched pages and record proposal.  The only treatment is the verified,
same-length record representation produced by V2.50.65.
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


DATE = "20260811"
PROTOCOL_ID = "v25068_quote_verified_record_external_mechanism_v1"
BUILD_AUDIT = Path(f"results/v25068_quote_verified_external_build_audit_v1_{DATE}.json")
PROTOCOL = Path(f"results/v25068_quote_verified_external_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v25068_quote_verified_external_preactivation_audit_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v25068_quote_verified_external_execution_start_v1_{DATE}.json")
FORWARD_RESULT = Path(f"results/v25068_quote_verified_external_forward_result_v1_{DATE}.json")
FORWARD_AUDIT = Path(f"results/v25068_quote_verified_external_forward_audit_v1_{DATE}.json")
EVALUATOR = Path("scripts/evaluate_v25068_quote_verified_external.py")
EVALUATOR_TEST = Path("tests/test_evaluate_v25068_quote_verified_external.py")
EVALUATOR_PROTOCOL = Path(f"results/v25068_quote_verified_external_evaluator_preregistration_v1_{DATE}.json")
RESULT = Path(f"results/v25068_quote_verified_external_result_v1_{DATE}.json")
POSTAUDIT = Path(f"results/v25068_quote_verified_external_postresult_audit_v1_{DATE}.json")
OUTPUT_ROOT = Path(f"outputs/v25068_quote_verified_external_v1_{DATE}")
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
TASK_ROWS = OUTPUT_ROOT / "frozen_task_results.jsonl"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
POSTFREEZE_GOLD = OUTPUT_ROOT / "postfreeze_pypi_gold.jsonl"

CONTRACT = Path("src/deepwide_agent/v25068_quote_verified_external_contract.py")
RUNNER = Path("scripts/run_v25068_quote_verified_external.py")
CONTROL = Path("scripts/control_v25068_quote_verified_external.py")
TEST = Path("tests/test_v25068_quote_verified_external.py")
HELPER = Path("scripts/run_v24985_robust_late_page_fetch_helper.py")
PARENT_AUDIT = Path("results/v25067_quote_verified_record_build_audit_v1_20260811.json")
FORWARD_SOURCES = (CONTRACT, RUNNER, HELPER)

TASK_COUNT = 20
EXECUTOR_CONCURRENCY = 20
MODEL_SLOT_CAP = 8
FRESHNESS_PARENT_COMMIT = "6f2ea2cf3daed6f15444d77f969443b1d363623e"
PARENT_AUDIT_SHA256 = "2c6d7fc9a5899f0c2813bde36a8aacb4a128d1e3b42ad829a1714f3b41bf382d"
LEASE_PATH = Path("outputs/deepwide_benchmark_api.lease.lock")
LEASE_OWNER = "v25068_quote_verified_external_forward_v1"
LEASE_PURPOSE = "fresh_label_blind_quote_verified_record_mechanism_gate"

MODEL = {
    "proxy_url": "http://127.0.0.1:9878/responses",
    "name": "gpt-5.6-sol",
    "reasoning_effort": "low",
    "service_tier": "priority",
    "timeout_seconds": 65,
    "max_retries": 2,
}
SEARCH = {
    "proxy_url": "http://127.0.0.1:9878/responses",
    "model": "gpt-5.6-sol",
    "reasoning_effort": "low",
    "service_tier": "priority",
    "timeout_seconds": 65,
    "max_retries": 2,
    "workers": 1,
    "batch_size": 8,
    "context_size": "medium",
    "max_output_tokens": 7_000,
    "fetch_workers": 8,
    "fetch_timeout_seconds": 20,
    "hard_fetch_deadline_seconds": 25,
    "server_auto_fetch_enabled": False,
}
LIMITS = {
    "wall_seconds": 240,
    "model_calls": 3,
    "search_queries": 4,
    "fetch_targets": 10,
    "search_results_per_query": 3,
    "evidence_chars": 60_000,
    "page_chars": 5_000,
    "plan_output_tokens": 4_000,
    "synthesis_output_tokens": 30_000,
    "repair_output_tokens": 12_000,
}
CLEANUP_RESERVE_SECONDS = 5.0
MINIMUM_MODEL_ATTEMPT_SECONDS = 0.05

ARMS = ("raw_fetched_evidence", "quote_verified_record_representation")
CONTROL_ARM, CANDIDATE_ARM = ARMS
COLUMNS = (
    "Package",
    "Latest version",
    "Latest release date (YYYY-MM-DD)",
    "Requires-Python",
)
PROJECTS = (
    "ruamel.yaml",
    "marshmallow-dataclass",
    "apischema",
    "pyserde",
    "serpy",
    "dirty-equals",
    "syrupy",
    "inline-snapshot",
    "approvaltests",
    "freezegun",
    "time-machine",
    "pytest-subtests",
    "pytest-randomly",
    "pytest-order",
    "pytest-repeat",
    "pytest-retry",
    "pytest-timeout",
    "pytest-env",
    "pytest-httpserver",
    "respx",
)
EXPECTED_WATCHERS = (
    (795336, 713986317, "scripts/watch_v2415_r1_checkpoint_liveness.py"),
    (3061652, 747569004, "scripts/watch_v24218_exact220_executor.py"),
    (2808901, 746680268, "scripts/watch_v24215_joint_package_recovery.py"),
    (2889939, 746969965, "scripts/watch_v24216_package_gate.py"),
)

_SECRET_PREFIXES = ("gh" + "p_", "github_" + "pat_", "tvly-" + "dev-", "s" + "k-")
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:"
    + "|".join(re.escape(value) for value in _SECRET_PREFIXES)
    + r")[A-Za-z0-9_-]{16,}"
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
        raise RuntimeError("V2.50.68 expected ordinary repository file")
    if tracked and subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(relative)],
        cwd=root,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=20,
        check=False,
    ).returncode != 0:
        raise RuntimeError("V2.50.68 expected tracked repository file")
    return path


def watcher_snapshot(proc_root: Path = Path("/proc")) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for pid, expected_ticks, marker in EXPECTED_WATCHERS:
        stat = proc_root / str(pid) / "stat"
        cmdline = proc_root / str(pid) / "cmdline"
        if not stat.is_file() or not cmdline.is_file():
            raise RuntimeError("V2.50.68 protected watcher absent")
        raw = stat.read_text(encoding="utf-8")
        suffix = raw[raw.rfind(")") + 2 :].split()
        command = cmdline.read_bytes().replace(b"\0", b" ").decode(errors="replace")
        if len(suffix) <= 19 or int(suffix[19]) != expected_ticks or marker not in command:
            raise RuntimeError("V2.50.68 protected watcher identity drifted")
        rows.append({"pid": pid, "start_ticks": expected_ticks, "marker": marker})
    return rows


def task_vector() -> list[dict[str, str]]:
    if len(PROJECTS) != TASK_COUNT or len(set(PROJECTS)) != TASK_COUNT:
        raise RuntimeError("V2.50.68 project vector drifted")
    rows: list[dict[str, str]] = []
    for project in PROJECTS:
        opaque = "task_" + hashlib.sha256(f"v25068:{project}".encode()).hexdigest()[:24]
        question = (
            "Use public web sources to return exactly one Markdown table and no prose. "
            f"Include exactly one row for the visible Python package identity <PACKAGE>{project}</PACKAGE>. "
            "Columns exactly: " + " | ".join(COLUMNS) + ". Use the canonical PyPI project name in Package. "
            "Latest release date means the earliest file upload date in the latest release, in YYYY-MM-DD form. "
            "Preserve the Requires-Python expression while collapsing whitespace. Values for one row must belong "
            "to the same package and release record. Use Unknown only when fetched public pages do not establish a value."
        )
        rows.append({"opaque_id": opaque, "question": question})
    return validate_task_vector(rows)


def validate_task_vector(values: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
    if isinstance(values, (str, bytes)) or len(values) != TASK_COUNT:
        raise ValueError("V2.50.68 task denominator drifted")
    output: list[dict[str, str]] = []
    for value, project in zip(values, PROJECTS, strict=True):
        if (
            not isinstance(value, Mapping)
            or set(value) != {"opaque_id", "question"}
            or re.fullmatch(r"task_[0-9a-f]{24}", str(value.get("opaque_id") or "")) is None
            or not isinstance(value.get("question"), str)
            or f"<PACKAGE>{project}</PACKAGE>" not in value["question"]
            or any(column not in value["question"] for column in COLUMNS)
            or "https://" in value["question"]
        ):
            raise ValueError("V2.50.68 visible task drifted")
        output.append({"opaque_id": str(value["opaque_id"]), "question": value["question"]})
    if len({row["opaque_id"] for row in output}) != TASK_COUNT:
        raise ValueError("V2.50.68 opaque identity collision")
    return output


def arm_order_vector() -> list[list[str]]:
    tasks = task_vector()
    ranked = sorted(
        range(TASK_COUNT),
        key=lambda index: hashlib.sha256(
            f"v25068-arm-order:{tasks[index]['opaque_id']}".encode()
        ).hexdigest(),
    )
    candidate_first = set(ranked[: TASK_COUNT // 2])
    return [
        [CANDIDATE_ARM, CONTROL_ARM] if index in candidate_first else [CONTROL_ARM, CANDIDATE_ARM]
        for index in range(TASK_COUNT)
    ]


def source_policy() -> dict[str, Any]:
    return {
        "runtime_boundary": ["opaque_id", "question", "same_forward_public_pages"],
        "fresh_population_selected_by_parent_history_literal_zero_scan_only": True,
        "population_endpoint_page_answer_model_or_evaluator_not_opened_before_freeze": True,
        "one_visible_only_plan_generates_four_queries_shared_by_both_arms": True,
        "both_arms_share_queries_search_responses_fetched_pages_and_record_proposal": True,
        "only_treatment_is_same_length_quote_verified_record_representation": True,
        "contiguous_quote_identity_field_and_value_verification_fails_closed": True,
        "robust_late_page_bound_search_client_required": True,
        "query_fetch_model_context_token_wall_and_network_byte_caps_not_expanded": True,
        "fixed_twenty_failure_as_zero_denominator_no_retry_resume_skip_or_replacement": True,
        "prediction_freeze_precedes_gold_evaluator_or_quality_decision": True,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "deepwidebench_dev64_exact220_leaderboard_or_sota_authorized": False,
    }


def mechanism_gate() -> dict[str, Any]:
    return {
        "fixed_task_denominator": TASK_COUNT,
        "terminal_tasks": TASK_COUNT,
        "completed_runtime_tasks": TASK_COUNT,
        "both_arms_model_success_tasks": TASK_COUNT,
        "minimum_tasks_with_usable_page": 16,
        "minimum_verifier_exposure_tasks": 8,
        "minimum_prediction_changed_tasks": 4,
        "exact_planned_and_physical_queries_per_completed_task": 4,
        "maximum_physical_fetches_per_completed_task": 10,
        "exact_physical_model_logical_calls_per_completed_task": 4,
        "exact_effective_model_logical_calls_per_completed_arm": 3,
        "equal_control_candidate_evidence_characters_per_task": True,
        "frozen_arm_order_exact": True,
        "maximum_transport_search_fetch_model_or_outer_hard_failures": 0,
        "candidate_arm_model_hard_failures_not_greater_than_control": True,
    }


def quality_gate() -> dict[str, Any]:
    return {
        "fixed_denominator": TASK_COUNT,
        "candidate_exact_strict_gain": True,
        "candidate_composite_nonregression": True,
        "entity_row_item_column_nonregression": True,
        "invalid_or_fallback_nonincrease": True,
        "same_search_fetch_evidence_length_and_effective_model_budget": True,
    }


def _module_candidates(relative: Path, node: ast.AST) -> list[Path]:
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
    return candidates


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
            for candidate in _module_candidates(relative, node):
                if (root / candidate).is_file() and not (root / candidate).is_symlink():
                    pending.append(candidate)
    return tuple(sorted(observed, key=str))


def dependency_manifest(root: Path, *, tracked: bool) -> dict[str, str]:
    relatives = {*forward_dependency_closure(root), CONTROL, TEST, PARENT_AUDIT}
    output: dict[str, str] = {}
    for relative in sorted(relatives, key=str):
        path = ordinary(root, relative, tracked=tracked)
        if SECRET.search(path.read_text(encoding="utf-8")):
            raise RuntimeError("V2.50.68 credential literal in source manifest")
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
        PROTOCOL,
        PREAUDIT,
        EXECUTION_START,
        FORWARD_RESULT,
        FORWARD_AUDIT,
        EVALUATOR,
        EVALUATOR_TEST,
        EVALUATOR_PROTOCOL,
        RESULT,
        POSTAUDIT,
        OUTPUT_ROOT,
    )
    if require_pristine and any((root / path).exists() or (root / path).is_symlink() for path in future):
        raise RuntimeError("V2.50.68 future surface is not pristine")
    manifest = dependency_manifest(root, tracked=tracked)
    tasks = task_vector()
    value = {
        "artifact_version": 1,
        "role": "v25068_quote_verified_external_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(now),
        "build_audit_sha256": build_audit_sha256,
        "parent": {"path": str(PARENT_AUDIT), "sha256": sha256(root / PARENT_AUDIT)},
        "freshness": {
            "parent_commit": FRESHNESS_PARENT_COMMIT,
            "parent_history_literal_zero_hit_projects": list(PROJECTS),
            "endpoint_page_value_model_or_evaluator_opened_during_selection": False,
        },
        "population": {
            "task_count": TASK_COUNT,
            "project_vector_sha256": payload_sha256(PROJECTS),
            "task_vector_sha256": payload_sha256(tasks),
            "opaque_id_vector_sha256": payload_sha256([row["opaque_id"] for row in tasks]),
            "arm_order_vector_sha256": payload_sha256(arm_order_vector()),
        },
        "execution": {
            "arms": list(ARMS),
            "only_treatment": "same_length_model_proposed_deterministically_quote_verified_record_representation",
            "executor_concurrency": EXECUTOR_CONCURRENCY,
            "model_slot_cap": MODEL_SLOT_CAP,
            "model": copy.deepcopy(MODEL),
            "search": copy.deepcopy(SEARCH),
            "limits": copy.deepcopy(LIMITS),
            "query_policy": "one_visible_only_plan_four_queries_shared_by_both_arms",
            "physical_paired_model_call_cap": 4,
            "effective_model_call_cap_per_arm": 3,
            "single_atomic_forward_no_retry_resume_skip_or_replacement": True,
        },
        "mechanism_gate": mechanism_gate(),
        "quality_gate": quality_gate(),
        "protected_watchers": watcher_snapshot(),
        "source_manifest": manifest,
        "source_manifest_sha256": payload_sha256(manifest),
        "source_policy": source_policy(),
        "authorization": {
            "one_external_forward_after_separate_clean_pushed_start": True,
            "evaluator_implementation_only_after_prediction_freeze_and_pushed_forward_audit_go": True,
            "deepwidebench_dev64_exact220_or_sota": False,
            "retry_resume_skip_population_replacement_or_selective_revaluation": False,
        },
    }
    return seal(value, "protocol_payload_sha256")


def validate_protocol(root: Path, value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    expected = build_protocol(
        root,
        now=int(copied.get("created_at_unix", -1)),
        tracked=True,
        require_pristine=False,
        build_audit_sha256=sha256(root / BUILD_AUDIT),
    )
    if copied != expected or not sealed(copied, "protocol_payload_sha256"):
        raise RuntimeError("V2.50.68 protocol drifted")
    return copied


__all__ = [name for name in globals() if name.isupper()] + [
    "arm_order_vector",
    "build_protocol",
    "dependency_manifest",
    "forward_dependency_closure",
    "git",
    "mechanism_gate",
    "ordinary",
    "payload_sha256",
    "quality_gate",
    "seal",
    "sealed",
    "sha256",
    "source_policy",
    "task_vector",
    "validate_protocol",
    "validate_task_vector",
    "watcher_snapshot",
]
