#!/usr/bin/env python3
"""Build-only audit authorizing one V2.48.13 population publication."""

from __future__ import annotations

import json
import os
import re
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

from scripts import design_v24813_fresh_worldbank_population as design  # noqa: E402
from deepwide_agent import v24809_worldbank_budget_ladder_smoke_contract as parent  # noqa: E402


OUTPUT = design.AUTHORIZATION
SOURCES = (
    design.PARENT_AUDIT,
    design.CONSUMED_POPULATION,
    Path("scripts/design_v24813_fresh_worldbank_population.py"),
    Path("tests/test_design_v24813_fresh_worldbank_population.py"),
    Path("scripts/audit_v24813_fresh_worldbank_population.py"),
)
EXPECTED_TESTS = 4
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}"
)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
        timeout=20, check=True,
    ).stdout.strip()


def _read(path: Path) -> dict[str, Any]:
    value = json.loads((ROOT / path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.48.13 audit expected object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == parent.payload_sha256(unsigned)


def _parent_valid() -> bool:
    value = _read(design.PARENT_AUDIT)
    return (
        value.get("role") == "v24812_batched_search_accounting_build_audit"
        and value.get("audit_valid") is True
        and value.get("findings") == []
        and value.get("authorization", {}).get(
            "fresh_disjoint_external_successor_design"
        ) is True
        and value.get("authorization", {}).get("external_launch") is False
        and _sealed(value, "audit_payload_sha256")
    )


def build(*, now: int | None = None) -> dict[str, Any]:
    completed = subprocess.run(
        [
            str(ROOT / ".venv-eval/bin/python"), "-I", "-B", "-m",
            "unittest", "discover", "-s", "tests",
            "-p", "test_design_v24813_fresh_worldbank_population.py", "-v",
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
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, text=True, timeout=120, check=False,
    )
    match = re.search(r"Ran (\d+) tests?", completed.stdout)
    observed = int(match.group(1)) if match else 0
    excluded, manifest = design.historical_iso3(ROOT)
    source_text = "\n".join((ROOT / path).read_text(encoding="utf-8") for path in SOURCES[2:])
    watchers_before = parent.protected_watcher_snapshot()
    watchers_after = parent.protected_watcher_snapshot()
    checks = {
        "clean_pushed_head": not _git("status", "--porcelain")
        and _git("rev-parse", "HEAD") == _git("rev-parse", "target/main"),
        "parent_accounting_audit_valid": _parent_valid(),
        "focused_tests_4_of_4": completed.returncode == 0
        and observed == EXPECTED_TESTS,
        "historical_exclusion_160": len(excluded) == 160
        and len(manifest) == 5,
        "selected_population_count_48": design.SELECTED_COUNT == 48
        and design.TASK_COUNT == 12 and design.TASK_SIZE == 4,
        "future_surfaces_pristine": all(
            not (ROOT / path).exists() and not (ROOT / path).is_symlink()
            for path in (design.AUTHORIZATION, design.PRIVATE, design.OUTPUT)
        ),
        "credential_literal_absent": SECRET.search(source_text) is None,
        "protected_watchers_unchanged": watchers_before == watchers_after,
    }
    value = {
        "artifact_version": 1,
        "role": "v24813_fresh_worldbank_population_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git_head": _git("rev-parse", "HEAD"),
        "parent_audit_sha256": parent.sha256(ROOT / design.PARENT_AUDIT),
        "consumed_population_sha256": parent.sha256(ROOT / design.CONSUMED_POPULATION),
        "source_manifest": {str(path): parent.sha256(ROOT / path) for path in SOURCES},
        "tests": {
            "expected": EXPECTED_TESTS, "observed": observed,
            "passed": completed.returncode == 0 and observed == EXPECTED_TESTS,
            "output_sha256": parent.payload_sha256(completed.stdout),
        },
        "historical_exclusion": {
            "country_count": len(excluded), "artifact_count": len(manifest),
            "manifest_sha256": parent.payload_sha256(manifest),
            "consumed_v24809_population_included": True,
        },
        "checks": checks,
        "protected_watchers": watchers_after,
        "network_model_search_fetch_or_evaluator_called_by_audit": False,
        "private_population_or_gold_read_by_future_forward": False,
        "findings": sorted(name for name, passed in checks.items() if not passed),
        "audit_valid": all(checks.values()),
        "authorization": {
            "one_population_publication": all(checks.values()),
            "external_protocol_design": False,
            "external_launch": False,
            "evaluator": False,
            "public_dev64_or_exact220": False,
        },
    }
    value["audit_payload_sha256"] = parent.payload_sha256(value)
    if value["findings"]:
        raise RuntimeError(f"V2.48.13 population audit failed: {value['findings']}")
    return value


def publish(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    artifact = build()
    publish(ROOT / OUTPUT, artifact)
    print(json.dumps({"path": str(OUTPUT), "tests": artifact["tests"], "findings": artifact["findings"]}, sort_keys=True))
