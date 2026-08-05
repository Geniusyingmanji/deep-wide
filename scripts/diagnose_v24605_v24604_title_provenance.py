#!/usr/bin/env python3
"""Content-free provenance diagnosis after the V2.46.04 title funnel.

V2.46.04 proves that every lead visible to the frozen selection surface had
an empty title.  It does not observe the provider action, query-local citation,
fetch request, or fetched-page title boundaries.  This diagnosis combines only
the sealed public V2.46.04 counts with a synthetic, no-network transport replay.
It therefore proves that the current adapters preserve a supplied title, but
does not claim that the real provider supplied one.
"""

from __future__ import annotations

import json
import os
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.native_search import AzureNativeSearchClient  # noqa: E402
from deepwide_agent.v24269_task_union_discovery import (  # noqa: E402
    TaskUnionDiscoverySearchClient,
)
from deepwide_agent.v24280_task_union_single_shot import (  # noqa: E402
    parse_task_union_single_shot,
)
from deepwide_agent.v24378_adaptive_heldout_verifier_runtime import (  # noqa: E402
    _lead_projection,
)
from deepwide_agent.v24320_forward_contract import payload_sha256, sha256  # noqa: E402
from deepwide_agent.v24474_nominal_hard_total_wall_search import (  # noqa: E402
    NominalCompatibleHardTotalWallUncertaintyNativeSearchClient,
    validate_compatibility_class,
)


DATE = "20260805"
RESULT = Path(f"results/v24604_content_free_title_funnel_external_result_v1_{DATE}.json")
DECISION = Path(f"results/v24604_content_free_title_funnel_external_decision_v1_{DATE}.json")
POSTAUDIT = Path(f"results/v24604_content_free_title_funnel_external_postresult_audit_v1_{DATE}.json")
OUTPUT = Path(f"results/v24605_v24604_title_provenance_diagnosis_v1_{DATE}.json")


