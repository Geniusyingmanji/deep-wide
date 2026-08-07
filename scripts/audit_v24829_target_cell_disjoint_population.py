#!/usr/bin/env python3
"""Build-only audit authorizing one V2.48.29 population publication."""

from __future__ import annotations

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

from scripts import design_v24829_target_cell_disjoint_population as design  # noqa: E402


OUTPUT = design.AUTHORIZATION
TEST = Path("tests/test_design_v24829_target_cell_disjoint_population.py")
SCRIPT = Path("scripts/design_v24829_target_cell_disjoint_population.py")
AUDIT = Path("scripts/audit_v24829_target_cell_disjoint_population.py")
SOURCES = (
    SCRIPT,
    TEST,
    AUDIT,
    design.ACCOUNTING_AUDIT,
    design.CANDIDATE_DESIGN,
    design.REQUEST_PROTOCOL,
    *design.HISTORICAL_POPULATIONS,
)
EXPECTED_TESTS = 8
PROTECTED_WATCHERS = (
    (795336, 713986317, "scripts/watch_v2415_r1_checkpoint_liveness.py"),
    (3061652, 747569004, "scripts/watch_v24218_exact220_executor.py"),
    (2808901, 746680268, "scripts/watch_v24215_joint_package_recovery.py"),
    (2889939, 746969965, "scripts/watch_v24216_package_gate.py"),
)
SECRET_PREFIXES = ("gh" + "p_", "github_" + "pat_", "tvly-" + "dev-", "s" + "k-")
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:"
    + "|".join(re.escape(value) for value in SECRET_PREFIXES)
    + r")[A-Za-z0-9_-]{16,}"
)


def _ordinary(relative: Path) -> Path:
    return design._ordinary(ROOT, relative)


def _read(relative: Path) -> dict[str, Any]:
    return design._read(ROOT, relative)


def _tracked(relative: Path) -> bool:
    return (
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
    )


def _watchers() -> list[dict[str, Any]]:
    output = []
    for pid, ticks, marker in PROTECTED_WATCHERS:
        stat = Path("/proc") / str(pid) / "stat"
        cmdline = Path("/proc") / str(pid) / "cmdline"
        if not stat.is_file() or not cmdline.is_file():
            raise RuntimeError("V2.48.29 protected watcher absent")
        raw = stat.read_text(encoding="utf-8")
        suffix = raw[raw.rfind(")") + 2 :].split()
        command = cmdline.read_bytes().replace(b"\0", b" ").decode(errors="replace")
        if len(suffix) <= 19 or int(suffix[19]) != ticks or marker not in command:
            raise RuntimeError("V2.48.29 protected watcher drifted")
        output.append({"pid": pid, "start_ticks": ticks, "marker": marker})
    return output


def _run_tests() -> tuple[int, bool, str]:
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
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests",
            "-p",
            TEST.name,
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
    return observed, completed.returncode == 0 and observed == EXPECTED_TESTS, completed.stdout


