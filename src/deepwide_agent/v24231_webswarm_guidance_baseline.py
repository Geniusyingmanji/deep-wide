"""Build-only WebSwarm guidance baseline with strict fact/experience isolation.

WebSwarm v1 first probes web-information topology and, for a homogeneous wide
fanout, runs two scout siblings before extracting process-level experience for
the remaining siblings.  This module freezes those two mechanisms plus the
``no_probing``, upstream-faithful ``no_experience``, and matched-schedule
``no_experience`` controls without executing a model, search, fetch, benchmark,
or evaluator.

Only exact-schema hashes, bounded counts, finite cost values, typed process
signals, and enum tactics enter this module.  Scout answers, raw questions,
queries, URLs, page text, predictions, benchmark labels, gold, evaluator
metadata, rewards, and scores are rejected.  Experience may change later
sibling search process but can never serve as factual evidence.  The module is
not connected to active forward code and grants no benchmark or training
authority.
"""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any, Mapping, Sequence


POLICY_ID = "v24231_webswarm_guidance_baseline_v1"
POLICY_ROLE = "v24231_webswarm_guidance_policy"
PROBE_ROLE = "v24231_web_structure_probe_receipt"
SCOUT_ROLE = "v24231_scout_process_trace"
EXPERIENCE_ROLE = "v24231_sibling_process_experience"
ARM_ROLE = "v24231_webswarm_guidance_arm"
BUNDLE_ROLE = "v24231_webswarm_guidance_ablation_bundle"

SOURCE_ARXIV = "2607.08662"
SOURCE_VERSION = 1
SOURCE_REPOSITORY_COMMIT = "40c9aacad7cd6e9cdb3e7add954d59b766425717"

SCOUT_COUNT = 2
MAX_SIBLINGS = 64
MAX_PROCESS_SIGNALS_PER_SCOUT = 32
MAX_AGGREGATED_PROCESS_SIGNALS = 64
MAX_COST_COUNT = 1_000_000_000
MAX_WALL_SECONDS = 1_000_000_000.0

TOPOLOGIES = frozenset(
    {"centralized", "centralized_with_gaps", "distributed"}
)
PROCESS_TACTICS = frozenset(
    {
        "probe_before_fanout",
        "extract_hub_then_verify_gaps",
        "extract_hub_then_target_visible_gaps",
        "partition_visible_dimension_then_deduplicate",
    }
)
PROCESS_TACTICS_BY_KIND = {
    "effective_query_pattern": frozenset(
        {
            "use_exact_phrase_for_visible_entity_and_attribute",
            "combine_visible_entity_and_attribute_terms",
            "restrict_search_to_visible_primary_source_domain",
            "search_for_a_visible_list_or_table_hub",
            "partition_the_visible_scope_by_date",
            "partition_the_visible_scope_by_entity",
            "partition_the_visible_scope_by_organization",
        }
    ),
    "ineffective_query_pattern": frozenset(
        {
            "avoid_broad_underspecified_query",
            "avoid_answer_leading_query",
            "avoid_semantic_duplicate_query",
            "avoid_unsupported_alias_query",
        }
    ),
    "reliable_source_family": frozenset(
        {
            "prefer_official_primary_source",
            "prefer_government_source",
            "prefer_academic_source",
            "prefer_structured_database",
            "prefer_encyclopedic_hub",
        }
    ),
    "unreliable_source_family": frozenset(
        {
            "avoid_unsupported_aggregator",
            "avoid_social_source",
            "avoid_user_generated_source",
            "avoid_unattributed_mirror",
        }
    ),
    "useful_page_type": frozenset(
        {
            "prefer_structured_table_page",
            "prefer_official_record_page",
            "prefer_entity_profile_page",
            "prefer_linked_index_page",
        }
    ),
    "dead_end_page_type": frozenset(
        {
            "avoid_search_snippet_only",
            "avoid_paywalled_stub",
            "avoid_dynamic_empty_page",
            "avoid_duplicate_mirror_page",
        }
    ),
    "workflow_hint": frozenset(
        {
            "fetch_before_extract",
            "verify_with_independent_source",
            "deduplicate_before_fanout",
            "resolve_anchor_before_table",
            "validate_row_before_fill",
            "falsify_after_fill",
        }
    ),
}
PROCESS_SIGNAL_KINDS = frozenset(PROCESS_TACTICS_BY_KIND)
PROCESS_TACTIC_ADVICE = {
    tactic: tactic.removeprefix("use_").replace("_", " ") + "."
    for tactics in PROCESS_TACTICS_BY_KIND.values()
    for tactic in tactics
}
ARMS = (
    "full",
    "no_probing",
    "no_experience_upstream",
    "no_experience_matched_schedule",
)

PRODUCTION_PACKAGE_AUTHORIZED = False
ACTIVE_FORWARD_INTEGRATION_AUTHORIZED = False
BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED = False
DEV64_OR_EXACT220_LAUNCH_AUTHORIZED = False
SHARED_API_LEASE_ACQUIRE_AUTHORIZED = False
LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED = False

FORBIDDEN_METADATA_KEYS = frozenset(
    {
        "answer",
        "answerkey",
        "benchmark",
        "benchmarkcategory",
        "benchmarklabel",
        "benchmarkname",
        "benchmarksubset",
        "category",
        "correctness",
        "dataset",
        "evaluator",
        "evaluatoroutput",
        "evaluatorpayload",
        "evaluatorscore",
        "finaloutcome",
        "gold",
        "groundtruth",
        "instanceid",
        "label",
        "mapping",
        "officialmetrics",
        "prediction",
        "question",
        "questiontype",
        "rawpage",
        "resultscsv",
        "reward",
        "score",
        "split",
        "subset",
        "taskcategory",
        "taskid",
        "url",
        "verifieroutcome",
    }
)

