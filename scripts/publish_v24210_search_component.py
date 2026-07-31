#!/usr/bin/env python3
"""Publish the selected search component after all frozen parents terminate.

The publisher is label-blind and reads only sealed control receipts.  A GO
materializes one deterministic, same-budget scheduler rebase; NO-GO or an
incomplete attempt retires the selected component without changing thresholds
or rerunning the experiment.  It never calls a model, search, evaluator, or
benchmark and never acquires the shared API lease.
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
from deepwide_agent.v24210_search_publisher import (  # noqa: E402
    build_search_publication_order,
)
from scripts.audit_v24205_markdown_rebase_feasibility import (  # noqa: E402
    runtime_identity,
)
from scripts.audit_v24208_search_rebase_feasibility import (  # noqa: E402
    RUNTIME_MODULE,
    RUNTIME_TEST,
    patch_search_production,
)
from scripts.build_v2410_rank_slot_candidate import (  # noqa: E402
    candidate_regular_file_manifest,
)
from scripts.preregister_v2408_combined_fasttrack import (  # noqa: E402
    _local_execution_closure,
)
from scripts.publish_v24206_markdown_component import (  # noqa: E402
    OUTPUT as MARKDOWN_PUBLICATION,
    SELECTED_WORK_ORDER,
    _write_candidate,
    extend_identity_assertions,
    load_selected_work_order,
    read_object,
)
from scripts.publish_v24207_scope_alias_component import (  # noqa: E402
    OUTPUT as SCOPE_PUBLICATION,
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


OUTPUT = Path("results/v24210_selected_search_component_publication_v1_20260731.json")
CANDIDATE_ROOT = ROOT / "outputs/v24210_selected_search_candidate_v1_20260731"
SEARCH_STATE = Path("outputs/v24180_predicate_search_yield_watcher_state_v1_20260730.json")
SEARCH_GATE = Path("results/v24180_predicate_search_yield_gate_v1_20260730.json")
SEARCH_PROTOCOL = Path("results/v24180_predicate_search_yield_preregistration_v1_20260730.json")
SEARCH_PROTOCOL_SHA256 = "1274fe4a9b7801d96dd5265443cb3f6b837edd469be3fe85bef1c3d71ebdf5e4"
V24208 = Path("results/v24208_search_rebase_feasibility_audit_v1_20260731.json")
V24208_SHA256 = "08302432416b2f88bc30b4b4507d99325a93217555abf902653e8379a9116b11"
TARGET_SUFFIX = "-predicate-fair-shared-query"
TERMINAL_SEARCH_STATUSES = {
    "complete_search_yield_go",
    "complete_search_yield_no_go",
    "terminal_incomplete_attempt_no_rerun",
}
SECRET_LITERAL = re.compile(rb"(?:ghp_|github_pat_|tvly-|sk-)[A-Za-z0-9_-]{16,}")
OPAQUE_ID = re.compile(rb"task_[0-9a-f]{24}")


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


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _ordinary(root: Path, relative: Path, digest: str | None = None) -> Path:
    if relative.is_absolute() or ".." in relative.parts:
        raise RuntimeError("V2.42.10 path is noncanonical")
    path = root / relative
    if (
        path.resolve(strict=False) != path.absolute()
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(root)
        or digest is not None
        and file_sha256(path) != digest
    ):
        raise RuntimeError(f"V2.42.10 frozen input drifted: {relative}")
    return path


def validate_search_terminal(
    root: Path = ROOT,
) -> tuple[str, dict[str, Any], dict[str, Any] | None]:
    """Validate only the immutable V2.41.80 terminal envelope and GO gate."""

    _ordinary(root, SEARCH_PROTOCOL, SEARCH_PROTOCOL_SHA256)
    state = read_object(_ordinary(root, SEARCH_STATE))
    status = state.get("status")
    common_false = (
        "mapping_gold_category_question_type_evaluator_score_prediction_or_outcome_read",
        "benchmark_forward_called",
        "resume_or_selective_rerun_used",
        "leaderboard_submission_or_sota_claim",
        "dev64_test156_or_full220_launch_allowed",
    )
    if (
        state.get("role") != "v24180_predicate_search_yield_watcher_state"
        or state.get("protocol_sha256") != SEARCH_PROTOCOL_SHA256
        or status not in TERMINAL_SEARCH_STATUSES
        or any(state.get(field) is not False for field in common_false)
        or state.get("shared_api_lease_acquired") is not False
    ):
        raise RuntimeError("V2.42.10 search terminal envelope drifted")

    gate: dict[str, Any] | None = None
    if status in {"complete_search_yield_go", "complete_search_yield_no_go"}:
        gate = read_object(_ordinary(root, SEARCH_GATE))
        expected_pass = status == "complete_search_yield_go"
        if (
            gate.get("role") != "v24180_predicate_search_yield_gate"
            or gate.get("protocol_sha256") != SEARCH_PROTOCOL_SHA256
            or gate.get("passed") is not expected_pass
            or gate.get("status")
            != ("paired_search_yield_go" if expected_pass else "paired_search_yield_no_go")
            or gate.get("authorization", {}).get(
                "shared_query_candidate_design_or_build_only"
            )
            is not expected_pass
            or gate.get("authorization", {}).get(
                "candidate_dev64_test156_or_full220_launch"
            )
            is not False
            or gate.get("authorization", {}).get("mapping_or_evaluator_read")
            is not False
            or gate.get("claims", {}).get("benchmark_score_available") is not False
            or file_sha256(root / SEARCH_GATE) != state.get("gate_result_sha256")
        ):
            raise RuntimeError("V2.42.10 search gate drifted")
    elif (root / SEARCH_GATE).exists() or (root / SEARCH_GATE).is_symlink():
        raise RuntimeError("V2.42.10 incomplete attempt unexpectedly has a gate")
    return str(status), state, gate


def load_inputs(
    root: Path = ROOT,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Bind the selected work order to terminal Markdown and scope receipts."""

    selected, _markdown_order = load_selected_work_order(root, SELECTED_WORK_ORDER)
    order = build_search_publication_order(selected["selected_work_order"])
    markdown = read_object(_ordinary(root, MARKDOWN_PUBLICATION))
    scope = read_object(_ordinary(root, SCOPE_PUBLICATION))
    markdown_false = (
        "search_yield_or_entropy_implemented",
        "joint_package_built_or_materialized",
        "package_gate_evaluated_or_launched",
        "shared_api_lease_acquired",
        "network_model_search_fetch_evaluator_or_api_called",
        "mapping_gold_category_question_type_evaluator_score_or_reward_read",
        "benchmark_forward_or_full220_launch_allowed",
        "leaderboard_submission_or_sota_claim",
    )
    scope_false = (
        "historical_scope_patch_reapplied",
        "candidate_bytes_modified_or_materialized",
        *markdown_false,
    )
    if (
        markdown.get("role") != "v24206_selected_markdown_component_publication"
        or markdown.get("label_blind") is not True
        or markdown.get("selected_work_order", {}).get("decision_sha256")
        != order["decision_sha256"]
        or any(markdown.get(field) is not False for field in markdown_false)
        or not _sealed(markdown, "publication_payload_sha256")
        or scope.get("role") != "v24207_selected_scope_alias_component_publication"
        or scope.get("label_blind") is not True
        or scope.get("selected_work_order", {}).get("decision_sha256")
        != order["decision_sha256"]
        or any(scope.get(field) is not False for field in scope_false)
        or not _sealed(scope, "publication_payload_sha256")
    ):
        raise RuntimeError("V2.42.10 selected parent publication drifted")
    if order["semantic_parent_variant"] == "selected_markdown_candidate" and not markdown.get(
        "markdown_component_published"
    ):
        raise RuntimeError("V2.42.10 selected Markdown parent is absent")
    if order["semantic_parent_variant"] == "selected_scope_candidate" and not scope.get(
        "branch_scope_component_published"
    ):
        raise RuntimeError("V2.42.10 selected scope parent is absent")
    return selected, order, markdown, scope