def validate(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    unsigned = dict(copied)
    seal = unsigned.pop("audit_payload_sha256", None)
    checks = copied.get("checks")
    if (
        copied.get("role")
        != "v24829_target_cell_disjoint_population_build_audit"
        or not isinstance(checks, Mapping)
        or copied.get("findings")
        != sorted(name for name, passed in checks.items() if not passed)
        or copied.get("audit_valid") is not (copied.get("findings") == [])
        or copied.get("authorization")
        != {
            "one_population_publication": bool(copied.get("audit_valid")),
            "external_protocol_design": False,
            "external_launch": False,
            "evaluator": False,
            "public_dev64_or_exact220": False,
        }
        or seal != design.payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.48.29 population build audit drifted")
    return copied


def build(
    *, now: int | None = None, require_clean: bool = True, require_tracked: bool = True
) -> dict[str, Any]:
    accounting = _read(design.ACCOUNTING_AUDIT)
    selection = design.target_selection_contract(ROOT)
    entities, cells, targets, manifest = design.historical_boundary(ROOT)
    target_pairs = {(item["indicator"], item["year"]) for item in design.TARGETS}
    observed, tests_passed, test_output = _run_tests()
    before = _watchers()
    source_text = "\n".join(
        _ordinary(path).read_text(encoding="utf-8", errors="ignore")
        for path in (SCRIPT, TEST, AUDIT)
    )
    after = _watchers()
    checks = {
        "accounting_successor_authority_valid": accounting.get("role")
        == "v24828_dedicated_exact_accounting_build_audit"
        and accounting.get("audit_valid") is True
        and accounting.get("findings") == []
        and accounting.get("authorization", {}).get(
            "fresh_target_cell_disjoint_external_design"
        )
        is True
        and accounting.get("authorization", {}).get("external_population_launch")
        is False
        and design._sealed(accounting, "audit_payload_sha256"),
        "clean_pushed_head": (not require_clean)
        or (
            not design._git("status", "--porcelain")
            and design._git("rev-parse", "HEAD")
            == design._git("rev-parse", "target/main")
        ),
        "sources_tracked": (not require_tracked) or all(_tracked(path) for path in SOURCES),
        "focused_tests_8_of_8": tests_passed and observed == EXPECTED_TESTS,
        "target_selection_is_preoutcome_unrequested_remainder": selection[
            "network_or_transport_outcome_field_read_for_selection"
        ]
        is False
        and selection["selected_unrequested_target_key_vector"]
        == ["SH.STA.BASS.ZS@2022", "SL.UEM.TOTL.ZS@2023"],
        "cumulative_historical_boundary_exact": len(manifest) == 5
        and len(entities) == 217
        and len(cells) == 672
        and len(targets) == 8,
        "target_pairs_historically_disjoint": target_pairs.isdisjoint(targets),
        "fixed_denominator_32x4": design.TASK_COUNT == 32
        and design.TASK_SIZE == 4
        and design.SELECTED_COUNT == 128,
        "future_surfaces_pristine": all(
            not (ROOT / path).exists() and not (ROOT / path).is_symlink()
            for path in (design.AUTHORIZATION, design.PRIVATE, design.OUTPUT)
        ),
        "credential_literal_absent": SECRET.search(source_text) is None,
        "protected_watchers_unchanged": before == after,
    }
    value = {
        "artifact_version": 1,
        "role": "v24829_target_cell_disjoint_population_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git_head": design._git("rev-parse", "HEAD"),
        "accounting_audit_sha256": design._sha256(ROOT, design.ACCOUNTING_AUDIT),
        "target_selection_contract": selection,
        "source_manifest": {str(path): design._sha256(ROOT, path) for path in SOURCES},
        "historical_boundary_manifest_sha256": design.payload_sha256(manifest),
        "historical_boundary_counts": {
            "population_count": len(manifest),
            "entity_count": len(entities),
            "gold_cell_key_count": len(cells),
            "target_pair_count": len(targets),
        },
        "tests": {
            "expected": EXPECTED_TESTS,
            "observed": observed,
            "passed": tests_passed,
            "output_sha256": design.payload_sha256(test_output),
        },
        "checks": checks,
        "protected_watchers_before": before,
        "protected_watchers_after": after,
        "effect_boundary": {
            "network_model_search_fetch_or_evaluator_called_by_audit": False,
            "historical_private_values_used_for_selection_or_routing": False,
            "population_or_task_vector_created": False,
        },
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
    value["audit_payload_sha256"] = design.payload_sha256(value)
    return validate(value)


def publish(path: Path, value: Mapping[str, Any]) -> None:
    target = ROOT / path
    if target.exists() or target.is_symlink():
        raise FileExistsError(target)
    descriptor = os.open(
        target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    artifact = build()
    if artifact["findings"]:
        raise RuntimeError(f"V2.48.29 audit rejected: {artifact['findings']}")
    publish(OUTPUT, artifact)
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
