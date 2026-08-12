#!/usr/bin/env python3
"""One-shot in-memory V2.52.19 snapshot population freezer.

The effectful entry point requires a hash-bound execution-start artifact.  It
runs exactly one V2.52.18 batch, parses all four bodies in memory, ranks fixed
snapshot candidates, runs the V2.52.13 repository-history audit, and persists
only content-free receipts plus the final visible task vector on a complete GO.
Raw snapshots, candidate pools, stratum-to-identity maps, and per-item hashes
are never written.  Any failure is whole-batch NO-GO without retry/backfill.
"""

from __future__ import annotations

import argparse
import copy
import fcntl
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25215_offline_candidate_discovery as discovery  # noqa: E402
from deepwide_agent import v25218_snapshot_hard_deadline_controller as controller  # noqa: E402


DATE = "20260812"
OUTPUT = Path(f"results/v25219_snapshot_population_freeze_v1_{DATE}.json")
ATTEMPT_CLAIM = Path(
    f"results/v25219_snapshot_population_attempt_claim_v1_{DATE}.json"
)
EXECUTION_START = Path(
    f"results/v25219_snapshot_population_execution_start_v1_{DATE}.json"
)
PREAUDIT = Path(
    f"results/v25219_snapshot_population_preactivation_audit_v1_{DATE}.json"
)
ROLE = "v25219_snapshot_population_freeze_result"
PROTOCOL_ID = "v25219_snapshot_population_freeze_v1"
SELECTION_ROLE = "v25213_receipt_reliability_population_selection_aggregate_audit"
TASK_COUNT = 64
TASKS_PER_STRATUM = 16
OVERSAMPLE_PER_STRATUM = 64
HISTORY_PATHS = (
    "src",
    "evaluation",
    "scripts",
    "tests",
    "results",
    "outputs",
)
SOURCE_FILES = (
    Path("scripts/control_v25219_snapshot_population.py"),
    Path("scripts/run_v25219_snapshot_population.py"),
    Path("tests/test_control_v25219_snapshot_population.py"),
    Path("tests/test_run_v25219_snapshot_population.py"),
    Path("src/deepwide_agent/v25218_snapshot_hard_deadline_controller.py"),
    Path("src/deepwide_agent/v25217_single_snapshot_transport.py"),
    Path("src/deepwide_agent/v25215_offline_candidate_discovery.py"),
    Path("scripts/design_v25214_candidate_preselection_protocol.py"),
    Path("scripts/audit_v25213_population_selection.py"),
)
RUNTIME_SOURCE_FILES = (
    Path("scripts/run_v25219_snapshot_population.py"),
    Path("src/deepwide_agent/v25215_offline_candidate_discovery.py"),
    Path("src/deepwide_agent/v25217_single_snapshot_transport.py"),
    Path("src/deepwide_agent/v25218_snapshot_hard_deadline_controller.py"),
)
LEASE_PATH = Path("outputs/deepwide_benchmark_api.lease.lock")
PROTECTED_WATCHERS = {
    795336: 713986317,
    2808901: 746680268,
    2889939: 746969965,
    3061652: 747569004,
}
PARENT_AUDIT = Path(
    "results/v25218_snapshot_hard_deadline_controller_build_audit_v1_20260812.json"
)
EXPECTED_PARENT_AUDIT_SHA256 = (
    "988185da358ad0a9b13e846c1abc735152a4a4cf60a103bc74ee6b7c4ba86edc"
)
TEST_SUITES = (
    ("test_control_v25219_snapshot_population.py", 6),
    ("test_run_v25219_snapshot_population.py", 13),
    ("test_audit_v25218_snapshot_hard_deadline_controller_build.py", 6),
    ("test_v25218_snapshot_hard_deadline_controller.py", 8),
    ("test_v25215_offline_candidate_discovery.py", 8),
    ("test_audit_v25213_population_selection.py", 6),
)
PARENT_RECEIPT_EFFECT_DISCLOSURE = {
    "legacy_field_name": "model_search_evaluator_benchmark_or_api_effect",
    "legacy_recorded_value": False,
    "legacy_field_is_overbroad_for_effectful_snapshot_execution": True,
    "legacy_value_must_not_be_used_to_deny_public_snapshot_network_or_api_effect": True,
    "current_public_snapshot_network_or_api_call_reported_separately": True,
    "current_model_hosted_search_tavily_evaluator_or_benchmark_called": False,
}
_CRATE = re.compile(r"[a-z0-9][a-z0-9_-]{0,99}")
_CRAN = re.compile(r"[a-z][a-z0-9.]{0,99}")
_DOI = re.compile(r"10\.[0-9]{4,9}/[-._;()/:a-z0-9]{1,80}")
_PYPI = re.compile(r"[a-z0-9](?:[a-z0-9-]{1,6}[a-z0-9])?")
_PATTERNS = {
    discovery.STRATA[0]: _CRATE,
    discovery.STRATA[1]: _CRAN,
    discovery.STRATA[2]: _DOI,
    discovery.STRATA[3]: _PYPI,
}


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _ordinary(relative: Path) -> Path:
    path = ROOT / relative
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(ROOT.resolve())
    ):
        raise RuntimeError("V2.52.19 expected ordinary repository file")
    return path


def _source_manifest() -> dict[str, str]:
    return {str(path): sha256(_ordinary(path)) for path in SOURCE_FILES}


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=30,
        check=True,
    ).stdout.strip()


def _protected_watchers_match() -> bool:
    for pid, expected in PROTECTED_WATCHERS.items():
        path = Path("/proc") / str(pid) / "stat"
        if not path.is_file():
            return False
        try:
            raw = path.read_text(encoding="utf-8")
            suffix = raw[raw.rfind(")") + 2 :].split()
            start = int(suffix[19]) if len(suffix) > 19 else None
        except (OSError, ValueError):
            return False
        if start != expected:
            return False
    return True


def _acquire_api_lease() -> Any:
    path = ROOT / LEASE_PATH
    if path.is_symlink():
        raise RuntimeError("V2.52.19 shared API lease path drifted")
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open("a+", encoding="utf-8")
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (BlockingIOError, OSError):
        handle.close()
        raise RuntimeError("V2.52.19 shared API lease active") from None
    return handle


def _normalize_identity(value: object) -> str:
    return "-".join(str(value).casefold().split())