POLICY_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "baseline_only",
        "source_arxiv",
        "source_version",
        "source_repository_commit",
        "selection_protocol_sha256",
        "model_contract_sha256",
        "search_fetch_contract_sha256",
        "total_budget_contract_sha256",
        "root_scope_projection_protocol_sha256",
        "process_signal_vocabulary_sha256",
        "scout_count",
        "max_siblings",
        "probe_scope",
        "experience_scope",
        "experience_fact_isolation",
        "same_parent_homogeneous_siblings_required",
        "test_or_benchmark_outcome_used_for_policy_selection",
        "runtime_label_routing_used",
        "production_package_authorized",
        "active_forward_integration_authorized",
        "policy_sha256",
    }
)
PROBE_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "baseline_only",
        "policy_sha256",
        "root_scope_projection_sha256",
        "parent_node_ref_sha256",
        "probe_run_ref_sha256",
        "topology",
        "process_tactic",
        "probe_search_calls",
        "probe_fetch_calls",
        "probe_model_calls",
        "probe_input_tokens",
        "probe_output_tokens",
        "probe_wall_seconds",
        "raw_question_query_url_page_text_answer_prediction_or_evaluator_payload_embedded",
        "benchmark_label_mapping_gold_score_or_reward_used",
        "probe_receipt_sha256",
    }
)
PROCESS_SIGNAL_KEYS = frozenset({"kind", "tactic", "value_sha256"})
SCOUT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "baseline_only",
        "policy_sha256",
        "root_scope_projection_sha256",
        "parent_node_ref_sha256",
        "homogeneous_group_ref_sha256",
        "scout_slot",
        "sibling_node_ref_sha256",
        "sibling_mode_sha256",
        "process_signals",
        "model_calls",
        "search_calls",
        "fetch_calls",
        "input_tokens",
        "output_tokens",
        "wall_seconds",
        "scout_terminal_status",
        "raw_task_query_url_page_text_answer_prediction_or_evaluator_payload_embedded",
        "raw_factual_value_visible_in_process_signal_schema",
        "process_fact_separation_independently_verified",
        "benchmark_label_mapping_gold_score_or_reward_used",
        "scout_trace_sha256",
    }
)
EXPERIENCE_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "baseline_only",
        "policy_sha256",
        "root_scope_projection_sha256",
        "parent_node_ref_sha256",
        "homogeneous_group_ref_sha256",
        "experience_extractor_ref_sha256",
        "source_scout_trace_sha256s",
        "process_signals",
        "extractor_model_calls",
        "extractor_input_tokens",
        "extractor_output_tokens",
        "extractor_wall_seconds",
        "same_instance_only",
        "same_parent_only",
        "homogeneous_siblings_only",
        "remaining_siblings_only",
        "process_advice_schema_only",
        "factual_evidence_authority",
        "raw_factual_value_visible_in_process_signal_schema",
        "process_fact_separation_independently_verified",
        "raw_scout_answer_query_url_page_text_or_evaluator_payload_embedded",
        "benchmark_label_mapping_gold_score_or_reward_used",
        "experience_sha256",
    }
)
COST_KEYS = frozenset(
    {
        "model_calls",
        "search_calls",
        "fetch_calls",
        "input_tokens",
        "output_tokens",
        "wall_seconds",
    }
)
ARM_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "baseline_only",
        "policy_sha256",
        "arm_name",
        "arm_ref_sha256",
        "root_scope_projection_sha256",
        "parent_node_ref_sha256",
        "homogeneous_group_ref_sha256",
        "sibling_count",
        "scout_count",
        "fanout_count",
        "web_probing_enabled",
        "experience_reuse_enabled",
        "probe_receipt_sha256",
        "scout_trace_sha256s",
        "experience_sha256",
        "probe_extractor_cost",
        "shared_model_contract_sha256",
        "shared_search_fetch_contract_sha256",
        "shared_total_budget_contract_sha256",
        "shared_root_scope_projection_protocol_sha256",
        "shared_user_prompt_and_output_contract",
        "same_sibling_schedule",
        "same_base_agent_budget_and_attempts",
        "method_specific_overhead_counted",
        "method_specific_overhead_debited_from_shared_total_cap",
        "experience_injected_only_into_remaining_siblings",
        "experience_has_factual_evidence_authority",
        "benchmark_metadata_available_to_forward",
        "benchmark_forward_or_evaluator_authorized",
        "arm_sha256",
    }
)
BUNDLE_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "baseline_only",
        "policy_sha256",
        "bundle_ref_sha256",
        "arm_sha256s",
        "arm_names",
        "exact_arm_set",
        "only_guidance_switches_differ",
        "upstream_no_experience_schedule_difference_disclosed",
        "matched_schedule_no_experience_control_present",
        "probe_and_extractor_overhead_included",
        "same_model_search_fetch_prompt_output_budget_attempts",
        "shared_total_budget_cap_includes_method_overhead",
        "future_dev64_is_engineering_only",
        "future_reportable_score_requires_fresh_exact220",
        "failure_as_zero_no_resume_no_selective_retry",
        "single_owner_and_inherited_capacity_freeze_required",
        "quality_cost_or_benchmark_effect_observed",
        "leaderboard_submission_or_sota_claim_authorized",
        "bundle_sha256",
    }
)


def object_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _normalized_key(value: object) -> str:
    return "".join(
        character for character in str(value).casefold() if character.isalnum()
    )


def reject_privileged_metadata(value: object) -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if _normalized_key(key) in FORBIDDEN_METADATA_KEYS:
                raise ValueError("V2.42.31 privileged runtime metadata rejected")
            reject_privileged_metadata(nested)
    elif isinstance(value, (list, tuple)):
        for nested in value:
            reject_privileged_metadata(nested)


def _exact(
    value: Mapping[str, Any], *, keys: frozenset[str], label: str
) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != keys:
        raise ValueError(f"V2.42.31 {label} schema is not exact")
    return value


def _integer(value: object, *, label: str, minimum: int, maximum: int) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < minimum
        or value > maximum
    ):
        raise ValueError(f"V2.42.31 {label} is outside the frozen range")
    return value


