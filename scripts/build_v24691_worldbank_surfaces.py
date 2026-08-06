#!/usr/bin/env python3
"""Derive separated visible and evaluator surfaces from V2.46.90 population."""

from __future__ import annotations

import ast
import csv
import hashlib
import io
import json
import os
import pprint
import re
import subprocess
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24320_forward_contract import payload_sha256  # noqa: E402
from scripts import design_v24688_worldbank_population as base  # noqa: E402
from scripts import design_v24690_worldbank_population_capacity_repair as design  # noqa: E402


DATE = "20260806"
AUTHORIZATION = Path(
    f"results/v24692_worldbank_surface_build_audit_v1_{DATE}.json"
)
CONTRACT = Path("src/deepwide_agent/v24691_worldbank_external_contract.py")
EVALUATOR = Path("src/deepwide_agent/v24691_worldbank_external_evaluator.py")
GOLD = Path("evaluation/v24691_worldbank_gold_v1.csv")
PROVENANCE = Path("evaluation/v24691_worldbank_gold_provenance_v1.json")


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.46.91 surface builder expected object")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def _validate_parents() -> tuple[dict[str, Any], dict[str, Any]]:
    private = _read(ROOT / design.PRIVATE)
    population = _read(ROOT / design.OUTPUT)
    groups = private.get("groups")
    if (
        private.get("role") != "v24690_worldbank_evaluator_only_population"
        or not _sealed(private, "private_payload_sha256")
        or population.get("role") != "v24690_worldbank_population_design"
        or not _sealed(population, "design_sha256")
        or population.get("selected_count") != 48
        or population.get("task_count") != 12
        or population.get("task_size") != 4
        or population.get("private_population_file_sha256")
        != _sha256(ROOT / design.PRIVATE)
        or population.get("authorization", {}).get(
            "isolated_forward_contract_gold_provenance_and_evaluator_design"
        )
        is not True
        or population.get("authorization", {}).get("activation_or_launch") is not False
        or not isinstance(groups, Sequence)
        or isinstance(groups, (str, bytes))
        or len(groups) != 12
        or any(not isinstance(group, list) or len(group) != 4 for group in groups)
    ):
        raise RuntimeError("V2.46.91 population parent drifted")
    seen: set[str] = set()
    for group in groups:
        for record in group:
            if not isinstance(record, Mapping):
                raise RuntimeError("V2.46.91 private country record drifted")
            iso3 = str(record.get("iso3", ""))
            name = str(record.get("name", ""))
            values = record.get("values")
            if (
                re.fullmatch(r"[A-Z]{3}", iso3) is None
                or iso3 in seen
                or not name
                or any(character in name for character in "[]|\r\n")
                or not isinstance(values, list)
                or len(values) != 2
            ):
                raise RuntimeError("V2.46.91 private country field drifted")
            expected_targets = {
                (target["indicator"], target["year"]) for target in base.TARGETS
            }
            if {
                (str(value.get("indicator")), str(value.get("year")))
                for value in values
                if isinstance(value, Mapping)
            } != expected_targets or any(
                not isinstance(value, Mapping)
                or not str(value.get("value", ""))
                or re.fullmatch(r"[0-9a-f]{64}", str(value.get("response_sha256", "")))
                is None
                for value in values
            ):
                raise RuntimeError("V2.46.91 private target value drifted")
            seen.add(iso3)
    if len(seen) != 48:
        raise RuntimeError("V2.46.91 private country denominator drifted")
    return private, population


def _question(group: Sequence[Mapping[str, Any]]) -> str:
    rows = "\n".join(
        f'{index}. {record["name"]} [{record["iso3"]}]'
        for index, record in enumerate(group, 1)
    )
    columns = " | ".join(
        [
            "Country",
            *(
                f'{target["label"]} [{target["indicator"]}] @{target["year"]}'
                for target in base.TARGETS
            ),
        ]
    )
    return (
        "Use public web sources to return one Markdown table about these countries:\n"
        f"<COUNTRIES>\n{rows}\n</COUNTRIES>\n"
        "Please output one Markdown table with the columns, in this exact order:\n"
        f"{columns}\n"
        "Use the World Bank API values. Preserve the decimal representation returned "
        "by the official API. Use Unknown when unavailable. Return one table only."
    )