def _read(path: Path) -> dict[str, Any]:
    value = json.loads((ROOT / path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.46.05 expected a public object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _public_chain() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    result = _read(RESULT)
    decision = _read(DECISION)
    postaudit = _read(POSTAUDIT)
    counts = result.get("mechanism_aggregate", {}).get(
        "total_content_free_title_funnel_count_fields", {}
    )
    if (
        not _sealed(result, "result_payload_sha256")
        or not _sealed(decision, "decision_payload_sha256")
        or not _sealed(postaudit, "audit_payload_sha256")
        or result.get("selected") != 8
        or result.get("reliability_passed") is not True
        or result.get("parent_validation_passed") is not True
        or result.get("latency_passed") is not True
        or counts.get("visible_input_lead_count") != 783
        or counts.get("empty_title_lead_count") != 783
        or counts.get("nonempty_title_lead_count") != 0
        or decision.get("status") != "fresh_content_free_title_funnel_observed"
        or decision.get("diagnostic_route") != "search_title_transport_successor"
        or decision.get("result_sha256") != sha256(ROOT / RESULT)
        or postaudit.get("result_sha256") != sha256(ROOT / RESULT)
        or postaudit.get("decision_sha256") != sha256(ROOT / DECISION)
        or postaudit.get("audit_valid") is not True
        or postaudit.get("findings") != []
        or postaudit.get("shared_api_lease_active") is not False
        or postaudit.get(
            "mapping_gold_category_question_type_split_evaluator_score_read"
        )
        is not False
    ):
        raise RuntimeError("V2.46.05 public chain drifted")
    return result, decision, postaudit


class _SyntheticInner:
    calls = 0
    failures = 0
    tool_calls = 0
    fetch_calls = 0
    fetch_failures = 0
    input_tokens = 0
    output_tokens = 0
    total_tokens = 0

    def __init__(self, batches: list[dict[str, Any]]) -> None:
        self._batches = batches

    def search_many(self, *_args: Any, **_kwargs: Any) -> list[dict[str, Any]]:
        return self._batches


def _synthetic_fidelity() -> dict[str, Any]:
    """Exercise the exact parser/union/projection path without any effect."""

    action_title = "Synthetic Action Title"
    citation_title = "Synthetic Citation Title"
    payload = {
        "id": "synthetic-response",
        "output": [
            {
                "type": "web_search_call",
                "id": "synthetic-call",
                "status": "completed",
                "action": {
                    "type": "search",
                    "queries": ["synthetic one", "synthetic two"],
                    "sources": [
                        {
                            "type": "web_source",
                            "url": "https://action.example/record",
                            "title": action_title,
                        }
                    ],
                },
            },
            {
                "type": "message",
                "content": [
                    {
                        "type": "output_text",
                        "text": "[[QUERY Q0001]]\nsynthetic evidence\n[[END Q0001]]\n",
                        "annotations": [
                            {
                                "type": "url_citation",
                                "url": "https://citation.example/record",
                                "title": citation_title,
                                "start_index": 18,
                                "end_index": 36,
                            }
                        ],
                    }
                ],
            },
        ],
    }
    client = AzureNativeSearchClient(
        "http://unused.invalid/responses",
        "synthetic",
        fetch_pages=False,
        max_workers=1,
    )
    batches, complete, normalized, attachments = parse_task_union_single_shot(
        client,
        ["synthetic one", "synthetic two"],
        payload,
        max_results=3,
    )
    union = TaskUnionDiscoverySearchClient(_SyntheticInner(batches)).search_many(
        ["synthetic one", "synthetic two"], max_results=3
    )
    titles = [
        str(item.get("title", ""))
        for batch in union
        for item in batch.get("results", [])
        if isinstance(item, Mapping)
    ]
    projected = [
        _lead_projection(item)
        for batch in union
        for item in batch.get("results", [])
        if isinstance(item, Mapping)
    ]
    validate_compatibility_class()
    cls = NominalCompatibleHardTotalWallUncertaintyNativeSearchClient
    request_owner = next(base.__name__ for base in cls.__mro__ if "_request" in base.__dict__)
    chunk_owner = next(base.__name__ for base in cls.__mro__ if "_run_chunk" in base.__dict__)
    return {
        "synthetic_action_title_preserved_to_union": action_title in titles,
        "synthetic_citation_title_preserved_to_union": citation_title in titles,
        "synthetic_union_titles_preserved_by_lead_projection": sorted(titles)
        == sorted(item["title"] for item in projected),
        "synthetic_multi_query_mapping_complete": complete,
        "synthetic_mapping_failure_rows_normalized": normalized,
        "synthetic_action_trace_attachments": attachments,
        "concrete_request_owner": request_owner,
        "concrete_chunk_owner": chunk_owner,
        "network_model_fetch_or_evaluator_called": False,
    }


def build_diagnosis(*, now: int | None = None) -> dict[str, Any]:
    result, decision, postaudit = _public_chain()
    counts = result["mechanism_aggregate"][
        "total_content_free_title_funnel_count_fields"
    ]
    fidelity = _synthetic_fidelity()
    if not (
        fidelity["synthetic_action_title_preserved_to_union"]
        and fidelity["synthetic_citation_title_preserved_to_union"]
        and fidelity["synthetic_union_titles_preserved_by_lead_projection"]
        and fidelity["synthetic_mapping_failure_rows_normalized"] == 1
        and fidelity["synthetic_action_trace_attachments"] == 1
        and fidelity["concrete_request_owner"] == "HardTotalWallNativeSearchClient"
        and fidelity["concrete_chunk_owner"] == "TaskUnionSingleShotMixin"
    ):
        raise RuntimeError("V2.46.05 synthetic fidelity premise drifted")
    value = {
        "artifact_version": 1,
        "role": "v24605_v24604_title_provenance_diagnosis",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "selection_titles_empty_upstream_provenance_unobserved",
        "public_chain": {
            "result_path": str(RESULT),
            "result_sha256": sha256(ROOT / RESULT),
            "decision_path": str(DECISION),
            "decision_sha256": sha256(ROOT / DECISION),
            "postaudit_path": str(POSTAUDIT),
            "postaudit_sha256": sha256(ROOT / POSTAUDIT),
            "diagnostic_route": decision["diagnostic_route"],
        },
        "observed_selection_boundary": {
            "visible_input_lead_count": int(counts["visible_input_lead_count"]),
            "empty_title_lead_count": int(counts["empty_title_lead_count"]),
            "nonempty_title_lead_count": int(counts["nonempty_title_lead_count"]),
            "all_visible_selection_titles_empty": True,
        },
        "synthetic_transport_fidelity": fidelity,
        "conclusions": {
            "supplied_action_title_is_preserved_by_current_synthetic_chain": True,
            "supplied_citation_title_is_preserved_by_current_synthetic_chain": True,
            "v24604_proves_concrete_adapter_deleted_nonempty_provider_titles": False,
            "v24604_proves_real_provider_action_sources_omitted_titles": False,
            "v24604_proves_query_local_citations_omitted_titles": False,
            "v24604_observed_fetch_request_titles": False,
            "v24604_observed_fetched_page_titles": False,
            "direct_parser_or_validator_change_is_evidence_supported": False,
            "next_successor_must_observe_title_provenance_boundaries": True,
            "benchmark_quality_or_sota_improvement_measured": False,
        },
        "required_next_observability": {
            "action_source_empty_and_nonempty_title_counts": True,
            "query_local_citation_empty_and_nonempty_title_counts": True,
            "same_url_action_empty_citation_nonempty_count": True,
            "fetch_request_empty_and_nonempty_title_counts": True,
            "fetched_page_empty_and_nonempty_title_counts": True,
            "empty_fetch_request_to_nonempty_page_title_count": True,
            "raw_task_question_query_url_title_page_or_prediction_emitted": False,
        },
        "source_policy": {
            "sealed_public_count_control_artifacts_and_repository_sources_only": True,
            "synthetic_payload_only": True,
            "prior_private_execution_directory_opened": False,
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
            "network_model_search_fetch_process_or_evaluator_called": False,
            "credential_read_hashed_persisted_or_emitted": False,
        },
        "authorization": {
            "content_free_title_provenance_observer_design": True,
            "search_parser_title_validator_or_evidence_rule_change": False,
            "fresh_external_protocol_design": False,
            "fresh_external_activation_or_launch": False,
            "paired_dev64_or_exact220": False,
            "evaluator_access_authorized": False,
            "leaderboard_or_sota": False,
        },
    }
    value["diagnosis_payload_sha256"] = payload_sha256(value)
    return validate_diagnosis(value)


def validate_diagnosis(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = json.loads(json.dumps(dict(value)))
    unsigned = dict(copied)
    seal = unsigned.pop("diagnosis_payload_sha256", None)
    observed = copied.get("observed_selection_boundary", {})
    fidelity = copied.get("synthetic_transport_fidelity", {})
    conclusions = copied.get("conclusions", {})
    required = copied.get("required_next_observability", {})
    source = copied.get("source_policy", {})
    authorization = copied.get("authorization", {})
    if (
        copied.get("role") != "v24605_v24604_title_provenance_diagnosis"
        or copied.get("status")
        != "selection_titles_empty_upstream_provenance_unobserved"
        or observed.get("visible_input_lead_count") != 783
        or observed.get("empty_title_lead_count") != 783
        or observed.get("nonempty_title_lead_count") != 0
        or observed.get("all_visible_selection_titles_empty") is not True
        or fidelity.get("synthetic_action_title_preserved_to_union") is not True
        or fidelity.get("synthetic_citation_title_preserved_to_union") is not True
        or fidelity.get("synthetic_union_titles_preserved_by_lead_projection") is not True
        or fidelity.get("network_model_fetch_or_evaluator_called") is not False
        or conclusions.get(
            "v24604_proves_concrete_adapter_deleted_nonempty_provider_titles"
        )
        is not False
        or conclusions.get("v24604_proves_real_provider_action_sources_omitted_titles")
        is not False
        or conclusions.get("direct_parser_or_validator_change_is_evidence_supported")
        is not False
        or conclusions.get("next_successor_must_observe_title_provenance_boundaries")
        is not True
        or any(
            required.get(name) is not True
            for name in required
            if name != "raw_task_question_query_url_title_page_or_prediction_emitted"
        )
        or required.get("raw_task_question_query_url_title_page_or_prediction_emitted")
        is not False
        or source.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
        or source.get("network_model_search_fetch_process_or_evaluator_called")
        is not False
        or authorization.get("content_free_title_provenance_observer_design")
        is not True
        or authorization.get("search_parser_title_validator_or_evidence_rule_change")
        is not False
        or authorization.get("fresh_external_protocol_design") is not False
        or authorization.get("fresh_external_activation_or_launch") is not False
        or authorization.get("paired_dev64_or_exact220") is not False
        or authorization.get("evaluator_access_authorized") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.46.05 diagnosis drifted")
    return copied


def publish_new(path: Path, value: Mapping[str, Any]) -> None:
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
    diagnosis = build_diagnosis()
    publish_new(ROOT / OUTPUT, diagnosis)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "status": diagnosis["status"],
                "observer_design_authorized": diagnosis["authorization"][
                    "content_free_title_provenance_observer_design"
                ],
            },
            sort_keys=True,
        )
    )
