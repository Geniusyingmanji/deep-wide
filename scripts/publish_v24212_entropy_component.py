#!/usr/bin/env python3
"""Build the selected V2.42.12 entropy component after frozen parents finish.

The reusable rebase functions in this module are outcome independent.  They
add the historical true-continuation adapters, the pure V2.42.11 kernel, the
runtime bridge and the V2.42.12 model binding to one exact selected parent.
The live publisher is intentionally separate from the watcher and may run only
after the selected work order, component publications and replicate-aware
Gate-2A are immutable.

This module never calls a model, search backend, evaluator or benchmark and
never acquires the shared API lease.
"""

from __future__ import annotations

import argparse
import ast
import copy
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
    ENTROPY,
    SEARCH,
    validate_work_order,
)
from deepwide_agent.v24211_entropy_controller import (  # noqa: E402
    validate_action_model,
)
from deepwide_agent.v24211_entropy_feasibility import (  # noqa: E402
    GATE2A_REPORT_PATH,
    GATE2A_STATE_PATH,
    MODEL_PATH,
    build_entropy_integration_order,
)
from deepwide_agent.v24212_entropy_binding import (  # noqa: E402
    MODEL_BUNDLE_PATH,
    build_entropy_binding,
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
    SELECTED_WORK_ORDER,
    _write_candidate,
    extend_identity_assertions,
    load_selected_work_order,
    read_object,
)
from scripts.publish_v24207_scope_alias_component import (  # noqa: E402
    OUTPUT as SCOPE_PUBLICATION,
)
from scripts.publish_v24210_search_component import (  # noqa: E402
    OUTPUT as SEARCH_PUBLICATION,
    build_search_publication_order,
    load_inputs as load_search_inputs,
    selected_parent_files,
)
from scripts.replay_v24201_repo_local_candidate_dag import (  # noqa: E402
    PUBLICATIONS,
    file_sha256,
    manifest_sha256,
    read_publication,
    text_manifest,
)


OUTPUT = Path("results/v24212_selected_entropy_component_publication_v1_20260731.json")
CANDIDATE_ROOT = ROOT / "outputs/v24212_selected_entropy_candidate_v1_20260731"
TARGET_SUFFIX = "-label-blind-entropy-voc-controller"
GATE2A_STATE = Path(GATE2A_STATE_PATH)
GATE2A_REPORT = Path(GATE2A_REPORT_PATH)
ACTION_MODEL = Path(MODEL_PATH)
ADAPTER_AND_CONTROLLER_FILES = (
    "src/deepwide_agent/owic.py",
    "src/deepwide_agent/v2409_pilot.py",
    "src/deepwide_agent/v2409_interventions.py",
    "src/deepwide_agent/v24121_continuation.py",
    "src/deepwide_agent/v24122_execution.py",
    "src/deepwide_agent/v24211_entropy_controller.py",
    "src/deepwide_agent/v24211_entropy_runtime.py",
    "src/deepwide_agent/v24212_entropy_binding.py",
)
ENTROPY_TEST_FILES = (
    "tests/test_v24121_continuation.py",
    "tests/test_v24122_execution.py",
    "tests/test_v24211_entropy_controller.py",
    "tests/test_v24211_entropy_runtime.py",
    "tests/test_v24212_entropy_binding.py",
)
INTEGRATED_TEST = "tests/test_v24212_entropy_runtime_integration.py"
FORWARD_ADDITIONS = (*ADAPTER_AND_CONTROLLER_FILES, MODEL_BUNDLE_PATH)
SECRET_LITERAL = re.compile(
    rb"(?:ghp_|github_pat_|tvly-(?:dev-)?|sk-)[A-Za-z0-9_-]{16,}"
)
OPAQUE_ID = re.compile(rb"task_[0-9a-f]{24}")


def _replace_once(source: str, old: str, new: str, label: str) -> str:
    if source.count(old) != 1:
        raise RuntimeError(f"V2.42.12 expected one {label}")
    return source.replace(old, new, 1)


def _source(relative: str) -> str:
    path = ROOT / relative
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"V2.42.12 source is not ordinary: {relative}")
    return path.read_text(encoding="utf-8")


