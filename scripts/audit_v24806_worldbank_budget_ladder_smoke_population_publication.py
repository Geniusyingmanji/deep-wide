#!/usr/bin/env python3
"""Cross-artifact audit of the published V2.48.06 smoke population."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import (  # noqa: E402
    audit_v24806_worldbank_budget_ladder_smoke_population as authority,
)
from scripts import (  # noqa: E402
    design_v24806_worldbank_budget_ladder_smoke_population as design,
)
from scripts.audit_v24804_shared_prefix_budget_ladder import payload_sha256  # noqa: E402


OUTPUT = Path(
    "results/v24806_worldbank_budget_ladder_smoke_population_publication_audit_v1_20260807.json"
)


def _ordinary(relative: Path) -> Path:
    path = ROOT / relative
    if (
        relative.is_absolute() or ".." in relative.parts or path.is_symlink()
        or not path.is_file() or not path.resolve().is_relative_to(ROOT.resolve())
    ):
        raise RuntimeError(f"V2.48.06 publication audit expected file: {relative}")
    return path


def _read(relative: Path) -> dict[str, Any]:
    value = json.loads(_ordinary(relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.48.06 publication audit expected object")
    return value


def _sha256(relative: Path) -> str:
    return hashlib.sha256(_ordinary(relative).read_bytes()).hexdigest()


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def _leaf_strings(value: object) -> set[str]:
    output: set[str] = set()
    if isinstance(value, Mapping):
        for nested in value.values():
            output.update(_leaf_strings(nested))
    elif isinstance(value, list):
        for nested in value:
            output.update(_leaf_strings(nested))
    elif isinstance(value, str):
        output.add(value)
    return output


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    private = _read(design.PRIVATE)
    public = _read(design.OUTPUT)
    build = _read(design.AUTHORIZATION)
    authority.validate_audit(build)
    groups = private.get("groups") or []
    flat = [item for group in groups for item in group] if isinstance(groups, list) else []
    identities = {
        str(item.get("iso3")) for item in flat if isinstance(item, Mapping)
    }
    forbidden = {
        str(value)
        for item in flat
        if isinstance(item, Mapping)
        for value in (item.get("iso3"), item.get("name"))
        if isinstance(value, str) and value
    }
    for item in flat:
        if isinstance(item, Mapping):
            for record in item.get("records") or []:
                if isinstance(record, Mapping) and record.get("value") is not None:
                    forbidden.add(str(record["value"]))
    strata = tuple(private.get("task_stratum_vector") or [])
    checks = {
        "build_authority_valid": True,
        "private_seal_valid": _sealed(private, "private_payload_sha256"),
        "public_seal_valid": _sealed(public, "design_payload_sha256"),
        "public_binds_private_exact_bytes": public.get("private_population_file_sha256")
        == _sha256(design.PRIVATE),
        "public_binds_authority": public.get("authorization_audit_sha256")
        == _sha256(design.AUTHORIZATION),
        "public_binds_failure_audit": public.get(
            "predecessor_zero_effect_failure_audit_sha256"
        ) == _sha256(design.FAILURE_AUDIT),
        "task_and_country_denominator_exact": (
            len(groups) == 16
            and all(isinstance(group, list) and len(group) == 4 for group in groups)
            and len(flat) == len(identities) == 64
        ),
        "stratum_vector_exact": (
            len(strata) == 16
            and Counter(strata) == Counter({"complete": 10, "missing": 4, "mixed": 2})
            and public.get("task_stratum_counts")
            == {"complete": 10, "missing": 4, "mixed": 2}
        ),
        "historical_exclusion_exact": public.get("historical_excluded_iso3_count") == 96,
        "public_leaf_values_exclude_identity_and_gold": not (
            forbidden & _leaf_strings(public)
        ),
        "public_authorizes_design_only": public.get("authorization") == {
            "isolated_smoke_forward_contract_and_evaluator_design": True,
            "smoke_protocol_design": True,
            "smoke_launch": False,
            "main_calibration_or_confirmatory_launch": False,
            "public_dev64_or_exact220": False,
            "evaluator_access": False,
        },
        "private_forbids_forward_import_and_early_evaluator": (
            private.get("forward_import_or_runtime_read_authorized") is False
            and private.get(
                "gold_provenance_or_evaluator_read_before_prediction_freeze_authorized"
            ) is False
        ),
        "publication_network_scope_exact": public.get("network") == {
            "worldbank_country_catalog_reads": 1,
            "worldbank_bulk_indicator_reads": 2,
            "model_search_benchmark_or_evaluator_calls": 0,
        },
    }
    value = {
        "artifact_version": 1,
        "role": "v24806_worldbank_budget_ladder_smoke_population_publication_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "private_population_sha256": _sha256(design.PRIVATE),
        "public_design_sha256": _sha256(design.OUTPUT),
        "build_authority_sha256": _sha256(design.AUTHORIZATION),
        "predecessor_failure_audit_sha256": _sha256(design.FAILURE_AUDIT),
        "counts": {
            "tasks": len(groups),
            "countries": len(flat),
            "unique_country_iso3": len(identities),
            "strata": dict(sorted(Counter(strata).items())),
        },
        "checks": checks,
        "findings": sorted(name for name, passed in checks.items() if not passed),
        "audit_valid": all(checks.values()),
        "effect_boundary": {
            "publication_effects_complete": True,
            "worldbank_public_reads": 3,
            "model_search_benchmark_or_evaluator_calls": 0,
            "forward_or_prediction_effect_started": False,
            "private_population_opened_by_runtime": False,
        },
        "authorization": {
            "isolated_smoke_protocol_design": all(checks.values()),
            "smoke_launch": False,
            "evaluator_access": False,
            "main_calibration_lock_validation_or_confirmatory_launch": False,
            "public_dev64_or_exact220": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return validate_audit(value)


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    unsigned = dict(copied)
    seal = unsigned.pop("audit_payload_sha256", None)
    if (
        copied.get("role")
        != "v24806_worldbank_budget_ladder_smoke_population_publication_audit"
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or copied.get("authorization") != {
            "isolated_smoke_protocol_design": True,
            "smoke_launch": False,
            "evaluator_access": False,
            "main_calibration_lock_validation_or_confirmatory_launch": False,
            "public_dev64_or_exact220": False,
        }
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.48.06 publication audit drifted")
    return copied


def publish(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    audit = build_audit()
    publish(ROOT / OUTPUT, audit)
    print(json.dumps({
        "path": str(OUTPUT), "audit_valid": audit["audit_valid"],
        "counts": audit["counts"], "authorization": audit["authorization"],
    }, sort_keys=True))
