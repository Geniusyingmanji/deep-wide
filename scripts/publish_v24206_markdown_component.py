#!/usr/bin/env python3
"""Publish one selected-baseline-bound Markdown component after V2.42.04.

The publisher is repo-local and label-blind.  It reconstructs frozen baseline
bytes from V2.42.01, rebases only the historical Markdown production hooks,
extends baseline test identity assertions to the unique successor identity,
and runs the complete selected-baseline regression plus Markdown tests.  It
does not publish branch scope, search-yield, entropy, a joint package, a
package gate, or any benchmark execution.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24200_successor import payload_sha256  # noqa: E402
from deepwide_agent.v24206_markdown_publisher import (  # noqa: E402
    build_markdown_publication_order,
)
from scripts import build_v24102_markdown_candidate as markdown  # noqa: E402
from scripts.audit_v24205_markdown_rebase_feasibility import (  # noqa: E402
    _hook_counts,
    rebase_markdown_production,
    runtime_identity,
)
from scripts.build_v2410_rank_slot_candidate import (  # noqa: E402
    candidate_regular_file_manifest,
)
from scripts.preregister_v2408_combined_fasttrack import (  # noqa: E402
    _local_execution_closure,
)
from scripts.replay_v24201_repo_local_candidate_dag import (  # noqa: E402
    PUBLICATIONS,
    build_replay,
    file_sha256,
    manifest_sha256,
    publication_manifest,
    read_publication,
    text_manifest,
)


OUTPUT = Path(
    "results/v24206_selected_markdown_component_publication_v1_20260731.json"
)
SELECTED_WORK_ORDER = Path(
    "results/v24204_selected_postdecision_work_order_v1_20260731.json"
)
PARENT_PROTOCOL = Path(
    "results/v24204_postdecision_work_order_preregistration_v1_20260731.json"
)
PARENT_PROTOCOL_SHA256 = (
    "aedd97c0ccbfaa3e18f157aa56e0d0969c39fc28b0903cbe2260a3db1172d5e4"
)
CANDIDATE_ROOT = ROOT / "outputs/v24206_selected_markdown_candidate_v1_20260731"
TARGET_SUFFIX = "-selected-markdown-rank-slot"
TARGET_SCHEMA = {"schema76": 78, "schema77": 79}
PARENT_EXPECTED_TESTS = {"schema76": 96, "schema77": 105}
# The historical pure module contributes 16 tests and the generated integrated
# source contributes 6, so each selected baseline gains exactly 22 tests.
EXPECTED_TESTS = {"schema76": 118, "schema77": 127}
SECRET_LITERAL = re.compile(rb"(?:ghp_|github_pat_|tvly-|sk-)[A-Za-z0-9_-]{16,}")
OPAQUE_ID = re.compile(rb"task_[0-9a-f]{24}")


def read_object(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("V2.42.06 expected an ordinary JSON file")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.42.06 expected one JSON object")
    return value


def publish_new(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def load_selected_work_order(
    root: Path = ROOT, path: Path = SELECTED_WORK_ORDER
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Validate the terminal V2.42.04 receipt and return its work order."""

    target = path if path.is_absolute() else root / path
    value = read_object(target)
    unsigned = dict(value)
    seal = unsigned.pop("selected_payload_sha256", None)
    work_order = value.get("selected_work_order")
    false_fields = (
        "candidate_code_built_merged_or_materialized",
        "component_implementation_publisher_invoked",
        "package_gate_evaluated_or_launched",
        "shared_api_lease_acquired",
        "network_model_search_fetch_evaluator_or_api_called",
        "mapping_gold_category_question_type_evaluator_score_or_reward_read",
        "benchmark_forward_or_full220_launch_allowed",
        "leaderboard_submission_or_sota_claim",
    )
    if (
        target.resolve(strict=False) != (root / SELECTED_WORK_ORDER).resolve(strict=False)
        or value.get("role") != "v24204_selected_postdecision_work_order"
        or value.get("label_blind") is not True
        or value.get("protocol", {}).get("path") != str(PARENT_PROTOCOL)
        or value.get("protocol", {}).get("sha256") != PARENT_PROTOCOL_SHA256
        or not isinstance(work_order, dict)
        or any(value.get(field) is not False for field in false_fields)
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.42.06 selected work-order receipt drifted")
    order = build_markdown_publication_order(work_order)
    if order["decision_sha256"] != value.get("parent_decision", {}).get(
        "decision_payload_sha256"
    ):
        raise RuntimeError("V2.42.06 decision binding drifted")
    return value, order


def _line_offsets(source: str) -> list[int]:
    offsets = [0]
    for line in source.splitlines(keepends=True):
        offsets.append(offsets[-1] + len(line))
    return offsets


def extend_identity_assertions(
    source: str, *, target_version: str, target_schema: int
) -> tuple[str, int]:
    """Append one exact successor identity to existing identity assertions.

    Frozen integration tests use both bare ``assert`` statements and the
    ``unittest`` identity assertions ``assertTrue``, ``assertEqual``, and
    ``assertIn``.  Rewriting the complete assertion predicate, rather than
    independently extending version suffixes and schema sets, keeps the new
    version/schema pair atomic.
    """

    tree = ast.parse(source)
    module_names = {
        node.id for node in ast.walk(tree) if isinstance(node, ast.Name)
    }
    replacements: list[tuple[int, int, str]] = []
    offsets = _line_offsets(source)
    exact = (
        "PIPELINE_VERSION == "
        + repr(target_version)
        + " and STATE_SCHEMA_VERSION == "
        + str(target_schema)
    )
    for node in ast.walk(tree):
        predicate: ast.AST | None = None
        replacement: str | None = None
        if isinstance(node, ast.Assert):
            predicate = node.test
            message = "" if node.msg is None else ", " + ast.unparse(node.msg)
            replacement = (
                "assert (" + ast.unparse(predicate) + ") or (" + exact + ")" + message
            )
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "self"
        ):
            method = node.func.attr
            required_args = {"assertTrue": 1, "assertEqual": 2, "assertIn": 2}
            required = required_args.get(method)
            if required is None or len(node.args) < required:
                continue
            if method == "assertTrue":
                predicate = node.args[0]
            elif method == "assertEqual":
                predicate = ast.Compare(
                    left=node.args[0], ops=[ast.Eq()], comparators=[node.args[1]]
                )
            else:
                predicate = ast.Compare(
                    left=node.args[0], ops=[ast.In()], comparators=[node.args[1]]
                )
            extras = [ast.unparse(item) for item in node.args[required:]]
            extras.extend(
                (keyword.arg + "=" if keyword.arg is not None else "**")
                + ast.unparse(keyword.value)
                for keyword in node.keywords
            )
            suffix = "" if not extras else ", " + ", ".join(extras)
            replacement = (
                "self.assertTrue(("
                + ast.unparse(predicate)
                + ") or ("
                + exact
                + ")"
                + suffix
                + ")"
            )
        if predicate is None or replacement is None:
            continue
        names = {
            child.id for child in ast.walk(predicate) if isinstance(child, ast.Name)
        }
        if not names.intersection({"PIPELINE_VERSION", "STATE_SCHEMA_VERSION"}):
            continue
        if not {"PIPELINE_VERSION", "STATE_SCHEMA_VERSION"}.issubset(module_names):
            raise RuntimeError("V2.42.06 identity assertion lacks both constants")
        start = offsets[node.lineno - 1] + node.col_offset
        end = offsets[node.end_lineno - 1] + node.end_col_offset
        replacements.append((start, end, replacement))
    for start, end, replacement in sorted(replacements, reverse=True):
        source = source[:start] + replacement + source[end:]
    ast.parse(source)
    return source, len(replacements)


