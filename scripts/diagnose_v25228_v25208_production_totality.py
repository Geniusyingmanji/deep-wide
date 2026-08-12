#!/usr/bin/env python3
"""Content-free production-totality diagnosis for frozen V2.52.08.

Only four top-level runtime status fields and one statically named nested
V2.51.70 observation are decoded.  Every other JSON value, including task
identity, question, prediction, pages, and parent results, is skipped
lexically.  The resulting aggregate cannot route a future benchmark task or
authorize a retry, evaluation, runtime change, or new exact-220 run.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import sys
import time
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import (  # noqa: E402
    v25170_production_normalizer_disposition_observer as observation,
)
from scripts import diagnose_v25063_three_run_output_structure as lexical  # noqa: E402
from scripts import diagnose_v25209_v25208_exact220 as parent  # noqa: E402


DATE = "20260812"
ROLE = "v25228_v25208_production_totality_aggregate_diagnosis"
OUTPUT = Path(
    f"results/v25228_v25208_production_totality_diagnosis_v1_{DATE}.json"
)
SOURCE = Path("scripts/diagnose_v25228_v25208_production_totality.py")
TEST = Path("tests/test_diagnose_v25228_v25208_production_totality.py")
RUNTIME = Path(
    f"outputs/v25208_quote_aware_exact220_r2_{DATE}/frozen_task_results.jsonl"
)
PARENT_DIAGNOSIS = Path(
    f"results/v25209_v25208_exact220_reliability_diagnosis_v1_{DATE}.json"
)
POSTAUDIT = Path(
    f"results/v25208_quote_aware_exact220_postresult_audit_r2_{DATE}.json"
)
EXPECTED_SHA256 = {
    "runtime": "ea56b3966db6ffb003769061a13660e9ea3f1edeeca2ec4c9d2ee97dd6e575f5",
    "parent_diagnosis": "1dee7aea4bf5d7ab2c3fa9427c62ae6149aa25545ece38571cfcc428ed7ea163",
    "postaudit": "360b655a083e1971b4d093906bea9ceb6d963a3a851fc8506821325e73b664e0",
}
TOP_LEVEL_FIELDS = frozenset(
    {"runtime_completed", "failure_as_zero", "prediction_kind", "failure_types"}
)
OBSERVATION_PATH = (
    "parent_result",
    "content_free_receipt",
    "raw_normalizer_observation",
)


def _selected_nested_value(text: str, path: Sequence[str]) -> Any:
    """Decode one fixed nested value while skipping all siblings lexically."""

    requested = tuple(path)
    if not requested or any(not isinstance(key, str) or not key for key in requested):
        raise ValueError("V2.52.28 nested path drifted")

    def descend(fragment: str, depth: int) -> Any:
        position = lexical._skip_ws(fragment, 0)
        if position >= len(fragment) or fragment[position] != "{":
            raise ValueError("V2.52.28 expected nested JSON object")
        position += 1
        seen: set[str] = set()
        selected: str | None = None
        while True:
            position = lexical._skip_ws(fragment, position)
            if position < len(fragment) and fragment[position] == "}":
                position = lexical._skip_ws(fragment, position + 1)
                if position != len(fragment):
                    raise ValueError("V2.52.28 trailing nested JSON content")
                break
            key, key_end = lexical._DECODER.raw_decode(fragment, position)
            if not isinstance(key, str) or key in seen:
                raise ValueError("V2.52.28 invalid nested JSON key")
            seen.add(key)
            position = lexical._skip_ws(fragment, key_end)
            if position >= len(fragment) or fragment[position] != ":":
                raise ValueError("V2.52.28 missing nested JSON colon")
            start = lexical._skip_ws(fragment, position + 1)
            end = lexical._value_end(fragment, start)
            if key == requested[depth]:
                if selected is not None:
                    raise ValueError("V2.52.28 duplicate selected nested key")
                selected = fragment[start:end]
            position = lexical._skip_ws(fragment, end)
            if position < len(fragment) and fragment[position] == ",":
                position += 1
                continue
            if position < len(fragment) and fragment[position] == "}":
                continue
            raise ValueError("V2.52.28 invalid nested JSON delimiter")
        if selected is None:
            raise ValueError("V2.52.28 selected nested path is absent")
        if depth + 1 == len(requested):
            return json.loads(selected)
        return descend(selected, depth + 1)

    return descend(str(text).strip(), 0)


def _parents() -> dict[str, str]:
    observed = {
        "runtime": parent.sha256(RUNTIME),
        "parent_diagnosis": parent.sha256(PARENT_DIAGNOSIS),
        "postaudit": parent.sha256(POSTAUDIT),
    }
    if observed != EXPECTED_SHA256:
        raise RuntimeError("V2.52.28 frozen parent hash drifted")
    diagnosis = json.loads(parent._ordinary(PARENT_DIAGNOSIS).read_text(encoding="utf-8"))
    postaudit = lexical.selected_top_level_fields(
        parent._ordinary(POSTAUDIT).read_text(encoding="utf-8"),
        frozenset({"audit_valid", "findings"}),
    )
    if (
        parent.validate_diagnosis(diagnosis) != diagnosis
        or postaudit != {"audit_valid": True, "findings": []}
    ):
        raise RuntimeError("V2.52.28 frozen parent validation drifted")
    return observed


def _aggregate() -> dict[str, Any]:
    runtime_rows = 0
    selected_rows = 0
    dispositions: Counter[str] = Counter()
    structural: Counter[str] = Counter()
    truncated = 0
    accepted = 0
    for line in parent._ordinary(RUNTIME).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        runtime_rows += 1
        top = lexical.selected_top_level_fields(line, TOP_LEVEL_FIELDS)
        failure_types = top.get("failure_types")
        if (
            top.get("runtime_completed") is not True
            or top.get("failure_as_zero") is not False
            or top.get("prediction_kind") != "fallback"
            or not isinstance(failure_types, Mapping)
            or failure_types.get("production") != "ValueError"
        ):
            continue
        selected_rows += 1
        raw = _selected_nested_value(line, OBSERVATION_PATH)
        if not isinstance(raw, Mapping):
            raise RuntimeError("V2.52.28 selected observation is not an object")
        checked = observation.validate_observation(raw)
        active = [
            name
            for name, count in checked["disposition_counts"].items()
            if count == 1
        ]
        if len(active) != 1:
            raise RuntimeError("V2.52.28 disposition accounting drifted")
        dispositions[active[0]] += 1
        for name in observation.COUNT_NAMES:
            structural[name] += int(checked[name])
        truncated += int(checked["provider_output_truncated"])
        accepted += int(checked["frozen_synthesis_contract_accepted"])
    if runtime_rows != 220 or selected_rows != 5:
        raise RuntimeError("V2.52.28 fixed denominator drifted")
    output = {
        "runtime_rows": runtime_rows,
        "completed_production_value_error_tasks": selected_rows,
        "disposition_counts": {
            name: int(dispositions[name]) for name in observation.DISPOSITION_NAMES
        },
        "structural_count_totals": {
            name: int(structural[name]) for name in observation.COUNT_NAMES
        },
        "provider_output_truncated_tasks": truncated,
        "frozen_synthesis_contract_accepted_tasks": accepted,
    }
    if (
        sum(output["disposition_counts"].values()) != selected_rows
        or output["disposition_counts"]["no_bindable_header_reject"] != 4
        or output["disposition_counts"]["missing_data_rows_reject"] != 1
        or truncated != 0
        or accepted != 0
    ):
        raise RuntimeError("V2.52.28 expected anonymous localization drifted")
    return output


def build_diagnosis(*, now: int | None = None) -> dict[str, Any]:
    parents = _parents()
    aggregate = _aggregate()
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parents": parents,
        "aggregate": aggregate,
        "diagnosis": {
            "four_of_five_production_fallbacks_stop_at_header_binding": True,
            "one_of_five_production_fallbacks_has_no_data_rows": True,
            "provider_truncation_explains_these_fallbacks": False,
            "escaped_pipe_or_malformed_row_explains_these_fallbacks": False,
            "quote_aware_successor_is_the_right_next_reliability_target": False,
            "missing_data_rows_remain_fail_closed": True,
            "safe_header_totality_successor_requires_synthetic_adversarial_proof": True,
            "old_fullset_receipts_prove_successor_recovery_coverage": False,
            "fresh_artifact_disjoint_reliability_gate_required": True,
        },
        "content_policy": {
            "top_level_fields_decoded": sorted(TOP_LEVEL_FIELDS),
            "only_nested_path_decoded": list(OBSERVATION_PATH),
            "all_sibling_values_skipped_lexically": True,
            "task_identity_question_page_prediction_gold_category_split_metric_or_score_decoded_or_emitted": False,
            "historical_outcome_used_as_future_runtime_router_signal": False,
            "credential_value_read_hashed_persisted_or_emitted": False,
        },
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "authorization": {
            "aggregate_production_totality_diagnosis": True,
            "synthetic_header_totality_successor_design_only": True,
            "runtime_integration_or_prediction_change": False,
            "fresh_external_protocol_or_launch": False,
            "retry_resume_replacement_selective_rerun_or_revaluation": False,
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
        },
    }
    value["diagnosis_payload_sha256"] = parent.payload_sha256(value)
    return validate_diagnosis(value)


def validate_diagnosis(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("diagnosis_payload_sha256", None)
    aggregate = copied.get("aggregate") or {}
    dispositions = aggregate.get("disposition_counts") or {}
    structural = aggregate.get("structural_count_totals") or {}
    diagnosis = copied.get("diagnosis") or {}
    policy = copied.get("content_policy") or {}
    authorization = copied.get("authorization") or {}
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "created_at_unix",
            "parents",
            "aggregate",
            "diagnosis",
            "content_policy",
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
            "network_model_search_fetch_evaluator_benchmark_or_api_called",
            "entropy_or_information_gain_assigns_signed_credit",
            "authorization",
            "diagnosis_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("parents") != EXPECTED_SHA256
        or aggregate.get("runtime_rows") != 220
        or aggregate.get("completed_production_value_error_tasks") != 5
        or set(dispositions) != set(observation.DISPOSITION_NAMES)
        or sum(dispositions.values()) != 5
        or dispositions.get("no_bindable_header_reject") != 4
        or dispositions.get("missing_data_rows_reject") != 1
        or any(
            value
            for name, value in dispositions.items()
            if name not in {"no_bindable_header_reject", "missing_data_rows_reject"}
        )
        or structural
        != {
            "pipe_group_count": 5,
            "separator_row_count": 5,
            "header_bound_separator_count": 1,
            "width_bound_separator_count": 1,
            "data_bearing_separator_count": 0,
            "malformed_candidate_count": 0,
            "normalizer_candidate_count": 0,
        }
        or aggregate.get("provider_output_truncated_tasks") != 0
        or aggregate.get("frozen_synthesis_contract_accepted_tasks") != 0
        or any(
            diagnosis.get(name) is not True
            for name in (
                "four_of_five_production_fallbacks_stop_at_header_binding",
                "one_of_five_production_fallbacks_has_no_data_rows",
                "missing_data_rows_remain_fail_closed",
                "safe_header_totality_successor_requires_synthetic_adversarial_proof",
                "fresh_artifact_disjoint_reliability_gate_required",
            )
        )
        or any(
            diagnosis.get(name) is not False
            for name in (
                "provider_truncation_explains_these_fallbacks",
                "escaped_pipe_or_malformed_row_explains_these_fallbacks",
                "quote_aware_successor_is_the_right_next_reliability_target",
                "old_fullset_receipts_prove_successor_recovery_coverage",
            )
        )
        or policy
        != {
            "top_level_fields_decoded": sorted(TOP_LEVEL_FIELDS),
            "only_nested_path_decoded": list(OBSERVATION_PATH),
            "all_sibling_values_skipped_lexically": True,
            "task_identity_question_page_prediction_gold_category_split_metric_or_score_decoded_or_emitted": False,
            "historical_outcome_used_as_future_runtime_router_signal": False,
            "credential_value_read_hashed_persisted_or_emitted": False,
        }
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
        )
        is not False
        or copied.get("network_model_search_fetch_evaluator_benchmark_or_api_called")
        is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit") is not False
        or authorization
        != {
            "aggregate_production_totality_diagnosis": True,
            "synthetic_header_totality_successor_design_only": True,
            "runtime_integration_or_prediction_change": False,
            "fresh_external_protocol_or_launch": False,
            "retry_resume_replacement_selective_rerun_or_revaluation": False,
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
        }
        or seal != parent.payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.28 production-totality diagnosis drifted")
    return copied


def publish_exclusive(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("diagnose",))
    args = parser.parse_args()
    if args.command == "diagnose":
        value = build_diagnosis()
        publish_exclusive(ROOT / OUTPUT, value)
        print(
            json.dumps(
                {
                    "path": str(OUTPUT),
                    "production_value_error_tasks": value["aggregate"][
                        "completed_production_value_error_tasks"
                    ],
                    "no_bindable_header_reject": value["aggregate"][
                        "disposition_counts"
                    ]["no_bindable_header_reject"],
                    "new_exact220_launch": value["authorization"][
                        "fresh_external_protocol_or_launch"
                    ],
                },
                sort_keys=True,
            )
        )


if __name__ == "__main__":
    main()