def _integrated_test_source(
    *, target_schema: int, target_version: str
) -> str:
    source = f'''from __future__ import annotations

import inspect
import unittest

from deepwide_agent.runtime import PIPELINE_VERSION, STATE_SCHEMA_VERSION
from deepwide_agent.v24211_entropy_runtime import (
    PRODUCTION_PACKAGE_AUTHORIZED,
    V24211EntropyRuntime,
)
from deepwide_agent.v24212_entropy_binding import MODEL_BUNDLE_PATH
from scripts.preflight_deepwide import (
    REQUIRED_FORWARD_CODE_PATHS,
    REQUIRED_STATIC_CHECK_NAMES,
)


class V24212EntropyRuntimeIntegrationTests(unittest.TestCase):
    def test_identity_authorization_and_forward_closure(self) -> None:
        self.assertEqual(STATE_SCHEMA_VERSION, {target_schema})
        self.assertEqual(PIPELINE_VERSION, {target_version!r})
        self.assertIs(PRODUCTION_PACKAGE_AUTHORIZED, True)
        self.assertIn(MODEL_BUNDLE_PATH, REQUIRED_FORWARD_CODE_PATHS)
        self.assertIn(
            "entropy_controller_binding_valid", REQUIRED_STATIC_CHECK_NAMES
        )

    def test_runner_uses_entropy_runtime_and_not_projection_arm(self) -> None:
        source = inspect.getsource(V24211EntropyRuntime)
        self.assertIn("prepare_v24122_matched_branch_states", source)
        self.assertNotIn("run_intervention_arm", source)
        self.assertNotIn('.get("question_type")', source)
        self.assertNotIn('["question_type"]', source)


if __name__ == "__main__":
    unittest.main()
'''
    ast.parse(source, filename=INTEGRATED_TEST)
    return source


def _patch_runner(source: str) -> str:
    runtime_import = "from deepwide_agent.runtime import (  # noqa: E402\n"
    source = _replace_once(
        source,
        runtime_import,
        "from deepwide_agent.v24211_entropy_runtime import (  # noqa: E402\n"
        "    V24211EntropyRuntime,\n"
        ")\n"
        "from deepwide_agent.v24212_entropy_binding import (  # noqa: E402\n"
        "    load_entropy_binding,\n"
        ")\n"
        + runtime_import,
        "runner entropy imports",
    )
    launch_anchor = """    launch_attestation = None
    if bool(args.freeze_file) != bool(args.preflight_report):
"""
    launch_replacement = """    launch_attestation = None
    entropy_binding = None
    entropy_model = None
    if not args.freeze_file or not args.preflight_report:
        raise RuntimeError("V2.42.12 entropy runtime requires a frozen launch")
    if bool(args.freeze_file) != bool(args.preflight_report):
"""
    source = _replace_once(
        source,
        launch_anchor,
        launch_replacement,
        "runner frozen-launch guard",
    )
    validation_anchor = """        validate_frozen_arguments(args, freeze, tasks)
        freeze_sha256 = hashlib.sha256(freeze_path.read_bytes()).hexdigest()
"""
    validation_replacement = """        validate_frozen_arguments(args, freeze, tasks)
        entropy_binding, entropy_model = load_entropy_binding(
            freeze.get("entropy_controller"), root=ROOT
        )
        freeze_sha256 = hashlib.sha256(freeze_path.read_bytes()).hexdigest()
"""
    source = _replace_once(
        source,
        validation_anchor,
        validation_replacement,
        "runner entropy binding load",
    )
    constructor = "runtime = DeepWideRuntime(model, search, runtime_config, out_dir)"
    replacement = """if entropy_binding is None or entropy_model is None:
        raise RuntimeError("V2.42.12 entropy binding was not loaded")
    runtime = V24211EntropyRuntime(
        model,
        search,
        runtime_config,
        out_dir,
        entropy_action_model=entropy_model,
        entropy_action_model_sha256=entropy_binding["action_model_sha256"],
        entropy_action_model_job_manifest_sha256=entropy_binding[
            "action_model_job_manifest_sha256"
        ],
        entropy_selected_parent_manifest_sha256=entropy_binding[
            "selected_parent_manifest_sha256"
        ],
        entropy_policy_branch=entropy_binding["policy_branch"],
    )"""
    return _replace_once(
        source, constructor, replacement, "runner entropy constructor"
    )


