#!/usr/bin/env python3
"""Build audit for executable append-only V2.46.94 World Bank surfaces."""

from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
import time
import types
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24320_forward_contract import payload_sha256  # noqa: E402
from scripts import audit_v24495_targeted_conversion_projection_build as common  # noqa: E402
from scripts import build_v24694_worldbank_surfaces as builder  # noqa: E402


DATE = "20260806"
AUDIT = builder.AUTHORIZATION
SOURCES = (
    builder.QUARANTINE,
    builder.predecessor.design.PRIVATE,
    builder.predecessor.design.OUTPUT,
    Path("scripts/design_v24688_worldbank_population.py"),
    Path("scripts/design_v24690_worldbank_population_capacity_repair.py"),
    Path("scripts/build_v24691_worldbank_surfaces.py"),
    Path("tests/test_build_v24691_worldbank_surfaces.py"),
    Path("scripts/build_v24694_worldbank_surfaces.py"),
    Path("tests/test_build_v24694_worldbank_surfaces.py"),
    Path("scripts/audit_v24695_worldbank_surface_repair_build.py"),
    Path("tests/test_audit_v24695_worldbank_surface_repair_build.py"),
)
TEST_SUITES = (
    (Path("tests/test_v24686_worldbank_target_value_runtime.py"), 10, 120),
    (Path("tests/test_build_v24691_worldbank_surfaces.py"), 6, 180),
    (Path("tests/test_build_v24694_worldbank_surfaces.py"), 6, 180),
    (Path("tests/test_audit_v24695_worldbank_surface_repair_build.py"), 6, 120),
)
EXPECTED_TEST_COUNT = 28


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value); seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def _run_test(path: Path, timeout: int) -> tuple[bool, int]:
    completed = subprocess.run(
        [str(ROOT / ".venv-eval/bin/python"), "-I", "-B", "-m", "unittest",
         "discover", "-s", "tests", "-p", path.name],
        cwd=ROOT,
        env={"HOME": os.environ.get("HOME", str(Path.home())),
             "USER": os.environ.get("USER", "azureuser"),
             "LOGNAME": os.environ.get("LOGNAME", "azureuser"),
             "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
             "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1",
             "PYTHONSAFEPATH": "1"},
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, timeout=timeout, check=False,
    )
    match = re.search(r"Ran (\d+) tests?", completed.stdout)
    return completed.returncode == 0, int(match.group(1)) if match else 0


def _load_surfaces(surfaces: Mapping[Path, str]) -> tuple[Any, Any]:
    contract_name = "deepwide_agent.v24694_worldbank_external_contract"
    evaluator_name = "deepwide_agent.v24694_worldbank_external_evaluator"
    contract = types.ModuleType(contract_name)
    contract.__package__ = "deepwide_agent"
    contract.__file__ = str(builder.CONTRACT)
    evaluator = types.ModuleType(evaluator_name)
    evaluator.__package__ = "deepwide_agent"
    evaluator.__file__ = str(builder.EVALUATOR)
    sys.modules[contract_name] = contract
    sys.modules[evaluator_name] = evaluator
    try:
        exec(compile(surfaces[builder.CONTRACT], str(builder.CONTRACT), "exec"), contract.__dict__)
        exec(compile(surfaces[builder.EVALUATOR], str(builder.EVALUATOR), "exec"), evaluator.__dict__)
    except BaseException:
        sys.modules.pop(contract_name, None); sys.modules.pop(evaluator_name, None)
        raise
    return contract, evaluator


