#!/usr/bin/env python3
"""Build physically separated visible and evaluator surfaces for V2.47.30."""

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

from scripts import design_v24729_dual_namespace_population_capacity_repair as design  # noqa: E402


DATE = "20260806"
AUTHORIZATION = Path(f"results/v24731_dual_namespace_surface_build_audit_v1_{DATE}.json")
CONTRACT = Path("src/deepwide_agent/v24730_dual_namespace_contract.py")
EVALUATOR = Path("src/deepwide_agent/v24730_dual_namespace_evaluator.py")
ROR_GOLD = Path("evaluation/v24730_ror_gold_v1.csv")
WB_GOLD = Path("evaluation/v24730_worldbank_gold_v1.csv")
PROVENANCE = Path("evaluation/v24730_dual_namespace_gold_provenance_v1.json")
SURFACES = (CONTRACT, EVALUATOR, ROR_GOLD, WB_GOLD, PROVENANCE)
TASKS_PER_CLUSTER = 12
TASK_SIZE = 4
TOTAL_TASKS = 24
RECORD_ID = re.compile(r"0[0-9a-z]{8}")
HEX40 = re.compile(r"[0-9a-f]{40}")
HEX64 = re.compile(r"[0-9a-f]{64}")


def payload_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()
    ).hexdigest()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"V2.47.30 expected ordinary file: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.47.30 expected object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _validate_parents() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    public = _read(ROOT / design.OUTPUT)
    ror = _read(ROOT / design.PRIVATE_ROR)
    wb = _read(ROOT / design.PRIVATE_WB)
    design.validate_public(public)
    if (
        ror.get("role") != "v24729_ror_evaluator_only_population"
        or wb.get("role") != "v24729_worldbank_evaluator_only_population"
        or not _sealed(ror, "private_payload_sha256")
        or not _sealed(wb, "private_payload_sha256")
        or public.get("clusters", {}).get("ror", {}).get(
            "private_population_file_sha256"
        )
        != sha256(ROOT / design.PRIVATE_ROR)
        or public.get("clusters", {}).get("worldbank", {}).get(
            "private_population_file_sha256"
        )
        != sha256(ROOT / design.PRIVATE_WB)
        or public.get("authorization")
        != {
            "dual_namespace_reachability_protocol_design": True,
            "population_publication_only": True,
            "forward_launch": False,
            "evaluator": False,
            "benchmark_dev64_or_exact220": False,
            "entropy_or_credit_claim": False,
            "leaderboard_or_sota": False,
        }
        or ror.get("forward_import_or_runtime_read_authorized") is not False
        or wb.get("forward_import_or_runtime_read_authorized") is not False
    ):
        raise RuntimeError("V2.47.30 population parent drifted")
    ror_groups = ror.get("groups")
    wb_groups = wb.get("groups")
    if (
        not isinstance(ror_groups, list)
        or not isinstance(wb_groups, list)
        or len(ror_groups) != TASKS_PER_CLUSTER
        or len(wb_groups) != TASKS_PER_CLUSTER
        or any(not isinstance(group, list) or len(group) != TASK_SIZE for group in ror_groups)
        or any(not isinstance(group, list) or len(group) != TASK_SIZE for group in wb_groups)
    ):
        raise RuntimeError("V2.47.30 private group envelope drifted")
    seen_ror: set[str] = set()
    for group in ror_groups:
        for item in group:
            if not isinstance(item, Mapping):
                raise RuntimeError("V2.47.30 ROR record drifted")
            label = str(item.get("label", ""))
            record_id = str(item.get("record_id", ""))
            country = str(item.get("country", ""))
            if (
                not label
                or any(character in label for character in '|\\"\r\n')
                or label in seen_ror
                or RECORD_ID.fullmatch(record_id) is None
                or re.fullmatch(r"[A-Z]{2}", country) is None
                or HEX40.fullmatch(str(item.get("git_blob_sha1", ""))) is None
                or HEX64.fullmatch(str(item.get("record_bytes_sha256", ""))) is None
            ):
                raise RuntimeError("V2.47.30 ROR private field drifted")
            seen_ror.add(label)
    seen_wb: set[str] = set()
    for group in wb_groups:
        for item in group:
            if not isinstance(item, Mapping):
                raise RuntimeError("V2.47.30 World Bank record drifted")
            name = str(item.get("name", ""))
            iso3 = str(item.get("iso3", ""))
            values = item.get("values")
            if (
                not name
                or any(character in name for character in "[]|\r\n")
                or iso3 in seen_wb
                or re.fullmatch(r"[A-Z]{3}", iso3) is None
                or not isinstance(values, list)
                or len(values) != len(design.base.WB_TARGETS)
                or any(not isinstance(value, str) or not value for value in values)
            ):
                raise RuntimeError("V2.47.30 World Bank private field drifted")
            seen_wb.add(iso3)
    if len(seen_ror) != 48 or len(seen_wb) != 48:
        raise RuntimeError("V2.47.30 private denominator drifted")
    return ror, wb, public