def _target_identity(baseline: str, files: Mapping[str, str]) -> tuple[int, str]:
    parent_schema, parent_version = runtime_identity(
        files["src/deepwide_agent/runtime.py"]
    )
    if parent_schema != int(baseline.removeprefix("schema")):
        raise RuntimeError("V2.42.06 baseline runtime identity drifted")
    return TARGET_SCHEMA[baseline], parent_version + TARGET_SUFFIX


def _integrated_source(target_version: str, target_schema: int) -> str:
    source = markdown.INTEGRATED_TEST_SOURCE
    source = source.replace(markdown.TARGET_PIPELINE_VERSION, target_version)
    source = source.replace(
        f"self.assertEqual(STATE_SCHEMA_VERSION, {markdown.TARGET_STATE_SCHEMA_VERSION})",
        f"self.assertEqual(STATE_SCHEMA_VERSION, {target_schema})",
    )
    ast.parse(source)
    return source


def baseline_test_modules(baseline: str) -> tuple[str, ...]:
    publication = read_publication(PUBLICATIONS[baseline])
    tests = publication.get("integrated_tests") or {}
    modules = tests.get("modules")
    if (
        tests.get("status") != "pass"
        or tests.get("tests_run") != PARENT_EXPECTED_TESTS[baseline]
        or not isinstance(modules, list)
        or not all(isinstance(item, str) for item in modules)
    ):
        raise RuntimeError("V2.42.06 parent regression receipt drifted")
    return tuple(modules)