def _finite(value: object, *, label: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
        or float(value) < 0.0
        or float(value) > MAX_WALL_SECONDS
    ):
        raise ValueError(f"V2.42.31 {label} is outside the frozen range")
    number = float(value)
    return 0.0 if number == 0.0 else number


def _sealed(value: Mapping[str, Any], *, seal_key: str) -> bool:
    if not _is_sha256(value.get(seal_key)):
        return False
    unsigned = dict(value)
    seal = unsigned.pop(seal_key)
    return seal == object_sha256(unsigned)


def _hashes(values: Sequence[object], *, label: str) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        raise ValueError(f"V2.42.31 {label} must be a sequence")
    output = tuple(str(value) for value in values)
    if not all(_is_sha256(value) for value in output):
        raise ValueError(f"V2.42.31 {label} is not SHA-256 bound")
    if len(set(output)) != len(output):
        raise ValueError(f"V2.42.31 {label} contains duplicates")
    return output


def _process_signals(
    values: Sequence[Mapping[str, Any]], *, maximum: int
) -> list[dict[str, str]]:
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        raise ValueError("V2.42.31 process signals must be a sequence")
    if len(values) > maximum:
        raise ValueError("V2.42.31 process-signal count exceeds the frozen cap")
    output: list[dict[str, str]] = []
    for value in values:
        signal = _exact(value, keys=PROCESS_SIGNAL_KEYS, label="process signal")
        kind = signal.get("kind")
        tactic = signal.get("tactic")
        digest = signal.get("value_sha256")
        if (
            kind not in PROCESS_SIGNAL_KINDS
            or tactic not in PROCESS_TACTICS_BY_KIND.get(str(kind), frozenset())
            or not _is_sha256(digest)
        ):
            raise ValueError("V2.42.31 process signal is outside the frozen vocabulary")
        output.append(
            {
                "kind": str(kind),
                "tactic": str(tactic),
                "value_sha256": str(digest),
            }
        )
    output.sort(
        key=lambda item: (item["kind"], item["tactic"], item["value_sha256"])
    )
    if len(
        {
            (item["kind"], item["tactic"], item["value_sha256"])
            for item in output
        }
    ) != len(output):
        raise ValueError("V2.42.31 process signals contain duplicates")
    return output


def build_guidance_policy(
    *,
    selection_protocol_sha256: str,
    model_contract_sha256: str,
    search_fetch_contract_sha256: str,
    total_budget_contract_sha256: str,
    root_scope_projection_protocol_sha256: str,
    process_signal_vocabulary_sha256: str,
) -> dict[str, Any]:
    hashes = (
        selection_protocol_sha256,
        model_contract_sha256,
        search_fetch_contract_sha256,
        total_budget_contract_sha256,
        root_scope_projection_protocol_sha256,
        process_signal_vocabulary_sha256,
    )
    if not all(_is_sha256(value) for value in hashes):
        raise ValueError("V2.42.31 policy identity is not SHA-256 bound")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": POLICY_ROLE,
        "policy_id": POLICY_ID,
        "baseline_only": True,
        "source_arxiv": SOURCE_ARXIV,
        "source_version": SOURCE_VERSION,
        "source_repository_commit": SOURCE_REPOSITORY_COMMIT,
        "selection_protocol_sha256": selection_protocol_sha256,
        "model_contract_sha256": model_contract_sha256,
        "search_fetch_contract_sha256": search_fetch_contract_sha256,
        "total_budget_contract_sha256": total_budget_contract_sha256,
        "root_scope_projection_protocol_sha256": root_scope_projection_protocol_sha256,
        "process_signal_vocabulary_sha256": process_signal_vocabulary_sha256,
        "scout_count": SCOUT_COUNT,
        "max_siblings": MAX_SIBLINGS,
        "probe_scope": "root_level_wide_node_only",
        "experience_scope": "same_instance_same_parent_homogeneous_siblings_only",
        "experience_fact_isolation": (
            "typed_process_signal_hash_schema_only_not_semantically_verified"
        ),
        "same_parent_homogeneous_siblings_required": True,
        "test_or_benchmark_outcome_used_for_policy_selection": False,
        "runtime_label_routing_used": False,
        "production_package_authorized": PRODUCTION_PACKAGE_AUTHORIZED,
        "active_forward_integration_authorized": ACTIVE_FORWARD_INTEGRATION_AUTHORIZED,
    }
    value["policy_sha256"] = object_sha256(value)
    return value


def validate_guidance_policy(value: Mapping[str, Any]) -> None:
    policy = _exact(value, keys=POLICY_KEYS, label="policy")
    expected = build_guidance_policy(
        selection_protocol_sha256=str(policy.get("selection_protocol_sha256")),
        model_contract_sha256=str(policy.get("model_contract_sha256")),
        search_fetch_contract_sha256=str(policy.get("search_fetch_contract_sha256")),
        total_budget_contract_sha256=str(
            policy.get("total_budget_contract_sha256")
        ),
        root_scope_projection_protocol_sha256=str(
            policy.get("root_scope_projection_protocol_sha256")
        ),
        process_signal_vocabulary_sha256=str(
            policy.get("process_signal_vocabulary_sha256")
        ),
    )
    if dict(policy) != expected or not _sealed(policy, seal_key="policy_sha256"):
        raise ValueError("V2.42.31 guidance policy contract drifted")


