"""Frozen contract for the V2.49.23 target--value shared-prefix gate.

The confirmatory targets are fixed before their responses are read.  Forward
runtime receives only a visible ``opaque_id``/``question`` task and the same
four frozen public pages for both arms.  Benchmark labels, DeepWideBench
mapping/gold/evaluator data, and prior per-task outcomes are outside the
runtime boundary.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


DATE = "20260808"
PROTOCOL_ID = "v24923_fresh_target_value_shared_prefix_v1"
HISTORICAL_BOUNDARY_COMMIT = "c202820abefe2abb9759e79ad0def6e384abe8e9"
SELECTION_SEED = "v24923-confirmatory-complete-country-rank-v1"
SELECTED_COUNT = 12
ROWS_PER_TASK = 12
SELECTED_ENTITY_COUNT = SELECTED_COUNT * ROWS_PER_TASK
ARMS = ("parent_30k", "target_value_30k")

# These were read only by an unpersisted development reachability probe.  They
# are permanently excluded from the confirmatory population.
DEVELOPMENT_TARGET_KEYS = (
    "SE.SEC.ENRR@2023",
    "SH.IMM.MEAS@2023",
    "SP.DYN.TFRT.IN@2023",
    "NY.GNP.PCAP.CD@2023",
)

# Fixed before any response for these target/year pairs is read.
TARGETS = (
    {
        "label": "School enrollment, primary (% gross)",
        "indicator": "SE.PRM.ENRR",
        "year": "2023",
    },
    {
        "label": "Mortality rate, under-5 (per 1,000 live births)",
        "indicator": "SH.DYN.MORT",
        "year": "2023",
    },
    {
        "label": "Population growth (annual %)",
        "indicator": "SP.POP.GROW",
        "year": "2023",
    },
    {
        "label": "GDP (current US$)",
        "indicator": "NY.GDP.MKTP.CD",
        "year": "2023",
    },
)
TARGET_KEYS = tuple(
    f"{target['indicator']}@{target['year']}" for target in TARGETS
)
CATALOG_URL = "https://api.worldbank.org/v2/country?format=json&per_page=400"
TARGET_URLS = tuple(
    "https://api.worldbank.org/v2/country/all/indicator/"
    + target["indicator"]
    + "?date="
    + target["year"]
    + "&format=json&per_page=400"
    for target in TARGETS
)

MODEL = {
    "proxy_url": "http://127.0.0.1:9878/responses",
    "name": "gpt-5.6-sol",
    "reasoning_effort": "low",
    "service_tier": "priority",
    "timeout_seconds": 90,
    "max_output_tokens": 8_000,
    "attempts_per_arm": 1,
}
MODEL_SLOT_CAP = 8
EXECUTOR_CONCURRENCY = 12
TASK_WALL_SECONDS = 210
FETCH_TIMEOUT_SECONDS = 60
FETCH_MAX_BYTES = 2 * 1024 * 1024
LEASE_PATH = Path("outputs/deepwide_api_effect.lock")
PROTECTED_WATCHERS = (
    (795336, "scripts/watch_v2415_r1_checkpoint_liveness.py"),
    (3061652, "scripts/watch_v24218_exact220_executor.py"),
    (2808901, "scripts/watch_v24215_joint_package_recovery.py"),
    (2889939, "scripts/watch_v24216_package_gate.py"),
)

BUILD_AUDIT = Path(f"results/v24923_target_value_external_build_audit_v1_{DATE}.json")
PROTOCOL = Path(f"results/v24923_target_value_external_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v24923_target_value_external_preactivation_audit_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v24923_target_value_external_execution_start_v1_{DATE}.json")
FORWARD_RESULT = Path(f"results/v24923_target_value_external_forward_result_v1_{DATE}.json")
FORWARD_AUDIT = Path(f"results/v24923_target_value_external_forward_audit_v1_{DATE}.json")
EVALUATOR_PROTOCOL = Path(f"results/v24923_target_value_external_evaluator_preregistration_v1_{DATE}.json")
RESULT = Path(f"results/v24923_target_value_external_result_v1_{DATE}.json")
POSTAUDIT = Path(f"results/v24923_target_value_external_postresult_audit_v1_{DATE}.json")

OUTPUT_ROOT = Path(f"outputs/v24923_target_value_external_v1_{DATE}")
SNAPSHOT_ROOT = OUTPUT_ROOT / "snapshot"
CATALOG_RESPONSE = SNAPSHOT_ROOT / "country_catalog.bin"
TARGET_RESPONSE_ROOT = SNAPSHOT_ROOT / "target_responses"
FROZEN_PAGES = SNAPSHOT_ROOT / "frozen_pages.json"
SNAPSHOT_FREEZE = SNAPSHOT_ROOT / "snapshot_freeze.json"
VISIBLE_TASKS = OUTPUT_ROOT / "visible_tasks.jsonl"
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
TASK_ROOT = OUTPUT_ROOT / "tasks"
PREDICTIONS = OUTPUT_ROOT / "frozen_predictions.jsonl"
PROJECTIONS = OUTPUT_ROOT / "frozen_projections.jsonl"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
RUN_SUMMARY = OUTPUT_ROOT / "run_summary.json"
SAFE_PROGRESS = OUTPUT_ROOT / "safe_forward_progress.json"

CONTROL = Path("scripts/control_v24923_target_value_external.py")
RUNNER = Path("scripts/run_v24923_target_value_external.py")
CHILD = Path("scripts/run_v24923_target_value_external_task.py")
EVALUATOR = Path("scripts/evaluate_v24923_target_value_external.py")
TEST = Path("tests/test_v24923_target_value_external.py")
RUNTIME_SOURCES = (
    Path("src/deepwide_agent/v24923_target_value_external_contract.py"),
    Path("src/deepwide_agent/v24921_target_value_coverage_projector.py"),
    Path("src/deepwide_agent/v24846_atomic_table_header_30k_profile.py"),
    Path("src/deepwide_agent/v24842_atomic_table_header_closure.py"),
    Path("src/deepwide_agent/v24839_structure_preserving_projector.py"),
    RUNNER,
    CHILD,
    Path("scripts/deepwide_api_lease.py"),
)
BUILD_SOURCES = (*RUNTIME_SOURCES, CONTROL, EVALUATOR, TEST)

COUNTRY_BLOCK = re.compile(r"<COUNTRIES>\s*(.*?)\s*</COUNTRIES>", re.S)
COUNTRY_LINE = re.compile(r"^\s*\d+\.\s*(.*?)\s*\[([A-Z]{3})\]\s*$")


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def visible_columns() -> list[str]:
    return [
        "Country",
        *(
            f"{target['label']} [{target['indicator']}] @{target['year']}"
            for target in TARGETS
        ),
    ]


def parse_visible_countries(question: str) -> list[tuple[str, str]]:
    if not isinstance(question, str):
        raise ValueError("V2.49.23 visible question is absent")
    match = COUNTRY_BLOCK.search(question)
    if match is None:
        raise ValueError("V2.49.23 visible country block is absent")
    output: list[tuple[str, str]] = []
    for line in match.group(1).splitlines():
        parsed = COUNTRY_LINE.match(line)
        if parsed is not None:
            output.append((parsed.group(1).strip(), parsed.group(2)))
    if (
        len(output) != ROWS_PER_TASK
        or len({iso3 for _name, iso3 in output}) != ROWS_PER_TASK
    ):
        raise ValueError("V2.49.23 visible country vector drifted")
    return output


def validate_task_vector(
    tasks: Sequence[Mapping[str, Any]],
) -> list[dict[str, str]]:
    if isinstance(tasks, (str, bytes)) or len(tasks) != SELECTED_COUNT:
        raise ValueError("V2.49.23 task denominator drifted")
    expected_columns = visible_columns()
    output: list[dict[str, str]] = []
    seen: set[str] = set()
    seen_entities: set[str] = set()
    for item in tasks:
        if not isinstance(item, Mapping) or set(item) != {"opaque_id", "question"}:
            raise ValueError("V2.49.23 runtime input must be opaque_id and question")
        opaque = item.get("opaque_id")
        question = item.get("question")
        if (
            not isinstance(opaque, str)
            or not opaque.startswith("task_")
            or len(opaque) != 29
            or opaque in seen
            or not isinstance(question, str)
            or not all(column in question for column in expected_columns)
        ):
            raise ValueError("V2.49.23 visible task binding drifted")
        countries = parse_visible_countries(question)
        if any(iso3 in seen_entities for _name, iso3 in countries):
            raise ValueError("V2.49.23 task entities are not disjoint")
        seen.add(opaque)
        seen_entities.update(iso3 for _name, iso3 in countries)
        output.append({"opaque_id": opaque, "question": question})
    if len(seen_entities) != SELECTED_ENTITY_COUNT:
        raise ValueError("V2.49.23 selected entity denominator drifted")
    return output


def protected_watcher_snapshot(
    proc_root: Path = Path("/proc"),
) -> list[dict[str, Any]]:
    output = []
    for pid, marker in PROTECTED_WATCHERS:
        stat = proc_root / str(pid) / "stat"
        cmdline = proc_root / str(pid) / "cmdline"
        if not stat.is_file() or not cmdline.is_file():
            raise RuntimeError("V2.49.23 protected watcher absent")
        raw = stat.read_text(encoding="utf-8")
        suffix = raw[raw.rfind(")") + 2 :].split()
        command = cmdline.read_bytes().replace(b"\0", b" ").decode(errors="replace")
        if len(suffix) <= 19 or marker not in command:
            raise RuntimeError("V2.49.23 protected watcher identity drifted")
        output.append({"pid": pid, "marker": marker, "start_ticks": int(suffix[19])})
    return output


__all__ = [name for name in globals() if name.isupper()] + [
    "parse_visible_countries",
    "payload_sha256",
    "protected_watcher_snapshot",
    "sealed",
    "sha256",
    "validate_task_vector",
    "visible_columns",
]
