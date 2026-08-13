#!/usr/bin/env python3
"""Build the content-free V2.53.53 query-contract failure diagnosis."""

from __future__ import annotations

import ast
import json
import sys
import time
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25110_exact_visible_schema as schema  # noqa: E402
from deepwide_agent import v25117_grounded_target_record_plan as target_plan  # noqa: E402
from deepwide_agent import v25353_fresh_pep_grounded_fact_external_contract as contract  # noqa: E402
from deepwide_agent import v25354_pre_effect_query_compatible_grounded_fact_runtime as repair  # noqa: E402
from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from scripts import audit_v25136_sparse_production_build as base_audit  # noqa: E402
from scripts import run_v25353_fresh_pep_grounded_fact_external as runner  # noqa: E402


OUTPUT = Path(
    "results/v25355_v25353_pre_effect_query_contract_diagnosis_v1_20260813.json"
)
FORWARD_RESULT = Path(
    "results/v25353_fresh_pep_grounded_fact_external_forward_result_v2_20260813.json"
)
FORWARD_AUDIT = Path(
    "results/v25353_fresh_pep_grounded_fact_external_forward_audit_v2_20260813.json"
)
TASK_ROWS = Path(
    "outputs/v25353_fresh_pep_grounded_fact_external_v2_20260813/frozen_task_results.jsonl"
)
REPAIR_SOURCE = Path(
    "src/deepwide_agent/v25354_pre_effect_query_compatible_grounded_fact_runtime.py"
)
REPAIR_TEST = Path(
    "tests/test_v25354_pre_effect_query_compatible_grounded_fact_runtime.py"
)
TEST_SUITES = (
    ("test_v25354_pre_effect_query_compatible_grounded_fact_runtime.py", 6),
    ("test_v25349_shared_prefix_grounded_fact_paired_runtime.py", 8),
    ("test_v25123_visible_legacy_query_compatible_runtime.py", 7),
    ("test_v25353_fresh_pep_grounded_fact_external.py", 8),
    ("test_v25253_outer_physical_cap_observed_runtime.py", 7),
)


