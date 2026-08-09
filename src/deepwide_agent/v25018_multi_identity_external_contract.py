"""Preregistered multi-row distinct-identity detail external gate.

Twenty tasks each enumerate four fresh IANA identities.  Runtime input remains
exactly ``opaque_id`` and ``question``.  The population is frozen from the
public namespace order without accessing any final detail endpoint or page.
Gold and evaluator surfaces remain absent until predictions are frozen and the
mechanism audit authorizes a post-freeze quality protocol.
"""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from . import v24831_keyless_exact220_contract as production
from . import v25012_attested_detail_external_contract as prior12
from . import v25014_multi_identity_detail_fields as projector
from . import v25017_distinct_identity_detail_runtime as runtime


DATE = "20260809"
PROTOCOL_ID = "v25018_multi_identity_distinct_detail_external_gate_v1"
BUILD_AUDIT = Path(f"results/v25018_multi_identity_external_build_audit_v1_{DATE}.json")
PROTOCOL = Path(f"results/v25018_multi_identity_external_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v25018_multi_identity_external_preactivation_audit_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v25018_multi_identity_external_execution_start_v1_{DATE}.json")
FORWARD_RESULT = Path(f"results/v25018_multi_identity_external_forward_result_v1_{DATE}.json")
FORWARD_AUDIT = Path(f"results/v25018_multi_identity_external_forward_audit_v1_{DATE}.json")
EVALUATOR_PROTOCOL = Path(f"results/v25018_multi_identity_external_evaluator_preregistration_v1_{DATE}.json")
RESULT = Path(f"results/v25018_multi_identity_external_result_v1_{DATE}.json")
POSTAUDIT = Path(f"results/v25018_multi_identity_external_postresult_audit_v1_{DATE}.json")
OUTPUT_ROOT = Path(f"outputs/v25018_multi_identity_external_v1_{DATE}")
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
TASK_RESULTS = OUTPUT_ROOT / "frozen_task_results.jsonl"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
POSTFREEZE_GOLD = OUTPUT_ROOT / "postfreeze_iana_multi_identity_gold.json"
LEASE_PATH = production.LEASE_PATH
LEASE_OWNER = "v25018_multi_identity_external_forward_v1"
LEASE_PURPOSE = "fresh_label_blind_multi_identity_distinct_detail_gate"

