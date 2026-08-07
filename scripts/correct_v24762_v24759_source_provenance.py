#!/usr/bin/env python3
"""Append-only correction for the V2.47.59 source-access provenance.

V2.47.59 correctly reproduced the population-capacity counts, but one
compound boolean incorrectly said that no ``network_model_search_...`` effect
preceded the V2.47.58 failure.  The population selector and the diagnosis both
read the immutable ROR Git snapshot over HTTPS.  They made no model, hosted
search, benchmark-forward, quality, or evaluator call.

This correction revokes the original successor authorization, records the
code-path-implied immutable read counts and absence of a direct transport
receipt, re-certifies the already-frozen V2.47.60 population without changing
its bytes, and authorizes only a replacement inert protocol publication.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
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

from deepwide_agent.v24320_forward_contract import payload_sha256  # noqa: E402
from scripts import diagnose_v24759_v24758_population_capacity as original  # noqa: E402
from scripts import design_v24760_zero_effect_population as population_design  # noqa: E402
from scripts import preregister_v24761_zero_effect_external as old_protocol  # noqa: E402


DATE = "20260806"
OUTPUT = Path(f"results/v24762_v24759_source_provenance_correction_v1_{DATE}.json")
ORIGINAL = original.OUTPUT
POPULATION = population_design.OUTPUT
PRIVATE = population_design.PRIVATE
CONTRACT = population_design.CONTRACT
OLD_PROTOCOL = old_protocol.OUTPUT
OLD_FUTURE_SURFACES = old_protocol.FUTURE_SURFACES
V24758_FAILED_SURFACES = population_design.FAILED_V24758_SURFACES
TREE_READS_PER_REPLAY = 1
RECORD_READS_PER_REPLAY = 3_482
INCORRECT_FIELD = (
    "network_model_search_benchmark_or_evaluator_effect_before_failure"
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


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("V2.47.62 expected ordinary JSON object")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.47.62 expected JSON object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def _parents() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    diagnosis = _read(ROOT / ORIGINAL)
    population = _read(ROOT / POPULATION)
    protocol = _read(ROOT / OLD_PROTOCOL)
    if (
        diagnosis.get("role")
        != "v24759_v24758_population_capacity_diagnosis"
        or diagnosis.get("failed_publication", {}).get(INCORRECT_FIELD)
        is not False
        or diagnosis.get("content_free_capacity", {}).get(
            "exact_v24758_failure_reproduced"
        )
        is not True
        or diagnosis.get("content_free_capacity", {}).get(
            "minimum_feasible_cap"
        )
        != 11
        or not _sealed(diagnosis, "diagnosis_payload_sha256")
        or population.get("role") != "v24760_zero_effect_population_design"
        or population.get("source", {}).get("tree_record_count")
        != RECORD_READS_PER_REPLAY
        or population.get("freshness", {}).get("selected_entity_count") != 32
        or population.get("freshness", {}).get("canonical_overlap_with_history")
        != 0
        or population.get("network")
        != {
            "immutable_ror_tree_reads": TREE_READS_PER_REPLAY,
            "immutable_ror_record_reads": RECORD_READS_PER_REPLAY,
            "model_search_benchmark_or_evaluator_calls": 0,
        }
        or population.get("authorization", {}).get(
            "activation_or_external_launch"
        )
        is not False
        or not _sealed(population, "design_payload_sha256")
        or protocol.get("role")
        != "v24761_zero_effect_external_preregistration"
        or protocol.get("authorization", {}).get("one_external_forward_launch")
        is not False
        or protocol.get("authorization", {}).get("quality_surface_open") is not False
        or not _sealed(protocol, "protocol_payload_sha256")
    ):
        raise RuntimeError("V2.47.62 parent chain drifted")
    return diagnosis, population, protocol


def build_correction(
    *, now: int | None = None, require_clean: bool = True, require_pristine: bool = True
) -> dict[str, Any]:
    if require_clean and (
        _git("status", "--porcelain")
        or _git("rev-parse", "HEAD") != _git("rev-parse", "target/main")
    ):
        raise RuntimeError("V2.47.62 correction requires clean pushed HEAD")
    if require_pristine and ((ROOT / OUTPUT).exists() or (ROOT / OUTPUT).is_symlink()):
        raise FileExistsError(OUTPUT)
    diagnosis, population, protocol = _parents()
    failed_pristine = all(
        not (ROOT / path).exists() and not (ROOT / path).is_symlink()
        for path in V24758_FAILED_SURFACES
    )
    old_future_pristine = all(
        not (ROOT / path).exists() and not (ROOT / path).is_symlink()
        for path in OLD_FUTURE_SURFACES
    )
    private_hash = sha256(ROOT / PRIVATE)
    contract_hash = sha256(ROOT / CONTRACT)
    population_recertified = bool(
        failed_pristine
        and old_future_pristine
        and population.get("private_population_file_sha256") == private_hash
        and population.get("visible_contract_sha256") == contract_hash
        and population.get("source", {}).get("tree_bytes_sha256")
        == "0fd37f3ad5b588c71d3509ce94a5316025d8b12d03455b208c6d966b25981107"
        and population.get("freshness", {}).get("eligible_record_count") == 1_180
        and population.get("freshness", {}).get(
            "canonical_unique_candidate_count"
        )
        == 1_180
        and population.get("freshness", {}).get("selected_country_count") == 6
        and population.get("freshness", {}).get("selected_country_max") == 11
        and population.get("selection_timing", {}).get(
            "generic_web_search_or_endpoint_reachability_used_for_selection"
        )
        is False
    )
    value = {
        "artifact_version": 1,
        "role": "v24762_v24759_source_provenance_correction",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git_head": _git("rev-parse", "HEAD"),
        "parents": {
            "v24759_original_artifact_sha256": sha256(ROOT / ORIGINAL),
            "v24760_population_design_sha256": sha256(ROOT / POPULATION),
            "v24760_private_population_sha256": private_hash,
            "v24760_visible_contract_sha256": contract_hash,
            "v24761_inert_protocol_sha256": sha256(ROOT / OLD_PROTOCOL),
        },
        "correction": {
            "original_incorrect_field": INCORRECT_FIELD,
            "original_incorrect_value": diagnosis.get("failed_publication", {}).get(
                INCORRECT_FIELD
            ),
            "original_statement_valid": False,
            "v24758_population_design": {
                "immutable_ror_tree_https_reads_code_path_implied": TREE_READS_PER_REPLAY,
                "immutable_ror_record_https_reads_code_path_implied": RECORD_READS_PER_REPLAY,
                "direct_transport_receipt_persisted": False,
                "full_deterministic_tree_loop_completed_before_capacity_error": True,
                "model_calls": 0,
                "hosted_search_calls": 0,
                "benchmark_forward_calls": 0,
                "quality_or_evaluator_calls": 0,
            },
            "v24759_capacity_diagnosis": {
                "immutable_ror_tree_https_reads_code_path_implied": TREE_READS_PER_REPLAY,
                "immutable_ror_record_https_reads_code_path_implied": RECORD_READS_PER_REPLAY,
                "direct_transport_receipt_persisted": False,
                "diagnosis_artifact_published_after_full_replay": True,
                "model_calls": 0,
                "hosted_search_calls": 0,
                "benchmark_forward_calls": 0,
                "quality_or_evaluator_calls": 0,
            },
            "v24760_population_design": {
                "immutable_ror_tree_https_reads_published": TREE_READS_PER_REPLAY,
                "immutable_ror_record_https_reads_published": RECORD_READS_PER_REPLAY,
                "model_search_benchmark_or_evaluator_calls_published": 0,
            },
            "capacity_counts_or_minimum_cap_changed": False,
            "benchmark_label_mapping_gold_score_or_prediction_read": False,
            "credential_read_or_emitted": False,
        },
        "recertification": {
            "v24758_failed_surfaces_remain_pristine": failed_pristine,
            "v24761_activation_execution_result_and_output_surfaces_pristine": old_future_pristine,
            "v24760_public_seal_valid": _sealed(population, "design_payload_sha256"),
            "v24760_private_file_hash_matches_public_design": population.get(
                "private_population_file_sha256"
            )
            == private_hash,
            "v24760_visible_contract_hash_matches_public_design": population.get(
                "visible_contract_sha256"
            )
            == contract_hash,
            "v24760_population_recertified_under_corrected_provenance": population_recertified,
            "v24760_private_population_bytes_hashed_for_integrity": True,
            "v24760_private_population_semantics_parsed_by_correction": False,
        },
        "supersession": {
            "v24759_original_artifact_deleted_or_rewritten": False,
            "v24759_original_successor_authorization_valid": False,
            "v24760_population_files_deleted_or_regenerated": False,
            "v24761_protocol_was_inert_and_never_activated": old_future_pristine,
            "v24761_protocol_authorizes_successor_use": False,
            "replacement_inert_protocol_required": True,
        },
        "source_policy": {
            "network_called_by_correction": False,
            "model_hosted_search_benchmark_forward_quality_or_evaluator_called_by_correction": False,
            "benchmark_manifest_mapping_gold_category_question_type_split_score_reward_read": False,
            "private_population_semantics_read": False,
            "private_population_bytes_hashed_for_integrity": True,
            "credential_read_hashed_persisted_or_emitted": False,
        },
        "authorization": {
            "replacement_v24763_inert_protocol_publication": population_recertified,
            "runner_or_control_plane_build": False,
            "preactivation_audit": False,
            "activation_or_external_launch": False,
            "quality_surface_open": False,
            "paired_dev64": False,
            "exact220": False,
            "entropy_or_credit_experiment": False,
            "leaderboard_or_sota": False,
        },
    }
    value["correction_payload_sha256"] = payload_sha256(value)
    return validate_correction(value)


def validate_correction(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("correction_payload_sha256", None)
    correction = copied.get("correction", {})
    recertification = copied.get("recertification", {})
    supersession = copied.get("supersession", {})
    source_policy = copied.get("source_policy", {})
    if (
        copied.get("role") != "v24762_v24759_source_provenance_correction"
        or correction.get("original_incorrect_field") != INCORRECT_FIELD
        or correction.get("original_incorrect_value") is not False
        or correction.get("original_statement_valid") is not False
        or correction.get("v24758_population_design")
        != {
            "immutable_ror_tree_https_reads_code_path_implied": 1,
            "immutable_ror_record_https_reads_code_path_implied": 3_482,
            "direct_transport_receipt_persisted": False,
            "full_deterministic_tree_loop_completed_before_capacity_error": True,
            "model_calls": 0,
            "hosted_search_calls": 0,
            "benchmark_forward_calls": 0,
            "quality_or_evaluator_calls": 0,
        }
        or correction.get("v24759_capacity_diagnosis")
        != {
            "immutable_ror_tree_https_reads_code_path_implied": 1,
            "immutable_ror_record_https_reads_code_path_implied": 3_482,
            "direct_transport_receipt_persisted": False,
            "diagnosis_artifact_published_after_full_replay": True,
            "model_calls": 0,
            "hosted_search_calls": 0,
            "benchmark_forward_calls": 0,
            "quality_or_evaluator_calls": 0,
        }
        or correction.get("v24760_population_design")
        != {
            "immutable_ror_tree_https_reads_published": 1,
            "immutable_ror_record_https_reads_published": 3_482,
            "model_search_benchmark_or_evaluator_calls_published": 0,
        }
        or correction.get("capacity_counts_or_minimum_cap_changed") is not False
        or correction.get("benchmark_label_mapping_gold_score_or_prediction_read")
        is not False
        or correction.get("credential_read_or_emitted") is not False
        or recertification
        != {
            "v24758_failed_surfaces_remain_pristine": True,
            "v24761_activation_execution_result_and_output_surfaces_pristine": True,
            "v24760_public_seal_valid": True,
            "v24760_private_file_hash_matches_public_design": True,
            "v24760_visible_contract_hash_matches_public_design": True,
            "v24760_population_recertified_under_corrected_provenance": True,
            "v24760_private_population_bytes_hashed_for_integrity": True,
            "v24760_private_population_semantics_parsed_by_correction": False,
        }
        or supersession
        != {
            "v24759_original_artifact_deleted_or_rewritten": False,
            "v24759_original_successor_authorization_valid": False,
            "v24760_population_files_deleted_or_regenerated": False,
            "v24761_protocol_was_inert_and_never_activated": True,
            "v24761_protocol_authorizes_successor_use": False,
            "replacement_inert_protocol_required": True,
        }
        or source_policy
        != {
            "network_called_by_correction": False,
            "model_hosted_search_benchmark_forward_quality_or_evaluator_called_by_correction": False,
            "benchmark_manifest_mapping_gold_category_question_type_split_score_reward_read": False,
            "private_population_semantics_read": False,
            "private_population_bytes_hashed_for_integrity": True,
            "credential_read_hashed_persisted_or_emitted": False,
        }
        or copied.get("authorization")
        != {
            "replacement_v24763_inert_protocol_publication": True,
            "runner_or_control_plane_build": False,
            "preactivation_audit": False,
            "activation_or_external_launch": False,
            "quality_surface_open": False,
            "paired_dev64": False,
            "exact220": False,
            "entropy_or_credit_experiment": False,
            "leaderboard_or_sota": False,
        }
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.47.62 provenance correction drifted")
    return copied


def _publish(path: Path, value: Mapping[str, Any]) -> None:
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


def main() -> None:
    correction = build_correction()
    _publish(ROOT / OUTPUT, correction)
    print(
        json.dumps(
            {
                "old_protocol_superseded": not correction["supersession"][
                    "v24761_protocol_authorizes_successor_use"
                ],
                "output": str(OUTPUT),
                "replacement_protocol_authorized": correction["authorization"][
                    "replacement_v24763_inert_protocol_publication"
                ],
                "v24760_population_recertified": correction["recertification"][
                    "v24760_population_recertified_under_corrected_provenance"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