def _validate_candidates(
    candidates: Mapping[str, Sequence[str]],
) -> dict[str, tuple[str, ...]]:
    if not isinstance(candidates, Mapping) or set(candidates) != set(discovery.STRATA):
        raise RuntimeError("V2.52.19 selection stratum set drifted")
    normalized: dict[str, tuple[str, ...]] = {}
    all_identities: list[str] = []
    for stratum in discovery.STRATA:
        values = candidates.get(stratum)
        if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
            raise RuntimeError("V2.52.19 selection vector drifted")
        rows = tuple(_normalize_identity(value) for value in values)
        if (
            len(rows) != TASKS_PER_STRATUM
            or len(set(rows)) != TASKS_PER_STRATUM
            or any(not value or len(value) > 100 for value in rows)
        ):
            raise RuntimeError("V2.52.19 selection vector drifted")
        normalized[stratum] = rows
        all_identities.extend(rows)
    if len(all_identities) != TASK_COUNT or len(set(all_identities)) != TASK_COUNT:
        raise RuntimeError("V2.52.19 global selection vector drifted")
    return normalized


def _deterministic_rank(
    stratum: str, identity: str, *, snapshot_sha256: str
) -> str:
    if stratum not in discovery.STRATA:
        raise ValueError("V2.52.19 sampling stratum drifted")
    normalized = _normalize_identity(identity)
    if not normalized or len(normalized) > 100:
        raise ValueError("V2.52.19 candidate identity drifted")
    if (
        not isinstance(snapshot_sha256, str)
        or len(snapshot_sha256) != 64
        or any(character not in "0123456789abcdef" for character in snapshot_sha256)
    ):
        raise ValueError("V2.52.19 snapshot hash drifted")
    return hashlib.sha256(
        f"v25214\0{stratum}\0{snapshot_sha256}\0{normalized}".encode()
    ).hexdigest()


def _select_candidates(
    candidates: Mapping[str, Sequence[str]],
    *,
    snapshot_hashes: Mapping[str, str],
) -> dict[str, list[str]]:
    if set(candidates) != set(discovery.STRATA) or set(snapshot_hashes) != set(
        discovery.STRATA
    ):
        raise RuntimeError("V2.52.19 candidate or snapshot stratum drifted")
    output: dict[str, list[str]] = {}
    global_seen: set[str] = set()
    for stratum in discovery.STRATA:
        normalized = [_normalize_identity(value) for value in candidates[stratum]]
        if (
            len(normalized) < OVERSAMPLE_PER_STRATUM
            or len(set(normalized)) != len(normalized)
            or any(not value or len(value) > 100 for value in normalized)
        ):
            raise RuntimeError("V2.52.19 oversample candidate pool drifted")
        ranked = sorted(
            normalized,
            key=lambda identity: (
                _deterministic_rank(
                    stratum,
                    identity,
                    snapshot_sha256=snapshot_hashes[stratum],
                ),
                identity,
            ),
        )
        selected = ranked[:TASKS_PER_STRATUM]
        if global_seen.intersection(selected):
            raise RuntimeError("V2.52.19 cross-stratum identity collision")
        global_seen.update(selected)
        output[stratum] = selected
    _validate_candidates(output)
    return output


def _identity_safe(stratum: str, identity: str) -> bool:
    return bool(
        isinstance(identity, str)
        and identity == identity.strip()
        and not any(ord(character) < 32 or ord(character) == 127 for character in identity)
        and _PATTERNS[stratum].fullmatch(identity) is not None
    )


def _question(stratum: str, identity: str) -> str:
    visible = json.dumps(identity, ensure_ascii=False)
    if stratum == discovery.STRATA[0]:
        return (
            "Retrieve the current public crates.io metadata record for the visible "
            f"crate named {visible}. Return exactly one Markdown table and no prose. "
            "Columns exactly: Crate | MaxVersion | Description. Preserve the canonical "
            "crate name, current maximum version, and published description. Use Unknown "
            "only when same-forward public pages do not establish a value."
        )
    if stratum == discovery.STRATA[1]:
        return (
            "Retrieve the current public CRAN metadata record for the visible R package "
            f"named {visible}. Return exactly one Markdown table and no prose. Columns "
            "exactly: Package | Version | License | SystemRequirementsOrSuggests. Preserve "
            "the canonical package spelling and complete published field values. Use "
            "Unknown only when same-forward public pages do not establish a value."
        )
    if stratum == discovery.STRATA[2]:
        return (
            "Retrieve the current public bibliographic record for the visible DOI "
            f"{visible}. Return exactly one Markdown table and no prose. Columns exactly: "
            "DOI | Title | Publisher | ContainerTitle. Preserve the canonical DOI and "
            "published record values. Use Unknown only when same-forward public pages do "
            "not establish a value."
        )
    if stratum == discovery.STRATA[3]:
        return (
            "Retrieve the current public PyPI metadata record for the visible project "
            f"named {visible}. Return exactly one Markdown table and no prose. Columns "
            "exactly: Project | Version | Summary | RequiresPython. Preserve the canonical "
            "project spelling and current published values. Use Unknown only when "
            "same-forward public pages do not establish a value."
        )
    raise ValueError("V2.52.19 task stratum drifted")


def _task_vector(selected: Mapping[str, Sequence[str]]) -> list[dict[str, str]]:
    _validate_candidates(selected)
    rows: list[dict[str, str]] = []
    index = 0
    for offset in range(TASKS_PER_STRATUM):
        for stratum in discovery.STRATA:
            identity = selected[stratum][offset]
            if not _identity_safe(stratum, identity):
                raise RuntimeError("V2.52.19 unsafe selected identity")
            rows.append(
                {
                    "opaque_id": "task_"
                    + hashlib.sha256(f"v25219:{index}".encode()).hexdigest()[:24],
                    "question": _question(stratum, identity),
                }
            )
            index += 1
    return validate_task_vector(rows)


def _task_safe_candidates(
    candidate_pools: Mapping[str, Sequence[str]],
) -> dict[str, list[str]]:
    safe: dict[str, list[str]] = {}
    for stratum in discovery.STRATA:
        values = candidate_pools.get(stratum)
        if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
            raise RuntimeError("V2.52.19 candidate pool shape drifted")
        rows = [
            identity
            for identity in values
            if isinstance(identity, str) and _identity_safe(stratum, identity)
        ]
        if (
            len(rows) < OVERSAMPLE_PER_STRATUM
            or len(set(rows)) != len(rows)
        ):
            raise RuntimeError("V2.52.19 task-safe candidate coverage failed")
        safe[stratum] = rows
    return safe