def _ror_question(group: Sequence[str]) -> str:
    rows = "\n".join(f"{index}. {entity}" for index, entity in enumerate(group, 1))
    return (
        "Use public web sources to return one Markdown table about these organizations:\n"
        f"<ENTITIES>\n{rows}\n</ENTITIES>\n"
        "The column names are: Organization, ROR ID, Country code. Use the 9-character "
        "ROR ID suffix, not the full URL, and the ISO 3166-1 alpha-2 country code. "
        "Use the official ROR registry. Use Unknown when unavailable. Return one table only."
    )


def _wb_question(group: Sequence[tuple[str, str]]) -> str:
    rows = "\n".join(
        f"{index}. {name} [{iso3}]"
        for index, (name, iso3) in enumerate(group, 1)
    )
    columns = " | ".join(
        [
            "Country",
            *(
                f'{target["label"]} [{target["indicator"]}] @{target["year"]}'
                for target in design.base.WB_TARGETS
            ),
        ]
    )
    return (
        "Use public web sources to return one Markdown table about these countries:\n"
        f"<COUNTRIES>\n{rows}\n</COUNTRIES>\n"
        "Please output one Markdown table with the columns, in this exact order:\n"
        f"{columns}\nUse the World Bank API values. Preserve the decimal representation "
        "returned by the official API. Use Unknown when unavailable. Return one table only."
    )


