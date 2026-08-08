"""Benchmark-external reliability contract for the parser-total seam."""

from __future__ import annotations

from pathlib import Path

from . import v24893_revision_envelope_reliability_contract as parent


DATE = "20260808"
PROTOCOL_ID = "v24904_neutral_revision_parser_total_reliability_gate_v1"
PROTOCOL = Path(f"results/v24904_revision_parser_total_reliability_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v24904_revision_parser_total_reliability_preactivation_audit_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v24904_revision_parser_total_reliability_execution_start_v1_{DATE}.json")
RESULT = Path(f"results/v24904_revision_parser_total_reliability_result_v1_{DATE}.json")
POSTAUDIT = Path(f"results/v24904_revision_parser_total_reliability_postresult_audit_v1_{DATE}.json")
OUTPUT_ROOT = Path(f"outputs/v24904_revision_parser_total_reliability_v1_{DATE}")
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
TASK_ROOT = OUTPUT_ROOT / "tasks"
LEASE_PATH = parent.LEASE_PATH
RUNNER_MARKER = "scripts/run_v24904_revision_parser_total_reliability_gate.py"
CHILD_MARKER = "scripts/run_v24904_revision_parser_total_reliability_task.py"
LEASE_OWNER = "v24904_neutral_revision_parser_total_reliability_v1"
LEASE_PURPOSE = "neutral_twenty_way_revision_parser_total_bundle_reliability"

TASK_COUNT = parent.TASK_COUNT
EXECUTOR_CONCURRENCY = parent.EXECUTOR_CONCURRENCY
MODEL_SLOT_CAP = parent.MODEL_SLOT_CAP
MINIMUM_VALID_BUNDLES = 19
MAXIMUM_HARD_TIMEOUTS = parent.MAXIMUM_HARD_TIMEOUTS
TASK_WALL_SECONDS = parent.TASK_WALL_SECONDS
PARENT_GRACE_SECONDS = parent.PARENT_GRACE_SECONDS
LIMITS = dict(parent.LIMITS)
MODEL = dict(parent.MODEL)
SEARCH = dict(parent.SEARCH)
PROTECTED_WATCHERS = parent.PROTECTED_WATCHERS

SOURCE = Path("src/deepwide_agent/v24904_revision_parser_total_reliability_contract.py")
CONTROL = Path("scripts/control_v24904_revision_parser_total_reliability_gate.py")
RUNNER = Path(RUNNER_MARKER)
CHILD = Path(CHILD_MARKER)
AUDITOR = Path("scripts/audit_v24904_revision_parser_total_reliability_result.py")
TEST = Path("tests/test_v24904_revision_parser_total_reliability_gate.py")
RUNTIME_SOURCES = tuple(
    Path(f"src/deepwide_agent/v{version}_{name}.py")
    for version, name in (
        ("24897", "revision_parser_totality"),
        ("24898", "revision_parser_total_integration"),
        ("24899", "revision_parser_total_exact_task"),
        ("24900", "revision_parser_total_runtime"),
        ("24901", "revision_parser_total_mapping_bundle"),
        ("24902", "revision_parser_total_child_runtime"),
        ("24903", "revision_parser_total_subprocess_gate"),
    )
) + (
    CHILD, RUNNER,
    Path("scripts/run_v24883_mapping_recovery_reliability_task.py"),
    Path("scripts/run_v24883_mapping_recovery_reliability_gate.py"),
)
TEST_SUITES = (
    (Path("tests/test_v24897_revision_parser_totality.py"), 4),
    (Path("tests/test_v24898_revision_parser_total_integration.py"), 2),
    (Path("tests/test_v24903_revision_parser_total_production_seam.py"), 5),
    (TEST, 9),
)
EXPECTED_TESTS = sum(expected for _path, expected in TEST_SUITES)
SOURCES = tuple(
    dict.fromkeys(
        (
            SOURCE, CONTROL, RUNNER, CHILD, AUDITOR, TEST,
            *RUNTIME_SOURCES,
            *(path for path, _expected in TEST_SUITES),
            Path("src/deepwide_agent/v24859_full_evidence_coverage_revision.py"),
            Path("src/deepwide_agent/v24860_coverage_revision_integration.py"),
            Path("src/deepwide_agent/v24861_coverage_revision_exact_task.py"),
            Path("src/deepwide_agent/v24873_keyless_fixed_coverage_runtime.py"),
            Path("src/deepwide_agent/v24879_mapping_recovery_effect_bundle.py"),
            Path("src/deepwide_agent/v24882_mapping_recovery_stage_runtime.py"),
            Path("scripts/deepwide_api_lease.py"),
            Path("scripts/control_v24883_mapping_recovery_reliability_gate.py"),
            Path("scripts/audit_v24883_mapping_recovery_reliability_result.py"),
        )
    )
)

payload_sha256 = parent.payload_sha256
sha256 = parent.sha256
git = parent.git
ordinary_tracked = parent.ordinary_tracked
protected_watcher_snapshot = parent.protected_watcher_snapshot


def source_manifest(root: Path) -> dict[str, str]:
    return {
        str(relative): sha256(ordinary_tracked(root, relative))
        for relative in sorted(SOURCES, key=str)
    }


def task_vector() -> list[dict[str, str]]:
    variants = (
        (1, False, "Name, Code, Note"),
        (1, True, "Name, Code, Note"),
        (512, False, "Name, Date"),
        (513, False, "Name, Date"),
        (700, False, "Name, Date"),
    )
    tasks: list[dict[str, str]] = []
    for repeat in range(4):
        for rows, fullwidth, columns in variants:
            if fullwidth:
                request = (
                    "Return exactly one Markdown table with columns Name, Code, Note "
                    "and one data row. The row must be Alpha, left｜right, Stable; "
                    "the character between left and right must remain the fullwidth "
                    "vertical line U+FF5C, not an ASCII delimiter."
                )
            else:
                request = (
                    f"Return exactly {rows} data rows in one Markdown table with "
                    f"columns {columns}. Names must be R0001 through R{rows:04d}; "
                    "every other cell must be 2000-01-01. Do not omit, merge, "
                    "summarize, or add rows."
                )
            index = len(tasks) + 1
            tasks.append(
                {
                    "opaque_id": f"task_{index:024x}",
                    "question": f"Synthetic reliability replicate {repeat + 1}. {request}",
                }
            )
    if len(tasks) != TASK_COUNT or any(
        set(task) != {"opaque_id", "question"} for task in tasks
    ):
        raise RuntimeError("V2.49.04 neutral vector drifted")
    return tasks


__all__ = [name for name in globals() if name.isupper()] + [
    "git", "ordinary_tracked", "payload_sha256", "protected_watcher_snapshot",
    "sha256", "source_manifest", "task_vector",
]
