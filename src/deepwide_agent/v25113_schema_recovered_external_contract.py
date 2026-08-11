"""Fresh external contract for exact-visible-schema recovery.

The twenty package identities were fixed only after an exact literal-zero scan
of ``FRESHNESS_PARENT_COMMIT``.  No package endpoint, page, value, model,
search, or evaluator was opened during selection.  Runtime input is exactly
``opaque_id`` and ``question``.  V2.51.10/11 is the only successor change;
the production budget is unchanged and the global model slot cap is reduced
from eight to four while task concurrency remains twenty.
"""

from __future__ import annotations

import ast
import copy
import hashlib
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from . import v25068_quote_verified_external_contract as base
from . import v25111_schema_recovered_paired_runtime as runtime


DATE = "20260811"
PROTOCOL_ID = "v25113_schema_recovered_external_mechanism_v1"
BUILD_AUDIT = Path(f"results/v25113_schema_recovered_external_build_audit_v1_{DATE}.json")
PROTOCOL = Path(f"results/v25113_schema_recovered_external_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v25113_schema_recovered_external_preactivation_audit_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v25113_schema_recovered_external_execution_start_v1_{DATE}.json")
FORWARD_RESULT = Path(f"results/v25113_schema_recovered_external_forward_result_v1_{DATE}.json")
FORWARD_AUDIT = Path(f"results/v25113_schema_recovered_external_forward_audit_v1_{DATE}.json")
EVALUATOR = Path("scripts/evaluate_v25113_schema_recovered_external.py")
EVALUATOR_TEST = Path("tests/test_evaluate_v25113_schema_recovered_external.py")
EVALUATOR_PROTOCOL = Path(
    f"results/v25113_schema_recovered_external_evaluator_preregistration_v1_{DATE}.json"
)
RESULT = Path(f"results/v25113_schema_recovered_external_result_v1_{DATE}.json")
POSTAUDIT = Path(f"results/v25113_schema_recovered_external_postresult_audit_v1_{DATE}.json")
OUTPUT_ROOT = Path(f"outputs/v25113_schema_recovered_external_v1_{DATE}")
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
TASK_ROWS = OUTPUT_ROOT / "frozen_task_results.jsonl"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
POSTFREEZE_GOLD = OUTPUT_ROOT / "postfreeze_pypi_gold.jsonl"

CONTRACT = Path("src/deepwide_agent/v25113_schema_recovered_external_contract.py")
RUNNER = Path("scripts/run_v25113_schema_recovered_external.py")
CONTROL = Path("scripts/control_v25113_schema_recovered_external.py")
TEST = Path("tests/test_v25113_schema_recovered_external.py")
HELPER = base.HELPER
PARENT_AUDIT = Path("results/v25112_schema_recovered_build_audit_v1_20260811.json")
PARENT_AUDIT_SHA256 = "2b5abd9fc72a62015ee5bff981ef4a6310ecf0064732b6834cc9ed637e73d9cd"
FORWARD_SOURCES = (CONTRACT, RUNNER, HELPER)

TASK_COUNT = 20
EXECUTOR_CONCURRENCY = 20
MODEL_SLOT_CAP = 4
FRESHNESS_PARENT_COMMIT = "46381b2ec145a40ff246c2eb087f93d8753c299c"
LEASE_PATH = base.LEASE_PATH
LEASE_OWNER = "v25113_schema_recovered_external_forward_v1"
LEASE_PURPOSE = "fresh_label_blind_exact_visible_schema_recovery_mechanism_gate"
MODEL = copy.deepcopy(base.MODEL)
SEARCH = copy.deepcopy(base.SEARCH)
LIMITS = copy.deepcopy(base.LIMITS)
CLEANUP_RESERVE_SECONDS = base.CLEANUP_RESERVE_SECONDS
MINIMUM_MODEL_ATTEMPT_SECONDS = base.MINIMUM_MODEL_ATTEMPT_SECONDS
ARMS = runtime.ARMS
CONTROL_ARM, CANDIDATE_ARM = ARMS
COLUMNS = base.COLUMNS
EXPECTED_WATCHERS = base.EXPECTED_WATCHERS

