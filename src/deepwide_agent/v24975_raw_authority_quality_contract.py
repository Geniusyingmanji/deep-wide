"""Fresh quality gate for compact fields derived from noisy raw authorities.

The V2.49.73 artifact roles are reused as a compatibility schema only.  This
contract has an independent protocol ID, task vector, dependency manifest, and
create-only artifact namespace; no V2.49.73 prediction or result is reused.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from . import v24973_identity_bound_field_quality_contract as parent


DATE = "20260809"
PROTOCOL_ID = "v24975_fresh_raw_authority_compact_field_quality_gate_v1"
BUILD_AUDIT = Path(f"results/v24975_raw_authority_quality_build_audit_v1_{DATE}.json")
PROTOCOL = Path(f"results/v24975_raw_authority_quality_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v24975_raw_authority_quality_preactivation_audit_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v24975_raw_authority_quality_execution_start_v1_{DATE}.json")
FORWARD_RESULT = Path(f"results/v24975_raw_authority_quality_forward_result_v1_{DATE}.json")
FORWARD_AUDIT = Path(f"results/v24975_raw_authority_quality_forward_audit_v1_{DATE}.json")
EVALUATOR_PROTOCOL = Path(f"results/v24975_raw_authority_quality_evaluator_preregistration_v1_{DATE}.json")
RESULT = Path(f"results/v24975_raw_authority_quality_result_v1_{DATE}.json")
POSTAUDIT = Path(f"results/v24975_raw_authority_quality_postresult_audit_v1_{DATE}.json")
OUTPUT_ROOT = Path(f"outputs/v24975_raw_authority_quality_v1_{DATE}")
TASK_ROWS = OUTPUT_ROOT / "frozen_task_results.jsonl"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
GOLD_SNAPSHOT = OUTPUT_ROOT / "postfreeze_authority_gold.json"

SOURCE = Path("src/deepwide_agent/v24975_raw_authority_quality_contract.py")
EXTRACTOR = Path("src/deepwide_agent/v24974_raw_authority_compact_fields.py")
RUNTIME = Path("scripts/run_v24975_raw_authority_quality.py")
CONTROL = Path("scripts/control_v24975_raw_authority_quality.py")
FINALIZER = Path("scripts/finalize_v24975_raw_authority_quality.py")
TEST = Path("tests/test_v24975_raw_authority_quality.py")
EXTRACTOR_TEST = Path("tests/test_v24974_raw_authority_compact_fields.py")
PARENT_CONTRACT = Path("src/deepwide_agent/v24973_identity_bound_field_quality_contract.py")
PARENT_RUNTIME = Path("scripts/run_v24973_identity_bound_field_quality.py")
PARENT_CONTROL = Path("scripts/control_v24973_identity_bound_field_quality.py")
PARENT_FINALIZER = Path("scripts/finalize_v24973_identity_bound_field_quality.py")
PARENT_TEST = Path("tests/test_v24973_identity_bound_field_quality.py")
FIELD_EXTRACTOR = Path("src/deepwide_agent/v24972_identity_bound_compact_fields.py")
FIELD_EXTRACTOR_TEST = Path("tests/test_v24972_identity_bound_compact_fields.py")
LOCAL_SOURCES = (
    SOURCE,
    EXTRACTOR,
    RUNTIME,
    CONTROL,
    FINALIZER,
    TEST,
    EXTRACTOR_TEST,
    PARENT_CONTRACT,
    PARENT_RUNTIME,
    PARENT_CONTROL,
    PARENT_FINALIZER,
    PARENT_TEST,
    FIELD_EXTRACTOR,
    FIELD_EXTRACTOR_TEST,
)

TASKS = (
    ("pandas", "pandas-dev/pandas"),
    ("scipy", "scipy/scipy"),
    ("scikit-learn", "scikit-learn/scikit-learn"),
    ("matplotlib", "matplotlib/matplotlib"),
    ("seaborn", "mwaskom/seaborn"),
    ("polars", "pola-rs/polars"),
    ("pyarrow", "apache/arrow"),
    ("duckdb", "duckdb/duckdb"),
    ("ipython", "ipython/ipython"),
    ("traitlets", "ipython/traitlets"),
    ("jupyter-core", "jupyter/jupyter_core"),
    ("jupyter-client", "jupyter/jupyter_client"),
    ("tornado", "tornadoweb/tornado"),
    ("pyzmq", "zeromq/pyzmq"),
    ("nbformat", "jupyter/nbformat"),
    ("nbclient", "jupyter/nbclient"),
    ("nbconvert", "jupyter/nbconvert"),
    ("jupyter-server", "jupyter-server/jupyter_server"),
    ("jupyterlab", "jupyterlab/jupyterlab"),
    ("notebook", "jupyter/notebook"),
)

# Every package touched during V2.49.74 transport/layout feasibility work is
# excluded from the final model/evaluator population regardless of outcome.
LAYOUT_PROBE_EXCLUSIONS = frozenset(
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
PRIOR_PROJECTS = frozenset(parent.PRIOR_PROJECTS).union(
    project for project, _repository in parent.TASKS
).union(LAYOUT_PROBE_EXCLUSIONS)

MAX_RESPONSE_BYTES = 8_000_000
FETCH_TIMEOUT = (5.0, 45.0)

# Unchanged matched-cost and safety constants.
ENDPOINT = parent.ENDPOINT
MODEL = parent.MODEL
CONTROL_ARM = parent.CONTROL_ARM
CANDIDATE_ARM = parent.CANDIDATE_ARM
ARMS = parent.ARMS
TASK_COUNT = parent.TASK_COUNT
EXECUTOR_CONCURRENCY = parent.EXECUTOR_CONCURRENCY
MODEL_CONCURRENCY = parent.MODEL_CONCURRENCY
NAMESPACE_EVIDENCE_CHARS = parent.NAMESPACE_EVIDENCE_CHARS
EVIDENCE_CHARS = parent.EVIDENCE_CHARS
MODEL_OUTPUT_TOKENS = parent.MODEL_OUTPUT_TOKENS
TASK_DEADLINE_SECONDS = parent.TASK_DEADLINE_SECONDS
FETCH_TARGETS_PER_TASK = parent.FETCH_TARGETS_PER_TASK
MINIMUM_PREDICTION_CHANGES = parent.MINIMUM_PREDICTION_CHANGES
LEASE_OWNER = "v24975_raw_authority_quality_forward_v1"
LEASE_PURPOSE = "fresh_shared_raw_authority_compact_field_quality_gate"
LEASE_PATH = parent.LEASE_PATH
COLUMNS = parent.COLUMNS
FALLBACK_TABLE = parent.FALLBACK_TABLE
PROTECTED_WATCHERS = parent.PROTECTED_WATCHERS


def source_policy() -> dict[str, Any]:
    return {
        "runtime_boundary": ["opaque_id", "question", "same_forward_public_pages"],
        "same_exact_address_complete_page_bytes_for_both_arms": True,
        "control_is_fixed_prefix_of_noisy_raw_authority_bytes": True,
        "candidate_compact_record_derived_from_complete_shared_bytes": True,
        "candidate_prefixes_record_then_same_ordered_raw_prefix_under_same_cap": True,
        "bounded_streaming_response_cap_bytes": MAX_RESPONSE_BYTES,
        "search_tool_or_github_api_used": False,
        "same_evidence_chars_prompt_model_output_cap_and_attempt_count": True,
        "only_treatment_is_identity_bound_compact_field_prefix": True,
        "prediction_freeze_before_evaluator_metrics_or_quality_decision": True,
        "deepwidebench_manifest_mapping_gold_category_question_type_split_evaluator_score_reward_read_by_forward": False,
        "entropy_or_information_gain_assigns_credit": False,
        "v24973_artifact_role_strings_reused_as_schema_only": True,
        "v24973_predictions_results_or_task_vector_reused": False,
        "layout_probes_used_model_or_evaluator": False,
        "public_exact220_or_sota_authorized": False,
    }


def configure_parent() -> None:
    assignments = {
        "DATE": DATE,
        "PROTOCOL_ID": PROTOCOL_ID,
        "BUILD_AUDIT": BUILD_AUDIT,
        "PROTOCOL": PROTOCOL,
        "PREAUDIT": PREAUDIT,
        "EXECUTION_START": EXECUTION_START,
        "FORWARD_RESULT": FORWARD_RESULT,
        "FORWARD_AUDIT": FORWARD_AUDIT,
        "EVALUATOR_PROTOCOL": EVALUATOR_PROTOCOL,
        "RESULT": RESULT,
        "POSTAUDIT": POSTAUDIT,
        "OUTPUT_ROOT": OUTPUT_ROOT,
        "TASK_ROWS": TASK_ROWS,
        "PREDICTION_FREEZE": PREDICTION_FREEZE,
        "GOLD_SNAPSHOT": GOLD_SNAPSHOT,
        "SOURCE": SOURCE,
        "EXTRACTOR": EXTRACTOR,
        "RUNTIME": RUNTIME,
        "CONTROL": CONTROL,
        "FINALIZER": FINALIZER,
        "TEST": TEST,
        "EXTRACTOR_TEST": EXTRACTOR_TEST,
        "LOCAL_SOURCES": LOCAL_SOURCES,
        "TASKS": TASKS,
        "PRIOR_PROJECTS": PRIOR_PROJECTS,
        "LEASE_OWNER": LEASE_OWNER,
        "LEASE_PURPOSE": LEASE_PURPOSE,
        "source_policy": source_policy,
        "task_vector": task_vector,
        "endpoint_vector": endpoint_vector,
        "gold_endpoint_vector": gold_endpoint_vector,
        "arm_order_vector": arm_order_vector,
    }
    for name, value in assignments.items():
        setattr(parent, name, value)


payload_sha256 = parent.payload_sha256
sha256 = parent.sha256
sealed = parent.sealed
seal = parent.seal
git = parent.git
ordinary_tracked = parent.ordinary_tracked
proc_start_ticks = parent.proc_start_ticks
watcher_snapshot = parent.watcher_snapshot


def task_vector() -> list[dict[str, str]]:
    projects = [project for project, _repository in TASKS]
    if (
        len(TASKS) != TASK_COUNT
        or len(set(TASKS)) != TASK_COUNT
        or set(projects) & PRIOR_PROJECTS
    ):
        raise RuntimeError("V2.49.75 fresh population drifted")
    output = []
    for project, repository in TASKS:
        opaque = "task_" + hashlib.sha256(
            f"v24975:{project}:{repository}".encode()
        ).hexdigest()[:24]
        question = (
            "Using only the supplied fetched public pages, return exactly one Markdown table and no prose. "
            "Include exactly one row. The visible identities are:\n"
            f"<PACKAGE>{project}</PACKAGE><REPOSITORY>{repository}</REPOSITORY>\n"
            "Columns exactly: " + " | ".join(COLUMNS) + ". "
            "PyPI fields describe the current PyPI project metadata. GitHub fields describe the latest non-draft, non-prerelease release for the visible repository. "
            "Dates use YYYY-MM-DD. Preserve the Requires-Python expression while collapsing whitespace. Use Unknown only when the supplied pages do not establish a value."
        )
        output.append({"opaque_id": opaque, "question": question})
    return output


def endpoint_vector() -> list[list[str]]:
    return [
        [
            f"https://pypi.org/pypi/{project}/json",
            f"https://github.com/{repository}/releases",
        ]
        for project, repository in TASKS
    ]


def gold_endpoint_vector() -> list[list[str]]:
    return [
        [
            f"https://pypi.org/pypi/{project}/json",
            f"https://api.github.com/repos/{repository}/releases/latest",
        ]
        for project, repository in TASKS
    ]


def arm_order_vector() -> list[list[str]]:
    ranked = sorted(
        range(TASK_COUNT),
        key=lambda index: hashlib.sha256(
            f"v24975-arm-order:{task_vector()[index]['opaque_id']}".encode()
        ).hexdigest(),
    )
    candidate_first = set(ranked[: TASK_COUNT // 2])
    return [
        [CANDIDATE_ARM, CONTROL_ARM]
        if index in candidate_first
        else [CONTROL_ARM, CANDIDATE_ARM]
        for index in range(TASK_COUNT)
    ]


def gates() -> dict[str, Any]:
    configure_parent()
    return parent.gates()


def dependency_manifest(root: Path, *, tracked: bool = True) -> dict[str, str]:
    configure_parent()
    return parent.dependency_manifest(root, tracked=tracked)


def build_protocol(root: Path, *, now: int) -> dict[str, Any]:
    configure_parent()
    return parent.build_protocol(root, now=now)


def validate_protocol(root: Path, value: Mapping[str, Any]) -> dict[str, Any]:
    configure_parent()
    return parent.validate_protocol(root, value)


def build_protocol_untracked(root: Path, *, now: int) -> dict[str, Any]:
    configure_parent()
    return parent.build_protocol_untracked(root, now=now)


def validate_protocol_untracked(root: Path, value: Mapping[str, Any]) -> dict[str, Any]:
    configure_parent()
    return parent.validate_protocol_untracked(root, value)


__all__ = [name for name in globals() if name.isupper()] + [
    "arm_order_vector", "build_protocol", "build_protocol_untracked",
    "configure_parent", "dependency_manifest", "endpoint_vector", "gates",
    "git", "gold_endpoint_vector", "ordinary_tracked", "payload_sha256",
    "proc_start_ticks", "seal", "sealed", "sha256", "source_policy",
    "task_vector", "validate_protocol", "validate_protocol_untracked",
    "watcher_snapshot",
]