def build_web_probe_receipt(
    *,
    policy: Mapping[str, Any],
    root_scope_projection_sha256: str,
    parent_node_ref_sha256: str,
    probe_run_ref_sha256: str,
    topology: str,
    probe_search_calls: int,
    probe_fetch_calls: int,
    probe_model_calls: int,
    probe_input_tokens: int,
    probe_output_tokens: int,
    probe_wall_seconds: float,
) -> dict[str, Any]:
    validate_guidance_policy(policy)
    if not all(
        _is_sha256(value)
        for value in (
            root_scope_projection_sha256,
            parent_node_ref_sha256,
            probe_run_ref_sha256,
        )
    ):
        raise ValueError("V2.42.31 probe identity is not SHA-256 bound")
    if topology not in TOPOLOGIES:
        raise ValueError("V2.42.31 probe topology is outside the frozen enum")
    tactic = {
        "centralized": "extract_hub_then_verify_gaps",
        "centralized_with_gaps": "extract_hub_then_target_visible_gaps",
        "distributed": "partition_visible_dimension_then_deduplicate",
    }[topology]
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": PROBE_ROLE,
        "policy_id": POLICY_ID,
        "baseline_only": True,
        "policy_sha256": policy["policy_sha256"],
        "root_scope_projection_sha256": root_scope_projection_sha256,
        "parent_node_ref_sha256": parent_node_ref_sha256,
        "probe_run_ref_sha256": probe_run_ref_sha256,
        "topology": topology,
        "process_tactic": tactic,
        "probe_search_calls": _integer(
            probe_search_calls,
            label="probe search calls",
            minimum=0,
            maximum=MAX_COST_COUNT,
        ),
        "probe_fetch_calls": _integer(
            probe_fetch_calls,
            label="probe fetch calls",
            minimum=0,
            maximum=MAX_COST_COUNT,
        ),
        "probe_model_calls": _integer(
            probe_model_calls,
            label="probe model calls",
            minimum=0,
            maximum=MAX_COST_COUNT,
        ),
        "probe_input_tokens": _integer(
            probe_input_tokens,
            label="probe input tokens",
            minimum=0,
            maximum=MAX_COST_COUNT,
        ),
        "probe_output_tokens": _integer(
            probe_output_tokens,
            label="probe output tokens",
            minimum=0,
            maximum=MAX_COST_COUNT,
        ),
        "probe_wall_seconds": _finite(
            probe_wall_seconds, label="probe wall seconds"
        ),
        "raw_question_query_url_page_text_answer_prediction_or_evaluator_payload_embedded": False,
        "benchmark_label_mapping_gold_score_or_reward_used": False,
    }
    value["probe_receipt_sha256"] = object_sha256(value)
    return value


def validate_web_probe_receipt(
    value: Mapping[str, Any], *, policy: Mapping[str, Any]
) -> None:
    probe = _exact(value, keys=PROBE_KEYS, label="probe receipt")
    expected = build_web_probe_receipt(
        policy=policy,
        root_scope_projection_sha256=str(probe.get("root_scope_projection_sha256")),
        parent_node_ref_sha256=str(probe.get("parent_node_ref_sha256")),
        probe_run_ref_sha256=str(probe.get("probe_run_ref_sha256")),
        topology=str(probe.get("topology")),
        probe_search_calls=probe.get("probe_search_calls"),
        probe_fetch_calls=probe.get("probe_fetch_calls"),
        probe_model_calls=probe.get("probe_model_calls"),
        probe_input_tokens=probe.get("probe_input_tokens"),
        probe_output_tokens=probe.get("probe_output_tokens"),
        probe_wall_seconds=probe.get("probe_wall_seconds"),
    )
    if dict(probe) != expected or not _sealed(
        probe, seal_key="probe_receipt_sha256"
    ):
        raise ValueError("V2.42.31 probe receipt contract drifted")


def build_scout_process_trace(
    *,
    policy: Mapping[str, Any],
    root_scope_projection_sha256: str,
    parent_node_ref_sha256: str,
    homogeneous_group_ref_sha256: str,
    scout_slot: int,
    sibling_node_ref_sha256: str,
    sibling_mode_sha256: str,
    process_signals: Sequence[Mapping[str, Any]],
    model_calls: int,
    search_calls: int,
    fetch_calls: int,
    input_tokens: int,
    output_tokens: int,
    wall_seconds: float,
    scout_terminal_status: str,
) -> dict[str, Any]:
    validate_guidance_policy(policy)
    if not all(
        _is_sha256(value)
        for value in (
            root_scope_projection_sha256,
            parent_node_ref_sha256,
            homogeneous_group_ref_sha256,
            sibling_node_ref_sha256,
            sibling_mode_sha256,
        )
    ):
        raise ValueError("V2.42.31 scout identity is not SHA-256 bound")
    slot = _integer(
        scout_slot,
        label="scout slot",
        minimum=1,
        maximum=SCOUT_COUNT,
    )
    if scout_terminal_status not in {"completed", "unresolved", "failed"}:
        raise ValueError("V2.42.31 scout terminal status is invalid")
    signals = _process_signals(
        process_signals, maximum=MAX_PROCESS_SIGNALS_PER_SCOUT
    )
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": SCOUT_ROLE,
        "policy_id": POLICY_ID,
        "baseline_only": True,
        "policy_sha256": policy["policy_sha256"],
        "root_scope_projection_sha256": root_scope_projection_sha256,
        "parent_node_ref_sha256": parent_node_ref_sha256,
        "homogeneous_group_ref_sha256": homogeneous_group_ref_sha256,
        "scout_slot": slot,
        "sibling_node_ref_sha256": sibling_node_ref_sha256,
        "sibling_mode_sha256": sibling_mode_sha256,
        "process_signals": signals,
        "model_calls": _integer(
            model_calls, label="scout model calls", minimum=0, maximum=MAX_COST_COUNT
        ),
        "search_calls": _integer(
            search_calls,
            label="scout search calls",
            minimum=0,
            maximum=MAX_COST_COUNT,
        ),
        "fetch_calls": _integer(
            fetch_calls, label="scout fetch calls", minimum=0, maximum=MAX_COST_COUNT
        ),
        "input_tokens": _integer(
            input_tokens, label="scout input tokens", minimum=0, maximum=MAX_COST_COUNT
        ),
        "output_tokens": _integer(
            output_tokens,
            label="scout output tokens",
            minimum=0,
            maximum=MAX_COST_COUNT,
        ),
        "wall_seconds": _finite(wall_seconds, label="scout wall seconds"),
        "scout_terminal_status": scout_terminal_status,
        "raw_task_query_url_page_text_answer_prediction_or_evaluator_payload_embedded": False,
        "raw_factual_value_visible_in_process_signal_schema": False,
        "process_fact_separation_independently_verified": False,
        "benchmark_label_mapping_gold_score_or_reward_used": False,
    }
    value["scout_trace_sha256"] = object_sha256(value)
    return value