def _contract_text(
    ror_groups: tuple[tuple[str, ...], ...],
    wb_groups: tuple[tuple[tuple[str, str], ...], ...],
) -> str:
    targets = tuple(dict(item) for item in design.base.WB_TARGETS)
    questions = tuple(_ror_question(group) for group in ror_groups) + tuple(
        _wb_question(group) for group in wb_groups
    )
    return f'''"""Visible-only contract for the V2.47.30 dual-namespace gate."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from .v24639_ror_objective_runtime import extract_visible_entities
from .v24686_worldbank_target_value_runtime import _visible_contract


POLICY_ID = "v24730_dual_namespace_visible_contract_v1"
TASK_COUNT = {TOTAL_TASKS}
TASKS_PER_CLUSTER = {TASKS_PER_CLUSTER}
ROR_ENTITY_GROUPS = {pprint.pformat(ror_groups, width=100, sort_dicts=False)}
WORLD_BANK_COUNTRY_GROUPS = {pprint.pformat(wb_groups, width=100, sort_dicts=False)}
WORLD_BANK_TARGETS = {pprint.pformat(targets, width=100, sort_dicts=False)}
QUESTIONS = {pprint.pformat(questions, width=100, sort_dicts=False)}


def payload_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def visible_namespace(question: str) -> str:
    if not isinstance(question, str):
        raise ValueError("V2.47.30 question drifted")
    if "<ENTITIES>" in question and "official ROR registry" in question:
        entities = extract_visible_entities(question)
        if len(entities) == {TASK_SIZE}:
            return "ror"
    if "<COUNTRIES>" in question and "World Bank API values" in question:
        contract = _visible_contract(question)
        if len(contract["countries"]) == {TASK_SIZE} and contract["targets"] == list(WORLD_BANK_TARGETS):
            return "worldbank"
    raise ValueError("V2.47.30 visible namespace is unsupported")


def visible_task(ordinal: int) -> dict[str, str]:
    if isinstance(ordinal, bool) or not isinstance(ordinal, int) or not 1 <= ordinal <= TASK_COUNT:
        raise ValueError("V2.47.30 task ordinal drifted")
    value = {{
        "opaque_id": f"task_{{0x247300 + ordinal:024x}}",
        "question": QUESTIONS[ordinal - 1],
    }}
    namespace = visible_namespace(value["question"])
    expected = "ror" if ordinal <= TASKS_PER_CLUSTER else "worldbank"
    if namespace != expected:
        raise ValueError("V2.47.30 namespace/order drifted")
    return value


def task_vector() -> list[dict[str, str]]:
    return [visible_task(index) for index in range(1, TASK_COUNT + 1)]


__all__ = [
    "POLICY_ID", "QUESTIONS", "ROR_ENTITY_GROUPS", "TASK_COUNT",
    "TASKS_PER_CLUSTER", "WORLD_BANK_COUNTRY_GROUPS", "WORLD_BANK_TARGETS",
    "payload_sha256", "task_vector", "visible_namespace", "visible_task",
]
'''


