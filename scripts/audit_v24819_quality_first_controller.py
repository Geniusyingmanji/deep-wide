#!/usr/bin/env python3
"""Build-only audit for the V2.48.19 quality-first controller."""

from __future__ import annotations

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


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24819_quality_first_controller import (  # noqa: E402
    CalibrationBinding,
    QualityFirstPolicy,
    decide_quality_first_state,
)
from scripts.audit_v24804_shared_prefix_budget_ladder import (  # noqa: E402
    ast_findings,
)


DATE = "20260807"
OUTPUT = Path(
    f"results/v24819_quality_first_controller_build_audit_v1_{DATE}.json"
)
PARENT = Path(
    f"results/v24818_v24815_adaptive_stop_diagnosis_v1_{DATE}.json"
)
PARENT_BUILD_AUDIT = Path(
    f"results/v24804_shared_prefix_budget_ladder_build_audit_v1_{DATE}.json"
)
RUNTIME = Path("src/deepwide_agent/v24819_quality_first_controller.py")
PARENT_RUNTIME = Path("src/deepwide_agent/v24804_shared_prefix_budget_ladder.py")
TEST = Path("tests/test_v24819_quality_first_controller.py")
AUDIT_TEST = Path("tests/test_audit_v24819_quality_first_controller.py")
AUDIT_SOURCE = Path("scripts/audit_v24819_quality_first_controller.py")
SOURCES = (RUNTIME, TEST, AUDIT_TEST, AUDIT_SOURCE)
DEPENDENCIES = (PARENT_RUNTIME, PARENT, PARENT_BUILD_AUDIT)
EXPECTED_TESTS = 16
PROTECTED_WATCHERS = (
    (795336, "scripts/watch_v2415_r1_checkpoint_liveness.py"),
    (3061652, "scripts/watch_v24218_exact220_executor.py"),
    (2808901, "scripts/watch_v24215_joint_package_recovery.py"),
    (2889939, "scripts/watch_v24216_package_gate.py"),
)
SECRET_PREFIXES = (
    "gh" + "p_",
    "github_" + "pat_",
    "tvly-" + "dev-",
    "s" + "k-",
)
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:"
    + "|".join(re.escape(value) for value in SECRET_PREFIXES)
    + r")[A-Za-z0-9_-]{16,}"
)


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()


def _ordinary(relative: Path) -> Path:
    path = ROOT / relative
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(ROOT.resolve())
    ):
        raise RuntimeError(f"V2.48.19 expected repository file: {relative}")
    return path


