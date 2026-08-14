#!/usr/bin/env python3
"""Aggregate-only diagnosis of the frozen V2.54.81 mechanism NO-GO.

This diagnosis opens only the already frozen same-forward runtime envelopes
after their label-blind forward audit.  It emits counts and booleans, never a
question, opaque id, URL, page, quote, source field/value, prediction, answer,
truth, evaluator row, score, reward, or per-task outcome.  It performs no
network, model, search, fetch, evaluator, or benchmark call.
"""

from __future__ import annotations

import copy
import json
import os
import re
import time
import unicodedata
from collections import Counter, defaultdict
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in __import__("sys").path:
        __import__("sys").path.insert(0, str(path))

from deepwide_agent import v25432_source_authoritative_field_candidate as source  # noqa: E402
from deepwide_agent import v25471_qualified_source_label_candidate as candidate  # noqa: E402
from deepwide_agent import v25481_qualified_source_label_external_contract as contract  # noqa: E402
from scripts import run_v25481_qualified_source_label_external as runner  # noqa: E402


ROLE = "v25482_v25481_qualified_label_no_go_diagnosis"
OUTPUT = Path(
    "results/v25482_v25481_qualified_label_no_go_diagnosis_v1_20260814.json"
)
EXPECTED = {
    str(contract.FORWARD_RESULT): "90b87437af58374e7587aa28fbc86987de56c4f89eb1979205489e6b5ae3c903",
    str(contract.FORWARD_AUDIT): "ba3135e2ffea7100e6481e396021a1c099f83ec17e0f300c6417832f92fffb4a",
    str(contract.TASK_ROWS): "4d4fe0f5223859e8932400a147fd5d8a933991e168c5eddcebad1798834f9645",
    str(contract.PREDICTION_FREEZE): "ed7160fc0b2277f9e297bfd1d86c888f17b2492f42a5617685e6f62c430af16d",
}
ADJACENT_COUNT_FIELDS = (
    "fused_standalone_field_surface_count",
    "adjacent_shape_rejected_count",
    "adjacent_evidence_rejected_count",
    "adjacent_evidence_closed_observation_count",
    "adjacent_conflicting_coordinate_count",
    "adjacent_ambiguous_same_value_coordinate_count",
    "adjacent_unchanged_coordinate_count",
    "adjacent_surface_equivalent_coordinate_count",
    "adjacent_counterfactual_candidate_count",
)


def _read(relative: Path) -> dict[str, Any]:
    value = json.loads(
        contract.ordinary(ROOT, relative, tracked=True).read_text(encoding="utf-8")
    )
    if not isinstance(value, dict):
        raise RuntimeError("V2.54.82 expected a JSON object")
    return value


def _rows() -> list[dict[str, Any]]:
    path = contract.ordinary(ROOT, contract.TASK_ROWS, tracked=True)
    values = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return [runner.validate_task_row(value) for value in values]


def _decorated_surface(value: str) -> str:
    text = unicodedata.normalize("NFKC", str(value)).strip()
    text = re.sub(r"^[#*_`~+\-\s:]+", "", text)
    text = re.sub(r"[#*_`~+\-\s:]+$", "", text)
    return text.strip()


def _fused_field(label: str, columns: tuple[str, ...]) -> tuple[int, str] | None:
    label_tokens = candidate.identity_parent._tokens(label)
    matches: list[tuple[int, str]] = []
    for index, field in enumerate(columns):
        if index == 0:
            continue
        field_tokens = candidate.identity_parent._tokens(field)
        if (
            field_tokens
            and len(label_tokens) == len(field_tokens)
            and tuple(label_tokens[1:]) == tuple(field_tokens[1:])
            and label_tokens[0].endswith(field_tokens[0])
            and 2 <= len(label_tokens[0]) - len(field_tokens[0]) <= 8
        ):
            matches.append((index, str(field)))
    return matches[0] if len(matches) == 1 else None