def validate_scout_process_trace(
    value: Mapping[str, Any], *, policy: Mapping[str, Any]
) -> None:
    trace = _exact(value, keys=SCOUT_KEYS, label="scout trace")
    expected = build_scout_process_trace(
        policy=policy,
        root_scope_projection_sha256=str(trace.get("root_scope_projection_sha256")),
        parent_node_ref_sha256=str(trace.get("parent_node_ref_sha256")),
        homogeneous_group_ref_sha256=str(trace.get("homogeneous_group_ref_sha256")),
        scout_slot=trace.get("scout_slot"),
        sibling_node_ref_sha256=str(trace.get("sibling_node_ref_sha256")),
        sibling_mode_sha256=str(trace.get("sibling_mode_sha256")),
        process_signals=trace.get("process_signals"),
        model_calls=trace.get("model_calls"),
        search_calls=trace.get("search_calls"),
        fetch_calls=trace.get("fetch_calls"),
        input_tokens=trace.get("input_tokens"),
        output_tokens=trace.get("output_tokens"),
        wall_seconds=trace.get("wall_seconds"),
        scout_terminal_status=str(trace.get("scout_terminal_status")),
    )
    if dict(trace) != expected or not _sealed(trace, seal_key="scout_trace_sha256"):
        raise ValueError("V2.42.31 scout process trace contract drifted")


def build_sibling_process_experience(
    *,
    policy: Mapping[str, Any],
    scouts: Sequence[Mapping[str, Any]],
    experience_extractor_ref_sha256: str,
    process_signals: Sequence[Mapping[str, Any]],
    extractor_model_calls: int,
    extractor_input_tokens: int,
    extractor_output_tokens: int,
    extractor_wall_seconds: float,
) -> dict[str, Any]:
    validate_guidance_policy(policy)
    if isinstance(scouts, (str, bytes)) or not isinstance(scouts, Sequence):
        raise ValueError("V2.42.31 scouts must be a sequence")
    if len(scouts) != SCOUT_COUNT:
        raise ValueError("V2.42.31 exactly two scout traces are required")
    ordered = sorted((dict(scout) for scout in scouts), key=lambda row: row.get("scout_slot"))
    for scout in ordered:
        validate_scout_process_trace(scout, policy=policy)
    if [scout["scout_slot"] for scout in ordered] != [1, 2]:
        raise ValueError("V2.42.31 scout slots must be exactly one and two")
    roots = {str(scout["root_scope_projection_sha256"]) for scout in ordered}
    parents = {str(scout["parent_node_ref_sha256"]) for scout in ordered}
    groups = {str(scout["homogeneous_group_ref_sha256"]) for scout in ordered}
    modes = {str(scout["sibling_mode_sha256"]) for scout in ordered}
    nodes = {str(scout["sibling_node_ref_sha256"]) for scout in ordered}
    if any(len(values) != 1 for values in (roots, parents, groups, modes)):
        raise ValueError("V2.42.31 scouts are not same-parent homogeneous siblings")
    if len(nodes) != SCOUT_COUNT:
        raise ValueError("V2.42.31 scout sibling nodes are not distinct")
    if not _is_sha256(experience_extractor_ref_sha256):
        raise ValueError("V2.42.31 experience extractor is not SHA-256 bound")
    signals = _process_signals(
        process_signals, maximum=MAX_AGGREGATED_PROCESS_SIGNALS
    )
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": EXPERIENCE_ROLE,
        "policy_id": POLICY_ID,
        "baseline_only": True,
        "policy_sha256": policy["policy_sha256"],
        "root_scope_projection_sha256": ordered[0]["root_scope_projection_sha256"],
        "parent_node_ref_sha256": ordered[0]["parent_node_ref_sha256"],
        "homogeneous_group_ref_sha256": ordered[0]["homogeneous_group_ref_sha256"],
        "experience_extractor_ref_sha256": experience_extractor_ref_sha256,
        "source_scout_trace_sha256s": [
            str(scout["scout_trace_sha256"]) for scout in ordered
        ],
        "process_signals": signals,
        "extractor_model_calls": _integer(
            extractor_model_calls,
            label="extractor model calls",
            minimum=0,
            maximum=MAX_COST_COUNT,
        ),
        "extractor_input_tokens": _integer(
            extractor_input_tokens,
            label="extractor input tokens",
            minimum=0,
            maximum=MAX_COST_COUNT,
        ),
        "extractor_output_tokens": _integer(
            extractor_output_tokens,
            label="extractor output tokens",
            minimum=0,
            maximum=MAX_COST_COUNT,
        ),
        "extractor_wall_seconds": _finite(
            extractor_wall_seconds, label="extractor wall seconds"
        ),
        "same_instance_only": True,
        "same_parent_only": True,
        "homogeneous_siblings_only": True,
        "remaining_siblings_only": True,
        "process_advice_schema_only": True,
        "factual_evidence_authority": False,
        "raw_factual_value_visible_in_process_signal_schema": False,
        "process_fact_separation_independently_verified": False,
        "raw_scout_answer_query_url_page_text_or_evaluator_payload_embedded": False,
        "benchmark_label_mapping_gold_score_or_reward_used": False,
    }
    value["experience_sha256"] = object_sha256(value)
    return value