def selected_parent_files(
    order: Mapping[str, Any],
    markdown: Mapping[str, Any],
    scope: Mapping[str, Any],
) -> tuple[dict[str, str], dict[str, Any]]:
    """Return the byte-exact selected parent and its provenance."""

    replay, maps = build_replay()
    if replay.get("all_stage_file_maps_byte_exact_to_frozen_publications") is not True:
        raise RuntimeError("V2.42.10 repository replay failed")
    baseline = str(order["baseline_name"])
    variant = str(order["semantic_parent_variant"])
    if baseline == "p12":
        schema = {
            "selected_baseline": "schema68",
            "selected_markdown_candidate": "schema69",
            "selected_scope_candidate": "schema70",
        }[variant]
        files = dict(maps[schema])
        publication = read_publication(PUBLICATIONS[schema])
        if text_manifest(files) != publication_manifest(publication):
            raise RuntimeError("V2.42.10 historical P12 parent bytes drifted")
        provenance = {
            "kind": "historical_byte_exact_parent",
            "schema": schema,
            "publication": {
                "path": PUBLICATIONS[schema].path,
                "sha256": PUBLICATIONS[schema].sha256,
            },
            "zero_byte_scope_alias": False,
        }
        return files, provenance

    if variant == "selected_baseline":
        files = dict(maps[baseline])
        provenance = {
            "kind": "historical_byte_exact_parent",
            "schema": baseline,
            "publication": {
                "path": PUBLICATIONS[baseline].path,
                "sha256": PUBLICATIONS[baseline].sha256,
            },
            "zero_byte_scope_alias": False,
        }
        return files, provenance

    component = markdown.get("component_publication")
    if not isinstance(component, Mapping):
        raise RuntimeError("V2.42.10 selected mainline Markdown parent is absent")
    candidate = Path(str(component.get("candidate_root", "")))
    manifest = component.get("candidate_regular_file_manifest")
    if (
        not candidate.is_absolute()
        or not candidate.resolve().is_relative_to(ROOT.resolve())
        or candidate.is_symlink()
        or not candidate.is_dir()
        or not isinstance(manifest, dict)
        or not manifest
    ):
        raise RuntimeError("V2.42.10 selected mainline parent is noncanonical")
    files: dict[str, str] = {}
    for raw_relative, digest in manifest.items():
        relative = str(raw_relative)
        path = candidate / relative
        if path.is_symlink() or not path.is_file() or file_sha256(path) != digest:
            raise RuntimeError("V2.42.10 selected mainline parent bytes drifted")
        files[relative] = path.read_text(encoding="utf-8")
    if text_manifest(files) != dict(sorted(manifest.items())):
        raise RuntimeError("V2.42.10 mainline parent manifest drifted")
    zero_alias = variant == "selected_scope_candidate"
    if zero_alias:
        scope_component = scope.get("component_publication")
        if (
            not isinstance(scope_component, Mapping)
            or scope_component.get("publication_kind")
            != "zero_byte_mainline_scope_namespace_alias"
            or scope_component.get("candidate_regular_file_manifest") != manifest
            or scope_component.get("candidate_bytes_modified_or_materialized") is not False
        ):
            raise RuntimeError("V2.42.10 mainline scope alias drifted")
    return files, {
        "kind": "selected_mainline_markdown_parent",
        "candidate_root": str(candidate),
        "publication": {
            "path": str(MARKDOWN_PUBLICATION),
            "sha256": file_sha256(ROOT / MARKDOWN_PUBLICATION),
        },
        "zero_byte_scope_alias": zero_alias,
    }