PROJECTS = (
    "shtab",
    "beaupy",
    "dataclass-wizard",
    "typedload",
    "pydantic-xml",
    "xsdata",
    "jsonref",
    "jsonmerge",
    "jsondiff",
    "niquests",
    "requests-mock",
    "httpx-sse",
    "httpx-ws",
    "aiohttp-retry",
    "aiohttp-client-cache",
    "jaxtyping",
    "multimethod",
    "dirtyjson",
    "demjson3",
    "pyjson5",
)
_SECRET_PREFIXES = ("gh" + "p_", "github_" + "pat_", "tvly-" + "dev-", "s" + "k-")
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:"
    + "|".join(re.escape(value) for value in _SECRET_PREFIXES)
    + r")[A-Za-z0-9_-]{16,}"
)

payload_sha256 = base.payload_sha256
sha256 = base.sha256
seal = base.seal
sealed = base.sealed
git = base.git
ordinary = base.ordinary
watcher_snapshot = base.watcher_snapshot


def task_vector() -> list[dict[str, str]]:
    if len(PROJECTS) != TASK_COUNT or len(set(PROJECTS)) != TASK_COUNT:
        raise RuntimeError("V2.51.13 project vector drifted")
    rows: list[dict[str, str]] = []
    for project in PROJECTS:
        opaque = "task_" + hashlib.sha256(f"v25113:{project}".encode()).hexdigest()[:24]
        question = (
            "Use public web sources, with PyPI as the visible authority for package release metadata, "
            "to return exactly one Markdown table and no prose. "
            f"Include exactly one row for the visible Python package identity <PACKAGE>{project}</PACKAGE>. "
            "Columns exactly: "
            + " | ".join(COLUMNS)
            + ". Use the canonical PyPI project name in Package. "
            "Latest release date means the earliest file upload date in the latest release, in YYYY-MM-DD form. "
            "Preserve the Requires-Python expression while collapsing whitespace. Values for one row must belong "
            "to the same package and release record. Use Unknown only when fetched public pages do not establish a value."
        )
        rows.append({"opaque_id": opaque, "question": question})
    return validate_task_vector(rows)