def _evaluator_text() -> str:
    wb_columns = (
        "Country",
        *(
            f'{target["label"]} [{target["indicator"]}] @{target["year"]}'
            for target in design.base.WB_TARGETS
        ),
    )
    return f'''"""Evaluator-only utilities for the V2.47.30 dual-namespace gate."""

from __future__ import annotations

import csv
import io
import re
from collections.abc import Mapping, Sequence
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from .v24640_ror_external_evaluator import evaluate_prediction as evaluate_ror_prediction
from .v24730_dual_namespace_contract import TASK_COUNT, TASKS_PER_CLUSTER, visible_task


ROR_GOLD = Path("{ROR_GOLD}")
WORLD_BANK_GOLD = Path("{WB_GOLD}")
PROVENANCE = Path("{PROVENANCE}")
ARMS = ("baseline", "candidate")
ROR_COLUMNS = ("Organization", "ROR ID", "Country code")
WORLD_BANK_COLUMNS = {pprint.pformat(wb_columns, width=100, sort_dicts=False)}


def _norm(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value).casefold())


def _numeric_equal(left: object, right: object) -> bool:
    try:
        return Decimal(str(left).strip()) == Decimal(str(right).strip())
    except (InvalidOperation, ValueError):
        return False


def _csv_rows(text: str, columns: tuple[str, ...], expected: int) -> list[dict[str, str]]:
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None or tuple(reader.fieldnames) != ("opaque_id", *columns):
        raise ValueError("V2.47.30 gold schema drifted")
    rows = [{{key: str(value or "").strip() for key, value in row.items()}} for row in reader]
    if len(rows) != expected:
        raise ValueError("V2.47.30 gold denominator drifted")
    return rows


def gold_rows(ror_text: str, worldbank_text: str) -> dict[str, list[dict[str, str]]]:
    ror = _csv_rows(ror_text, ROR_COLUMNS, TASKS_PER_CLUSTER * 4)
    worldbank = _csv_rows(worldbank_text, WORLD_BANK_COLUMNS, TASKS_PER_CLUSTER * 4)
    expected_ror = {{visible_task(index)["opaque_id"] for index in range(1, TASKS_PER_CLUSTER + 1)}}
    expected_wb = {{visible_task(index)["opaque_id"] for index in range(TASKS_PER_CLUSTER + 1, TASK_COUNT + 1)}}
    if {{row["opaque_id"] for row in ror}} != expected_ror or {{row["opaque_id"] for row in worldbank}} != expected_wb:
        raise ValueError("V2.47.30 gold task identity drifted")
    return {{"ror": ror, "worldbank": worldbank}}


def evaluate_worldbank_prediction(prediction: str, expected: Sequence[Mapping[str, str]]) -> dict[str, Any]:
    lines = [line.strip() for line in str(prediction).replace("\\r\\n", "\\n").splitlines()]
    rows = [[cell.strip() for cell in line[1:-1].split("|")] for line in lines if line.startswith("|") and line.endswith("|")]
    if len(rows) < 3 or tuple(rows[0]) != WORLD_BANK_COLUMNS:
        return {{"exact_table_success": 0, "entity_recall": 0.0, "row_f1": 0.0, "item_f1": 0.0, "column_f1": 0.0, "composite": 0.0, "unknown_value_cells": 0}}
    data = [row for row in rows[2:] if len(row) == len(WORLD_BANK_COLUMNS) and all(row)]
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
            item_true += sum(_numeric_equal(row[index], gold[key][WORLD_BANK_COLUMNS[index]]) for index in (1, 2))
    predicted_items = len(predicted) * 2
    gold_items = len(gold) * 2
    item_precision = item_true / predicted_items if predicted_items else 0.0
    item_recall = item_true / gold_items
    item_f1 = 2 * item_precision * item_recall / (item_precision + item_recall) if item_precision + item_recall else 0.0
    exact = int(len(data) == len(expected) and true_entities == len(expected) and item_true == gold_items)
    composite = (recall + row_f1 + item_f1 + 1.0) / 4
    return {{"exact_table_success": exact, "entity_recall": recall, "row_f1": row_f1, "item_f1": item_f1, "column_f1": 1.0, "composite": composite, "unknown_value_cells": unknown}}


def evaluate_frozen_rows(predictions: Sequence[Mapping[str, Any]], gold: Mapping[str, Sequence[Mapping[str, str]]]) -> dict[str, Any]:
    by_task = {{str(row["opaque_id"]): ("ror", row) for row in gold["ror"]}}
    for row in gold["worldbank"]:
        by_task[str(row["opaque_id"])] = ("worldbank", row)
    grouped: dict[str, list[Mapping[str, str]]] = {{}}
    namespaces: dict[str, str] = {{}}
    for namespace, rows in gold.items():
        for row in rows:
            opaque_id = str(row["opaque_id"])
            grouped.setdefault(opaque_id, []).append(row)
            namespaces[opaque_id] = namespace
    metrics = {{namespace: {{arm: [] for arm in ARMS}} for namespace in ("ror", "worldbank")}}
    seen = set()
    for row in predictions:
        opaque_id = str(row.get("opaque_id", "")); arms = row.get("predictions")
        if opaque_id in seen or opaque_id not in grouped or not isinstance(arms, Mapping) or set(arms) != set(ARMS):
            raise ValueError("V2.47.30 frozen prediction drifted")
        seen.add(opaque_id); namespace = namespaces[opaque_id]
        for arm in ARMS:
            metric = evaluate_ror_prediction(str(arms[arm]), grouped[opaque_id]) if namespace == "ror" else evaluate_worldbank_prediction(str(arms[arm]), grouped[opaque_id])
            metrics[namespace][arm].append(metric)
    if len(seen) != TASK_COUNT:
        raise ValueError("V2.47.30 prediction denominator drifted")
    output = {{}}
    for namespace in metrics:
        output[namespace] = {{}}
        for arm, rows in metrics[namespace].items():
            output[namespace][arm] = {{
                "tasks": TASKS_PER_CLUSTER,
                "exact_table_successes": sum(row["exact_table_success"] for row in rows),
                **{{key: sum(float(row[key]) for row in rows) / TASKS_PER_CLUSTER for key in ("entity_recall", "row_f1", "item_f1", "column_f1", "composite")}},
                "unknown_value_cells": sum(row["unknown_value_cells"] for row in rows),
            }}
        output[namespace]["candidate_minus_baseline"] = {{key: output[namespace]["candidate"][key] - output[namespace]["baseline"][key] for key in ("exact_table_successes", "entity_recall", "row_f1", "item_f1", "column_f1", "composite")}}
    output["gate_passed"] = all(
        output[namespace]["candidate_minus_baseline"]["exact_table_successes"] > 0
        and output[namespace]["candidate_minus_baseline"]["composite"] >= 0
        and output[namespace]["candidate_minus_baseline"]["item_f1"] >= 0
        for namespace in ("ror", "worldbank")
    )
    return output


__all__ = ["ARMS", "PROVENANCE", "ROR_GOLD", "WORLD_BANK_GOLD", "evaluate_frozen_rows", "evaluate_worldbank_prediction", "gold_rows"]
'''


