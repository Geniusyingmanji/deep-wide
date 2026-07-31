#!/usr/bin/env python3
"""Publish one revalidated deepest-candidate V2.42 joint package.

Component publications in this lineage are cumulative candidates.  The joint
publisher therefore selects one complete deepest byte graph, validates its
parent chain and component activation, materializes that exact graph in a
fresh repo-local directory, and reruns the complete frozen regression.  It
never overlays component directories, calls a service, acquires the shared
lease, evaluates dev64, or launches a benchmark.
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
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24200_successor import payload_sha256  # noqa: E402
from deepwide_agent.v24206_markdown_publisher import (  # noqa: E402
    ENTROPY,
    MARKDOWN,
    SCOPE,
    SEARCH,
)
from deepwide_agent.v24214_joint_package import (  # noqa: E402
    build_joint_package_order,
    validate_joint_package_order,
)
from scripts.audit_v24205_markdown_rebase_feasibility import (  # noqa: E402
    runtime_identity,
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
    load_selected_work_order,
    read_object,
)
from scripts.publish_v24207_scope_alias_component import (  # noqa: E402
    OUTPUT as SCOPE_PUBLICATION,
)
from scripts.publish_v24210_search_component import (  # noqa: E402
    OUTPUT as SEARCH_PUBLICATION,
)
from scripts.publish_v24213_entropy_recovery import (  # noqa: E402
    OUTPUT as ENTROPY_PUBLICATION,
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


OUTPUT = Path("results/v24214_selected_joint_package_publication_v1_20260731.json")
CANDIDATE_ROOT = ROOT / "outputs/v24214_selected_joint_package_candidate_v1_20260731"
HISTORICAL_SCHEMA = {
    68: "schema68",
    69: "schema69",
    70: "schema70",
    76: "schema76",
    77: "schema77",
}
COMPONENT_PUBLICATIONS = {
    "markdown": MARKDOWN_PUBLICATION,
    "scope": SCOPE_PUBLICATION,
    "search": SEARCH_PUBLICATION,
    "entropy": ENTROPY_PUBLICATION,
}
COMPONENT_SOURCE_PATHS = {
    MARKDOWN: {"src/deepwide_agent/v24102.py"},
    SCOPE: {"src/deepwide_agent/v24104.py"},
    SEARCH: {"src/deepwide_agent/v24179.py"},
    ENTROPY: {
        "src/deepwide_agent/v24121_continuation.py",
        "src/deepwide_agent/v24122_execution.py",
        "src/deepwide_agent/v24211_entropy_controller.py",
        "src/deepwide_agent/v24211_entropy_runtime.py",
        "src/deepwide_agent/v24212_entropy_binding.py",
        "src/deepwide_agent/v24211_entropy_action_model.json",
    },
}
COMPONENT_TEST_NAMES = {
    MARKDOWN: {
        "tests.test_v24102_markdown_rank_slot",
        "tests.test_v24102_integrated_markdown_rank_slot",
    },
    SCOPE: {
        "tests.test_v24104_scope_open_fallback",
        "tests.test_v24104_integrated_scope_open_fallback",
    },
    SEARCH: {"tests.test_v24179_predicate_fair_query_scheduler"},
    ENTROPY: {
        "tests.test_v24121_continuation",
        "tests.test_v24122_execution",
        "tests.test_v24211_entropy_controller",
        "tests.test_v24212_entropy_binding",
        "tests.test_v24212_entropy_runtime_integration",
    },
}
FORBIDDEN_RUNTIME_KEYS = frozenset(
    {
        "answer_key",
        "category",
        "gold",
        "ground_truth",
        "question_type",
        "split",
        "task_category",
    }
)
SECRET_LITERAL = re.compile(
    rb"(?:ghp_|github_pat_|tvly-(?:dev-)?|sk-)[A-Za-z0-9_-]{16,}"
)
OPAQUE_ID = re.compile(rb"task_[0-9a-f]{24}")


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _ordinary(root: Path, relative: Path, digest: str | None = None) -> Path:
    if relative.is_absolute() or ".." in relative.parts:
        raise RuntimeError("V2.42.14 path is noncanonical")
    path = root / relative
    if (
        path.resolve(strict=False) != path.absolute()
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(root)
        or digest is not None
        and file_sha256(path) != digest
    ):
        raise RuntimeError(f"V2.42.14 frozen input drifted: {relative}")
    return path


def _publication(
    root: Path,
    path: Path,
    *,
    role: str,
    decision: str,
) -> dict[str, Any]:
    value = read_object(_ordinary(root, path))
    if (
        value.get("role") != role
        or value.get("label_blind") is not True
        or value.get("selected_work_order", {}).get("decision_sha256")
        != decision
        or not _sealed(value, "publication_payload_sha256")
    ):
        raise RuntimeError(f"V2.42.14 component publication drifted: {path}")
    return value


def load_selected_inputs(
    root: Path = ROOT,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, dict[str, Any]]]:
    """Load all terminal component receipts after V2.42.13 terminates."""

    selected, _markdown_order = load_selected_work_order(root, SELECTED_WORK_ORDER)
    work_order = selected["selected_work_order"]
    order = build_joint_package_order(work_order)
    decision = str(order["decision_sha256"])
    publications = {
        "markdown": _publication(
            root,
            MARKDOWN_PUBLICATION,
            role="v24206_selected_markdown_component_publication",
            decision=decision,
        ),
        "scope": _publication(
            root,
            SCOPE_PUBLICATION,
            role="v24207_selected_scope_alias_component_publication",
            decision=decision,
        ),
        "search": _publication(
            root,
            SEARCH_PUBLICATION,
            role="v24210_selected_search_component_publication",
            decision=decision,
        ),
        "entropy": _publication(
            root,
            ENTROPY_PUBLICATION,
            role="v24213_selected_entropy_component_recovery_publication",
            decision=decision,
        ),
    }
    components = set(order["eligible_components"])
    expected_presence = {
        "markdown": MARKDOWN in components,
        "scope": SCOPE in components,
        "search": SEARCH in components,
        "entropy": ENTROPY in components,
    }
    actual_presence = {
        "markdown": publications["markdown"].get("markdown_component_published"),
        "scope": publications["scope"].get("branch_scope_component_published"),
        "search": publications["search"].get("search_component_published"),
        "entropy": publications["entropy"].get("entropy_component_published"),
    }
    false_fields = {
        "markdown": (
            "joint_package_built_or_materialized",
            "package_gate_evaluated_or_launched",
            "shared_api_lease_acquired",
            "network_model_search_fetch_evaluator_or_api_called",
            "benchmark_forward_or_full220_launch_allowed",
            "leaderboard_submission_or_sota_claim",
        ),
        "scope": (
            "joint_package_built_or_materialized",
            "package_gate_evaluated_or_launched",
            "shared_api_lease_acquired",
            "network_model_search_fetch_evaluator_or_api_called",
            "benchmark_forward_or_full220_launch_allowed",
            "leaderboard_submission_or_sota_claim",
        ),
        "search": (
            "joint_package_built_or_materialized",
            "package_gate_evaluated_or_launched",
            "shared_api_lease_acquired",
            "network_model_search_fetch_evaluator_or_api_called",
            "benchmark_forward_or_full220_launch_allowed",
            "leaderboard_submission_or_sota_claim",
        ),
        "entropy": (
            "joint_package_quality_gate_evaluated_or_launched",
            "shared_api_lease_acquired",
            "network_model_search_fetch_evaluator_or_api_called",
            "benchmark_forward_or_full220_launch_allowed",
            "leaderboard_submission_or_sota_claim",
        ),
    }
    if actual_presence != expected_presence:
        raise RuntimeError("V2.42.14 selected component presence drifted")
    for name, fields in false_fields.items():
        if any(publications[name].get(field) is not False for field in fields):
            raise RuntimeError(f"V2.42.14 {name} authority boundary drifted")
    if publications["search"].get("search_component_retired") is True:
        raise RuntimeError("V2.42.14 selected search component was retired")
    return selected, order, publications


def _validated_regression(value: Mapping[str, Any]) -> tuple[list[str], int]:
    tests = value.get("integrated_tests")
    if not isinstance(tests, Mapping):
        raise RuntimeError("V2.42.14 deepest regression receipt is absent")
    raw_names = tests.get("modules")
    if raw_names is None:
        raw_names = tests.get("names")
    count = tests.get("tests_run")
    if (
        tests.get("status") != "pass"
        or not isinstance(raw_names, list)
        or not raw_names
        or not all(
            isinstance(name, str) and name.startswith("tests.")
            for name in raw_names
        )
        or isinstance(count, bool)
        or not isinstance(count, int)
        or count <= 0
        or tests.get("returncode") != 0
        or tests.get("network_or_api_required") is not False
    ):
        raise RuntimeError("V2.42.14 deepest regression receipt drifted")
    return list(raw_names), count


def _candidate_files(
    component: Mapping[str, Any], *, expected_schema: int
) -> tuple[dict[str, str], dict[str, Any]]:
    root = Path(str(component.get("candidate_root", "")))
    manifest = component.get("candidate_regular_file_manifest")
    if (
        not root.is_absolute()
        or not root.resolve().is_relative_to(ROOT.resolve())
        or root.is_symlink()
        or not root.is_dir()
        or not isinstance(manifest, Mapping)
        or not manifest
        or manifest_sha256(manifest)
        != component.get("candidate_regular_file_manifest_sha256")
    ):
        raise RuntimeError("V2.42.14 deepest candidate root is noncanonical")
    files: dict[str, str] = {}
    for raw_relative, raw_digest in manifest.items():
        relative = str(raw_relative)
        path = root / relative
        if (
            path.is_symlink()
            or not path.is_file()
            or not path.resolve().is_relative_to(root.resolve())
            or file_sha256(path) != str(raw_digest)
        ):
            raise RuntimeError("V2.42.14 deepest candidate bytes drifted")
        files[relative] = path.read_text(encoding="utf-8")
    if text_manifest(files) != dict(sorted(manifest.items())):
        raise RuntimeError("V2.42.14 deepest candidate manifest drifted")
    if runtime_identity(files["src/deepwide_agent/runtime.py"])[0] != expected_schema:
        raise RuntimeError("V2.42.14 deepest candidate identity drifted")
    return files, {
        "kind": "repo_local_cumulative_candidate",
        "source_candidate_root": str(root),
        "source_manifest_sha256": manifest_sha256(manifest),
    }


def _historical_files(
    order: Mapping[str, Any], *, expected_schema: int
) -> tuple[dict[str, str], dict[str, Any], dict[str, Any]]:
    key = HISTORICAL_SCHEMA.get(expected_schema)
    if key is None:
        raise RuntimeError("V2.42.14 historical graph is unregistered")
    replay, maps = build_replay()
    if replay.get("all_stage_file_maps_byte_exact_to_frozen_publications") is not True:
        raise RuntimeError("V2.42.14 repository-local replay failed")
    files = dict(maps[key])
    publication = read_publication(PUBLICATIONS[key])
    if (
        text_manifest(files) != publication_manifest(publication)
        or runtime_identity(files["src/deepwide_agent/runtime.py"])[0]
        != expected_schema
    ):
        raise RuntimeError("V2.42.14 historical byte graph drifted")
    baseline = order["baseline_publication"]
    baseline_value = read_object(
        _ordinary(ROOT, Path(str(baseline["path"])), str(baseline["sha256"]))
    )
    baseline_key = {
        "p12": "schema68",
        "schema76": "schema76",
        "schema77": "schema77",
    }[str(order["baseline_name"])]
    if publication_manifest(baseline_value) != text_manifest(maps[baseline_key]):
        raise RuntimeError("V2.42.14 selected baseline bytes drifted")
    return files, publication, {
        "kind": "repository_local_byte_exact_replay",
        "historical_schema": key,
        "historical_publication": {
            "path": PUBLICATIONS[key].path,
            "sha256": PUBLICATIONS[key].sha256,
        },
        "source_manifest_sha256": manifest_sha256(text_manifest(files)),
    }


def resolve_deepest_graph(
    order: Mapping[str, Any],
    publications: Mapping[str, Mapping[str, Any]],
) -> tuple[dict[str, str], list[str], int, dict[str, Any]]:
    """Resolve one complete graph; never merge component directories."""

    validated = validate_joint_package_order(order)
    schema = int(validated["final_state_schema_version"])
    byte_owner = str(validated["deepest_byte_owner"])
    if byte_owner == "baseline" or schema in {68, 69, 70, 76, 77}:
        files, historical, provenance = _historical_files(
            validated, expected_schema=schema
        )
        names, count = _validated_regression(historical)
    else:
        publication = publications.get(byte_owner)
        component = (
            publication.get("component_publication")
            if isinstance(publication, Mapping)
            else None
        )
        if not isinstance(component, Mapping):
            raise RuntimeError("V2.42.14 deepest component publication is absent")
        files, provenance = _candidate_files(component, expected_schema=schema)
        names, count = _validated_regression(component)

    manifest = text_manifest(files)
    components = list(validated["eligible_components"])
    required_paths = set().union(
        *(COMPONENT_SOURCE_PATHS[name] for name in components)
    ) if components else set()
    missing_paths = sorted(required_paths - set(manifest))
    required_tests = set().union(
        *(COMPONENT_TEST_NAMES[name] for name in components)
    ) if components else set()
    missing_tests = sorted(required_tests - set(names))
    if missing_paths or missing_tests:
        raise RuntimeError(
            "V2.42.14 selected component activation is incomplete: "
            f"paths={missing_paths}, tests={missing_tests}"
        )
    if ENTROPY in components:
        runtime = files["src/deepwide_agent/v24211_entropy_runtime.py"]
        runner = files["scripts/run_deepwide_agent.py"]
        if (
            runtime.count("PRODUCTION_PACKAGE_AUTHORIZED = True") != 1
            or runner.count("runtime = V24211EntropyRuntime(") != 1
        ):
            raise RuntimeError("V2.42.14 entropy runtime activation drifted")
    provenance.update(
        deepest_semantic_owner=validated["deepest_semantic_owner"],
        deepest_byte_owner=byte_owner,
        source_state_schema_version=schema,
        source_regular_file_count=len(manifest),
        selected_component_source_paths=sorted(required_paths),
        selected_component_test_names=sorted(required_tests),
        all_selected_components_present_in_source_and_regression=True,
        component_directory_overlay_used=False,
    )
    return files, names, count, provenance


def _forbidden_runtime_accesses(
    files: Mapping[str, str], paths: Sequence[str]
) -> list[str]:
    hits: list[str] = []
    for relative in paths:
        if not relative.endswith(".py"):
            continue
        tree = ast.parse(files[relative], filename=relative)
        for node in ast.walk(tree):
            key: str | None = None
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "get"
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
            if key in FORBIDDEN_RUNTIME_KEYS:
                hits.append(f"{relative}:{getattr(node, 'lineno', 0)}:{key}")
    return sorted(hits)


def run_full_regression(
    candidate: Path, names: Sequence[str], expected_tests: int
) -> dict[str, Any]:
    environment = {
        "HOME": str(candidate / ".sandbox-home"),
        "USER": "v24214-regression",
        "LOGNAME": "v24214-regression",
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "PYTHONSAFEPATH": "1",
    }
    runner = (
        "import sys,unittest; sys.path.insert(0,'.'); "
        f"names={list(names)!r}; expected={expected_tests}; "
        "suite=unittest.defaultTestLoader.loadTestsFromNames(names); "
        "count=suite.countTestCases(); print('V24214_COUNT='+str(count)); "
        "assert count == expected, (count, expected); "
        "result=unittest.TextTestRunner(verbosity=2).run(suite); "
        "raise SystemExit(not result.wasSuccessful())"
    )
    completed = subprocess.run(
        [str(candidate / ".venv-eval/bin/python"), "-I", "-B", "-c", runner],
        cwd=candidate,
        env=environment,
        text=True,
        capture_output=True,
        timeout=900,
        check=False,
    )
    output = completed.stdout + completed.stderr
    markers = re.findall(r"^V24214_COUNT=(\d+)$", output, flags=re.MULTILINE)
    counts = re.findall(r"^Ran (\d+) tests? in ", output, flags=re.MULTILINE)
    observed = int(counts[-1]) if counts else -1
    if (
        completed.returncode != 0
        or not markers
        or int(markers[-1]) != expected_tests
        or observed != expected_tests
        or not re.search(r"^OK\s*$", output, flags=re.MULTILINE)
    ):
        raise RuntimeError("V2.42.14 joint regression failed:\n" + output[-30000:])
    return {
        "status": "pass",
        "names": list(names),
        "tests_run": observed,
        "returncode": completed.returncode,
        "output_sha256": hashlib.sha256(output.encode()).hexdigest(),
        "complete_deepest_parent_and_component_regression_rerun": True,
        "scrubbed_environment": True,
        "network_or_api_required": False,
    }


def materialize_joint_candidate(
    files: Mapping[str, str],
    names: Sequence[str],
    expected_tests: int,
    provenance: Mapping[str, Any],
    *,
    candidate: Path = CANDIDATE_ROOT,
) -> dict[str, Any]:
    candidate = candidate.resolve(strict=False)
    if candidate.exists() or candidate.is_symlink():
        raise FileExistsError(candidate)
    candidate.mkdir(parents=True, exist_ok=False)
    try:
        environment = ROOT / ".venv-eval"
        (candidate / ".venv-eval").symlink_to(
            environment.resolve(), target_is_directory=True
        )
        _write_candidate(candidate, files)
        manifest = text_manifest(files)
        live = candidate_regular_file_manifest(candidate, source_only=True)
        if live != manifest:
            raise RuntimeError("V2.42.14 materialized graph drifted")
        regression = run_full_regression(candidate, names, expected_tests)
        if candidate_regular_file_manifest(candidate, source_only=True) != live:
            raise RuntimeError("V2.42.14 regression mutated candidate source")
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
        if not closure.issubset(live):
            raise RuntimeError("V2.42.14 forward execution closure is incomplete")
        forbidden = _forbidden_runtime_accesses(files, sorted(closure))
        if forbidden:
            raise RuntimeError(
                "V2.42.14 evaluator-only runtime access appeared: "
                + ", ".join(forbidden)
            )
        forward = {relative: live[relative] for relative in sorted(closure)}
        return {
            "candidate_root": str(candidate),
            "candidate_regular_file_count": len(live),
            "candidate_regular_file_manifest": live,
            "candidate_regular_file_manifest_sha256": manifest_sha256(live),
            "candidate_disk_hashes_verified": True,
            "candidate_regular_file_set_exact": True,
            "candidate_is_exact_copy_of_single_deepest_graph": True,
            "candidate_directory_overlay_used": False,
            "candidate_forward_execution_closure_exact": True,
            "candidate_forward_manifest": forward,
            "candidate_forward_manifest_sha256": manifest_sha256(forward),
            "runtime_evaluator_only_key_accesses": [],
            "runtime_label_blind_ast_audit_passed": True,
            "source_graph": dict(provenance),
            "integrated_tests": regression,
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
    publications: Mapping[str, Mapping[str, Any]],
    *,
    candidate: Path = CANDIDATE_ROOT,
) -> dict[str, Any]:
    validated = validate_joint_package_order(order)
    identity = bool(validated["identity_handoff_only"])
    if identity:
        files, _names, _count, provenance = resolve_deepest_graph(
            validated, publications
        )
        component = None
        identity_manifest = text_manifest(files)
        disposition = "byte_exact_selected_baseline_identity_handoff"
    else:
        files, names, count, provenance = resolve_deepest_graph(
            validated, publications
        )
        component = materialize_joint_candidate(
            files,
            names,
            count,
            provenance,
            candidate=candidate,
        )
        identity_manifest = None
        disposition = "single_deepest_graph_joint_package_revalidated"

    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24214_selected_joint_package_publication",
        "label_blind": True,
        "selected_work_order": {
            "path": str(SELECTED_WORK_ORDER),
            "sha256": file_sha256(ROOT / SELECTED_WORK_ORDER),
            "selected_payload_sha256": selected["selected_payload_sha256"],
            "decision_sha256": validated["decision_sha256"],
        },
        "component_publications": {
            name: {
                "path": str(COMPONENT_PUBLICATIONS[name]),
                "sha256": file_sha256(ROOT / COMPONENT_PUBLICATIONS[name]),
                "publication_payload_sha256": publications[name][
                    "publication_payload_sha256"
                ],
            }
            for name in ("markdown", "scope", "search", "entropy")
        },
        "joint_package_order": validated,
        "publication_disposition": disposition,
        "component_publication": component,
        "identity_handoff_manifest": identity_manifest,
        "identity_handoff_only": identity,
        "joint_package_materialized": component is not None,
        "all_selected_components_covered_exactly_once": True,
        "single_deepest_cumulative_graph_used": True,
        "component_directory_overlay_used": False,
        "complete_parent_and_component_regression_rerun": component is not None,
        "strict_component_activation_validated": component is not None,
        "silent_component_drop_or_baseline_fallback_used": False,
        "package_gate_evaluated_or_launched": False,
        "dev64_launch_allowed": False,
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
        raise RuntimeError("V2.42.14 publication exposes forbidden content")
    value["publication_payload_sha256"] = payload_sha256(value)
    return value


def publish_new(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(dict(value), handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise


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
        raise RuntimeError("V2.42.14 CLI path drifted")
    selected, order, publications = load_selected_inputs(ROOT)
    value = build_selected_publication(
        selected, order, publications, candidate=candidate
    )
    publish_new(output, value)
    print(json.dumps({"path": str(output), "sha256": file_sha256(output)}))


if __name__ == "__main__":
    main()