def _batch_body_receipt_binding(
    bodies: object, batch_receipt: Mapping[str, Any]
) -> bool:
    if (
        batch_receipt.get("terminal_outcome") != "success"
        or not isinstance(bodies, Mapping)
        or set(bodies) != set(discovery.STRATA)
    ):
        return False
    for stratum in discovery.STRATA:
        body = bodies.get(stratum)
        child = (batch_receipt.get("children") or {}).get(stratum)
        nested = child.get("transport_receipt") if isinstance(child, Mapping) else None
        if (
            not isinstance(body, bytes)
            or not isinstance(nested, Mapping)
            or nested.get("terminal_outcome") != "success"
            or nested.get("response_bytes") != len(body)
            or nested.get("response_sha256") != hashlib.sha256(body).hexdigest()
        ):
            return False
    return True


def _public_snapshot_network_or_api_called(
    batch_receipt: Mapping[str, Any],
) -> bool:
    children = batch_receipt.get("children") or {}
    return any(
        isinstance(row, Mapping)
        and row.get("started") is True
        for row in children.values()
    )


_SELECTION_AUDIT_FIELDS = frozenset(
    {
        "artifact_version",
        "role",
        "created_at_unix",
        "parent_commit",
        "risk_strata",
        "tasks_per_stratum",
        "identity_count",
        "unique_identity_count",
        "stratum_identity_counts",
        "ordered_identity_vector_sha256",
        "identity_history_introduction_hit_total",
        "identity_history_zero_hit_count",
        "stratum_identity_history_zero_hit_counts",
        "selection_uses_local_repository_history_only",
        "candidate_preselection_provenance_attested_by_selector",
        "identity_plaintext_item_hash_or_stratum_identity_mapping_persisted",
        "endpoint_page_value_question_prediction_or_evidence_persisted",
        "risk_stratum_passed_as_hidden_runtime_input_or_router_signal",
        "identity_is_future_visible_task_input_not_hidden_mapping",
        "selection_script_network_model_search_fetch_or_evaluator_called",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "prior_external_or_deepwidebench_population_reuse",
        "population_frozen_or_external_protocol_authorized",
        "retry_resume_replacement_selective_rerun_or_revaluation_authorized",
        "entropy_or_information_gain_assigns_signed_credit",
        "findings",
        "audit_valid",
        "audit_payload_sha256",
    }
)


def _validated_selection_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    if set(value) != _SELECTION_AUDIT_FIELDS:
        raise RuntimeError("V2.52.19 selection audit surface drifted")
    checked = validate_selection_audit(value)
    if checked != dict(value):
        raise RuntimeError("V2.52.19 selection audit value drifted")
    return checked


def _parser_observations_bound(
    batch_receipt: Mapping[str, Any],
    parser_observations: Mapping[str, Mapping[str, Any]],
) -> bool:
    children = batch_receipt.get("children") or {}
    for stratum, observed in parser_observations.items():
        child = children.get(stratum)
        nested = child.get("transport_receipt") if isinstance(child, Mapping) else None
        if (
            not isinstance(nested, Mapping)
            or observed.get("snapshot_sha256") != nested.get("response_sha256")
            or (
                observed.get("parse_completed") is True
                and observed.get("snapshot_byte_count") != nested.get("response_bytes")
            )
        ):
            return False
    return True