SOURCE = Path("src/deepwide_agent/v25018_multi_identity_external_contract.py")
HISTORICAL_COHORT_SOURCE = prior12.SOURCE
PARENT_PROJECTOR = Path("src/deepwide_agent/v24980_late_page_bound_projection.py")
ROBUST_PROJECTOR = Path("src/deepwide_agent/v24984_robust_late_page_projection.py")
SINGLE_PROJECTOR = Path("src/deepwide_agent/v25004_identity_bound_detail_fields.py")
PROJECTOR = Path("src/deepwide_agent/v25014_multi_identity_detail_fields.py")
PARENT_FETCH = Path("src/deepwide_agent/v24981_late_page_bound_fetch.py")
ROBUST_FETCH = Path("src/deepwide_agent/v24985_robust_late_page_fetch.py")
FETCH = Path("src/deepwide_agent/v25016_multi_identity_detail_fetch.py")
PARENT_SELECTOR = Path("src/deepwide_agent/v24998_identity_authority_action_selection.py")
LINK_SELECTOR = Path("src/deepwide_agent/v25010_attested_child_detail_selection.py")
SELECTOR = Path("src/deepwide_agent/v25015_distinct_identity_child_selection.py")
PARENT_RUNTIME = Path("src/deepwide_agent/v25002_page_visible_link_paired_runtime.py")
RUNTIME = Path("src/deepwide_agent/v25017_distinct_identity_detail_runtime.py")
HELPER = Path("scripts/run_v25016_multi_identity_detail_fetch_helper.py")
CONTROL = Path("scripts/control_v25018_multi_identity_external.py")
RUNNER = Path("scripts/run_v25018_multi_identity_external.py")
EVALUATOR = Path("scripts/evaluate_v25018_multi_identity_external.py")
TEST = Path("tests/test_v25018_multi_identity_external.py")
TEST_SOURCES = (
    TEST,
    Path("tests/test_v24980_late_page_bound_projection.py"),
    Path("tests/test_v24981_late_page_bound_fetch.py"),
    Path("tests/test_v24984_robust_late_page_projection.py"),
    Path("tests/test_v24985_robust_late_page_fetch.py"),
    Path("tests/test_v24998_identity_authority_action_selection.py"),
    Path("tests/test_v24999_shared_response_selection_runtime.py"),
    Path("tests/test_v25001_page_visible_link_selection.py"),
    Path("tests/test_v25002_page_visible_link_paired_runtime.py"),
    Path("tests/test_v25004_identity_bound_detail_fields.py"),
    Path("tests/test_v25010_attested_child_detail_selection.py"),
    Path("tests/test_v25014_multi_identity_detail_fields.py"),
    Path("tests/test_v25015_distinct_identity_child_selection.py"),
    Path("tests/test_v25016_multi_identity_detail_fetch.py"),
    Path("tests/test_v25017_distinct_identity_detail_runtime.py"),
    Path("tests/test_native_search.py"),
    Path("tests/test_v24286_visible_schema_runtime.py"),
    Path("tests/test_v24259_deterministic_table_normalizer.py"),
)
LOCAL_SOURCES = (
    SOURCE,
    HISTORICAL_COHORT_SOURCE,
    PARENT_PROJECTOR,
    ROBUST_PROJECTOR,
    SINGLE_PROJECTOR,
    PROJECTOR,
    PARENT_FETCH,
    ROBUST_FETCH,
    FETCH,
    PARENT_SELECTOR,
    LINK_SELECTOR,
    SELECTOR,
    PARENT_RUNTIME,
    RUNTIME,
    HELPER,
    CONTROL,
    RUNNER,
    EVALUATOR,
    *TEST_SOURCES,
)

TASK_COUNT = 20
GROUP_SIZE = 4
IDENTITY_COUNT = TASK_COUNT * GROUP_SIZE
EXECUTOR_CONCURRENCY = 20
MODEL_SLOT_CAP = 8
LIMITS = copy.deepcopy(production.LIMITS)
MODEL = copy.deepcopy(production.MODEL)
SEARCH = copy.deepcopy(production.SEARCH)
ARMS = runtime.ARMS
CONTROL_ARM = runtime.CONTROL_ARM
CANDIDATE_ARM = runtime.CANDIDATE_ARM
PHASES = runtime.PHASES
PROTECTED_WATCHERS = production.PROTECTED_WATCHERS
COLUMNS = (
    "Domain",
    "Sponsoring Organisation",
    "Registration date",
    "Record last updated",
)
IANA_DETAIL_PREFIX = "https://www.iana.org/domains/root/db/"
MAX_GOLD_BYTES_PER_PAGE = 1_000_000

# First eighty alphabetic IANA identities after the frozen V2.50.12 cohort,
# skipping every identity in the prior 180-item history.  Selection used the
# public namespace spelling/order only; no endpoint or page was accessed.
TLD_COHORT = (
    ".art", ".arte", ".asda", ".asia", ".associates", ".athleta",
    ".attorney", ".auction", ".audi", ".audible", ".audio", ".auspost",
    ".author", ".auto", ".autos", ".avianca", ".aws", ".axa", ".azure",
    ".baby", ".baidu", ".banamex", ".bananarepublic", ".band", ".bank",
    ".bar", ".barcelona", ".barclaycard", ".barclays", ".barefoot",
    ".bargains", ".baseball", ".basketball", ".bauhaus", ".bayern",
    ".bbc", ".bbt", ".bbva", ".bcg", ".bcn", ".beats", ".beauty",
    ".beer", ".bentley", ".berlin", ".best", ".bestbuy", ".bet",
    ".bharti", ".bible", ".bid", ".bike", ".bing", ".bingo", ".bio",
    ".biz", ".black", ".blackfriday", ".blockbuster", ".blog",
    ".bloomberg", ".blue", ".bms", ".bmw", ".bnpparibas", ".boats",
    ".boehringer", ".bofa", ".bom", ".bond", ".boo", ".book",
    ".booking", ".bosch", ".bostik", ".boston", ".bot", ".boutique",
    ".box", ".bradesco",
)
HISTORICAL_TLD_COHORT = frozenset(
    (*prior12.HISTORICAL_TLD_COHORT, *prior12.TLD_COHORT)
)