def _contract_text(groups: tuple[tuple[tuple[str, str], ...], ...]) -> str:
    questions = tuple(
        _question([{"name": name, "iso3": iso3} for name, iso3 in group])
        for group in groups
    )
    groups_text = pprint.pformat(groups, width=100, sort_dicts=False)
    questions_text = pprint.pformat(questions, width=100, sort_dicts=False)
    targets_text = pprint.pformat(tuple(dict(item) for item in base.TARGETS), width=100)
    return f'''"""Visible-only frozen contract for V2.46.91 World Bank gate."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .v24686_worldbank_target_value_runtime import _visible_contract


DATE = "{DATE}"
PROTOCOL_ID = "v24691_worldbank_target_value_external_v1"
PROTOCOL = Path(f"results/v24691_worldbank_preregistration_v1_{{DATE}}.json")
PREAUDIT = Path(f"results/v24691_worldbank_preactivation_audit_v1_{{DATE}}.json")
ACTIVATION = Path(f"results/v24691_worldbank_activation_v1_{{DATE}}.json")
EXECUTION_START = Path(f"results/v24691_worldbank_execution_start_v1_{{DATE}}.json")
FORWARD_RESULT = Path(f"results/v24691_worldbank_forward_result_v1_{{DATE}}.json")
FORWARD_AUDIT = Path(f"results/v24691_worldbank_forward_audit_v1_{{DATE}}.json")
OUTPUT_ROOT = Path(f"outputs/v24691_worldbank_v1_{{DATE}}")
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
TASK_ROOT = OUTPUT_ROOT / "tasks"
PREDICTIONS = OUTPUT_ROOT / "frozen_predictions.jsonl"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
RUN_SUMMARY = OUTPUT_ROOT / "run_summary.json"
LEASE_PATH = Path("outputs/deepwide_benchmark_api.lease.lock")
LEASE_OWNER = PROTOCOL_ID
LEASE_PURPOSE = "benchmark_external_worldbank_target_value"
SELECTED_COUNT = 12
ARM_COUNT = 3
EXECUTOR_CONCURRENCY = 12
MODEL_SLOT_CAP = 8
PARENT_TIMEOUT_SECONDS = 255.0
PROTECTED_WATCHERS = (
    (795336, "scripts/watch_v2415_r1_checkpoint_liveness.py"),
    (3061652, "scripts/watch_v24218_exact220_executor.py"),
)
MODEL = {{
    "proxy_url": "http://127.0.0.1:9878/responses",
    "name": "gpt-5.6-sol",
    "reasoning_effort": "low",
    "service_tier": "priority",
    "timeout_seconds": 65,
    "max_retries": 2,
}}
SEARCH = {{
    "proxy_url": "http://127.0.0.1:9878/responses",
    "model": "gpt-5.6-sol",
    "workers": 1,
    "batch_size": 8,
    "context_size": "medium",
    "max_output_tokens": 7_000,
    "timeout_seconds": 65,
    "max_retries": 2,
    "fetch_workers": 10,
    "fetch_timeout_seconds": 35,
    "hard_fetch_deadline_seconds": 40,
}}
LIMITS = {{
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
}}
TARGETS = {targets_text}
COUNTRY_GROUPS = {groups_text}
QUESTIONS = {questions_text}


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def protected_watcher_snapshot(proc_root: Path = Path("/proc")) -> list[dict[str, Any]]:
    output = []
    for pid, marker in PROTECTED_WATCHERS:
        stat = proc_root / str(pid) / "stat"
        cmdline = proc_root / str(pid) / "cmdline"
        if not stat.is_file() or not cmdline.is_file():
            raise RuntimeError("V2.46.91 protected watcher is absent")
        raw = stat.read_text(encoding="utf-8")
        suffix = raw[raw.rfind(")") + 2 :].split()
        command = cmdline.read_bytes().replace(b"\\0", b" ").decode(errors="replace")
        if len(suffix) <= 19 or marker not in command:
            raise RuntimeError("V2.46.91 protected watcher identity drifted")
        output.append({{"pid": pid, "marker": marker, "start_ticks": int(suffix[19])}})
    return output


def visible_task(ordinal: int) -> dict[str, str]:
    if isinstance(ordinal, bool) or not isinstance(ordinal, int) or not 1 <= ordinal <= SELECTED_COUNT:
        raise ValueError("V2.46.91 task ordinal drifted")
    value = {{
        "opaque_id": f"task_{{0x246910 + ordinal:024x}}",
        "question": QUESTIONS[ordinal - 1],
    }}
    contract = _visible_contract(value["question"])
    expected = [{{"name": name, "iso3": iso3}} for name, iso3 in COUNTRY_GROUPS[ordinal - 1]]
    if contract["countries"] != expected:
        raise ValueError("V2.46.91 visible task round trip drifted")
    return value


def task_vector() -> list[dict[str, str]]:
    return [visible_task(index) for index in range(1, SELECTED_COUNT + 1)]


__all__ = [name for name in tuple(globals()) if name.isupper()] + [
    "payload_sha256", "protected_watcher_snapshot", "sha256", "task_vector", "visible_task"
]
'''


