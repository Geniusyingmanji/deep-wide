#!/usr/bin/env python3
"""Evaluate the audited frozen V2.48.66 220-vector exactly once."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24866_coverage_revision_exact220_contract as contract  # noqa: E402
from scripts import finalize_v24800_exact220 as base  # noqa: E402
from scripts import finalize_v24287_exact220 as evaluator  # noqa: E402
from scripts.finalize_fullset_rollout import summarize_rollout  # noqa: E402


EVALUATOR_ROOT = contract.OUTPUT_ROOT / "evaluator"
EVALUATOR_PROTOCOL = Path(
    f"results/v24866_coverage_revision_exact220_evaluator_preregistration_v1_{contract.DATE}.json"
)
FINAL_RESULT = Path(
    f"results/v24866_coverage_revision_exact220_result_v1_{contract.DATE}.json"
)


def configure() -> None:
    values = {
        "contract": contract,
        "EVALUATOR_ROOT": EVALUATOR_ROOT,
        "PREPARE_ATTESTATION": EVALUATOR_ROOT / "prepare_attestation.json",
        "JOINED_OUTCOMES": EVALUATOR_ROOT
        / "terminal_outcomes_evaluator_joined.jsonl",
        "OFFICIAL_PREDICTIONS": EVALUATOR_ROOT / "official_predictions.jsonl",
        "EVALUATOR_RUNS": EVALUATOR_ROOT / "official_eval_workers",
        "EVALUATOR_LOGS": EVALUATOR_ROOT / "logs",
        "MERGED_RESULTS": EVALUATOR_ROOT / "official_eval_results.jsonl",
        "MERGE_ATTESTATION": EVALUATOR_ROOT / "merge_attestation.json",
        "SUMMARY": EVALUATOR_ROOT / "conservative_summary.json",
        "EVALUATOR_OWNER": "v24866_coverage_revision_exact220_evaluator_v1",
        "EVALUATOR_PURPOSE": "postfreeze_fixed_partition_parallel_v24866_evaluator",
    }
    for name, value in values.items():
        setattr(base, name, value)


def read_rows(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def main() -> None:
    configure()
    audit = json.loads((ROOT / contract.FORWARD_AUDIT).read_text(encoding="utf-8"))
    protocol = json.loads((ROOT / contract.PROTOCOL).read_text(encoding="utf-8"))
    rows = read_rows(ROOT / contract.RUNTIME_PREDICTIONS)
    tasks = contract.task_vector(ROOT, protocol)
    if (
        audit.get("audit_valid") is not True
        or audit.get("findings") != []
        or audit.get("authorization", {}).get(
            "postfreeze_exact220_evaluator_protocol"
        )
        is not True
        or audit.get("forward_result_sha256")
        != contract.sha256(ROOT / contract.FORWARD_RESULT)
        or len(rows) != 220
        or [row["opaque_id"] for row in rows]
        != [task["opaque_id"] for task in tasks]
        or any(
            (ROOT / path).exists() or (ROOT / path).is_symlink()
            for path in (EVALUATOR_ROOT, EVALUATOR_PROTOCOL, FINAL_RESULT)
        )
    ):
        raise RuntimeError("V2.48.66 evaluator barrier drifted")

    base.configure_evaluator()
    mapping = ROOT / base.MAPPING_PATH
    query = ROOT / base.QUERY_PATH
    answers = ROOT / base.ANSWER_ROOT
    evaluator_contract = base._parent_evaluator_contract()
    evaluator_contract["mapping"] = {
        "path": str(base.MAPPING_PATH),
        "sha256": contract.sha256(mapping),
    }
    evaluator_contract["query_data"] = {
        "path": str(base.QUERY_PATH),
        "sha256": contract.sha256(query),
    }
    evaluator_contract["answer_corpus"] = {
        "root": str(base.ANSWER_ROOT),
        "manifest_sha256": base._live_answer_corpus_manifest_sha256(answers),
    }
    evaluator_contract["evaluator_source"] = {
        "manifest_sha256": base._live_evaluator_source_manifest_sha256()
    }
    evaluator_contract.pop(
        "opened_only_after_v24800_exact220_prediction_freeze", None
    )
    evaluator_contract[
        "opened_only_after_v24866_exact220_prediction_freeze"
    ] = True
    evaluator_protocol = {
        "artifact_version": 1,
        "role": "v24866_coverage_revision_exact220_evaluator_preregistration",
        "protocol_id": contract.PROTOCOL_ID,
        "selected": 220,
        "evaluator_workers": 32,
        "forward_barrier": {
            "forward_result_sha256": contract.sha256(
                ROOT / contract.FORWARD_RESULT
            ),
            "forward_audit_sha256": contract.sha256(ROOT / contract.FORWARD_AUDIT),
            "prediction_freeze_sha256": contract.sha256(
                ROOT / contract.PREDICTION_FREEZE
            ),
            "runtime_predictions_sha256": contract.sha256(
                ROOT / contract.RUNTIME_PREDICTIONS
            ),
            "terminal_predictions": 220,
            "mapping_or_evaluator_opened_during_forward": False,
        },
        "evaluator_contract": evaluator_contract,
        "evaluation_contract": {
            "all_220_predictions_frozen_before_mapping_query_answer_or_evaluator_open": True,
            "fixed_contiguous_32_way_partition_in_prediction_order": True,
            "official_evaluator_on_every_frozen_prediction_exactly_once": True,
            "worker_error_rows_are_terminal_failure_as_zero": True,
            "selective_retry_revaluation_or_prediction_selection": False,
            "conservative_denominators": {"test_156": 156, "all_220": 220},
        },
        "authorization": {
            "postfreeze_exact220_evaluation": True,
            "selective_retry_or_revaluation": False,
            "additional_rollout_avg4_leaderboard_or_sota": False,
        },
    }
    evaluator_protocol["protocol_payload_sha256"] = contract.payload_sha256(
        evaluator_protocol
    )
    evaluator._new_json(ROOT / EVALUATOR_PROTOCOL, evaluator_protocol)
    base.EVALUATOR_PROTOCOL = EVALUATOR_PROTOCOL

    barrier = {
        "runtime_rows": rows,
        "freeze": json.loads(
            (ROOT / contract.PREDICTION_FREEZE).read_text(encoding="utf-8")
        ),
    }
    prepared = evaluator.prepare_evaluator_inputs(ROOT, evaluator_protocol, barrier)
    with evaluator.acquire_deepwide_api_lease(
        ROOT,
        owner=base.EVALUATOR_OWNER,
        purpose=base.EVALUATOR_PURPOSE,
        path=ROOT / contract.LEASE_PATH,
    ):
        eval_rows, parallel = evaluator.run_parallel_evaluator(
            ROOT, evaluator_protocol, prepared["official"]
        )
    summary = summarize_rollout(prepared["joined"], eval_rows, rollout_id=1)
    evaluator._new_json(ROOT / base.SUMMARY, summary)
    all_metrics = base._group_metrics(summary, "all_220")
    test_metrics = base._group_metrics(summary, "test_156")
    run_summary = json.loads(
        (ROOT / contract.RUN_SUMMARY).read_text(encoding="utf-8")
    )
    all_metrics.update(
        {
            "model_generated_tables": run_summary["model_generated_tables"],
            "fallback_tables": run_summary["fallback_tables"],
            "system_total_tokens": run_summary["system_total_tokens"],
        }
    )
    result = {
        "artifact_version": 1,
        "role": "v24866_coverage_revision_exact220_result",
        "protocol_id": contract.PROTOCOL_ID,
        "status": "exact220_single_rollout_complete",
        "selected": 220,
        "failure_as_zero": True,
        "exact220_prediction_freeze_before_evaluator": True,
        "metrics": {"test_156": test_metrics, "all_220": all_metrics},
        "efficiency": {
            "forward_wall_seconds": run_summary["forward_wall_seconds"],
            "evaluator_parallel_wall_seconds": parallel["attestation"][
                "parallel_wall_seconds"
            ],
            "evaluator_workers": 32,
        },
        "coverage_revision_totals": run_summary["coverage_revision_totals"],
        "claims": {
            "public_exact220_single_rollout": True,
            "leaderboard_submitted": False,
            "sota": False,
            "quality_improvement_established": False,
        },
        "authorization": {
            "additional_rollout_or_avg4": False,
            "selective_retry_or_revaluation": False,
            "leaderboard_submission": False,
            "sota_claim": False,
        },
        "provenance": {
            "evaluator_protocol_sha256": contract.sha256(
                ROOT / EVALUATOR_PROTOCOL
            ),
            "forward_result_sha256": contract.sha256(
                ROOT / contract.FORWARD_RESULT
            ),
            "forward_audit_sha256": contract.sha256(
                ROOT / contract.FORWARD_AUDIT
            ),
            "prediction_freeze_sha256": contract.sha256(
                ROOT / contract.PREDICTION_FREEZE
            ),
            "merged_official_eval_results_sha256": contract.sha256(
                ROOT / base.MERGED_RESULTS
            ),
            "parallel_merge_attestation_sha256": contract.sha256(
                ROOT / base.MERGE_ATTESTATION
            ),
            "conservative_summary_sha256": contract.sha256(ROOT / base.SUMMARY),
        },
        "source_policy": {
            "runtime_boundary": ["opaque_id", "question"],
            "mapping_opened_only_after_exact220_prediction_freeze_and_pushed_audit": True,
            "same_run_evaluator_feedback_used_for_forward_or_prediction_selection": False,
            "fixed_public_exact220_task_set_reexecuted": True,
        },
    }
    result["result_payload_sha256"] = contract.payload_sha256(result)
    evaluator._new_json(ROOT / FINAL_RESULT, result)
    print(json.dumps({"path": str(FINAL_RESULT), "metrics": all_metrics}))


if __name__ == "__main__":
    main()