def identity_groups() -> tuple[tuple[str, ...], ...]:
    if len(TLD_COHORT) != IDENTITY_COUNT:
        raise RuntimeError("V2.50.18 identity denominator drifted")
    return tuple(
        tuple(TLD_COHORT[start : start + GROUP_SIZE])
        for start in range(0, IDENTITY_COUNT, GROUP_SIZE)
    )


def detail_url(tld: str) -> str:
    if tld not in TLD_COHORT:
        raise ValueError("V2.50.18 detail identity is outside frozen cohort")
    return IANA_DETAIL_PREFIX + tld.removeprefix(".") + ".html"


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=20,
        check=True,
    ).stdout.strip()


def seal(value: Mapping[str, Any], field: str) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    copied.pop(field, None)
    copied[field] = payload_sha256(copied)
    return copied


def sealed(value: Mapping[str, Any], field: str) -> bool:
    copied = copy.deepcopy(dict(value))
    observed = copied.pop(field, None)
    return isinstance(observed, str) and observed == payload_sha256(copied)


def watcher_snapshot(proc_root: Path = Path("/proc")) -> list[dict[str, Any]]:
    return production.protected_watcher_snapshot(proc_root)


def task_vector() -> list[dict[str, str]]:
    if (
        len(TLD_COHORT) != IDENTITY_COUNT
        or len(set(TLD_COHORT)) != IDENTITY_COUNT
        or set(TLD_COHORT).intersection(HISTORICAL_TLD_COHORT)
        or len(identity_groups()) != TASK_COUNT
    ):
        raise RuntimeError("V2.50.18 fresh multi-identity population drifted")
    values: list[dict[str, str]] = []
    for group in identity_groups():
        rows = "\n".join(f"{index}. {tld}" for index, tld in enumerate(group, 1))
        opaque = "task_" + hashlib.sha256(
            f"v25018:{'|'.join(group)}".encode()
        ).hexdigest()[:24]
        question = (
            "Use web search and the official IANA Root Zone Database public page to "
            "return exactly one Markdown table and no prose for these visible domain identities:\n"
            f"<DOMAINS>\n{rows}\n</DOMAINS>\n"
            "Column names: Domain, Sponsoring Organisation, Registration date, "
            "Record last updated. Preserve the exact row order and domain spelling "
            "shown above. Each row's three target fields must come from that row's "
            "same official IANA detail record. Use Unknown only if the fetched "
            "official detail page does not establish the value."
        )
        values.append({"opaque_id": opaque, "question": question})
    return validate_task_vector(values)


def validate_task_vector(
    values: Sequence[Mapping[str, Any]],
) -> list[dict[str, str]]:
    if isinstance(values, (str, bytes)) or len(values) != TASK_COUNT:
        raise ValueError("V2.50.18 task denominator drifted")
    output: list[dict[str, str]] = []
    seen: set[str] = set()
    for value, group in zip(values, identity_groups(), strict=True):
        if not isinstance(value, Mapping) or set(value) != {"opaque_id", "question"}:
            raise ValueError("V2.50.18 runtime input must be opaque_id and question")
        opaque, question = value.get("opaque_id"), value.get("question")
        if (
            not isinstance(opaque, str)
            or len(opaque) != 29
            or not opaque.startswith("task_")
            or opaque in seen
            or not isinstance(question, str)
            or projector.visible_identities(question) != group
            or any(column not in question for column in COLUMNS)
            or IANA_DETAIL_PREFIX in question
            or any(detail_url(tld) in question for tld in group)
        ):
            raise ValueError("V2.50.18 visible task binding drifted")
        seen.add(opaque)
        output.append({"opaque_id": opaque, "question": question})
    return output