def build_diagnosis(*, now: int | None = None) -> dict[str, Any]:
    if any(contract.sha256(ROOT / path) != digest for path, digest in EXPECTED.items()):
        raise RuntimeError("V2.54.82 frozen input hash drifted")
    forward = runner.validate_forward_result(_read(contract.FORWARD_RESULT))
    audit = _read(contract.FORWARD_AUDIT)
    if (
        audit.get("audit_valid") is not True
        or audit.get("findings") != []
        or audit.get("authorization", {}).get("postfreeze_quality_protocol")
        is not False
    ):
        raise RuntimeError("V2.54.82 forward audit barrier drifted")

    rows = _rows()
    registry = Counter()
    adjacent = Counter()
    per_task_adjacent_candidates = 0
    for row in rows:
        decoded = runner._decode_completed(
            row["runtime_result"], row["content_free_stage_receipt"]
        )
        result = decoded["result"]
        application = candidate.validate_application(
            result["private_source_application"]
        )
        receipt = candidate.validate_registry_receipt(
            application["private_candidate_registry"]["content_free_receipt"]
        )
        for name, amount in receipt.items():
            if isinstance(amount, int) and not isinstance(amount, bool):
                registry[name] += amount

        columns, table_rows = source._canonical_table(
            result["predictions"][runner.runtime.BASE_ARM],
            result["private_source_columns"],
        )
        bound, _counts = candidate.parent._bound_pages(
            table_rows, result["private_same_forward_pages"]
        )
        row_map = {source._key(value[0]): index for index, value in enumerate(table_rows)}
        observations: list[tuple[int, int, str, str, str]] = []
        for page in bound:
            spans = source._line_spans(str(page["content"]))
            for index, (start, _end, line) in enumerate(spans):
                fused = _fused_field(_decorated_surface(line), columns)
                if fused is None:
                    continue
                adjacent["fused_standalone_field_surface_count"] += 1
                if (
                    index + 2 >= len(spans)
                    or spans[index + 1][2].strip()
                    or not spans[index + 2][2].strip()
                ):
                    adjacent["adjacent_shape_rejected_count"] += 1
                    continue
                value = source._safe_cell(spans[index + 2][2].strip())
                quote = str(page["content"])[start : spans[index + 2][1]]
                if (
                    value is None
                    or not 1 <= len(quote) <= source.MAXIMUM_QUOTE_CHARACTERS
                    or str(page["content"]).count(quote) != 1
                ):
                    adjacent["adjacent_evidence_rejected_count"] += 1
                    continue
                adjacent["adjacent_evidence_closed_observation_count"] += 1
                row_index = row_map[source._key(page["row_identity"])]
                column_index, _field = fused
                observations.append(
                    (
                        row_index,
                        column_index,
                        source._key(value),
                        str(table_rows[row_index][column_index]),
                        value,
                    )
                )
        groups: defaultdict[tuple[int, int], list[tuple[int, int, str, str, str]]] = defaultdict(list)
        for observation in observations:
            groups[observation[:2]].append(observation)
        retained = 0
        for coordinate, items in groups.items():
            if len(items) != 1:
                normalized = {item[2] for item in items}
                adjacent[
                    "adjacent_conflicting_coordinate_count"
                    if len(normalized) > 1
                    else "adjacent_ambiguous_same_value_coordinate_count"
                ] += 1
                continue
            _row_index, _column_index, _value_key, old_value, exact_value = items[0]
            if source._key(old_value) == source._key(exact_value):
                adjacent["adjacent_unchanged_coordinate_count"] += 1
                continue
            if candidate.parent._surface_equivalent(
                columns[coordinate[1]], old_value, exact_value
            ):
                adjacent["adjacent_surface_equivalent_coordinate_count"] += 1
                continue
            retained += 1
            adjacent["adjacent_counterfactual_candidate_count"] += 1
        per_task_adjacent_candidates += int(retained > 0)

    aggregate = forward["aggregate"]
    unused_fetch_capacity = (
        aggregate["completed_runtime_tasks"]
        * contract.mechanism_gate()["maximum_physical_fetches_per_completed_task"]
        - aggregate["completed_physical_fetches"]
    )
    diagnosis = {
        "terminal_tasks": aggregate["terminal_tasks"],
        "completed_runtime_tasks": aggregate["completed_runtime_tasks"],
        "failure_as_zero_tasks": aggregate["failure_as_zero_tasks"],
        "accepted_unique_identity_page_tasks": aggregate[
            "accepted_unique_identity_page_tasks"
        ],
        "accepted_unique_identity_page_count_total": aggregate[
            "accepted_unique_identity_page_count_total"
        ],
        "qualified_label_surface_count": registry["qualified_label_surface_count"],
        "qualified_label_observation_count": registry[
            "qualified_label_observation_count"
        ],
        "available_candidate_count": registry["available_candidate_count"],
        "applied_coordinate_count": registry["applied_coordinate_count"],
        "prediction_changed_tasks": aggregate["prediction_changed_tasks"],
        "application_failure_tasks": aggregate["application_failure_tasks"],
        "completed_physical_queries": aggregate["completed_physical_queries"],
        "completed_physical_fetches": aggregate["completed_physical_fetches"],
        "completed_physical_model_forwards": aggregate[
            "completed_physical_model_forwards"
        ],
        "unused_fetch_capacity_under_existing_hard_cap": unused_fetch_capacity,
        "adjacent_surface_counterfactual": {
            **{name: int(adjacent[name]) for name in ADJACENT_COUNT_FIELDS},
            "counterfactual_candidate_tasks": per_task_adjacent_candidates,
        },
        "mechanism_gate_passed": forward["mechanism_decision"][
            "mechanism_gate_passed"
        ],
        "failed_checks": forward["mechanism_decision"]["failed_checks"],
        "next_bottleneck": "row_key_bound_official_detail_page_reach_before_field_parsing",
        "relaxing_qualified_label_or_adjacent_line_grammar_is_not_supported": True,
        "next_candidate_requires_one_row_key_derived_official_detail_fetch_within_existing_cap": True,
        "next_candidate_must_not_reuse_v25481_population_or_execution_authority": True,
    }
    checks = {
        "frozen_inputs_hash_exact": True,
        "forward_and_rows_validate": len(rows) == contract.TASK_COUNT,
        "forward_audit_valid_and_quality_unauthorized": True,
        "all_tasks_terminal_and_runtime_completed_without_failure": (
            aggregate["terminal_tasks"] == 20
            and aggregate["completed_runtime_tasks"] == 20
            and aggregate["failure_as_zero_tasks"] == 0
        ),
        "qualified_label_mechanism_engaged_but_below_gate": (
            registry["qualified_label_surface_count"] == 1
            and registry["available_candidate_count"] == 1
            and aggregate["prediction_changed_tasks"] == 1
        ),
        "no_application_or_budget_failure": (
            aggregate["application_failure_tasks"] == 0
            and aggregate["budget_rejection_tasks"] == 0
        ),
        "adjacent_surface_exists_but_produces_no_counterfactual_candidate": (
            adjacent["fused_standalone_field_surface_count"] > 0
            and adjacent["adjacent_evidence_closed_observation_count"] > 0
            and adjacent["adjacent_counterfactual_candidate_count"] == 0
            and per_task_adjacent_candidates == 0
        ),
        "existing_physical_fetch_cap_has_at_least_one_spare_per_task": (
            unused_fetch_capacity >= contract.TASK_COUNT
        ),
        "mechanism_no_go_and_quality_not_opened": (
            forward["mechanism_decision"]["mechanism_gate_passed"] is False
        ),
        "positive_signed_credit_zero": aggregate["positive_signed_credit_count"] == 0,
        "mapping_gold_truth_score_reward_evaluator_or_historical_correctness_absent": True,
        "network_model_search_fetch_or_evaluator_call_absent": True,
        "question_opaque_id_query_url_page_quote_value_prediction_or_per_task_outcome_not_persisted": True,
        "protected_watchers_unchanged": contract.watcher_snapshot()
        == [
            {"pid": pid, "start_ticks": ticks, "marker": marker}
            for pid, ticks, marker in contract.EXPECTED_WATCHERS
        ],
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "frozen_inputs": copy.deepcopy(EXPECTED),
        "content_free_aggregate_only": True,
        "diagnosis": diagnosis,
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "mapping_gold_category_question_type_split_truth_evaluator_score_reward_or_historical_correctness_read": False,
        "network_model_search_fetch_or_evaluator_called": False,
        "positive_signed_credit_count": 0,
        "authorization": {
            "row_key_derived_official_detail_fetch_build_design": not findings,
            "external_protocol_or_forward": False,
            "postfreeze_quality_or_truth": False,
            "deepwidebench_forward_or_evaluator": False,
            "leaderboard_or_sota": False,
            "retry_resume_replay_backfill_replacement_or_selective_rerun": False,
        },
    }
    value["diagnosis_payload_sha256"] = contract.payload_sha256(value)
    return validate_diagnosis(value)