def validate_sibling_process_experience(
    value: Mapping[str, Any],
    *,
    policy: Mapping[str, Any],
    scouts: Sequence[Mapping[str, Any]],
) -> None:
    experience = _exact(value, keys=EXPERIENCE_KEYS, label="experience")
    expected = build_sibling_process_experience(
        policy=policy,
        scouts=scouts,
        experience_extractor_ref_sha256=str(
            experience.get("experience_extractor_ref_sha256")
        ),
        process_signals=experience.get("process_signals"),
        extractor_model_calls=experience.get("extractor_model_calls"),
        extractor_input_tokens=experience.get("extractor_input_tokens"),
        extractor_output_tokens=experience.get("extractor_output_tokens"),
        extractor_wall_seconds=experience.get("extractor_wall_seconds"),
    )
    if dict(experience) != expected or not _sealed(
        experience, seal_key="experience_sha256"
    ):
        raise ValueError("V2.42.31 sibling process experience contract drifted")


def _method_overhead_cost(
    *,
    probe: Mapping[str, Any] | None,
    experience: Mapping[str, Any] | None,
) -> dict[str, int | float]:
    value: dict[str, int | float] = {
        "model_calls": 0,
        "search_calls": 0,
        "fetch_calls": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "wall_seconds": 0.0,
    }
    if probe is not None:
        value["model_calls"] += int(probe["probe_model_calls"])
        value["search_calls"] += int(probe["probe_search_calls"])
        value["fetch_calls"] += int(probe["probe_fetch_calls"])
        value["input_tokens"] += int(probe["probe_input_tokens"])
        value["output_tokens"] += int(probe["probe_output_tokens"])
        value["wall_seconds"] += float(probe["probe_wall_seconds"])
    if experience is not None:
        value["model_calls"] += int(experience["extractor_model_calls"])
        value["input_tokens"] += int(experience["extractor_input_tokens"])
        value["output_tokens"] += int(experience["extractor_output_tokens"])
        value["wall_seconds"] += float(experience["extractor_wall_seconds"])
    value["wall_seconds"] = (
        0.0 if value["wall_seconds"] == 0.0 else value["wall_seconds"]
    )
    return value


def render_process_experience_prompt(
    *,
    experience: Mapping[str, Any],
    policy: Mapping[str, Any],
    scouts: Sequence[Mapping[str, Any]],
    root_scope_projection_sha256: str,
    parent_node_ref_sha256: str,
    homogeneous_group_ref_sha256: str,
) -> str:
    """Render executable generic advice without revealing fact projections."""

    validate_sibling_process_experience(
        experience,
        policy=policy,
        scouts=scouts,
    )
    if (
        experience["root_scope_projection_sha256"]
        != root_scope_projection_sha256
        or experience["parent_node_ref_sha256"] != parent_node_ref_sha256
        or experience["homogeneous_group_ref_sha256"]
        != homogeneous_group_ref_sha256
    ):
        raise ValueError("V2.42.31 experience prompt identity differs")
    signals = _process_signals(
        experience["process_signals"], maximum=MAX_AGGREGATED_PROCESS_SIGNALS
    )
    advice = list(
        dict.fromkeys(PROCESS_TACTIC_ADVICE[item["tactic"]] for item in signals)
    )
    return (
        "[SCOUT-DERIVED PROCESS ADVICE; NOT FACTUAL EVIDENCE]\n"
        + "\n".join(f"- {item}" for item in advice)
        + "\nDo not cite this advice as evidence. Verify all task facts from current "
        "page-backed sources."
    )


def build_guidance_arm(
    *,
    policy: Mapping[str, Any],
    arm_name: str,
    arm_ref_sha256: str,
    root_scope_projection_sha256: str,
    parent_node_ref_sha256: str,
    homogeneous_group_ref_sha256: str,
    sibling_count: int,
    scouts: Sequence[Mapping[str, Any]],
    probe: Mapping[str, Any] | None,
    experience: Mapping[str, Any] | None,
) -> dict[str, Any]:
    validate_guidance_policy(policy)
    if arm_name not in ARMS:
        raise ValueError("V2.42.31 guidance arm name is invalid")
    if not all(
        _is_sha256(value)
        for value in (
            arm_ref_sha256,
            root_scope_projection_sha256,
            parent_node_ref_sha256,
            homogeneous_group_ref_sha256,
        )
    ):
        raise ValueError("V2.42.31 arm identity is not SHA-256 bound")
    siblings = _integer(
        sibling_count,
        label="sibling count",
        minimum=SCOUT_COUNT + 1,
        maximum=MAX_SIBLINGS,
    )
    if isinstance(scouts, (str, bytes)) or not isinstance(scouts, Sequence):
        raise ValueError("V2.42.31 arm scouts must be a sequence")
    upstream_no_experience = arm_name == "no_experience_upstream"
    expected_scout_count = 0 if upstream_no_experience else SCOUT_COUNT
    if len(scouts) != expected_scout_count:
        raise ValueError("V2.42.31 arm scout schedule does not match its policy")
    for scout in scouts:
        validate_scout_process_trace(scout, policy=policy)
        if (
            scout["root_scope_projection_sha256"] != root_scope_projection_sha256
            or scout["parent_node_ref_sha256"] != parent_node_ref_sha256
            or scout["homogeneous_group_ref_sha256"] != homogeneous_group_ref_sha256
        ):
            raise ValueError("V2.42.31 arm and scout identities differ")
    probe_enabled = arm_name != "no_probing"
    experience_enabled = arm_name in {"full", "no_probing"}
    if probe_enabled:
        if probe is None:
            raise ValueError("V2.42.31 probing-enabled arm lacks a probe receipt")
        validate_web_probe_receipt(probe, policy=policy)
        if (
            probe["root_scope_projection_sha256"] != root_scope_projection_sha256
            or probe["parent_node_ref_sha256"] != parent_node_ref_sha256
        ):
            raise ValueError("V2.42.31 arm and probe identities differ")
    elif probe is not None:
        raise ValueError("V2.42.31 no-probing arm carries a probe receipt")
    if experience_enabled:
        if experience is None:
            raise ValueError("V2.42.31 experience-enabled arm lacks experience")
        validate_sibling_process_experience(
            experience, policy=policy, scouts=scouts
        )
        if (
            experience["root_scope_projection_sha256"]
            != root_scope_projection_sha256
            or experience["parent_node_ref_sha256"] != parent_node_ref_sha256
            or experience["homogeneous_group_ref_sha256"]
            != homogeneous_group_ref_sha256
        ):
            raise ValueError("V2.42.31 arm and experience identities differ")
    elif experience is not None:
        raise ValueError("V2.42.31 no-experience arm carries experience")
    cost = _method_overhead_cost(probe=probe, experience=experience)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ARM_ROLE,
        "policy_id": POLICY_ID,
        "baseline_only": True,
        "policy_sha256": policy["policy_sha256"],
        "arm_name": arm_name,
        "arm_ref_sha256": arm_ref_sha256,
        "root_scope_projection_sha256": root_scope_projection_sha256,
        "parent_node_ref_sha256": parent_node_ref_sha256,
        "homogeneous_group_ref_sha256": homogeneous_group_ref_sha256,
        "sibling_count": siblings,
        "scout_count": expected_scout_count,
        "fanout_count": siblings - expected_scout_count,
        "web_probing_enabled": probe_enabled,
        "experience_reuse_enabled": experience_enabled,
        "probe_receipt_sha256": (
            probe["probe_receipt_sha256"] if probe is not None else None
        ),
        "scout_trace_sha256s": sorted(
            str(scout["scout_trace_sha256"]) for scout in scouts
        ),
        "experience_sha256": (
            experience["experience_sha256"] if experience is not None else None
        ),
        "probe_extractor_cost": cost,
        "shared_model_contract_sha256": policy["model_contract_sha256"],
        "shared_search_fetch_contract_sha256": policy[
            "search_fetch_contract_sha256"
        ],
        "shared_total_budget_contract_sha256": policy[
            "total_budget_contract_sha256"
        ],
        "shared_root_scope_projection_protocol_sha256": policy[
            "root_scope_projection_protocol_sha256"
        ],
        "shared_user_prompt_and_output_contract": True,
        "same_sibling_schedule": not upstream_no_experience,
        "same_base_agent_budget_and_attempts": True,
        "method_specific_overhead_counted": True,
        "method_specific_overhead_debited_from_shared_total_cap": True,
        "experience_injected_only_into_remaining_siblings": experience_enabled,
        "experience_has_factual_evidence_authority": False,
        "benchmark_metadata_available_to_forward": False,
        "benchmark_forward_or_evaluator_authorized": BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED,
    }
    value["arm_sha256"] = object_sha256(value)
    return value