def arm_order_vector() -> list[list[str]]:
    tasks = task_vector()
    ranked = sorted(
        range(TASK_COUNT),
        key=lambda index: hashlib.sha256(
            f"v25018-arm-order:{tasks[index]['opaque_id']}".encode()
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
        "fresh_eighty_identity_population_disjoint_from_prior_180": True,
        "twenty_tasks_each_have_four_visible_rows": True,
        "final_population_url_or_page_probed_before_protocol_freeze": False,
        "population_selected_by_public_namespace_order_only": True,
        "one_visible_only_planning_call": True,
        "same_completed_legacy_query_vector_for_both_arms": True,
        "one_physical_first_wave_pages_and_link_vectors_reused_by_both_arms": True,
        "one_physical_second_wave_search_response_reused_by_both_arms": True,
        "completed_search_prefix_identical_and_non_displaceable": True,
        "candidate_optimizes_only_uncovered_distinct_visible_identity_count": True,
        "raw_link_count_does_not_define_credit": True,
        "detail_page_requires_unique_identity_path_surface_authority_and_all_fields": True,
        "two_arm_full_second_wave_url_union_fetched_once": True,
        "page_text_partitioned_by_selected_canonical_url": True,
        "per_arm_logical_query_fetch_caps": {"queries": 4, "fetches": 10},
        "paired_physical_query_fetch_caps": {"queries": 4, "fetches": 14},
        "same_evidence_renderer_columns_prompt_model_output_and_deadline": True,
        "executed_order_receipt_bound_per_terminal_task": True,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read_by_forward": False,
        "prediction_freeze_before_gold_fetch_or_quality_decision": True,
        "entropy_or_information_gain_assigns_credit_or_routes": False,
        "public_deepwidebench_exact220_launch_authorized": False,
    }


def mechanism_gate() -> dict[str, Any]:
    return {
        "terminal_tasks": TASK_COUNT,
        "minimum_distinct_identity_strategy_eligible_tasks": 8,
        "shared_first_wave_completed_tasks": TASK_COUNT,
        "shared_second_wave_completed_tasks": TASK_COUNT,
        "all_tasks_execute_exactly_four_physical_queries": True,
        "all_tasks_fetch_at_most_fourteen_physical_pages": True,
        "minimum_both_arms_model_success_tasks": 18,
        "all_task_evidence_character_counts_equal_between_arms": True,
        "completed_task_model_calls_at_most_three": True,
        "all_tasks_plan_exactly_four_queries_per_arm": True,
        "all_tasks_execute_exactly_four_queries_per_arm": True,
        "executed_arm_order_complete_and_matches_frozen_vector": True,
        "minimum_selection_changed_tasks": 8,
        "minimum_total_new_distinct_identity_gain": 16,
        "minimum_tasks_with_positive_distinct_identity_gain": 8,
        "candidate_total_new_distinct_identity_count_strict_gain": True,
        "candidate_total_target_bound_projected_pages_strict_gain": True,
        "minimum_tasks_with_positive_target_bound_projected_page_gain": 6,
        "candidate_total_target_bound_records_strict_gain": True,
        "minimum_tasks_with_positive_target_bound_record_gain": 6,
        "minimum_target_bound_record_mechanism_engaged_tasks": 6,
        "minimum_prediction_changed_tasks": 6,
        "query_cap_per_arm_per_task": 4,
        "fetch_cap_per_arm_per_task": 10,
        "physical_query_cap_per_task": 4,
        "physical_fetch_cap_per_task": 14,
    }


def quality_gate() -> dict[str, Any]:
    return {
        "fixed_task_denominator": TASK_COUNT,
        "fixed_row_denominator": IDENTITY_COUNT,
        "candidate_exact_strictly_greater": True,
        "entity_row_item_column_composite_nonregression": True,
        "invalid_or_fallback_nonincrease": True,
    }


def _execution_receipt(
    *, task_ordinal: int, requested_order: Sequence[str], result: Mapping[str, Any]
) -> dict[str, Any]:
    checked = runtime.validate_result(result)
    main = checked["parent_result"]["content_free_receipt"]
    metrics = main["arm_metrics"]
    first = main["first_synthesis_arm"]
    attempted = {arm for arm in ARMS if metrics[arm]["synthesis_attempted"]}
    actual: list[str] = []
    if first in attempted:
        actual.append(first)
        actual.extend(arm for arm in ARMS if arm != first and arm in attempted)
    value = {
        "artifact_version": 1,
        "role": "v25018_content_free_executed_arm_order_receipt",
        "task_ordinal": int(task_ordinal),
        "requested_arm_order": list(requested_order),
        "executed_synthesis_order": actual,
        "both_arms_synthesis_attempted": len(attempted) == 2,
        "executed_order_complete": len(actual) == 2,
        "executed_order_matches_frozen": actual == list(requested_order),
        "contains_question_prediction_page_gold_score_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
    }
    value["receipt_payload_sha256"] = payload_sha256(value)
    return value


def wrap_task_result(
    task_ordinal: int,
    requested_order: Sequence[str],
    result: Mapping[str, Any],
) -> dict[str, Any]:
    if (
        isinstance(task_ordinal, bool)
        or not isinstance(task_ordinal, int)
        or not 1 <= task_ordinal <= TASK_COUNT
        or list(requested_order) != arm_order_vector()[task_ordinal - 1]
    ):
        raise ValueError("V2.50.18 frozen task/order binding drifted")
    checked = runtime.validate_result(result)
    if checked["parent_result"]["opaque_id"] != task_vector()[task_ordinal - 1]["opaque_id"]:
        raise ValueError("V2.50.18 runtime task identity drifted")
    receipt = _execution_receipt(
        task_ordinal=task_ordinal,
        requested_order=requested_order,
        result=checked,
    )
    value = {
        "artifact_version": 1,
        "role": "v25018_multi_identity_external_task_result",
        "runtime_result": copy.deepcopy(checked),
        "executed_order_receipt": receipt,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
    }
    value["task_result_payload_sha256"] = payload_sha256(value)
    return validate_task_result(value)


def validate_task_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "runtime_result",
            "executed_order_receipt",
            "mapping_gold_category_question_type_split_evaluator_score_reward_read",
            "task_result_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != "v25018_multi_identity_external_task_result"
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_read"
        )
        is not False
        or not sealed(copied, "task_result_payload_sha256")
    ):
        raise ValueError("V2.50.18 task-result envelope drifted")
    runtime_result = runtime.validate_result(copied.get("runtime_result"))
    receipt = copied.get("executed_order_receipt")
    if not isinstance(receipt, Mapping):
        raise ValueError("V2.50.18 execution receipt absent")
    ordinal = receipt.get("task_ordinal")
    if (
        isinstance(ordinal, bool)
        or not isinstance(ordinal, int)
        or not 1 <= ordinal <= TASK_COUNT
        or set(receipt)
        != {
            "artifact_version",
            "role",
            "task_ordinal",
            "requested_arm_order",
            "executed_synthesis_order",
            "both_arms_synthesis_attempted",
            "executed_order_complete",
            "executed_order_matches_frozen",
            "contains_question_prediction_page_gold_score_or_credential",
            "mapping_gold_category_question_type_split_evaluator_score_reward_read",
            "receipt_payload_sha256",
        }
        or receipt.get("artifact_version") != 1
        or receipt.get("role") != "v25018_content_free_executed_arm_order_receipt"
        or not sealed(receipt, "receipt_payload_sha256")
        or receipt.get("requested_arm_order") != arm_order_vector()[ordinal - 1]
        or receipt
        != _execution_receipt(
            task_ordinal=ordinal,
            requested_order=receipt["requested_arm_order"],
            result=runtime_result,
        )
        or runtime_result["parent_result"]["opaque_id"]
        != task_vector()[ordinal - 1]["opaque_id"]
    ):
        raise ValueError("V2.50.18 executed-order receipt drifted")
    copied["runtime_result"] = runtime_result
    return copied


