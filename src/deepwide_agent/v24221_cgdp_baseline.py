"""Pure label-blind predicate-belief and exhaustion baseline.

This module implements a controlled CGDP-style baseline for later comparison
with the four-layer V2.42.11 controller.  It consumes only sealed predicate,
action-class, evidence-equivalence, and source-class hashes produced by
the current forward pass.  It never receives question text, raw evidence,
benchmark metadata, predictions, answers, evaluator output, or rewards.

The baseline separates three terminal decisions:

* ``answer_ready`` when every required predicate has non-contradicted support;
* ``continue`` while an unresolved predicate has a non-exhausted action; and
* ``abstain_exhausted`` when every pending action has repeatedly produced no
  new usable evidence, source class, or contradiction signal.

Exhaustion therefore never authorizes an incomplete answer or a success claim.
The module is pure and grants no benchmark-launch, evaluation, credit, or
training authority.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from typing import Any


POLICY_ID = "v24221_label_blind_cgdp_predicate_baseline_v1"
LEDGER_ROLE = "v24221_cgdp_predicate_ledger"
TRACE_STEP_ROLE = "v24221_cgdp_trace_step"
RECEIPT_ROLE = "v24221_cgdp_decision_receipt"
CONSTRUCTION_POLICY = "visible_input_and_same_pass_evidence_only"

PREDICATE_STATUSES = ("contradicted", "unresolved", "supported")
MAX_PREDICATES = 512
MAX_TRACE_STEPS = 512
MAX_EVIDENCE_RECORDS_PER_STEP = 512
MAX_PRIORITY = 1_000_000
MINIMUM_STAGNANT_REPEATS = 2
PRODUCTION_PACKAGE_AUTHORIZED = False

FORBIDDEN_METADATA_KEYS = frozenset(
    {
        "answerkey",
        "benchmark",
        "benchmarkcategory",
        "benchmarklabel",
        "benchmarkname",
        "benchmarkquestiontype",
        "benchmarkversion",
        "category",
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
        "question",
        "questiontext",
        "questiontype",
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
    }
)

PREDICATE_KEYS = frozenset(
    {
        "predicate_ref_sha256",
        "required",
        "priority",
        "status",
        "action_class_sha256",
        "support_evidence_class_sha256s",
        "contradiction_evidence_class_sha256s",
    }
)
LEDGER_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "root_scope_sha256",
        "construction_policy",
        "predicates",
        "question_text_or_raw_evidence_embedded",
        "benchmark_metadata_or_outcome_embedded",
        "ledger_sha256",
    }
)
EVIDENCE_KEYS = frozenset(
    {
        "evidence_class_sha256",
        "source_class_sha256",
        "page_backed",
        "contradicted",
    }
)
TRACE_STEP_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "step_index",
        "action_class_sha256",
        "evidence",
        "step_sha256",
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
        "predicate_ledger_sha256",
        "trace_sha256",
        "required_predicate_count",
        "required_supported_count",
        "required_unresolved_count",
        "required_contradicted_count",
        "pending_action_count",
        "pending_action_stagnant_repeats",
        "minimum_stagnant_repeats",
        "usable_page_evidence_class_count",
        "source_class_count",
        "contradiction_page_evidence_class_count",
        "nonpage_observation_count",
        "decision_kind",
        "selected_predicate_ref_sha256",
        "selected_action_class_sha256",
        "decision_reason",
        "answer_ready_is_not_task_success",
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
        raise ValueError(f"V2.42.21 {label} is not a SHA-256")
    return str(value)


def _integer(
    value: object, *, label: str, minimum: int = 0, maximum: int
) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not minimum <= value <= maximum
    ):
        raise ValueError(f"V2.42.21 {label} is outside its integer bounds")
    return value


def _canonical_key(value: object) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value).casefold())


def reject_privileged_metadata(value: object, *, path: str = "payload") -> None:
    """Reject evaluator-only or raw-content keys anywhere in input objects."""

    if isinstance(value, Mapping):
        for raw_key, child in value.items():
            if _canonical_key(raw_key) in FORBIDDEN_METADATA_KEYS:
                raise ValueError(
                    f"V2.42.21 privileged metadata rejected at {path}.{raw_key}"
                )
            reject_privileged_metadata(child, path=f"{path}.{raw_key}")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            reject_privileged_metadata(child, path=f"{path}[{index}]")


def _exact_mapping(
    value: object, *, keys: frozenset[str], label: str
) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != keys:
        raise ValueError(f"V2.42.21 {label} schema is not exact")
    return value


def _hash_list(value: object, *, label: str) -> list[str]:
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"V2.42.21 {label} is not an array")
    output = [_sha256(item, label=label) for item in value]
    if output != sorted(set(output)):
        raise ValueError(f"V2.42.21 {label} is not sorted and unique")
    return output


def _normalize_predicate(value: object) -> dict[str, Any]:
    reject_privileged_metadata(value, path="predicate")
    row = _exact_mapping(value, keys=PREDICATE_KEYS, label="predicate")
    required = row.get("required")
    if not isinstance(required, bool):
        raise ValueError("V2.42.21 predicate required flag is not boolean")
    status = str(row.get("status", ""))
    if status not in PREDICATE_STATUSES:
        raise ValueError("V2.42.21 predicate status is invalid")
    support = _hash_list(
        row.get("support_evidence_class_sha256s"), label="support evidence"
    )
    contradiction = _hash_list(
        row.get("contradiction_evidence_class_sha256s"),
        label="contradiction evidence",
    )
    if set(support).intersection(contradiction):
        raise ValueError(
            "V2.42.21 support and contradiction evidence overlap"
        )
    if status == "supported" and (not support or contradiction):
        raise ValueError(
            "V2.42.21 supported predicate lacks clean supporting evidence"
        )
    if status == "contradicted" and not contradiction:
        raise ValueError(
            "V2.42.21 contradicted predicate lacks contradiction evidence"
        )
    return {
        "predicate_ref_sha256": _sha256(
            row.get("predicate_ref_sha256"), label="predicate reference"
        ),
        "required": required,
        "priority": _integer(
            row.get("priority"),
            label="predicate priority",
            maximum=MAX_PRIORITY,
        ),
        "status": status,
        "action_class_sha256": _sha256(
            row.get("action_class_sha256"), label="action class"
        ),
        "support_evidence_class_sha256s": support,
        "contradiction_evidence_class_sha256s": contradiction,
    }


def build_predicate_ledger(
    *, root_scope_sha256: str, predicates: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    """Build a content-free predicate ledger from same-pass projections."""

    if isinstance(predicates, (str, bytes)) or not isinstance(predicates, Sequence):
        raise ValueError("V2.42.21 predicates are not a sequence")
    if not 1 <= len(predicates) <= MAX_PREDICATES:
        raise ValueError("V2.42.21 predicate count is outside its bound")
    rows = [_normalize_predicate(item) for item in predicates]
    rows.sort(key=lambda item: (item["priority"], item["predicate_ref_sha256"]))
    references = [item["predicate_ref_sha256"] for item in rows]
    if len(set(references)) != len(references):
        raise ValueError("V2.42.21 predicate references are not unique")
    if not any(item["required"] for item in rows):
        raise ValueError("V2.42.21 ledger has no required predicate")
    ledger: dict[str, Any] = {
        "artifact_version": 1,
        "role": LEDGER_ROLE,
        "policy_id": POLICY_ID,
        "root_scope_sha256": _sha256(
            root_scope_sha256, label="root scope"
        ),
        "construction_policy": CONSTRUCTION_POLICY,
        "predicates": rows,
        "question_text_or_raw_evidence_embedded": False,
        "benchmark_metadata_or_outcome_embedded": False,
    }
    ledger["ledger_sha256"] = object_sha256(ledger)
    return ledger


def validate_predicate_ledger(value: object) -> dict[str, Any]:
    """Validate a canonical predicate ledger and its content-free seal."""

    reject_privileged_metadata(value, path="ledger")
    ledger = _exact_mapping(value, keys=LEDGER_KEYS, label="ledger")
    predicates = ledger.get("predicates")
    if not isinstance(predicates, list):
        raise ValueError("V2.42.21 ledger predicates are not an array")
    rebuilt = build_predicate_ledger(
        root_scope_sha256=str(ledger.get("root_scope_sha256", "")),
        predicates=predicates,
    )
    if (
        ledger.get("artifact_version") != 1
        or ledger.get("role") != LEDGER_ROLE
        or ledger.get("policy_id") != POLICY_ID
        or ledger.get("construction_policy") != CONSTRUCTION_POLICY
        or ledger.get("question_text_or_raw_evidence_embedded") is not False
        or ledger.get("benchmark_metadata_or_outcome_embedded") is not False
        or dict(ledger) != rebuilt
    ):
        raise ValueError("V2.42.21 predicate ledger contract drifted")
    return rebuilt


def _normalize_evidence(value: object) -> dict[str, Any]:
    reject_privileged_metadata(value, path="trace.evidence")
    row = _exact_mapping(value, keys=EVIDENCE_KEYS, label="evidence record")
    page_backed = row.get("page_backed")
    contradicted = row.get("contradicted")
    if not isinstance(page_backed, bool) or not isinstance(contradicted, bool):
        raise ValueError("V2.42.21 evidence flags are not boolean")
    return {
        "evidence_class_sha256": _sha256(
            row.get("evidence_class_sha256"), label="evidence class"
        ),
        "source_class_sha256": _sha256(
            row.get("source_class_sha256"),
            label="source class",
        ),
        "page_backed": page_backed,
        "contradicted": contradicted,
    }


def build_trace_step(
    *,
    step_index: int,
    action_class_sha256: str,
    evidence: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Build one sealed, content-free action/observation trace step."""

    if isinstance(evidence, (str, bytes)) or not isinstance(evidence, Sequence):
        raise ValueError("V2.42.21 trace evidence is not a sequence")
    if len(evidence) > MAX_EVIDENCE_RECORDS_PER_STEP:
        raise ValueError("V2.42.21 trace evidence exceeds its bound")
    rows = [_normalize_evidence(item) for item in evidence]
    rows.sort(
        key=lambda item: (
            item["evidence_class_sha256"],
            item["source_class_sha256"],
            item["page_backed"],
            item["contradicted"],
        )
    )
    identities = [
        (
            item["evidence_class_sha256"],
            item["source_class_sha256"],
            item["page_backed"],
            item["contradicted"],
        )
        for item in rows
    ]
    if len(set(identities)) != len(identities):
        raise ValueError("V2.42.21 trace evidence contains duplicates")
    step: dict[str, Any] = {
        "artifact_version": 1,
        "role": TRACE_STEP_ROLE,
        "step_index": _integer(
            step_index,
            label="trace step index",
            maximum=MAX_TRACE_STEPS - 1,
        ),
        "action_class_sha256": _sha256(
            action_class_sha256, label="trace action class"
        ),
        "evidence": rows,
    }
    step["step_sha256"] = object_sha256(step)
    return step