def _patch_parent_identity_tests(
    before: Mapping[str, str],
    after: dict[str, str],
    *,
    target_version: str,
    target_schema: int,
) -> dict[str, int]:
    guards: dict[str, int] = {}
    for relative in sorted(before):
        if not relative.startswith("tests/") or not relative.endswith(".py"):
            continue
        patched, count = extend_identity_assertions(
            after[relative],
            target_version=target_version,
            target_schema=target_schema,
        )
        if count:
            after[relative] = patched
            guards[relative] = count
    if not guards:
        raise RuntimeError("V2.42.10 no parent identity assertion was rebased")
    return guards


def build_candidate_files(
    order: Mapping[str, Any],
    markdown: Mapping[str, Any],
    scope: Mapping[str, Any],
) -> tuple[dict[str, str], dict[str, Any]]:
    """Build one search candidate in memory from the exact semantic parent."""

    before, parent = selected_parent_files(order, markdown, scope)
    target_schema = int(order["target_state_schema_version"])
    parent_schema, parent_version = runtime_identity(
        before["src/deepwide_agent/runtime.py"]
    )
    target_version = parent_version + TARGET_SUFFIX
    after = patch_search_production(before, target_schema=target_schema)
    # V2.42.08 was an AST/build-only feasibility audit and its generated
    # integration test counted two occurrences outside the inspected method.
    # Every frozen parent has exactly three in-method plan references after
    # the hook.  Bind the executable regression to that exact invariant.
    old_count = 'self.assertEqual(source.count("membership_gap_query_plan"), 5)'
    new_count = 'self.assertEqual(source.count("membership_gap_query_plan"), 3)'
    if after[RUNTIME_TEST].count(old_count) != 1:
        raise RuntimeError("V2.42.10 search integration assertion drifted")
    after[RUNTIME_TEST] = after[RUNTIME_TEST].replace(old_count, new_count, 1)
    guards = _patch_parent_identity_tests(
        before,
        after,
        target_version=target_version,
        target_schema=target_schema,
    )
    for relative, source in after.items():
        if relative.endswith(".py"):
            ast.parse(source, filename=relative)
    changed = sorted(
        relative
        for relative in set(before) | set(after)
        if before.get(relative) != after.get(relative)
    )
    required = {
        "src/deepwide_agent/runtime.py",
        "scripts/preflight_deepwide.py",
        RUNTIME_MODULE,
        RUNTIME_TEST,
        *guards,
    }
    if set(changed) != required or len(after) != len(before) + 2:
        raise RuntimeError("V2.42.10 candidate delta file set drifted")
    if runtime_identity(after["src/deepwide_agent/runtime.py"]) != (
        target_schema,
        target_version,
    ):
        raise RuntimeError("V2.42.10 target identity drifted")
    manifest = text_manifest(after)
    return after, {
        "parent_provenance": parent,
        "parent_pipeline_version": parent_version,
        "parent_state_schema_version": parent_schema,
        "target_pipeline_version": target_version,
        "target_state_schema_version": target_schema,
        "delta_files": changed,
        "identity_guard_assertion_counts": guards,
        "candidate_regular_file_count": len(after),
        "candidate_regular_file_manifest": manifest,
        "candidate_regular_file_manifest_sha256": manifest_sha256(manifest),
        "same_membership_gap_query_budget": True,
        "query_search_fetch_model_context_token_or_item_budget_increased": False,
        "label_or_evaluator_conditioned_routing_added": False,
    }