def dependency_manifest(root: Path, *, tracked: bool = True) -> dict[str, str]:
    output: dict[str, str] = {}
    for relative in LOCAL_SOURCES:
        path = root / relative
        if (
            relative.is_absolute()
            or ".." in relative.parts
            or path.is_symlink()
            or not path.is_file()
            or not path.resolve().is_relative_to(root.resolve())
        ):
            raise RuntimeError("V2.50.18 source manifest path drifted")
        if tracked and subprocess.run(
            ["git", "ls-files", "--error-unmatch", str(relative)],
            cwd=root,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=20,
            check=False,
        ).returncode != 0:
            raise RuntimeError("V2.50.18 source is not tracked")
        output[str(relative)] = sha256(path)
    return output


def _protocol(root: Path, *, now: int, tracked: bool) -> dict[str, Any]:
    tasks = task_vector()
    manifest = dependency_manifest(root, tracked=tracked)
    value = {
        "artifact_version": 1,
        "role": "v25018_multi_identity_external_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(now),
        "git_head": git(root, "rev-parse", "HEAD"),
        "population": {
            "selected_tasks": TASK_COUNT,
            "selected_visible_identities": IDENTITY_COUNT,
            "identities_per_task": GROUP_SIZE,
            "opaque_id_vector_sha256": payload_sha256([task["opaque_id"] for task in tasks]),
            "visible_question_vector_sha256": payload_sha256([task["question"] for task in tasks]),
            "task_vector_sha256": payload_sha256(tasks),
            "tld_vector_sha256": payload_sha256(TLD_COHORT),
            "identity_group_vector_sha256": payload_sha256(identity_groups()),
            "arm_order_vector_sha256": payload_sha256(arm_order_vector()),
            "disjoint_from_all_prior_tld_cohorts": not bool(
                set(TLD_COHORT) & HISTORICAL_TLD_COHORT
            ),
            "selection_basis": "first_eighty_alphabetic_unseen_iana_identities_after_v25012_public_namespace_only",
            "official_detail_endpoint_vector_sha256": payload_sha256(
                [detail_url(tld) for tld in TLD_COHORT]
            ),
            "final_population_url_or_page_probed_before_protocol_freeze": False,
        },
        "execution": {
            "output_root": str(OUTPUT_ROOT),
            "executor_concurrency": EXECUTOR_CONCURRENCY,
            "model_slot_cap": MODEL_SLOT_CAP,
            "model": copy.deepcopy(MODEL),
            "search": copy.deepcopy(SEARCH),
            "limits_per_arm": copy.deepcopy(LIMITS),
            "protected_watchers": watcher_snapshot(),
            "single_atomic_forward_no_retry_resume_or_selective_rerun": True,
        },
        "mechanism_gate_before_evaluator": mechanism_gate(),
        "quality_gate": quality_gate(),
        "source_policy": source_policy(),
        "dependency_manifest": manifest,
        "dependency_manifest_sha256": payload_sha256(manifest),
        "authorization": {
            "preactivation_audit_generation": True,
            "one_external_forward": False,
            "postfreeze_evaluator": False,
            "public_exact220_launch": False,
            "leaderboard_or_sota": False,
        },
    }
    value["protocol_payload_sha256"] = payload_sha256(value)
    return validate_protocol(root, value, tracked=tracked)


