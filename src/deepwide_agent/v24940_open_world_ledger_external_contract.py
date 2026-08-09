"""Fresh matched-cost external gate for the V2.49.39 open-world ledger.

One World Bank indicator/year is fixed before its response is read and is
absent from the historical repository boundary.  A frozen, deterministic
public-data transform creates 240 disjoint records in 24 task pages.  Each
task exposes only an output schema and a visible cohort predicate; it does not
enumerate the ten qualifying row identities.  Both arms receive byte-identical
pages and one counterbalanced GPT-5.6 call.  The only treatment is replacing
the V2.49.33 projector with the V2.49.39 schema-bound record ledger.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


DATE = "20260809"
PROTOCOL_ID = "v24940_fresh_open_world_schema_bound_ledger_external_v1"
HISTORICAL_BOUNDARY_COMMIT = "53c668df"
SELECTION_SEED = "v24940-open-world-ledger-record-rank-v1"
COHORT_SEED = "v24940-visible-cohort-assignment-v1"
SELECTED_COUNT = 24
ROWS_PER_TASK = 8
DISTRACTOR_ROWS_PER_TASK = 8
PAGE_ROWS_PER_TASK = ROWS_PER_TASK + DISTRACTOR_ROWS_PER_TASK
SELECTED_ENTITY_COUNT = SELECTED_COUNT * ROWS_PER_TASK
# Target identities are disjoint across tasks; one fixed eight-record
# distractor pool is shared to keep the required public-source capacity below
# the number of real economies with non-null values.
SELECTED_RECORD_COUNT = SELECTED_ENTITY_COUNT + DISTRACTOR_ROWS_PER_TASK
ARMS = ("parent_30k", "target_value_30k")

DEVELOPMENT_TARGET_KEYS = (
    "AG.SRF.TOTL.K2@2022",
    "EG.ELC.ACCS.ZS@2022",
    "EN.POP.DNST@2022",
    "IT.CEL.SETS.P2@2022",
    "IT.NET.USER.ZS@2022",
    "NY.GDP.MKTP.CD@2023",
    "NY.GDP.PCAP.CD@2022",
    "NY.GDP.PCAP.CD@2023",
    "NY.GNP.PCAP.CD@2023",
    "SE.PRM.ENRR@2023",
    "SE.SEC.ENRR@2023",
    "SH.DYN.MORT@2023",
    "SH.H2O.BASW.ZS@2022",
    "SH.IMM.MEAS@2023",
    "SH.STA.BASS.ZS@2022",
    "SL.UEM.TOTL.ZS@2023",
    "SP.DYN.LE00.IN@2022",
    "SP.DYN.TFRT.IN@2023",
    "SP.POP.0014.TO.ZS@2023",
    "SP.POP.1564.TO.ZS@2023",
    "SP.POP.65UP.TO.ZS@2023",
    "SP.POP.DPND@2023",
    "SP.POP.GROW@2023",
    "SP.POP.TOTL.FE.IN@2023",
    "SP.POP.TOTL.FE.ZS@2023",
    "SP.POP.TOTL.MA.IN@2023",
    "SP.POP.TOTL.MA.ZS@2023",
    "SP.POP.TOTL@2022",
    "SP.POP.TOTL@2023",
    "SP.RUR.TOTL.ZS@2022",
    "SP.URB.TOTL.IN.ZS@2023",
    "TG.VAL.TOTL.GD.ZS@2023",
)
TARGETS = (
    {
        "label": "Infant mortality rate per thousand live births",
        "indicator": "SP.DYN.IMRT.IN",
        "year": "2022",
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
EXECUTOR_CONCURRENCY = 20
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

BUILD_AUDIT = Path(
    f"results/v24940_open_world_ledger_external_build_audit_v1_{DATE}.json"
)
PROTOCOL = Path(
    f"results/v24940_open_world_ledger_external_preregistration_v1_{DATE}.json"
)
PREAUDIT = Path(
    f"results/v24940_open_world_ledger_external_preactivation_audit_v1_{DATE}.json"
)
EXECUTION_START = Path(
    f"results/v24940_open_world_ledger_external_execution_start_v1_{DATE}.json"
)
FORWARD_RESULT = Path(
    f"results/v24940_open_world_ledger_external_forward_result_v1_{DATE}.json"
)
FORWARD_AUDIT = Path(
    f"results/v24940_open_world_ledger_external_forward_audit_v1_{DATE}.json"
)
EVALUATOR_PROTOCOL = Path(
    f"results/v24940_open_world_ledger_external_evaluator_preregistration_v1_{DATE}.json"
)
RESULT = Path(
    f"results/v24940_open_world_ledger_external_result_v1_{DATE}.json"
)
POSTAUDIT = Path(
    f"results/v24940_open_world_ledger_external_postresult_audit_v1_{DATE}.json"
)

OUTPUT_ROOT = Path(f"outputs/v24940_open_world_ledger_external_v1_{DATE}")
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

CONTROL = Path("scripts/control_v24940_open_world_ledger_external.py")
RUNNER = Path("scripts/run_v24940_open_world_ledger_external.py")
CHILD = Path("scripts/run_v24940_open_world_ledger_external_task.py")
EVALUATOR = Path("scripts/evaluate_v24940_open_world_ledger_external.py")
TEST = Path("tests/test_v24940_open_world_ledger_external.py")
CANDIDATE_AUDIT = Path(
    f"results/v24940_schema_bound_record_ledger_build_audit_v1_{DATE}.json"
)
RUNTIME_SOURCES = (
    Path("src/deepwide_agent/v24940_open_world_ledger_external_contract.py"),
    Path("src/deepwide_agent/v24939_schema_bound_record_ledger.py"),
    Path("src/deepwide_agent/v24933_contextual_record_value_projector.py"),
    Path("src/deepwide_agent/v24928_unicode_total_visible_row_compactor.py"),
    Path("src/deepwide_agent/v24921_target_value_coverage_projector.py"),
    Path("src/deepwide_agent/v24842_atomic_table_header_closure.py"),
    Path("src/deepwide_agent/v24839_structure_preserving_projector.py"),
    RUNNER,
    CHILD,
    Path("scripts/run_v24923_target_value_external.py"),
    Path("scripts/run_v24923_target_value_external_task.py"),
    Path("scripts/deepwide_api_lease.py"),
)
BUILD_SOURCES = (
    *RUNTIME_SOURCES,
    CONTROL,
    EVALUATOR,
    Path("scripts/control_v24923_target_value_external.py"),
    Path("scripts/evaluate_v24923_target_value_external.py"),
    TEST,
    CANDIDATE_AUDIT,
)

COHORT_PATTERN = re.compile(r"\bC([0-9A-F]{2})\b")


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


def sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def visible_columns() -> list[str]:
    target = TARGETS[0]
    return [
        "Country",
        "Cohort",
        "ISO3",
        f"{target['label']} [{target['indicator']}] @{target['year']}",
    ]


def parse_visible_cohort(question: str) -> str:
    if not isinstance(question, str):
        raise ValueError("V2.49.40 visible question is absent")
    matches = COHORT_PATTERN.findall(question)
    if len(matches) != 2 or matches[0] != matches[1]:
        raise ValueError("V2.49.40 visible cohort predicate drifted")
    return "C" + matches[0]


def parse_visible_countries(question: str) -> list[tuple[str, str]]:
    # Compatibility name used by the inherited child runner.  No row identity
    # is exposed by this open-world task; only a visible cohort predicate is.
    parse_visible_cohort(question)
    return []


parse_visible_entities = parse_visible_countries


def arm_order(opaque_id: str) -> tuple[str, str]:
    if not isinstance(opaque_id, str) or not opaque_id.startswith("task_"):
        raise ValueError("V2.49.40 opaque arm-order key drifted")
    return (
        ARMS
        if int(hashlib.sha256(opaque_id.encode()).hexdigest()[-1], 16) % 2 == 0
        else ARMS[::-1]
    )


def validate_task_vector(
    tasks: Sequence[Mapping[str, Any]],
) -> list[dict[str, str]]:
    if isinstance(tasks, (str, bytes)) or len(tasks) != SELECTED_COUNT:
        raise ValueError("V2.49.40 task denominator drifted")
    columns = visible_columns()
    output: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    seen_cohorts: set[str] = set()
    for item in tasks:
        if not isinstance(item, Mapping) or set(item) != {"opaque_id", "question"}:
            raise ValueError("V2.49.40 runtime input must be opaque_id and question")
        opaque = item.get("opaque_id")
        question = item.get("question")
        if (
            not isinstance(opaque, str)
            or not opaque.startswith("task_")
            or len(opaque) != 29
            or opaque in seen_ids
            or not isinstance(question, str)
            or not all(column in question for column in columns)
            or "<ENTITIES>" in question
            or "<COUNTRIES>" in question
        ):
            raise ValueError("V2.49.40 visible task binding drifted")
        cohort = parse_visible_cohort(question)
        if cohort in seen_cohorts:
            raise ValueError("V2.49.40 visible cohorts are not unique")
        seen_ids.add(opaque)
        seen_cohorts.add(cohort)
        output.append({"opaque_id": opaque, "question": question})
    return output


def protected_watcher_snapshot(proc_root: Path = Path("/proc")) -> list[dict[str, Any]]:
    output = []
    for pid, marker in PROTECTED_WATCHERS:
        stat = proc_root / str(pid) / "stat"
        cmdline = proc_root / str(pid) / "cmdline"
        if not stat.is_file() or not cmdline.is_file():
            raise RuntimeError("V2.49.40 protected watcher absent")
        raw = stat.read_text(encoding="utf-8")
        suffix = raw[raw.rfind(")") + 2 :].split()
        command = cmdline.read_bytes().replace(b"\0", b" ").decode(errors="replace")
        if len(suffix) <= 19 or marker not in command:
            raise RuntimeError("V2.49.40 protected watcher identity drifted")
        output.append({"pid": pid, "marker": marker, "start_ticks": int(suffix[19])})
    return output


__all__ = [name for name in globals() if name.isupper()] + [
    "arm_order",
    "parse_visible_cohort",
    "parse_visible_countries",
    "parse_visible_entities",
    "payload_sha256",
    "protected_watcher_snapshot",
    "sealed",
    "sha256",
    "validate_task_vector",
    "visible_columns",
]