def build_surfaces() -> dict[Path, str]:
    ror, wb, public = _validate_parents()
    ror_groups = tuple(
        tuple(str(item["label"]) for item in group) for group in ror["groups"]
    )
    wb_groups = tuple(
        tuple((str(item["name"]), str(item["iso3"])) for item in group)
        for group in wb["groups"]
    )
    contract = _contract_text(ror_groups, wb_groups)
    evaluator = _evaluator_text()
    tree = ast.parse(contract)
    assignments = {
        target.id: ast.literal_eval(node.value)
        for node in tree.body
        if isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance((target := node.targets[0]), ast.Name)
        and target.id
        in {"ROR_ENTITY_GROUPS", "WORLD_BANK_COUNTRY_GROUPS", "WORLD_BANK_TARGETS", "QUESTIONS"}
    }
    if (
        assignments.get("ROR_ENTITY_GROUPS") != ror_groups
        or assignments.get("WORLD_BANK_COUNTRY_GROUPS") != wb_groups
        or assignments.get("WORLD_BANK_TARGETS")
        != tuple(dict(item) for item in design.base.WB_TARGETS)
        or len(assignments.get("QUESTIONS", ())) != TOTAL_TASKS
    ):
        raise RuntimeError("V2.47.30 generated visible contract drifted")
    forbidden_literals = {
        str(item[key])
        for group in ror["groups"]
        for item in group
        for key in ("record_id", "git_blob_sha1", "record_bytes_sha256")
    }
    forbidden_literals.update(
        str(item.get("raw_sha256", ""))
        for item in public["clusters"]["worldbank"].get("snapshot_metadata", [])
    )
    if (
        any(value and value in contract for value in forbidden_literals)
        or str(design.PRIVATE_ROR) in contract
        or str(design.PRIVATE_WB) in contract
        or "evaluation/" in contract
        or "external_evaluator" in contract
    ):
        raise RuntimeError("V2.47.30 visible contract contains evaluator-only data")

    ror_output = io.StringIO(newline="")
    ror_writer = csv.DictWriter(
        ror_output,
        fieldnames=["opaque_id", "Organization", "ROR ID", "Country code"],
        lineterminator="\n",
    )
    ror_writer.writeheader()
    ror_provenance = []
    for ordinal, group in enumerate(ror["groups"], 1):
        opaque_id = f"task_{0x247300 + ordinal:024x}"
        for item in group:
            ror_writer.writerow(
                {
                    "opaque_id": opaque_id,
                    "Organization": item["label"],
                    "ROR ID": item["record_id"],
                    "Country code": item["country"],
                }
            )
            ror_provenance.append(
                {
                    "opaque_id": opaque_id,
                    "record_id": item["record_id"],
                    "git_blob_sha1": item["git_blob_sha1"],
                    "record_bytes_sha256": item["record_bytes_sha256"],
                }
            )

    wb_columns = [
        "Country",
        *(
            f'{target["label"]} [{target["indicator"]}] @{target["year"]}'
            for target in design.base.WB_TARGETS
        ),
    ]
    wb_output = io.StringIO(newline="")
    wb_writer = csv.DictWriter(
        wb_output,
        fieldnames=["opaque_id", *wb_columns],
        lineterminator="\n",
    )
    wb_writer.writeheader()
    wb_provenance = []
    for local, group in enumerate(wb["groups"], 1):
        ordinal = TASKS_PER_CLUSTER + local
        opaque_id = f"task_{0x247300 + ordinal:024x}"
        for item in group:
            row = {"opaque_id": opaque_id, "Country": item["name"]}
            for column, value, target in zip(
                wb_columns[1:], item["values"], design.base.WB_TARGETS, strict=True
            ):
                row[column] = value
                wb_provenance.append(
                    {
                        "opaque_id": opaque_id,
                        "iso3": item["iso3"],
                        "indicator": target["indicator"],
                        "year": target["year"],
                    }
                )
            wb_writer.writerow(row)
    provenance = {
        "artifact_version": 1,
        "role": "v24730_dual_namespace_gold_provenance",
        "population_design_sha256": sha256(ROOT / design.OUTPUT),
        "private_population_sha256": {
            "ror": sha256(ROOT / design.PRIVATE_ROR),
            "worldbank": sha256(ROOT / design.PRIVATE_WB),
        },
        "ror_source": {
            "commit": ror["commit"],
            "version": ror["version"],
            "directory_tree_sha1": ror["directory_tree_sha1"],
            "records": ror_provenance,
        },
        "worldbank_source": {
            "targets": wb["targets"],
            "snapshot_metadata": public["clusters"]["worldbank"]["snapshot_metadata"],
            "records": wb_provenance,
        },
        "forward_import_or_runtime_read_authorized": False,
        "gold_open_before_prediction_freeze_authorized": False,
    }
    provenance["provenance_payload_sha256"] = payload_sha256(provenance)
    return {
        CONTRACT: contract,
        EVALUATOR: evaluator,
        ROR_GOLD: ror_output.getvalue(),
        WB_GOLD: wb_output.getvalue(),
        PROVENANCE: json.dumps(provenance, ensure_ascii=False, sort_keys=True) + "\n",
    }