def validate_task_vector(values: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
    if isinstance(values, (str, bytes)) or len(values) != TASK_COUNT:
        raise ValueError("V2.52.19 task denominator drifted")
    output: list[dict[str, str]] = []
    for index, row in enumerate(values):
        expected_opaque_id = "task_" + hashlib.sha256(
            f"v25219:{index}".encode()
        ).hexdigest()[:24]
        stratum = discovery.STRATA[index % len(discovery.STRATA)]
        if (
            not isinstance(row, Mapping)
            or set(row) != {"opaque_id", "question"}
            or row.get("opaque_id") != expected_opaque_id
            or not isinstance(row.get("question"), str)
        ):
            raise ValueError("V2.52.19 visible task drifted")
        identity = _identity_from_question(stratum, row["question"])
        if not _identity_safe(stratum, identity):
            raise ValueError("V2.52.19 visible task identity drifted")
        output.append({"opaque_id": str(row["opaque_id"]), "question": row["question"]})
    if len({row["opaque_id"] for row in output}) != TASK_COUNT:
        raise ValueError("V2.52.19 opaque identity collision")
    return output


def _identity_from_question(stratum: str, question: str) -> str:
    marker = "v25219identitymarker"
    template = _question(stratum, marker)
    encoded_marker = json.dumps(marker, ensure_ascii=False)
    prefix, separator, suffix = template.partition(encoded_marker)
    if not separator or not question.startswith(prefix) or not question.endswith(suffix):
        raise ValueError("V2.52.19 visible task template drifted")
    stop = len(question) - len(suffix) if suffix else len(question)
    encoded = question[len(prefix) : stop]
    try:
        identity = json.loads(encoded)
    except (json.JSONDecodeError, TypeError):
        raise ValueError("V2.52.19 visible task identity encoding drifted") from None
    if not isinstance(identity, str) or _question(stratum, identity) != question:
        raise ValueError("V2.52.19 visible task reconstruction drifted")
    return identity


def _selected_from_task_vector(
    values: Sequence[Mapping[str, Any]],
) -> dict[str, list[str]]:
    checked = validate_task_vector(values)
    selected = {stratum: [] for stratum in discovery.STRATA}
    for index, row in enumerate(checked):
        stratum = discovery.STRATA[index % len(discovery.STRATA)]
        selected[stratum].append(_identity_from_question(stratum, row["question"]))
    _validate_candidates(selected)
    return selected


def _history_hits(identity: str, *, parent_commit: str) -> int:
    completed = subprocess.run(
        [
            "git",
            "log",
            parent_commit,
            "-i",
            "-S",
            identity,
            "--format=%H",
            "--",
            *HISTORY_PATHS,
        ],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=30,
        check=True,
    )
    return sum(bool(line.strip()) for line in completed.stdout.splitlines())


def build_selection_audit(
    candidates: Mapping[str, Sequence[str]],
    *,
    parent_commit: str,
    now: int | None = None,
) -> dict[str, Any]:
    normalized = _validate_candidates(candidates)
    resolved = _git("rev-parse", "--verify", parent_commit + "^{commit}")
    ordered = [
        identity
        for stratum in discovery.STRATA
        for identity in normalized[stratum]
    ]
    hits = {
        stratum: [
            _history_hits(identity, parent_commit=resolved)
            for identity in normalized[stratum]
        ]
        for stratum in discovery.STRATA
    }
    total_hits = sum(sum(rows) for rows in hits.values())
    zero_counts = {
        stratum: sum(count == 0 for count in hits[stratum])
        for stratum in discovery.STRATA
    }
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": SELECTION_ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parent_commit": resolved,
        "risk_strata": list(discovery.STRATA),
        "tasks_per_stratum": TASKS_PER_STRATUM,
        "identity_count": len(ordered),
        "unique_identity_count": len(set(ordered)),
        "stratum_identity_counts": {
            stratum: len(normalized[stratum]) for stratum in discovery.STRATA
        },
        "ordered_identity_vector_sha256": payload_sha256(ordered),
        "identity_history_introduction_hit_total": total_hits,
        "identity_history_zero_hit_count": sum(zero_counts.values()),
        "stratum_identity_history_zero_hit_counts": zero_counts,
        "selection_uses_local_repository_history_only": True,
        "candidate_preselection_provenance_attested_by_selector": False,
        "identity_plaintext_item_hash_or_stratum_identity_mapping_persisted": False,
        "endpoint_page_value_question_prediction_or_evidence_persisted": False,
        "risk_stratum_passed_as_hidden_runtime_input_or_router_signal": False,
        "identity_is_future_visible_task_input_not_hidden_mapping": True,
        "selection_script_network_model_search_fetch_or_evaluator_called": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "prior_external_or_deepwidebench_population_reuse": False,
        "population_frozen_or_external_protocol_authorized": False,
        "retry_resume_replacement_selective_rerun_or_revaluation_authorized": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "findings": [] if total_hits == 0 else ["identity_history_not_disjoint"],
        "audit_valid": total_hits == 0,
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return validate_selection_audit(value)


def validate_selection_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    if set(copied) != _SELECTION_AUDIT_FIELDS:
        raise RuntimeError("V2.52.19 selection audit surface drifted")
    unsigned = dict(copied)
    seal = unsigned.pop("audit_payload_sha256", None)
    expected_counts = {
        stratum: TASKS_PER_STRATUM for stratum in discovery.STRATA
    }
    true_flags = (
        "selection_uses_local_repository_history_only",
        "identity_is_future_visible_task_input_not_hidden_mapping",
    )
    false_flags = (
        "candidate_preselection_provenance_attested_by_selector",
        "identity_plaintext_item_hash_or_stratum_identity_mapping_persisted",
        "endpoint_page_value_question_prediction_or_evidence_persisted",
        "risk_stratum_passed_as_hidden_runtime_input_or_router_signal",
        "selection_script_network_model_search_fetch_or_evaluator_called",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "prior_external_or_deepwidebench_population_reuse",
        "population_frozen_or_external_protocol_authorized",
        "retry_resume_replacement_selective_rerun_or_revaluation_authorized",
        "entropy_or_information_gain_assigns_signed_credit",
    )
    vector_hash = copied.get("ordered_identity_vector_sha256")
    if (
        copied.get("artifact_version") != 1
        or copied.get("role") != SELECTION_ROLE
        or not isinstance(copied.get("created_at_unix"), int)
        or isinstance(copied.get("created_at_unix"), bool)
        or not isinstance(copied.get("parent_commit"), str)
        or len(copied["parent_commit"]) != 40
        or any(
            character not in "0123456789abcdef"
            for character in copied["parent_commit"]
        )
        or copied.get("risk_strata") != list(discovery.STRATA)
        or copied.get("tasks_per_stratum") != TASKS_PER_STRATUM
        or copied.get("identity_count") != TASK_COUNT
        or copied.get("unique_identity_count") != TASK_COUNT
        or copied.get("stratum_identity_counts") != expected_counts
        or not isinstance(vector_hash, str)
        or len(vector_hash) != 64
        or any(character not in "0123456789abcdef" for character in vector_hash)
        or copied.get("identity_history_introduction_hit_total") != 0
        or copied.get("identity_history_zero_hit_count") != TASK_COUNT
        or copied.get("stratum_identity_history_zero_hit_counts")
        != expected_counts
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or copied.get("findings") != []
        or copied.get("audit_valid") is not True
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.52.19 population selection audit drifted")
    return copied


def _no_go(
    *,
    execution_start_sha256: str,
    execution_claim_sha256: str,
    parent_commit: str,
    failure_stage: str,
    batch_receipt: Mapping[str, Any],
    batch_body_receipt_binding_passed: bool,
    parser_observations: Mapping[str, Mapping[str, Any]],
    now: int,
) -> dict[str, Any]:
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": now,
        "status": "no_go",
        "failure_stage": failure_stage,
        "execution_start_sha256": execution_start_sha256,
        "execution_claim_sha256": execution_claim_sha256,
        "history_parent_commit": parent_commit,
        "batch_receipt": copy.deepcopy(dict(batch_receipt)),
        "batch_body_receipt_bytes_and_sha256_binding_required": True,
        "batch_body_receipt_bytes_and_sha256_binding_passed": (
            batch_body_receipt_binding_passed
        ),
        "parser_observations": copy.deepcopy(dict(parser_observations)),
        "selection_audit": None,
        "task_vector": [],
        "task_vector_sha256": None,
        "raw_snapshot_candidate_pool_stratum_identity_map_or_item_hash_persisted": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "public_snapshot_network_or_api_called": (
            _public_snapshot_network_or_api_called(batch_receipt)
        ),
        "model_hosted_search_tavily_evaluator_or_benchmark_called": False,
        "parent_receipt_effect_disclosure": copy.deepcopy(
            PARENT_RECEIPT_EFFECT_DISCLOSURE
        ),
        "authorization": {
            "fresh_disjoint_reliability_protocol_design": False,
            "external_forward_or_probe_runtime_integration": False,
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
        },
    }
    value["result_payload_sha256"] = payload_sha256(value)
    return validate_result(value)


def build_result(
    *,
    execution_start_sha256: str,
    execution_claim_sha256: str = "c" * 64,
    parent_commit: str,
    batch_runner: Callable[..., tuple[dict[str, bytes], dict[str, Any]]] = controller.run_snapshot_batch,
    history_builder: Callable[..., dict[str, Any]] = build_selection_audit,
    now: int | None = None,
) -> dict[str, Any]:
    created = int(time.time()) if now is None else int(now)
    bodies, batch_receipt = batch_runner()
    checked_batch = controller.validate_receipt(batch_receipt)
    body_binding_passed = _batch_body_receipt_binding(bodies, checked_batch)
    if not body_binding_passed:
        return _no_go(
            execution_start_sha256=execution_start_sha256,
            execution_claim_sha256=execution_claim_sha256,
            parent_commit=parent_commit,
            failure_stage="snapshot_transport",
            batch_receipt=checked_batch,
            batch_body_receipt_binding_passed=False,
            parser_observations={},
            now=created,
        )

    candidate_pools: dict[str, list[str]] = {}
    parser_observations: dict[str, dict[str, Any]] = {}
    for stratum in discovery.STRATA:
        candidates, observed = discovery.discover_candidates(
            bodies[stratum], stratum=stratum
        )
        parser_observations[stratum] = observed
        if (
            observed["parse_completed"] is not True
            or observed["minimum_candidate_count_met"] is not True
        ):
            return _no_go(
                execution_start_sha256=execution_start_sha256,
                execution_claim_sha256=execution_claim_sha256,
                parent_commit=parent_commit,
                failure_stage="snapshot_parse_or_coverage",
                batch_receipt=checked_batch,
                batch_body_receipt_binding_passed=True,
                parser_observations=parser_observations,
                now=created,
            )
        candidate_pools[stratum] = candidates

    try:
        safe_candidate_pools = _task_safe_candidates(candidate_pools)
        selected = _select_candidates(
            safe_candidate_pools,
            snapshot_hashes={
                stratum: parser_observations[stratum]["snapshot_sha256"]
                for stratum in discovery.STRATA
            },
        )
        if any(
            not _identity_safe(stratum, identity)
            for stratum in discovery.STRATA
            for identity in selected[stratum]
        ):
            raise RuntimeError("unsafe selected identity")
        selection_audit = history_builder(
            selected,
            parent_commit=parent_commit,
            now=created,
        )
        checked_selection = _validated_selection_audit(selection_audit)
        task_vector = _task_vector(selected)
    except BaseException:
        return _no_go(
            execution_start_sha256=execution_start_sha256,
            execution_claim_sha256=execution_claim_sha256,
            parent_commit=parent_commit,
            failure_stage="deterministic_selection_or_history",
            batch_receipt=checked_batch,
            batch_body_receipt_binding_passed=True,
            parser_observations=parser_observations,
            now=created,
        )

    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": created,
        "status": "go",
        "failure_stage": None,
        "execution_start_sha256": execution_start_sha256,
        "execution_claim_sha256": execution_claim_sha256,
        "history_parent_commit": parent_commit,
        "batch_receipt": checked_batch,
        "batch_body_receipt_bytes_and_sha256_binding_required": True,
        "batch_body_receipt_bytes_and_sha256_binding_passed": True,
        "parser_observations": parser_observations,
        "selection_audit": checked_selection,
        "task_vector": task_vector,
        "task_vector_sha256": payload_sha256(task_vector),
        "raw_snapshot_candidate_pool_stratum_identity_map_or_item_hash_persisted": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "public_snapshot_network_or_api_called": (
            _public_snapshot_network_or_api_called(checked_batch)
        ),
        "model_hosted_search_tavily_evaluator_or_benchmark_called": False,
        "parent_receipt_effect_disclosure": copy.deepcopy(
            PARENT_RECEIPT_EFFECT_DISCLOSURE
        ),
        "authorization": {
            "fresh_disjoint_reliability_protocol_design": True,
            "external_forward_or_probe_runtime_integration": False,
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
        },
    }
    value["result_payload_sha256"] = payload_sha256(value)
    return validate_result(value)


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("result_payload_sha256", None)
    status = copied.get("status")
    batch = copied.get("batch_receipt")
    parsers = copied.get("parser_observations")
    task_vector = copied.get("task_vector")
    authorization = copied.get("authorization") or {}
    expected_fields = {
        "artifact_version",
        "role",
        "protocol_id",
        "created_at_unix",
        "status",
        "failure_stage",
        "execution_start_sha256",
        "execution_claim_sha256",
        "history_parent_commit",
        "batch_receipt",
        "batch_body_receipt_bytes_and_sha256_binding_required",
        "batch_body_receipt_bytes_and_sha256_binding_passed",
        "parser_observations",
        "selection_audit",
        "task_vector",
        "task_vector_sha256",
        "raw_snapshot_candidate_pool_stratum_identity_map_or_item_hash_persisted",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "public_snapshot_network_or_api_called",
        "model_hosted_search_tavily_evaluator_or_benchmark_called",
        "parent_receipt_effect_disclosure",
        "authorization",
        "result_payload_sha256",
    }
    if (
        set(copied) != expected_fields
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("protocol_id") != PROTOCOL_ID
        or status not in {"go", "no_go"}
        or copied.get("failure_stage")
        not in {
            None,
            "snapshot_transport",
            "snapshot_parse_or_coverage",
            "deterministic_selection_or_history",
        }
        or not isinstance(copied.get("execution_start_sha256"), str)
        or len(copied["execution_start_sha256"]) != 64
        or not isinstance(copied.get("execution_claim_sha256"), str)
        or len(copied["execution_claim_sha256"]) != 64
        or any(
            character not in "0123456789abcdef"
            for character in copied["execution_claim_sha256"]
        )
        or not isinstance(copied.get("history_parent_commit"), str)
        or len(copied["history_parent_commit"]) != 40
        or not isinstance(batch, Mapping)
        or controller.validate_receipt(batch) != dict(batch)
        or copied.get("batch_body_receipt_bytes_and_sha256_binding_required")
        is not True
        or not isinstance(
            copied.get("batch_body_receipt_bytes_and_sha256_binding_passed"), bool
        )
        or not isinstance(parsers, Mapping)
        or not set(parsers).issubset(discovery.STRATA)
        or any(
            discovery.validate_observation(observed) != dict(observed)
            for observed in parsers.values()
        )
        or not _parser_observations_bound(batch, parsers)
        or not isinstance(task_vector, list)
        or copied.get(
            "raw_snapshot_candidate_pool_stratum_identity_map_or_item_hash_persisted"
        )
        is not False
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
        )
        is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit") is not False
        or copied.get("public_snapshot_network_or_api_called")
        is not _public_snapshot_network_or_api_called(batch)
        or copied.get(
            "model_hosted_search_tavily_evaluator_or_benchmark_called"
        )
        is not False
        or copied.get("parent_receipt_effect_disclosure")
        != PARENT_RECEIPT_EFFECT_DISCLOSURE
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.19 snapshot population result drifted")
    if status == "go":
        if (
            copied.get("failure_stage") is not None
            or batch["terminal_outcome"] != "success"
            or copied.get("batch_body_receipt_bytes_and_sha256_binding_passed")
            is not True
            or set(parsers) != set(discovery.STRATA)
            or any(
                observed["parse_completed"] is not True
                or observed["minimum_candidate_count_met"] is not True
                for observed in parsers.values()
            )
            or not isinstance(copied.get("selection_audit"), Mapping)
            or _validated_selection_audit(copied["selection_audit"])
            != dict(copied["selection_audit"])
            or copied["selection_audit"].get("parent_commit")
            != copied.get("history_parent_commit")
            or validate_task_vector(task_vector) != task_vector
            or copied.get("task_vector_sha256") != payload_sha256(task_vector)
            or copied["selection_audit"].get("ordered_identity_vector_sha256")
            != payload_sha256(
                [
                    identity
                    for stratum in discovery.STRATA
                    for identity in _selected_from_task_vector(task_vector)[stratum]
                ]
            )
            or authorization
            != {
                "fresh_disjoint_reliability_protocol_design": True,
                "external_forward_or_probe_runtime_integration": False,
                "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
            }
        ):
            raise ValueError("V2.52.19 GO result drifted")
    elif (
        copied.get("failure_stage") is None
        or copied.get("selection_audit") is not None
        or task_vector != []
        or copied.get("task_vector_sha256") is not None
        or authorization
        != {
            "fresh_disjoint_reliability_protocol_design": False,
            "external_forward_or_probe_runtime_integration": False,
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
        }
        or (
            copied.get("failure_stage") == "snapshot_transport"
            and (
                copied.get("batch_body_receipt_bytes_and_sha256_binding_passed")
                is not False
                or parsers != {}
            )
        )
        or (
            copied.get("failure_stage") == "snapshot_parse_or_coverage"
            and (
                copied.get("batch_body_receipt_bytes_and_sha256_binding_passed")
                is not True
                or not parsers
                or not any(
                    observed.get("parse_completed") is not True
                    or observed.get("minimum_candidate_count_met") is not True
                    for observed in parsers.values()
                )
            )
        )
        or (
            copied.get("failure_stage") == "deterministic_selection_or_history"
            and (
                copied.get("batch_body_receipt_bytes_and_sha256_binding_passed")
                is not True
                or set(parsers) != set(discovery.STRATA)
                or any(
                    observed.get("parse_completed") is not True
                    or observed.get("minimum_candidate_count_met") is not True
                    for observed in parsers.values()
                )
            )
        )
    ):
        raise ValueError("V2.52.19 NO-GO result drifted")
    return copied


