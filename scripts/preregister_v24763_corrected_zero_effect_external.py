#!/usr/bin/env python3
"""Publish the corrected inert V2.47.63 zero-effect external protocol.

The task vector, runtime envelope, mechanism gate, quality gate, and entropy
scope are byte-semantic copies of the never-activated V2.47.61 protocol.  The
only protocol-level change is provenance and authority: V2.47.62 is now the
required parent, immutable ROR source reads are acknowledged, V2.47.61 is
superseded, and runner/control-plane construction is not authorized.
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
from scripts import correct_v24762_v24759_source_provenance as correction  # noqa: E402
from scripts import preregister_v24761_zero_effect_external as predecessor  # noqa: E402


DATE = "20260806"
PROTOCOL_ID = "v24763_corrected_zero_effect_natural_structured_external_v1"
OUTPUT = Path(
    f"results/v24763_corrected_zero_effect_external_preregistration_v1_{DATE}.json"
)
CORRECTION = correction.OUTPUT
POPULATION = predecessor.POPULATION
BUILD_AUDIT = predecessor.BUILD_AUDIT
OLD_PROTOCOL = predecessor.OUTPUT
FUTURE_SURFACES = (
    Path(f"results/v24763_zero_effect_external_package_audit_v1_{DATE}.json"),
    Path(f"results/v24763_zero_effect_external_preactivation_audit_v1_{DATE}.json"),
    Path(f"results/v24763_zero_effect_external_activation_v1_{DATE}.json"),
    Path(f"results/v24763_zero_effect_external_execution_start_v1_{DATE}.json"),
    Path(f"results/v24763_zero_effect_external_forward_result_v1_{DATE}.json"),
    Path(f"results/v24763_zero_effect_external_forward_audit_v1_{DATE}.json"),
    Path(f"results/v24763_zero_effect_external_quality_preregistration_v1_{DATE}.json"),
    Path(f"results/v24763_zero_effect_external_quality_result_v1_{DATE}.json"),
    Path(f"results/v24763_zero_effect_external_postresult_audit_v1_{DATE}.json"),
    Path(f"outputs/v24763_zero_effect_external_v1_{DATE}"),
)
DEPENDENCIES = (
    Path("src/deepwide_agent/clients.py"),
    Path("src/deepwide_agent/native_search.py"),
    Path("src/deepwide_agent/v24257_score_first_runtime.py"),
    Path("src/deepwide_agent/v24259_deterministic_table_normalizer.py"),
    Path("src/deepwide_agent/v24269_task_union_discovery.py"),
    Path("src/deepwide_agent/v24286_visible_schema_runtime.py"),
    Path("src/deepwide_agent/v24308_child_exit_observability.py"),
    Path("src/deepwide_agent/v24325_shared_prefix_revision_runtime.py"),
    Path("src/deepwide_agent/v24743_generic_record_binding.py"),
    Path("src/deepwide_agent/v24754_generic_structured_page_adapter.py"),
    Path("src/deepwide_agent/v24756_zero_effect_structured_integration.py"),
    Path("src/deepwide_agent/v24760_zero_effect_external_contract.py"),
    Path("tests/test_v24743_generic_record_binding.py"),
    Path("tests/test_v24754_generic_structured_page_adapter.py"),
    Path("tests/test_v24756_zero_effect_structured_integration.py"),
    Path("scripts/correct_v24762_v24759_source_provenance.py"),
    Path("tests/test_correct_v24762_v24759_source_provenance.py"),
    Path("scripts/preregister_v24761_zero_effect_external.py"),
    Path("tests/test_preregister_v24761_zero_effect_external.py"),
    Path("scripts/preregister_v24763_corrected_zero_effect_external.py"),
    Path("tests/test_preregister_v24763_corrected_zero_effect_external.py"),
    BUILD_AUDIT,
    CORRECTION,
    POPULATION,
    OLD_PROTOCOL,
)
FORBIDDEN_DEPENDENCY_MARKERS = predecessor.FORBIDDEN_DEPENDENCY_MARKERS


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
        raise RuntimeError("V2.47.63 expected ordinary JSON object")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.47.63 expected JSON object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def _tracked_ordinary(relative: Path) -> Path:
    path = ROOT / relative
    tracked = subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(relative)],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=20,
        check=False,
    ).returncode == 0
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(ROOT.resolve())
        or not tracked
    ):
        raise RuntimeError(f"V2.47.63 expected tracked dependency: {relative}")
    return path


def dependency_manifest() -> dict[str, str]:
    output: dict[str, str] = {}
    for relative in DEPENDENCIES:
        folded = str(relative).casefold()
        if any(marker in folded for marker in FORBIDDEN_DEPENDENCY_MARKERS):
            raise RuntimeError("V2.47.63 evaluator/private dependency entered manifest")
        output[str(relative)] = sha256(_tracked_ordinary(relative))
    return output


def _parents() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    corrected = _read(ROOT / CORRECTION)
    population = _read(ROOT / POPULATION)
    old = _read(ROOT / OLD_PROTOCOL)
    if (
        correction.validate_correction(corrected) != corrected
        or corrected.get("authorization", {}).get(
            "replacement_v24763_inert_protocol_publication"
        )
        is not True
        or corrected.get("authorization", {}).get(
            "activation_or_external_launch"
        )
        is not False
        or corrected.get("recertification", {}).get(
            "v24760_population_recertified_under_corrected_provenance"
        )
        is not True
        or corrected.get("supersession", {}).get(
            "v24761_protocol_authorizes_successor_use"
        )
        is not False
        or population.get("role") != "v24760_zero_effect_population_design"
        or population.get("freshness", {}).get("selected_entity_count") != 32
        or population.get("freshness", {}).get("canonical_overlap_with_history")
        != 0
        or population.get("network")
        != {
            "immutable_ror_tree_reads": 1,
            "immutable_ror_record_reads": 3_482,
            "model_search_benchmark_or_evaluator_calls": 0,
        }
        or population.get("authorization", {}).get(
            "activation_or_external_launch"
        )
        is not False
        or not _sealed(population, "design_payload_sha256")
        or predecessor.validate_protocol(old) != old
        or old.get("authorization", {}).get("one_external_forward_launch")
        is not False
    ):
        raise RuntimeError("V2.47.63 corrected parent chain drifted")
    return corrected, population, old


def build_protocol(
    *, now: int | None = None, require_clean: bool = True, require_pristine: bool = True
) -> dict[str, Any]:
    if require_clean and (
        _git("status", "--porcelain")
        or _git("rev-parse", "HEAD") != _git("rev-parse", "target/main")
    ):
        raise RuntimeError("V2.47.63 publication requires clean pushed HEAD")
    if require_pristine and (
        (ROOT / OUTPUT).exists()
        or (ROOT / OUTPUT).is_symlink()
        or any((ROOT / path).exists() or (ROOT / path).is_symlink() for path in FUTURE_SURFACES)
    ):
        raise RuntimeError("V2.47.63 protocol/future surface is not pristine")
    corrected, population, old = _parents()
    manifest = dependency_manifest()
    value = copy.deepcopy(old)
    value.pop("protocol_payload_sha256", None)
    value["role"] = "v24763_corrected_zero_effect_external_preregistration"
    value["protocol_id"] = PROTOCOL_ID
    value["created_at_unix"] = int(time.time()) if now is None else int(now)
    value["git_head"] = _git("rev-parse", "HEAD")
    value["parents"] = {
        "v24757_integration_build_audit_sha256": sha256(ROOT / BUILD_AUDIT),
        "v24760_population_design_sha256": sha256(ROOT / POPULATION),
        "v24761_superseded_inert_protocol_sha256": sha256(ROOT / OLD_PROTOCOL),
        "v24762_source_provenance_correction_sha256": sha256(ROOT / CORRECTION),
        "v24760_population_recertified": corrected.get("recertification", {}).get(
            "v24760_population_recertified_under_corrected_provenance"
        )
        is True,
        "v24761_never_activated": corrected.get("supersession", {}).get(
            "v24761_protocol_was_inert_and_never_activated"
        )
        is True,
        "v24761_authorizes_successor_use": False,
    }
    value["dependency_manifest"] = manifest
    value["dependency_manifest_sha256"] = payload_sha256(manifest)
    value["provenance_correction"] = {
        "v24758_immutable_ror_tree_https_reads_code_path_implied": 1,
        "v24758_immutable_ror_record_https_reads_code_path_implied": 3_482,
        "v24759_immutable_ror_tree_https_reads_code_path_implied": 1,
        "v24759_immutable_ror_record_https_reads_code_path_implied": 3_482,
        "v24760_immutable_ror_tree_https_reads_published": population.get(
            "network", {}
        ).get("immutable_ror_tree_reads"),
        "v24760_immutable_ror_record_https_reads_published": population.get(
            "network", {}
        ).get("immutable_ror_record_reads"),
        "direct_v24758_or_v24759_transport_receipt_persisted": False,
        "model_hosted_search_benchmark_forward_quality_or_evaluator_calls": 0,
        "capacity_counts_or_population_bytes_changed_by_correction": False,
    }
    value["supersession"] = {
        "v24759_original_successor_authorization_valid": False,
        "v24761_protocol_authorizes_activation_or_successor_use": False,
        "v24761_protocol_or_artifact_deleted_or_rewritten": False,
        "v24763_is_only_current_inert_protocol": True,
    }
    value["source_policy"] = {
        "benchmark_manifest_mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
        "private_population_truth_provenance_or_quality_file_opened_or_hashed": False,
        "credential_read_hashed_persisted_or_emitted": False,
        "network_model_search_fetch_or_benchmark_forward_called_by_publication": False,
        "question_entity_url_page_prediction_or_answer_emitted": False,
        "historical_immutable_ror_source_reads_acknowledged": True,
    }
    value["authorization"] = {
        "corrected_protocol_published": True,
        "runner_or_control_plane_build": False,
        "package_audit_generation": False,
        "preactivation_audit_generation": False,
        "activation": False,
        "execution_start": False,
        "one_external_forward_launch": False,
        "quality_surface_open": False,
        "paired_dev64": False,
        "exact220": False,
        "entropy_or_credit_experiment": False,
        "leaderboard_or_sota": False,
    }
    value["protocol_payload_sha256"] = payload_sha256(value)
    return validate_protocol(value)


def validate_protocol(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("protocol_payload_sha256", None)
    manifest = copied.get("dependency_manifest")
    provenance = copied.get("provenance_correction")
    supersession = copied.get("supersession")
    if (
        copied.get("role")
        != "v24763_corrected_zero_effect_external_preregistration"
        or copied.get("protocol_id") != PROTOCOL_ID
        or not isinstance(manifest, Mapping)
        or dict(manifest) != dependency_manifest()
        or copied.get("dependency_manifest_sha256") != payload_sha256(manifest)
        or copied.get("task_contract", {}).get("runtime_input_keys")
        != ["opaque_id", "question"]
        or copied.get("task_contract", {}).get("task_count") != 8
        or copied.get("runtime")
        != _read(ROOT / OLD_PROTOCOL).get("runtime")
        or copied.get("forward_health_gate")
        != _read(ROOT / OLD_PROTOCOL).get("forward_health_gate")
        or copied.get("mechanism_gate_before_private_truth")
        != _read(ROOT / OLD_PROTOCOL).get("mechanism_gate_before_private_truth")
        or copied.get("quality_gate_after_prediction_freeze")
        != _read(ROOT / OLD_PROTOCOL).get("quality_gate_after_prediction_freeze")
        or copied.get("entropy_credit_scope")
        != _read(ROOT / OLD_PROTOCOL).get("entropy_credit_scope")
        or provenance
        != {
            "v24758_immutable_ror_tree_https_reads_code_path_implied": 1,
            "v24758_immutable_ror_record_https_reads_code_path_implied": 3_482,
            "v24759_immutable_ror_tree_https_reads_code_path_implied": 1,
            "v24759_immutable_ror_record_https_reads_code_path_implied": 3_482,
            "v24760_immutable_ror_tree_https_reads_published": 1,
            "v24760_immutable_ror_record_https_reads_published": 3_482,
            "direct_v24758_or_v24759_transport_receipt_persisted": False,
            "model_hosted_search_benchmark_forward_quality_or_evaluator_calls": 0,
            "capacity_counts_or_population_bytes_changed_by_correction": False,
        }
        or supersession
        != {
            "v24759_original_successor_authorization_valid": False,
            "v24761_protocol_authorizes_activation_or_successor_use": False,
            "v24761_protocol_or_artifact_deleted_or_rewritten": False,
            "v24763_is_only_current_inert_protocol": True,
        }
        or copied.get("source_policy")
        != {
            "benchmark_manifest_mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "private_population_truth_provenance_or_quality_file_opened_or_hashed": False,
            "credential_read_hashed_persisted_or_emitted": False,
            "network_model_search_fetch_or_benchmark_forward_called_by_publication": False,
            "question_entity_url_page_prediction_or_answer_emitted": False,
            "historical_immutable_ror_source_reads_acknowledged": True,
        }
        or copied.get("authorization")
        != {
            "corrected_protocol_published": True,
            "runner_or_control_plane_build": False,
            "package_audit_generation": False,
            "preactivation_audit_generation": False,
            "activation": False,
            "execution_start": False,
            "one_external_forward_launch": False,
            "quality_surface_open": False,
            "paired_dev64": False,
            "exact220": False,
            "entropy_or_credit_experiment": False,
            "leaderboard_or_sota": False,
        }
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.47.63 corrected protocol drifted")
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
    protocol = build_protocol()
    _publish(ROOT / OUTPUT, protocol)
    print(
        json.dumps(
            {
                "external_launch": protocol["authorization"][
                    "one_external_forward_launch"
                ],
                "output": str(OUTPUT),
                "protocol_id": PROTOCOL_ID,
                "runner_build": protocol["authorization"][
                    "runner_or_control_plane_build"
                ],
                "task_count": protocol["task_contract"]["task_count"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
