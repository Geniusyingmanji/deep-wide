"""Fresh shared-page quality gate for identity-bound compact field evidence."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Any


DATE = "20260809"
PROTOCOL_ID = "v24973_fresh_identity_bound_compact_field_quality_gate_v1"
BUILD_AUDIT = Path(f"results/v24973_identity_bound_field_build_audit_v1_{DATE}.json")
PROTOCOL = Path(f"results/v24973_identity_bound_field_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v24973_identity_bound_field_preactivation_audit_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v24973_identity_bound_field_execution_start_v1_{DATE}.json")
FORWARD_RESULT = Path(f"results/v24973_identity_bound_field_forward_result_v1_{DATE}.json")
FORWARD_AUDIT = Path(f"results/v24973_identity_bound_field_forward_audit_v1_{DATE}.json")
EVALUATOR_PROTOCOL = Path(f"results/v24973_identity_bound_field_evaluator_preregistration_v1_{DATE}.json")
RESULT = Path(f"results/v24973_identity_bound_field_result_v1_{DATE}.json")
POSTAUDIT = Path(f"results/v24973_identity_bound_field_postresult_audit_v1_{DATE}.json")
OUTPUT_ROOT = Path(f"outputs/v24973_identity_bound_field_quality_v1_{DATE}")
TASK_ROWS = OUTPUT_ROOT / "frozen_task_results.jsonl"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
GOLD_SNAPSHOT = OUTPUT_ROOT / "postfreeze_authority_gold.json"
LEASE_PATH = Path("outputs/deepwide_benchmark_api.lease.lock")

SOURCE = Path("src/deepwide_agent/v24973_identity_bound_field_quality_contract.py")
EXTRACTOR = Path("src/deepwide_agent/v24972_identity_bound_compact_fields.py")
RUNTIME = Path("scripts/run_v24973_identity_bound_field_quality.py")
CONTROL = Path("scripts/control_v24973_identity_bound_field_quality.py")
FINALIZER = Path("scripts/finalize_v24973_identity_bound_field_quality.py")
TEST = Path("tests/test_v24973_identity_bound_field_quality.py")
EXTRACTOR_TEST = Path("tests/test_v24972_identity_bound_compact_fields.py")
LOCAL_SOURCES = (SOURCE, EXTRACTOR, RUNTIME, CONTROL, FINALIZER, TEST, EXTRACTOR_TEST)

ENDPOINT = "http://127.0.0.1:9878/responses"
MODEL = "gpt-5.6-sol"
CONTROL_ARM = "raw_authoritative_pages"
CANDIDATE_ARM = "identity_bound_compact_fields"
ARMS = (CONTROL_ARM, CANDIDATE_ARM)
TASK_COUNT = 20
EXECUTOR_CONCURRENCY = 20
MODEL_CONCURRENCY = 8
NAMESPACE_EVIDENCE_CHARS = 8_000
EVIDENCE_CHARS = NAMESPACE_EVIDENCE_CHARS * 2
MODEL_OUTPUT_TOKENS = 2_400
TASK_DEADLINE_SECONDS = 180.0
FETCH_TARGETS_PER_TASK = 2
MINIMUM_PREDICTION_CHANGES = 10
LEASE_OWNER = "v24973_identity_bound_field_quality_forward_v1"
LEASE_PURPOSE = "fresh_shared_authority_pages_compact_field_quality_gate"

TASKS = (
    ("pillow", "python-pillow/Pillow"),
    ("arrow", "arrow-py/arrow"),
    ("python-dateutil", "dateutil/dateutil"),
    ("pytz", "stub42/pytz"),
    ("tzdata", "python/tzdata"),
    ("jsonschema", "python-jsonschema/jsonschema"),
    ("referencing", "python-jsonschema/referencing"),
    ("rpds-py", "crate-py/rpds"),
    ("lxml", "lxml/lxml"),
    ("soupsieve", "facelessuser/soupsieve"),
    ("markdown-it-py", "executablebooks/markdown-it-py"),
    ("pygments", "pygments/pygments"),
    ("sphinx", "sphinx-doc/sphinx"),
    ("babel", "python-babel/babel"),
    ("alabaster", "sphinx-doc/alabaster"),
    ("blinker", "pallets-eco/blinker"),
    ("pathspec", "cpburnz/python-pathspec"),
    ("nodeenv", "ekalinin/nodeenv"),
    ("pre-commit", "pre-commit/pre-commit"),
    ("wrapt", "GrahamDumpleton/wrapt"),
)
PRIOR_PROJECTS = frozenset(
    {
        "pydantic-settings", "rich", "httpx", "typer", "hatchling",
        "poetry-core", "twine", "virtualenv", "pipx", "cibuildwheel",
        "maturin", "meson-python", "scikit-build-core", "pytest-xdist",
        "pytest-cov", "hypothesis", "cattrs", "msgspec", "orjson",
        "rapidfuzz", "fastapi", "starlette", "uvicorn", "sqlalchemy",
        "alembic", "attrs", "structlog", "loguru", "tenacity", "anyio",
        "trio", "click", "flask", "werkzeug", "jinja2", "itsdangerous",
        "markupsafe", "black", "ruff", "mypy", "pytest-asyncio",
        "pydantic", "numpy",
        # V2.49.73 parser-development population, permanently excluded from
        # the frozen quality gate after exact-page layout inspection.
        "requests", "httpcore", "platformdirs", "filelock", "packaging",
        "build", "installer", "trove-classifiers", "tomlkit", "dulwich",
        "cachecontrol", "keyring", "iniconfig", "exceptiongroup",
        "typing-extensions", "setuptools", "wheel", "distlib", "urllib3",
        "charset-normalizer",
        # Additional transport/layout feasibility probes excluded before the
        # final task vector was frozen; no model or evaluator was called.
        "certifi", "idna", "sniffio", "h11", "cffi", "pycparser",
        "importlib-metadata", "zipp", "more-itertools", "six", "decorator",
        "pluggy", "coverage", "tox", "pip", "pip-tools", "pkginfo",
        "readme-renderer", "requests-toolbelt", "resolvelib", "cryptography",
        "bcrypt", "pynacl", "paramiko", "fabric", "invoke", "beautifulsoup4",
        "docutils", "imagesize", "snowballstemmer", "greenlet", "tomli",
        "tomli-w", "identify", "cfgv", "virtualenv-clone", "deprecated",
        "typing-inspection", "annotated-types",
    }
)
COLUMNS = (
    "Package",
    "PyPI latest version",
    "Requires-Python",
    "GitHub latest release tag",
    "GitHub latest release date (YYYY-MM-DD)",
)
FALLBACK_TABLE = (
    "| Package | PyPI latest version | Requires-Python | GitHub latest release tag | GitHub latest release date (YYYY-MM-DD) |\n"
    "|---|---|---|---|---|\n"
    "| Unknown | Unknown | Unknown | Unknown | Unknown |"
)
PROTECTED_WATCHERS = (
    (795336, 713986317, "scripts/watch_v2415_r1_checkpoint_liveness.py"),
    (3061652, 747569004, "scripts/watch_v24218_exact220_executor.py"),
    (2808901, 746680268, "scripts/watch_v24215_joint_package_recovery.py"),
    (2889939, 746969965, "scripts/watch_v24216_package_gate.py"),
)


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def seal(value: dict[str, Any], field: str) -> dict[str, Any]:
    value[field] = payload_sha256(value)
    return value


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=root, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
        timeout=20, check=True,
    ).stdout.strip()


def ordinary_tracked(root: Path, relative: Path) -> Path:
    path = root / relative
    tracked = subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(relative)], cwd=root,
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, timeout=20, check=False,
    ).returncode == 0
    if (
        relative.is_absolute() or ".." in relative.parts or path.is_symlink()
        or not path.is_file() or not path.resolve().is_relative_to(root.resolve())
        or not tracked
    ):
        raise RuntimeError(f"V2.49.73 expected tracked ordinary file: {relative}")
    return path


def proc_start_ticks(pid: int, proc_root: Path = Path("/proc")) -> int:
    text = (proc_root / str(pid) / "stat").read_text(encoding="utf-8")
    close = text.rfind(")")
    fields = text[close + 2 :].split() if close >= 0 else []
    if len(fields) < 20:
        raise RuntimeError("V2.49.73 process stat drifted")
    return int(fields[19])


def watcher_snapshot(proc_root: Path = Path("/proc")) -> list[dict[str, Any]]:
    output = []
    for pid, ticks, marker in PROTECTED_WATCHERS:
        if proc_start_ticks(pid, proc_root) != ticks:
            raise RuntimeError("V2.49.73 protected watcher drifted")
        command = (proc_root / str(pid) / "cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace")
        if marker not in command:
            raise RuntimeError("V2.49.73 protected watcher marker drifted")
        output.append({"pid": pid, "start_ticks": ticks, "marker": marker})
    return output


def task_vector() -> list[dict[str, str]]:
    projects = [project for project, _repository in TASKS]
    if len(TASKS) != TASK_COUNT or len(set(TASKS)) != TASK_COUNT or set(projects) & PRIOR_PROJECTS:
        raise RuntimeError("V2.49.73 fresh population drifted")
    output = []
    for project, repository in TASKS:
        opaque = "task_" + hashlib.sha256(f"v24973:{project}:{repository}".encode()).hexdigest()[:24]
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
    """Post-freeze evaluator authorities; never opened by the forward."""

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
            f"v24973-arm-order:{task_vector()[index]['opaque_id']}".encode()
        ).hexdigest(),
    )
    candidate_first = set(ranked[: TASK_COUNT // 2])
    return [
        [CANDIDATE_ARM, CONTROL_ARM] if index in candidate_first else [CONTROL_ARM, CANDIDATE_ARM]
        for index in range(TASK_COUNT)
    ]


def gates() -> dict[str, Any]:
    return {
        "mechanism": {
            "terminal_tasks": TASK_COUNT,
            "successful_shared_fetches": TASK_COUNT * FETCH_TARGETS_PER_TASK,
            "admitted_compact_records": TASK_COUNT,
            "unique_bound_fields": TASK_COUNT * 4,
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
        "runtime_boundary": ["opaque_id", "question", "same_forward_public_pages"],
        "same_exact_address_page_bytes_for_both_arms": True,
        "control_has_fixed_equal_namespace_raw_char_quota": True,
        "candidate_prefixes_compact_record_then_same_ordered_raw_evidence": True,
        "search_tool_or_github_api_used": False,
        "same_evidence_chars_prompt_model_output_cap_and_attempt_count": True,
        "only_treatment_is_identity_bound_compact_field_prefix": True,
        "short_exact_projection_space_padded_to_fixed_namespace_cap": True,
        "public_authority_pages_are_task_evidence_not_benchmark_metadata": True,
        "prediction_freeze_before_evaluator_metrics_or_quality_decision": True,
        "deepwidebench_manifest_mapping_gold_category_question_type_split_evaluator_score_reward_read_by_forward": False,
        "entropy_or_information_gain_assigns_credit": False,
        "public_exact220_or_sota_authorized": False,
    }


def dependency_manifest(root: Path, *, tracked: bool = True) -> dict[str, str]:
    output: dict[str, str] = {}
    for relative in LOCAL_SOURCES:
        path = ordinary_tracked(root, relative) if tracked else root / relative
        if (
            relative.is_absolute()
            or ".." in relative.parts
            or path.is_symlink()
            or not path.is_file()
            or not path.resolve().is_relative_to(root.resolve())
        ):
            raise RuntimeError(f"V2.49.73 expected ordinary file: {relative}")
        output[str(relative)] = sha256(path)
    return output


def build_protocol(root: Path, *, now: int) -> dict[str, Any]:
    if git(root, "status", "--porcelain") or git(root, "rev-parse", "HEAD") != git(root, "rev-parse", "target/main"):
        raise RuntimeError("V2.49.73 protocol requires clean pushed HEAD")
    future = (PROTOCOL, PREAUDIT, EXECUTION_START, FORWARD_RESULT, FORWARD_AUDIT, EVALUATOR_PROTOCOL, RESULT, POSTAUDIT, OUTPUT_ROOT)
    if any((root / path).exists() or (root / path).is_symlink() for path in future):
        raise FileExistsError("V2.49.73 future surface exists")
    manifest = dependency_manifest(root)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24973_identity_bound_field_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(now),
        "git_head": git(root, "rev-parse", "HEAD"),
        "build_audit_sha256": sha256(ordinary_tracked(root, BUILD_AUDIT)),
        "population": {
            "task_count": TASK_COUNT,
            "task_vector_sha256": payload_sha256(task_vector()),
            "endpoint_vector_sha256": payload_sha256(endpoint_vector()),
            "postfreeze_gold_endpoint_vector_sha256": payload_sha256(
                gold_endpoint_vector()
            ),
            "arm_order_vector_sha256": payload_sha256(arm_order_vector()),
            "fresh_against_v24966_v24968_model_and_evaluator_populations": True,
            "transport_layout_preflight_only_without_model_or_evaluator": True,
        },
        "execution": {
            "arms": list(ARMS),
            "only_treatment": "identity_bound_compact_field_prefix_under_same_total_cap",
            "executor_concurrency": EXECUTOR_CONCURRENCY,
            "model_concurrency": MODEL_CONCURRENCY,
            "model": MODEL,
            "model_endpoint": ENDPOINT,
            "evidence_chars_per_arm": EVIDENCE_CHARS,
            "namespace_evidence_chars": NAMESPACE_EVIDENCE_CHARS,
            "model_output_tokens": MODEL_OUTPUT_TOKENS,
            "task_deadline_seconds": TASK_DEADLINE_SECONDS,
            "fetch_targets_per_task": FETCH_TARGETS_PER_TASK,
            "exactly_one_model_attempt_per_arm": True,
            "unified_pair_failure_as_zero": True,
        },
        "gates": gates(),
        "protected_watchers": watcher_snapshot(),
        "dependency_manifest": manifest,
        "dependency_manifest_sha256": payload_sha256(manifest),
        "source_policy": source_policy(),
        "authorization": {
            "preactivation_audit_generation": True,
            "one_external_forward": False,
            "evaluator": False,
            "public_exact220_or_sota": False,
            "retry_resume_selective_rerun": False,
        },
    }
    return validate_protocol(root, seal(value, "protocol_payload_sha256"))


def validate_protocol(root: Path, value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    population = copied.get("population") or {}
    execution = copied.get("execution") or {}
    manifest = dependency_manifest(root)
    if (
        copied.get("role") != "v24973_identity_bound_field_preregistration"
        or copied.get("protocol_id") != PROTOCOL_ID
        or not sealed(copied, "protocol_payload_sha256")
        or copied.get("build_audit_sha256")
        != sha256(ordinary_tracked(root, BUILD_AUDIT))
        or population.get("task_count") != TASK_COUNT
        or population.get("task_vector_sha256") != payload_sha256(task_vector())
        or population.get("endpoint_vector_sha256") != payload_sha256(endpoint_vector())
        or population.get("postfreeze_gold_endpoint_vector_sha256")
        != payload_sha256(gold_endpoint_vector())
        or population.get("arm_order_vector_sha256") != payload_sha256(arm_order_vector())
        or execution.get("arms") != list(ARMS)
        or execution.get("executor_concurrency") != 20
        or execution.get("model_concurrency") != 8
        or execution.get("evidence_chars_per_arm") != EVIDENCE_CHARS
        or execution.get("namespace_evidence_chars") != NAMESPACE_EVIDENCE_CHARS
        or execution.get("fetch_targets_per_task") != 2
        or copied.get("gates") != gates()
        or copied.get("protected_watchers") != watcher_snapshot()
        or copied.get("dependency_manifest") != manifest
        or copied.get("dependency_manifest_sha256") != payload_sha256(manifest)
        or copied.get("source_policy") != source_policy()
        or copied.get("authorization", {}).get("public_exact220_or_sota") is not False
    ):
        raise RuntimeError("V2.49.73 protocol drifted")
    return copied


def build_protocol_untracked(root: Path, *, now: int) -> dict[str, Any]:
    """Construct the exact protocol during build tests, before force-add."""

    manifest = dependency_manifest(root, tracked=False)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24973_identity_bound_field_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(now),
        "git_head": "build-only",
        "build_audit_sha256": "build-only",
        "population": {
            "task_count": TASK_COUNT,
            "task_vector_sha256": payload_sha256(task_vector()),
            "endpoint_vector_sha256": payload_sha256(endpoint_vector()),
            "postfreeze_gold_endpoint_vector_sha256": payload_sha256(
                gold_endpoint_vector()
            ),
            "arm_order_vector_sha256": payload_sha256(arm_order_vector()),
            "fresh_against_v24966_v24968_model_and_evaluator_populations": True,
            "transport_layout_preflight_only_without_model_or_evaluator": True,
        },
        "execution": {
            "arms": list(ARMS),
            "only_treatment": "identity_bound_compact_field_prefix_under_same_total_cap",
            "executor_concurrency": EXECUTOR_CONCURRENCY,
            "model_concurrency": MODEL_CONCURRENCY,
            "model": MODEL,
            "model_endpoint": ENDPOINT,
            "evidence_chars_per_arm": EVIDENCE_CHARS,
            "namespace_evidence_chars": NAMESPACE_EVIDENCE_CHARS,
            "model_output_tokens": MODEL_OUTPUT_TOKENS,
            "task_deadline_seconds": TASK_DEADLINE_SECONDS,
            "fetch_targets_per_task": FETCH_TARGETS_PER_TASK,
            "exactly_one_model_attempt_per_arm": True,
            "unified_pair_failure_as_zero": True,
        },
        "gates": gates(),
        "protected_watchers": watcher_snapshot(),
        "dependency_manifest": manifest,
        "dependency_manifest_sha256": payload_sha256(manifest),
        "source_policy": source_policy(),
        "authorization": {
            "preactivation_audit_generation": True,
            "one_external_forward": False,
            "evaluator": False,
            "public_exact220_or_sota": False,
            "retry_resume_selective_rerun": False,
        },
    }
    return seal(value, "protocol_payload_sha256")


def validate_protocol_untracked(root: Path, value: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a build-only protocol without weakening production validation."""

    copied = copy.deepcopy(dict(value))
    population = copied.get("population") or {}
    execution = copied.get("execution") or {}
    manifest = dependency_manifest(root, tracked=False)
    if (
        copied.get("role") != "v24973_identity_bound_field_preregistration"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("git_head") != "build-only"
        or copied.get("build_audit_sha256") != "build-only"
        or not sealed(copied, "protocol_payload_sha256")
        or population.get("task_count") != TASK_COUNT
        or population.get("task_vector_sha256") != payload_sha256(task_vector())
        or population.get("endpoint_vector_sha256") != payload_sha256(endpoint_vector())
        or population.get("postfreeze_gold_endpoint_vector_sha256")
        != payload_sha256(gold_endpoint_vector())
        or population.get("arm_order_vector_sha256") != payload_sha256(arm_order_vector())
        or execution.get("arms") != list(ARMS)
        or execution.get("executor_concurrency") != EXECUTOR_CONCURRENCY
        or execution.get("model_concurrency") != MODEL_CONCURRENCY
        or execution.get("evidence_chars_per_arm") != EVIDENCE_CHARS
        or execution.get("namespace_evidence_chars") != NAMESPACE_EVIDENCE_CHARS
        or execution.get("fetch_targets_per_task") != FETCH_TARGETS_PER_TASK
        or copied.get("gates") != gates()
        or copied.get("protected_watchers") != watcher_snapshot()
        or copied.get("dependency_manifest") != manifest
        or copied.get("dependency_manifest_sha256") != payload_sha256(manifest)
        or copied.get("source_policy") != source_policy()
        or copied.get("authorization", {}).get("public_exact220_or_sota") is not False
    ):
        raise RuntimeError("V2.49.73 build-only protocol drifted")
    return copied


__all__ = [name for name in globals() if name.isupper()] + [
    "arm_order_vector", "build_protocol", "build_protocol_untracked", "dependency_manifest", "endpoint_vector",
    "gold_endpoint_vector",
    "gates", "git", "ordinary_tracked", "payload_sha256", "proc_start_ticks",
    "seal", "sealed", "sha256", "source_policy", "task_vector",
    "validate_protocol", "validate_protocol_untracked", "watcher_snapshot",
]