def publish(path: Path, value: Mapping[str, Any]) -> None:
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
    directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def build_attempt_claim(
    *,
    execution_start_path: Path,
    execution_start_sha256: str,
    history_parent_commit: str,
    source_manifest: Mapping[str, str],
    now: int | None = None,
) -> dict[str, Any]:
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25219_snapshot_population_single_attempt_claim",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "execution_start": {
            "path": str(execution_start_path),
            "sha256": execution_start_sha256,
        },
        "history_parent_commit": history_parent_commit,
        "source_manifest": copy.deepcopy(dict(source_manifest)),
        "fixed_attempt_claim_path": str(ATTEMPT_CLAIM),
        "fixed_result_path": str(OUTPUT),
        "claim_created_before_public_snapshot_network_or_api_call": True,
        "claim_is_permanent_even_if_process_crashes_or_result_write_fails": True,
        "retry_refetch_backfill_replacement_or_second_batch_authorized": False,
        "public_snapshot_network_or_api_called_before_claim": False,
        "model_hosted_search_tavily_evaluator_or_benchmark_called": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
    }
    value["claim_payload_sha256"] = payload_sha256(value)
    return validate_attempt_claim(
        value, expected_source_manifest=source_manifest
    )


def validate_attempt_claim(
    value: Mapping[str, Any], *, expected_source_manifest: Mapping[str, str]
) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("claim_payload_sha256", None)
    start = copied.get("execution_start")
    manifest = copied.get("source_manifest")
    expected_fields = {
        "artifact_version",
        "role",
        "created_at_unix",
        "execution_start",
        "history_parent_commit",
        "source_manifest",
        "fixed_attempt_claim_path",
        "fixed_result_path",
        "claim_created_before_public_snapshot_network_or_api_call",
        "claim_is_permanent_even_if_process_crashes_or_result_write_fails",
        "retry_refetch_backfill_replacement_or_second_batch_authorized",
        "public_snapshot_network_or_api_called_before_claim",
        "model_hosted_search_tavily_evaluator_or_benchmark_called",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "claim_payload_sha256",
    }
    if (
        set(copied) != expected_fields
        or copied.get("artifact_version") != 1
        or copied.get("role")
        != "v25219_snapshot_population_single_attempt_claim"
        or not isinstance(copied.get("created_at_unix"), int)
        or isinstance(copied.get("created_at_unix"), bool)
        or not isinstance(start, Mapping)
        or set(start) != {"path", "sha256"}
        or start.get("path") != str(EXECUTION_START)
        or not isinstance(start.get("sha256"), str)
        or len(start["sha256"]) != 64
        or any(character not in "0123456789abcdef" for character in start["sha256"])
        or not isinstance(copied.get("history_parent_commit"), str)
        or len(copied["history_parent_commit"]) != 40
        or any(
            character not in "0123456789abcdef"
            for character in copied["history_parent_commit"]
        )
        or not isinstance(manifest, Mapping)
        or not manifest
        or dict(manifest) != dict(expected_source_manifest)
        or any(
            not isinstance(path, str)
            or not isinstance(digest, str)
            or len(digest) != 64
            or any(character not in "0123456789abcdef" for character in digest)
            for path, digest in manifest.items()
        )
        or copied.get("fixed_attempt_claim_path") != str(ATTEMPT_CLAIM)
        or copied.get("fixed_result_path") != str(OUTPUT)
        or copied.get(
            "claim_created_before_public_snapshot_network_or_api_call"
        )
        is not True
        or copied.get(
            "claim_is_permanent_even_if_process_crashes_or_result_write_fails"
        )
        is not True
        or copied.get(
            "retry_refetch_backfill_replacement_or_second_batch_authorized"
        )
        is not False
        or copied.get("public_snapshot_network_or_api_called_before_claim")
        is not False
        or copied.get(
            "model_hosted_search_tavily_evaluator_or_benchmark_called"
        )
        is not False
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
        )
        is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit")
        is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.19 execution claim drifted")
    return copied


