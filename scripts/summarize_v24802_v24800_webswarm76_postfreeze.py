#!/usr/bin/env python3
"""Post-freeze aggregate comparison on WebSwarm's public 76-task manifest.

The V2.48.00 exact-220 forward, prediction freeze, official evaluation, and
post-result audit are terminal before this program opens the external subset
manifest.  Instance IDs are used only for an in-memory join.  The published
artifact contains no task ID, question, prediction, answer, query, URL, page,
credential, or per-task metric and grants no benchmark execution authority.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import time
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24800_exact220_contract as contract  # noqa: E402
from scripts import finalize_v24800_exact220 as finalizer  # noqa: E402


OUTPUT = Path(
    "results/v24802_v24800_webswarm76_postfreeze_aggregate_v1_20260807.json"
)
DEFAULT_SUBSET = Path(
    ".research/tmp/webswarm/task_manager/benchmark/deepwidesearch/"
    "data/deepwidesearch_en_subset.jsonl"
)
WEBSWARM_REPOSITORY_COMMIT = "40c9aacad7cd6e9cdb3e7add954d59b766425717"
WEBSWARM_SUBSET_SHA256 = (
    "13de7dbe7cdd287e48ebbd8053bbfb8d6326ff804bba2dcf38bdc48c423df560"
)
WEBSWARM_ARXIV_ID = "2607.08662v1"
SELECTED = 76
QUALITY_METRICS = (
    "score",
    "entity_acc",
    "f1_by_row",
    "f1_by_item",
    "column_f1",
)
COMPOSITE_METRICS = ("entity_acc", "f1_by_row", "f1_by_item", "column_f1")
PUBLIC_INSTANCE_ID = re.compile(r"(?:deep2wide_result_|wide2deep_ws_)")
OPAQUE_ID = re.compile(r"task_[0-9a-f]{24}")
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}"
)


def _ordinary(path: Path) -> Path:
    resolved = path.resolve()
    if (
        path.is_symlink()
        or not path.is_file()
        or not resolved.is_relative_to(ROOT.resolve())
    ):
        raise RuntimeError(f"V2.48.02 expected ordinary repository-local file: {path}")
    return path


def _read_object(path: Path) -> dict[str, Any]:
    value = json.loads(_ordinary(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.48.02 expected JSON object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == contract.payload_sha256(unsigned)


def _validate_terminal_parent() -> tuple[dict[str, Any], dict[str, Any]]:
    result = _read_object(ROOT / finalizer.FINAL_RESULT)
    post = _read_object(ROOT / finalizer.POSTAUDIT)
    summary = _read_object(ROOT / finalizer.SUMMARY)
    if (
        result.get("role") != "v24800_exact220_result"
        or result.get("status") != "exact220_single_rollout_complete"
        or result.get("selected") != 220
        or result.get("exact220_prediction_freeze_before_evaluator") is not True
        or result.get("source_policy", {}).get("runtime_boundary")
        != ["opaque_id", "question"]
        or not _sealed(result, "result_payload_sha256")
        or post.get("audit_valid") is not True
        or post.get("findings") != []
        or not _sealed(post, "audit_payload_sha256")
        or post.get("checks", {}).get("forward_barrier_exact220") is not True
        or post.get("checks", {}).get("joined_official_merged_rows_exact220")
        is not True
        or post.get("checks", {}).get("mapping_and_evaluator_closed_during_forward")
        is not True
        or post.get("checks", {}).get("no_selective_retry_or_revaluation")
        is not True
        or post.get("provenance", {}).get("conservative_summary_sha256")
        != contract.sha256(ROOT / finalizer.SUMMARY)
        or len(summary.get("per_task") or []) != 220
    ):
        raise RuntimeError("V2.48.02 terminal parent chain drifted")
    return result, summary


def _read_subset(path: Path) -> tuple[set[str], dict[str, int]]:
    path = _ordinary(path)
    if contract.sha256(path) != WEBSWARM_SUBSET_SHA256:
        raise RuntimeError("V2.48.02 WebSwarm subset bytes drifted")
    identifiers: set[str] = set()
    languages: Counter[str] = Counter()
    rows = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise RuntimeError("V2.48.02 WebSwarm subset row is not an object")
        identifier = value.get("instance_id")
        language = value.get("language")
        if (
            not isinstance(identifier, str)
            or not identifier
            or identifier in identifiers
            or language not in {"en", "zh"}
        ):
            raise RuntimeError("V2.48.02 WebSwarm subset schema drifted")
        identifiers.add(identifier)
        languages[str(language)] += 1
        rows += 1
    if rows != SELECTED or len(identifiers) != SELECTED:
        raise RuntimeError("V2.48.02 WebSwarm subset denominator drifted")
    return identifiers, dict(sorted(languages.items()))


def _project_rows(
    summary: Mapping[str, Any], identifiers: set[str]
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in summary.get("per_task") or []:
        identifier = row.get("instance_id")
        if identifier not in identifiers:
            continue
        metrics = row.get("metrics") or {}
        cost = row.get("cost") or {}
        if (
            not isinstance(identifier, str)
            or identifier in seen
            or any(
                isinstance(metrics.get(name), bool)
                or not isinstance(metrics.get(name), (int, float))
                or not math.isfinite(float(metrics[name]))
                for name in QUALITY_METRICS
            )
            or not isinstance(row.get("evaluator_valid"), bool)
            or any(
                isinstance(cost.get(name), bool)
                or not isinstance(cost.get(name), (int, float))
                or not math.isfinite(float(cost[name]))
                or float(cost[name]) < 0
                for name in (
                    "system_total_tokens",
                    "search_calls",
                    "search_fetch_calls",
                )
            )
            or isinstance(row.get("elapsed_seconds"), bool)
            or not isinstance(row.get("elapsed_seconds"), (int, float))
            or not math.isfinite(float(row["elapsed_seconds"]))
            or float(row["elapsed_seconds"]) < 0
        ):
            raise RuntimeError("V2.48.02 frozen evaluator projection drifted")
        seen.add(identifier)
        output.append(
            {
                "evaluator_valid": row["evaluator_valid"],
                "metrics": {
                    name: float(metrics[name]) for name in QUALITY_METRICS
                },
                "system_total_tokens": int(cost["system_total_tokens"]),
                "search_calls": int(cost["search_calls"]),
                "fetch_calls": int(cost["search_fetch_calls"]),
                "elapsed_seconds": float(row["elapsed_seconds"]),
            }
        )
    if seen != identifiers or len(output) != SELECTED:
        raise RuntimeError("V2.48.02 subset is not an exact subset of frozen exact220")
    return output


def _aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    metrics = {
        name: sum(row["metrics"][name] for row in rows) / SELECTED
        for name in QUALITY_METRICS
    }
    metrics["quality_composite"] = sum(
        metrics[name] for name in COMPOSITE_METRICS
    ) / len(COMPOSITE_METRICS)
    return {
        "selected": SELECTED,
        "evaluator_valid": sum(row["evaluator_valid"] is True for row in rows),
        "evaluator_invalid_failure_as_zero": sum(
            row["evaluator_valid"] is False for row in rows
        ),
        "whole_table_successes": sum(
            row["metrics"]["score"] > 0 for row in rows
        ),
        "metrics": metrics,
        "cost": {
            "system_total_tokens": sum(row["system_total_tokens"] for row in rows),
            "search_calls": sum(row["search_calls"] for row in rows),
            "fetch_calls": sum(row["fetch_calls"] for row in rows),
            "task_wall_seconds_sum": sum(row["elapsed_seconds"] for row in rows),
            "mean_search_calls_per_task": sum(
                row["search_calls"] for row in rows
            )
            / SELECTED,
            "mean_fetch_calls_per_task": sum(row["fetch_calls"] for row in rows)
            / SELECTED,
        },
    }


def build_report(
    *, subset_path: Path = DEFAULT_SUBSET, now: int | None = None
) -> dict[str, Any]:
    result, summary = _validate_terminal_parent()
    identifiers, languages = _read_subset(ROOT / subset_path)
    aggregate = _aggregate(_project_rows(summary, identifiers))
    paper = {
        "system": "WebSwarm",
        "backbone": "GLM-4.5",
        "selected": SELECTED,
        "reported_success_rate": 0.0658,
        "reported_row_f1": 0.2964,
        "reported_item_f1": 0.5840,
        "reported_mean_web_tool_calls": 203.73,
        "reported_metrics_are_rounded_from_paper_table": True,
        "entity_column_or_composite_not_reported": True,
    }
    ours = aggregate["metrics"]
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24802_v24800_webswarm76_aggregate_only_postfreeze_comparison",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "same_manifest_descriptive_comparison_not_matched_or_sota",
        "parents": {
            "v24800_result_sha256": contract.sha256(ROOT / finalizer.FINAL_RESULT),
            "v24800_postresult_audit_sha256": contract.sha256(
                ROOT / finalizer.POSTAUDIT
            ),
            "v24800_conservative_summary_sha256": contract.sha256(
                ROOT / finalizer.SUMMARY
            ),
        },
        "external_source": {
            "repository": "songxiaoshuai/WebSwarm",
            "repository_commit": WEBSWARM_REPOSITORY_COMMIT,
            "subset_relative_path": (
                "task_manager/benchmark/deepwidesearch/data/"
                "deepwidesearch_en_subset.jsonl"
            ),
            "subset_sha256": WEBSWARM_SUBSET_SHA256,
            "subset_rows": SELECTED,
            "subset_language_field_counts": languages,
            "subset_label_in_repository": "en_subset",
            "subset_label_and_language_fields_opened_postfreeze_only": True,
            "arxiv_id": WEBSWARM_ARXIV_ID,
        },
        "v24800_same_manifest": aggregate,
        "webswarm_paper_report": paper,
        "descriptive_delta_from_paper_report": {
            "success_rate": ours["score"] - paper["reported_success_rate"],
            "row_f1": ours["f1_by_row"] - paper["reported_row_f1"],
            "item_f1": ours["f1_by_item"] - paper["reported_item_f1"],
            "success_rate_equal_at_two_decimal_percentage_precision": round(
                100 * ours["score"], 2
            )
            == round(100 * paper["reported_success_rate"], 2),
        },
        "comparability": {
            "same_exact_public_task_manifest": True,
            "same_model_backbone": False,
            "same_agent_or_prompt": False,
            "same_search_and_page_tool_implementation": False,
            "same_budget_or_action_cap": False,
            "same_evaluator_implementation_proven": False,
            "web_tool_call_definition_comparable": False,
            "randomized_or_matched_cost_comparison": False,
            "fair_system_ranking_established": False,
            "leaderboard_or_sota_established": False,
        },
        "boundary": {
            "exact220_forward_prediction_freeze_evaluation_and_audit_terminal_before_subset_open": True,
            "external_manifest_used_only_for_postfreeze_in_memory_membership_join": True,
            "instance_id_question_prediction_answer_query_url_page_or_credential_emitted": False,
            "per_task_metric_or_membership_emitted": False,
            "network_model_search_fetch_or_evaluator_called": False,
            "same_run_forward_feedback_or_prediction_selection": False,
            "retry_resume_skip_or_selective_revaluation": False,
            "subset_membership_must_not_feed_future_public_benchmark_routing": True,
        },
        "claims": {
            "v24800_matches_webswarm_reported_success_rate_at_reported_precision": True,
            "v24800_row_f1_is_higher_on_same_manifest_descriptively": True,
            "v24800_item_f1_is_lower_on_same_manifest_descriptively": True,
            "webswarm_outperformed_under_matched_conditions": False,
            "v24800_outperformed_under_matched_conditions": False,
            "entropy_or_credit_assignment_validated": False,
            "external_sota": False,
        },
        "authorization": {
            "documentation_update": True,
            "new_public_dev64": False,
            "new_public_exact220": False,
            "leaderboard_submission": False,
            "sota_claim": False,
        },
    }
    checks = {
        "terminal_parent_chain_valid": result.get("selected") == 220,
        "subset_denominator_exact76": aggregate["selected"] == SELECTED,
        "subset_all_present_in_frozen_exact220": True,
        "subset_language_counts_reconcile": sum(languages.values()) == SELECTED,
        "fixed_failure_as_zero_denominator": (
            aggregate["evaluator_valid"]
            + aggregate["evaluator_invalid_failure_as_zero"]
            == SELECTED
        ),
        "whole_table_count_reconciles": aggregate["whole_table_successes"] == 5,
        "reported_precision_success_rate_reconciles": round(
            100 * ours["score"], 2
        )
        == 6.58,
    }
    value["checks"] = checks
    value["findings"] = sorted(name for name, passed in checks.items() if not passed)
    value["audit_valid"] = not value["findings"]
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True)
    if (
        OPAQUE_ID.search(encoded)
        or PUBLIC_INSTANCE_ID.search(encoded)
        or SECRET.search(encoded)
    ):
        raise RuntimeError("V2.48.02 emitted prohibited task or credential content")
    value["report_payload_sha256"] = contract.payload_sha256(value)
    return validate_report(value)


def validate_report(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    unsigned = dict(copied)
    seal = unsigned.pop("report_payload_sha256", None)
    if (
        copied.get("role")
        != "v24802_v24800_webswarm76_aggregate_only_postfreeze_comparison"
        or copied.get("status")
        != "same_manifest_descriptive_comparison_not_matched_or_sota"
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or copied.get("comparability", {}).get("fair_system_ranking_established")
        is not False
        or copied.get("claims", {}).get("entropy_or_credit_assignment_validated")
        is not False
        or copied.get("authorization")
        != {
            "documentation_update": True,
            "new_public_dev64": False,
            "new_public_exact220": False,
            "leaderboard_submission": False,
            "sota_claim": False,
        }
        or seal != contract.payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.48.02 aggregate report drifted")
    return copied


def publish(path: Path, value: Mapping[str, Any]) -> None:
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
    parser.add_argument("--subset", type=Path, default=DEFAULT_SUBSET)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    report = build_report(subset_path=args.subset)
    publish(ROOT / args.output, report)
    print(
        json.dumps(
            {
                "path": str(args.output),
                "selected": report["v24800_same_manifest"]["selected"],
                "whole_table_successes": report["v24800_same_manifest"][
                    "whole_table_successes"
                ],
                "metrics": report["v24800_same_manifest"]["metrics"],
                "authorization": report["authorization"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