def validate_trace(value: object) -> list[dict[str, Any]]:
    """Validate an ordered trace without accepting raw actions or observations."""

    reject_privileged_metadata(value, path="trace")
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ValueError("V2.42.21 trace is not a sequence")
    if len(value) > MAX_TRACE_STEPS:
        raise ValueError("V2.42.21 trace exceeds its bound")
    output: list[dict[str, Any]] = []
    for index, raw in enumerate(value):
        step = _exact_mapping(raw, keys=TRACE_STEP_KEYS, label="trace step")
        evidence = step.get("evidence")
        if not isinstance(evidence, list):
            raise ValueError("V2.42.21 trace-step evidence is not an array")
        rebuilt = build_trace_step(
            step_index=index,
            action_class_sha256=str(step.get("action_class_sha256", "")),
            evidence=evidence,
        )
        if (
            step.get("artifact_version") != 1
            or step.get("role") != TRACE_STEP_ROLE
            or step.get("step_index") != index
            or dict(step) != rebuilt
        ):
            raise ValueError("V2.42.21 trace step contract drifted")
        output.append(rebuilt)
    return output


def _trace_features(trace: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    seen_usable: set[str] = set()
    seen_sources: set[str] = set()
    seen_contradictions: set[str] = set()
    seen_actions: set[str] = set()
    clean_observation_classes: set[str] = set()
    contradicted_observation_classes: set[str] = set()
    nonpage_count = 0
    steps: list[dict[str, Any]] = []
    for step in trace:
        clean_observation_classes.update(
            item["evidence_class_sha256"]
            for item in step["evidence"]
            if not item["contradicted"]
        )
        contradicted_observation_classes.update(
            item["evidence_class_sha256"]
            for item in step["evidence"]
            if item["contradicted"]
        )
        if clean_observation_classes.intersection(
            contradicted_observation_classes
        ):
            raise ValueError(
                "V2.42.21 evidence class is both clean and contradicted"
            )
        usable = {
            item["evidence_class_sha256"]
            for item in step["evidence"]
            if item["page_backed"] and not item["contradicted"]
        }
        sources = {
            item["source_class_sha256"]
            for item in step["evidence"]
            if item["page_backed"] and not item["contradicted"]
        }
        contradictions = {
            item["evidence_class_sha256"]
            for item in step["evidence"]
            if item["page_backed"] and item["contradicted"]
        }
        nonpage_count += sum(not item["page_backed"] for item in step["evidence"])
        new_usable = usable - seen_usable
        new_sources = sources - seen_sources
        new_contradictions = contradictions - seen_contradictions
        action = str(step["action_class_sha256"])
        repeated = action in seen_actions
        steps.append(
            {
                "action_class_sha256": action,
                "new_usable_evidence_class_count": len(new_usable),
                "new_source_class_count": len(new_sources),
                "new_contradiction_class_count": len(new_contradictions),
                "stagnant_repeat": bool(
                    repeated
                    and not new_usable
                    and not new_sources
                    and not new_contradictions
                ),
            }
        )
        seen_usable.update(usable)
        seen_sources.update(sources)
        seen_contradictions.update(contradictions)
        seen_actions.add(action)
    return {
        "steps": steps,
        "usable_page_evidence_classes": seen_usable,
        "source_classes": seen_sources,
        "contradiction_page_evidence_classes": seen_contradictions,
        "nonpage_observation_count": nonpage_count,
    }


def _stagnant_suffix_repeats(features: Mapping[str, Any], action: str) -> int:
    count = 0
    for step in reversed(features["steps"]):
        if step["action_class_sha256"] != action:
            continue
        if not step["stagnant_repeat"]:
            break
        count += 1
    return count


def _build_decision(
    *,
    ledger: Mapping[str, Any],
    trace: Sequence[Mapping[str, Any]],
    opaque_task_ref_sha256: str,
    decision_index: int,
) -> dict[str, Any]:
    required = [item for item in ledger["predicates"] if item["required"]]
    counts = {
        status: sum(item["status"] == status for item in required)
        for status in PREDICATE_STATUSES
    }
    pending = [item for item in required if item["status"] != "supported"]
    pending.sort(
        key=lambda item: (
            0 if item["status"] == "contradicted" else 1,
            item["priority"],
            item["predicate_ref_sha256"],
        )
    )
    features = _trace_features(trace)
    usable_classes = features["usable_page_evidence_classes"]
    contradiction_classes = features["contradiction_page_evidence_classes"]
    for item in ledger["predicates"]:
        support_classes = set(item["support_evidence_class_sha256s"])
        if (
            not support_classes.issubset(usable_classes)
            or support_classes.intersection(contradiction_classes)
        ):
            raise ValueError(
                "V2.42.21 predicate support is not backed by clean trace page evidence"
            )
        if not set(item["contradiction_evidence_class_sha256s"]).issubset(
            contradiction_classes
        ):
            raise ValueError(
                "V2.42.21 predicate contradiction is not backed by trace page evidence"
            )
    pending_actions = sorted({item["action_class_sha256"] for item in pending})
    stagnant = {
        action: _stagnant_suffix_repeats(features, action)
        for action in pending_actions
    }

    selected_predicate: str | None = None
    selected_action: str | None = None
    if not pending:
        decision_kind = "answer_ready"
        reason = "all_required_predicates_have_clean_page_backed_support"
    else:
        candidate = next(
            (
                item
                for item in pending
                if stagnant[item["action_class_sha256"]]
                < MINIMUM_STAGNANT_REPEATS
            ),
            None,
        )
        if candidate is None:
            decision_kind = "abstain_exhausted"
            reason = "all_pending_action_classes_exhausted_without_success_claim"
        else:
            decision_kind = "continue"
            selected_predicate = candidate["predicate_ref_sha256"]
            selected_action = candidate["action_class_sha256"]
            reason = (
                "highest_priority_pending_predicate_nonexhausted_action"
                if stagnant.get(selected_action, 0) == 0
                else "pending_predicate_action_below_exhaustion_threshold"
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
        "root_scope_sha256": ledger["root_scope_sha256"],
        "decision_index": _integer(
            decision_index,
            label="decision index",
            maximum=1_000_000,
        ),
        "predicate_ledger_sha256": ledger["ledger_sha256"],
        "trace_sha256": object_sha256(trace),
        "required_predicate_count": len(required),
        "required_supported_count": counts["supported"],
        "required_unresolved_count": counts["unresolved"],
        "required_contradicted_count": counts["contradicted"],
        "pending_action_count": len(pending_actions),
        "pending_action_stagnant_repeats": stagnant,
        "minimum_stagnant_repeats": MINIMUM_STAGNANT_REPEATS,
        "usable_page_evidence_class_count": len(
            features["usable_page_evidence_classes"]
        ),
        "source_class_count": len(features["source_classes"]),
        "contradiction_page_evidence_class_count": len(
            features["contradiction_page_evidence_classes"]
        ),
        "nonpage_observation_count": features["nonpage_observation_count"],
        "decision_kind": decision_kind,
        "selected_predicate_ref_sha256": selected_predicate,
        "selected_action_class_sha256": selected_action,
        "decision_reason": reason,
        "answer_ready_is_not_task_success": True,
        "open_set_completeness_claimed": False,
        "source_independence_claimed": False,
        "four_layer_risk_entropy_or_voc_used": False,
        "question_text_or_raw_evidence_read": False,
        "mapping_gold_category_question_type_evaluator_score_or_reward_read": False,
        "file_environment_network_model_search_fetch_or_process_accessed": False,
        "benchmark_forward_evaluator_credit_or_training_authorized": False,
    }


def decide_cgdp_baseline(
    *,
    predicate_ledger: object,
    trace: object,
    opaque_task_ref_sha256: str,
    decision_index: int,
) -> dict[str, Any]:
    """Return one sealed baseline decision without performing an action."""

    ledger = validate_predicate_ledger(predicate_ledger)
    clean_trace = validate_trace(trace)
    receipt = _build_decision(
        ledger=ledger,
        trace=clean_trace,
        opaque_task_ref_sha256=opaque_task_ref_sha256,
        decision_index=decision_index,
    )
    receipt["receipt_sha256"] = object_sha256(receipt)
    return receipt


def validate_decision_receipt(
    value: object,
    *,
    predicate_ledger: object,
    trace: object,
    opaque_task_ref_sha256: str,
    decision_index: int,
) -> dict[str, Any]:
    """Recompute a decision so a resealed semantic mutation still fails."""

    reject_privileged_metadata(value, path="receipt")
    receipt = _exact_mapping(value, keys=RECEIPT_KEYS, label="decision receipt")
    expected = decide_cgdp_baseline(
        predicate_ledger=predicate_ledger,
        trace=trace,
        opaque_task_ref_sha256=opaque_task_ref_sha256,
        decision_index=decision_index,
    )
    if dict(receipt) != expected:
        raise ValueError("V2.42.21 decision receipt contract drifted")
    return expected