def validate_preactivation_for_execution(
    value: Mapping[str, Any],
    *,
    expected_source_manifest: Mapping[str, str],
) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("audit_payload_sha256", None)
    authorization = copied.get("authorization")
    git = copied.get("git")
    tests = copied.get("tests")
    parent_audit = copied.get("parent_controller_build_audit")
    semantic = copied.get("semantic_audit")
    runtime = copied.get("runtime_state")
    checks = copied.get("checks")
    expected_fields = {
        "artifact_version",
        "role",
        "created_at_unix",
        "git",
        "tests",
        "source_manifest",
        "parent_controller_build_audit",
        "dependency_closure",
        "semantic_audit",
        "runtime_state",
        "checks",
        "findings",
        "audit_valid",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "public_snapshot_network_or_api_called",
        "model_hosted_search_tavily_evaluator_or_benchmark_called",
        "parent_receipt_effect_disclosure",
        "entropy_or_information_gain_assigns_signed_credit",
        "authorization",
        "audit_payload_sha256",
    }
    expected_checks = {
        "control_runner_parent_controller_discovery_selector_tests_exact47",
        "v25218_controller_build_audit_bound",
        "all_sources_tests_and_parent_artifacts_tracked",
        "git_clean_head_equals_target_main",
        "fork_start_method_available",
        "source_manifest_complete",
        "runtime_dependency_closure_exact",
        "privileged_runtime_field_access_zero",
        "evaluator_capability_zero",
        "credential_literal_zero",
        "execution_start_and_result_surfaces_pristine",
        "active_v25219_snapshot_runner_conflicts_zero",
        "protected_watchers_unchanged",
        "shared_api_lease_inactive",
        "no_public_snapshot_network_or_api_called_before_execution_start",
        "no_model_hosted_search_tavily_evaluator_or_benchmark_called",
        "no_external_effect_performed",
    }
    if (
        set(copied) != expected_fields
        or copied.get("artifact_version") != 1
        or copied.get("role")
        != "v25219_snapshot_population_preactivation_audit"
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or not isinstance(git, Mapping)
        or set(git) != {"head", "target_main", "equal", "clean"}
        or git.get("equal") is not True
        or git.get("clean") is not True
        or git.get("head") != git.get("target_main")
        or not isinstance(tests, Mapping)
        or set(tests) != {"expected", "observed", "passed", "suites"}
        or tests.get("expected") != 47
        or tests.get("observed") != 47
        or tests.get("passed") is not True
        or not isinstance(tests.get("suites"), list)
        or len(tests["suites"]) != len(TEST_SUITES)
        or any(
            not isinstance(row, Mapping)
            or set(row)
            != {
                "pattern",
                "expected",
                "observed",
                "returncode",
                "passed",
                "output_sha256",
            }
            or row.get("pattern") != pattern
            or row.get("expected") != expected
            or row.get("observed") != expected
            or row.get("returncode") != 0
            or row.get("passed") is not True
            or not isinstance(row.get("output_sha256"), str)
            or len(row["output_sha256"]) != 64
            or any(
                character not in "0123456789abcdef"
                for character in row["output_sha256"]
            )
            for row, (pattern, expected) in zip(
                tests["suites"], TEST_SUITES, strict=True
            )
        )
        or not isinstance(checks, Mapping)
        or set(checks) != expected_checks
        or any(checks.get(name) is not True for name in expected_checks)
        or copied.get("source_manifest") != dict(expected_source_manifest)
        or copied.get("dependency_closure")
        != [str(path) for path in RUNTIME_SOURCE_FILES]
        or not isinstance(parent_audit, Mapping)
        or set(parent_audit) != {"path", "sha256"}
        or parent_audit.get("path") != str(PARENT_AUDIT)
        or parent_audit.get("sha256") != EXPECTED_PARENT_AUDIT_SHA256
        or not isinstance(semantic, Mapping)
        or set(semantic)
        != {
            "privileged_runtime_field_accesses",
            "evaluator_capabilities",
            "credential_literal_hits",
            "allowed_provider_rank_access",
            "untracked_sources",
        }
        or semantic.get("privileged_runtime_field_accesses") != []
        or semantic.get("evaluator_capabilities") != []
        or semantic.get("credential_literal_hits") != []
        or semantic.get("allowed_provider_rank_access") != []
        or semantic.get("untracked_sources") != []
        or not isinstance(runtime, Mapping)
        or set(runtime)
        != {"shared_api_lease_inactive", "protected_watchers", "active_conflicts"}
        or runtime.get("shared_api_lease_inactive") is not True
        or runtime.get("active_conflicts") != []
        or not isinstance(runtime.get("protected_watchers"), Mapping)
        or set(runtime["protected_watchers"])
        != {str(pid) for pid in PROTECTED_WATCHERS}
        or not all(
            isinstance(row, Mapping)
            and set(row) == {"present", "start_ticks", "matches_frozen_identity"}
            and row.get("present") is True
            and row.get("start_ticks") == PROTECTED_WATCHERS[int(pid)]
            and row.get("matches_frozen_identity") is True
            for pid, row in runtime["protected_watchers"].items()
        )
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
        )
        is not False
        or copied.get("public_snapshot_network_or_api_called") is not False
        or copied.get(
            "model_hosted_search_tavily_evaluator_or_benchmark_called"
        )
        is not False
        or copied.get("parent_receipt_effect_disclosure")
        != PARENT_RECEIPT_EFFECT_DISCLOSURE
        or copied.get("entropy_or_information_gain_assigns_signed_credit")
        is not False
        or authorization
        != {
            "execution_start_generation": True,
            "single_public_snapshot_population_batch": False,
            "real_identity_selection_and_conditional_population_freeze": False,
            "external_forward_or_probe_runtime_integration": False,
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
        }
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.19 preactivation execution boundary drifted")
    return copied