def _evaluator_semantics(surfaces: Mapping[Path, str]) -> dict[str, Any]:
    contract, evaluator = _load_surfaces(surfaces)
    try:
        gold = evaluator.gold_rows(surfaces[builder.GOLD])
        provenance = json.loads(surfaces[builder.PROVENANCE])
        unsigned = dict(provenance)
        seal = unsigned.pop("provenance_payload_sha256", None)
        if seal != payload_sha256(unsigned):
            raise RuntimeError("V2.46.95 provenance seal drifted")

        def table(rows: list[Mapping[str, str]], *, wrong: bool = False) -> str:
            values = []
            for index, row in enumerate(rows):
                first = row[evaluator.COLUMNS[1]]
                if wrong and index == 0: first = "999999999"
                values.append([row["Country"], first, row[evaluator.COLUMNS[2]]])
            return (
                "```markdown\n| " + " | ".join(evaluator.COLUMNS) + " |\n| "
                + " | ".join("---" for _ in evaluator.COLUMNS) + " |\n"
                + "\n".join("| " + " | ".join(row) + " |" for row in values)
                + "\n```"
            )

        first_task = contract.visible_task(1)["opaque_id"]
        first_rows = [row for row in gold if row["opaque_id"] == first_task]
        exact = evaluator.evaluate_prediction(table(first_rows), first_rows)
        wrong = evaluator.evaluate_prediction(table(first_rows, wrong=True), first_rows)
        predictions = []
        for task in contract.task_vector():
            rows = [row for row in gold if row["opaque_id"] == task["opaque_id"]]
            predictions.append({
                "opaque_id": task["opaque_id"],
                "predictions": {"frozen_parser": "broken", "expanded_parser": "broken",
                                "target_value": table(rows)},
            })
        gate = evaluator.evaluate_frozen_rows(predictions, gold)
        return {
            "contract_task_count": len(contract.task_vector()),
            "gold_row_count": len(gold),
            "provenance_record_count": len(provenance["records"]),
            "exact_table_accepted": exact["exact_table_success"] == 1,
            "wrong_value_rejected": wrong["exact_table_success"] == 0,
            "synthetic_complete_gate_passed": gate["gate_passed"] is True,
            "synthetic_exact_gain": gate["target_value_minus_expanded"][
                "exact_table_successes"
            ],
        }
    finally:
        sys.modules.pop(contract.__name__, None)
        sys.modules.pop(evaluator.__name__, None)


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    manifest = {str(path): common._sha256(path) for path in SOURCES}
    suites = []
    for path, expected, timeout in TEST_SUITES:
        passed, observed = _run_test(path, timeout)
        suites.append({"path": str(path), "expected_test_count": expected,
                       "observed_test_count": observed,
                       "passed": passed and observed == expected})
    test_count = sum(item["observed_test_count"] for item in suites)
    secret_hits = [str(path) for path in SOURCES if common.SECRET.search(
        common._ordinary(path).read_text(encoding="utf-8"))]
    head = common._git("rev-parse", "HEAD"); remote = common._git("rev-parse", "target/main")
    clean = common._git("status", "--porcelain") == ""
    tracked = all(common._tracked(path) for path in SOURCES)
    watchers = [{"pid": pid, "start_ticks": ticks, "marker": marker,
                 "identity_valid": common._watcher(pid, ticks, marker)}
                for pid, ticks, marker in common.EXPECTED_WATCHERS]
    lease_inactive = common._lease_inactive()
    pristine = all(not (ROOT / path).exists() and not (ROOT / path).is_symlink()
                   for path in (builder.CONTRACT, builder.EVALUATOR, builder.GOLD, builder.PROVENANCE))
    quarantine_valid = builder._quarantine_valid()
    surfaces = builder.build_surfaces() if quarantine_valid else {}
    contract_source = surfaces.get(builder.CONTRACT, "")
    accesses, imports = _contract_findings(contract_source)
    try:
        semantics = _evaluator_semantics(surfaces) if surfaces else {}
    except BaseException as error:
        semantics = {"failure_type": type(error).__name__}
    private = _read_json(ROOT / builder.predecessor.design.PRIVATE)
    private_literals = [
        str(value[field])
        for group in private["groups"] for record in group for value in record["values"]
        for field in ("value", "response_sha256")
    ]
    forward_clean = (
        "evaluation/" not in contract_source
        and "external_evaluator" not in contract_source
        and not any(literal in contract_source for literal in private_literals)
    )
    semantics_valid = semantics == {
        "contract_task_count": 12, "gold_row_count": 48,
        "provenance_record_count": 96, "exact_table_accepted": True,
        "wrong_value_rejected": True, "synthetic_complete_gate_passed": True,
        "synthetic_exact_gain": 12,
    }
    findings: list[str] = []
    if head != remote: findings.append("v24695_source_commit_not_pushed")
    if not clean: findings.append("v24695_source_worktree_not_clean")
    if not tracked: findings.append("v24695_source_not_tracked")
    if not quarantine_valid: findings.append("v24693_quarantine_drifted")
    if not forward_clean: findings.append("v24694_forward_separation_drifted")
    if not semantics_valid: findings.append("v24694_evaluator_semantics_failed")
    if any(not item["passed"] for item in suites) or test_count != EXPECTED_TEST_COUNT:
        findings.append("v24686_v24694_v24695_regression_failed")
    if accesses or imports: findings.append("privileged_or_evaluator_forward_access")
    if secret_hits: findings.append("credential_literal_in_surface_repair")
    if any(not item["identity_valid"] for item in watchers): findings.append("protected_watcher_identity_drifted")
    if not lease_inactive: findings.append("shared_api_lease_active")
    if not pristine: findings.append("v24694_surface_not_pristine")
    value = {
        "artifact_version": 1, "role": "v24695_worldbank_surface_repair_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "repair": {"invalid_predecessor": "v24691", "new_surface_namespace": "v24694",
                   "only_semantic_repair": "generated_evaluator_double_braces_to_single_braces",
                   "quarantine_valid": quarantine_valid, "forward_separation_valid": forward_clean,
                   "evaluator_semantics": semantics, "evaluator_semantics_valid": semantics_valid},
        "source_manifest": manifest, "source_manifest_sha256": payload_sha256(manifest),
        "git": {"head": head, "target_main": remote, "head_equals_target_main": head == remote,
                "worktree_clean": clean, "all_sources_tracked": tracked},
        "tests": {"suites": suites, "test_count": test_count,
                  "passed": all(item["passed"] for item in suites) and test_count == EXPECTED_TEST_COUNT,
                  "network_model_search_worldbank_benchmark_or_prediction_evaluator_called": False},
        "runtime_state": {"protected_watchers": watchers,
                          "protected_watchers_unchanged": all(item["identity_valid"] for item in watchers),
                          "shared_api_lease_inactive": lease_inactive, "surface_pristine": pristine,
                          "external_effect_performed_by_audit": False},
        "credential_literal_hits": sorted(secret_hits), "findings": findings,
        "audit_valid": not findings,
        "authorization": {"one_repaired_surface_publication": not findings,
                          "external_protocol_design": False, "preactivation_or_launch": False,
                          "evaluator_execution_on_predictions": False, "dev64_or_exact220": False,
                          "leaderboard_or_sota": False},
    }
    value["audit_payload_sha256"] = payload_sha256(value); return value


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict): raise RuntimeError("V2.46.95 expected object")
    return value


