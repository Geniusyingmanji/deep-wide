"""Pure label-blind fixed evidence-sufficiency termination baseline.

The criterion catalog is declared against a SHA-256 projection of visible
input, and its builder accepts only an empty supplied pre-search action trace.
Runtime decisions consume only that sealed catalog, a content-free action
trace, and a sealed snapshot declared to contain active
criterion/evidence/source-class projections from the same forward pass.  A
hash cannot by itself prove semantic derivation, chronology outside this call,
or completeness of the active-evidence snapshot; those remain integration
obligations.

The baseline has three decisions:

* ``answer_ready`` when every frozen criterion has enough clean, page-backed
  evidence and source classes and no active contradiction;
* ``continue`` while at least one criterion is pending and action budget
  remains; and
* ``abstain_budget_exhausted`` when criteria remain pending at the hard cap.

Neither criterion satisfaction nor budget exhaustion claims task success,
open-set completeness, source independence, or benchmark quality.  The module
is pure and grants no forward, evaluator, credit, training, or launch authority.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from typing import Any


POLICY_ID = "v24222_label_blind_fixed_evidence_sufficiency_v1"
CATALOG_ROLE = "v24222_fixed_sufficiency_criterion_catalog"
ACTION_STEP_ROLE = "v24222_fixed_sufficiency_action_step"
SNAPSHOT_ROLE = "v24222_fixed_sufficiency_evidence_snapshot"
RECEIPT_ROLE = "v24222_fixed_sufficiency_decision_receipt"
CONSTRUCTION_POLICY = "declared_visible_input_projection_only_before_first_action"

CRITERION_KINDS = ("coverage", "source", "time", "exclusion")
CRITERION_STATUSES = ("contradicted", "unresolved", "satisfied")
ASSERTION_KINDS = ("contradiction", "support")
MAX_CRITERIA = 512
MAX_ACTION_STEPS = 512
MAX_ASSERTIONS = 4096
MAX_PRIORITY = 1_000_000
MAX_THRESHOLD = 512
PRODUCTION_PACKAGE_AUTHORIZED = False

FORBIDDEN_METADATA_KEYS = frozenset(
    {
        "answer",
        "answerkey",
        "benchmark",
        "benchmarkcategory",
        "benchmarklabel",
        "benchmarkname",
        "benchmarkquestiontype",
        "benchmarkversion",
        "category",
        "content",
        "dataset",
        "datasetname",
        "evaluation",
        "evaluator",
        "evaluatorscore",
        "expectedanswer",
        "gold",
        "goldanswer",
        "groundtruth",
        "instanceid",
        "label",
        "labels",
        "mapping",
        "officialanswer",
        "prediction",
        "predictions",
        "query",
        "question",
        "questiontext",
        "questiontype",
        "rawcontent",
        "rawerror",
        "rawevidence",
        "referenceanswer",
        "resultscsv",
        "reward",
        "score",
        "scores",
        "split",
        "subset",
        "taskcategory",
        "taskid",
        "text",
        "url",
    }
)

CRITERION_KEYS = frozenset(
    {
        "criterion_ref_sha256",
        "criterion_kind",
        "priority",
        "action_class_sha256",
        "minimum_clean_evidence_classes",
        "minimum_clean_source_classes",
    }
)
CATALOG_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "visible_input_projection_sha256",
        "root_scope_sha256",
        "construction_policy",
        "construction_action_trace_sha256",
        "catalog_frozen_before_first_action",
        "max_action_steps",
        "criteria",
        "question_text_or_raw_evidence_embedded",
        "benchmark_metadata_or_outcome_embedded",
        "catalog_sha256",
    }
)
ACTION_STEP_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "step_index",
        "action_class_sha256",
        "step_sha256",
    }
)
ASSERTION_KEYS = frozenset(
    {
        "criterion_ref_sha256",
        "evidence_class_sha256",
        "source_class_sha256",
        "page_backed",
        "assertion_kind",
    }
)
SNAPSHOT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "root_scope_sha256",
        "after_action_count",
        "active_evidence_only",
        "assertions",
        "question_text_or_raw_evidence_embedded",
        "benchmark_metadata_or_outcome_embedded",
        "snapshot_sha256",
    }
)
DIAGNOSTIC_KEYS = frozenset(
    {
        "criterion_ref_sha256",
        "criterion_kind",
        "priority",
        "action_class_sha256",
        "status",
        "clean_page_evidence_class_count",
        "clean_source_class_count",
        "contradiction_page_evidence_class_count",
        "minimum_clean_evidence_classes",
        "minimum_clean_source_classes",
    }
)
RECEIPT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "label_blind",
        "baseline_only",
        "opaque_task_ref_sha256",
        "root_scope_sha256",
        "decision_index",
        "criterion_catalog_sha256",
        "action_trace_sha256",
        "evidence_snapshot_sha256",
        "max_action_steps",
        "consumed_action_steps",
        "remaining_action_steps",
        "criterion_count",
        "satisfied_criterion_count",
        "unresolved_criterion_count",
        "contradicted_criterion_count",
        "nonpage_assertion_count",
        "criterion_diagnostics",
        "decision_kind",
        "selected_criterion_ref_sha256",
        "selected_action_class_sha256",
        "decision_reason",
        "criteria_frozen_before_first_action",
        "answer_ready_is_not_task_success",
        "budget_exhaustion_is_not_task_success",
        "open_set_completeness_claimed",
        "source_independence_claimed",
        "four_layer_risk_entropy_or_voc_used",
        "question_text_or_raw_evidence_read",
        "mapping_gold_category_question_type_evaluator_score_or_reward_read",
        "file_environment_network_model_search_fetch_or_process_accessed",
        "benchmark_forward_evaluator_credit_or_training_authorized",
        "receipt_sha256",
    }
)


def object_sha256(value: object) -> str:
    """Hash a JSON-compatible object with the frozen canonical encoding."""

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
        and set(value).issubset(set("0123456789abcdef"))
    )


def _sha256(value: object, *, label: str) -> str:
    if not _is_sha256(value):
        raise ValueError(f"V2.42.22 {label} is not a SHA-256")
    return str(value)


def _integer(
    value: object, *, label: str, minimum: int = 0, maximum: int
) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not minimum <= value <= maximum
    ):
        raise ValueError(f"V2.42.22 {label} is outside its integer bounds")
    return value


def _canonical_key(value: object) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value).casefold())


def reject_privileged_metadata(value: object, *, path: str = "payload") -> None:
    """Reject raw content and evaluator-only keys anywhere in input objects."""

    if isinstance(value, Mapping):
        for raw_key, child in value.items():
            if _canonical_key(raw_key) in FORBIDDEN_METADATA_KEYS:
                raise ValueError(
                    f"V2.42.22 privileged metadata rejected at {path}.{raw_key}"
                )
            reject_privileged_metadata(child, path=f"{path}.{raw_key}")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            reject_privileged_metadata(child, path=f"{path}[{index}]")


def _exact_mapping(
    value: object, *, keys: frozenset[str], label: str
) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != keys:
        raise ValueError(f"V2.42.22 {label} schema is not exact")
    return value


def _normalize_criterion(value: object) -> dict[str, Any]:
    reject_privileged_metadata(value, path="criterion")
    row = _exact_mapping(value, keys=CRITERION_KEYS, label="criterion")
    kind = str(row.get("criterion_kind", ""))
    if kind not in CRITERION_KINDS:
        raise ValueError("V2.42.22 criterion kind is invalid")
    return {
        "criterion_ref_sha256": _sha256(
            row.get("criterion_ref_sha256"), label="criterion reference"
        ),
        "criterion_kind": kind,
        "priority": _integer(
            row.get("priority"),
            label="criterion priority",
            maximum=MAX_PRIORITY,
        ),
        "action_class_sha256": _sha256(
            row.get("action_class_sha256"), label="action class"
        ),
        "minimum_clean_evidence_classes": _integer(
            row.get("minimum_clean_evidence_classes"),
            label="minimum clean evidence classes",
            minimum=1,
            maximum=MAX_THRESHOLD,
        ),
        "minimum_clean_source_classes": _integer(
            row.get("minimum_clean_source_classes"),
            label="minimum clean source classes",
            minimum=1,
            maximum=MAX_THRESHOLD,
        ),
    }


def build_criterion_catalog(
    *,
    visible_input_projection_sha256: str,
    root_scope_sha256: str,
    max_action_steps: int,
    criteria: Sequence[Mapping[str, Any]],
    presearch_action_trace: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Build a sealed catalog only when the supplied action trace is empty."""

    reject_privileged_metadata(presearch_action_trace, path="presearch_trace")
    if (
        isinstance(presearch_action_trace, (str, bytes))
        or not isinstance(presearch_action_trace, Sequence)
        or len(presearch_action_trace) != 0
    ):
        raise ValueError(
            "V2.42.22 criterion catalog must be frozen before the first action"
        )
    if isinstance(criteria, (str, bytes)) or not isinstance(criteria, Sequence):
        raise ValueError("V2.42.22 criteria are not a sequence")
    if not 1 <= len(criteria) <= MAX_CRITERIA:
        raise ValueError("V2.42.22 criterion count is outside its bound")
    rows = [_normalize_criterion(item) for item in criteria]
    rows.sort(key=lambda item: (item["priority"], item["criterion_ref_sha256"]))
    references = [item["criterion_ref_sha256"] for item in rows]
    if len(set(references)) != len(references):
        raise ValueError("V2.42.22 criterion references are not unique")
    if not any(item["criterion_kind"] == "coverage" for item in rows):
        raise ValueError("V2.42.22 catalog has no coverage criterion")
    catalog: dict[str, Any] = {
        "artifact_version": 1,
        "role": CATALOG_ROLE,
        "policy_id": POLICY_ID,
        "visible_input_projection_sha256": _sha256(
            visible_input_projection_sha256,
            label="visible input projection",
        ),
        "root_scope_sha256": _sha256(root_scope_sha256, label="root scope"),
        "construction_policy": CONSTRUCTION_POLICY,
        "construction_action_trace_sha256": object_sha256([]),
        "catalog_frozen_before_first_action": True,
        "max_action_steps": _integer(
            max_action_steps,
            label="maximum action steps",
            minimum=1,
            maximum=MAX_ACTION_STEPS,
        ),
        "criteria": rows,
        "question_text_or_raw_evidence_embedded": False,
        "benchmark_metadata_or_outcome_embedded": False,
    }
    catalog["catalog_sha256"] = object_sha256(catalog)
    return catalog