def validate_execution_start(
    value: Mapping[str, Any],
    *,
    expected_source_manifest: Mapping[str, str],
) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("start_payload_sha256", None)
    authorization = copied.get("authorization")
    git = copied.get("git")
    preaudit = copied.get("preactivation_audit")
    expected_fields = {
        "artifact_version",
        "role",
        "created_at_unix",
        "git",
        "preactivation_audit",
        "source_manifest",
        "history_parent_commit",
        "single_batch_no_retry_refetch_backfill_or_partial_freeze",
        "public_snapshot_network_or_api_called",
        "model_hosted_search_tavily_evaluator_or_benchmark_called",
        "parent_receipt_effect_disclosure",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "authorization",
        "start_payload_sha256",
    }
    if (
        set(copied) != expected_fields
        or copied.get("artifact_version") != 1
        or copied.get("role")
        != "v25219_snapshot_population_execution_start"
        or not isinstance(git, Mapping)
        or set(git) != {"head", "target_main", "equal", "clean"}
        or git.get("equal") is not True
        or git.get("clean") is not True
        or git.get("head") != copied.get("history_parent_commit")
        or git.get("target_main") != copied.get("history_parent_commit")
        or not isinstance(preaudit, Mapping)
        or set(preaudit) != {"path", "sha256"}
        or preaudit.get("path") != str(PREAUDIT)
        or not isinstance(preaudit.get("sha256"), str)
        or len(preaudit["sha256"]) != 64
        or any(
            character not in "0123456789abcdef" for character in preaudit["sha256"]
        )
        or copied.get("source_manifest") != dict(expected_source_manifest)
        or not isinstance(copied.get("history_parent_commit"), str)
        or len(copied["history_parent_commit"]) != 40
        or any(
            character not in "0123456789abcdef"
            for character in copied["history_parent_commit"]
        )
        or copied.get("single_batch_no_retry_refetch_backfill_or_partial_freeze")
        is not True
        or copied.get("public_snapshot_network_or_api_called") is not False
        or copied.get(
            "model_hosted_search_tavily_evaluator_or_benchmark_called"
        )
        is not False
        or copied.get("parent_receipt_effect_disclosure")
        != PARENT_RECEIPT_EFFECT_DISCLOSURE
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
        )
        is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit")
        is not False
        or authorization
        != {
            "single_public_snapshot_population_batch": True,
            "real_identity_selection_and_conditional_population_freeze": True,
            "retry_refetch_backfill_or_second_batch": False,
            "external_forward_or_probe_runtime_integration": False,
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
        }
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.19 execution start drifted")
    return copied