def validate_guidance_arm(
    value: Mapping[str, Any],
    *,
    policy: Mapping[str, Any],
    scouts: Sequence[Mapping[str, Any]],
    probe: Mapping[str, Any] | None,
    experience: Mapping[str, Any] | None,
) -> None:
    arm = _exact(value, keys=ARM_KEYS, label="guidance arm")
    cost = arm.get("probe_extractor_cost")
    if not isinstance(cost, Mapping) or set(cost) != COST_KEYS:
        raise ValueError("V2.42.31 guidance-arm cost schema is not exact")
    expected = build_guidance_arm(
        policy=policy,
        arm_name=str(arm.get("arm_name")),
        arm_ref_sha256=str(arm.get("arm_ref_sha256")),
        root_scope_projection_sha256=str(arm.get("root_scope_projection_sha256")),
        parent_node_ref_sha256=str(arm.get("parent_node_ref_sha256")),
        homogeneous_group_ref_sha256=str(
            arm.get("homogeneous_group_ref_sha256")
        ),
        sibling_count=arm.get("sibling_count"),
        scouts=scouts,
        probe=probe,
        experience=experience,
    )
    if dict(arm) != expected or not _sealed(arm, seal_key="arm_sha256"):
        raise ValueError("V2.42.31 guidance arm contract drifted")