def parent_regression_contract(
    order: Mapping[str, Any], markdown: Mapping[str, Any]
) -> tuple[list[str], int]:
    """Reuse the exact parent regression receipt and add two search tests."""

    baseline = str(order["baseline_name"])
    variant = str(order["semantic_parent_variant"])
    if baseline == "p12":
        schema = {
            "selected_baseline": "schema68",
            "selected_markdown_candidate": "schema69",
            "selected_scope_candidate": "schema70",
        }[variant]
        tests = read_publication(PUBLICATIONS[schema]).get("integrated_tests")
    elif variant == "selected_baseline":
        tests = read_publication(PUBLICATIONS[baseline]).get("integrated_tests")
    else:
        component = markdown.get("component_publication")
        tests = component.get("integrated_tests") if isinstance(component, Mapping) else None
    if not isinstance(tests, Mapping):
        raise RuntimeError("V2.42.10 parent regression receipt is absent")
    modules = tests.get("modules")
    tests_run = tests.get("tests_run")
    if (
        tests.get("status") != "pass"
        or not isinstance(modules, list)
        or not modules
        or not all(isinstance(item, str) and item.startswith("tests.") for item in modules)
        or isinstance(tests_run, bool)
        or not isinstance(tests_run, int)
        or tests_run <= 0
    ):
        raise RuntimeError("V2.42.10 parent regression receipt drifted")
    modules = list(modules)
    module = RUNTIME_TEST.removesuffix(".py").replace("/", ".")
    if module not in modules:
        modules.append(module)
    return modules, tests_run + 2