def build_protocol(root: Path, *, now: int) -> dict[str, Any]:
    return _protocol(root, now=now, tracked=True)


def validate_protocol(
    root: Path, value: Mapping[str, Any], *, tracked: bool = True
) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    population = copied.get("population")
    execution = copied.get("execution")
    authorization = copied.get("authorization")
    tasks = task_vector()
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "protocol_id",
            "created_at_unix",
            "git_head",
            "population",
            "execution",
            "mechanism_gate_before_evaluator",
            "quality_gate",
            "source_policy",
            "dependency_manifest",
            "dependency_manifest_sha256",
            "authorization",
            "protocol_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != "v25018_multi_identity_external_preregistration"
        or copied.get("protocol_id") != PROTOCOL_ID
        or not isinstance(copied.get("created_at_unix"), int)
        or not isinstance(copied.get("git_head"), str)
        or len(copied["git_head"]) != 40
        or not isinstance(population, Mapping)
        or set(population)
        != {
            "selected_tasks",
            "selected_visible_identities",
            "identities_per_task",
            "opaque_id_vector_sha256",
            "visible_question_vector_sha256",
            "task_vector_sha256",
            "tld_vector_sha256",
            "identity_group_vector_sha256",
            "arm_order_vector_sha256",
            "disjoint_from_all_prior_tld_cohorts",
            "selection_basis",
            "official_detail_endpoint_vector_sha256",
            "final_population_url_or_page_probed_before_protocol_freeze",
        }
        or population.get("selected_tasks") != TASK_COUNT
        or population.get("selected_visible_identities") != IDENTITY_COUNT
        or population.get("identities_per_task") != GROUP_SIZE
        or population.get("opaque_id_vector_sha256")
        != payload_sha256([task["opaque_id"] for task in tasks])
        or population.get("visible_question_vector_sha256")
        != payload_sha256([task["question"] for task in tasks])
        or population.get("task_vector_sha256") != payload_sha256(tasks)
        or population.get("tld_vector_sha256") != payload_sha256(TLD_COHORT)
        or population.get("identity_group_vector_sha256")
        != payload_sha256(identity_groups())
        or population.get("arm_order_vector_sha256")
        != payload_sha256(arm_order_vector())
        or population.get("disjoint_from_all_prior_tld_cohorts") is not True
        or population.get("selection_basis")
        != "first_eighty_alphabetic_unseen_iana_identities_after_v25012_public_namespace_only"
        or population.get("official_detail_endpoint_vector_sha256")
        != payload_sha256([detail_url(tld) for tld in TLD_COHORT])
        or population.get("final_population_url_or_page_probed_before_protocol_freeze")
        is not False
        or not isinstance(execution, Mapping)
        or set(execution)
        != {
            "output_root",
            "executor_concurrency",
            "model_slot_cap",
            "model",
            "search",
            "limits_per_arm",
            "protected_watchers",
            "single_atomic_forward_no_retry_resume_or_selective_rerun",
        }
        or execution.get("output_root") != str(OUTPUT_ROOT)
        or execution.get("executor_concurrency") != EXECUTOR_CONCURRENCY
        or execution.get("model_slot_cap") != MODEL_SLOT_CAP
        or execution.get("model") != MODEL
        or execution.get("search") != SEARCH
        or execution.get("limits_per_arm") != LIMITS
        or execution.get("protected_watchers") != watcher_snapshot()
        or execution.get("single_atomic_forward_no_retry_resume_or_selective_rerun")
        is not True
        or copied.get("mechanism_gate_before_evaluator") != mechanism_gate()
        or copied.get("quality_gate") != quality_gate()
        or copied.get("source_policy") != source_policy()
        or copied.get("dependency_manifest")
        != dependency_manifest(root, tracked=tracked)
        or copied.get("dependency_manifest_sha256")
        != payload_sha256(copied["dependency_manifest"])
        or authorization
        != {
            "preactivation_audit_generation": True,
            "one_external_forward": False,
            "postfreeze_evaluator": False,
            "public_exact220_launch": False,
            "leaderboard_or_sota": False,
        }
        or not sealed(copied, "protocol_payload_sha256")
    ):
        raise RuntimeError("V2.50.18 protocol drifted")
    return copied


__all__ = [name for name in tuple(globals()) if name.isupper()] + [
    "arm_order_vector",
    "build_protocol",
    "dependency_manifest",
    "detail_url",
    "git",
    "identity_groups",
    "mechanism_gate",
    "payload_sha256",
    "quality_gate",
    "seal",
    "sealed",
    "sha256",
    "source_policy",
    "task_vector",
    "validate_protocol",
    "validate_task_result",
    "validate_task_vector",
    "watcher_snapshot",
    "wrap_task_result",
]