def _patch_preflight(source: str) -> str:
    runtime_import = (
        "from deepwide_agent.runtime import PIPELINE_VERSION, "
        "STATE_SCHEMA_VERSION, load_manifest  # noqa: E402\n"
    )
    source = _replace_once(
        source,
        runtime_import,
        runtime_import
        + "from deepwide_agent.v24212_entropy_binding import (  # noqa: E402\n"
        + "    load_entropy_binding,\n"
        + ")\n",
        "preflight entropy import",
    )
    path_anchor = '        "src/deepwide_agent/shadow_risk.py",\n'
    additions = "".join(f'        "{path}",\n' for path in FORWARD_ADDITIONS)
    source = _replace_once(
        source,
        path_anchor,
        path_anchor + additions,
        "preflight forward allowlist",
    )
    check_anchor = '        "code_manifest_exact",\n'
    source = _replace_once(
        source,
        check_anchor,
        check_anchor + '        "entropy_controller_binding_valid",\n',
        "preflight static-check registry",
    )
    declared_anchor = """    declared_code = freeze.get("code_sha256")
    if not isinstance(declared_code, dict):
        declared_code = {}
    static_checks = {
"""
    declared_replacement = """    declared_code = freeze.get("code_sha256")
    if not isinstance(declared_code, dict):
        declared_code = {}
    try:
        load_entropy_binding(freeze.get("entropy_controller"), root=ROOT)
        entropy_controller_binding_valid = True
    except (OSError, RuntimeError, TypeError, ValueError):
        entropy_controller_binding_valid = False
    static_checks = {
"""
    source = _replace_once(
        source,
        declared_anchor,
        declared_replacement,
        "preflight binding validation",
    )
    static_anchor = (
        '        "code_manifest_exact": set(declared_code) '
        '== REQUIRED_FORWARD_CODE_PATHS,\n'
    )
    return _replace_once(
        source,
        static_anchor,
        static_anchor
        + '        "entropy_controller_binding_valid": '
        + "entropy_controller_binding_valid,\n",
        "preflight binding static result",
    )


def _patch_launcher(source: str) -> str:
    runtime_import = "from deepwide_agent.runtime import (  # noqa: E402\n"
    source = _replace_once(
        source,
        runtime_import,
        "from deepwide_agent.v24212_entropy_binding import (  # noqa: E402\n"
        "    load_entropy_binding,\n"
        ")\n"
        + runtime_import,
        "launcher entropy import",
    )
    load_anchor = """    freeze = _load_object(freeze_path)
    report = _load_object(report_path)
    freeze_sha256 = sha256_file(freeze_path)

"""
    load_replacement = """    freeze = _load_object(freeze_path)
    report = _load_object(report_path)
    freeze_sha256 = sha256_file(freeze_path)
    load_entropy_binding(freeze.get("entropy_controller"), root=root)

"""
    return _replace_once(
        source,
        load_anchor,
        load_replacement,
        "launcher entropy binding validation",
    )


