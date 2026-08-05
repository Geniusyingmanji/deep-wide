#!/usr/bin/env python3
"""Content-free diagnosis of V2.45.72's real-pipeline reachability.

The V2.45.72 selector can choose a better representative only when it receives
multiple leads from one registrable source.  The frozen targeted stage first
passes search output through V2.43.71 ``_unique_host_leads``, which keeps the
first lead per source.  This diagnosis uses a synthetic visible-lead vector to
prove that a later title-aligned lead is removed before V2.45.72 runs.

No task, benchmark, historical private artifact, network, model, search,
fetch, evaluator, credential, or page content is opened.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24371_batch_stratified_verifier_runtime as prefilter  # noqa: E402
from deepwide_agent import v24388_uncertainty_credit as credit  # noqa: E402
from deepwide_agent import v24515_neutral_cell_discovery_planner as neutral  # noqa: E402
from deepwide_agent import v24572_validator_aligned_alias_lead_selection as aligned  # noqa: E402
from deepwide_agent.v24320_forward_contract import payload_sha256  # noqa: E402


DATE = "20260805"
OUTPUT = Path(f"results/v24577_v24572_prededup_reachability_diagnosis_v1_{DATE}.json")


def _plan() -> dict[str, Any]:
    baseline = (
        "```markdown\n"
        "| University | Founding year |\n"
        "| --- | --- |\n"
        "| University of Southern Queensland | Unknown |\n"
        "| Beta College | Unknown |\n"
        "```"
    )
    state = credit.apply_active_evidence(
        credit.build_uncertainty_catalog(baseline, []), []
    )
    value = neutral.build_target_plan(state)
    if value is None:
        raise RuntimeError("V2.45.77 synthetic discovery plan is absent")
    return value


def _raw_batches() -> list[dict[str, Any]]:
    return [
        {
            "results": [
                {
                    "url": "https://usq.example.edu/url-only-history",
                    "title": "Institutional history",
                },
                {
                    "url": "https://www.usq.example.edu/title-history",
                    "title": "USQ institutional history",
                },
                {
                    "url": "https://archive.example.org/usq",
                    "title": "University of Southern Queensland archive",
                },
            ]
        }
    ]


def _project_all() -> list[dict[str, str]]:
    output: list[dict[str, str]] = []
    seen_urls: set[str] = set()
    for batch in _raw_batches():
        for raw in batch["results"]:
            lead = prefilter._lead(raw, batch_ordinal=4)
            if lead is None or lead["url"] in seen_urls:
                continue
            seen_urls.add(lead["url"])
            output.append(lead)
    return output


def build_diagnosis(*, now: int | None = None) -> dict[str, Any]:
    plan = _plan()
    pre_dedup = _project_all()
    current = prefilter._unique_host_leads(_raw_batches(), batch_ordinal=4)
    _pre_selected, pre = aligned._selection(
        pre_dedup, plan, excluded_sources=set()
    )
    _current_selected, post = aligned._selection(
        current, plan, excluded_sources=set()
    )
    if not (
        len(pre_dedup) == 3
        and len(current) == 2
        and pre["duplicate_source_lead_count"] == 1
        and pre["source_representative_replacement_count"] == 1
        and pre["validator_aligned_title_replacement_count"] == 1
        and pre["url_only_first_representative_avoided_count"] == 1
        and post["duplicate_source_lead_count"] == 0
        and post["source_representative_replacement_count"] == 0
        and post["validator_aligned_title_replacement_count"] == 0
        and post["url_only_first_representative_avoided_count"] == 0
    ):
        raise RuntimeError("V2.45.77 pre-dedup reachability diagnosis drifted")
    value = {
        "artifact_version": 1,
        "role": "v24577_v24572_prededup_reachability_diagnosis",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "v24572_same_source_replacement_unreachable_in_frozen_targeted_pipeline",
        "pipeline_order": {
            "task_union_deduplicates_exact_url_before_targeted_projection": True,
            "v24371_unique_host_leads_keeps_first_registrable_source_representative": True,
            "v24572_runs_after_v24371_registrable_source_deduplication": True,
            "v24572_receives_at_most_one_lead_per_registrable_source": True,
        },
        "synthetic_counterexample": {
            "exact_url_distinct_visible_lead_count": len(pre_dedup),
            "post_v24371_unique_source_lead_count": len(current),
            "pre_dedup_duplicate_source_lead_count": pre[
                "duplicate_source_lead_count"
            ],
            "pre_dedup_source_representative_replacement_count": pre[
                "source_representative_replacement_count"
            ],
            "pre_dedup_validator_aligned_title_replacement_count": pre[
                "validator_aligned_title_replacement_count"
            ],
            "pre_dedup_url_only_first_representative_avoided_count": pre[
                "url_only_first_representative_avoided_count"
            ],
            "current_pipeline_duplicate_source_lead_count": post[
                "duplicate_source_lead_count"
            ],
            "current_pipeline_source_representative_replacement_count": post[
                "source_representative_replacement_count"
            ],
            "current_pipeline_validator_aligned_title_replacement_count": post[
                "validator_aligned_title_replacement_count"
            ],
            "current_pipeline_url_only_first_representative_avoided_count": post[
                "url_only_first_representative_avoided_count"
            ],
        },
        "conclusions": {
            "v24572_standalone_selection_logic_locally_valid": True,
            "v24572_current_real_pipeline_mechanism_reachable": False,
            "v24576_clean_build_audit_remains_valid_for_tested_surface": True,
            "v24576_protocol_design_authorization_sufficient_for_external_launch": False,
            "v24577_external_protocol_design_must_not_be_frozen_or_launched": True,
            "pre_dedup_candidate_preservation_required_before_new_external_population": True,
            "synthetic_counterexample_claims_external_effect_or_quality_gain": False,
        },
        "source_policy": {
            "visible_title_url_and_registrable_source_only": True,
            "page_content_candidate_value_entropy_or_evaluator_used": False,
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
            "historical_private_task_lead_title_url_query_page_value_or_prediction_opened": False,
            "network_model_search_fetch_process_or_evaluator_called": False,
            "credential_read_hashed_persisted_or_emitted": False,
        },
        "authorization": {
            "prededup_candidate_preservation_successor_design": True,
            "fresh_external_protocol_design": False,
            "fresh_external_activation_or_launch": False,
            "paired_dev64_or_exact220": False,
            "evaluator_access_authorized": False,
            "leaderboard_or_sota": False,
        },
    }
    value["diagnosis_payload_sha256"] = payload_sha256(value)
    return value


def validate_diagnosis(value: dict[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    unsigned = dict(copied)
    seal = unsigned.pop("diagnosis_payload_sha256", None)
    conclusions = copied.get("conclusions", {})
    authorization = copied.get("authorization", {})
    if (
        copied.get("role")
        != "v24577_v24572_prededup_reachability_diagnosis"
        or copied.get("status")
        != "v24572_same_source_replacement_unreachable_in_frozen_targeted_pipeline"
        or conclusions.get("v24572_current_real_pipeline_mechanism_reachable")
        is not False
        or conclusions.get("v24577_external_protocol_design_must_not_be_frozen_or_launched")
        is not True
        or authorization.get("prededup_candidate_preservation_successor_design")
        is not True
        or authorization.get("fresh_external_protocol_design") is not False
        or authorization.get("fresh_external_activation_or_launch") is not False
        or authorization.get("paired_dev64_or_exact220") is not False
        or authorization.get("evaluator_access_authorized") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.45.77 diagnosis drifted")
    return copied


def publish_new(path: Path, value: dict[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    diagnosis = validate_diagnosis(build_diagnosis())
    publish_new(ROOT / OUTPUT, diagnosis)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "status": diagnosis["status"],
                "external_protocol_design_authorized": diagnosis[
                    "authorization"
                ]["fresh_external_protocol_design"],
            },
            sort_keys=True,
        )
    )
