#!/usr/bin/env python3
"""Audit the append-only V2.48.06 smoke-population publication repair.

The predecessor publication stopped at its clean-worktree gate.  This module
first freezes a zero-effect controlled replay of that failure, then audits the
successor whose only behavioral change is accepting the one pre-existing local
``.research/tmp/`` cache.  Neither audit authorizes a smoke forward/evaluator.
"""

from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import (  # noqa: E402
    audit_v24805_worldbank_budget_ladder_smoke_population as parent_audit,
)
from scripts import (  # noqa: E402
    design_v24805_worldbank_budget_ladder_smoke_population as predecessor,
)
from scripts import (  # noqa: E402
    design_v24806_worldbank_budget_ladder_smoke_population as design,
)
from scripts.audit_v24804_shared_prefix_budget_ladder import (  # noqa: E402
    SECRET,
    payload_sha256,
)


FAILURE_OUTPUT = design.FAILURE_AUDIT
OUTPUT = design.AUTHORIZATION
SOURCES = (
    predecessor.AUTHORIZATION,
    design.FAILURE_AUDIT,
    Path("scripts/design_v24805_worldbank_budget_ladder_smoke_population.py"),
    Path("scripts/audit_v24805_worldbank_budget_ladder_smoke_population.py"),
    Path("scripts/design_v24806_worldbank_budget_ladder_smoke_population.py"),
    Path("tests/test_design_v24806_worldbank_budget_ladder_smoke_population.py"),
    Path("scripts/audit_v24806_worldbank_budget_ladder_smoke_population.py"),
    Path("tests/test_audit_v24806_worldbank_budget_ladder_smoke_population.py"),
)
TEST_SUITES = (
    (Path("tests/test_v24804_shared_prefix_budget_ladder.py"), 6),
    (Path("tests/test_audit_v24804_shared_prefix_budget_ladder.py"), 4),
    (Path("tests/test_design_v24805_worldbank_budget_ladder_smoke_population.py"), 5),
    (Path("tests/test_audit_v24805_worldbank_budget_ladder_smoke_population.py"), 3),
    (Path("tests/test_design_v24806_worldbank_budget_ladder_smoke_population.py"), 4),
    (Path("tests/test_audit_v24806_worldbank_budget_ladder_smoke_population.py"), 5),
)
EXPECTED_TESTS = sum(expected for _path, expected in TEST_SUITES)


def _ordinary(relative: Path) -> Path:
    path = ROOT / relative
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(ROOT.resolve())
    ):
        raise RuntimeError(f"V2.48.06 expected repository file: {relative}")
    return path


def _read(relative: Path) -> dict[str, Any]:
    value = json.loads(_ordinary(relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.48.06 expected JSON object")
    return value


def _sha256(relative: Path) -> str:
    return hashlib.sha256(_ordinary(relative).read_bytes()).hexdigest()


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=20,
    ).stdout.strip()


def _tracked(relative: Path) -> bool:
    return subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(relative)], cwd=ROOT,
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, timeout=20, check=False,
    ).returncode == 0


def _watchers() -> list[dict[str, Any]]:
    from scripts.audit_v24804_shared_prefix_budget_ladder import _watchers

    return _watchers()


def _lease_inactive() -> bool:
    from scripts.audit_v24804_shared_prefix_budget_ladder import _lease_inactive

    return _lease_inactive()


def _predecessor_authority_valid() -> bool:
    value = _read(predecessor.AUTHORIZATION)
    try:
        parent_audit.validate_audit(value)
    except RuntimeError:
        return False
    return (
        value.get("authorization", {}).get("one_smoke_population_publication")
        is True
        and value.get("authorization", {}).get("smoke_launch") is False
        and value.get("effect_boundary", {}).get("population_consumed") is False
    )


def controlled_predecessor_failure_replay() -> dict[str, Any]:
    """Replay only the dirty-tree guard and prove all effect hooks stay closed."""
    with (
        patch.object(predecessor, "_git", return_value="?? .research/tmp/"),
        patch.object(predecessor, "_authorized") as authorized,
        patch.object(predecessor, "_fetch_bytes") as fetch,
        patch.object(predecessor, "_publish") as publish,
    ):
        message = ""
        try:
            predecessor.main()
        except RuntimeError as error:
            message = str(error)
        else:
            raise RuntimeError("V2.48.06 predecessor replay unexpectedly passed")
    return {
        "failure_type": "RuntimeError",
        "failure_message": message,
        "authorization_checks": authorized.call_count,
        "network_fetch_calls": fetch.call_count,
        "publication_calls": publish.call_count,
    }