def _contract_findings(source: str) -> tuple[list[str], list[str]]:
    tree = ast.parse(source)
    privileged = {
        "benchmark_question_type", "question_type", "task_category", "category",
        "split", "ground_truth", "gold", "answer_key", "mapping", "evaluator",
        "score", "reward",
    }
    accesses: list[str] = []
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
            key = node.args[0].value
        elif (
            isinstance(node, ast.Subscript)
            and isinstance(node.slice, ast.Constant)
            and isinstance(node.slice.value, str)
        ):
            key = node.slice.value
        if key is not None and key.casefold() in privileged:
            accesses.append(f"generated_contract:{node.lineno}:{key}")
        names = []
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            names = [node.module or "", *(alias.name for alias in node.names)]
        for name in names:
            if "evaluator" in name.casefold() or "gold" in name.casefold():
                imports.append(f"generated_contract:{node.lineno}:{name}")
    return sorted(accesses), sorted(imports)


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    if (
        copied.get("role") != "v24695_worldbank_surface_repair_build_audit"
        or copied.get("audit_valid") is not True or copied.get("findings") != []
        or copied.get("repair", {}).get("quarantine_valid") is not True
        or copied.get("repair", {}).get("forward_separation_valid") is not True
        or copied.get("repair", {}).get("evaluator_semantics_valid") is not True
        or copied.get("tests", {}).get("passed") is not True
        or copied.get("tests", {}).get("test_count") != EXPECTED_TEST_COUNT
        or copied.get("runtime_state", {}).get("protected_watchers_unchanged") is not True
        or copied.get("runtime_state", {}).get("shared_api_lease_inactive") is not True
        or copied.get("runtime_state", {}).get("surface_pristine") is not True
        or copied.get("authorization") != {"one_repaired_surface_publication": True,
            "external_protocol_design": False, "preactivation_or_launch": False,
            "evaluator_execution_on_predictions": False, "dev64_or_exact220": False,
            "leaderboard_or_sota": False}
        or not _sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.46.95 surface repair audit drifted")
    return copied


def publish_new(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink(): raise FileExistsError(path)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n"); handle.flush(); os.fsync(handle.fileno())


if __name__ == "__main__":
    result = build_audit(); validate_audit(result); publish_new(ROOT / AUDIT, result)
    print(json.dumps({"path": str(AUDIT), "audit_valid": result["audit_valid"],
                      "findings": result["findings"], "test_count": result["tests"]["test_count"]},
                     sort_keys=True))