def validate_criterion_catalog(value: object) -> dict[str, Any]:
    """Validate the exact catalog schema, chronology attestation, and seal."""

    reject_privileged_metadata(value, path="catalog")
    catalog = _exact_mapping(value, keys=CATALOG_KEYS, label="criterion catalog")
    criteria = catalog.get("criteria")
    if not isinstance(criteria, list):
        raise ValueError("V2.42.22 catalog criteria are not an array")
    rebuilt = build_criterion_catalog(
        visible_input_projection_sha256=str(
            catalog.get("visible_input_projection_sha256", "")
        ),
        root_scope_sha256=str(catalog.get("root_scope_sha256", "")),
        max_action_steps=catalog.get("max_action_steps"),
        criteria=criteria,
        presearch_action_trace=(),
    )
    if (
        catalog.get("artifact_version") != 1
        or catalog.get("role") != CATALOG_ROLE
        or catalog.get("policy_id") != POLICY_ID
        or catalog.get("construction_policy") != CONSTRUCTION_POLICY
        or catalog.get("construction_action_trace_sha256") != object_sha256([])
        or catalog.get("catalog_frozen_before_first_action") is not True
        or catalog.get("question_text_or_raw_evidence_embedded") is not False
        or catalog.get("benchmark_metadata_or_outcome_embedded") is not False
        or dict(catalog) != rebuilt
    ):
        raise ValueError("V2.42.22 criterion catalog contract drifted")
    return rebuilt


