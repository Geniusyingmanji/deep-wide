#!/usr/bin/env python3
"""Build-only audit for the V2.48.26 exact API transport."""

from __future__ import annotations

import ast
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

from deepwide_agent.v24826_worldbank_exact_api_transport import (  # noqa: E402
    EXPECTED_TARGET_COUNT,
    exact_target_key,
    payload_sha256,
)


DATE = "20260807"
OUTPUT = Path(
    f"results/v24826_worldbank_exact_api_transport_build_audit_v1_{DATE}.json"
)
PARENT = Path(
    f"results/v24825_v24824_fetch_failure_diagnosis_v1_{DATE}.json"
)
RUNTIME = Path("src/deepwide_agent/v24826_worldbank_exact_api_transport.py")
HELPER = Path("scripts/run_v24826_worldbank_exact_fetch_helper.py")
TEST = Path("tests/test_v24826_worldbank_exact_api_transport.py")
AUDIT_SOURCE = Path("scripts/audit_v24826_worldbank_exact_api_transport.py")
SOURCES = (RUNTIME, HELPER, TEST, AUDIT_SOURCE)
EXPECTED_TESTS = 8
PRIVILEGED = frozenset(
    {
        "benchmark_question_type",
        "question_type",
        "task_category",
        "category",
        "split",
        "ground_truth",
        "gold",
        "answer_key",
        "mapping",
        "evaluator",
        "score",
        "reward",
    }
)
EVALUATOR_MARKERS = (
    "official_eval",
    "official_evaluator",
    "external_evaluator",
    "evaluator_mapping",
    "finalize_v24",
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
PROTECTED_WATCHERS = (
    (795336, "scripts/watch_v2415_r1_checkpoint_liveness.py"),
    (3061652, "scripts/watch_v24218_exact220_executor.py"),
    (2808901, "scripts/watch_v24215_joint_package_recovery.py"),
    (2889939, "scripts/watch_v24216_package_gate.py"),
)


def _ordinary(relative: Path) -> Path:
    path = ROOT / relative
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(ROOT.resolve())
    ):
        raise RuntimeError(f"V2.48.26 expected repository file: {relative}")
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
        raise RuntimeError("V2.48.26 audit expected JSON object")
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


def ast_findings(relative: Path) -> tuple[list[str], list[str]]:
    tree = ast.parse(_ordinary(relative).read_text(encoding="utf-8"))
    fields: list[str] = []
    imports: list[str] = []
    for node in ast.walk(tree):
        key = None
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in {"get", "pop", "setdefault"}
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            key = node.args[0].value.casefold()
        elif (
            isinstance(node, ast.Subscript)
            and isinstance(node.slice, ast.Constant)
            and isinstance(node.slice.value, str)
        ):
            key = node.slice.value.casefold()
        if key in PRIVILEGED:
            fields.append(f"{relative}:{node.lineno}:{key}")
        names = (
            [alias.name for alias in node.names]
            if isinstance(node, ast.Import)
            else [node.module or "", *(alias.name for alias in node.names)]
            if isinstance(node, ast.ImportFrom)
            else []
        )
        for name in names:
            if any(marker in name.casefold() for marker in EVALUATOR_MARKERS):
                imports.append(f"{relative}:{node.lineno}:{name}")
    return sorted(fields), sorted(imports)


def _watchers() -> list[dict[str, Any]]:
    rows = []
    for pid, marker in PROTECTED_WATCHERS:
        stat = Path("/proc") / str(pid) / "stat"
        cmdline = Path("/proc") / str(pid) / "cmdline"
        if not stat.is_file() or not cmdline.is_file():
            raise RuntimeError("V2.48.26 protected watcher absent")
        raw = stat.read_text(encoding="utf-8")
        suffix = raw[raw.rfind(")") + 2 :].split()
        command = cmdline.read_bytes().replace(b"\0", b" ").decode(
            errors="replace"
        )
        if len(suffix) <= 19 or marker not in command:
            raise RuntimeError("V2.48.26 protected watcher drifted")
        rows.append(
            {"pid": pid, "marker": marker, "start_ticks": int(suffix[19])}
        )
    return rows


