#!/usr/bin/env python3
"""Counts-only diagnosis of the V2.47.84 projection-closure NO-GO.

The diagnostic consumes only the tracked, post-freeze V2.47.84 forward audit.
It never opens V2.47.84 outputs, visible tasks, predictions, pages, private
catalogs, population truth/provenance/quality, benchmark mappings, evaluator
inputs, labels, scores, or rewards.  Pure synthetic Alpha/example pages test
whether the frozen Founded/Country projection and support pipeline can close.

The aggregate receipt does not reveal whether the one Unknown projection group
is one of the two multi-source groups.  This diagnostic therefore reports the
sharp set intersection bounds and refuses to infer task-local co-occurrence.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24333_programmatic_support_catalog as support  # noqa: E402
from deepwide_agent import v24365_entity_segment_projection as segment  # noqa: E402
from deepwide_agent import v24743_generic_record_binding as binder  # noqa: E402
from deepwide_agent import v24781_projection_conversion_funnel as funnel  # noqa: E402
from deepwide_agent import v24784_projection_funnel_execution_contract as contract  # noqa: E402


PARENT = contract.FORWARD_AUDIT
OUTPUT = Path("results/v24785_v24784_projection_closure_diagnosis_v1_20260807.json")
SOURCE = Path("scripts/diagnose_v24785_v24784_projection_closure.py")
TEST = Path("tests/test_diagnose_v24785_v24784_projection_closure.py")
SOURCES = (
    PARENT,
    SOURCE,
    TEST,
    Path("src/deepwide_agent/v24333_programmatic_support_catalog.py"),
    Path("src/deepwide_agent/v24365_entity_segment_projection.py"),
    Path("src/deepwide_agent/v24743_generic_record_binding.py"),
    Path("src/deepwide_agent/v24781_projection_conversion_funnel.py"),
)
SECRET_PREFIXES = ("gh" + "p_", "github_" + "pat_", "tvly-" + "dev-", "s" + "k-")
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:"
    + "|".join(re.escape(value) for value in SECRET_PREFIXES)
    + r")[A-Za-z0-9_-]{16,}"
)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
        check=True,
    ).stdout.strip()


def _tracked(relative: Path) -> bool:
    return subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(relative)],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=20,
        check=False,
    ).returncode == 0


def _ordinary(relative: Path) -> Path:
    path = ROOT / relative
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or relative.parts[:1] in {("evaluation",), ("outputs",)}
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(ROOT.resolve())
        or not _tracked(relative)
    ):
        raise RuntimeError(f"V2.47.85 expected tracked public file: {relative}")
    return path


def _sha256(relative: Path) -> str:
    digest = hashlib.sha256()
    with _ordinary(relative).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read(relative: Path) -> dict[str, Any]:
    value = json.loads(_ordinary(relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.47.85 expected JSON object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == contract.payload_sha256(unsigned)


def _manifest() -> dict[str, str]:
    output: dict[str, str] = {}
    for relative in SOURCES:
        raw = _ordinary(relative).read_bytes()
        if SECRET.search(raw.decode("utf-8", errors="ignore")):
            raise RuntimeError("V2.47.85 credential literal found")
        output[str(relative)] = hashlib.sha256(raw).hexdigest()
    return output


def _parent() -> dict[str, Any]:
    value = _read(PARENT)
    metrics = value.get("content_free_effect_metrics", {})
    counts = value.get("replayed_summary_counts", {})
    if (
        value.get("role") != "v24784_projection_funnel_forward_audit"
        or value.get("protocol_id") != contract.PROTOCOL_ID
        or value.get("forward_health_go") is not True
        or value.get("mechanism_go") is not False
        or value.get("findings")
        != [
            "minimum_changed_cell_count",
            "minimum_changed_task_count",
            "minimum_projection_backed_support_task_count",
            "minimum_strict_task_local_joint_projection_backed_safe_change",
            "minimum_unconflicted_projection_backed_unknown_proposal_task_count",
        ]
        or metrics.get("strict_task_local_joint_count") != 0
        or counts.get("status_validated_count") != 8
        or counts.get("projection_emitted_pair_count") != 17
        or counts.get("projection_emitted_task_count") != 7
        or counts.get("distinct_target_value_projection_count") != 16
        or counts.get("projection_target_binding_count") != 15
        or counts.get("projection_unknown_target_value_group_count") != 1
        or counts.get("projection_single_source_group_count") != 14
        or counts.get("projection_two_or_more_source_group_count") != 2
        or counts.get("catalog_candidate_target_value_group_count") != 55
        or counts.get("catalog_eligible_support_set_count") != 0
        or counts.get("projection_backed_eligible_support_set_count") != 0
        or counts.get("unconflicted_projection_backed_unknown_proposal_count") != 0
        or counts.get("changed_cell_count") != 0
        or counts.get("nonunknown_changed_cell_count") != 0
        or value.get("authorization", {}).get(
            "additional_forward_retry_resume_or_rerun"
        )
        is not False
        or value.get("authorization", {}).get("paired_dev64_execution") is not False
        or value.get("authorization", {}).get("exact220") is not False
        or not _sealed(value, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.47.85 parent audit drifted")
    return value


def _intersection_bounds(left: int, right: int, universe: int) -> tuple[int, int]:
    values = (left, right, universe)
    if any(isinstance(value, bool) or not isinstance(value, int) for value in values):
        raise ValueError("V2.47.85 intersection counts must be integers")
    if universe < 0 or not 0 <= left <= universe or not 0 <= right <= universe:
        raise ValueError("V2.47.85 intersection counts are outside universe")
    return max(0, left + right - universe), min(left, right)


def _synthetic_page(host: str, content: str) -> dict[str, Any]:
    return {"host": host, "content": content, "fetch_integrity": True}


def synthetic_closure() -> dict[str, Any]:
    cases = (
        (
            "Founded",
            "Alpha was founded in 1999.",
            "Alpha was established in 1999.",
        ),
        (
            "Country",
            "Alpha is based in France.",
            "Alpha is located in France.",
        ),
    )
    rows = []
    for column, left, right in cases:
        target = support.CellTarget("Alpha", column, "Unknown")
        catalog = segment.build_target_segment_catalog(
            [target],
            [_synthetic_page("one.example", left)],
            [_synthetic_page("two.example", right)],
        )
        receipt = funnel.build_projection_conversion_funnel(catalog)
        rows.append(
            {
                "column_kind": column.casefold(),
                "semantic_projection_count": int(
                    catalog["semantic_projection_count"]
                ),
                "catalog_eligible_support_set_count": int(
                    catalog["eligible_support_set_count"]
                ),
                "projection_two_or_more_source_group_count": int(
                    receipt["projection_two_or_more_source_group_count"]
                ),
                "projection_unknown_target_value_group_count": int(
                    receipt["projection_unknown_target_value_group_count"]
                ),
                "projection_backed_eligible_support_set_count": int(
                    receipt["projection_backed_eligible_support_set_count"]
                ),
                "unconflicted_projection_backed_unknown_proposal_count": int(
                    receipt[
                        "unconflicted_projection_backed_unknown_proposal_count"
                    ]
                ),
            }
        )
    return {
        "cases": rows,
        "all_cases_close_two_source_unknown_proposal": all(
            row
            == {
                "column_kind": row["column_kind"],
                "semantic_projection_count": 2,
                "catalog_eligible_support_set_count": 1,
                "projection_two_or_more_source_group_count": 1,
                "projection_unknown_target_value_group_count": 1,
                "projection_backed_eligible_support_set_count": 1,
                "unconflicted_projection_backed_unknown_proposal_count": 1,
            }
            for row in rows
        ),
        "synthetic_entity_or_value_from_benchmark": False,
        "file_environment_network_model_search_fetch_process_or_evaluator_effect": False,
    }


def source_key_equivalence() -> dict[str, Any]:
    hosts = (
        "one.example",
        "a.example.org",
        "foo.ac.uk",
        "bar.foo.ac.uk",
        "example.com.au",
        "sub.example.com.au",
    )
    rows = [
        {
            "host_sha256": hashlib.sha256(host.encode()).hexdigest(),
            "binder_source_sha256": hashlib.sha256(
                binder._source_key(host).encode()
            ).hexdigest(),
            "catalog_source_sha256": hashlib.sha256(
                support._source_key(host).encode()
            ).hexdigest(),
            "equal": binder._source_key(host) == support._source_key(host),
        }
        for host in hosts
    ]
    return {
        "common_suffix_sets_equal": binder.COMMON_SECOND_LEVEL_SUFFIXES
        == support.COMMON_SECOND_LEVEL_SUFFIXES,
        "synthetic_host_case_count": len(rows),
        "synthetic_host_cases": rows,
        "all_synthetic_source_keys_equal": all(row["equal"] for row in rows),
    }


def build_diagnosis(*, now: int | None = None) -> dict[str, Any]:
    parent = _parent()
    counts = parent["replayed_summary_counts"]
    unknown_groups = int(counts["projection_unknown_target_value_group_count"])
    multisource_groups = int(counts["projection_two_or_more_source_group_count"])
    distinct_groups = int(counts["distinct_target_value_projection_count"])
    lower, upper = _intersection_bounds(
        unknown_groups, multisource_groups, distinct_groups
    )
    synthetic = synthetic_closure()
    source_keys = source_key_equivalence()
    value = {
        "artifact_version": 1,
        "role": "v24785_v24784_projection_closure_counts_only_diagnosis",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parent_forward_audit_sha256": _sha256(PARENT),
        "source_manifest": _manifest(),
        "source_manifest_sha256": contract.payload_sha256(_manifest()),
        "observed_counts": {
            name: int(counts[name])
            for name in (
                "target_count",
                "baseline_unknown_target_count",
                "projection_emitted_pair_count",
                "projection_emitted_task_count",
                "distinct_target_value_projection_count",
                "projection_target_binding_count",
                "projection_unknown_target_value_group_count",
                "projection_single_source_group_count",
                "projection_two_or_more_source_group_count",
                "projection_conflicting_target_binding_count",
                "catalog_candidate_target_value_group_count",
                "catalog_eligible_support_set_count",
                "projection_backed_eligible_support_set_count",
                "unconflicted_projection_backed_unknown_proposal_count",
                "changed_cell_count",
                "nonunknown_changed_cell_count",
                "task_local_joint_projection_backed_safe_change_task_count",
            )
        },
        "identifiability": {
            "unknown_and_multisource_group_intersection_lower_bound": lower,
            "unknown_and_multisource_group_intersection_upper_bound": upper,
            "unknown_group_is_proven_multisource": lower == upper == unknown_groups,
            "unknown_group_is_proven_single_source": upper == 0,
            "aggregate_cross_task_or_cross_group_cooccurrence_used_as_joint": False,
            "unknown_multisource_intersection_not_identified_by_parent_receipt": lower
            != upper,
        },
        "synthetic_projection_support_closure": synthetic,
        "source_key_equivalence": source_keys,
        "diagnosis": {
            "transport_or_funnel_validation_is_primary_bottleneck": False,
            "projection_parser_has_zero_capacity": False,
            "projection_to_support_pipeline_has_systematic_founded_or_country_incompatibility": False,
            "source_key_implementation_mismatch_supported_as_primary_bottleneck": False,
            "safe_unknown_fill_failed_because_no_projection_backed_two_source_unknown_support_set_closed": True,
            "whether_parent_multisource_groups_intersect_unknown_group_is_identified": False,
            "current_counts_are_consistent_with_multisource_groups_only_on_known_cells": True,
            "current_counts_are_also_consistent_with_an_unknown_multisource_group_quarantined_before_support": True,
            "support_threshold_should_be_relaxed": False,
        },
        "next_falsification": {
            "same_v24784_population_retry_resume_or_selective_rerun": False,
            "fresh_entity_and_task_disjoint_population_required": True,
            "cross_tab_observer_must_count_unknown_by_source_multiplicity_jointly": True,
            "cross_tab_observer_must_count_catalog_quarantine_dispositions": True,
            "one_baseline_unknown_target_per_task": True,
            "unknown_target_fetch_budget_concentrated_without_relaxing_two_source_gate": True,
            "same_model_query_fetch_caps_as_successor_protocol_required": True,
            "positive_epistemic_credit_for_entity_localization_or_page_volume": False,
            "positive_decision_credit_before_safe_change_and_outer_utility": False,
            "evaluator_before_mechanism_gate": False,
        },
        "source_policy": {
            "v24784_output_visible_task_prediction_page_result_or_private_catalog_opened_or_hashed": False,
            "v24783_private_population_truth_provenance_or_quality_opened_or_hashed": False,
            "benchmark_manifest_mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "credential_read_hashed_persisted_or_emitted": False,
            "network_model_search_fetch_benchmark_or_evaluator_called": False,
            "only_tracked_counts_only_parent_and_pure_synthetic_inputs_used": True,
        },
        "claim_scope": {
            "deepwidebench_score_measured": False,
            "entropy_or_credit_assignment_validated": False,
            "leaderboard_or_sota_supported": False,
        },
        "authorization": {
            "append_only_cross_tab_observer_build": True,
            "fresh_disjoint_population_design": True,
            "activation_or_external_launch": False,
            "same_population_retry_resume_or_selective_rerun": False,
            "private_truth_or_quality_surface_open": False,
            "paired_dev64": False,
            "exact220": False,
            "entropy_or_credit_experiment": False,
            "leaderboard_or_sota": False,
        },
    }
    value["diagnosis_payload_sha256"] = contract.payload_sha256(value)
    return validate_diagnosis(value)


def validate_diagnosis(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("diagnosis_payload_sha256", None)
    identified = copied.get("identifiability", {})
    synthetic = copied.get("synthetic_projection_support_closure", {})
    keys = copied.get("source_key_equivalence", {})
    if (
        copied.get("role")
        != "v24785_v24784_projection_closure_counts_only_diagnosis"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("parent_forward_audit_sha256") != _sha256(PARENT)
        or copied.get("source_manifest") != _manifest()
        or copied.get("source_manifest_sha256")
        != contract.payload_sha256(copied["source_manifest"])
        or identified
        != {
            "unknown_and_multisource_group_intersection_lower_bound": 0,
            "unknown_and_multisource_group_intersection_upper_bound": 1,
            "unknown_group_is_proven_multisource": False,
            "unknown_group_is_proven_single_source": False,
            "aggregate_cross_task_or_cross_group_cooccurrence_used_as_joint": False,
            "unknown_multisource_intersection_not_identified_by_parent_receipt": True,
        }
        or synthetic != synthetic_closure()
        or synthetic.get("all_cases_close_two_source_unknown_proposal") is not True
        or keys != source_key_equivalence()
        or keys.get("common_suffix_sets_equal") is not True
        or keys.get("all_synthetic_source_keys_equal") is not True
        or copied.get("diagnosis", {}).get("support_threshold_should_be_relaxed")
        is not False
        or copied.get("diagnosis", {}).get(
            "whether_parent_multisource_groups_intersect_unknown_group_is_identified"
        )
        is not False
        or copied.get("next_falsification", {}).get(
            "same_v24784_population_retry_resume_or_selective_rerun"
        )
        is not False
        or copied.get("source_policy")
        != {
            "v24784_output_visible_task_prediction_page_result_or_private_catalog_opened_or_hashed": False,
            "v24783_private_population_truth_provenance_or_quality_opened_or_hashed": False,
            "benchmark_manifest_mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "credential_read_hashed_persisted_or_emitted": False,
            "network_model_search_fetch_benchmark_or_evaluator_called": False,
            "only_tracked_counts_only_parent_and_pure_synthetic_inputs_used": True,
        }
        or copied.get("claim_scope")
        != {
            "deepwidebench_score_measured": False,
            "entropy_or_credit_assignment_validated": False,
            "leaderboard_or_sota_supported": False,
        }
        or copied.get("authorization")
        != {
            "append_only_cross_tab_observer_build": True,
            "fresh_disjoint_population_design": True,
            "activation_or_external_launch": False,
            "same_population_retry_resume_or_selective_rerun": False,
            "private_truth_or_quality_surface_open": False,
            "paired_dev64": False,
            "exact220": False,
            "entropy_or_credit_experiment": False,
            "leaderboard_or_sota": False,
        }
        or seal != contract.payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.47.85 diagnosis drifted")
    return copied


def publish_new(path: Path, value: Mapping[str, Any]) -> None:
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


if __name__ == "__main__":
    diagnosis = build_diagnosis()
    publish_new(ROOT / OUTPUT, diagnosis)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "unknown_multisource_intersection_bounds": [
                    diagnosis["identifiability"][
                        "unknown_and_multisource_group_intersection_lower_bound"
                    ],
                    diagnosis["identifiability"][
                        "unknown_and_multisource_group_intersection_upper_bound"
                    ],
                ],
                "synthetic_closure": diagnosis[
                    "synthetic_projection_support_closure"
                ]["all_cases_close_two_source_unknown_proposal"],
                "external_launch": diagnosis["authorization"][
                    "activation_or_external_launch"
                ],
            },
            sort_keys=True,
        )
    )