def _evaluator_text() -> str:
    return '''"""Post-freeze evaluator-only utilities for V2.46.91 World Bank gate."""

from __future__ import annotations

import csv
import io
import re
from collections.abc import Mapping, Sequence
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from .v24691_worldbank_external_contract import COUNTRY_GROUPS, SELECTED_COUNT, visible_task


GOLD = Path("evaluation/v24691_worldbank_gold_v1.csv")
PROVENANCE = Path("evaluation/v24691_worldbank_gold_provenance_v1.json")
ARMS = ("frozen_parser", "expanded_parser", "target_value")
COLUMNS = ("Country", "GDP per capita (current US$) [NY.GDP.PCAP.CD] @2023", "Urban population (%) [SP.URB.TOTL.IN.ZS] @2023")


def _norm(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value).casefold())


def _numeric_equal(left: object, right: object) -> bool:
    try:
        return Decimal(str(left).strip()) == Decimal(str(right).strip())
    except (InvalidOperation, ValueError):
        return False


def gold_rows(text: str) -> list[dict[str, str]]:
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None or tuple(reader.fieldnames) != ("opaque_id", *COLUMNS):
        raise ValueError("V2.46.91 gold schema drifted")
    rows = [{key: str(value or "").strip() for key, value in row.items()} for row in reader]
    pairs = [
        (visible_task(index)["opaque_id"], name)
        for index, group in enumerate(COUNTRY_GROUPS, 1)
        for name, _iso3 in group
    ]
    if len(rows) != 48 or [(row["opaque_id"], row["Country"]) for row in rows] != pairs:
        raise ValueError("V2.46.91 gold denominator or identity drifted")
    return rows


def evaluate_prediction(prediction: str, expected: Sequence[Mapping[str, str]]) -> dict[str, Any]:
    lines = [line.strip() for line in str(prediction).replace("\\r\\n", "\\n").splitlines()]
    rows = [
        [cell.strip() for cell in line[1:-1].split("|")]
        for line in lines if line.startswith("|") and line.endswith("|")
    ]
    if len(rows) < 3 or tuple(rows[0]) != COLUMNS:
        return {"exact_table_success": 0, "entity_recall": 0.0, "row_f1": 0.0, "item_f1": 0.0, "column_f1": 0.0, "composite": 0.0, "unknown_value_cells": 0}
    data = [row for row in rows[2:] if len(row) == len(COLUMNS) and all(row)]
    gold = {{_norm(row["Country"]): row for row in expected}}
    predicted = {{_norm(row[0]): row for row in data if _norm(row[0])}}
    true_entities = len(set(gold) & set(predicted))
    precision = true_entities / len(predicted) if predicted else 0.0
    recall = true_entities / len(gold)
    row_f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    item_true = 0
    unknown = 0
    for key, row in predicted.items():
        unknown += sum(cell.casefold() in {{"unknown", "未知", "n/a", "na", "-", "—"}} for cell in row[1:])
        if key in gold:
            item_true += int(_numeric_equal(row[1], gold[key][COLUMNS[1]]))
            item_true += int(_numeric_equal(row[2], gold[key][COLUMNS[2]]))
    predicted_items = len(predicted) * 2
    gold_items = len(gold) * 2
    item_precision = item_true / predicted_items if predicted_items else 0.0
    item_recall = item_true / gold_items
    item_f1 = 2 * item_precision * item_recall / (item_precision + item_recall) if item_precision + item_recall else 0.0
    exact = int(len(data) == len(expected) and true_entities == len(expected) and item_true == gold_items)
    composite = (recall + row_f1 + item_f1 + 1.0) / 4
    return {"exact_table_success": exact, "entity_recall": recall, "row_f1": row_f1, "item_f1": item_f1, "column_f1": 1.0, "composite": composite, "unknown_value_cells": unknown}


def evaluate_frozen_rows(predictions: Sequence[Mapping[str, Any]], gold: Sequence[Mapping[str, str]]) -> dict[str, Any]:
    by_task: dict[str, list[Mapping[str, str]]] = {}
    for row in gold:
        by_task.setdefault(str(row["opaque_id"]), []).append(row)
    metrics = {{arm: [] for arm in ARMS}}
    seen: set[str] = set()
    for row in predictions:
        opaque_id = str(row.get("opaque_id", ""))
        arms = row.get("predictions")
        if opaque_id in seen or opaque_id not in by_task or not isinstance(arms, Mapping) or set(arms) != set(ARMS):
            raise ValueError("V2.46.91 frozen prediction drifted")
        seen.add(opaque_id)
        for arm in ARMS:
            metrics[arm].append(evaluate_prediction(str(arms[arm]), by_task[opaque_id]))
    if len(predictions) != SELECTED_COUNT or len(seen) != SELECTED_COUNT:
        raise ValueError("V2.46.91 fixed denominator drifted")
    aggregates = {{}}
    for arm, task_rows in metrics.items():
        aggregates[arm] = {{
            "tasks": SELECTED_COUNT,
            "exact_table_successes": sum(row["exact_table_success"] for row in task_rows),
            **{{key: sum(float(row[key]) for row in task_rows) / SELECTED_COUNT for key in ("entity_recall", "row_f1", "item_f1", "column_f1", "composite")}},
            "unknown_value_cells": sum(row["unknown_value_cells"] for row in task_rows),
        }}
    parser_delta = {{key: aggregates["expanded_parser"][key] - aggregates["frozen_parser"][key] for key in ("exact_table_successes", "entity_recall", "row_f1", "item_f1", "column_f1", "composite")}}
    target_delta = {{key: aggregates["target_value"][key] - aggregates["expanded_parser"][key] for key in ("exact_table_successes", "entity_recall", "row_f1", "item_f1", "column_f1", "composite")}}
    return {{
        "arms": aggregates,
        "expanded_minus_frozen": parser_delta,
        "target_value_minus_expanded": target_delta,
        "gate_passed": target_delta["exact_table_successes"] > 0 and target_delta["composite"] >= 0 and target_delta["item_f1"] >= 0,
    }}


__all__ = ["ARMS", "COLUMNS", "GOLD", "PROVENANCE", "evaluate_frozen_rows", "evaluate_prediction", "gold_rows"]
'''


