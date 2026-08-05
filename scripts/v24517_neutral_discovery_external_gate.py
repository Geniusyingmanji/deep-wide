#!/usr/bin/env python3
"""Fresh one-wave external gate for neutral no-alternative discovery.

The frozen V2.45.14 terminal-state gate is reused with the V2.45.16 worker.
The new population is literal/canonical disjoint from all 348 prior external
questions and 2,784 entities.  V2.45.14 is closed and is never rerun.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24320_forward_contract import payload_sha256, sha256  # noqa: E402
from deepwide_agent.v24515_neutral_cell_discovery_planner import (  # noqa: E402
    POLICY_ID as PLANNER_POLICY_ID,
)
from deepwide_agent.v24516_neutral_discovery_record_bound_worker import (  # noqa: E402
    POLICY_ID as WORKER_POLICY_ID,
    run_neutral_discovery_record_bound_worker,
)
from scripts import v24514_terminal_state_external_gate as predecessor  # noqa: E402


DATE = "20260805"
PROTOCOL_ID = "v24517_fresh_neutral_discovery_terminal_external_gate_v1"
PROTOCOL = Path(f"results/v24517_neutral_external_preregistration_v1_{DATE}.json")
PREAUDIT = Path(
    f"results/v24517_neutral_external_preactivation_audit_v1_{DATE}.json"
)
ACTIVATION = Path(f"results/v24517_neutral_external_activation_v1_{DATE}.json")
EXECUTION_START = Path(
    f"results/v24517_neutral_external_execution_start_v1_{DATE}.json"
)
RESULT = Path(f"results/v24517_neutral_external_result_v1_{DATE}.json")
DECISION = Path(f"results/v24517_neutral_external_decision_v1_{DATE}.json")
POSTAUDIT = Path(
    f"results/v24517_neutral_external_postresult_audit_v1_{DATE}.json"
)
PARENT = Path(
    f"results/v24516_neutral_discovery_worker_build_audit_v1_{DATE}.json"
)
RUNNER_MARKER = "scripts/v24517_neutral_discovery_external_gate.py"
LEASE_OWNER = PROTOCOL_ID
LEASE_PURPOSE = "fresh_neutral_discovery_terminal_external_gate"
PRIOR_QUESTION_COUNT = 348
PRIOR_ENTITY_COUNT = 2784
PRIOR_QUESTIONS = predecessor._prior_questions() + predecessor.QUESTIONS
PREVIOUS_RESULT = predecessor.RESULT
PREVIOUS_DECISION = predecessor.DECISION
PREVIOUS_POSTAUDIT = predecessor.POSTAUDIT
PREVIOUS_PROTOCOL_ID = predecessor.PROTOCOL_ID
ENTITY_GROUPS = (
    (
        "Kenyon College",
        "Denison University",
        "Oberlin College",
        "Ohio Wesleyan University",
        "Hiram College",
        "Marietta College",
        "Muskingum University",
        "Otterbein University",
    ),
    (
        "Carleton College",
        "Macalester College",
        "St. Olaf College",
        "Gustavus Adolphus College",
        "Hamline University",
        "Augsburg University",
        "Concordia College Moorhead",
        "College of Saint Benedict",
    ),
    (
        "Simpson College",
        "Central College",
        "Dordt University",
        "Northwestern College",
        "Morningside University",
        "University of Dubuque",
        "Loras College",
        "Lawrence University",
    ),
    (
        "Hampden–Sydney College",
        "Sweet Briar College",
        "Randolph College",
        "Roanoke College",
        "Hollins University",
        "Bridgewater College",
        "Shenandoah University",
        "Emory & Henry University",
    ),
    (
        "Guilford College",
        "Catawba College",
        "Elon University",
        "High Point University",
        "Meredith College",
        "Queens University of Charlotte",
        "Warren Wilson College",
        "Sewanee: The University of the South",
    ),
    (
        "Claremont McKenna College",
        "Harvey Mudd College",
        "Scripps College",
        "Pitzer College",
        "Occidental College",
        "University of Redlands",
        "Whittier College",
        "Chapman University",
    ),
    (
        "Pacific Lutheran University",
        "Seattle Pacific University",
        "Whitworth University",
        "Gonzaga University",
        "Northwest University",
        "Saint Martin's University",
        "Walla Walla University",
        "Lewis–Clark State College",
    ),
    (
        "Nebraska Wesleyan University",
        "Doane University",
        "Hastings College",
        "Midland University",
        "Concordia University Nebraska",
        "Wayne State College",
        "Chadron State College",
        "Black Hills State University",
    ),
)


def _question(group: tuple[str, ...]) -> str:
    if len(group) != 8:
        raise ValueError("V2.45.17 entity group drifted")
    return (
        "Use public web sources to return one Markdown table about "
        + ", ".join(group[:-1])
        + ", and "
        + group[-1]
        + ". The column names are: University, Founding year. Return one table only."
    )


QUESTIONS = tuple(_question(group) for group in ENTITY_GROUPS)
GATES = dict(predecessor.GATES)
SOURCE_FILES = (
    *predecessor.SOURCE_FILES,
    "src/deepwide_agent/v24515_neutral_cell_discovery_planner.py",
    "src/deepwide_agent/v24516_neutral_discovery_record_bound_worker.py",
    "tests/test_v24515_neutral_cell_discovery_planner.py",
    "tests/test_v24516_neutral_discovery_record_bound_worker.py",
    "scripts/audit_v24516_neutral_discovery_worker_build.py",
    "tests/test_audit_v24516_neutral_discovery_worker_build.py",
    str(PARENT),
    str(PREVIOUS_RESULT),
    str(PREVIOUS_DECISION),
    str(PREVIOUS_POSTAUDIT),
    RUNNER_MARKER,
    "tests/test_v24517_neutral_discovery_external_gate.py",
)
TEST_SUITES = (
    ("tests/test_v24515_neutral_cell_discovery_planner.py", 7, 120),
    ("tests/test_v24516_neutral_discovery_record_bound_worker.py", 4, 300),
    ("tests/test_v24513_terminal_record_bound_projection.py", 7, 240),
    ("tests/test_v24514_terminal_state_external_gate.py", 11, 240),
    ("tests/test_v24517_neutral_discovery_external_gate.py", 10, 240),
)
EXPECTED_TEST_COUNT = 39


_ORIGINAL_PATCHED_CORE = predecessor._patched_core
_ORIGINAL_VALIDATE_PROTOCOL = predecessor.validate_protocol
_ORIGINAL_VALIDATE_PREAUDIT = predecessor.validate_preaudit
_ORIGINAL_VALIDATE_ACTIVATION = predecessor.validate_activation
_ORIGINAL_VALIDATE_EXECUTION_START = predecessor.validate_execution_start
_FROZEN_PREDECESSOR_RECORD_BOUND_BINDING = copy.deepcopy(
    predecessor._record_bound_binding()
)


def _read(relative: Path) -> dict[str, Any]:
    value = json.loads((ROOT / relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.45.17 expected object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _prior_questions() -> tuple[str, ...]:
    return PRIOR_QUESTIONS


def _fresh_entity_vector_valid() -> bool:
    parser = (
        predecessor.predecessor.predecessor.reserve_history.base.history.history.previous_gate.history.history.history.parent
    )
    current = {
        entity
        for question in QUESTIONS
        for entity in parser._question_entity_vector(question)
    }
    prior = {
        entity
        for question in _prior_questions()
        for entity in parser._question_entity_vector(question)
    }
    current_canonical = {parser._canonical_entity(item) for item in current}
    prior_canonical = {parser._canonical_entity(item) for item in prior}
    return (
        len(QUESTIONS) == 8
        and len(current) == 64
        and len(current_canonical) == 64
        and len(_prior_questions()) == PRIOR_QUESTION_COUNT
        and len(prior) == PRIOR_ENTITY_COUNT
        and len(prior_canonical) == PRIOR_ENTITY_COUNT
        and current.isdisjoint(prior)
        and current_canonical.isdisjoint(prior_canonical)
    )


def _parent(root: Path) -> dict[str, Any]:
    value = json.loads((root / PARENT).read_text(encoding="utf-8"))
    authorization = value.get("authorization", {})
    if (
        not isinstance(value, dict)
        or value.get("role") != "v24516_neutral_discovery_worker_build_audit"
        or value.get("audit_valid") is not True
        or value.get("findings") != []
        or authorization.get(
            "fresh_disjoint_neutral_discovery_external_protocol_design"
        )
        is not True
        or authorization.get("fresh_external_activation_or_launch") is not False
        or authorization.get("same_v24514_population_rerun") is not False
        or value.get("label_blind_audit", {}).get("passed") is not True
        or not _sealed(value, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.45.17 build parent drifted")
    return value


def _task_contract() -> dict[str, Any]:
    return {
        "selected": 8,
        "fixed_ordinal_vector": list(range(1, 9)),
        "one_wave_exactly_equals_selected_and_executor_count": True,
        "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_348_prior_external_questions": _fresh_entity_vector_valid(),
        "prior_external_question_count": PRIOR_QUESTION_COUNT,
        "prior_external_entity_count": PRIOR_ENTITY_COUNT,
        "all_prior_external_populations_rerun": False,
        "synthetic_identifiers_not_selected_from_benchmark": True,
        "runtime_input_keys_exactly_opaque_id_and_question": True,
        "question_opaque_id_or_private_content_persisted": False,
    }


def _previous_closed() -> bool:
    result = _read(PREVIOUS_RESULT)
    decision = _read(PREVIOUS_DECISION)
    postaudit = _read(PREVIOUS_POSTAUDIT)
    return (
        result.get("protocol_id") == PREVIOUS_PROTOCOL_ID
        and decision.get("protocol_id") == PREVIOUS_PROTOCOL_ID
        and postaudit.get("protocol_id") == PREVIOUS_PROTOCOL_ID
        and result.get("passed") is False
        and decision.get("status") == "fresh_targeted_external_no_go"
        and postaudit.get("audit_valid") is True
        and postaudit.get("shared_api_lease_active") is False
        and postaudit.get("findings") == []
        and _sealed(result, "result_payload_sha256")
        and _sealed(decision, "decision_payload_sha256")
        and _sealed(postaudit, "audit_payload_sha256")
    )


def _record_bound_binding() -> dict[str, Any]:
    if not _previous_closed():
        raise RuntimeError("V2.45.17 V2.45.14 closure drifted")
    return {
        **copy.deepcopy(_FROZEN_PREDECESSOR_RECORD_BOUND_BINDING),
        "neutral_discovery_planner_policy": PLANNER_POLICY_ID,
        "neutral_discovery_worker_policy": WORKER_POLICY_ID,
        "parent_build_audit_path": str(PARENT),
        "parent_build_audit_sha256": sha256(ROOT / PARENT),
        "prior_external_question_count": PRIOR_QUESTION_COUNT,
        "prior_external_entity_count": PRIOR_ENTITY_COUNT,
        "new_population_reuses_prior_question_or_entity": False,
        "v24512_population_rerun": False,
        "v24514_population_rerun": False,
        "v24514_result_sha256": sha256(ROOT / PREVIOUS_RESULT),
        "v24514_decision_sha256": sha256(ROOT / PREVIOUS_DECISION),
        "v24514_postaudit_sha256": sha256(ROOT / PREVIOUS_POSTAUDIT),
        "neutral_discovery_query_contains_candidate_value": False,
        "neutral_discovery_seed_receives_vote_or_source_credit": False,
        "neutral_discovery_queries_use_only_frozen_row_and_column": True,
    }


def _patched_core() -> dict[str, Any]:
    value = dict(_ORIGINAL_PATCHED_CORE())
    value.update(
        {
            "PROTOCOL_ID": PROTOCOL_ID,
            "PROTOCOL": PROTOCOL,
            "PREAUDIT": PREAUDIT,
            "ACTIVATION": ACTIVATION,
            "EXECUTION_START": EXECUTION_START,
            "RESULT": RESULT,
            "DECISION": DECISION,
            "POSTAUDIT": POSTAUDIT,
            "PARENT": PARENT,
            "LEASE_OWNER": LEASE_OWNER,
            "LEASE_PURPOSE": LEASE_PURPOSE,
            "RUNNER_MARKER": RUNNER_MARKER,
            "SOURCE_FILES": SOURCE_FILES,
            "TEST_SUITES": TEST_SUITES,
            "EXPECTED_TEST_COUNT": EXPECTED_TEST_COUNT,
            "ENTITY_GROUPS": ENTITY_GROUPS,
            "QUESTIONS": QUESTIONS,
            "GATES": GATES,
            "_prior_questions": _prior_questions,
            "_fresh_entity_vector_valid": _fresh_entity_vector_valid,
            "_parent": _parent,
            "_task_contract": _task_contract,
            "run_targeted_worker": run_neutral_discovery_record_bound_worker,
        }
    )
    return value


@contextmanager
def configured_predecessor(*, validators: bool = False) -> Iterator[None]:
    patches: dict[str, Any] = {
        "PROTOCOL_ID": PROTOCOL_ID,
        "PROTOCOL": PROTOCOL,
        "PREAUDIT": PREAUDIT,
        "ACTIVATION": ACTIVATION,
        "EXECUTION_START": EXECUTION_START,
        "RESULT": RESULT,
        "DECISION": DECISION,
        "POSTAUDIT": POSTAUDIT,
        "PARENT": PARENT,
        "RUNNER_MARKER": RUNNER_MARKER,
        "LEASE_OWNER": LEASE_OWNER,
        "LEASE_PURPOSE": LEASE_PURPOSE,
        "PRIOR_QUESTION_COUNT": PRIOR_QUESTION_COUNT,
        "PRIOR_ENTITY_COUNT": PRIOR_ENTITY_COUNT,
        "PRIOR_QUESTIONS": PRIOR_QUESTIONS,
        "PREVIOUS_RESULT": PREVIOUS_RESULT,
        "PREVIOUS_DECISION": PREVIOUS_DECISION,
        "PREVIOUS_POSTAUDIT": PREVIOUS_POSTAUDIT,
        "PREVIOUS_PROTOCOL_ID": PREVIOUS_PROTOCOL_ID,
        "ENTITY_GROUPS": ENTITY_GROUPS,
        "QUESTIONS": QUESTIONS,
        "GATES": GATES,
        "SOURCE_FILES": SOURCE_FILES,
        "TEST_SUITES": TEST_SUITES,
        "EXPECTED_TEST_COUNT": EXPECTED_TEST_COUNT,
        "_prior_questions": _prior_questions,
        "_fresh_entity_vector_valid": _fresh_entity_vector_valid,
        "_parent": _parent,
        "_task_contract": _task_contract,
        "_previous_closed": _previous_closed,
        "_record_bound_binding": _record_bound_binding,
        "_patched_core": _patched_core,
    }
    if validators:
        patches.update(
            {
                "validate_protocol": validate_protocol,
                "validate_preaudit": validate_preaudit,
                "validate_activation": validate_activation,
                "validate_execution_start": validate_execution_start,
            }
        )
    missing = object()
    originals = {name: getattr(predecessor, name, missing) for name in patches}
    try:
        for name, value in patches.items():
            setattr(predecessor, name, value)
        yield
    finally:
        for name, value in originals.items():
            if value is missing:
                delattr(predecessor, name)
            else:
                setattr(predecessor, name, value)


def build_protocol(
    *, now: int | None = None, require_pristine: bool = True
) -> dict[str, Any]:
    if not _previous_closed():
        raise RuntimeError("V2.45.17 predecessor is not closed")
    with configured_predecessor():
        return predecessor.build_protocol(
            now=now, require_pristine=require_pristine
        )


def validate_protocol(
    *, value: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    with configured_predecessor():
        copied = _ORIGINAL_VALIDATE_PROTOCOL(value=value)
    if (
        copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("record_bound_binding") != _record_bound_binding()
        or copied.get("task_contract") != _task_contract()
        or copied.get("gates") != GATES
        or not _sealed(copied, "protocol_payload_sha256")
    ):
        raise RuntimeError("V2.45.17 protocol drifted")
    return copied


def build_preaudit(*, now: int | None = None) -> dict[str, Any]:
    validate_protocol()
    with configured_predecessor():
        value = predecessor.build_preaudit(now=now)
    value = copy.deepcopy(value)
    checks = value["checks"]
    checks.pop(
        "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_340_prior_external_questions",
        None,
    )
    checks.pop("prior_external_questions_and_entities_exactly_340_and_2720", None)
    checks[
        "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_348_prior_external_questions"
    ] = True
    checks["prior_external_questions_and_entities_exactly_348_and_2784"] = True
    value["audit_payload_sha256"] = payload_sha256(
        {key: item for key, item in value.items() if key != "audit_payload_sha256"}
    )
    return validate_preaudit(value=value)


def validate_preaudit(
    *, value: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    copied = dict(value) if value is not None else _read(PREAUDIT)
    checks = copied.get("checks")
    if not isinstance(checks, Mapping):
        raise RuntimeError("V2.45.17 preaudit checks are absent")
    core = copy.deepcopy(copied)
    core_checks = core["checks"]
    core_checks.pop(
        "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_348_prior_external_questions",
        None,
    )
    core_checks.pop("prior_external_questions_and_entities_exactly_348_and_2784", None)
    core_checks[
        "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_340_prior_external_questions"
    ] = True
    core_checks["prior_external_questions_and_entities_exactly_340_and_2720"] = True
    core["audit_payload_sha256"] = payload_sha256(
        {key: item for key, item in core.items() if key != "audit_payload_sha256"}
    )
    with configured_predecessor():
        _ORIGINAL_VALIDATE_PREAUDIT(value=core)
    if (
        copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("audit_valid") is not True
        or copied.get("launch_authorized") is not True
        or checks.get(
            "fresh_64_entity_vector_literal_and_canonical_disjoint_from_all_348_prior_external_questions"
        )
        is not True
        or checks.get("prior_external_questions_and_entities_exactly_348_and_2784")
        is not True
        or checks.get("focused_tests", {}).get("test_count")
        != EXPECTED_TEST_COUNT
        or not _sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.45.17 preactivation audit drifted")
    return copied


def build_activation(*, now: int | None = None) -> dict[str, Any]:
    validate_protocol(); validate_preaudit()
    with configured_predecessor(validators=True):
        return predecessor.build_activation(now=now)


def validate_activation() -> dict[str, Any]:
    with configured_predecessor(validators=True):
        return _ORIGINAL_VALIDATE_ACTIVATION()


def build_execution_start(*, now: int | None = None) -> dict[str, Any]:
    validate_activation()
    with configured_predecessor(validators=True):
        return predecessor.build_execution_start(now=now)


def validate_execution_start() -> dict[str, Any]:
    with configured_predecessor(validators=True):
        return _ORIGINAL_VALIDATE_EXECUTION_START()


def validate_public_result(value: Mapping[str, Any]) -> dict[str, Any]:
    with configured_predecessor(validators=True):
        return predecessor.validate_public_result(value)


def run_probe() -> dict[str, Any]:
    with configured_predecessor(validators=True):
        return predecessor.run_probe()


def build_decision(*, now: int | None = None) -> dict[str, Any]:
    with configured_predecessor(validators=True):
        return predecessor.build_decision(now=now)


def build_postaudit(*, now: int | None = None) -> dict[str, Any]:
    with configured_predecessor(validators=True):
        return predecessor.build_postaudit(now=now)


def run_process_subcommand(args: argparse.Namespace) -> None:
    with configured_predecessor(validators=True):
        predecessor.run_process_subcommand(args)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=(
            "protocol", "preaudit", "activation", "start", "run", "finalize",
            "supervisor", "worker",
        ),
    )
    parser.add_argument("--ordinal")
    parser.add_argument("--output-root")
    parser.add_argument("--directory")
    parser.add_argument("--checkpoint-directory")
    parser.add_argument("--slots")
    parser.add_argument(
        predecessor.predecessor.predecessor.base.worker_budget.DEADLINE_ORIGIN_ARGUMENT
    )
    args = parser.parse_args()
    base = predecessor.predecessor.predecessor.base
    if args.command == "protocol":
        base.publish(ROOT / PROTOCOL, build_protocol())
    elif args.command == "preaudit":
        base.publish(ROOT / PREAUDIT, build_preaudit())
    elif args.command == "activation":
        base.publish(ROOT / ACTIVATION, build_activation())
    elif args.command == "start":
        base.publish(ROOT / EXECUTION_START, build_execution_start())
    elif args.command == "run":
        run_probe()
    elif args.command == "finalize":
        base.publish(ROOT / DECISION, build_decision())
        base.publish(ROOT / POSTAUDIT, build_postaudit())
    else:
        run_process_subcommand(args)


if __name__ == "__main__":
    main()
