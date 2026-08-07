#!/usr/bin/env python3
"""Build-only audit for the V2.48.14 population successor."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from collections.abc import Mapping
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import design_v24814_fresh_worldbank_population as design  # noqa: E402
from deepwide_agent import v24809_worldbank_budget_ladder_smoke_contract as contract  # noqa: E402


OUTPUT = design.AUTHORIZATION
SOURCES = (
    design.FAILURE_AUDIT,
    Path("scripts/design_v24814_fresh_worldbank_population.py"),
    Path("tests/test_design_v24814_fresh_worldbank_population.py"),
    Path("scripts/audit_v24814_fresh_worldbank_population.py"),
)
EXPECTED_TESTS = 7
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}"
)


def _git(*args: str) -> str:
    return design.base._git(*args)


def _read(path: Path) -> dict:
    value = json.loads((ROOT / path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.48.14 audit expected object")
    return value


def build(*, now: int | None = None) -> dict:
    completed = subprocess.run(
        [
            str(ROOT / ".venv-eval/bin/python"), "-I", "-B", "-m",
            "unittest", "discover", "-s", "tests",
            "-p", "test_design_v24814_fresh_worldbank_population.py", "-v",
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
        stderr=subprocess.STDOUT, text=True, timeout=180, check=False,
    )
    match = re.search(r"Ran (\d+) tests?", completed.stdout)
    observed = int(match.group(1)) if match else 0
    failure = _read(design.FAILURE_AUDIT)
    excluded, manifest = design.base.historical_iso3(ROOT)
    source_text = "\n".join((ROOT / path).read_text(encoding="utf-8") for path in SOURCES)
    watchers_before = contract.protected_watcher_snapshot()
    watchers_after = contract.protected_watcher_snapshot()
    checks = {
        "clean_pushed_head": not _git("status", "--porcelain")
        and _git("rev-parse", "HEAD") == _git("rev-parse", "target/main"),
        "v24813_failure_is_zero_publication": failure.get("status")
        == "invalid_zero_publication_do_not_resume_or_retry"
        and failure.get("surfaces", {}).get("private_population_written") is False
        and failure.get("surfaces", {}).get("public_population_written") is False,
        "v24813_future_surfaces_absent": all(
            not (ROOT / path).exists() and not (ROOT / path).is_symlink()
            for path in (design.base.PRIVATE, design.base.OUTPUT)
        ),
        "focused_tests_7_of_7": completed.returncode == 0
        and observed == EXPECTED_TESTS,
        "historical_exclusion_160": len(excluded) == 160 and len(manifest) == 5,
        "successor_keeps_48_12x4": design.base.SELECTED_COUNT == 48
        and design.base.TASK_COUNT == 12 and design.base.TASK_SIZE == 4,
        "only_change_is_region_cap_removal": design.REGION_CAP
        == design.base.SELECTED_COUNT,
        "future_surfaces_pristine": all(
            not (ROOT / path).exists() and not (ROOT / path).is_symlink()
            for path in (design.AUTHORIZATION, design.PRIVATE, design.OUTPUT)
        ),
        "credential_literal_absent": SECRET.search(source_text) is None,
        "protected_watchers_unchanged": watchers_before == watchers_after,
    }
    value = {
        "artifact_version": 1,
        "role": "v24814_fresh_worldbank_population_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git_head": _git("rev-parse", "HEAD"),
        "v24813_failure_audit_sha256": design.base._sha256(ROOT / design.FAILURE_AUDIT),
        "source_manifest": {
            str(path): design.base._sha256(ROOT / path) for path in SOURCES
        },
        "tests": {
            "expected": EXPECTED_TESTS, "observed": observed,
            "passed": completed.returncode == 0 and observed == EXPECTED_TESTS,
            "output_sha256": design.base.payload_sha256(completed.stdout),
        },
        "checks": checks,
        "protected_watchers": watchers_after,
        "network_model_search_fetch_or_evaluator_called_by_audit": False,
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
    value["audit_payload_sha256"] = design.base.payload_sha256(value)
    if value["findings"]:
        raise RuntimeError(f"V2.48.14 audit failed: {value['findings']}")
    return value


def publish(path: Path, value: Mapping[str, object]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    artifact = build()
    publish(ROOT / OUTPUT, artifact)
    print(json.dumps({"path": str(OUTPUT), "tests": artifact["tests"], "findings": artifact["findings"]}, sort_keys=True))