def run_integrated_tests(
    candidate: Path, modules: list[str], expected_tests: int
) -> dict[str, Any]:
    environment = {
        "HOME": str(candidate / ".sandbox-home"),
        "USER": "v24210-regression",
        "LOGNAME": "v24210-regression",
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "PYTHONSAFEPATH": "1",
    }
    runner = (
        "import sys,unittest; sys.path.insert(0,'.'); "
        f"names={modules!r}; "
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
        timeout=600,
        check=False,
    )
    output = completed.stdout + completed.stderr
    counts = re.findall(r"^Ran (\d+) tests? in ", output, flags=re.MULTILINE)
    tests_run = int(counts[-1]) if counts else -1
    if (
        completed.returncode != 0
        or tests_run != expected_tests
        or not re.search(r"^OK\s*$", output, flags=re.MULTILINE)
    ):
        raise RuntimeError("V2.42.10 integrated tests failed:\n" + output[-30000:])
    return {
        "status": "pass",
        "modules": modules,
        "tests_run": tests_run,
        "returncode": completed.returncode,
        "output_sha256": hashlib.sha256(output.encode()).hexdigest(),
        "scrubbed_environment": True,
        "network_or_api_required": False,
    }


def materialize_candidate(
    order: Mapping[str, Any],
    markdown: Mapping[str, Any],
    scope: Mapping[str, Any],
    candidate: Path = CANDIDATE_ROOT,
) -> dict[str, Any]:
    candidate = candidate.resolve(strict=False)
    if candidate.exists() or candidate.is_symlink():
        raise FileExistsError(candidate)
    files, report = build_candidate_files(order, markdown, scope)
    candidate.mkdir(parents=True, exist_ok=False)
    try:
        environment = ROOT / ".venv-eval"
        (candidate / ".venv-eval").symlink_to(
            environment.resolve(), target_is_directory=True
        )
        _write_candidate(candidate, files)
        live = candidate_regular_file_manifest(candidate, source_only=True)
        if live != report["candidate_regular_file_manifest"]:
            raise RuntimeError("V2.42.10 materialized source drifted")
        modules, expected_tests = parent_regression_contract(order, markdown)
        tests = run_integrated_tests(candidate, modules, expected_tests)
        if candidate_regular_file_manifest(candidate, source_only=True) != live:
            raise RuntimeError("V2.42.10 tests mutated candidate source")
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
        if RUNTIME_MODULE not in closure or not closure.issubset(live):
            raise RuntimeError("V2.42.10 forward closure is incomplete")
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


