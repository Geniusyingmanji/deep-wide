"""Neutral 20-way reliability contract for mapping-recovery bundles."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


DATE = "20260808"
PROTOCOL_ID = "v24883_neutral_mapping_recovery_reliability_gate_v1"
PROTOCOL = Path(
    f"results/v24883_mapping_recovery_reliability_preregistration_v1_{DATE}.json"
)
PREAUDIT = Path(
    f"results/v24883_mapping_recovery_reliability_preactivation_audit_v1_{DATE}.json"
)
EXECUTION_START = Path(
    f"results/v24883_mapping_recovery_reliability_execution_start_v1_{DATE}.json"
)
RESULT = Path(
    f"results/v24883_mapping_recovery_reliability_result_v1_{DATE}.json"
)
OUTPUT_ROOT = Path(f"outputs/v24883_mapping_recovery_reliability_v1_{DATE}")
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
TASK_ROOT = OUTPUT_ROOT / "tasks"
LEASE_PATH = Path("outputs/deepwide_benchmark_api.lease.lock")
RUNNER_MARKER = "scripts/run_v24883_mapping_recovery_reliability_gate.py"
CHILD_MARKER = "scripts/run_v24883_mapping_recovery_reliability_task.py"
LEASE_OWNER = "v24883_neutral_mapping_recovery_reliability_v1"
LEASE_PURPOSE = "neutral_twenty_way_mapping_recovery_bundle_reliability"

TASK_COUNT = 20
EXECUTOR_CONCURRENCY = 20
MODEL_SLOT_CAP = 8
MINIMUM_VALID_BUNDLES = 19
MAXIMUM_HARD_TIMEOUTS = 0
TASK_WALL_SECONDS = 240
PARENT_GRACE_SECONDS = 30
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
MODEL = {
    "proxy_url": "http://127.0.0.1:9878/responses",
    "name": "gpt-5.6-sol",
    "reasoning_effort": "low",
    "service_tier": "priority",
    "timeout_seconds": 65,
    "max_retries": 2,
}
SEARCH = {
    "proxy_url": MODEL["proxy_url"],
    "model": MODEL["name"],
    "batch_size": 8,
    "workers": 1,
    "context_size": "medium",
    "max_output_tokens": 7_000,
    "timeout_seconds": 65,
    "max_retries": 2,
    "fetch_workers": 8,
    "fetch_timeout_seconds": 20,
    "hard_fetch_deadline_seconds": 25,
}
PRODUCTS = (
    "Python packaging",
    "Git",
    "CMake",
    "Docker Engine",
    "Terraform",
    "Redis",
    "NGINX",
    "Pandas",
    "NumPy",
    "Django",
    "Flask",
    "FastAPI",
    "PyTorch",
    "TensorFlow",
    "Apache Spark",
    "Apache Kafka",
    "Prometheus",
    "Grafana",
    "OpenSSL",
    "curl",
)
PROTECTED_WATCHERS = (
    (795336, "scripts/watch_v2415_r1_checkpoint_liveness.py"),
    (3061652, "scripts/watch_v24218_exact220_executor.py"),
    (2808901, "scripts/watch_v24215_joint_package_recovery.py"),
    (2889939, "scripts/watch_v24216_package_gate.py"),
)
SOURCE = Path(
    "src/deepwide_agent/v24883_mapping_recovery_reliability_contract.py"
)
CONTROL = Path("scripts/control_v24883_mapping_recovery_reliability_gate.py")
RUNNER = Path(RUNNER_MARKER)
CHILD = Path(CHILD_MARKER)
TEST = Path("tests/test_v24883_mapping_recovery_reliability_gate.py")
RUNTIME_SOURCES = (
    Path("src/deepwide_agent/v24873_keyless_fixed_coverage_runtime.py"),
    Path("src/deepwide_agent/v24879_mapping_recovery_effect_bundle.py"),
    Path("src/deepwide_agent/v24882_mapping_recovery_stage_runtime.py"),
    Path("src/deepwide_agent/v24881_mapping_recovery_subprocess_gate.py"),
    CHILD,
    RUNNER,
)
TEST_SUITES = (
    (Path("tests/test_v24879_mapping_recovery_effect_bundle.py"), 15),
    (Path("tests/test_v24880_mapping_recovery_child_runtime.py"), 2),
    (Path("tests/test_v24881_mapping_recovery_subprocess_gate.py"), 2),
    (Path("tests/test_v24882_mapping_recovery_stage_runtime.py"), 10),
    (TEST, 8),
)
EXPECTED_TESTS = 37
SOURCES = tuple(
    dict.fromkeys(
        (
            SOURCE,
            CONTROL,
            RUNNER,
            CHILD,
            TEST,
            *RUNTIME_SOURCES,
            *(path for path, _expected in TEST_SUITES),
            Path("src/deepwide_agent/v24874_keyless_coverage_bundle.py"),
            Path("src/deepwide_agent/v24875_keyless_coverage_child_runtime.py"),
            Path("src/deepwide_agent/v24876_keyless_coverage_subprocess_gate.py"),
            Path("src/deepwide_agent/v24630_thin_backfill_search.py"),
            Path("src/deepwide_agent/v24312_deadline_reliability.py"),
            Path("src/deepwide_agent/v24468_total_wall_transport.py"),
            Path("scripts/deepwide_api_lease.py"),
        )
    )
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


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
        check=True,
    ).stdout.strip()


def ordinary_tracked(root: Path, relative: Path) -> Path:
    path = root / relative
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(root.resolve())
        or subprocess.run(
            ["git", "ls-files", "--error-unmatch", str(relative)],
            cwd=root,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=20,
            check=False,
        ).returncode
        != 0
    ):
        raise RuntimeError(f"V2.48.83 expected tracked source: {relative}")
    return path


def source_manifest(root: Path) -> dict[str, str]:
    return {
        str(relative): sha256(ordinary_tracked(root, relative))
        for relative in sorted(SOURCES, key=str)
    }


def task_vector() -> list[dict[str, str]]:
    tasks = [
        {
            "opaque_id": f"task_{index:024x}",
            "question": (
                f"Using official documentation, list the principal documentation "
                f"sections for {product}. Return a Markdown table with columns: "
                "Section, Official documentation URL."
            ),
        }
        for index, product in enumerate(PRODUCTS, start=1)
    ]
    if len(tasks) != TASK_COUNT or any(
        set(task) != {"opaque_id", "question"} for task in tasks
    ):
        raise RuntimeError("V2.48.83 neutral task vector drifted")
    return tasks


def protected_watcher_snapshot(
    proc_root: Path = Path("/proc"),
) -> list[dict[str, Any]]:
    output = []
    for pid, marker in PROTECTED_WATCHERS:
        stat = proc_root / str(pid) / "stat"
        cmdline = proc_root / str(pid) / "cmdline"
        if not stat.is_file() or not cmdline.is_file():
            raise RuntimeError("V2.48.83 protected watcher is absent")
        raw = stat.read_text(encoding="utf-8")
        suffix = raw[raw.rfind(")") + 2 :].split()
        command = cmdline.read_bytes().replace(b"\x00", b" ").decode(errors="replace")
        if len(suffix) <= 19 or marker not in command:
            raise RuntimeError("V2.48.83 protected watcher identity drifted")
        output.append(
            {"pid": pid, "marker": marker, "start_ticks": int(suffix[19])}
        )
    return output


__all__ = [name for name in globals() if name.isupper()] + [
    "git",
    "ordinary_tracked",
    "payload_sha256",
    "protected_watcher_snapshot",
    "sha256",
    "source_manifest",
    "task_vector",
]