def build_action_step(*, step_index: int, action_class_sha256: str) -> dict[str, Any]:
    """Build one content-free action step."""

    step: dict[str, Any] = {
        "artifact_version": 1,
        "role": ACTION_STEP_ROLE,
        "step_index": _integer(
            step_index,
            label="action step index",
            maximum=MAX_ACTION_STEPS - 1,
        ),
        "action_class_sha256": _sha256(
            action_class_sha256, label="trace action class"
        ),
    }
    step["step_sha256"] = object_sha256(step)
    return step


def validate_action_trace(value: object) -> list[dict[str, Any]]:
    """Validate an ordered trace that contains no raw action or observation."""

    reject_privileged_metadata(value, path="action_trace")
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ValueError("V2.42.22 action trace is not a sequence")
    if len(value) > MAX_ACTION_STEPS:
        raise ValueError("V2.42.22 action trace exceeds its bound")
    output: list[dict[str, Any]] = []
    for index, raw in enumerate(value):
        step = _exact_mapping(raw, keys=ACTION_STEP_KEYS, label="action step")
        rebuilt = build_action_step(
            step_index=index,
            action_class_sha256=str(step.get("action_class_sha256", "")),
        )
        if (
            step.get("artifact_version") != 1
            or step.get("role") != ACTION_STEP_ROLE
            or step.get("step_index") != index
            or dict(step) != rebuilt
        ):
            raise ValueError("V2.42.22 action step contract drifted")
        output.append(rebuilt)
    return output


