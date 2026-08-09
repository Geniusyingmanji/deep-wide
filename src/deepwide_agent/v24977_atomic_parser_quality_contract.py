"""Atomic parser-readiness and paired quality contract for V2.49.77."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from . import v24973_identity_bound_field_quality_contract as schema


DATE = "20260809"
PROTOCOL_ID = "v24977_atomic_section_bound_raw_authority_quality_gate_v1"
BUILD_AUDIT = Path(f"results/v24977_atomic_parser_quality_build_audit_v1_{DATE}.json")
PROTOCOL = Path(f"results/v24977_atomic_parser_quality_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v24977_atomic_parser_quality_preactivation_audit_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v24977_atomic_parser_quality_execution_start_v1_{DATE}.json")
PARSER_READINESS = Path(f"results/v24977_atomic_parser_readiness_v1_{DATE}.json")
FORWARD_RESULT = Path(f"results/v24977_atomic_parser_quality_forward_result_v1_{DATE}.json")
FORWARD_AUDIT = Path(f"results/v24977_atomic_parser_quality_forward_audit_v1_{DATE}.json")
EVALUATOR_PROTOCOL = Path(f"results/v24977_atomic_parser_quality_evaluator_preregistration_v1_{DATE}.json")
RESULT = Path(f"results/v24977_atomic_parser_quality_result_v1_{DATE}.json")
POSTAUDIT = Path(f"results/v24977_atomic_parser_quality_postresult_audit_v1_{DATE}.json")
OUTPUT_ROOT = Path(f"outputs/v24977_atomic_parser_quality_v1_{DATE}")
TASK_ROWS = OUTPUT_ROOT / "frozen_task_results.jsonl"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
GOLD_SNAPSHOT = OUTPUT_ROOT / "postfreeze_authority_gold.json"

SOURCE = Path("src/deepwide_agent/v24977_atomic_parser_quality_contract.py")
EXTRACTOR = Path("src/deepwide_agent/v24976_section_bound_raw_authority_fields.py")
RUNTIME = Path("scripts/run_v24977_atomic_parser_quality.py")
CONTROL = Path("scripts/control_v24977_atomic_parser_quality.py")
FINALIZER = Path("scripts/finalize_v24977_atomic_parser_quality.py")
TEST = Path("tests/test_v24977_atomic_parser_quality.py")
EXTRACTOR_TEST = Path("tests/test_v24976_section_bound_raw_authority_fields.py")
PARENT_CONTRACT = Path("src/deepwide_agent/v24975_raw_authority_quality_contract.py")
PARENT_RUNTIME = Path("scripts/run_v24975_raw_authority_quality.py")
PARENT_CONTROL = Path("scripts/control_v24975_raw_authority_quality.py")
PARENT_FINALIZER = Path("scripts/finalize_v24975_raw_authority_quality.py")
PARENT_TEST = Path("tests/test_v24975_raw_authority_quality.py")
SCHEMA_CONTRACT = Path("src/deepwide_agent/v24973_identity_bound_field_quality_contract.py")
SCHEMA_RUNTIME = Path("scripts/run_v24973_identity_bound_field_quality.py")
SCHEMA_CONTROL = Path("scripts/control_v24973_identity_bound_field_quality.py")
SCHEMA_FINALIZER = Path("scripts/finalize_v24973_identity_bound_field_quality.py")
FIELD_EXTRACTOR = Path("src/deepwide_agent/v24972_identity_bound_compact_fields.py")
LOCAL_SOURCES = (
    SOURCE, EXTRACTOR, RUNTIME, CONTROL, FINALIZER, TEST, EXTRACTOR_TEST,
    PARENT_CONTRACT, PARENT_RUNTIME, PARENT_CONTROL, PARENT_FINALIZER,
    PARENT_TEST, SCHEMA_CONTRACT, SCHEMA_RUNTIME, SCHEMA_CONTROL,
    SCHEMA_FINALIZER, FIELD_EXTRACTOR,
)

TASKS = (
    ("pyyaml", "yaml/pyyaml"),
    ("msgpack", "msgpack/msgpack-python"),
    ("ujson", "ultrajson/ultrajson"),
    ("zstandard", "indygreg/python-zstandard"),
    ("lz4", "python-lz4/python-lz4"),
    ("pycryptodome", "Legrandin/pycryptodome"),
    ("protobuf", "protocolbuffers/protobuf"),
    ("flatbuffers", "google/flatbuffers"),
    ("textual", "Textualize/textual"),
    ("prompt-toolkit", "prompt-toolkit/python-prompt-toolkit"),
    ("uvloop", "MagicStack/uvloop"),
    ("websockets", "python-websockets/websockets"),
    ("twisted", "twisted/twisted"),
    ("scrapy", "scrapy/scrapy"),
    ("pyopenssl", "pyca/pyopenssl"),
    ("playwright", "microsoft/playwright-python"),
    ("selenium", "SeleniumHQ/selenium"),
    ("sanic", "sanic-org/sanic"),
    ("hypercorn", "pgjones/hypercorn"),
    ("aiofiles", "Tinche/aiofiles"),
)

# Everything used by prior external populations and every transport/layout
# probe remains excluded.  The final V2.49.77 vector is not probed pre-freeze.
PROBED_PROJECTS = frozenset(
    {
        "pendulum", "marshmallow", "webargs", "apispec", "flask-smorest",
        "cerberus", "voluptuous", "schematics", "dacite", "mashumaro",
        "dataclasses-json", "deepdiff", "boltons", "toolz", "cytoolz",
        "pyrsistent", "immutables", "sortedcontainers", "bidict", "cachetools",
        "diskcache", "dogpile.cache", "beaker", "redis", "pymongo", "psycopg",
        "asyncpg", "pg8000", "pymysql", "safetensors", "huggingface-hub",
        "einops", "opt-einsum", "numexpr", "bottleneck", "xarray", "dask",
        "distributed", "partd", "locket", "psutil", "humanize", "tqdm",
        "tabulate", "networkx", "sympy", "mpmath", "joblib", "threadpoolctl",
        "cloudpickle", "dill", "multiprocess", "fsspec", "s3fs", "aiohttp",
        "yarl", "multidict", "frozenlist", "aiosignal", "async-timeout",
    }
)
PRIOR_PROJECTS = frozenset(schema.PRIOR_PROJECTS).union(
    project for project, _repo in schema.TASKS
).union(
    {
        "pandas", "scipy", "scikit-learn", "matplotlib", "seaborn", "polars",
        "pyarrow", "duckdb", "ipython", "traitlets", "jupyter-core",
        "jupyter-client", "tornado", "pyzmq", "nbformat", "nbclient",
        "nbconvert", "jupyter-server", "jupyterlab", "notebook",
    }
).union(PROBED_PROJECTS)

ENDPOINT = schema.ENDPOINT
MODEL = schema.MODEL
CONTROL_ARM = schema.CONTROL_ARM
CANDIDATE_ARM = schema.CANDIDATE_ARM
ARMS = schema.ARMS
TASK_COUNT = schema.TASK_COUNT
EXECUTOR_CONCURRENCY = schema.EXECUTOR_CONCURRENCY
MODEL_CONCURRENCY = schema.MODEL_CONCURRENCY
NAMESPACE_EVIDENCE_CHARS = schema.NAMESPACE_EVIDENCE_CHARS
EVIDENCE_CHARS = schema.EVIDENCE_CHARS
MODEL_OUTPUT_TOKENS = schema.MODEL_OUTPUT_TOKENS
TASK_DEADLINE_SECONDS = schema.TASK_DEADLINE_SECONDS
FETCH_TARGETS_PER_TASK = schema.FETCH_TARGETS_PER_TASK
MINIMUM_PREDICTION_CHANGES = schema.MINIMUM_PREDICTION_CHANGES
MAX_RESPONSE_BYTES = 8_000_000
FETCH_TIMEOUT = (5.0, 45.0)
LEASE_OWNER = "v24977_atomic_parser_quality_forward_v1"
LEASE_PURPOSE = "atomic_parser_ready_then_paired_raw_authority_quality_gate"
LEASE_PATH = schema.LEASE_PATH
COLUMNS = schema.COLUMNS
FALLBACK_TABLE = schema.FALLBACK_TABLE
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
    projects = [project for project, _repository in TASKS]
    if len(TASKS) != TASK_COUNT or len(set(TASKS)) != TASK_COUNT or set(projects) & PRIOR_PROJECTS:
        raise RuntimeError("V2.49.77 fresh population drifted")
    rows = []
    for project, repository in TASKS:
        opaque = "task_" + hashlib.sha256(
            f"v24977:{project}:{repository}".encode()
        ).hexdigest()[:24]
        question = (
            "Using only the supplied fetched public pages, return exactly one Markdown table and no prose. "
            "Include exactly one row. The visible identities are:\n"
            f"<PACKAGE>{project}</PACKAGE><REPOSITORY>{repository}</REPOSITORY>\n"
            "Columns exactly: " + " | ".join(COLUMNS) + ". "
            "PyPI fields describe the current PyPI project metadata. GitHub fields describe the latest non-draft, non-prerelease release for the visible repository. "
            "Dates use YYYY-MM-DD. Preserve the Requires-Python expression while collapsing whitespace. Use Unknown only when the supplied pages do not establish a value."
        )
        rows.append({"opaque_id": opaque, "question": question})
    return rows


def endpoint_vector() -> list[list[str]]:
    return [[f"https://pypi.org/pypi/{p}/json", f"https://github.com/{r}/releases"] for p, r in TASKS]


def gold_endpoint_vector() -> list[list[str]]:
    return [[f"https://pypi.org/pypi/{p}/json", f"https://api.github.com/repos/{r}/releases/latest"] for p, r in TASKS]


def arm_order_vector() -> list[list[str]]:
    ranked = sorted(
        range(TASK_COUNT),
        key=lambda index: hashlib.sha256(
            f"v24977-arm-order:{task_vector()[index]['opaque_id']}".encode()
        ).hexdigest(),
    )
    candidate_first = set(ranked[: TASK_COUNT // 2])
    return [[CANDIDATE_ARM, CONTROL_ARM] if i in candidate_first else [CONTROL_ARM, CANDIDATE_ARM] for i in range(TASK_COUNT)]


def gates() -> dict[str, Any]:
    return schema.gates()


def source_policy() -> dict[str, Any]:
    return {
        "runtime_boundary": ["opaque_id", "question", "same_forward_public_pages"],
        "all_twenty_page_pairs_fetched_and_parsed_before_any_model_call": True,
        "parser_readiness_go_requires_tasks_fields_conflicts": [20, 80, 0],
        "parser_readiness_failure_stops_before_output_root_and_model": True,
        "parser_readiness_receipt_contains_counts_only": True,
        "same_exact_address_complete_page_bytes_for_both_arms": True,
        "control_is_fixed_prefix_of_noisy_raw_authority_bytes": True,
        "candidate_section_bound_record_derived_from_complete_shared_bytes": True,
        "same_evidence_chars_prompt_model_output_cap_and_attempt_count": True,
        "search_tool_or_github_api_used": False,
        "prediction_freeze_before_evaluator_metrics_or_quality_decision": True,
        "deepwidebench_manifest_mapping_gold_category_question_type_split_evaluator_score_reward_read_by_forward": False,
        "entropy_or_information_gain_assigns_credit": False,
        "final_population_url_model_or_evaluator_probed_before_freeze": False,
        "public_exact220_or_sota_authorized": False,
    }


def _configure_schema() -> None:
    assignments = {
        "DATE": DATE, "PROTOCOL_ID": PROTOCOL_ID, "BUILD_AUDIT": BUILD_AUDIT,
        "PROTOCOL": PROTOCOL, "PREAUDIT": PREAUDIT,
        "EXECUTION_START": EXECUTION_START, "FORWARD_RESULT": FORWARD_RESULT,
        "FORWARD_AUDIT": FORWARD_AUDIT, "EVALUATOR_PROTOCOL": EVALUATOR_PROTOCOL,
        "RESULT": RESULT, "POSTAUDIT": POSTAUDIT, "OUTPUT_ROOT": OUTPUT_ROOT,
        "TASK_ROWS": TASK_ROWS, "PREDICTION_FREEZE": PREDICTION_FREEZE,
        "GOLD_SNAPSHOT": GOLD_SNAPSHOT, "SOURCE": SOURCE, "EXTRACTOR": EXTRACTOR,
        "RUNTIME": RUNTIME, "CONTROL": CONTROL, "FINALIZER": FINALIZER,
        "TEST": TEST, "EXTRACTOR_TEST": EXTRACTOR_TEST,
        "LOCAL_SOURCES": LOCAL_SOURCES, "TASKS": TASKS,
        "PRIOR_PROJECTS": PRIOR_PROJECTS, "LEASE_OWNER": LEASE_OWNER,
        "LEASE_PURPOSE": LEASE_PURPOSE, "source_policy": source_policy,
        "task_vector": task_vector, "endpoint_vector": endpoint_vector,
        "gold_endpoint_vector": gold_endpoint_vector,
        "arm_order_vector": arm_order_vector,
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
        "parser_ready_unique_fields": TASK_COUNT * 4,
        "parser_conflicts": 0,
        "model_calls_if_parser_no_go": 0,
        "output_root_created_if_parser_no_go": False,
        "no_retry_resume_or_population_replacement": True,
    }


def _augment(value: dict[str, Any]) -> dict[str, Any]:
    value.pop("protocol_payload_sha256", None)
    value["atomic_parser_readiness"] = _atomic_contract()
    return seal(value, "protocol_payload_sha256")


def build_protocol(root: Path, *, now: int) -> dict[str, Any]:
    _configure_schema()
    if (root / PARSER_READINESS).exists() or (root / PARSER_READINESS).is_symlink():
        raise FileExistsError("V2.49.77 parser readiness surface exists")
    return _augment(schema.build_protocol(root, now=now))


def validate_protocol(root: Path, value: Mapping[str, Any]) -> dict[str, Any]:
    _configure_schema()
    copied = dict(value)
    if copied.get("atomic_parser_readiness") != _atomic_contract():
        raise RuntimeError("V2.49.77 atomic parser contract drifted")
    copied.pop("atomic_parser_readiness")
    copied.pop("protocol_payload_sha256", None)
    seal(copied, "protocol_payload_sha256")
    schema.validate_protocol(root, copied)
    return dict(value)


def build_protocol_untracked(root: Path, *, now: int) -> dict[str, Any]:
    _configure_schema()
    return _augment(schema.build_protocol_untracked(root, now=now))


def validate_protocol_untracked(root: Path, value: Mapping[str, Any]) -> dict[str, Any]:
    _configure_schema()
    copied = dict(value)
    if copied.get("atomic_parser_readiness") != _atomic_contract():
        raise RuntimeError("V2.49.77 build-only atomic parser contract drifted")
    copied.pop("atomic_parser_readiness")
    copied.pop("protocol_payload_sha256", None)
    seal(copied, "protocol_payload_sha256")
    schema.validate_protocol_untracked(root, copied)
    return dict(value)


__all__ = [name for name in globals() if name.isupper()] + [
    "arm_order_vector", "build_protocol", "build_protocol_untracked",
    "dependency_manifest", "endpoint_vector", "gates", "git",
    "gold_endpoint_vector", "ordinary_tracked", "payload_sha256",
    "proc_start_ticks", "seal", "sealed", "sha256", "source_policy",
    "task_vector", "validate_protocol", "validate_protocol_untracked",
    "watcher_snapshot",
]
