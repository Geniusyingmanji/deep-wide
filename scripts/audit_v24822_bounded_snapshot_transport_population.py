#!/usr/bin/env python3
"""Build audit authorizing one V2.48.22 population publication."""

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

from deepwide_agent import (  # noqa: E402
    v24809_worldbank_budget_ladder_smoke_contract as watcher_contract,
)
from scripts import (  # noqa: E402
    design_v24822_bounded_snapshot_transport_population as design,
)


OUTPUT = design.AUTHORIZATION
TEST = Path("tests/test_design_v24822_bounded_snapshot_transport_population.py")
SOURCES = (
    Path("scripts/design_v24822_bounded_snapshot_transport_population.py"),
    TEST,
    Path("scripts/audit_v24822_bounded_snapshot_transport_population.py"),
)
EXPECTED_TESTS = 7
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}"
)


def _publish(path: Path, value: Mapping[str, object]) -> None:
    target = ROOT / path
    if target.exists() or target.is_symlink():
        raise FileExistsError(target)
    descriptor = os.open(
        target,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def build(*, now: int | None = None) -> dict:
    environment = {
        "HOME": os.environ.get("HOME", str(Path.home())),
        "USER": os.environ.get("USER", "azureuser"),
        "LOGNAME": os.environ.get("LOGNAME", "azureuser"),
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "PYTHONSAFEPATH": "1",
    }
    completed = subprocess.run(
        [
            str(ROOT / ".venv-eval/bin/python"),
            "-I",
            "-B",
            str(ROOT / TEST),
            "-v",
        ],
        cwd=ROOT,
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=180,
        check=False,
    )
    match = re.search(r"Ran (\d+) tests?", completed.stdout)
    observed = int(match.group(1)) if match else 0
    failure = design._read(design.FAILURE_AUDIT)
    before = watcher_contract.protected_watcher_snapshot()
    source_text = "\n".join(
        (ROOT / path).read_text(encoding="utf-8") for path in SOURCES
    )
    after = watcher_contract.protected_watcher_snapshot()
    checks = {
        "clean_pushed_head": not design._git("status", "--porcelain")
        and design._git("rev-parse", "HEAD")
        == design._git("rev-parse", "target/main"),
        "predecessor_failure_is_zero_publication": failure.get("role")
        == "v24821_v24820_population_zero_publication_failure_audit"
        and failure.get("status")
        == "invalid_zero_publication_do_not_resume_retry_or_rerun"
        and failure.get("surfaces", {}).get("private_population_written") is False
        and failure.get("surfaces", {}).get("public_population_written") is False
        and failure.get("authorization", {}).get(
            "append_only_transport_successor_design"
        )
        is True
        and failure.get("authorization", {}).get("same_v24820_retry_resume_or_rerun")
        is False,
        "predecessor_surfaces_absent": all(
            not (ROOT / path).exists() and not (ROOT / path).is_symlink()
            for path in (design.parent.PRIVATE, design.parent.OUTPUT)
        ),
        "focused_tests_7_of_7": completed.returncode == 0
        and observed == EXPECTED_TESTS,
        "only_transport_and_surfaces_changed": design.TARGETS
        == design.parent.TARGETS
        and design.TASK_SIZE == design.parent.TASK_SIZE
        and design.TASK_COUNT == design.parent.TASK_COUNT
        and design.SELECTED_COUNT == design.parent.SELECTED_COUNT
        and design.ATTEMPT_TIMEOUT_SECONDS == 90
        and design.MAX_ATTEMPTS == 3,
        "future_surfaces_pristine": all(
            not (ROOT / path).exists() and not (ROOT / path).is_symlink()
            for path in (design.AUTHORIZATION, design.PRIVATE, design.OUTPUT)
        ),
        "credential_literal_absent": SECRET.search(source_text) is None,
        "protected_watchers_unchanged": before == after,
    }
    value = {
        "artifact_version": 1,
        "role": "v24822_bounded_snapshot_transport_population_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git_head": design._git("rev-parse", "HEAD"),
        "predecessor_failure_audit_sha256": design._sha256(
            design.FAILURE_AUDIT
        ),
        "source_manifest": {
            str(path): design._sha256(path) for path in SOURCES
        },
        "tests": {
            "expected": EXPECTED_TESTS,
            "observed": observed,
            "passed": completed.returncode == 0
            and observed == EXPECTED_TESTS,
            "output_sha256": design.payload_sha256(completed.stdout),
        },
        "checks": checks,
        "protected_watchers_before": before,
        "protected_watchers_after": after,
        "network_model_search_fetch_or_evaluator_called_by_audit": False,
        "findings": sorted(name for name, passed in checks.items() if not passed),
        "authorization": {
            "one_population_publication": all(checks.values()),
            "external_protocol_design": False,
            "external_launch": False,
            "evaluator": False,
            "public_dev64_or_exact220": False,
        },
    }
    value["audit_valid"] = not value["findings"]
    value["audit_payload_sha256"] = design.payload_sha256(value)
    if value["findings"]:
        raise RuntimeError(f"V2.48.22 audit rejected: {value['findings']}")
    return value


if __name__ == "__main__":
    artifact = build()
    _publish(OUTPUT, artifact)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "tests": artifact["tests"],
                "findings": artifact["findings"],
                "authorization": artifact["authorization"],
            },
            sort_keys=True,
        )
    )
