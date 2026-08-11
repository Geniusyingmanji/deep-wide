"""Fixed-denominator external coverage gate for prefix-salient records."""

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
PROTOCOL_ID = "v25062_docsrs_prefix_salience_coverage_gate_v1"
BUILD_AUDIT = Path(f"results/v25062_prefix_salience_build_audit_v1_{DATE}.json")
PROTOCOL = Path(f"results/v25062_prefix_salience_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v25062_prefix_salience_preactivation_audit_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v25062_prefix_salience_execution_start_v1_{DATE}.json")
FORWARD_RESULT = Path(f"results/v25062_prefix_salience_forward_result_v1_{DATE}.json")
FORWARD_AUDIT = Path(f"results/v25062_prefix_salience_forward_audit_v1_{DATE}.json")
OUTPUT_ROOT = Path(f"outputs/v25062_prefix_salience_gate_v1_{DATE}")
TASK_ROWS = OUTPUT_ROOT / "content_free_task_receipts.jsonl"

SOURCE = Path("src/deepwide_agent/v25062_prefix_salient_atomic_record.py")
PURE_PARENT = Path(
    "src/deepwide_agent/v25061_pure_version_qualified_late_record.py"
)
HTML_SURFACE = Path("src/deepwide_agent/v25061_html_surface.py")
CONTRACT = Path("src/deepwide_agent/v25062_prefix_salience_gate_contract.py")
RUNNER = Path("scripts/run_v25062_prefix_salience_gate.py")
CONTROL = Path("scripts/control_v25062_prefix_salience_gate.py")
TEST = Path("tests/test_v25062_prefix_salience_gate.py")
PURE_TEST = Path("tests/test_v25062_prefix_salient_atomic_record.py")
FORWARD_SOURCES = (SOURCE, HTML_SURFACE, CONTRACT, RUNNER)

TASK_COUNT = 20
FETCH_WORKERS = 20
FETCH_CONNECT_TIMEOUT_SECONDS = 5.0
FETCH_READ_TIMEOUT_SECONDS = 20.0
MAX_RESPONSE_BYTES = 3_000_000
MINIMUM_FETCH_SUCCESSES = 18
MINIMUM_UNIQUE_IDENTITIES = 18
MINIMUM_PREFIX_COMPLETE_RECORDS = 8
MINIMUM_NATURAL_EXPOSURES = 8
FRESHNESS_PARENT_COMMIT = "e46c9d81d657e9e77f1bb036eae94135ee86f661"
CONSUMED_CRATES = (
    "serde", "tokio", "clap", "anyhow", "thiserror", "tracing", "axum",
    "rayon", "smallvec", "indexmap", "dashmap", "once_cell", "pin-project",
    "arc-swap", "crossbeam-channel", "crossbeam-queue", "moka", "owo-colors",
    "indicatif", "dialoguer", "comfy-table", "rust_decimal", "urlencoding",
)
EXPECTED_WATCHERS = (
    (795336, 713986317, "scripts/watch_v2415_r1_checkpoint_liveness.py"),
    (3061652, 747569004, "scripts/watch_v24218_exact220_executor.py"),
    (2808901, 746680268, "scripts/watch_v24215_joint_package_recovery.py"),
    (2889939, 746969965, "scripts/watch_v24216_package_gate.py"),
)
CRATES = (
    "bitflags",
    "parking_lot",
    "uuid",
    "semver",
    "env_logger",
    "compact_str",
    "const_format",
    "enumflags2",
    "fixedbitset",
    "lexical-core",
    "smol_str",
    "tinyvec",
    "unicode-segmentation",
    "unicode-width",
    "zerocopy",
    "zerovec",
    "bytestring",
    "globset",
    "jiff",
    "matchit",
)
COLUMNS = ("Crate", "License")
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
        raise RuntimeError("V2.50.62 expected ordinary repository file")
    if tracked and subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(relative)],
        cwd=root,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=20,
        check=False,
    ).returncode != 0:
        raise RuntimeError("V2.50.62 expected tracked repository file")
    return path


def watcher_snapshot(proc_root: Path = Path("/proc")) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for pid, expected_ticks, marker in EXPECTED_WATCHERS:
        stat = proc_root / str(pid) / "stat"
        cmdline = proc_root / str(pid) / "cmdline"
        if not stat.is_file() or not cmdline.is_file():
            raise RuntimeError("V2.50.62 protected watcher absent")
        raw = stat.read_text(encoding="utf-8")
        suffix = raw[raw.rfind(")") + 2 :].split()
        command = cmdline.read_bytes().replace(b"\0", b" ").decode(errors="replace")
        if (
            len(suffix) <= 19
            or int(suffix[19]) != expected_ticks
            or marker not in command
        ):
            raise RuntimeError("V2.50.62 protected watcher identity drifted")
        rows.append({"pid": pid, "start_ticks": expected_ticks, "marker": marker})
    return rows


def task_vector() -> list[dict[str, str]]:
    if (
        len(CRATES) != TASK_COUNT
        or len(set(CRATES)) != TASK_COUNT
        or set(CRATES) & set(CONSUMED_CRATES)
    ):
        raise RuntimeError("V2.50.62 crate vector drifted")
    question = (
        "Using only the supplied public crate detail page, identify the crate "
        "and return exactly one Markdown table and no prose. Include exactly "
        "one row. Columns must be: Crate | License. Preserve the page's "
        "canonical crate spelling and license value while collapsing "
        "whitespace. Use Unknown only when the supplied page does not "
        "establish a value."
    )
    return [
        {
            "opaque_id": "task_"
            + hashlib.sha256(f"v25062:{crate}".encode()).hexdigest()[:24],
            "question": question,
        }
        for crate in CRATES
    ]