def build_surfaces() -> dict[Path, str]:
    private, population = _validate_parents()
    raw_groups = private["groups"]
    groups = tuple(
        tuple((str(record["name"]), str(record["iso3"])) for record in group)
        for group in raw_groups
    )
    contract_source = _contract_text(groups)
    evaluator_source = _evaluator_text()
    tree = ast.parse(contract_source)
    assignments = {
        target.id: ast.literal_eval(node.value)
        for node in tree.body
        if isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance((target := node.targets[0]), ast.Name)
        and target.id in {"COUNTRY_GROUPS", "QUESTIONS", "TARGETS"}
    }
    if assignments.get("COUNTRY_GROUPS") != groups:
        raise RuntimeError("V2.46.91 generated visible groups drifted")
    private_values = {
        str(value["value"])
        for group in raw_groups
        for record in group
        for value in record["values"]
    }
    private_hashes = {
        str(value["response_sha256"])
        for group in raw_groups
        for record in group
        for value in record["values"]
    }
    if (
        any(value in contract_source for value in private_values)
        or any(value in contract_source for value in private_hashes)
        or str(design.PRIVATE) in contract_source
        or "external_evaluator" in contract_source
        or "evaluation/" in contract_source
    ):
        raise RuntimeError("V2.46.91 visible contract contains evaluator-only data")

    column_names = [
        "Country",
        *(
            f'{target["label"]} [{target["indicator"]}] @{target["year"]}'
            for target in base.TARGETS
        ),
    ]
    output = io.StringIO(newline="")
    writer = csv.DictWriter(
        output,
        fieldnames=["opaque_id", *column_names],
        lineterminator="\n",
    )
    writer.writeheader()
    provenance_records = []
    for ordinal, group in enumerate(raw_groups, 1):
        opaque_id = f"task_{0x246910 + ordinal:024x}"
        for record in group:
            by_target = {
                (value["indicator"], value["year"]): value
                for value in record["values"]
            }
            row = {"opaque_id": opaque_id, "Country": record["name"]}
            for target, column in zip(base.TARGETS, column_names[1:], strict=True):
                value = by_target[(target["indicator"], target["year"])]
                row[column] = value["value"]
                provenance_records.append(
                    {
                        "opaque_id": opaque_id,
                        "iso3": record["iso3"],
                        "indicator": target["indicator"],
                        "year": target["year"],
                        "source_url": value["source_url"],
                        "response_sha256": value["response_sha256"],
                    }
                )
            writer.writerow(row)
    provenance = {
        "artifact_version": 1,
        "role": "v24691_worldbank_gold_provenance",
        "population_design_sha256": _sha256(ROOT / design.OUTPUT),
        "private_population_sha256": _sha256(ROOT / design.PRIVATE),
        "catalog_response_sha256": private["catalog"]["response_sha256"],
        "records": provenance_records,
        "forward_import_or_runtime_read_authorized": False,
        "gold_open_before_prediction_freeze_authorized": False,
    }
    provenance["provenance_payload_sha256"] = payload_sha256(provenance)
    return {
        CONTRACT: contract_source,
        EVALUATOR: evaluator_source,
        GOLD: output.getvalue(),
        PROVENANCE: json.dumps(
            provenance, ensure_ascii=False, indent=2, sort_keys=True
        )
        + "\n",
    }