def validate_task_vector(values: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
    if isinstance(values, (str, bytes)) or len(values) != TASK_COUNT:
        raise ValueError("V2.51.13 task denominator drifted")
    output: list[dict[str, str]] = []
    for value, project in zip(values, PROJECTS, strict=True):
        if (
            not isinstance(value, Mapping)
            or set(value) != {"opaque_id", "question"}
            or re.fullmatch(r"task_[0-9a-f]{24}", str(value.get("opaque_id") or ""))
            is None
            or not isinstance(value.get("question"), str)
            or f"<PACKAGE>{project}</PACKAGE>" not in value["question"]
            or "Columns exactly: " + " | ".join(COLUMNS) not in value["question"]
            or "https://" in value["question"]
        ):
            raise ValueError("V2.51.13 visible task drifted")
        output.append({"opaque_id": str(value["opaque_id"]), "question": value["question"]})
    if len({row["opaque_id"] for row in output}) != TASK_COUNT:
        raise ValueError("V2.51.13 opaque identity collision")
    return output


def arm_order_vector() -> list[list[str]]:
    tasks = task_vector()
    ranked = sorted(
        range(TASK_COUNT),
        key=lambda index: hashlib.sha256(
            f"v25113-arm-order:{tasks[index]['opaque_id']}".encode()
        ).hexdigest(),
    )
    candidate_first = set(ranked[: TASK_COUNT // 2])
    return [
        [CANDIDATE_ARM, CONTROL_ARM]
        if index in candidate_first
        else [CONTROL_ARM, CANDIDATE_ARM]
        for index in range(TASK_COUNT)
    ]


def source_policy() -> dict[str, Any]:
    return {
        "runtime_boundary": ["opaque_id", "question", "same_forward_public_pages"],
        "fresh_population_selected_by_parent_history_literal_zero_scan_only": True,
        "population_endpoint_page_answer_model_or_evaluator_not_opened_before_freeze": True,
        "columns_exactly_pipe_schema_parsed_from_visible_question_only": True,
        "visible_schema_forced_on_plan_envelope_even_after_plan_effect_failure": True,
        "plan_proposal_transport_and_representation_failures_accounted_separately": True,
        "one_visible_only_plan_four_queries_shared_by_both_arms": True,
        "both_arms_share_queries_search_responses_fetched_pages_and_record_proposal": True,
        "only_treatment_is_same_length_verified_field_enforced_representation": True,
        "visible_identity_requires_exact_url_segment_and_title_or_leading_segment": True,
        "one_strict_identity_page_or_one_unique_visible_authority_winner_is_given_to_field_proposal": True,
        "visible_authority_is_explicitly_scoped_to_package_release_metadata": True,
        "exact_target_column_value_shape_corroboration_is_fail_closed": True,
        "selected_authority_page_is_rebased_to_local_ordinal_one": True,
        "every_non_key_column_requires_one_ordered_found_or_unavailable_disposition": True,
        "only_found_dispositions_enter_the_unchanged_value_shape_verifier": True,
        "verified_fields_are_deterministically_enforced_only_in_the_unique_identity_row": True,
        "whitespace_only_pages_use_one_canonical_usable_page_count": True,
        "zero_usable_pages_still_preserve_equal_fixed_model_budget": True,
        "model_slot_cap_reduced_from_eight_to_four_with_twenty_task_concurrency": True,
        "model_does_not_propose_identity_anchor_or_quote": True,
        "field_quotes_are_deterministically_derived_from_unique_minimum_label_value_spans": True,
        "cross_page_cross_identity_cross_record_or_cross_release_join_forbidden": True,
        "robust_late_page_bound_search_client_required": True,
        "query_fetch_model_context_token_wall_and_network_byte_caps_not_expanded": True,
        "query_local_mapping_failure_is_coverage_diagnostic_not_terminal_transport_failure": True,
        "terminal_hard_failure_uses_transport_timeout_helper_or_model_effect_receipts_only": True,
        "candidate_prediction_identity_handoff_required_when_candidate_evidence_is_unchanged": True,
        "prediction_change_counts_only_when_candidate_evidence_changed": True,
        "representation_validation_failure_is_safe_identity_handoff": True,
        "post_synthesis_accounting_or_receipt_validation_failure_is_terminal_no_go": True,
        "fixed_twenty_failure_as_zero_denominator_no_retry_resume_skip_or_replacement": True,
        "prediction_freeze_precedes_gold_evaluator_or_quality_decision": True,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "deepwidebench_dev64_exact220_leaderboard_or_sota_authorized": False,
    }


def mechanism_gate() -> dict[str, Any]:
    return {
        "fixed_task_denominator": TASK_COUNT,
        "terminal_tasks": TASK_COUNT,
        "completed_runtime_tasks": TASK_COUNT,
        "both_arms_model_success_tasks": TASK_COUNT,
        "minimum_tasks_with_usable_page": 16,
        "minimum_verifier_exposure_tasks": 8,
        "minimum_prediction_changed_tasks": 4,
        "minimum_exposed_and_prediction_changed_tasks": 4,
        "maximum_unexposed_and_prediction_changed_tasks": 0,
        "maximum_plan_model_effect_failures": 0,
        "maximum_plan_transport_failures": 0,
        "maximum_plan_output_validation_failures": 0,
        "maximum_proposal_model_effect_failures": 0,
        "maximum_proposal_transport_failures": 0,
        "maximum_representation_validation_failures": 0,
        "exact_planned_and_physical_queries_per_completed_task": 4,
        "maximum_physical_fetches_per_completed_task": 10,
        "exact_physical_model_logical_calls_per_completed_task": 4,
        "exact_effective_model_logical_calls_per_completed_arm": 3,
        "equal_control_candidate_evidence_characters_per_task": True,
        "frozen_arm_order_exact": True,
        "maximum_terminal_transport_timeout_helper_model_or_outer_hard_failures": 0,
        "maximum_post_synthesis_accounting_or_receipt_validation_failures": 0,
        "candidate_arm_model_hard_failures_not_greater_than_control": True,
    }


def quality_gate() -> dict[str, Any]:
    return {
        "fixed_denominator": TASK_COUNT,
        "candidate_exact_strict_gain": True,
        "candidate_composite_nonregression": True,
        "entity_row_item_column_nonregression": True,
        "invalid_or_fallback_nonincrease": True,
        "same_search_fetch_evidence_length_and_effective_model_budget": True,
    }


def forward_dependency_closure(root: Path) -> tuple[Path, ...]:
    pending = list(FORWARD_SOURCES)
    observed: set[Path] = set()
    while pending:
        relative = pending.pop()
        if relative in observed:
            continue
        path = ordinary(root, relative, tracked=False)
        observed.add(relative)
        if path.suffix != ".py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            for candidate in base._module_candidates(relative, node):
                if (root / candidate).is_file() and not (root / candidate).is_symlink():
                    pending.append(candidate)
    return tuple(sorted(observed, key=str))


def dependency_manifest(root: Path, *, tracked: bool) -> dict[str, str]:
    relatives = {*forward_dependency_closure(root), CONTROL, TEST, PARENT_AUDIT}
    output: dict[str, str] = {}
    for relative in sorted(relatives, key=str):
        path = ordinary(root, relative, tracked=tracked)
        if SECRET.search(path.read_text(encoding="utf-8")):
            raise RuntimeError("V2.51.13 credential literal in source manifest")
        output[str(relative)] = sha256(path)
    return output


def build_protocol(
    root: Path,
    *,
    now: int,
    tracked: bool,
    require_pristine: bool,
    build_audit_sha256: str,
) -> dict[str, Any]:
    future = (
        PROTOCOL,
        PREAUDIT,
        EXECUTION_START,
        FORWARD_RESULT,
        FORWARD_AUDIT,
        EVALUATOR,
        EVALUATOR_TEST,
        EVALUATOR_PROTOCOL,
        RESULT,
        POSTAUDIT,
        OUTPUT_ROOT,
    )
    if require_pristine and any(
        (root / path).exists() or (root / path).is_symlink() for path in future
    ):
        raise RuntimeError("V2.51.13 future surface is not pristine")
    if sha256(root / PARENT_AUDIT) != PARENT_AUDIT_SHA256:
        raise RuntimeError("V2.51.13 parent audit drifted")
    manifest = dependency_manifest(root, tracked=tracked)
    tasks = task_vector()
    value = {
        "artifact_version": 1,
        "role": "v25113_schema_recovered_external_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(now),
        "build_audit_sha256": build_audit_sha256,
        "parent": {"path": str(PARENT_AUDIT), "sha256": PARENT_AUDIT_SHA256},
        "freshness": {
            "parent_commit": FRESHNESS_PARENT_COMMIT,
            "parent_history_literal_zero_hit_projects": list(PROJECTS),
            "endpoint_page_value_model_or_evaluator_opened_during_selection": False,
        },
        "population": {
            "task_count": TASK_COUNT,
            "project_vector_sha256": payload_sha256(PROJECTS),
            "task_vector_sha256": payload_sha256(tasks),
            "opaque_id_vector_sha256": payload_sha256([row["opaque_id"] for row in tasks]),
            "arm_order_vector_sha256": payload_sha256(arm_order_vector()),
        },
        "execution": {
            "arms": list(ARMS),
            "only_treatment": "same_length_verified_field_enforced_representation",
            "exact_visible_schema_recovery": True,
            "separated_stage_failure_accounting": True,
            "executor_concurrency": EXECUTOR_CONCURRENCY,
            "model_slot_cap": MODEL_SLOT_CAP,
            "model": copy.deepcopy(MODEL),
            "search": copy.deepcopy(SEARCH),
            "limits": copy.deepcopy(LIMITS),
            "query_policy": "one_visible_only_plan_four_queries_shared_by_both_arms",
            "physical_paired_model_call_cap": 4,
            "effective_model_call_cap_per_arm": 3,
            "unexposed_prediction_identity_handoff": True,
            "representation_validation_failure_safe_identity_handoff": True,
            "post_synthesis_accounting_or_receipt_validation_failure_terminal_no_go": True,
            "single_atomic_forward_no_retry_resume_skip_or_replacement": True,
        },
        "mechanism_gate": mechanism_gate(),
        "quality_gate": quality_gate(),
        "protected_watchers": watcher_snapshot(),
        "source_manifest": manifest,
        "source_manifest_sha256": payload_sha256(manifest),
        "source_policy": source_policy(),
        "authorization": {
            "one_external_forward_after_separate_clean_pushed_start": True,
            "evaluator_implementation_only_after_prediction_freeze_and_pushed_forward_audit_go": True,
            "deepwidebench_dev64_exact220_or_sota": False,
            "retry_resume_skip_population_replacement_or_selective_revaluation": False,
        },
    }
    return seal(value, "protocol_payload_sha256")


def validate_protocol(root: Path, value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    expected = build_protocol(
        root,
        now=int(copied.get("created_at_unix", -1)),
        tracked=True,
        require_pristine=False,
        build_audit_sha256=sha256(root / BUILD_AUDIT),
    )
    if copied != expected or not sealed(copied, "protocol_payload_sha256"):
        raise RuntimeError("V2.51.13 protocol drifted")
    return copied


__all__ = [name for name in globals() if name.isupper()] + [
    "arm_order_vector",
    "build_protocol",
    "dependency_manifest",
    "forward_dependency_closure",
    "git",
    "mechanism_gate",
    "ordinary",
    "payload_sha256",
    "quality_gate",
    "seal",
    "sealed",
    "sha256",
    "source_policy",
    "task_vector",
    "validate_protocol",
    "validate_task_vector",
    "watcher_snapshot",
]