def _normalize_assertion(value: object) -> dict[str, Any]:
    reject_privileged_metadata(value, path="snapshot.assertion")
    row = _exact_mapping(value, keys=ASSERTION_KEYS, label="evidence assertion")
    page_backed = row.get("page_backed")
    if not isinstance(page_backed, bool):
        raise ValueError("V2.42.22 page-backed flag is not boolean")
    assertion_kind = str(row.get("assertion_kind", ""))
    if assertion_kind not in ASSERTION_KINDS:
        raise ValueError("V2.42.22 assertion kind is invalid")
    return {
        "criterion_ref_sha256": _sha256(
            row.get("criterion_ref_sha256"), label="assertion criterion reference"
        ),
        "evidence_class_sha256": _sha256(
            row.get("evidence_class_sha256"), label="evidence class"
        ),
        "source_class_sha256": _sha256(
            row.get("source_class_sha256"), label="source class"
        ),
        "page_backed": page_backed,
        "assertion_kind": assertion_kind,
    }


def build_evidence_snapshot(
    *,
    root_scope_sha256: str,
    after_action_count: int,
    assertions: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Build a current active-evidence snapshot from content-free projections."""

    if isinstance(assertions, (str, bytes)) or not isinstance(assertions, Sequence):
        raise ValueError("V2.42.22 assertions are not a sequence")
    if len(assertions) > MAX_ASSERTIONS:
        raise ValueError("V2.42.22 assertion count exceeds its bound")
    rows = [_normalize_assertion(item) for item in assertions]
    rows.sort(
        key=lambda item: (
            item["criterion_ref_sha256"],
            item["evidence_class_sha256"],
            item["source_class_sha256"],
            item["page_backed"],
            item["assertion_kind"],
        )
    )
    identities = [
        (
            item["criterion_ref_sha256"],
            item["evidence_class_sha256"],
            item["source_class_sha256"],
            item["page_backed"],
            item["assertion_kind"],
        )
        for item in rows
    ]
    if len(identities) != len(set(identities)):
        raise ValueError("V2.42.22 snapshot contains duplicate assertions")
    snapshot: dict[str, Any] = {
        "artifact_version": 1,
        "role": SNAPSHOT_ROLE,
        "policy_id": POLICY_ID,
        "root_scope_sha256": _sha256(root_scope_sha256, label="root scope"),
        "after_action_count": _integer(
            after_action_count,
            label="snapshot action count",
            maximum=MAX_ACTION_STEPS,
        ),
        "active_evidence_only": True,
        "assertions": rows,
        "question_text_or_raw_evidence_embedded": False,
        "benchmark_metadata_or_outcome_embedded": False,
    }
    snapshot["snapshot_sha256"] = object_sha256(snapshot)
    return snapshot


def validate_evidence_snapshot(value: object) -> dict[str, Any]:
    """Validate the current active-evidence snapshot and its seal."""

    reject_privileged_metadata(value, path="snapshot")
    snapshot = _exact_mapping(value, keys=SNAPSHOT_KEYS, label="evidence snapshot")
    assertions = snapshot.get("assertions")
    if not isinstance(assertions, list):
        raise ValueError("V2.42.22 snapshot assertions are not an array")
    rebuilt = build_evidence_snapshot(
        root_scope_sha256=str(snapshot.get("root_scope_sha256", "")),
        after_action_count=snapshot.get("after_action_count"),
        assertions=assertions,
    )
    if (
        snapshot.get("artifact_version") != 1
        or snapshot.get("role") != SNAPSHOT_ROLE
        or snapshot.get("policy_id") != POLICY_ID
        or snapshot.get("active_evidence_only") is not True
        or snapshot.get("question_text_or_raw_evidence_embedded") is not False
        or snapshot.get("benchmark_metadata_or_outcome_embedded") is not False
        or dict(snapshot) != rebuilt
    ):
        raise ValueError("V2.42.22 evidence snapshot contract drifted")
    return rebuilt


def _criterion_diagnostics(
    *, catalog: Mapping[str, Any], snapshot: Mapping[str, Any]
) -> tuple[list[dict[str, Any]], int]:
    criteria = {
        item["criterion_ref_sha256"]: item for item in catalog["criteria"]
    }
    unknown = sorted(
        {
            item["criterion_ref_sha256"]
            for item in snapshot["assertions"]
            if item["criterion_ref_sha256"] not in criteria
        }
    )
    if unknown:
        raise ValueError("V2.42.22 snapshot references an unknown criterion")

    page_assertions = [
        item for item in snapshot["assertions"] if item["page_backed"]
    ]
    polarities: dict[tuple[str, str], set[str]] = {}
    for item in page_assertions:
        key = (item["criterion_ref_sha256"], item["evidence_class_sha256"])
        polarities.setdefault(key, set()).add(item["assertion_kind"])
    if any(len(values) > 1 for values in polarities.values()):
        raise ValueError(
            "V2.42.22 criterion evidence class is both support and contradiction"
        )

    diagnostics: list[dict[str, Any]] = []
    for criterion in catalog["criteria"]:
        reference = criterion["criterion_ref_sha256"]
        contradiction_classes = {
            item["evidence_class_sha256"]
            for item in page_assertions
            if item["criterion_ref_sha256"] == reference
            and item["assertion_kind"] == "contradiction"
        }
        clean_support = [
            item
            for item in page_assertions
            if item["criterion_ref_sha256"] == reference
            and item["assertion_kind"] == "support"
            and item["evidence_class_sha256"] not in contradiction_classes
        ]
        evidence_classes = {
            item["evidence_class_sha256"] for item in clean_support
        }
        source_classes = {item["source_class_sha256"] for item in clean_support}
        if contradiction_classes:
            status = "contradicted"
        elif (
            len(evidence_classes) >= criterion["minimum_clean_evidence_classes"]
            and len(source_classes)
            >= criterion["minimum_clean_source_classes"]
        ):
            status = "satisfied"
        else:
            status = "unresolved"
        diagnostic = {
            "criterion_ref_sha256": reference,
            "criterion_kind": criterion["criterion_kind"],
            "priority": criterion["priority"],
            "action_class_sha256": criterion["action_class_sha256"],
            "status": status,
            "clean_page_evidence_class_count": len(evidence_classes),
            "clean_source_class_count": len(source_classes),
            "contradiction_page_evidence_class_count": len(
                contradiction_classes
            ),
            "minimum_clean_evidence_classes": criterion[
                "minimum_clean_evidence_classes"
            ],
            "minimum_clean_source_classes": criterion[
                "minimum_clean_source_classes"
            ],
        }
        if set(diagnostic) != DIAGNOSTIC_KEYS:
            raise RuntimeError("V2.42.22 internal diagnostic schema drifted")
        diagnostics.append(diagnostic)
    nonpage_count = sum(
        not item["page_backed"] for item in snapshot["assertions"]
    )
    return diagnostics, nonpage_count


def _build_decision(
    *,
    catalog: Mapping[str, Any],
    action_trace: Sequence[Mapping[str, Any]],
    snapshot: Mapping[str, Any],
    opaque_task_ref_sha256: str,
) -> dict[str, Any]:
    if catalog["root_scope_sha256"] != snapshot["root_scope_sha256"]:
        raise ValueError("V2.42.22 catalog and snapshot root scopes differ")
    if snapshot["after_action_count"] != len(action_trace):
        raise ValueError("V2.42.22 snapshot is not bound to the action trace")
    if len(action_trace) > catalog["max_action_steps"]:
        raise ValueError("V2.42.22 action trace exceeds the frozen budget")
    allowed_actions = {
        item["action_class_sha256"] for item in catalog["criteria"]
    }
    if any(
        step["action_class_sha256"] not in allowed_actions
        for step in action_trace
    ):
        raise ValueError("V2.42.22 trace uses an action outside the frozen menu")

    diagnostics, nonpage_count = _criterion_diagnostics(
        catalog=catalog,
        snapshot=snapshot,
    )
    counts = {
        status: sum(item["status"] == status for item in diagnostics)
        for status in CRITERION_STATUSES
    }
    pending = [item for item in diagnostics if item["status"] != "satisfied"]
    pending.sort(
        key=lambda item: (
            0 if item["status"] == "contradicted" else 1,
            item["priority"],
            item["criterion_ref_sha256"],
        )
    )
    consumed = len(action_trace)
    remaining = catalog["max_action_steps"] - consumed
    selected_criterion: str | None = None
    selected_action: str | None = None
    if not pending:
        decision_kind = "answer_ready"
        reason = "all_frozen_criteria_have_clean_page_backed_sufficiency"
    elif remaining == 0:
        decision_kind = "abstain_budget_exhausted"
        reason = "hard_action_budget_exhausted_with_pending_criteria"
    else:
        decision_kind = "continue"
        selected_criterion = pending[0]["criterion_ref_sha256"]
        selected_action = pending[0]["action_class_sha256"]
        reason = (
            "highest_priority_contradicted_criterion_with_budget"
            if pending[0]["status"] == "contradicted"
            else "highest_priority_unresolved_criterion_with_budget"
        )

    return {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "label_blind": True,
        "baseline_only": True,
        "opaque_task_ref_sha256": _sha256(
            opaque_task_ref_sha256, label="opaque task reference"
        ),
        "root_scope_sha256": catalog["root_scope_sha256"],
        "decision_index": consumed,
        "criterion_catalog_sha256": catalog["catalog_sha256"],
        "action_trace_sha256": object_sha256(action_trace),
        "evidence_snapshot_sha256": snapshot["snapshot_sha256"],
        "max_action_steps": catalog["max_action_steps"],
        "consumed_action_steps": consumed,
        "remaining_action_steps": remaining,
        "criterion_count": len(diagnostics),
        "satisfied_criterion_count": counts["satisfied"],
        "unresolved_criterion_count": counts["unresolved"],
        "contradicted_criterion_count": counts["contradicted"],
        "nonpage_assertion_count": nonpage_count,
        "criterion_diagnostics": diagnostics,
        "decision_kind": decision_kind,
        "selected_criterion_ref_sha256": selected_criterion,
        "selected_action_class_sha256": selected_action,
        "decision_reason": reason,
        "criteria_frozen_before_first_action": True,
        "answer_ready_is_not_task_success": True,
        "budget_exhaustion_is_not_task_success": True,
        "open_set_completeness_claimed": False,
        "source_independence_claimed": False,
        "four_layer_risk_entropy_or_voc_used": False,
        "question_text_or_raw_evidence_read": False,
        "mapping_gold_category_question_type_evaluator_score_or_reward_read": False,
        "file_environment_network_model_search_fetch_or_process_accessed": False,
        "benchmark_forward_evaluator_credit_or_training_authorized": False,
    }


def decide_fixed_sufficiency_baseline(
    *,
    criterion_catalog: object,
    action_trace: object,
    evidence_snapshot: object,
    opaque_task_ref_sha256: str,
) -> dict[str, Any]:
    """Return one sealed decision without performing an action."""

    catalog = validate_criterion_catalog(criterion_catalog)
    trace = validate_action_trace(action_trace)
    snapshot = validate_evidence_snapshot(evidence_snapshot)
    receipt = _build_decision(
        catalog=catalog,
        action_trace=trace,
        snapshot=snapshot,
        opaque_task_ref_sha256=opaque_task_ref_sha256,
    )
    receipt["receipt_sha256"] = object_sha256(receipt)
    return receipt


def validate_decision_receipt(
    value: object,
    *,
    criterion_catalog: object,
    action_trace: object,
    evidence_snapshot: object,
    opaque_task_ref_sha256: str,
) -> dict[str, Any]:
    """Recompute a decision so resealed semantic mutations still fail."""

    reject_privileged_metadata(value, path="receipt")
    receipt = _exact_mapping(value, keys=RECEIPT_KEYS, label="decision receipt")
    expected = decide_fixed_sufficiency_baseline(
        criterion_catalog=criterion_catalog,
        action_trace=action_trace,
        evidence_snapshot=evidence_snapshot,
        opaque_task_ref_sha256=opaque_task_ref_sha256,
    )
    if dict(receipt) != expected:
        raise ValueError("V2.42.22 decision receipt contract drifted")
    return expected
