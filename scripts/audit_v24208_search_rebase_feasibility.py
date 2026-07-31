#!/usr/bin/env python3
"""Audit a repo-local, outcome-independent V2.41.79 search rebase.

The audit reconstructs frozen P12/schema76/schema77 bytes in memory and applies
one deterministic production hook.  It does not read live quality outcomes,
materialize a candidate, run a benchmark, call a service, or grant publication
authority.  Search publication remains conditional on the frozen V2.41.80
quality gate reaching GO after its serial barrier.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24200_successor import payload_sha256  # noqa: E402
from deepwide_agent.v24208_search_rebase_audit import (  # noqa: E402
    build_search_rebase_manifest,
)
from scripts.audit_v24205_markdown_rebase_feasibility import (  # noqa: E402
    runtime_identity,
)
from scripts.publish_v24206_markdown_component import (  # noqa: E402
    build_mainline_candidate_files,
)
from scripts.replay_v24201_repo_local_candidate_dag import (  # noqa: E402
    build_replay,
    file_sha256,
    manifest_sha256,
    text_manifest,
)


ROLE = "v24208_search_rebase_feasibility_audit"
OUTPUT = Path("results/v24208_search_rebase_feasibility_audit_v1_20260731.json")
V24201 = Path("results/v24201_repo_local_candidate_dag_replay_v1_20260731.json")
V24201_SHA256 = "cee95e892c1aa2e80dbcc70bac5f426e7f66a7e023c14554a63e42878bdb2a6f"
V24204 = Path("results/v24204_postdecision_work_order_preregistration_v1_20260731.json")
V24204_SHA256 = "aedd97c0ccbfaa3e18f157aa56e0d0969c39fc28b0903cbe2260a3db1172d5e4"
V24206 = Path("results/v24206_selected_markdown_component_preregistration_v1_20260731.json")
V24206_SHA256 = "3c543a52309df2c2503e92b5c75e9b24434be4a410f0219ac1b2448f01389ffa"
V24207 = Path("results/v24207_selected_scope_alias_component_preregistration_v1_20260731.json")
V24207_SHA256 = "2a2800caf6056526bc432baffcadea913de593ba8bed085b5174bffc7ec1ebe0"
V24179 = Path("results/v24179_predicate_fair_query_scheduler_replay_v1_20260730.json")
V24179_SHA256 = "7cb6670888215d738183f093114e338d392b158fcea7eca9b2bed75c5a68e024"
V24180 = Path("results/v24180_predicate_search_yield_preregistration_v1_20260730.json")
V24180_SHA256 = "1274fe4a9b7801d96dd5265443cb3f6b837edd469be3fe85bef1c3d71ebdf5e4"
SCHEDULER_SOURCE = Path("scripts/prototype_v24179_predicate_fair_query_scheduler.py")
SCHEDULER_SOURCE_SHA256 = "3b6e2816d5208c55fbe515a20d4d1fe46f6ce6d8f8f024faa977b61a7f18519c"
RUNTIME_MODULE = "src/deepwide_agent/v24179.py"
RUNTIME_TEST = "tests/test_v24179_predicate_fair_query_scheduler.py"
TARGET_SUFFIX = "-predicate-fair-shared-query"
TARGET_SCHEMAS = {
    ("p12", "selected_baseline"): 80,
    ("p12", "selected_markdown_candidate"): 81,
    ("schema76", "selected_baseline"): 82,
    ("schema76", "selected_markdown_candidate"): 83,
    ("schema77", "selected_baseline"): 84,
    ("schema77", "selected_markdown_candidate"): 85,
}
SECRET_LITERAL = re.compile(rb"(?:ghp_|github_pat_|tvly-|sk-)[A-Za-z0-9_-]{16,}")
OPAQUE_ID = re.compile(rb"task_[0-9a-f]{24}")


def ordinary(root: Path, relative: Path, digest: str) -> Path:
    if relative.is_absolute() or ".." in relative.parts:
        raise RuntimeError("V2.42.08 input path is noncanonical")
    path = root / relative
    if (
        path.resolve(strict=False) != path.absolute()
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(root)
        or file_sha256(path) != digest
    ):
        raise RuntimeError(f"V2.42.08 frozen input drifted: {relative}")
    return path


def read_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.42.08 expected one JSON object")
    return value


def replace_once(source: str, old: str, new: str, label: str) -> str:
    if source.count(old) != 1:
        raise RuntimeError(f"V2.42.08 expected one {label}")
    return source.replace(old, new, 1)


def _scheduler_module_source() -> str:
    source = ordinary(ROOT, SCHEDULER_SOURCE, SCHEDULER_SOURCE_SHA256).read_text(
        encoding="utf-8"
    )
    ast.parse(source, filename=RUNTIME_MODULE)
    return source


def _integrated_test_source(target_version: str, target_schema: int) -> str:
    source = f'''from __future__ import annotations

import inspect
import unittest

from deepwide_agent.runtime import (
    PIPELINE_VERSION,
    STATE_SCHEMA_VERSION,
    DeepWideRuntime,
)
from deepwide_agent.v24179 import (
    PredicateQueryOpportunity,
    build_predicate_fair_query_schedule,
)


class PredicateFairQuerySchedulerIntegratedTests(unittest.TestCase):
    def test_runtime_identity_and_single_hook(self) -> None:
        self.assertEqual(PIPELINE_VERSION, {target_version!r})
        self.assertEqual(STATE_SCHEMA_VERSION, {target_schema})
        source = inspect.getsource(DeepWideRuntime._membership_gap_recovery)
        self.assertEqual(source.count("build_predicate_fair_query_schedule("), 1)
        self.assertEqual(source.count("membership_gap_query_plan"), 5)

    def test_same_cap_shared_route_gain(self) -> None:
        opportunities = [
            PredicateQueryOpportunity("R1", "P1", "R1 P1", "subject P1 list"),
            PredicateQueryOpportunity("R1", "P2", "R1 P2", "subject P2 list"),
            PredicateQueryOpportunity("R2", "P1", "R2 P1", "subject P1 list"),
            PredicateQueryOpportunity("R2", "P2", "R2 P2", "subject P2 list"),
        ]
        value = build_predicate_fair_query_schedule(
            baseline_queries=["generic", "R1 P1", "R1 P2"],
            baseline_query_to_rows={{
                "generic": ["R0"], "R1 P1": ["R1"], "R1 P2": ["R1"]
            }},
            opportunities=opportunities,
            budget=3,
        )
        self.assertTrue(value.activated)
        self.assertEqual(len(value.queries), 3)
        self.assertEqual(value.gained_routed_opportunities, 2)
        self.assertEqual(value.lost_routed_opportunities, 0)


if __name__ == "__main__":
    unittest.main()
'''
    ast.parse(source, filename=RUNTIME_TEST)
    return source


def patch_search_production(
    files: Mapping[str, str], *, target_schema: int
) -> dict[str, str]:
    """Apply one label-blind same-budget scheduler hook to a parent file map."""

    output = dict(files)
    runtime_path = "src/deepwide_agent/runtime.py"
    preflight_path = "scripts/preflight_deepwide.py"
    parent_schema, parent_version = runtime_identity(output[runtime_path])
    target_version = parent_version + TARGET_SUFFIX
    source = replace_once(
        output[runtime_path],
        f'STATE_SCHEMA_VERSION = {parent_schema}\nPIPELINE_VERSION = "{parent_version}"',
        f'STATE_SCHEMA_VERSION = {target_schema}\nPIPELINE_VERSION = "{target_version}"',
        "runtime identity",
    )
    import_anchor = "from .shadow_risk import record_shadow_snapshot\n"
    source = replace_once(
        source,
        import_anchor,
        import_anchor
        + "from .v24179 import (\n"
        + "    PredicateQueryOpportunity,\n"
        + "    build_predicate_fair_query_schedule,\n"
        + ")\n",
        "search scheduler import",
    )
    plan_anchor = '''            state["membership_gap_query_plan"] = {
                "queries": queries,
                "query_to_rows": mapping,
                "target_row_ids": target_ids,
            }
'''
    plan_replacement = '''            required_predicate_descriptions = {
                str(item.get("predicate_id", "")): _normalize_text(
                    str(item.get("description", ""))
                )
                for item in state.get("scope_plan", {}).get(
                    "required_predicates", []
                )
                if isinstance(item, dict)
                and item.get("required") is True
                and re.fullmatch(r"P\\d{2,}", str(item.get("predicate_id", "")))
            }
            rows_by_id_for_query_plan = {
                str(row.get("row_id", "")): row
                for row in (state.get("merged_rows") or {}).get("rows", [])
                if isinstance(row, dict)
                and str(row.get("row_id", "")) in target_ids
            }
            opportunities = []
            membership_subject = resolved_subject_for_state(state)
            for row_id in target_ids:
                row = rows_by_id_for_query_plan.get(row_id)
                if row is None:
                    continue
                predicate_evidence = _normalize_predicate_evidence(
                    row.get("predicate_evidence")
                )
                row_query_identity = _row_query_identity(row, row_identity)
                row_search_identity = _normalize_text(
                    str(
                        row.get("search_identity")
                        or row.get("canonical_identity")
                        or ""
                    )
                )
                for predicate_id, description in (
                    required_predicate_descriptions.items()
                ):
                    if predicate_evidence.get(predicate_id):
                        continue
                    opportunities.append(
                        PredicateQueryOpportunity(
                            row_key=row_id,
                            predicate_key=predicate_id,
                            specific_query=_normalize_text(
                                f'"{row_search_identity or row_query_identity}" '
                                f'"{membership_subject}" "{description}" official'
                            ),
                            shared_query=_normalize_text(
                                f'"{membership_subject}" "{description}" '
                                "official directory list results"
                            ),
                        )
                    )
            fair_schedule = build_predicate_fair_query_schedule(
                baseline_queries=queries,
                baseline_query_to_rows=mapping,
                opportunities=opportunities,
                budget=self.config.membership_gap_query_budget,
            )
            state["membership_gap_query_plan"] = {
                "queries": list(fair_schedule.queries),
                "query_to_rows": {
                    query: list(row_ids)
                    for query, row_ids in fair_schedule.query_to_rows.items()
                },
                "target_row_ids": target_ids,
                "predicate_fair_query_audit": fair_schedule.audit(),
            }
'''
    source = replace_once(
        source,
        plan_anchor,
        plan_replacement,
        "membership-gap query plan",
    )
    output[runtime_path] = source

    preflight = output[preflight_path]
    required_anchor = '        "src/deepwide_agent/shadow_risk.py",\n'
    output[preflight_path] = replace_once(
        preflight,
        required_anchor,
        required_anchor + f'        "{RUNTIME_MODULE}",\n',
        "preflight forward code allowlist",
    )
    output[RUNTIME_MODULE] = _scheduler_module_source()
    output[RUNTIME_TEST] = _integrated_test_source(target_version, target_schema)
    for relative, text in output.items():
        if relative.endswith(".py"):
            ast.parse(text, filename=relative)
    if runtime_identity(output[runtime_path]) != (target_schema, target_version):
        raise RuntimeError("V2.42.08 target identity drifted")
    if (
        output[runtime_path].count("from .v24179 import (\n") != 1
        or output[runtime_path].count("build_predicate_fair_query_schedule(") != 1
        or output[preflight_path].count(f'"{RUNTIME_MODULE}"') != 1
    ):
        raise RuntimeError("V2.42.08 search hook count drifted")
    return output


def _validate_parents(root: Path) -> dict[str, Any]:
    specs = (
        ("v24201_replay", V24201, V24201_SHA256),
        ("v24204_work_order", V24204, V24204_SHA256),
        ("v24206_markdown", V24206, V24206_SHA256),
        ("v24207_scope_alias", V24207, V24207_SHA256),
        ("v24179_scheduler_replay", V24179, V24179_SHA256),
        ("v24180_quality_protocol", V24180, V24180_SHA256),
    )
    values = {
        name: read_object(ordinary(root, path, digest))
        for name, path, digest in specs
    }
    if (
        values["v24201_replay"].get(
            "all_stage_file_maps_byte_exact_to_frozen_publications"
        )
        is not True
        or values["v24201_replay"].get("candidate_tree_materialized") is not False
        or values["v24204_work_order"].get("authorization", {}).get(
            "candidate_code_build_merge_materialization_or_freeze_generation"
        )
        is not False
        or values["v24206_markdown"].get("authorization", {}).get(
            "benchmark_forward_or_full220_launch"
        )
        is not False
        or values["v24207_scope_alias"].get("authorization", {}).get(
            "benchmark_forward_or_full220_launch"
        )
        is not False
        or values["v24179_scheduler_replay"].get("decision", {}).get(
            "zero_api_query_routing_mechanism_supported"
        )
        is not True
        or values["v24179_scheduler_replay"].get("claims", {}).get(
            "shared_query_retrieval_yield_observed"
        )
        is not False
        or values["v24180_quality_protocol"].get("claims", {}).get(
            "search_yield_observed"
        )
        is not False
        or values["v24180_quality_protocol"].get("authorization", {}).get(
            "candidate_build"
        )
        is not False
    ):
        raise RuntimeError("V2.42.08 frozen parent contract drifted")
    return {
        name: {"path": str(path), "sha256": digest}
        for name, path, digest in specs
    }


def _parent_maps() -> dict[tuple[str, str], dict[str, str]]:
    replay, maps = build_replay()
    if replay.get("all_stage_file_maps_byte_exact_to_frozen_publications") is not True:
        raise RuntimeError("V2.42.08 repo-local replay failed")
    schema76_markdown, _ = build_mainline_candidate_files("schema76")
    schema77_markdown, _ = build_mainline_candidate_files("schema77")
    return {
        ("p12", "selected_baseline"): maps["schema68"],
        ("p12", "selected_markdown_candidate"): maps["schema69"],
        ("schema76", "selected_baseline"): maps["schema76"],
        ("schema76", "selected_markdown_candidate"): schema76_markdown,
        ("schema77", "selected_baseline"): maps["schema77"],
        ("schema77", "selected_markdown_candidate"): schema77_markdown,
    }


def build_audit(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve()
    if root != ROOT.resolve():
        raise RuntimeError("V2.42.08 may only audit the canonical workspace")
    parents = _validate_parents(root)
    rows: dict[str, Any] = {}
    for key, before in _parent_maps().items():
        baseline, variant = key
        target_schema = TARGET_SCHEMAS[key]
        parent_identity = runtime_identity(before["src/deepwide_agent/runtime.py"])
        after = patch_search_production(before, target_schema=target_schema)
        after_identity = runtime_identity(after["src/deepwide_agent/runtime.py"])
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
        }
        if set(changed) != required or len(after) != len(before) + 2:
            raise RuntimeError("V2.42.08 candidate delta drifted")
        rows[f"{baseline}:{variant}"] = {
            "baseline_name": baseline,
            "parent_variant": variant,
            "parent_identity": {
                "state_schema_version": parent_identity[0],
                "pipeline_version": parent_identity[1],
            },
            "feasibility_identity": {
                "state_schema_version": after_identity[0],
                "pipeline_version": after_identity[1],
            },
            "delta_files": changed,
            "parent_regular_file_count": len(before),
            "feasibility_regular_file_count": len(after),
            "parent_manifest_sha256": manifest_sha256(text_manifest(before)),
            "feasibility_manifest_sha256": manifest_sha256(text_manifest(after)),
            "single_search_import_and_call": True,
            "same_membership_gap_query_budget": True,
            "query_search_fetch_model_context_token_or_item_budget_increased": False,
            "parent_bytes_modified_outside_declared_delta": False,
            "candidate_or_publication_materialized": False,
        }
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "label_blind": True,
        "frozen_parents": parents,
        "decision_classification": build_search_rebase_manifest(),
        "rebase_feasibility": rows,
        "conclusion": {
            "six_selected_parent_variants_rebase_deterministically": len(rows) == 6,
            "p12_schema76_schema77_baseline_and_markdown_parents_covered": True,
            "scope_alias_requires_no_byte_patch": True,
            "same_query_budget_and_no_new_api_budget": True,
            "v24180_quality_go_still_required_before_publication": True,
            "selected_search_component_publication_available": False,
            "joint_conflict_audit_and_regression_still_absent": True,
        },
        "live_status_gate_result_or_decision_receipt_read": False,
        "runtime_task_state_prediction_or_result_read": False,
        "benchmark_question_answer_evidence_or_url_read": False,
        "mapping_gold_category_question_type_evaluator_score_or_reward_read": False,
        "credential_value_read_persisted_hashed_or_emitted": False,
        "network_model_search_fetch_evaluator_or_api_called": False,
        "candidate_tree_or_package_materialized": False,
        "component_publication_or_implementation_authority_granted": False,
        "package_gate_evaluated_or_launched": False,
        "shared_api_lease_acquired": False,
        "process_signal_restart_resume_rerun_skip_or_selective_retry": False,
        "benchmark_forward_or_full220_launch_allowed": False,
        "leaderboard_submission_or_sota_claim": False,
    }
    encoded = json.dumps(value, sort_keys=True).encode()
    if SECRET_LITERAL.search(encoded) or OPAQUE_ID.search(encoded):
        raise RuntimeError("V2.42.08 receipt would expose forbidden content")
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


def publish_new(path: Path, value: dict[str, Any]) -> None:
    target = path.resolve(strict=False)
    if target != (ROOT / OUTPUT).resolve(strict=False):
        raise RuntimeError("V2.42.08 output path is noncanonical")
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        target.unlink(missing_ok=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(OUTPUT))
    args = parser.parse_args()
    target = Path(args.output)
    target = target if target.is_absolute() else ROOT / target
    value = build_audit()
    publish_new(target, value)
    print(json.dumps({"path": str(target), "sha256": file_sha256(target)}))


if __name__ == "__main__":
    main()
