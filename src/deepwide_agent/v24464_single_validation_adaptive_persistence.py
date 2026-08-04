"""Single-complete-validation persistence for V2.44.57 adaptive support.

``run_v24457_task`` already finishes by running the complete adaptive
semantic and cross-artifact validator.  The frozen persistence helper then
called ``build_envelope``, which recursively validated the same historical
graph a second time before the proof certificate was written.  On realistic
external envelopes that duplicate replay consumed the terminal reserve and
V2.44.63 produced no child terminal receipt.

This append-only adapter keeps the first complete validation unchanged.  It
mints an in-process opaque capability only after that call returns, builds the
byte-identical envelope mechanically from the validated outcome, checks only
the outer adaptive shell and compact receipts, writes the four terminal
artifacts, and then uses the unchanged V2.44.59 certificate builder.  The
trusted child therefore performs exactly one complete semantic replay; the
parent still verifies exact bytes, receipts, certificate, and terminal state.

This is a pinned-local-source trust boundary, not protection from a malicious
child.  It does not access benchmark labels, mapping, gold, evaluator state,
reward, score, or credentials.
"""

from __future__ import annotations

import copy
import threading
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from .v24323_shared_prefix_cell_entropy import payload_sha256
from .v24397_failure_observability import build_failure_snapshot
from .v24399_failure_observable_runner import (
    FAILURE_NAME,
    MODEL_NAME,
    RESULT_NAME,
    SEARCH_NAME,
    TRANSPORT_NAME,
    persist_failure_artifacts,
)
from . import v24457_adaptive_entropy_support as adaptive
from .v24457_adaptive_entropy_support import (
    ENVELOPE_ROLE,
    IntegratedAdaptiveEntropySupportOutcome,
    POLICY_ID as ADAPTIVE_POLICY_ID,
)
from .v24459_proof_carrying_adaptive_entropy_support import (
    CERTIFICATE_NAME,
    build_terminal_certificate,
)


POLICY_ID = "v24464_single_complete_validation_adaptive_persistence_v1"
_CAPTURE_LOCK = threading.Lock()


class ValidatedAdaptiveExecution:
    """Opaque in-process proof that frozen V2.44.57 returned successfully."""

    __slots__ = ("__outcome", "__parent_envelope")

    def __init__(self, *_: object, **__: object) -> None:
        raise TypeError("use run_single_validation_v24457_task")

    @classmethod
    def _create(
        cls,
        outcome: IntegratedAdaptiveEntropySupportOutcome,
        *,
        parent_envelope: Mapping[str, Any],
    ) -> "ValidatedAdaptiveExecution":
        if not isinstance(outcome, IntegratedAdaptiveEntropySupportOutcome):
            raise TypeError("V2.44.64 requires a validated adaptive outcome")
        instance = object.__new__(cls)
        instance.__outcome = outcome
        instance.__parent_envelope = copy.deepcopy(dict(parent_envelope))
        return instance

    def _trusted_outcome(self) -> IntegratedAdaptiveEntropySupportOutcome:
        return self.__outcome

    def _trusted_parent_envelope(self) -> dict[str, Any]:
        return copy.deepcopy(self.__parent_envelope)


def run_single_validation_v24457_task(
    task: Mapping[str, Any],
    *,
    model: Any,
    search: Any,
    partition_seed_sha256: str,
    limits: Any,
    monotonic: Callable[[], float],
) -> ValidatedAdaptiveExecution:
    """Run the unchanged complete validator once and mint a local capability."""

    captured: list[dict[str, Any]] = []
    # V2.44.57 constructs the exact parent envelope as an input to its final
    # complete cross-artifact validation.  Capture that already-validated
    # value in the single-threaded child instead of reconstructing it later.
    with _CAPTURE_LOCK:
        original = adaptive.parent.build_envelope

        def capture_parent(outcome: Any) -> dict[str, Any]:
            value = original(outcome)
            captured.append(copy.deepcopy(value))
            return value

        adaptive.parent.build_envelope = capture_parent
        try:
            outcome = adaptive.run_v24457_task(
                task,
                model=model,
                search=search,
                partition_seed_sha256=partition_seed_sha256,
                limits=limits,
                monotonic=monotonic,
            )
        finally:
            adaptive.parent.build_envelope = original
    if len(captured) != 1:
        raise RuntimeError("V2.44.64 complete parent validation count drifted")
    return ValidatedAdaptiveExecution._create(
        outcome, parent_envelope=captured[0]
    )


