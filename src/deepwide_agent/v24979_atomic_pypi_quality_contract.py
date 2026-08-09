"""Atomic external quality contract for late PyPI release-file fields."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from . import v24973_identity_bound_field_quality_contract as schema


DATE = "20260809"
PROTOCOL_ID = "v24979_atomic_pypi_release_file_quality_gate_v1"
BUILD_AUDIT = Path(f"results/v24979_atomic_pypi_quality_build_audit_v1_{DATE}.json")
PROTOCOL = Path(f"results/v24979_atomic_pypi_quality_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v24979_atomic_pypi_quality_preactivation_audit_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v24979_atomic_pypi_quality_execution_start_v1_{DATE}.json")
PARSER_READINESS = Path(f"results/v24979_atomic_pypi_readiness_v1_{DATE}.json")
FORWARD_RESULT = Path(f"results/v24979_atomic_pypi_quality_forward_result_v1_{DATE}.json")
FORWARD_AUDIT = Path(f"results/v24979_atomic_pypi_quality_forward_audit_v1_{DATE}.json")
EVALUATOR_PROTOCOL = Path(f"results/v24979_atomic_pypi_quality_evaluator_preregistration_v1_{DATE}.json")
RESULT = Path(f"results/v24979_atomic_pypi_quality_result_v1_{DATE}.json")
POSTAUDIT = Path(f"results/v24979_atomic_pypi_quality_postresult_audit_v1_{DATE}.json")
OUTPUT_ROOT = Path(f"outputs/v24979_atomic_pypi_quality_v1_{DATE}")
TASK_ROWS = OUTPUT_ROOT / "frozen_task_results.jsonl"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
GOLD_SNAPSHOT = OUTPUT_ROOT / "postfreeze_pypi_gold.json"

SOURCE = Path("src/deepwide_agent/v24979_atomic_pypi_quality_contract.py")
EXTRACTOR = Path("src/deepwide_agent/v24978_pypi_release_file_compactor.py")
RUNTIME = Path("scripts/run_v24979_atomic_pypi_quality.py")
CONTROL = Path("scripts/control_v24979_atomic_pypi_quality.py")
FINALIZER = Path("scripts/finalize_v24979_atomic_pypi_quality.py")
TEST = Path("tests/test_v24979_atomic_pypi_quality.py")
EXTRACTOR_TEST = Path("tests/test_v24978_pypi_release_file_compactor.py")
ATOMIC_CONTRACT = Path("src/deepwide_agent/v24977_atomic_parser_quality_contract.py")
ATOMIC_RUNTIME = Path("scripts/run_v24977_atomic_parser_quality.py")
ATOMIC_TEST = Path("tests/test_v24977_atomic_parser_quality.py")
SCHEMA_CONTRACT = Path("src/deepwide_agent/v24973_identity_bound_field_quality_contract.py")
SCHEMA_RUNTIME = Path("scripts/run_v24973_identity_bound_field_quality.py")
SCHEMA_CONTROL = Path("scripts/control_v24973_identity_bound_field_quality.py")
SCHEMA_FINALIZER = Path("scripts/finalize_v24973_identity_bound_field_quality.py")
FIELD_EXTRACTOR = Path("src/deepwide_agent/v24972_identity_bound_compact_fields.py")
LOCAL_SOURCES = (
    SOURCE, EXTRACTOR, RUNTIME, CONTROL, FINALIZER, TEST, EXTRACTOR_TEST,
    ATOMIC_CONTRACT, ATOMIC_RUNTIME, ATOMIC_TEST, SCHEMA_CONTRACT,
    SCHEMA_RUNTIME, SCHEMA_CONTROL, SCHEMA_FINALIZER, FIELD_EXTRACTOR,
)

PROJECTS = (
    "python-dotenv",
    "colorama",
    "wcwidth",
    "executing",
    "pure-eval",
    "asttokens",
    "stack-data",
    "jedi",
    "parso",
    "pickleshare",
    "comm",
    "nest-asyncio",
    "matplotlib-inline",
    "backcall",
    "pexpect",
    "ptyprocess",
    "terminado",
    "send2trash",
    "defusedxml",
    "mistune",
)

PRIOR_PROJECTS = frozenset(
    {
        # All prior paired populations and layout/transport probes are excluded.
        "pydantic-settings", "rich", "httpx", "typer", "hatchling",
        "poetry-core", "twine", "virtualenv", "pipx", "cibuildwheel",
        "maturin", "meson-python", "scikit-build-core", "pytest-xdist",
        "pytest-cov", "hypothesis", "cattrs", "msgspec", "orjson",
        "rapidfuzz", "fastapi", "starlette", "uvicorn", "sqlalchemy",
        "alembic", "attrs", "structlog", "loguru", "tenacity", "anyio",
        "trio", "click", "flask", "werkzeug", "jinja2", "itsdangerous",
        "markupsafe", "black", "ruff", "mypy", "pytest-asyncio",
        "pillow", "arrow", "python-dateutil", "pytz", "tzdata", "jsonschema",
        "referencing", "rpds-py", "lxml", "soupsieve", "markdown-it-py",
        "pygments", "sphinx", "babel", "alabaster", "blinker", "pathspec",
        "nodeenv", "pre-commit", "wrapt", "pandas", "scipy", "scikit-learn",
        "matplotlib", "seaborn", "polars", "pyarrow", "duckdb", "ipython",
        "traitlets", "jupyter-core", "jupyter-client", "tornado", "pyzmq",
        "nbformat", "nbclient", "nbconvert", "jupyter-server", "jupyterlab",
        "notebook", "pyyaml", "msgpack", "ujson", "zstandard", "lz4",
        "pycryptodome", "protobuf", "flatbuffers", "textual", "prompt-toolkit",
        "uvloop", "websockets", "twisted", "scrapy", "pyopenssl", "playwright",
        "selenium", "sanic", "hypercorn", "aiofiles",
    }
)

ENDPOINT = schema.ENDPOINT
MODEL = schema.MODEL
CONTROL_ARM = "raw_pypi_json_prefix"
CANDIDATE_ARM = "identity_bound_release_file_fields"
ARMS = (CONTROL_ARM, CANDIDATE_ARM)
TASK_COUNT = 20
EXECUTOR_CONCURRENCY = 20
MODEL_CONCURRENCY = 8
EVIDENCE_CHARS = 16_000
NAMESPACE_EVIDENCE_CHARS = EVIDENCE_CHARS
MODEL_OUTPUT_TOKENS = 2_400
TASK_DEADLINE_SECONDS = 180.0
FETCH_TARGETS_PER_TASK = 1
MINIMUM_PREDICTION_CHANGES = 10
MAX_RESPONSE_BYTES = 32_000_000
FETCH_TIMEOUT = (5.0, 60.0)
LEASE_OWNER = "v24979_atomic_pypi_quality_forward_v1"
LEASE_PURPOSE = "atomic_pypi_ready_then_release_file_quality_gate"
LEASE_PATH = schema.LEASE_PATH
COLUMNS = (
    "Package",
    "Latest version",
    "Requires-Python",
    "Current-version file count",
    "Current-version first upload date (YYYY-MM-DD)",
    "Current-version largest file size (bytes)",
)
FALLBACK_TABLE = (
    "| Package | Latest version | Requires-Python | Current-version file count | "
    "Current-version first upload date (YYYY-MM-DD) | Current-version largest file size (bytes) |\n"
    "|---|---|---|---|---|---|\n| Unknown | Unknown | Unknown | Unknown | Unknown | Unknown |"
)
PROTECTED_WATCHERS = schema.PROTECTED_WATCHERS

payload_sha256 = schema.payload_sha256
sha256 = schema.sha256
sealed = schema.sealed
seal = schema.seal
git = schema.git
ordinary_tracked = schema.ordinary_tracked
proc_start_ticks = schema.proc_start_ticks
watcher_snapshot = schema.watcher_snapshot


def task_vector() -> list[dict[str, str]]:
    if len(PROJECTS) != TASK_COUNT or len(set(PROJECTS)) != TASK_COUNT or set(PROJECTS) & PRIOR_PROJECTS:
        raise RuntimeError("V2.49.79 fresh population drifted")
    rows = []
    for project in PROJECTS:
        opaque = "task_" + hashlib.sha256(f"v24979:{project}".encode()).hexdigest()[:24]
        question = (
            "Using only the supplied fetched public page, return exactly one Markdown table and no prose. "
            "Include exactly one row. The visible package identity is:\n"
            f"<PACKAGE>{project}</PACKAGE>\n"
            "Columns exactly: " + " | ".join(COLUMNS) + ". "
            "Latest version and Requires-Python come from current PyPI project metadata. "
            "The file count, first upload date, and largest file size refer only to files in the current version's PyPI release vector. "
            "Dates use YYYY-MM-DD and sizes use base-10 bytes without separators. Preserve the Requires-Python expression while collapsing whitespace. "
            "Use Unknown only when the supplied page does not establish a value."
        )
        rows.append({"opaque_id": opaque, "question": question})
    return rows


def endpoint_vector() -> list[list[str]]:
    return [[f"https://pypi.org/pypi/{project}/json"] for project in PROJECTS]


def gold_endpoint_vector() -> list[list[str]]:
    return endpoint_vector()


def arm_order_vector() -> list[list[str]]:
    ranked = sorted(
        range(TASK_COUNT),
        key=lambda index: hashlib.sha256(
            f"v24979-arm-order:{task_vector()[index]['opaque_id']}".encode()
        ).hexdigest(),
    )
    candidate_first = set(ranked[: TASK_COUNT // 2])
    return [[CANDIDATE_ARM, CONTROL_ARM] if i in candidate_first else [CONTROL_ARM, CANDIDATE_ARM] for i in range(TASK_COUNT)]


def gates() -> dict[str, Any]:
    return {
        "mechanism": {
            "terminal_tasks": TASK_COUNT,
            "successful_shared_fetches": TASK_COUNT,
            "admitted_compact_records": TASK_COUNT,
            "unique_bound_fields": TASK_COUNT * 5,
            "field_conflicts": 0,
            "candidate_evidence_changed_tasks": TASK_COUNT,
            "minimum_prediction_changed_tasks": MINIMUM_PREDICTION_CHANGES,
            "model_successes_per_arm": TASK_COUNT,
            "evidence_chars_per_arm": TASK_COUNT * EVIDENCE_CHARS,
            "fallback_tasks": 0,
        },
        "quality": {
            "candidate_exact_strictly_greater": True,
            "entity_row_item_column_composite_nonregression": True,
            "evaluator_invalid_and_fallback_nonincrease": True,
            "fixed_denominator": TASK_COUNT,
        },
    }


def source_policy() -> dict[str, Any]:
    return {
        "runtime_boundary": ["opaque_id", "question", "same_forward_public_pypi_json"],
        "all_twenty_pages_fetched_and_parsed_before_any_model_call": True,
        "parser_readiness_go_requires_tasks_fields_conflicts": [20, 100, 0],
        "parser_readiness_failure_stops_before_output_root_and_model": True,
        "parser_readiness_receipt_contains_counts_only": True,
        "same_complete_pypi_json_bytes_for_both_arms": True,
        "control_is_fixed_raw_json_prefix": True,
        "candidate_record_derived_from_complete_shared_json": True,
        "same_evidence_chars_prompt_model_output_cap_and_attempt_count": True,
        "search_tool_or_github_surface_used": False,
        "prediction_freeze_before_evaluator_metrics_or_quality_decision": True,
        "postfreeze_evaluator_refetches_each_exact_pypi_endpoint_once": True,
        "deepwidebench_manifest_mapping_gold_category_question_type_split_evaluator_score_reward_read_by_forward": False,
        "entropy_or_information_gain_assigns_credit": False,
        "final_population_url_model_or_evaluator_probed_before_freeze": False,
        "public_exact220_or_sota_authorized": False,
    }


def _configure_schema() -> None:
    assignments = {
        "DATE": DATE, "PROTOCOL_ID": PROTOCOL_ID, "BUILD_AUDIT": BUILD_AUDIT,
        "PROTOCOL": PROTOCOL, "PREAUDIT": PREAUDIT, "EXECUTION_START": EXECUTION_START,
        "FORWARD_RESULT": FORWARD_RESULT, "FORWARD_AUDIT": FORWARD_AUDIT,
        "EVALUATOR_PROTOCOL": EVALUATOR_PROTOCOL, "RESULT": RESULT,
        "POSTAUDIT": POSTAUDIT, "OUTPUT_ROOT": OUTPUT_ROOT, "TASK_ROWS": TASK_ROWS,
        "PREDICTION_FREEZE": PREDICTION_FREEZE, "GOLD_SNAPSHOT": GOLD_SNAPSHOT,
        "SOURCE": SOURCE, "EXTRACTOR": EXTRACTOR, "RUNTIME": RUNTIME,
        "CONTROL": CONTROL, "FINALIZER": FINALIZER, "TEST": TEST,
        "EXTRACTOR_TEST": EXTRACTOR_TEST, "LOCAL_SOURCES": LOCAL_SOURCES,
        "TASKS": tuple((project, "pypi-only") for project in PROJECTS),
        "PRIOR_PROJECTS": PRIOR_PROJECTS, "CONTROL_ARM": CONTROL_ARM,
        "CANDIDATE_ARM": CANDIDATE_ARM, "ARMS": ARMS, "COLUMNS": COLUMNS,
        "FALLBACK_TABLE": FALLBACK_TABLE, "EVIDENCE_CHARS": EVIDENCE_CHARS,
        "NAMESPACE_EVIDENCE_CHARS": NAMESPACE_EVIDENCE_CHARS,
        # The schema validator historically hard-codes two targets. Production
        # protocol translation below restores the real one-target value.
        "FETCH_TARGETS_PER_TASK": 2,
        "LEASE_OWNER": LEASE_OWNER, "LEASE_PURPOSE": LEASE_PURPOSE,
        "source_policy": source_policy, "task_vector": task_vector,
        "endpoint_vector": endpoint_vector, "gold_endpoint_vector": gold_endpoint_vector,
        "arm_order_vector": arm_order_vector, "gates": gates,
    }
    for name, value in assignments.items():
        setattr(schema, name, value)


def dependency_manifest(root: Path, *, tracked: bool = True) -> dict[str, str]:
    _configure_schema()
    return schema.dependency_manifest(root, tracked=tracked)


def _atomic_contract() -> dict[str, Any]:
    return {
        "fetch_all_tasks_before_model": True,
        "parser_ready_tasks": TASK_COUNT,
        "parser_ready_unique_fields": TASK_COUNT * 5,
        "parser_conflicts": 0,
        "model_calls_if_parser_no_go": 0,
        "output_root_created_if_parser_no_go": False,
        "no_retry_resume_or_population_replacement": True,
    }


def _augment(value: dict[str, Any]) -> dict[str, Any]:
    value.pop("protocol_payload_sha256", None)
    value["execution"]["fetch_targets_per_task"] = FETCH_TARGETS_PER_TASK
    value["atomic_parser_readiness"] = _atomic_contract()
    return seal(value, "protocol_payload_sha256")


def _schema_copy(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    copied["execution"] = dict(copied.get("execution") or {})
    copied["execution"]["fetch_targets_per_task"] = 2
    copied.pop("atomic_parser_readiness", None)
    copied.pop("protocol_payload_sha256", None)
    return seal(copied, "protocol_payload_sha256")


def build_protocol(root: Path, *, now: int) -> dict[str, Any]:
    _configure_schema()
    if (root / PARSER_READINESS).exists() or (root / PARSER_READINESS).is_symlink():
        raise FileExistsError("V2.49.79 parser readiness surface exists")
    return _augment(schema.build_protocol(root, now=now))


def validate_protocol(root: Path, value: Mapping[str, Any]) -> dict[str, Any]:
    _configure_schema()
    if value.get("atomic_parser_readiness") != _atomic_contract() or (value.get("execution") or {}).get("fetch_targets_per_task") != 1:
        raise RuntimeError("V2.49.79 atomic protocol drifted")
    schema.validate_protocol(root, _schema_copy(value))
    return dict(value)


def build_protocol_untracked(root: Path, *, now: int) -> dict[str, Any]:
    _configure_schema()
    return _augment(schema.build_protocol_untracked(root, now=now))


def validate_protocol_untracked(root: Path, value: Mapping[str, Any]) -> dict[str, Any]:
    _configure_schema()
    if value.get("atomic_parser_readiness") != _atomic_contract() or (value.get("execution") or {}).get("fetch_targets_per_task") != 1:
        raise RuntimeError("V2.49.79 build-only atomic protocol drifted")
    schema.validate_protocol_untracked(root, _schema_copy(value))
    return dict(value)


__all__ = [name for name in globals() if name.isupper()] + [
    "arm_order_vector", "build_protocol", "build_protocol_untracked",
    "dependency_manifest", "endpoint_vector", "gates", "git",
    "gold_endpoint_vector", "ordinary_tracked", "payload_sha256",
    "proc_start_ticks", "seal", "sealed", "sha256", "source_policy",
    "task_vector", "validate_protocol", "validate_protocol_untracked",
    "watcher_snapshot",
]