def _parent_valid() -> bool:
    value = _read(PARENT)
    return (
        value.get("role") == "v24825_v24824_fetch_failure_diagnosis"
        and value.get("diagnosis_valid") is True
        and value.get("findings") == []
        and value.get("authorization", {}).get(
            "append_only_exact_api_transport_design"
        )
        is True
        and value.get("authorization", {}).get(
            "same_population_retry_resume_rerun_or_revaluation"
        )
        is False
        and _sealed(value, "diagnosis_payload_sha256")
    )


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
    return observed, completed.returncode == 0 and observed == EXPECTED_TESTS, completed.stdout


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    unsigned = dict(copied)
    seal = unsigned.pop("audit_payload_sha256", None)
    checks = copied.get("checks")
    authorization = copied.get("authorization")
    if (
        copied.get("role") != "v24826_worldbank_exact_api_transport_build_audit"
        or not isinstance(checks, Mapping)
        or copied.get("findings")
        != sorted(name for name, passed in checks.items() if not passed)
        or copied.get("audit_valid") is not (copied.get("findings") == [])
        or not isinstance(authorization, Mapping)
        or authorization.get("non_evaluation_transport_probe_design")
        is not copied.get("audit_valid")
        or authorization.get("external_population_or_launch") is not False
        or authorization.get("same_population_retry_resume_rerun_or_revaluation")
        is not False
        or authorization.get("public_exact220") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.48.26 build audit drifted")
    return copied


def build(
    *,
    now: int | None = None,
    require_clean: bool = True,
    require_tracked: bool = True,
) -> dict[str, Any]:
    before = _watchers()
    runtime_fields, runtime_imports = ast_findings(RUNTIME)
    helper_fields, helper_imports = ast_findings(HELPER)
    observed, tests_passed, test_output = _run_tests()
    after = _watchers()
    source_text = "\n".join(
        _ordinary(relative).read_text(encoding="utf-8") for relative in SOURCES
    )
    sample = (
        "https://api.worldbank.org/v2/country/WLD/indicator/"
        "SP.POP.0014.TO.ZS?date=2023&format=json&per_page=100"
    )
    checks = {
        "parent_diagnosis_authority_valid": _parent_valid(),
        "clean_pushed_head": (not require_clean)
        or (
            not _git("status", "--porcelain")
            and _git("rev-parse", "HEAD") == _git("rev-parse", "target/main")
        ),
        "sources_tracked": (not require_tracked)
        or all(
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
            for relative in SOURCES
        ),
        "focused_tests_8_of_8": tests_passed and observed == EXPECTED_TESTS,
        "runtime_privileged_access_absent": runtime_fields == [],
        "runtime_evaluator_import_absent": runtime_imports == [],
        "helper_privileged_access_absent": helper_fields == [],
        "helper_evaluator_import_absent": helper_imports == [],
        "credential_literal_absent": SECRET.search(source_text) is None,
        "exact_allowlist_shape_valid": exact_target_key(sample)
        == "WLD|SP.POP.0014.TO.ZS|2023",
        "fixed_eight_target_boundary": EXPECTED_TARGET_COUNT == 8,
        "protected_watchers_unchanged": before == after,
    }
    value = {
        "artifact_version": 1,
        "role": "v24826_worldbank_exact_api_transport_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "base_commit": _git("rev-parse", "HEAD"),
        "parent_diagnosis_sha256": _sha256(PARENT),
        "source_manifest": {
            str(relative): _sha256(relative) for relative in SOURCES
        },
        "tests": {
            "expected": EXPECTED_TESTS,
            "observed": observed,
            "passed": tests_passed,
            "output_sha256": payload_sha256(test_output),
        },
        "runtime_privileged_accesses": runtime_fields,
        "runtime_evaluator_imports": runtime_imports,
        "helper_privileged_accesses": helper_fields,
        "helper_evaluator_imports": helper_imports,
        "checks": checks,
        "findings": sorted(name for name, passed in checks.items() if not passed),
        "audit_valid": all(checks.values()),
        "protected_watchers_before": before,
        "protected_watchers_after": after,
        "audit_preconditions": {
            "clean_pushed_head_required": require_clean,
            "tracked_sources_required": require_tracked,
        },
        "effect_boundary": {
            "network_model_search_fetch_or_evaluator_called_by_audit": False,
            "in_memory_fake_transport_only": True,
            "benchmark_or_external_population_opened": False,
            "same_population_replayed_retried_rerun_or_revalued": False,
        },
        "authorization": {
            "non_evaluation_transport_probe_design": all(checks.values()),
            "external_population_or_launch": False,
            "same_population_retry_resume_rerun_or_revaluation": False,
            "public_exact220": False,
            "sota_claim": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return validate_audit(value)


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
    if artifact["findings"]:
        raise RuntimeError(f"V2.48.26 audit rejected: {artifact['findings']}")
    publish(ROOT / OUTPUT, artifact)
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