def execution_start_commit_boundary(
    start: Mapping[str, Any],
    *,
    current_head: str,
    current_target: str,
    git: Callable[..., str],
) -> bool:
    try:
        parent_row = git("rev-list", "--parents", "-n", "1", current_head).split()
        changed = sorted(
            line.strip()
            for line in git(
                "diff-tree", "--no-commit-id", "--name-only", "-r", current_head
            ).splitlines()
            if line.strip()
        )
    except BaseException:
        return False
    return bool(
        current_head == current_target
        and len(parent_row) == 2
        and parent_row[0] == current_head
        and parent_row[1] == start.get("history_parent_commit")
        and changed == [str(EXECUTION_START)]
    )


def preactivation_commit_boundary(
    preaudit: Mapping[str, Any],
    *,
    preactivation_commit: str,
    git: Callable[..., str],
) -> bool:
    try:
        parent_row = git(
            "rev-list", "--parents", "-n", "1", preactivation_commit
        ).split()
        changed = sorted(
            line.strip()
            for line in git(
                "diff-tree",
                "--no-commit-id",
                "--name-only",
                "-r",
                preactivation_commit,
            ).splitlines()
            if line.strip()
        )
    except BaseException:
        return False
    return bool(
        len(parent_row) == 2
        and parent_row[0] == preactivation_commit
        and parent_row[1] == preaudit.get("git", {}).get("head")
        and changed == [str(PREAUDIT)]
    )


def main() -> None:
    command = argparse.ArgumentParser()
    command.add_argument("--execution-start", type=Path, required=True)
    command.add_argument("--expected-start-sha256", required=True)
    command.add_argument("--output", type=Path, default=OUTPUT)
    args = command.parse_args()

    if args.execution_start != EXECUTION_START or args.output != OUTPUT:
        raise RuntimeError("V2.52.19 frozen execution path drifted")
    start_path = _ordinary(EXECUTION_START)
    if sha256(start_path) != args.expected_start_sha256:
        raise RuntimeError("V2.52.19 execution-start hash drifted")
    current_manifest = _source_manifest()
    start = validate_execution_start(
        json.loads(start_path.read_text(encoding="utf-8")),
        expected_source_manifest=current_manifest,
    )
    preaudit_path = _ordinary(PREAUDIT)
    if sha256(preaudit_path) != start["preactivation_audit"]["sha256"]:
        raise RuntimeError("V2.52.19 preactivation hash drifted")
    preaudit = validate_preactivation_for_execution(
        json.loads(preaudit_path.read_text(encoding="utf-8")),
        expected_source_manifest=current_manifest,
    )
    current_head = _git("rev-parse", "HEAD")
    current_target = _git("rev-parse", "target/main")
    if (
        _git("status", "--porcelain")
        or not execution_start_commit_boundary(
            start,
            current_head=current_head,
            current_target=current_target,
            git=_git,
        )
        or not preactivation_commit_boundary(
            preaudit,
            preactivation_commit=start["history_parent_commit"],
            git=_git,
        )
        or not _protected_watchers_match()
        or start["authorization"]["single_public_snapshot_population_batch"]
        is not True
        or (ROOT / ATTEMPT_CLAIM).exists()
        or (ROOT / ATTEMPT_CLAIM).is_symlink()
        or (ROOT / args.output).exists()
        or (ROOT / args.output).is_symlink()
    ):
        raise RuntimeError("V2.52.19 execution boundary drifted")
    lease = _acquire_api_lease()
    try:
        if not _protected_watchers_match():
            raise RuntimeError("V2.52.19 protected watcher drifted before claim")
        claim = build_attempt_claim(
            execution_start_path=EXECUTION_START,
            execution_start_sha256=args.expected_start_sha256,
            history_parent_commit=start["history_parent_commit"],
            source_manifest=start["source_manifest"],
        )
        publish(ROOT / ATTEMPT_CLAIM, claim)
        validate_attempt_claim(
            json.loads((ROOT / ATTEMPT_CLAIM).read_text(encoding="utf-8")),
            expected_source_manifest=start["source_manifest"],
        )
        claim_sha256 = sha256(ROOT / ATTEMPT_CLAIM)
        value = build_result(
            execution_start_sha256=args.expected_start_sha256,
            execution_claim_sha256=claim_sha256,
            parent_commit=start["history_parent_commit"],
        )
        publish(ROOT / args.output, value)
    finally:
        try:
            fcntl.flock(lease.fileno(), fcntl.LOCK_UN)
        finally:
            lease.close()
    print(
        json.dumps(
            {
                "path": str(args.output),
                "status": value["status"],
                "failure_stage": value["failure_stage"],
                "task_count": len(value["task_vector"]),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
