#!/usr/bin/env python3
"""Build-only audit authorizing one V2.48.20 population publication."""

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
    design_v24820_cell_disjoint_worldbank_population as design,
)


OUTPUT = design.AUTHORIZATION
TEST = Path("tests/test_design_v24820_cell_disjoint_worldbank_population.py")
SOURCES = (
    Path("scripts/design_v24820_cell_disjoint_worldbank_population.py"),
    TEST,
    Path("scripts/audit_v24820_cell_disjoint_worldbank_population.py"),
)
EXPECTED_TESTS = 7
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}"
)


def _read(path: Path) -> dict:
    value = json.loads((ROOT / path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.48.20 audit expected object")
    return value


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
    controller = _read(design.CONTROLLER_AUDIT)
    entities, cells, targets, manifest = design.historical_boundary()
    target_pairs = {
        (item["indicator"], item["year"]) for item in design.TARGETS
    }
    before = watcher_contract.protected_watcher_snapshot()
    source_text = "\n".join(
        (ROOT / path).read_text(encoding="utf-8") for path in SOURCES
    )
    after = watcher_contract.protected_watcher_snapshot()
    checks = {
        "clean_pushed_head": not design._git("status", "--porcelain")
        and design._git("rev-parse", "HEAD")
        == design._git("rev-parse", "target/main"),
        "controller_audit_valid": controller.get("role")
        == "v24819_quality_first_controller_build_audit"
        and controller.get("audit_valid") is True
        and controller.get("findings") == []
        and controller.get("authorization", {}).get(
            "fresh_external_population_and_protocol_design"
        )
        is True
        and controller.get("authorization", {}).get("external_launch") is False
        and design._sealed(controller, "audit_payload_sha256"),
        "focused_tests_7_of_7": completed.returncode == 0
        and observed == EXPECTED_TESTS,
        "historical_boundary_material": len(entities) >= 190
        and len(cells) > 0
        and len(targets) == 6
        and len(manifest) == 4,
        "target_pairs_historically_disjoint": target_pairs.isdisjoint(targets),
        "fixed_denominator_32x4": design.TASK_COUNT == 32
        and design.TASK_SIZE == 4
        and design.SELECTED_COUNT == 128,
        "entity_disjointness_not_claimed": True,
        "future_surfaces_pristine": all(
            not (ROOT / path).exists() and not (ROOT / path).is_symlink()
            for path in (design.AUTHORIZATION, design.PRIVATE, design.OUTPUT)
        ),
        "credential_literal_absent": SECRET.search(source_text) is None,
        "protected_watchers_unchanged": before == after,
    }
    value = {
        "artifact_version": 1,
        "role": "v24820_cell_disjoint_worldbank_population_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git_head": design._git("rev-parse", "HEAD"),
        "controller_audit_sha256": design._sha256(design.CONTROLLER_AUDIT),
        "source_manifest": {
            str(path): design._sha256(path) for path in SOURCES
        },
        "historical_boundary_manifest_sha256": design.payload_sha256(manifest),
        "historical_boundary_counts": {
            "entity_count": len(entities),
            "gold_cell_key_count": len(cells),
            "target_pair_count": len(targets),
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
        "historical_private_values_used_for_selection_or_routing": False,
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
        raise RuntimeError(f"V2.48.20 audit rejected: {value['findings']}")
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