def _authorization_valid() -> bool:
    if not (ROOT / AUTHORIZATION).is_file() or (ROOT / AUTHORIZATION).is_symlink():
        return False
    value = _read(ROOT / AUTHORIZATION)
    return (
        value.get("role") == "v24692_worldbank_surface_build_audit"
        and value.get("audit_valid") is True
        and value.get("findings") == []
        and value.get("authorization")
        == {
            "one_surface_publication": True,
            "external_protocol_design": False,
            "preactivation_or_launch": False,
            "evaluator_execution": False,
            "dev64_or_exact220": False,
            "leaderboard_or_sota": False,
        }
        and _sealed(value, "audit_payload_sha256")
    )


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=20,
    ).stdout.strip()


def _publish(relative: Path, data: str) -> None:
    path = ROOT / relative
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def main() -> None:
    if _git("status", "--porcelain") or _git("rev-parse", "HEAD") != _git(
        "rev-parse", "target/main"
    ):
        raise RuntimeError("V2.46.91 surface builder requires clean pushed HEAD")
    if not _authorization_valid():
        raise RuntimeError("V2.46.91 surface publication is not authorized")
    surfaces = build_surfaces()
    if any((ROOT / path).exists() or (ROOT / path).is_symlink() for path in surfaces):
        raise FileExistsError("V2.46.91 surface already exists")
    for path, data in surfaces.items():
        _publish(path, data)
    print(
        json.dumps(
            {
                "contract": str(CONTRACT),
                "gold_rows": 48,
                "surface_sha256": {
                    str(path): _sha256(ROOT / path) for path in surfaces
                },
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