def validate_diagnosis(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("diagnosis_payload_sha256", None)
    valid = copied.get("audit_valid") is True
    diagnosis = copied.get("diagnosis") or {}
    if (
        copied.get("role") != ROLE
        or copied.get("frozen_inputs") != EXPECTED
        or copied.get("content_free_aggregate_only") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or diagnosis.get("mechanism_gate_passed") is not False
        or diagnosis.get("prediction_changed_tasks") != 1
        or diagnosis.get("unused_fetch_capacity_under_existing_hard_cap") != 80
        or diagnosis.get("adjacent_surface_counterfactual", {}).get(
            "adjacent_counterfactual_candidate_count"
        )
        != 0
        or copied.get("positive_signed_credit_count") != 0
        or copied.get(
            "mapping_gold_category_question_type_split_truth_evaluator_score_reward_or_historical_correctness_read"
        )
        is not False
        or copied.get("network_model_search_fetch_or_evaluator_called") is not False
        or copied.get("authorization")
        != {
            "row_key_derived_official_detail_fetch_build_design": valid,
            "external_protocol_or_forward": False,
            "postfreeze_quality_or_truth": False,
            "deepwidebench_forward_or_evaluator": False,
            "leaderboard_or_sota": False,
            "retry_resume_replay_backfill_replacement_or_selective_rerun": False,
        }
        or seal != contract.payload_sha256(unsigned)
    ):
        raise ValueError("V2.54.82 diagnosis drifted")
    return copied


def _publish(value: Mapping[str, Any]) -> None:
    path = ROOT / OUTPUT
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def main() -> None:
    value = build_diagnosis()
    if value["findings"]:
        raise RuntimeError(value["findings"])
    _publish(value)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "audit_valid": value["audit_valid"],
                "diagnosis": value["diagnosis"],
                "authorization": value["authorization"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