def patch_entropy_production(
    files: Mapping[str, str],
    *,
    model: Mapping[str, Any],
    target_schema: int,
    selected_parent_manifest_sha256: str,
) -> tuple[dict[str, str], dict[str, Any]]:
    """Rebase one exact parent map into a sealed entropy candidate in memory."""

    if isinstance(target_schema, bool) or not isinstance(target_schema, int):
        raise ValueError("V2.42.12 target schema is invalid")
    output = dict(files)
    required_parent = {
        "src/deepwide_agent/runtime.py",
        "scripts/run_deepwide_agent.py",
        "scripts/preflight_deepwide.py",
        "scripts/launch_frozen_deepwide.py",
    }
    if not required_parent.issubset(output):
        raise RuntimeError("V2.42.12 parent execution closure is incomplete")
    parent_manifest = text_manifest(output)
    if manifest_sha256(parent_manifest) != selected_parent_manifest_sha256:
        raise RuntimeError("V2.42.12 selected parent manifest drifted")
    parent_schema, parent_version = runtime_identity(
        output["src/deepwide_agent/runtime.py"]
    )
    target_version = parent_version + TARGET_SUFFIX
    output["src/deepwide_agent/runtime.py"] = _replace_once(
        output["src/deepwide_agent/runtime.py"],
        f'STATE_SCHEMA_VERSION = {parent_schema}\n'
        f'PIPELINE_VERSION = "{parent_version}"',
        f'STATE_SCHEMA_VERSION = {target_schema}\n'
        f'PIPELINE_VERSION = "{target_version}"',
        "runtime identity",
    )

    for relative in ADAPTER_AND_CONTROLLER_FILES:
        current = _source(relative)
        if relative in output and output[relative] != current:
            raise RuntimeError(f"V2.42.12 parent conflicts with {relative}")
        output[relative] = current
    output["src/deepwide_agent/v24211_entropy_runtime.py"] = _replace_once(
        output["src/deepwide_agent/v24211_entropy_runtime.py"],
        "PRODUCTION_PACKAGE_AUTHORIZED = False",
        "PRODUCTION_PACKAGE_AUTHORIZED = True",
        "production package authorization",
    )

    binding, model_payload = build_entropy_binding(
        model,
        selected_parent_manifest_sha256=selected_parent_manifest_sha256,
    )
    output[MODEL_BUNDLE_PATH] = model_payload.decode("utf-8")
    output["scripts/run_deepwide_agent.py"] = _patch_runner(
        output["scripts/run_deepwide_agent.py"]
    )
    output["scripts/preflight_deepwide.py"] = _patch_preflight(
        output["scripts/preflight_deepwide.py"]
    )
    output["scripts/launch_frozen_deepwide.py"] = _patch_launcher(
        output["scripts/launch_frozen_deepwide.py"]
    )

    for relative in ENTROPY_TEST_FILES:
        output[relative] = _source(relative)
    output[INTEGRATED_TEST] = _integrated_test_source(
        target_schema=target_schema,
        target_version=target_version,
    )

    guards: dict[str, int] = {}
    for relative in sorted(files):
        if not relative.startswith("tests/") or not relative.endswith(".py"):
            continue
        patched, count = extend_identity_assertions(
            output[relative],
            target_version=target_version,
            target_schema=target_schema,
        )
        if count:
            output[relative] = patched
            guards[relative] = count

    for relative, source in output.items():
        if relative.endswith(".py"):
            ast.parse(source, filename=relative)
    if runtime_identity(output["src/deepwide_agent/runtime.py"]) != (
        target_schema,
        target_version,
    ):
        raise RuntimeError("V2.42.12 target runtime identity drifted")
    if (
        output["scripts/run_deepwide_agent.py"].count(
            "runtime = V24211EntropyRuntime("
        )
        != 1
        or output["scripts/run_deepwide_agent.py"].count(
            "load_entropy_binding("
        )
        != 1
        or output["scripts/preflight_deepwide.py"].count(
            '"entropy_controller_binding_valid"'
        )
        != 2
        or output["scripts/launch_frozen_deepwide.py"].count(
            "load_entropy_binding("
        )
        != 1
        or output["src/deepwide_agent/v24211_entropy_runtime.py"].count(
            "PRODUCTION_PACKAGE_AUTHORIZED = True"
        )
        != 1
    ):
        raise RuntimeError("V2.42.12 production hook count drifted")

    manifest = text_manifest(output)
    changed = sorted(
        relative
        for relative in set(files) | set(output)
        if files.get(relative) != output.get(relative)
    )
    report = {
        "parent_pipeline_version": parent_version,
        "parent_state_schema_version": parent_schema,
        "selected_parent_manifest_sha256": selected_parent_manifest_sha256,
        "target_pipeline_version": target_version,
        "target_state_schema_version": target_schema,
        "delta_files": changed,
        "identity_guard_assertion_counts": guards,
        "entropy_binding": binding,
        "candidate_regular_file_count": len(output),
        "candidate_regular_file_manifest": manifest,
        "candidate_regular_file_manifest_sha256": manifest_sha256(manifest),
        "real_state_transition_adapters_included": True,
        "runtime_constructor_hooked": True,
        "preflight_and_launcher_model_binding_enforced": True,
        "historical_module_containing_revoked_projection_arm_present_as_adapter_dependency": True,
        "projection_only_action_arm_selected_instantiated_or_called": False,
        "mapping_gold_category_question_type_evaluator_score_or_reward_read": False,
        "network_model_search_fetch_evaluator_or_api_called": False,
    }
    return output, report