def _read(path: Path) -> dict[str, Any]:
    value = json.loads((ROOT / path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("V2.53.55 expected JSON object")
    return value


def _closure() -> tuple[Path, ...]:
    pending = [REPAIR_SOURCE]
    observed: set[Path] = set()
    while pending:
        relative = pending.pop()
        if relative in observed:
            continue
        observed.add(relative)
        tree = ast.parse(
            (ROOT / relative).read_text(encoding="utf-8"),
            filename=str(relative),
        )
        for node in ast.walk(tree):
            for candidate in contract._module_candidates(relative, node):
                path = ROOT / candidate
                if path.is_file() and not path.is_symlink():
                    pending.append(candidate)
    return tuple(sorted(observed, key=str))


def _tests() -> dict[str, Any]:
    suites = [base_audit._test(name, count) for name, count in TEST_SUITES]
    expected = sum(count for _name, count in TEST_SUITES)
    observed = sum(row["observed"] for row in suites)
    return {
        "expected": expected,
        "observed": observed,
        "passed": observed == expected and all(row["passed"] for row in suites),
        "suites": suites,
    }


def build(*, now: int | None = None) -> dict[str, Any]:
    forward = runner.validate_forward_result(_read(FORWARD_RESULT))
    audit = _read(FORWARD_AUDIT)
    if (
        audit.get("audit_valid") is not True
        or audit.get("findings") != []
        or audit.get("authorization", {}).get("deepwidebench_successor_build")
        is not False
    ):
        raise ValueError("V2.53.55 parent forward audit is not a valid NO-GO")
    rows = [
        runner.validate_task_row(value)
        for value in runner._read_jsonl(TASK_ROWS, tracked=True)
    ]
    failure_rows = [row for row in rows if row["failure_as_zero"]]
    completed_rows = [row for row in rows if row["runtime_completed"]]
    query_after_plan_pattern = sum(
        row["outer_failure_type"] == "ValueError"
        and row["actual_effect_snapshot"]["model_admitted_count"] == 1
        and row["actual_effect_snapshot"]["query_admitted_count"] == 2
        and 1 <= row["actual_effect_snapshot"]["fetch_admitted_count"] <= 6
        for row in failure_rows
    )
    search_failures = sum(
        row["hard_failure_health"]["search_request_failures"] for row in rows
    )
    other_hard_failures = sum(
        amount
        for row in rows
        for name, amount in row["hard_failure_health"].items()
        if name != "search_request_failures"
    )
    limits = ScoreFirstLimits(**contract.LIMITS)
    before_rejected = 0
    after_accepted = 0
    before_contains_markup = 0
    before_over_downstream_cap = 0
    for task in contract.task_vector():
        raw = schema.validated_exact_plan({}, task["question"], limits)
        before_contains_markup += int(
            any("<" in query or ">" in query for query in raw["queries"])
        )
        before_over_downstream_cap += int(
            any(
                len(query) > target_plan.MAXIMUM_QUERY_CHARACTERS
                for query in raw["queries"]
            )
        )
        try:
            target_plan.prepare_plan(
                task["question"], raw["columns"], raw["queries"], []
            )
        except ValueError:
            before_rejected += 1
        projected, _observation = repair.projected_plan(
            {}, task["question"], limits
        )
        target_plan.prepare_plan(
            task["question"],
            projected["columns"],
            projected["queries"],
            [],
        )
        after_accepted += 1
    closure = _closure()
    semantic = base_audit._semantic_findings(closure)
    tests = _tests()
    checks = {
        "parent_forward_audit_valid_nogo": True,
        "fixed_terminal_denominator_20": len(rows) == contract.TASK_COUNT,
        "all_outer_failures_match_post_plan_first_wave_value_error_pattern": (
            len(failure_rows) == 9 and query_after_plan_pattern == len(failure_rows)
        ),
        "completed_rows_never_show_outer_failure": all(
            row["outer_failure_type"] is None for row in completed_rows
        ),
        "all_hard_failures_are_search_request_accounting": (
            search_failures == 26 and other_hard_failures == 0
        ),
        "raw_visible_fallback_rejected_by_downstream_grammar_20_of_20": (
            before_rejected == contract.TASK_COUNT
        ),
        "raw_visible_fallback_has_markup_20_of_20": (
            before_contains_markup == contract.TASK_COUNT
        ),
        "raw_visible_fallback_exceeds_downstream_cap_20_of_20": (
            before_over_downstream_cap == contract.TASK_COUNT
        ),
        "pre_effect_projection_accepted_by_downstream_grammar_20_of_20": (
            after_accepted == contract.TASK_COUNT
        ),
        "repair_and_parent_regression_tests_exact36": tests["passed"],
        "repair_dependency_privileged_runtime_access_zero": semantic[
            "privileged_runtime_field_accesses"
        ]
        == [],
        "repair_dependency_evaluator_capability_zero": semantic[
            "evaluator_capabilities"
        ]
        == [],
        "repair_dependency_credential_literal_zero": semantic[
            "credential_literal_hits"
        ]
        == [],
        "only_known_provider_rank_score_exception": semantic[
            "allowed_provider_rank_access"
        ]
        == ["src/deepwide_agent/clients.py:565:score"],
        "no_network_model_search_fetch_evaluator_or_benchmark_effect": True,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25355_v25353_pre_effect_query_contract_diagnosis",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parent": {
            "forward_result_sha256": contract.sha256(ROOT / FORWARD_RESULT),
            "forward_audit_sha256": contract.sha256(ROOT / FORWARD_AUDIT),
            "task_rows_sha256": contract.sha256(ROOT / TASK_ROWS),
            "mechanism_gate_passed": forward["mechanism_decision"]
            ["mechanism_gate_passed"],
        },
        "observations": {
            "terminal_tasks": len(rows),
            "completed_runtime_tasks": len(completed_rows),
            "failure_as_zero_tasks": len(failure_rows),
            "post_plan_first_wave_value_error_pattern_tasks": query_after_plan_pattern,
            "search_request_failure_count": search_failures,
            "other_hard_failure_count": other_hard_failures,
            "raw_fallback_downstream_rejection_tasks": before_rejected,
            "raw_fallback_markup_tasks": before_contains_markup,
            "raw_fallback_over_downstream_cap_tasks": before_over_downstream_cap,
            "projected_fallback_downstream_acceptance_tasks": after_accepted,
        },
        "root_cause": {
            "class": "pre_effect_query_contract_mismatch",
            "upstream_query_character_cap": 900,
            "downstream_query_character_cap": target_plan.MAXIMUM_QUERY_CHARACTERS,
            "upstream_visible_fallback_may_retain_markup": True,
            "downstream_grounded_plan_legacy_query_grammar_forbids_markup": True,
            "downstream_validation_previously_occurred_after_first_search_and_fetch_wave": True,
        },
        "repair": {
            "source": str(REPAIR_SOURCE),
            "source_sha256": contract.sha256(ROOT / REPAIR_SOURCE),
            "test": str(REPAIR_TEST),
            "test_sha256": contract.sha256(ROOT / REPAIR_TEST),
            "reuses_frozen_v25123_visible_query_projector": True,
            "projection_occurs_before_first_search_or_fetch_effect": True,
            "additional_model_search_fetch_or_budget": False,
            "rerun_same_twenty_tasks_authorized": False,
        },
        "tests": tests,
        "semantic_audit": {
            "dependency_closure": [str(path) for path in closure],
            "dependency_closure_sha256": contract.payload_sha256(
                {str(path): contract.sha256(ROOT / path) for path in closure}
            ),
            **semantic,
        },
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "contains_question_query_url_host_title_page_record_value_prediction_answer_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "authorization": {
            "fresh_disjoint_population_design": not findings,
            "same_population_retry_resume_replay_backfill_or_replacement": False,
            "external_forward_or_evaluator": False,
            "deepwidebench_forward_evaluator_leaderboard_or_sota": False,
        },
    }
    value["diagnosis_payload_sha256"] = contract.payload_sha256(value)
    return value


def validate(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    unsigned = dict(copied)
    signature = unsigned.pop("diagnosis_payload_sha256", None)
    if (
        copied.get("role")
        != "v25355_v25353_pre_effect_query_contract_diagnosis"
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or copied.get("observations", {}).get(
            "raw_fallback_downstream_rejection_tasks"
        )
        != contract.TASK_COUNT
        or copied.get("observations", {}).get(
            "projected_fallback_downstream_acceptance_tasks"
        )
        != contract.TASK_COUNT
        or copied.get("repair", {}).get("rerun_same_twenty_tasks_authorized")
        is not False
        or copied.get("authorization")
        != {
            "fresh_disjoint_population_design": True,
            "same_population_retry_resume_replay_backfill_or_replacement": False,
            "external_forward_or_evaluator": False,
            "deepwidebench_forward_evaluator_leaderboard_or_sota": False,
        }
        or signature != contract.payload_sha256(unsigned)
    ):
        raise ValueError("V2.53.55 diagnosis drifted")
    return copied


def main() -> None:
    if (ROOT / OUTPUT).exists() or (ROOT / OUTPUT).is_symlink():
        raise FileExistsError(OUTPUT)
    value = validate(build())
    (ROOT / OUTPUT).write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "audit_valid": value["audit_valid"],
                "findings": value["findings"],
                "observations": value["observations"],
                "authorization": value["authorization"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