def build_envelope_from_validated_execution(
    validated: ValidatedAdaptiveExecution,
) -> dict[str, Any]:
    """Build the exact frozen envelope without a second semantic replay."""

    if not isinstance(validated, ValidatedAdaptiveExecution):
        raise TypeError("V2.44.64 requires a validated execution capability")
    outcome = validated._trusted_outcome()
    value = {
        "artifact_version": 1,
        "role": ENVELOPE_ROLE,
        "policy_id": ADAPTIVE_POLICY_ID,
        "parent_envelope": validated._trusted_parent_envelope(),
        "adaptive_result": copy.deepcopy(outcome.adaptive_result),
        "model_slot_receipt_before_adaptive_support": copy.deepcopy(
            outcome.model_slot_receipt_before_adaptive_support
        ),
        "transport_health_before_adaptive_support": copy.deepcopy(
            outcome.transport_health_before_adaptive_support
        ),
        "search_single_shot_receipt_before_adaptive_support": copy.deepcopy(
            outcome.search_single_shot_receipt_before_adaptive_support
        ),
        "model_slot_receipt": copy.deepcopy(outcome.model_slot_receipt),
        "transport_health": copy.deepcopy(outcome.transport_health),
        "search_single_shot_receipt": copy.deepcopy(
            outcome.search_single_shot_receipt
        ),
        "effect_delta_receipt": copy.deepcopy(outcome.effect_delta_receipt),
        "private_task_content_present": True,
        "private_task_content_emitted_to_public_aggregate": False,
        "credential_or_privileged_evaluator_content_present": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["envelope_payload_sha256"] = payload_sha256(value)
    # Importing the compact shell checker is intentional: unlike
    # validate_envelope, it checks the outer seals/receipts and parent/result
    # binding without recursively replaying the historical semantic graph.
    from .v24459_proof_carrying_adaptive_entropy_support import _validate_shells

    shell, _, _ = _validate_shells(value)
    if shell != value:
        raise RuntimeError("V2.44.64 compact envelope shell drifted")
    return value


def run_and_persist_single_validation_adaptive_task(
    task: Mapping[str, Any],
    *,
    model_factory: Callable[[], Any],
    search_factory: Callable[[], Any],
    partition_seed_sha256: str,
    limits: Any,
    monotonic: Callable[[], float],
    expected_model_cap: int,
    directory: Path,
    writer: Callable[[str, Mapping[str, Any]], None],
    validator_manifest_sha256: str,
) -> IntegratedAdaptiveEntropySupportOutcome:
    """Run once, persist exact artifacts, then publish the proof certificate."""

    model: Any = None
    search: Any = None
    stage = "model_construction"
    try:
        model = model_factory()
        stage = "search_construction"
        search = search_factory()
        stage = "runtime"
        validated = run_single_validation_v24457_task(
            task,
            model=model,
            search=search,
            partition_seed_sha256=partition_seed_sha256,
            limits=limits,
            monotonic=monotonic,
        )
    except BaseException as error:
        persist_failure_artifacts(
            error,
            failure_stage=stage,
            model=model,
            search=search,
            expected_model_cap=expected_model_cap,
            writer=writer,
        )
        raise

    outcome = validated._trusted_outcome()
    envelope = build_envelope_from_validated_execution(validated)
    artifacts = {
        MODEL_NAME: copy.deepcopy(outcome.model_slot_receipt),
        TRANSPORT_NAME: copy.deepcopy(outcome.transport_health),
        SEARCH_NAME: copy.deepcopy(outcome.search_single_shot_receipt),
        RESULT_NAME: envelope,
    }
    written: set[str] = set()
    try:
        for name in (MODEL_NAME, TRANSPORT_NAME, SEARCH_NAME, RESULT_NAME):
            writer(name, artifacts[name])
            written.add(name)
    except BaseException as error:
        snapshot = build_failure_snapshot(
            error,
            failure_stage="artifact_serialization",
            model_receipt=(
                outcome.model_slot_receipt if MODEL_NAME in written else None
            ),
            transport_health=(
                outcome.transport_health if TRANSPORT_NAME in written else None
            ),
            search_receipt=(
                outcome.search_single_shot_receipt if SEARCH_NAME in written else None
            ),
            expected_model_cap=expected_model_cap,
        )
        writer(FAILURE_NAME, snapshot)
        raise

    certificate = build_terminal_certificate(
        directory,
        outcome,
        validator_manifest_sha256=validator_manifest_sha256,
        expected_artifacts=artifacts,
    )
    writer(CERTIFICATE_NAME, certificate)
    return outcome


__all__ = [
    "POLICY_ID",
    "ValidatedAdaptiveExecution",
    "build_envelope_from_validated_execution",
    "run_and_persist_single_validation_adaptive_task",
    "run_single_validation_v24457_task",
]