def build_mainline_candidate_files(
    baseline: str,
) -> tuple[dict[str, str], dict[str, Any]]:
    """Build schema76/77 + Markdown entirely in memory."""

    if baseline not in TARGET_SCHEMA:
        raise RuntimeError("V2.42.06 mainline baseline is unsupported")
    replay, maps = build_replay()
    if replay.get("all_stage_file_maps_byte_exact_to_frozen_publications") is not True:
        raise RuntimeError("V2.42.06 baseline replay failed")
    before = maps[baseline]
    target_schema, target_version = _target_identity(baseline, before)
    files = rebase_markdown_production(
        before,
        target_schema=target_schema,
        target_suffix=TARGET_SUFFIX,
    )
    files[markdown.PURE_TEST] = (ROOT / markdown.PURE_TEST).read_text(
        encoding="utf-8"
    )
    files[markdown.INTEGRATED_TEST] = _integrated_source(
        target_version, target_schema
    )
    guard_files: dict[str, int] = {}
    for relative in sorted(before):
        if not relative.startswith("tests/") or not relative.endswith(".py"):
            continue
        patched, count = extend_identity_assertions(
            files[relative],
            target_version=target_version,
            target_schema=target_schema,
        )
        if count:
            files[relative] = patched
            guard_files[relative] = count
    for relative, source in files.items():
        if relative.endswith(".py"):
            ast.parse(source, filename=relative)
    if runtime_identity(files["src/deepwide_agent/runtime.py"]) != (
        target_schema,
        target_version,
    ):
        raise RuntimeError("V2.42.06 target runtime identity drifted")
    hooks = _hook_counts(files["src/deepwide_agent/runtime.py"])
    if (
        hooks["markdown_import"] != 1
        or hooks["scope_import"] != 1
        or hooks["scope_fallback_call"] != 1
        or hooks["scope_audit_write"] != 1
    ):
        raise RuntimeError("V2.42.06 hook composition drifted")
    if not guard_files:
        raise RuntimeError("V2.42.06 no baseline identity guard was rebased")
    manifest = text_manifest(files)
    changed = sorted(
        relative
        for relative in set(before) | set(files)
        if before.get(relative) != files.get(relative)
    )
    required = {
        "src/deepwide_agent/runtime.py",
        "scripts/preflight_deepwide.py",
        markdown.PURE_MODULE,
        markdown.PURE_TEST,
        markdown.INTEGRATED_TEST,
        *guard_files,
    }
    if set(changed) != required or len(files) != len(before) + 3:
        raise RuntimeError("V2.42.06 candidate delta file set drifted")
    report: dict[str, Any] = {
        "baseline_name": baseline,
        "baseline_publication": {
            "path": PUBLICATIONS[baseline].path,
            "sha256": PUBLICATIONS[baseline].sha256,
            "manifest_sha256": manifest_sha256(text_manifest(before)),
        },
        "target_pipeline_version": target_version,
        "target_state_schema_version": target_schema,
        "delta_files": changed,
        "identity_guard_assertion_counts": guard_files,
        "candidate_regular_file_count": len(files),
        "candidate_regular_file_manifest": manifest,
        "candidate_regular_file_manifest_sha256": manifest_sha256(manifest),
        "mainline_scope_hook_preserved_exactly_once": True,
        "branch_scope_patch_or_alias_applied": False,
        "search_yield_or_entropy_implemented": False,
        "mapping_gold_category_question_type_evaluator_score_prediction_or_outcome_read": False,
        "runtime_task_state_or_result_read": False,
        "credential_or_network_read": False,
        "network_model_search_fetch_evaluator_or_api_called": False,
        "joint_package_built_or_materialized": False,
        "package_gate_evaluated_or_launched": False,
        "benchmark_forward_or_full220_launch_allowed": False,
    }
    return files, report