def build_guidance_ablation_bundle(
    *,
    policy: Mapping[str, Any],
    bundle_ref_sha256: str,
    arms: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    validate_guidance_policy(policy)
    if not _is_sha256(bundle_ref_sha256):
        raise ValueError("V2.42.31 bundle identity is not SHA-256 bound")
    if isinstance(arms, (str, bytes)) or not isinstance(arms, Sequence):
        raise ValueError("V2.42.31 arms must be a sequence")
    if len(arms) != len(ARMS):
        raise ValueError("V2.42.31 bundle requires exactly four arms")
    ordered = sorted((dict(arm) for arm in arms), key=lambda row: str(row.get("arm_name")))
    for arm in ordered:
        _exact(arm, keys=ARM_KEYS, label="guidance arm")
        if not _sealed(arm, seal_key="arm_sha256"):
            raise ValueError("V2.42.31 guidance arm seal is invalid")
    names = {str(arm["arm_name"]) for arm in ordered}
    if names != set(ARMS):
        raise ValueError("V2.42.31 bundle arm set is not exact")
    expected_safe_values = {
        "artifact_version": 1,
        "role": ARM_ROLE,
        "policy_id": POLICY_ID,
        "baseline_only": True,
        "policy_sha256": policy["policy_sha256"],
        "shared_model_contract_sha256": policy["model_contract_sha256"],
        "shared_search_fetch_contract_sha256": policy[
            "search_fetch_contract_sha256"
        ],
        "shared_total_budget_contract_sha256": policy[
            "total_budget_contract_sha256"
        ],
        "shared_root_scope_projection_protocol_sha256": policy[
            "root_scope_projection_protocol_sha256"
        ],
        "shared_user_prompt_and_output_contract": True,
        "same_base_agent_budget_and_attempts": True,
        "method_specific_overhead_counted": True,
        "method_specific_overhead_debited_from_shared_total_cap": True,
        "experience_has_factual_evidence_authority": False,
        "benchmark_metadata_available_to_forward": False,
        "benchmark_forward_or_evaluator_authorized": False,
    }
    for arm in ordered:
        if any(arm[key] != expected for key, expected in expected_safe_values.items()):
            raise ValueError("V2.42.31 guidance arm safe invariant drifted")
    invariant_keys = (
        "policy_sha256",
        "root_scope_projection_sha256",
        "parent_node_ref_sha256",
        "homogeneous_group_ref_sha256",
        "sibling_count",
        "shared_model_contract_sha256",
        "shared_search_fetch_contract_sha256",
        "shared_total_budget_contract_sha256",
        "shared_root_scope_projection_protocol_sha256",
        "shared_user_prompt_and_output_contract",
        "same_base_agent_budget_and_attempts",
        "method_specific_overhead_counted",
        "method_specific_overhead_debited_from_shared_total_cap",
        "experience_has_factual_evidence_authority",
        "benchmark_metadata_available_to_forward",
        "benchmark_forward_or_evaluator_authorized",
    )
    for key in invariant_keys:
        if len({json.dumps(arm[key], sort_keys=True) for arm in ordered}) != 1:
            raise ValueError(f"V2.42.31 ablation invariant drifted: {key}")
    by_name = {str(arm["arm_name"]): arm for arm in ordered}
    if not (
        by_name["full"]["web_probing_enabled"] is True
        and by_name["full"]["experience_reuse_enabled"] is True
        and by_name["full"]["scout_count"] == SCOUT_COUNT
        and by_name["full"]["same_sibling_schedule"] is True
        and by_name["no_probing"]["web_probing_enabled"] is False
        and by_name["no_probing"]["experience_reuse_enabled"] is True
        and by_name["no_probing"]["scout_count"] == SCOUT_COUNT
        and len(by_name["no_probing"]["scout_trace_sha256s"]) == SCOUT_COUNT
        and by_name["no_probing"]["fanout_count"]
        == by_name["no_probing"]["sibling_count"] - SCOUT_COUNT
        and by_name["no_probing"]["same_sibling_schedule"] is True
        and by_name["no_experience_upstream"]["web_probing_enabled"] is True
        and by_name["no_experience_upstream"]["experience_reuse_enabled"] is False
        and by_name["no_experience_upstream"]["scout_count"] == 0
        and by_name["no_experience_upstream"]["fanout_count"]
        == by_name["no_experience_upstream"]["sibling_count"]
        and by_name["no_experience_upstream"]["same_sibling_schedule"] is False
        and by_name["no_experience_upstream"]["scout_trace_sha256s"] == []
        and by_name["no_experience_matched_schedule"]["web_probing_enabled"]
        is True
        and by_name["no_experience_matched_schedule"]["experience_reuse_enabled"]
        is False
        and by_name["no_experience_matched_schedule"]["scout_count"]
        == SCOUT_COUNT
        and len(
            by_name["no_experience_matched_schedule"]["scout_trace_sha256s"]
        )
        == SCOUT_COUNT
        and by_name["no_experience_matched_schedule"]["fanout_count"]
        == by_name["no_experience_matched_schedule"]["sibling_count"] - SCOUT_COUNT
        and by_name["no_experience_matched_schedule"]["same_sibling_schedule"]
        is True
        and _is_sha256(by_name["full"]["probe_receipt_sha256"])
        and _is_sha256(by_name["full"]["experience_sha256"])
        and _is_sha256(by_name["no_probing"]["experience_sha256"])
        and _is_sha256(
            by_name["no_experience_upstream"]["probe_receipt_sha256"]
        )
        and _is_sha256(
            by_name["no_experience_matched_schedule"]["probe_receipt_sha256"]
        )
        and by_name["no_probing"]["probe_receipt_sha256"] is None
        and by_name["no_experience_upstream"]["experience_sha256"] is None
        and by_name["no_experience_matched_schedule"]["experience_sha256"]
        is None
    ):
        raise ValueError("V2.42.31 ablation switches are not exact")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": BUNDLE_ROLE,
        "policy_id": POLICY_ID,
        "baseline_only": True,
        "policy_sha256": policy["policy_sha256"],
        "bundle_ref_sha256": bundle_ref_sha256,
        "arm_sha256s": {
            name: str(by_name[name]["arm_sha256"]) for name in ARMS
        },
        "arm_names": list(ARMS),
        "exact_arm_set": True,
        "only_guidance_switches_differ": False,
        "upstream_no_experience_schedule_difference_disclosed": True,
        "matched_schedule_no_experience_control_present": True,
        "probe_and_extractor_overhead_included": True,
        "same_model_search_fetch_prompt_output_budget_attempts": True,
        "shared_total_budget_cap_includes_method_overhead": True,
        "future_dev64_is_engineering_only": True,
        "future_reportable_score_requires_fresh_exact220": True,
        "failure_as_zero_no_resume_no_selective_retry": True,
        "single_owner_and_inherited_capacity_freeze_required": True,
        "quality_cost_or_benchmark_effect_observed": False,
        "leaderboard_submission_or_sota_claim_authorized": LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED,
    }
    value["bundle_sha256"] = object_sha256(value)
    return value


def validate_guidance_ablation_bundle(
    value: Mapping[str, Any],
    *,
    policy: Mapping[str, Any],
    bundle_ref_sha256: str,
    arms: Sequence[Mapping[str, Any]],
) -> None:
    bundle = _exact(value, keys=BUNDLE_KEYS, label="ablation bundle")
    arm_hashes = bundle.get("arm_sha256s")
    if not isinstance(arm_hashes, Mapping) or set(arm_hashes) != set(ARMS):
        raise ValueError("V2.42.31 bundle arm-hash schema is not exact")
    expected = build_guidance_ablation_bundle(
        policy=policy,
        bundle_ref_sha256=bundle_ref_sha256,
        arms=arms,
    )
    if dict(bundle) != expected or not _sealed(bundle, seal_key="bundle_sha256"):
        raise ValueError("V2.42.31 guidance ablation bundle contract drifted")