def endpoint_vector() -> list[str]:
    return [f"https://docs.rs/crate/{crate}/latest" for crate in CRATES]


def source_policy() -> dict[str, Any]:
    return {
        "runtime_boundary": [
            "opaque_id",
            "shared_visible_question",
            "same_forward_public_html_page",
        ],
        "fresh_disjoint_twenty_task_failure_as_zero_denominator": True,
        "final_population_endpoints_not_opened_before_protocol_freeze": True,
        "one_http_fetch_attempt_per_task_no_retry_redirect_or_replacement": True,
        "candidate_only_reorders_prefix_complete_atomic_record": True,
        "absolute_late_information_recovery_disabled": True,
        "identity_complete_record_and_candidate_change_reported_separately": True,
        "no_page_question_url_identity_value_or_prediction_persisted": True,
        "no_model_search_evaluator_or_benchmark_call": True,
        "mapping_gold_category_question_type_split_score_reward_read": False,
        "entropy_or_information_gain_assigns_credit_or_routes": False,
        "deepwidebench_dev64_exact220_leaderboard_or_sota_authorized": False,
    }


def gates() -> dict[str, Any]:
    return {
        "fixed_denominator": TASK_COUNT,
        "fetch_attempts": TASK_COUNT,
        "minimum_fetch_successes": MINIMUM_FETCH_SUCCESSES,
        "minimum_unique_identity_pages": MINIMUM_UNIQUE_IDENTITIES,
        "minimum_prefix_complete_record_pages": MINIMUM_PREFIX_COMPLETE_RECORDS,
        "minimum_natural_mechanism_exposures": MINIMUM_NATURAL_EXPOSURES,
        "every_exposure_is_prefix_complete_and_has_zero_late_targets": True,
        "projection_failures": 0,
        "compact_capacity_failures": 0,
        "positive_signed_credit_count": 0,
    }


def _module_candidates(relative: Path, node: ast.AST) -> list[Path]:
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
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            for candidate in _module_candidates(relative, node):
                if (root / candidate).is_file() and not (root / candidate).is_symlink():
                    pending.append(candidate)
    return tuple(sorted(observed, key=str))


def dependency_manifest(root: Path, *, tracked: bool) -> dict[str, str]:
    relatives = {
        *forward_dependency_closure(root),
        CONTROL,
        TEST,
        PURE_TEST,
    }
    output: dict[str, str] = {}
    for relative in sorted(relatives, key=str):
        path = ordinary(root, relative, tracked=tracked)
        if SECRET.search(path.read_text(encoding="utf-8")):
            raise RuntimeError("V2.50.62 credential literal in source manifest")
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
        OUTPUT_ROOT,
    )
    if require_pristine and any(
        (root / path).exists() or (root / path).is_symlink() for path in future
    ):
        raise RuntimeError("V2.50.62 future surface is not pristine")
    manifest = dependency_manifest(root, tracked=tracked)
    value = {
        "artifact_version": 1,
        "role": "v25062_prefix_salience_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(now),
        "build_audit_sha256": build_audit_sha256,
        "freshness": {
            "parent_commit": FRESHNESS_PARENT_COMMIT,
            "parent_history_literal_zero_hit_crates": list(CRATES),
            "consumed_crates": list(CONSUMED_CRATES),
            "endpoint_page_value_model_or_evaluator_opened_during_selection": False,
        },
        "population": {
            "task_count": TASK_COUNT,
            "crate_vector_sha256": payload_sha256(CRATES),
            "task_vector_sha256": payload_sha256(task_vector()),
            "endpoint_vector_sha256": payload_sha256(endpoint_vector()),
        },
        "execution": {
            "fetch_workers": FETCH_WORKERS,
            "fetch_attempts_per_task": 1,
            "fetch_connect_timeout_seconds": FETCH_CONNECT_TIMEOUT_SECONDS,
            "fetch_read_timeout_seconds": FETCH_READ_TIMEOUT_SECONDS,
            "maximum_response_bytes": MAX_RESPONSE_BYTES,
            "model_calls": 0,
            "search_calls": 0,
            "evaluator_calls": 0,
            "only_candidate": "v25062_prefix_salient_atomic_record",
        },
        "gates": gates(),
        "protected_watchers": watcher_snapshot(),
        "source_manifest": manifest,
        "source_manifest_sha256": payload_sha256(manifest),
        "source_policy": source_policy(),
        "authorization": {
            "one_fixed_denominator_external_coverage_forward_after_clean_pushed_start": True,
            "fresh_disjoint_paired_quality_gate_design_only_after_coverage_go": True,
            "model_or_evaluator_on_this_population": False,
            "deepwidebench_dev64_exact220_or_sota": False,
            "retry_resume_population_replacement_or_selective_revaluation": False,
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
        raise RuntimeError("V2.50.62 protocol drifted")
    return copied


__all__ = [name for name in globals() if name.isupper()] + [
    "build_protocol",
    "dependency_manifest",
    "endpoint_vector",
    "forward_dependency_closure",
    "gates",
    "git",
    "ordinary",
    "payload_sha256",
    "seal",
    "sealed",
    "sha256",
    "source_policy",
    "task_vector",
    "validate_protocol",
    "watcher_snapshot",
]