def _write_candidate(root: Path, files: Mapping[str, str]) -> None:
    for relative, source in files.items():
        target = (root / relative).resolve(strict=False)
        if not target.is_relative_to(root):
            raise RuntimeError("V2.42.06 candidate path escaped root")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(source, encoding="utf-8")


def run_integrated_tests(candidate: Path, baseline: str) -> dict[str, Any]:
    modules = baseline_test_modules(baseline) + (
        "tests.test_v24102_markdown_rank_slot",
        "tests.test_v24102_integrated_markdown_rank_slot",
    )
    environment = {
        "HOME": str(candidate / ".sandbox-home"),
        "USER": "v24206-regression",
        "LOGNAME": "v24206-regression",
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "PYTHONSAFEPATH": "1",
    }
    runner = (
        "import sys,unittest; sys.path.insert(0,'.'); "
        f"names={list(modules)!r}; "
        "suite=unittest.defaultTestLoader.loadTestsFromNames(names); "
        "result=unittest.TextTestRunner(verbosity=2).run(suite); "
        "raise SystemExit(not result.wasSuccessful())"
    )
    completed = subprocess.run(
        [str(candidate / ".venv-eval/bin/python"), "-I", "-B", "-c", runner],
        cwd=candidate,
        env=environment,
        text=True,
        capture_output=True,
        timeout=300,
        check=False,
    )
    output = completed.stdout + completed.stderr
    counts = re.findall(r"^Ran (\d+) tests? in ", output, flags=re.MULTILINE)
    tests_run = int(counts[-1]) if counts else -1
    if (
        completed.returncode != 0
        or tests_run != EXPECTED_TESTS[baseline]
        or not re.search(r"^OK\s*$", output, flags=re.MULTILINE)
    ):
        raise RuntimeError("V2.42.06 integrated tests failed:\n" + output[-30000:])
    return {
        "status": "pass",
        "modules": list(modules),
        "tests_run": tests_run,
        "returncode": completed.returncode,
        "output_sha256": hashlib.sha256(output.encode()).hexdigest(),
        "scrubbed_environment": True,
        "network_or_api_required": False,
    }


def materialize_mainline_candidate(
    baseline: str, candidate: Path = CANDIDATE_ROOT
) -> dict[str, Any]:
    candidate = candidate.resolve(strict=False)
    if candidate.exists() or candidate.is_symlink():
        raise FileExistsError(candidate)
    files, report = build_mainline_candidate_files(baseline)
    candidate.mkdir(parents=True, exist_ok=False)
    try:
        environment = ROOT / ".venv-eval"
        (candidate / ".venv-eval").symlink_to(
            environment.resolve(), target_is_directory=True
        )
        _write_candidate(candidate, files)
        live = candidate_regular_file_manifest(candidate, source_only=True)
        if live != report["candidate_regular_file_manifest"]:
            raise RuntimeError("V2.42.06 materialized source drifted")
        tests = run_integrated_tests(candidate, baseline)
        if candidate_regular_file_manifest(candidate, source_only=True) != live:
            raise RuntimeError("V2.42.06 tests mutated candidate source")
        closure = set(
            _local_execution_closure(
                candidate,
                (
                    "scripts/preflight_deepwide.py",
                    "scripts/launch_frozen_deepwide.py",
                    "scripts/run_deepwide_agent.py",
                ),
            )
        )
        forward = {relative: live[relative] for relative in sorted(closure)}
        if markdown.PURE_MODULE not in closure or not closure.issubset(live):
            raise RuntimeError("V2.42.06 forward closure is incomplete")
        return {
            **report,
            "candidate_root": str(candidate),
            "candidate_disk_hashes_verified": True,
            "candidate_regular_file_set_exact": True,
            "candidate_forward_execution_closure_exact": True,
            "candidate_forward_manifest": forward,
            "candidate_forward_manifest_sha256": manifest_sha256(forward),
            "integrated_tests": tests,
            "execution_environment": {
                "path": str(candidate / ".venv-eval"),
                "symlink_target": str(environment.resolve()),
            },
        }
    except BaseException:
        shutil.rmtree(candidate, ignore_errors=True)
        raise