def _predecessor_control_flow() -> dict[str, Any]:
    source = _ordinary(
        Path("scripts/design_v24805_worldbank_budget_ladder_smoke_population.py")
    ).read_text(encoding="utf-8")
    tree = ast.parse(source)
    main = next(
        node for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == "main"
    )
    first_if = main.body[0]
    if not isinstance(first_if, ast.If):
        raise RuntimeError("V2.48.06 predecessor first guard drifted")
    return {
        "main_first_statement_is_clean_pushed_guard": True,
        "clean_guard_source_line": int(first_if.lineno),
        "authorization_source_line": source[: source.index("if not _authorized()")].count("\n") + 1,
        "first_fetch_source_line": source[: source.index("catalog_raw = _fetch_bytes")].count("\n") + 1,
    }


def build_failure_audit(*, now: int | None = None) -> dict[str, Any]:
    before = _watchers()
    replay = controlled_predecessor_failure_replay()
    flow = _predecessor_control_flow()
    after = _watchers()
    predecessor_surfaces_absent = all(
        not (ROOT / path).exists() and not (ROOT / path).is_symlink()
        for path in (predecessor.PRIVATE, predecessor.OUTPUT)
    )
    checks = {
        "predecessor_authority_valid_and_unconsumed": _predecessor_authority_valid(),
        "predecessor_population_surfaces_absent": predecessor_surfaces_absent,
        "controlled_replay_matches_observed_clean_gate_error": replay == {
            "failure_type": "RuntimeError",
            "failure_message": "V2.48.05 population publication requires clean pushed HEAD",
            "authorization_checks": 0,
            "network_fetch_calls": 0,
            "publication_calls": 0,
        },
        "clean_guard_precedes_authority_and_network": (
            flow["clean_guard_source_line"]
            < flow["authorization_source_line"]
            < flow["first_fetch_source_line"]
        ),
        "protected_watchers_unchanged": before == after,
        "shared_api_lease_inactive": _lease_inactive(),
    }
    value = {
        "artifact_version": 1,
        "role": "v24806_v24805_population_zero_effect_failure_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "base_commit": _git("rev-parse", "HEAD"),
        "predecessor_authority_sha256": _sha256(predecessor.AUTHORIZATION),
        "predecessor_source_sha256": _sha256(
            Path("scripts/design_v24805_worldbank_budget_ladder_smoke_population.py")
        ),
        "controlled_failure_replay": replay,
        "static_control_flow": flow,
        "checks": checks,
        "findings": sorted(name for name, passed in checks.items() if not passed),
        "audit_valid": all(checks.values()),
        "effect_boundary": {
            "controlled_replay_network_model_search_fetch_benchmark_or_evaluator_called": False,
            "controlled_replay_population_or_private_surface_published": False,
            "predecessor_population_surfaces_currently_absent": predecessor_surfaces_absent,
            "historical_network_absence_not_inferred_from_surface_absence_alone": True,
            "population_consumed": False,
        },
        "authorization": {
            "append_only_clean_gate_successor_build_audit": all(checks.values()),
            "population_publication": False,
            "smoke_protocol_design": False,
            "smoke_launch": False,
            "evaluator_access": False,
            "public_dev64_or_exact220": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return validate_failure_audit(value)


def validate_failure_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("audit_payload_sha256", None)
    if (
        copied.get("role")
        != "v24806_v24805_population_zero_effect_failure_audit"
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or copied.get("authorization") != {
            "append_only_clean_gate_successor_build_audit": True,
            "population_publication": False,
            "smoke_protocol_design": False,
            "smoke_launch": False,
            "evaluator_access": False,
            "public_dev64_or_exact220": False,
        }
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.48.06 predecessor failure audit drifted")
    return copied


def _run_tests() -> tuple[int, bool, list[dict[str, Any]]]:
    environment = {
        "HOME": os.environ.get("HOME", str(Path.home())),
        "USER": os.environ.get("USER", "azureuser"),
        "LOGNAME": os.environ.get("LOGNAME", "azureuser"),
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "PYTHONSAFEPATH": "1",
    }
    rows: list[dict[str, Any]] = []
    for path, expected in TEST_SUITES:
        completed = subprocess.run(
            [
                str(ROOT / ".venv-eval/bin/python"), "-I", "-B", "-m",
                "unittest", "discover", "-s", "tests", "-p", path.name, "-v",
            ],
            cwd=ROOT, env=environment, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            timeout=120, check=False,
        )
        match = re.search(r"Ran (\d+) tests?", completed.stdout)
        observed = int(match.group(1)) if match else 0
        rows.append({
            "path": str(path),
            "expected": expected,
            "observed": observed,
            "passed": completed.returncode == 0 and observed == expected,
            "output_sha256": payload_sha256(completed.stdout),
        })
    observed = sum(row["observed"] for row in rows)
    return observed, all(row["passed"] for row in rows) and observed == EXPECTED_TESTS, rows


def _failure_audit_valid() -> bool:
    try:
        value = _read(FAILURE_OUTPUT)
        validate_failure_audit(value)
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError):
        return False
    return _tracked(FAILURE_OUTPUT)


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    before = _watchers()
    observed, tests_passed, suites = _run_tests()
    after = _watchers()
    source_text = "\n".join(
        _ordinary(path).read_text(encoding="utf-8") for path in SOURCES
    )
    successor_source = _ordinary(
        Path("scripts/design_v24806_worldbank_budget_ladder_smoke_population.py")
    ).read_text(encoding="utf-8")
    implementation = {
        "predecessor": "v24805",
        "only_change": "permit_exact_untracked_research_tmp_directory",
        "population_selection_delegates_to_predecessor": "base.select_population(" in successor_source,
        "catalog_and_snapshot_parsers_delegate_to_predecessor": (
            "base.parse_country_catalog(" in successor_source
            and "base.parse_indicator_snapshot(" in successor_source
        ),
        "targets_equal_predecessor": design.base.TARGETS == predecessor.TARGETS,
        "rank_strata_policy_equal_predecessor": (
            design.base.STRATUM_VECTOR == predecessor.STRATUM_VECTOR
            and design.base.POLICY == predecessor.POLICY
        ),
        "successor_authority_precedes_first_fetch": successor_source.index(
            "if not _authorized()"
        ) < successor_source.index("catalog_raw = base._fetch_bytes"),
        "predecessor_surfaces_rejected": "for path in (base.PRIVATE, base.OUTPUT, PRIVATE, OUTPUT)" in successor_source,
    }
    future_pristine = all(
        not (ROOT / path).exists() and not (ROOT / path).is_symlink()
        for path in (design.PRIVATE, design.OUTPUT)
    )
    predecessor_pristine = all(
        not (ROOT / path).exists() and not (ROOT / path).is_symlink()
        for path in (predecessor.PRIVATE, predecessor.OUTPUT)
    )
    checks = {
        "clean_pushed_head": _git("status", "--porcelain") == ""
        and _git("rev-parse", "HEAD") == _git("rev-parse", "target/main"),
        "predecessor_authority_valid_and_unconsumed": _predecessor_authority_valid(),
        "predecessor_failure_audit_valid_and_tracked": _failure_audit_valid(),
        "focused_tests_passed": tests_passed,
        "implementation_is_narrow_successor": all(implementation.values()),
        "historical_exclusion_count_96": len(predecessor.historical_iso3(ROOT)[0]) == 96,
        "predecessor_population_surfaces_pristine": predecessor_pristine,
        "successor_population_surfaces_pristine": future_pristine,
        "credential_literal_absent": SECRET.search(source_text) is None,
        "protected_watchers_unchanged": before == after,
        "shared_api_lease_inactive": _lease_inactive(),
    }
    value = {
        "artifact_version": 1,
        "role": "v24806_worldbank_budget_ladder_smoke_population_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "base_commit": _git("rev-parse", "HEAD"),
        "parent_authority_sha256": _sha256(predecessor.AUTHORIZATION),
        "predecessor_failure_audit_sha256": _sha256(FAILURE_OUTPUT),
        "source_manifest": {str(path): _sha256(path) for path in SOURCES},
        "focused_tests": {
            "expected": EXPECTED_TESTS,
            "observed": observed,
            "passed": tests_passed,
            "suites": suites,
        },
        "implementation": implementation,
        "checks": checks,
        "findings": sorted(name for name, passed in checks.items() if not passed),
        "audit_valid": all(checks.values()),
        "effect_boundary": {
            "network_model_search_fetch_benchmark_or_evaluator_called_by_audit": False,
            "private_gold_value_used_for_routing": False,
            "predecessor_population_consumed": False,
            "successor_population_consumed": False,
        },
        "authorization": {
            "one_smoke_population_publication": all(checks.values()),
            "smoke_protocol_design": False,
            "smoke_launch": False,
            "main_calibration_lock_validation_or_confirmatory_launch": False,
            "evaluator_access": False,
            "public_dev64_or_exact220": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return validate_audit(value)


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("audit_payload_sha256", None)
    if (
        copied.get("role")
        != "v24806_worldbank_budget_ladder_smoke_population_build_audit"
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or copied.get("authorization") != {
            "one_smoke_population_publication": True,
            "smoke_protocol_design": False,
            "smoke_launch": False,
            "main_calibration_lock_validation_or_confirmatory_launch": False,
            "evaluator_access": False,
            "public_dev64_or_exact220": False,
        }
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.48.06 population build audit drifted")
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("failure", "build"))
    args = parser.parse_args()
    if args.command == "failure":
        value = build_failure_audit()
        path = FAILURE_OUTPUT
    else:
        value = build_audit()
        path = OUTPUT
    publish(ROOT / path, value)
    print(json.dumps({
        "path": str(path),
        "role": value["role"],
        "audit_valid": value["audit_valid"],
        "authorization": value["authorization"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