def _sha256(relative: Path) -> str:
    digest = hashlib.sha256()
    with _ordinary(relative).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read(relative: Path) -> dict[str, Any]:
    value = json.loads(_ordinary(relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.48.19 expected JSON object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


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


def _clean_pushed() -> bool:
    return (
        not _git("status", "--porcelain")
        and _git("rev-parse", "HEAD") == _git("rev-parse", "target/main")
    )


def _tracked_sources() -> bool:
    return all(
        subprocess.run(
            ["git", "ls-files", "--error-unmatch", str(relative)],
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=20,
            check=False,
        ).returncode
        == 0
        for relative in (*SOURCES, *DEPENDENCIES)
    )


def _parent_valid() -> bool:
    value = _read(PARENT)
    return (
        value.get("role")
        == "v24818_v24815_adaptive_stop_aggregate_diagnosis"
        and value.get("status")
        == "smoke_cost_quality_scale_uncalibrated_boundary_stop_no_go"
        and value.get("diagnosis_valid") is True
        and value.get("findings") == []
        and value.get("authorization", {}).get(
            "append_only_quality_first_controller_design"
        )
        is True
        and value.get("authorization", {}).get(
            "fresh_external_population_design"
        )
        is True
        and value.get("authorization", {}).get(
            "same_population_replay_or_revaluation"
        )
        is False
        and _sealed(value, "diagnosis_payload_sha256")
    )


def _parent_build_valid() -> bool:
    value = _read(PARENT_BUILD_AUDIT)
    return (
        value.get("role") == "v24804_shared_prefix_budget_ladder_build_audit"
        and value.get("audit_valid") is True
        and value.get("findings") == []
        and value.get("authorization", {}).get("public_exact220") is False
        and _sealed(value, "audit_payload_sha256")
    )


def _watchers() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for pid, marker in PROTECTED_WATCHERS:
        stat = Path("/proc") / str(pid) / "stat"
        cmdline = Path("/proc") / str(pid) / "cmdline"
        if not stat.is_file() or not cmdline.is_file():
            raise RuntimeError("V2.48.19 protected watcher is absent")
        raw = stat.read_text(encoding="utf-8")
        suffix = raw[raw.rfind(")") + 2 :].split()
        command = cmdline.read_bytes().replace(b"\0", b" ").decode(
            errors="replace"
        )
        if len(suffix) <= 19 or marker not in command:
            raise RuntimeError("V2.48.19 protected watcher identity drifted")
        rows.append(
            {"pid": pid, "marker": marker, "start_ticks": int(suffix[19])}
        )
    return rows


def _lease_inactive() -> bool:
    completed = subprocess.run(
        [
            str(ROOT / ".venv-eval/bin/python"),
            "-I",
            "-B",
            "-c",
            "from pathlib import Path; import fcntl, os; "
            "p=Path('outputs/deepwide_benchmark_api.lease.lock'); "
            "p.parent.mkdir(parents=True,exist_ok=True); "
            "fd=os.open(p,os.O_RDWR|os.O_CREAT,0o600); "
            "fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB); "
            "fcntl.flock(fd,fcntl.LOCK_UN); os.close(fd)",
        ],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=10,
        check=False,
    )
    return completed.returncode == 0


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
    total = 0
    for test, expected in ((TEST, 11), (AUDIT_TEST, 5)):
        completed = subprocess.run(
            [
                str(ROOT / ".venv-eval/bin/python"),
                "-I",
                "-B",
                str(ROOT / test),
                "-v",
            ],
            cwd=ROOT,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=120,
            check=False,
        )
        match = re.search(r"Ran (\d+) tests?", completed.stdout)
        observed = int(match.group(1)) if match else 0
        total += observed
        rows.append(
            {
                "path": str(test),
                "expected": expected,
                "observed": observed,
                "passed": completed.returncode == 0 and observed == expected,
                "output_sha256": payload_sha256(completed.stdout),
            }
        )
    return total, all(row["passed"] for row in rows), rows


def _valid_binding(*, drift: bool = False) -> CalibrationBinding:
    declared = hashlib.sha256(b"v24819-calibration-artifact").hexdigest()
    observed = (
        hashlib.sha256(b"v24819-drifted-artifact").hexdigest()
        if drift
        else declared
    )
    return CalibrationBinding(
        artifact_path="results/v24819_external_calibration_v1.json",
        declared_artifact_sha256=declared,
        observed_artifact_sha256=observed,
        artifact_payload_sha256=hashlib.sha256(
            b"v24819-calibration-payload"
        ).hexdigest(),
        calibration_task_count=128,
        terminal_utility_observed=True,
        heldout_validation_passed=True,
        external_artifact_verified_before_runtime=True,
        quality_cost_exchange_rate=10.0,
    )


def _decision_gate() -> dict[str, Any]:
    high_cost = QualityFirstPolicy(
        calibration_binding=_valid_binding(),
        per_lookup_resource_units=1_000_000.0,
    )
    mandatory = decide_quality_first_state(
        required_visible_cell_keys=("cell-a", "cell-b"),
        observed_required_cell_keys=("cell-a",),
        candidate_action_cell_keys=("cell-b",),
        valid_first_records=4,
        returned_first_results=4,
        valid_first_countries=4,
        remaining_lookup_budget=1,
        policy=high_cost,
    )
    missing = decide_quality_first_state(
        required_visible_cell_keys=("cell-a",),
        observed_required_cell_keys=("cell-a",),
        candidate_action_cell_keys=("optional-check",),
        valid_first_records=4,
        returned_first_results=4,
        valid_first_countries=4,
        remaining_lookup_budget=1,
        policy=QualityFirstPolicy(),
    )
    drifted = decide_quality_first_state(
        required_visible_cell_keys=("cell-a",),
        observed_required_cell_keys=("cell-a",),
        candidate_action_cell_keys=("optional-check",),
        valid_first_records=4,
        returned_first_results=4,
        valid_first_countries=4,
        remaining_lookup_budget=1,
        policy=QualityFirstPolicy(
            calibration_binding=_valid_binding(drift=True)
        ),
    )
    calibrated_stop = decide_quality_first_state(
        required_visible_cell_keys=("cell-a",),
        observed_required_cell_keys=("cell-a",),
        candidate_action_cell_keys=("optional-check",),
        valid_first_records=4,
        returned_first_results=4,
        valid_first_countries=4,
        remaining_lookup_budget=1,
        policy=QualityFirstPolicy(
            calibration_binding=_valid_binding(),
            per_lookup_resource_units=10.0,
        ),
    )
    budget_blocked = decide_quality_first_state(
        required_visible_cell_keys=("cell-a", "cell-b"),
        observed_required_cell_keys=("cell-a",),
        candidate_action_cell_keys=("cell-b",),
        valid_first_records=4,
        returned_first_results=4,
        valid_first_countries=4,
        remaining_lookup_budget=0,
        policy=QualityFirstPolicy(calibration_binding=_valid_binding()),
    )
    unactionable = decide_quality_first_state(
        required_visible_cell_keys=("cell-a", "cell-b"),
        observed_required_cell_keys=("cell-a",),
        candidate_action_cell_keys=("optional-check",),
        valid_first_records=4,
        returned_first_results=4,
        valid_first_countries=4,
        remaining_lookup_budget=1,
        policy=QualityFirstPolicy(
            calibration_binding=_valid_binding(),
            per_lookup_resource_units=1_000_000.0,
        ),
    )
    rows = (
        mandatory,
        missing,
        drifted,
        calibrated_stop,
        budget_blocked,
        unactionable,
    )
    return {
        "mandatory_high_cost_decision": mandatory["decision"],
        "mandatory_high_cost_reason": mandatory["reason"],
        "missing_calibration_decision": missing["decision"],
        "missing_calibration_reason": missing["reason"],
        "drifted_calibration_decision": drifted["decision"],
        "drifted_calibration_reason": drifted["reason"],
        "calibrated_complete_coverage_decision": calibrated_stop["decision"],
        "calibrated_complete_coverage_reason": calibrated_stop["reason"],
        "budget_blocked_decision": budget_blocked["decision"],
        "budget_blocked_reason": budget_blocked["reason"],
        "unactionable_gap_decision": unactionable["decision"],
        "unactionable_gap_reason": unactionable["reason"],
        "all_suffix_blind": all(
            row["suffix_response_or_value_read"] is False for row in rows
        ),
        "all_entropy_shadow_only": all(
            row["information_gain_feature_value"] == 0.0
            and row["entropy_assigns_signed_credit"] is False
            and row[
                "terminal_utility_signed_credit_observed_for_this_action"
            ]
            is False
            for row in rows
        ),
        "quality_cost_stop_only_after_complete_coverage_and_valid_calibration": (
            calibrated_stop["cost_sensitive_stopping_applied"] is True
            and calibrated_stop["coverage_observation"][
                "missing_required_cell_count"
            ]
            == 0
            and calibrated_stop["calibration_binding_status"]["valid"] is True
            and all(
                row["cost_sensitive_stopping_applied"] is False
                for row in (
                    mandatory,
                    missing,
                    drifted,
                    budget_blocked,
                    unactionable,
                )
            )
        ),
    }


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("audit_payload_sha256", None)
    checks = copied.get("checks")
    authorization = copied.get("authorization")
    if (
        copied.get("role")
        != "v24819_quality_first_controller_build_audit"
        or not isinstance(checks, Mapping)
        or copied.get("findings")
        != sorted(name for name, passed in checks.items() if not passed)
        or copied.get("audit_valid") is not (copied.get("findings") == [])
        or not isinstance(authorization, Mapping)
        or authorization.get("fresh_external_population_and_protocol_design")
        is not copied.get("audit_valid")
        or authorization.get("external_launch") is not False
        or authorization.get("public_dev64") is not False
        or authorization.get("public_exact220") is not False
        or authorization.get("leaderboard_submission") is not False
        or authorization.get("sota_claim") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.48.19 build audit drifted")
    return copied


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    before = _watchers()
    accesses, imports = ast_findings(RUNTIME)
    parent_accesses, parent_imports = ast_findings(PARENT_RUNTIME)
    observed, tests_passed, suites = _run_tests()
    after = _watchers()
    source_text = "\n".join(
        _ordinary(relative).read_text(encoding="utf-8") for relative in SOURCES
    )
    decision = _decision_gate()
    checks = {
        "parent_diagnosis_authority_valid": _parent_valid(),
        "parent_runtime_build_audit_valid": _parent_build_valid(),
        "clean_pushed_head": _clean_pushed(),
        "source_and_dependencies_tracked": _tracked_sources(),
        "focused_tests_passed": tests_passed
        and observed == EXPECTED_TESTS,
        "runtime_privileged_access_absent": accesses == [],
        "runtime_evaluator_import_absent": imports == [],
        "parent_runtime_privileged_access_absent": parent_accesses == [],
        "parent_runtime_evaluator_import_absent": parent_imports == [],
        "credential_literal_absent": SECRET.search(source_text) is None,
        "mandatory_incomplete_coverage_expands_despite_cost": decision[
            "mandatory_high_cost_decision"
        ]
        == "expand"
        and decision["mandatory_high_cost_reason"]
        == "mandatory_visible_cell_coverage",
        "missing_calibration_safe_expands": decision[
            "missing_calibration_decision"
        ]
        == "expand"
        and decision["missing_calibration_reason"]
        == "calibration_missing_or_drifted_safe_expand",
        "drifted_calibration_safe_expands": decision[
            "drifted_calibration_decision"
        ]
        == "expand"
        and decision["drifted_calibration_reason"]
        == "calibration_missing_or_drifted_safe_expand",
        "cost_stop_guarded_by_complete_coverage_and_valid_calibration": decision[
            "quality_cost_stop_only_after_complete_coverage_and_valid_calibration"
        ],
        "budget_block_is_explicit_not_cost_stop": decision[
            "budget_blocked_decision"
        ]
        == "stop"
        and decision["budget_blocked_reason"]
        == "mandatory_coverage_budget_blocked",
        "unactionable_required_gap_is_not_cost_stop": decision[
            "unactionable_gap_decision"
        ]
        == "stop"
        and decision["unactionable_gap_reason"]
        == "required_coverage_not_actionable",
        "decision_is_suffix_blind": decision["all_suffix_blind"],
        "entropy_is_shadow_only_not_signed_credit": decision[
            "all_entropy_shadow_only"
        ],
        "protected_watchers_unchanged": before == after,
        "shared_api_lease_inactive": _lease_inactive(),
    }
    value = {
        "artifact_version": 1,
        "role": "v24819_quality_first_controller_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "base_commit": _git("rev-parse", "HEAD"),
        "parent_diagnosis_sha256": _sha256(PARENT),
        "parent_build_audit_sha256": _sha256(PARENT_BUILD_AUDIT),
        "source_manifest": {
            str(relative): _sha256(relative) for relative in SOURCES
        },
        "dependency_manifest": {
            str(relative): _sha256(relative) for relative in DEPENDENCIES
        },
        "focused_tests": {
            "expected": EXPECTED_TESTS,
            "observed": observed,
            "passed": tests_passed,
            "suites": suites,
        },
        "runtime_privileged_accesses": accesses,
        "runtime_evaluator_imports": imports,
        "parent_runtime_privileged_accesses": parent_accesses,
        "parent_runtime_evaluator_imports": parent_imports,
        "synthetic_decision_gate": decision,
        "protected_watchers_before": before,
        "protected_watchers_after": after,
        "checks": checks,
        "findings": sorted(name for name, passed in checks.items() if not passed),
        "effect_boundary": {
            "external_network_provider_model_search_fetch_or_evaluator_called": False,
            "in_memory_fake_clients_called_by_focused_tests": True,
            "benchmark_task_mapping_gold_or_evaluator_resource_opened": False,
            "v24815_population_replayed_retried_or_revalued": False,
            "public_benchmark_forward_authorized": False,
        },
        "authorization": {
            "fresh_external_population_and_protocol_design": all(
                checks.values()
            ),
            "external_launch": False,
            "public_dev64": False,
            "public_exact220": False,
            "leaderboard_submission": False,
            "sota_claim": False,
        },
    }
    value["audit_valid"] = not value["findings"]
    value["audit_payload_sha256"] = payload_sha256(value)
    return validate_audit(value)


def _publish(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def main() -> None:
    value = build_audit()
    if value["findings"]:
        raise RuntimeError(f"V2.48.19 audit rejected: {value['findings']}")
    _publish(ROOT / OUTPUT, value)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "audit_valid": value["audit_valid"],
                "focused_tests": value["focused_tests"]["observed"],
                "authorization": value["authorization"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