def _read_candidate_files(component: Mapping[str, Any]) -> dict[str, str]:
    raw_root = component.get("candidate_root")
    manifest = component.get("candidate_regular_file_manifest")
    if not isinstance(raw_root, str) or not isinstance(manifest, Mapping):
        raise RuntimeError("V2.42.12 selected component publication is absent")
    candidate = Path(raw_root)
    if (
        not candidate.is_absolute()
        or not candidate.resolve().is_relative_to(ROOT.resolve())
        or candidate.is_symlink()
        or not candidate.is_dir()
    ):
        raise RuntimeError("V2.42.12 parent candidate root is noncanonical")
    files: dict[str, str] = {}
    for raw_relative, raw_digest in manifest.items():
        relative = str(raw_relative)
        digest = str(raw_digest)
        path = candidate / relative
        if (
            path.is_symlink()
            or not path.is_file()
            or file_sha256(path) != digest
        ):
            raise RuntimeError("V2.42.12 selected parent bytes drifted")
        files[relative] = path.read_text(encoding="utf-8")
    if text_manifest(files) != dict(sorted(manifest.items())):
        raise RuntimeError("V2.42.12 selected parent manifest drifted")
    return files


def selected_entropy_parent_files(
    selected: Mapping[str, Any],
    entropy_order: Mapping[str, Any],
    search_order: Mapping[str, Any],
    markdown: Mapping[str, Any],
    scope: Mapping[str, Any],
    search_publication: Mapping[str, Any],
) -> tuple[dict[str, str], dict[str, Any]]:
    """Load exactly the parent selected by the frozen entropy order."""

    if SEARCH in selected["selected_work_order"]["eligible_components"]:
        component = search_publication.get("component_publication")
        if (
            search_publication.get("search_component_published") is not True
            or not isinstance(component, Mapping)
        ):
            raise RuntimeError("V2.42.12 selected search parent is unpublished")
        files = _read_candidate_files(component)
        provenance = {
            "kind": "selected_search_candidate",
            "publication_path": str(SEARCH_PUBLICATION),
            "publication_sha256": file_sha256(ROOT / SEARCH_PUBLICATION),
            "candidate_root": component["candidate_root"],
        }
    else:
        files, provenance = selected_parent_files(search_order, markdown, scope)
    schema, _version = runtime_identity(files["src/deepwide_agent/runtime.py"])
    if schema != entropy_order["source_state_schema_version"]:
        raise RuntimeError("V2.42.12 selected parent schema drifted")
    parent_manifest = text_manifest(files)
    return files, {
        **dict(provenance),
        "state_schema_version": schema,
        "candidate_regular_file_manifest_sha256": manifest_sha256(
            parent_manifest
        ),
    }


