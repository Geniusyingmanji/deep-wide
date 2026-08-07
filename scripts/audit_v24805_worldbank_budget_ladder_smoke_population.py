#!/usr/bin/env python3
"""Build-only publication audit for the V2.48.05 smoke population."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import (  # noqa: E402
    design_v24805_worldbank_budget_ladder_smoke_population as design,
)
from scripts.audit_v24804_shared_prefix_budget_ladder import (  # noqa: E402
    SECRET,
    payload_sha256,
)


OUTPUT = design.AUTHORIZATION
SOURCES = (
    design.PARENT,
    *design.HISTORICAL_PRIVATE,
    Path("scripts/design_v24805_worldbank_budget_ladder_smoke_population.py"),
    Path("tests/test_design_v24805_worldbank_budget_ladder_smoke_population.py"),
    Path("scripts/audit_v24805_worldbank_budget_ladder_smoke_population.py"),
    Path("tests/test_audit_v24805_worldbank_budget_ladder_smoke_population.py"),
)
EXPECTED_TESTS = 5


def _ordinary(relative: Path) -> Path:
    path = ROOT / relative
    if (
        relative.is_absolute() or ".." in relative.parts or path.is_symlink()
        or not path.is_file() or not path.resolve().is_relative_to(ROOT.resolve())
    ):
        raise RuntimeError(f"V2.48.05 expected repository file: {relative}")
    return path


def _sha256(relative: Path) -> str:
    return hashlib.sha256(_ordinary(relative).read_bytes()).hexdigest()


def _read(relative: Path) -> dict[str, Any]:
    value = json.loads(_ordinary(relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.48.05 audit expected object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def _parent_valid() -> bool:
    value = _read(design.PARENT)
    return (
        value.get("role") == "v24804_shared_prefix_budget_ladder_build_audit"
        and value.get("audit_valid") is True and value.get("findings") == []
        and value.get("authorization", {}).get(
            "fresh_benchmark_external_population_and_protocol_design"
        ) is True
        and value.get("authorization", {}).get("external_launch") is False
        and _sealed(value, "audit_payload_sha256")
    )


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=20,
    ).stdout.strip()


def _watcher_snapshot() -> list[dict[str, Any]]:
    from scripts.audit_v24804_shared_prefix_budget_ladder import _watchers

    return _watchers()


def _lease_inactive() -> bool:
    from scripts.audit_v24804_shared_prefix_budget_ladder import _lease_inactive

    return _lease_inactive()


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    before = _watcher_snapshot()
    completed = subprocess.run(
        [
            str(ROOT / ".venv-eval/bin/python"), "-I", "-B",
            str(ROOT / "tests/test_design_v24805_worldbank_budget_ladder_smoke_population.py"),
            "-v",
        ],
        cwd=ROOT,
        env={
            "HOME": os.environ.get("HOME", str(Path.home())),
            "USER": os.environ.get("USER", "azureuser"),
            "LOGNAME": os.environ.get("LOGNAME", "azureuser"),
            "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
            "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1",
            "PYTHONSAFEPATH": "1",
        },
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, timeout=60, check=False,
    )
    after = _watcher_snapshot()
    observed = completed.stdout.count(" ... ok")
    source_text = "\n".join(
        _ordinary(path).read_text(encoding="utf-8") for path in SOURCES
    )
    source = _ordinary(
        Path("scripts/design_v24805_worldbank_budget_ladder_smoke_population.py")
    ).read_text(encoding="utf-8")
    implementation = {
        "selected_country_count": design.SELECTED_COUNT,
        "task_count": design.TASK_COUNT,
        "task_size": design.TASK_SIZE,
        "stratum_vector": list(design.STRATUM_VECTOR),
        "complete_selected": design.COMPLETE_SELECTED,
        "missing_selected": design.MISSING_SELECTED,
        "historical_artifact_count": len(design.HISTORICAL_PRIVATE),
        "target_vector": [dict(target) for target in design.TARGETS],
        "smoke_not_main_sample": design.TASK_COUNT < 128,
        "authorization_check_precedes_network": source.index(
            "if not _authorized()"
        ) < source.index("catalog_raw = _fetch_bytes"),
    }
    checks = {
        "parent_authority_valid": _parent_valid(),
        "focused_tests_passed": completed.returncode == 0
        and observed == EXPECTED_TESTS,
        "implementation_contract_valid": implementation == {
            "selected_country_count": 64,
            "task_count": 16,
            "task_size": 4,
            "stratum_vector": [
                *("complete" for _ in range(10)),
                *("missing" for _ in range(4)),
                "mixed", "mixed",
            ],
            "complete_selected": 44,
            "missing_selected": 20,
            "historical_artifact_count": 4,
            "target_vector": [
                {
                    "label": "Male unemployment rate (%)",
                    "indicator": "SL.UEM.TOTL.MA.ZS",
                    "year": "2023",
                },
                {
                    "label": "Female unemployment rate (%)",
                    "indicator": "SL.UEM.TOTL.FE.ZS",
                    "year": "2023",
                },
            ],
            "smoke_not_main_sample": True,
            "authorization_check_precedes_network": True,
        },
        "historical_exclusion_count_96": len(design.historical_iso3(ROOT)[0])
        == 96,
        "credential_literal_absent": SECRET.search(source_text) is None,
        "future_population_surfaces_pristine": all(
            not (ROOT / path).exists() and not (ROOT / path).is_symlink()
            for path in (design.PRIVATE, design.OUTPUT)
        ),
        "protected_watchers_unchanged": before == after,
        "shared_api_lease_inactive": _lease_inactive(),
    }
    value = {
        "artifact_version": 1,
        "role": "v24805_worldbank_budget_ladder_smoke_population_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "base_commit": _git("rev-parse", "HEAD"),
        "parent_sha256": _sha256(design.PARENT),
        "source_manifest": {str(path): _sha256(path) for path in SOURCES},
        "focused_test_count": observed,
        "implementation": implementation,
        "checks": checks,
        "findings": sorted(name for name, passed in checks.items() if not passed),
        "effect_boundary": {
            "network_model_search_fetch_benchmark_or_evaluator_called": False,
            "private_gold_value_used_for_routing": False,
            "population_consumed": False,
        },
        "authorization": {
            "one_smoke_population_publication": all(checks.values()),
            "smoke_protocol_design": False,
            "smoke_launch": False,
            "main_calibration_or_confirmatory_launch": False,
            "public_dev64_or_exact220": False,
            "evaluator_access": False,
        },
    }
    value["audit_valid"] = not value["findings"]
    value["audit_payload_sha256"] = payload_sha256(value)
    return validate_audit(value)


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    unsigned = dict(copied)
    seal = unsigned.pop("audit_payload_sha256", None)
    if (
        copied.get("role")
        != "v24805_worldbank_budget_ladder_smoke_population_build_audit"
        or copied.get("audit_valid") is not True or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or copied.get("authorization") != {
            "one_smoke_population_publication": True,
            "smoke_protocol_design": False, "smoke_launch": False,
            "main_calibration_or_confirmatory_launch": False,
            "public_dev64_or_exact220": False, "evaluator_access": False,
        }
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.48.05 population build audit drifted")
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


if __name__ == "__main__":
    audit = build_audit()
    publish(ROOT / OUTPUT, audit)
    print(json.dumps({
        "output": str(OUTPUT), "audit_valid": audit["audit_valid"],
        "focused_test_count": audit["focused_test_count"],
        "authorization": audit["authorization"],
    }, sort_keys=True))