def historical_p12_binding() -> dict[str, Any]:
    replay, maps = build_replay()
    publication = read_publication(PUBLICATIONS["schema69"])
    manifest = text_manifest(maps["schema69"])
    if (
        replay.get("all_stage_file_maps_byte_exact_to_frozen_publications") is not True
        or manifest != publication_manifest(publication)
    ):
        raise RuntimeError("V2.42.06 historical Markdown bytes drifted")
    return {
        "historical_publication": {
            "path": PUBLICATIONS["schema69"].path,
            "sha256": PUBLICATIONS["schema69"].sha256,
        },
        "target_pipeline_version": publication["target_pipeline_version"],
        "target_state_schema_version": publication["target_state_schema_version"],
        "candidate_regular_file_count": len(manifest),
        "candidate_regular_file_manifest": manifest,
        "candidate_regular_file_manifest_sha256": manifest_sha256(manifest),
        "historical_bytes_byte_exact": True,
        "candidate_root_created": False,
        "integrated_tests_reused_from_historical_publication": publication[
            "integrated_tests"
        ],
    }


def build_selected_publication(
    selected_receipt: Mapping[str, Any],
    order: Mapping[str, Any],
    *,
    candidate: Path = CANDIDATE_ROOT,
) -> dict[str, Any]:
    mode = order["publication_mode"]
    component: dict[str, Any] | None
    if mode == "no_op_component_absent":
        component = None
    elif mode == "bind_historical_schema69_bytes":
        component = historical_p12_binding()
    elif mode == "materialize_selected_baseline_rebase":
        component = materialize_mainline_candidate(order["baseline_name"], candidate)
    else:
        raise RuntimeError("V2.42.06 publication mode is unsupported")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24206_selected_markdown_component_publication",
        "label_blind": True,
        "selected_work_order": {
            "path": str(SELECTED_WORK_ORDER),
            "sha256": file_sha256(ROOT / SELECTED_WORK_ORDER),
            "selected_payload_sha256": selected_receipt[
                "selected_payload_sha256"
            ],
            "decision_sha256": order["decision_sha256"],
        },
        "publication_order": dict(order),
        "component_publication": component,
        "markdown_component_published": component is not None,
        "selected_baseline_bound": component is not None,
        "unowned_components_preserved_as_blockers": list(
            order["unowned_components_preserved_as_blockers"]
        ),
        "branch_scope_patch_or_alias_applied": False,
        "search_yield_or_entropy_implemented": False,
        "joint_package_built_or_materialized": False,
        "package_gate_evaluated_or_launched": False,
        "shared_api_lease_acquired": False,
        "network_model_search_fetch_evaluator_or_api_called": False,
        "benchmark_question_answer_evidence_prediction_or_url_parsed_or_emitted": False,
        "mapping_gold_category_question_type_evaluator_score_or_reward_read": False,
        "credential_value_read_persisted_hashed_or_emitted": False,
        "process_signal_restart_resume_rerun_skip_or_selective_retry": False,
        "benchmark_forward_or_full220_launch_allowed": False,
        "leaderboard_submission_or_sota_claim": False,
    }
    encoded = json.dumps(value, sort_keys=True).encode()
    if SECRET_LITERAL.search(encoded) or OPAQUE_ID.search(encoded):
        raise RuntimeError("V2.42.06 publication exposes forbidden content")
    value["publication_payload_sha256"] = payload_sha256(value)
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selected-work-order", default=str(SELECTED_WORK_ORDER))
    parser.add_argument("--candidate-root", default=str(CANDIDATE_ROOT))
    parser.add_argument("--output", default=str(OUTPUT))
    args = parser.parse_args()
    selected = Path(args.selected_work_order)
    candidate = Path(args.candidate_root)
    output = Path(args.output)
    if (
        selected.resolve(strict=False)
        != (ROOT / SELECTED_WORK_ORDER).resolve(strict=False)
        or candidate.resolve(strict=False) != CANDIDATE_ROOT.resolve(strict=False)
        or output.resolve(strict=False) != (ROOT / OUTPUT).resolve(strict=False)
    ):
        raise RuntimeError("V2.42.06 CLI path drifted")
    receipt, order = load_selected_work_order(ROOT, selected)
    value = build_selected_publication(receipt, order, candidate=candidate)
    publish_new(output, value)
    print(json.dumps({"path": str(output), "sha256": file_sha256(output)}))


if __name__ == "__main__":
    main()