def _authorization_valid() -> bool:
    try:
        value = _read(ROOT / AUTHORIZATION)
    except (OSError, RuntimeError, json.JSONDecodeError):
        return False
    return (
        value.get("role") == "v24731_dual_namespace_surface_build_audit"
        and value.get("audit_valid") is True
        and value.get("findings") == []
        and value.get("authorization")
        == {
            "one_surface_publication": True,
            "reachability_protocol_design": True,
            "forward_launch": False,
            "evaluator_execution": False,
            "benchmark_dev64_or_exact220": False,
            "leaderboard_or_sota": False,
        }
        and _sealed(value, "audit_payload_sha256")
    )


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=20,
    ).stdout.strip()


def _publish(path: Path, text: str) -> None:
    target = ROOT / path
    if target.exists() or target.is_symlink():
        raise FileExistsError(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())


def main() -> None:
    if _git("status", "--porcelain") or _git("rev-parse", "HEAD") != _git(
        "rev-parse", "target/main"
    ):
        raise RuntimeError("V2.47.30 requires clean pushed HEAD")
    if not _authorization_valid():
        raise RuntimeError("V2.47.30 surface publication is not authorized")
    surfaces = build_surfaces()
    if set(surfaces) != set(SURFACES) or any(
        (ROOT / path).exists() or (ROOT / path).is_symlink() for path in SURFACES
    ):
        raise RuntimeError("V2.47.30 surface is not pristine")
    created = []
    try:
        for path, text in surfaces.items():
            _publish(path, text)
            created.append(ROOT / path)
    except BaseException:
        for path in reversed(created):
            path.unlink(missing_ok=True)
        raise


if __name__ == "__main__":
    main()