def build_selected_publication(
    selected: Mapping[str, Any],
    order: Mapping[str, Any],
    markdown: Mapping[str, Any],
    scope: Mapping[str, Any],
    search_status: str,
    search_state: Mapping[str, Any],
    gate: Mapping[str, Any] | None,
    *,
    candidate: Path = CANDIDATE_ROOT,
) -> dict[str, Any]:
    if not order["search_component_selected"]:
        disposition = "component_absent_no_op"
        component = None
        retired = False
    elif search_status == "complete_search_yield_go":
        disposition = "quality_go_component_materialized"
        component = materialize_candidate(order, markdown, scope, candidate)
        retired = False
    else:
        disposition = (
            "quality_no_go_component_retired"
            if search_status == "complete_search_yield_no_go"
            else "incomplete_attempt_component_retired_no_rerun"
        )
        component = None
        retired = True

    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24210_selected_search_component_publication",
        "label_blind": True,
        "selected_work_order": {
            "path": str(SELECTED_WORK_ORDER),
            "sha256": file_sha256(ROOT / SELECTED_WORK_ORDER),
            "selected_payload_sha256": selected["selected_payload_sha256"],
            "decision_sha256": order["decision_sha256"],
        },
        "markdown_parent_publication": {
            "path": str(MARKDOWN_PUBLICATION),
            "sha256": file_sha256(ROOT / MARKDOWN_PUBLICATION),
            "publication_payload_sha256": markdown["publication_payload_sha256"],
        },
        "scope_parent_publication": {
            "path": str(SCOPE_PUBLICATION),
            "sha256": file_sha256(ROOT / SCOPE_PUBLICATION),
            "publication_payload_sha256": scope["publication_payload_sha256"],
        },
        "search_quality_outcome": {
            "state_path": str(SEARCH_STATE),
            "state_sha256": file_sha256(ROOT / SEARCH_STATE),
            "status": search_status,
            "gate_path": str(SEARCH_GATE) if gate is not None else None,
            "gate_sha256": (
                file_sha256(ROOT / SEARCH_GATE) if gate is not None else None
            ),
            "gate_passed": gate.get("passed") if gate is not None else None,
            "threshold_or_query_policy_changed": False,
            "rerun_or_selective_retry_used": False,
            "contents_emitted": False,
        },
        "publication_order": dict(order),
        "publication_disposition": disposition,
        "component_publication": component,
        "search_component_published": component is not None,
        "search_component_retired": retired,
        "search_component_absent_noop": not order["search_component_selected"],
        "p12_scope_schema70_parent_preserved": bool(
            component is not None
            and order["p12_scope_uses_historical_schema70_parent"]
            and component["parent_state_schema_version"] == 70
            and component["target_state_schema_version"] == 86
        ),
        "mainline_scope_zero_byte_alias_preserved": bool(
            component is not None
            and order["mainline_scope_is_zero_byte_markdown_alias"]
            and component["parent_provenance"]["zero_byte_scope_alias"]
        ),
        "entropy_controller_published_or_implemented": False,
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
    if search_state.get("status") != search_status:
        raise RuntimeError("V2.42.10 bound search state status drifted")
    if (gate is not None) != (search_status != "terminal_incomplete_attempt_no_rerun"):
        raise RuntimeError("V2.42.10 bound search gate presence drifted")
    encoded = json.dumps(value, sort_keys=True).encode()
    if SECRET_LITERAL.search(encoded) or OPAQUE_ID.search(encoded):
        raise RuntimeError("V2.42.10 publication exposes forbidden content")
    value["publication_payload_sha256"] = payload_sha256(value)
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-root", default=str(CANDIDATE_ROOT))
    parser.add_argument("--output", default=str(OUTPUT))
    args = parser.parse_args()
    candidate = Path(args.candidate_root)
    output = Path(args.output)
    if (
        candidate.resolve(strict=False) != CANDIDATE_ROOT.resolve(strict=False)
        or output.resolve(strict=False) != (ROOT / OUTPUT).resolve(strict=False)
    ):
        raise RuntimeError("V2.42.10 CLI path drifted")
    selected, order, markdown, scope = load_inputs(ROOT)
    status, state, gate = validate_search_terminal(ROOT)
    value = build_selected_publication(
        selected,
        order,
        markdown,
        scope,
        status,
        state,
        gate,
        candidate=candidate,
    )
    publish_new(output, value)
    print(json.dumps({"path": str(output), "sha256": file_sha256(output)}))


if __name__ == "__main__":
    main()
