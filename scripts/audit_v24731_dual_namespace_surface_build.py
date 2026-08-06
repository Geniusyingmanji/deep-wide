#!/usr/bin/env python3
"""Audit and authorize one V2.47.30 physically separated surface build."""

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

from scripts import build_v24730_dual_namespace_surfaces as builder  # noqa: E402
from scripts import design_v24729_dual_namespace_population_capacity_repair as design  # noqa: E402


DATE = "20260806"
OUTPUT = Path(f"results/v24731_dual_namespace_surface_build_audit_v1_{DATE}.json")
SOURCES = (
    Path("scripts/build_v24730_dual_namespace_surfaces.py"),
    Path("tests/test_build_v24730_dual_namespace_surfaces.py"),
    Path("scripts/design_v24729_dual_namespace_population_capacity_repair.py"),
    Path("results/v24729_dual_namespace_population_design_v1_20260806.json"),
    Path("evaluation/v24729_ror_population_private_v1_20260806.json"),
    Path("evaluation/v24729_worldbank_population_private_v1_20260806.json"),
)
TEST_FILE = Path("tests/test_build_v24730_dual_namespace_surfaces.py")
EXPECTED_TESTS = 5
SECRET_PREFIXES = ("gh" + "p_", "github_" + "pat_", "tvly-" + "dev-", "s" + "k-")
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:"
    + "|".join(re.escape(value) for value in SECRET_PREFIXES)
    + r")[A-Za-z0-9_-]{16,}"
)
PRIVILEGED = frozenset(
    {
        "answer",
        "answer_key",
        "category",
        "evaluator",
        "gold",
        "ground_truth",
        "question_type",
        "reward",
        "score",
        "split",
        "task_category",
    }
)


def payload_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()
    ).hexdigest()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=20,
    ).stdout.strip()


def _ordinary(relative: Path) -> Path:
    path = ROOT / relative
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(ROOT.resolve())
    ):
        raise RuntimeError(f"V2.47.31 expected repository file: {relative}")
    return path


def _manifest() -> dict[str, str]:
    output = {}
    for relative in SOURCES:
        raw = _ordinary(relative).read_bytes()
        if SECRET.search(raw.decode("utf-8", errors="ignore")):
            raise RuntimeError("V2.47.31 credential literal found")
        output[str(relative)] = hashlib.sha256(raw).hexdigest()
    return output


def ast_findings() -> tuple[list[str], list[str]]:
    accesses = []
    imports = []
    for relative in (SOURCES[0], TEST_FILE):
        tree = ast.parse(_ordinary(relative).read_text(encoding="utf-8"))
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
                key = node.args[0].value
            elif isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
                key = node.slice.value if isinstance(node.slice.value, str) else None
            if key is not None and key.casefold() in PRIVILEGED:
                accesses.append(f"{relative}:{node.lineno}:{key}")
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or "", *(alias.name for alias in node.names)]
            for name in names:
                if any(marker in name.casefold() for marker in ("official_eval", "evaluator_mapping", "finalize_v24")):
                    imports.append(f"{relative}:{node.lineno}:{name}")
    return sorted(accesses), sorted(imports)


def _run_tests() -> tuple[bool, int, str]:
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
            TEST_FILE.name,
            "-v",
        ],
        cwd=ROOT,
        env={
            "HOME": os.environ.get("HOME", str(Path.home())),
            "USER": os.environ.get("USER", "azureuser"),
            "LOGNAME": os.environ.get("LOGNAME", "azureuser"),
            "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
            "PYTHONSAFEPATH": "1",
        },
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=120,
        check=False,
    )
    match = re.search(r"Ran (\d+) tests?", completed.stdout)
    observed = int(match.group(1)) if match else 0
    return completed.returncode == 0 and observed == EXPECTED_TESTS, observed, completed.stdout


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    private_ror, private_wb, public = builder._validate_parents()
    del private_ror, private_wb
    surfaces = builder.build_surfaces()
    manifest = _manifest()
    tests_passed, observed, output = _run_tests()
    accesses, imports = ast_findings()
    findings = []
    if not tests_passed:
        findings.append("surface_tests_failed")
    if accesses or imports:
        findings.append("label_blind_ast_failed")
    if set(surfaces) != set(builder.SURFACES):
        findings.append("surface_set_drifted")
    if any((ROOT / path).exists() or (ROOT / path).is_symlink() for path in builder.SURFACES):
        findings.append("future_surface_not_pristine")
    if _git("status", "--porcelain") or _git("rev-parse", "HEAD") != _git(
        "rev-parse", "target/main"
    ):
        findings.append("repository_not_clean_pushed_head")
    value = {
        "artifact_version": 1,
        "role": "v24731_dual_namespace_surface_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "population_design_sha256": sha256(ROOT / design.OUTPUT),
        "population_design_payload_sha256": public["design_payload_sha256"],
        "dependency_manifest": manifest,
        "dependency_manifest_sha256": payload_sha256(manifest),
        "tests": {
            "passed": tests_passed,
            "observed": observed,
            "expected": EXPECTED_TESTS,
            "output_sha256": hashlib.sha256(output.encode()).hexdigest(),
        },
        "label_blind_audit": {
            "accesses": accesses,
            "evaluator_imports": imports,
            "passed": not accesses and not imports,
        },
        "surface_hashes_before_publication": {
            str(path): hashlib.sha256(text.encode()).hexdigest()
            for path, text in surfaces.items()
        },
        "source_policy": {
            "benchmark_manifest_question_prediction_mapping_gold_category_question_type_split_evaluator_score_reward_read_by_forward_surface": False,
            "network_model_search_benchmark_forward_or_evaluator_called": False,
            "credential_read_hashed_persisted_or_emitted": False,
            "private_record_id_value_or_provenance_present_in_visible_contract": False,
        },
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "one_surface_publication": not findings,
            "reachability_protocol_design": not findings,
            "forward_launch": False,
            "evaluator_execution": False,
            "benchmark_dev64_or_exact220": False,
            "leaderboard_or_sota": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    validate_audit(value)
    return value


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    manifest = copied.get("dependency_manifest")
    tests = copied.get("tests", {})
    findings = copied.get("findings")
    valid = copied.get("audit_valid")
    unsigned = dict(copied)
    seal = unsigned.pop("audit_payload_sha256", None)
    if (
        copied.get("role") != "v24731_dual_namespace_surface_build_audit"
        or copied.get("population_design_sha256") != sha256(ROOT / design.OUTPUT)
        or not isinstance(manifest, Mapping)
        or dict(manifest) != _manifest()
        or copied.get("dependency_manifest_sha256") != payload_sha256(manifest)
        or tests.get("passed") is not True
        or tests.get("observed") != EXPECTED_TESTS
        or tests.get("expected") != EXPECTED_TESTS
        or copied.get("label_blind_audit")
        != {"accesses": [], "evaluator_imports": [], "passed": True}
        or any(copied.get("source_policy", {}).values())
        or not isinstance(findings, list)
        or valid is not (findings == [])
        or copied.get("authorization")
        != {
            "one_surface_publication": bool(valid),
            "reachability_protocol_design": bool(valid),
            "forward_launch": False,
            "evaluator_execution": False,
            "benchmark_dev64_or_exact220": False,
            "leaderboard_or_sota": False,
        }
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.47.31 surface build audit drifted")
    return copied


def _publish(path: Path, value: Mapping[str, Any]) -> None:
    target = ROOT / path
    if target.exists() or target.is_symlink():
        raise FileExistsError(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def main() -> None:
    _publish(OUTPUT, build_audit())


if __name__ == "__main__":
    main()
