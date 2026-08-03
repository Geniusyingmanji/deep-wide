#!/usr/bin/env python3
"""Finalize the preregistered neutral V2.42.90 rescue gate."""

from __future__ import annotations

import json
import os
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import preregister_v24290_neutral_low_coverage as prereg  # noqa: E402
from scripts import probe_v24290_neutral_low_coverage as probe  # noqa: E402
from scripts.run_v24257_score_first_smoke import payload_sha256, sha256  # noqa: E402


OUTPUT = prereg.DECISION


def _ordinary(root: Path, relative: Path) -> Path:
    path = root / relative
    if relative.is_absolute() or ".." in relative.parts or path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root):
        raise RuntimeError(f"V2.42.90 finalizer expected ordinary file: {relative}")
    return path


def _checks(result: Mapping[str, Any], gates: Mapping[str, Any]) -> dict[str, bool]:
    coverage = result["coverage"]
    controller = result["controller"]
    health = result["runtime_health"]
    table = result["table_shape"]
    timing = result["attributed_timing"]
    return {
        "wall_seconds": float(result["wall_seconds"]) <= float(gates["maximum_wall_seconds"]),
        "completion_kind": result["completion_kind"] in gates["required_completion_kinds"],
        "controller_decision": controller["decision"] == gates["required_controller_decision"],
        "rescue_triggered": coverage["rescue_triggered"] is gates["required_rescue_triggered"],
        "rescue_fetches": int(coverage["rescue_fetches"]) >= int(gates["minimum_rescue_fetches"]),
        "rescue_usable_pages": int(coverage["rescue_usable_pages"]) >= int(gates["minimum_rescue_usable_pages"]),
        "usable_pages_strictly_increased": int(coverage["usable_pages_after_rescue"]) > int(coverage["usable_pages_before_rescue"]),
        "content_chars_strictly_increased": int(coverage["content_chars_after_rescue"]) > int(coverage["content_chars_before_rescue"]),
        "total_fetches": int(coverage["fetches_after_rescue"]) <= int(gates["maximum_total_fetches"]),
        "total_queries": int(coverage["queries_executed"]) <= int(gates["maximum_total_queries"]),
        "no_added_hosted_search_request": int(controller["hosted_search_requests_added_by_rescue"]) <= int(gates["maximum_hosted_search_requests_added_by_rescue"]),
        "provider_search_calls_unchanged": controller["provider_search_calls_before_rescue"] == controller["provider_search_calls_after_rescue"],
        "cache_misses": int(health["cache_miss_count"]) <= int(gates["maximum_cache_misses"]),
        "cache_serve_network_fetches": int(health["network_fetches_during_cache_serve"]) <= int(gates["maximum_cache_serve_network_fetches"]),
        "provider_fetch_calls_match_receipt": health["provider_fetch_calls_match_receipt"] is True,
        "output_rows": int(table["row_count"]) >= int(gates["minimum_output_rows"]),
        "output_columns": int(table["column_count"]) == int(gates["required_output_columns"]),
        "timing_additivity": timing["timings_are_additive_not_parallel_work_sum"] is gates["timing_additivity_required"],
        "deadline_not_exceeded": result["budget"]["deadline_exceeded_at_return"] is False,
    }


def build_decision(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    protocol = prereg.validate_protocol(root)
    result_path = _ordinary(root, prereg.RESULT)
    result = json.loads(result_path.read_text(encoding="utf-8"))
    probe.validate_projection(result)
    checks = _checks(result, protocol["gates"])
    failed = sorted(name for name, passed in checks.items() if not passed)
    passed = not failed
    value = {
        "artifact_version": 1,
        "role": "v24290_neutral_low_coverage_decision",
        "protocol_id": prereg.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "neutral_mechanism_go" if passed else "neutral_mechanism_no_go",
        "passed": passed,
        "checks": checks,
        "failed_checks": failed,
        "observed": {
            "wall_seconds": result["wall_seconds"],
            "completion_kind": result["completion_kind"],
            "controller_decision": result["controller"]["decision"],
            "rescue_triggered": result["coverage"]["rescue_triggered"],
            "hosted_search_requests_added_by_rescue": result["controller"]["hosted_search_requests_added_by_rescue"],
            "fetches_before_rescue": result["coverage"]["fetches_before_rescue"],
            "fetches_after_rescue": result["coverage"]["fetches_after_rescue"],
            "usable_pages_before_rescue": result["coverage"]["usable_pages_before_rescue"],
            "usable_pages_after_rescue": result["coverage"]["usable_pages_after_rescue"],
            "content_chars_before_rescue": result["coverage"]["content_chars_before_rescue"],
            "content_chars_after_rescue": result["coverage"]["content_chars_after_rescue"],
            "table_rows": result["table_shape"]["row_count"],
            "table_columns": result["table_shape"]["column_count"],
        },
        "provenance": {
            "protocol_sha256": sha256(root / prereg.OUTPUT),
            "result_sha256": sha256(result_path),
            "surface_manifest_sha256": protocol["surface_manifest_sha256"],
        },
        "claim_scope": {
            "fault_injected_mechanism_robustness": True,
            "natural_trigger_frequency_measured": False,
            "benchmark_quality_measured": False,
            "causal_quality_improvement_proven": False,
            "sota_supported": False,
        },
        "source_policy": {
            "benchmark_manifest_mapping_gold_prediction_or_evaluator_read": False,
            "question_query_url_host_page_prediction_answer_or_hash_persisted": False,
            "credential_value_read_persisted_hashed_or_emitted": False,
            "official_evaluator_called": False,
        },
        "authorization": {
            "consumed_dev64_design": passed,
            "consumed_dev64_launch": False,
            "exact220_launch": False,
            "evaluator_call": False,
            "training_credit_assignment": False,
            "leaderboard_submission_or_sota_claim": False,
        },
    }
    value["decision_payload_sha256"] = payload_sha256(value)
    validate_decision(value)
    return value


def validate_decision(value: Mapping[str, Any]) -> None:
    unsigned = dict(value)
    seal = unsigned.pop("decision_payload_sha256", None)
    checks = value.get("checks")
    failed = value.get("failed_checks")
    claim = value.get("claim_scope")
    source = value.get("source_policy")
    auth = value.get("authorization")
    if (
        value.get("role") != "v24290_neutral_low_coverage_decision"
        or value.get("protocol_id") != prereg.PROTOCOL_ID
        or not isinstance(checks, Mapping)
        or not isinstance(failed, list)
        or value.get("passed") is not all(checks.values())
        or failed != sorted(name for name, passed in checks.items() if not passed)
        or value.get("status") != ("neutral_mechanism_go" if value["passed"] else "neutral_mechanism_no_go")
        or not isinstance(claim, Mapping)
        or claim.get("fault_injected_mechanism_robustness") is not True
        or any(value_ for key, value_ in claim.items() if key != "fault_injected_mechanism_robustness")
        or not isinstance(source, Mapping)
        or any(source.values())
        or not isinstance(auth, Mapping)
        or auth.get("consumed_dev64_design") is not value["passed"]
        or any(value_ for key, value_ in auth.items() if key != "consumed_dev64_design")
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.42.90 neutral decision drifted")


def publish_new(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    decision = build_decision()
    publish_new(ROOT / OUTPUT, decision)
    print(json.dumps({"path": str(OUTPUT), "status": decision["status"], "failed_checks": decision["failed_checks"]}, sort_keys=True))