def validate_gate2a_and_model(
    root: Path = ROOT,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Validate the terminal design gate and fit/calibration-only model."""

    state = read_object(root / GATE2A_STATE)
    report = read_object(root / GATE2A_REPORT)
    model = read_object(root / ACTION_MODEL)
    unsigned_state = copy.deepcopy(state)
    state_seal = unsigned_state.pop("state_payload_sha256", None)
    unsigned_report = copy.deepcopy(report)
    report_seal = unsigned_report.pop("report_payload_sha256", None)
    if (
        state.get("role") != "v24193_replicate_aware_gate2a_consumer_state"
        or state.get("status") != "replicate_aware_gate2a_pass"
        or state.get("terminal") is not True
        or state.get("replicate_aware_gate2a_evaluated") is not True
        or state.get("replicate_aware_gate2a_passed") is not True
        or state.get("controller_design_allowed") is not True
        or state.get("controller_implementation_or_pilot_launch_allowed")
        is not False
        or state.get("training_credit_allowed") is not False
        or state.get("full220_controller_launch_allowed") is not False
        or state_seal != payload_sha256(unsigned_state)
        or report.get("role")
        != "v24193_replicate_aware_true_continuation_gate2a_report"
        or report.get("controller_design_allowed") is not True
        or report.get("controller_implementation_or_pilot_launch_allowed")
        is not False
        or report.get("training_credit_allowed") is not False
        or report.get("full220_controller_launch_allowed") is not False
        or report_seal != payload_sha256(unsigned_report)
        or state.get("replicate_aware_report", {}).get("sha256")
        != file_sha256(root / GATE2A_REPORT)
        or report.get("sources", {}).get("model", {}).get("sha256")
        != file_sha256(root / ACTION_MODEL)
    ):
        raise RuntimeError("V2.42.12 Gate-2A/model binding drifted")
    clean = validate_action_model(
        model,
        expected_model_sha256=str(model.get("model_sha256")),
        expected_job_manifest_sha256=str(model.get("job_manifest_sha256")),
    )
    return state, report, clean


def _existing_search_publication(root: Path) -> dict[str, Any]:
    value = read_object(root / SEARCH_PUBLICATION)
    unsigned = copy.deepcopy(value)
    seal = unsigned.pop("publication_payload_sha256", None)
    if (
        value.get("role") != "v24210_selected_search_component_publication"
        or value.get("label_blind") is not True
        or value.get("entropy_controller_published_or_implemented") is not False
        or value.get("benchmark_forward_or_full220_launch_allowed") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.42.12 search publication drifted")
    return value


def load_selected_inputs(
    root: Path = ROOT,
) -> tuple[
    dict[str, Any],
    dict[str, Any] | None,
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
]:
    selected, _markdown_order = load_selected_work_order(root)
    work_order = validate_work_order(selected["selected_work_order"])
    search_selected, search_order, markdown, scope = load_search_inputs(root)
    if search_selected != selected:
        raise RuntimeError("V2.42.12 selected work-order copies differ")
    search_publication = _existing_search_publication(root)
    if (
        search_publication.get("selected_work_order", {}).get("decision_sha256")
        != work_order["decision_sha256"]
    ):
        raise RuntimeError("V2.42.12 search publication decision drifted")
    entropy_order = (
        build_entropy_integration_order(work_order)
        if ENTROPY in work_order["eligible_components"]
        else None
    )
    return (
        selected,
        entropy_order,
        search_order,
        markdown,
        scope,
        search_publication,
    )


def _candidate_test_names() -> list[str]:
    return [
        "tests.test_v24121_continuation",
        "tests.test_v24122_execution",
        "tests.test_v24211_entropy_controller",
        (
            "tests.test_v24211_entropy_runtime.V24211EntropyRuntimeTests."
            "test_action_executes_two_searches_mutates_state_and_restarts_once"
        ),
        (
            "tests.test_v24211_entropy_runtime.V24211EntropyRuntimeTests."
            "test_all_context_action_pairs_execute_real_state_transitions"
        ),
        (
            "tests.test_v24211_entropy_runtime.V24211EntropyRuntimeTests."
            "test_constructor_validates_model_before_forward_use"
        ),
        (
            "tests.test_v24211_entropy_runtime.V24211EntropyRuntimeTests."
            "test_missing_signal_abstains_without_search"
        ),
        (
            "tests.test_v24211_entropy_runtime.V24211EntropyRuntimeTests."
            "test_nested_receipt_tamper_fails_even_after_outer_reseal"
        ),
        (
            "tests.test_v24211_entropy_runtime.V24211EntropyRuntimeTests."
            "test_restart_loop_is_bounded_and_clears_question"
        ),
        (
            "tests.test_v24211_entropy_runtime.V24211EntropyRuntimeTests."
            "test_stop_records_once_without_search_or_restart"
        ),
        (
            "tests.test_v24211_entropy_runtime.V24211EntropyRuntimeTests."
            "test_transition_ledger_tamper_fails_before_duplicate_decision"
        ),
        "tests.test_v24212_entropy_binding",
        "tests.test_v24212_entropy_runtime_integration",
    ]


def _validated_test_receipt(value: object) -> tuple[list[str], int]:
    if not isinstance(value, Mapping):
        raise RuntimeError("V2.42.12 parent regression receipt is absent")
    modules = value.get("modules")
    tests_run = value.get("tests_run")
    if (
        value.get("status") != "pass"
        or not isinstance(modules, list)
        or not modules
        or not all(
            isinstance(item, str) and item.startswith("tests.")
            for item in modules
        )
        or isinstance(tests_run, bool)
        or not isinstance(tests_run, int)
        or tests_run <= 0
    ):
        raise RuntimeError("V2.42.12 parent regression receipt drifted")
    return list(modules), tests_run


def parent_regression_contract(
    search_order: Mapping[str, Any],
    markdown: Mapping[str, Any],
    search_publication: Mapping[str, Any],
) -> tuple[list[str], int]:
    """Bind the selected parent's complete published regression receipt."""

    if search_order.get("search_component_selected") is True:
        component = search_publication.get("component_publication")
        tests = (
            component.get("integrated_tests")
            if isinstance(component, Mapping)
            else None
        )
        return _validated_test_receipt(tests)
    baseline = str(search_order["baseline_name"])
    variant = str(search_order["semantic_parent_variant"])
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
        tests = (
            component.get("integrated_tests")
            if isinstance(component, Mapping)
            else None
        )
    return _validated_test_receipt(tests)


def run_integrated_tests(
    candidate: Path,
    *,
    parent_modules: list[str],
    parent_tests: int,
) -> dict[str, Any]:
    additions = _candidate_test_names()
    names = list(dict.fromkeys([*parent_modules, *additions]))
    expected_added_tests = 37
    if len(names) != len(parent_modules) + len(additions):
        raise RuntimeError("V2.42.12 new regression names overlap parent modules")
    environment = {
        "HOME": str(candidate / ".sandbox-home"),
        "USER": "v24212-regression",
        "LOGNAME": "v24212-regression",
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "PYTHONSAFEPATH": "1",
    }
    runner = (
        "import sys,unittest; sys.path.insert(0,'.'); "
        f"names={names!r}; expected={parent_tests + expected_added_tests}; "
        "suite=unittest.defaultTestLoader.loadTestsFromNames(names); "
        "count=suite.countTestCases(); print('V24212_COUNT='+str(count)); "
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
        timeout=600,
        check=False,
    )
    output = completed.stdout + completed.stderr
    marker = re.findall(r"^V24212_COUNT=(\d+)$", output, flags=re.MULTILINE)
    counts = re.findall(r"^Ran (\d+) tests? in ", output, flags=re.MULTILINE)
    expected = int(marker[-1]) if marker else -1
    observed = int(counts[-1]) if counts else -1
    if (
        completed.returncode != 0
        or expected != parent_tests + expected_added_tests
        or observed != expected
        or not re.search(r"^OK\s*$", output, flags=re.MULTILINE)
    ):
        raise RuntimeError(
            "V2.42.12 integrated tests failed:\n" + output[-30000:]
        )
    return {
        "status": "pass",
        "names": names,
        "tests_run": observed,
        "parent_tests_run": parent_tests,
        "entropy_tests_added": expected_added_tests,
        "returncode": completed.returncode,
        "output_sha256": hashlib.sha256(output.encode()).hexdigest(),
        "scrubbed_environment": True,
        "network_or_api_required": False,
    }


def materialize_candidate(
    files: Mapping[str, str],
    report: Mapping[str, Any],
    *,
    parent_modules: list[str],
    parent_tests: int,
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
        live = candidate_regular_file_manifest(candidate, source_only=True)
        if live != report["candidate_regular_file_manifest"]:
            raise RuntimeError("V2.42.12 materialized source drifted")
        tests = run_integrated_tests(
            candidate,
            parent_modules=parent_modules,
            parent_tests=parent_tests,
        )
        if candidate_regular_file_manifest(candidate, source_only=True) != live:
            raise RuntimeError("V2.42.12 tests mutated candidate source")
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
        forward_paths = closure | {MODEL_BUNDLE_PATH}
        forward = {
            relative: live[relative] for relative in sorted(forward_paths)
        }
        if (
            not set(ADAPTER_AND_CONTROLLER_FILES).issubset(closure)
            or not forward_paths.issubset(live)
        ):
            raise RuntimeError("V2.42.12 forward closure is incomplete")
        return {
            **dict(report),
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
    entropy_order: Mapping[str, Any] | None,
    search_order: Mapping[str, Any],
    markdown: Mapping[str, Any],
    scope: Mapping[str, Any],
    search_publication: Mapping[str, Any],
    *,
    candidate: Path = CANDIDATE_ROOT,
) -> dict[str, Any]:
    work_order = selected["selected_work_order"]
    if entropy_order is None:
        disposition = "entropy_component_absent_no_op"
        component = None
        gate_source = None
    else:
        state, report, model = validate_gate2a_and_model(ROOT)
        parent_files, parent = selected_entropy_parent_files(
            selected,
            entropy_order,
            search_order,
            markdown,
            scope,
            search_publication,
        )
        files, rebase = patch_entropy_production(
            parent_files,
            model=model,
            target_schema=int(entropy_order["target_state_schema_version"]),
            selected_parent_manifest_sha256=parent[
                "candidate_regular_file_manifest_sha256"
            ],
        )
        parent_modules, parent_tests = parent_regression_contract(
            search_order, markdown, search_publication
        )
        component = materialize_candidate(
            files,
            rebase,
            parent_modules=parent_modules,
            parent_tests=parent_tests,
            candidate=candidate,
        )
        component["parent_provenance"] = parent
        disposition = "replicate_aware_gate2a_pass_entropy_component_materialized"
        gate_source = {
            "state_path": str(GATE2A_STATE),
            "state_sha256": file_sha256(ROOT / GATE2A_STATE),
            "status": state["status"],
            "report_path": str(GATE2A_REPORT),
            "report_sha256": file_sha256(ROOT / GATE2A_REPORT),
            "report_payload_sha256": report["report_payload_sha256"],
            "action_model_path": str(ACTION_MODEL),
            "action_model_file_sha256": file_sha256(ROOT / ACTION_MODEL),
            "action_model_sha256": model["model_sha256"],
            "action_model_job_manifest_sha256": model[
                "job_manifest_sha256"
            ],
            "audit_outcomes_not_used_by_action_model": True,
            "contents_emitted": False,
        }

    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24212_selected_entropy_component_publication",
        "label_blind": True,
        "selected_work_order": {
            "path": str(SELECTED_WORK_ORDER),
            "sha256": file_sha256(ROOT / SELECTED_WORK_ORDER),
            "selected_payload_sha256": selected["selected_payload_sha256"],
            "decision_sha256": work_order["decision_sha256"],
        },
        "search_parent_publication": {
            "path": str(SEARCH_PUBLICATION),
            "sha256": file_sha256(ROOT / SEARCH_PUBLICATION),
            "publication_payload_sha256": search_publication[
                "publication_payload_sha256"
            ],
        },
        "entropy_integration_order": (
            dict(entropy_order) if entropy_order is not None else None
        ),
        "replicate_aware_gate2a_source": gate_source,
        "publication_disposition": disposition,
        "component_publication": component,
        "entropy_component_published": component is not None,
        "entropy_component_absent_noop": entropy_order is None,
        "real_state_transition_adapters_included": component is not None,
        "historical_module_containing_revoked_projection_arm_present_as_adapter_dependency": component is not None,
        "projection_only_action_arm_selected_instantiated_or_called": False,
        "joint_package_quality_gate_evaluated_or_launched": False,
        "shared_api_lease_acquired": False,
        "network_model_search_fetch_evaluator_or_api_called": False,
        "benchmark_question_answer_evidence_prediction_or_url_parsed_or_emitted": False,
        "post_terminal_evaluator_derived_gate_report_read": gate_source is not None,
        "mapping_gold_category_question_type_evaluator_score_or_reward_read_for_forward_routing": False,
        "credential_value_read_persisted_hashed_or_emitted": False,
        "process_signal_restart_resume_rerun_skip_or_selective_retry": False,
        "benchmark_forward_or_full220_launch_allowed": False,
        "leaderboard_submission_or_sota_claim": False,
    }
    encoded = json.dumps(value, sort_keys=True).encode()
    if SECRET_LITERAL.search(encoded) or OPAQUE_ID.search(encoded):
        raise RuntimeError("V2.42.12 publication exposes forbidden content")
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
        raise RuntimeError("V2.42.12 CLI path drifted")
    selected, order, search_order, markdown, scope, search = (
        load_selected_inputs(ROOT)
    )
    value = build_selected_publication(
        selected,
        order,
        search_order,
        markdown,
        scope,
        search,
        candidate=candidate,
    )
    publish_new(output, value)
    print(json.dumps({"path": str(output), "sha256": file_sha256(output)}))


if __name__ == "__main__":
    main()
