#!/usr/bin/env python3
"""Replay the published P12/schema-77 DAG from repository-local bytes only.

This is a build-only equivalence audit.  It invokes the original pure patch
functions used by the historical builders, but replaces their sibling-tree
parents with immutable in-memory file maps reconstructed from the canonical
repository.  It never materializes a candidate, runs a benchmark, calls a
service, reads task state, or opens evaluator artifacts.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from scripts import (  # noqa: E402
    build_v24102_markdown_candidate as v102,
    build_v24104_scope_open_candidate as v104,
    build_v24108_post_verification_partial_candidate as v108,
    build_v24127_exact_identity_candidate as v127,
    build_v24132_membership_fresh_candidate as v132,
    build_v24144_p10_relation_candidate as v144,
    build_v24149_combined_candidate as v149,
    build_v24153_scope_combined_candidate as v153,
    build_v24173_predicate_completion_candidate as v173,
)
from scripts.build_v2410_rank_slot_candidate import build_candidate as build_p12  # noqa: E402


ROLE = "v24201_repo_local_candidate_dag_replay"
OUTPUT = Path("results/v24201_repo_local_candidate_dag_replay_v1_20260731.json")
SECRET_LITERAL = __import__("re").compile(
    rb"(?:ghp_|github_pat_|tvly-(?:dev-)?|sk-)[A-Za-z0-9_-]{16,}"
)
OPAQUE_ID = __import__("re").compile(rb"task_[0-9a-f]{24}")


@dataclass(frozen=True)
class Publication:
    path: str
    sha256: str


PUBLICATIONS = {
    "schema68": Publication(
        "results/v2410_rank_slot_candidate_publication_v4_20260727.json",
        "e7dee0a2f8b8b2ed55e318aeed1c383bcc7fdfbae226dd8732c1d2eb5a2c1675",
    ),
    "schema71": Publication(
        "results/v24108_post_verification_partial_candidate_publication_v1_20260729.json",
        "5672848572a79afba0b5a183c2349f07fbb9b16723a5e3f0fe5ad592083f0a01",
    ),
    "schema72": Publication(
        "results/v24127_exact_identity_candidate_publication_v1_20260729.json",
        "9f3dbda585fb47b626247b168cdff3badb5756966d8010fe68df149e555ff762",
    ),
    "schema73": Publication(
        "results/v24132_membership_fresh_candidate_publication_v1_20260729.json",
        "44bfde2a3cd2975888e1d2a63521dc7ef91c3d3ae199666510ccdbe180bed5c4",
    ),
    "schema74": Publication(
        "results/v24144_p10_relation_candidate_publication_v1_20260729.json",
        "c38841651a649fdcd37f32e7f1a85facd69c6315b06ef3afe85ff4ddf764cb15",
    ),
    "schema75": Publication(
        "results/v24149_combined_execution_candidate_publication_v1_20260729.json",
        "cdad8aacedb686dce4d63b443cb003cf0bbeab598deb3ec87152a7b1fa715f08",
    ),
    "schema76": Publication(
        "results/v24153_scope_combined_execution_candidate_publication_v1_20260729.json",
        "fbfb673ed5beab6e3dfed6782e578414e5e44ee0b76a2883d4f7522b7ea809e3",
    ),
    "schema77": Publication(
        "results/v24173_predicate_completion_candidate_publication_v1_20260729.json",
        "7320ef2070a199ecbfe4e89c0ef7593650884356b4867938632e50983c5c83ca",
    ),
    "schema69": Publication(
        "results/v24102_markdown_candidate_publication_v1_20260728.json",
        "c0d1af9d54b654fbb413601bfbbe1e1a3921e7c60153028ccdc4138c7f578c92",
    ),
    "schema70": Publication(
        "results/v24104_scope_open_candidate_publication_v1_20260729.json",
        "3eb5d71445a9e19cc4c8328f89b2c5e59616e4a2bfa489a72a9f7f51f02acdc5",
    ),
}

MATERIALIZED_EMPTY_SUPPORT = frozenset({"scripts/__init__.py", "tests/__init__.py"})


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def text_manifest(files: Mapping[str, str]) -> dict[str, str]:
    return {
        relative: hashlib.sha256(source.encode()).hexdigest()
        for relative, source in sorted(files.items())
    }


def manifest_sha256(manifest: Mapping[str, str]) -> str:
    return payload_sha256(dict(manifest))


def read_publication(spec: Publication) -> dict[str, Any]:
    path = ROOT / spec.path
    if (
        path.resolve(strict=False) != path.absolute()
        or path.is_symlink()
        or not path.is_file()
        or file_sha256(path) != spec.sha256
    ):
        raise RuntimeError(f"V2.42.01 publication drifted: {spec.path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.42.01 publication is not one object")
    return value


def publication_manifest(value: Mapping[str, Any]) -> dict[str, str]:
    direct = value.get("candidate_regular_file_manifest")
    if isinstance(direct, dict):
        manifest = dict(sorted((str(k), str(v)) for k, v in direct.items()))
    else:
        generated = value.get("generated_file_manifest")
        support = value.get("support_file_manifest")
        if not isinstance(generated, dict) or not isinstance(support, dict):
            raise RuntimeError("V2.42.01 publication has no complete manifest")
        manifest = dict(
            sorted(
                (str(k), str(v))
                for k, v in {**support, **generated}.items()
            )
        )
    if (
        len(manifest) != value.get("candidate_regular_file_count")
        or manifest_sha256(manifest)
        != value.get("candidate_regular_file_manifest_sha256")
    ):
        raise RuntimeError("V2.42.01 publication manifest is internally invalid")
    return manifest


def repository_support_files(value: Mapping[str, Any]) -> dict[str, str]:
    """Reconstruct frozen support bytes without opening a candidate tree."""

    expected = value.get("support_file_manifest")
    if not isinstance(expected, dict) or not expected:
        raise RuntimeError("V2.42.01 publication has no support manifest")
    files = {
        str(relative): (
            "" if str(relative) in MATERIALIZED_EMPTY_SUPPORT else repo_text(str(relative))
        )
        for relative in expected
    }
    if text_manifest(files) != dict(sorted((str(k), str(v)) for k, v in expected.items())):
        raise RuntimeError("V2.42.01 repository support bytes drifted")
    return files


def repo_text(relative: str) -> str:
    path = ROOT / relative
    if (
        Path(relative).is_absolute()
        or ".." in Path(relative).parts
        or path.resolve(strict=False) != path.absolute()
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(ROOT)
    ):
        raise RuntimeError(f"V2.42.01 noncanonical repository source: {relative}")
    return path.read_text(encoding="utf-8")


def parse_all(files: Mapping[str, str]) -> None:
    for relative, source in files.items():
        if relative.endswith(".py"):
            ast.parse(source, filename=relative)


def assert_matches(
    name: str, files: Mapping[str, str], publications: Mapping[str, dict[str, Any]]
) -> dict[str, Any]:
    manifest = text_manifest(files)
    expected = publication_manifest(publications[name])
    if manifest != expected:
        differing = sorted(
            relative
            for relative in set(manifest) | set(expected)
            if manifest.get(relative) != expected.get(relative)
        )
        raise RuntimeError(
            f"V2.42.01 {name} replay differs from publication: {differing[:12]}"
        )
    parse_all(files)
    return {
        "state_schema_version": publications[name]["target_state_schema_version"],
        "file_count": len(manifest),
        "manifest_sha256": manifest_sha256(manifest),
        "publication": {
            "path": PUBLICATIONS[name].path,
            "sha256": PUBLICATIONS[name].sha256,
        },
        "byte_exact": True,
    }


def _changed(parent: Mapping[str, str], files: Mapping[str, str]) -> list[str]:
    return sorted(
        relative
        for relative in set(parent) | set(files)
        if parent.get(relative) != files.get(relative)
    )


def _expect_changed(actual: list[str], expected: set[str], name: str) -> None:
    if actual != sorted(expected):
        raise RuntimeError(f"V2.42.01 {name} delta drifted: {actual}")


def linear_successor(
    parent: Mapping[str, str],
    *,
    module: Any,
    pure_sources: Mapping[str, str],
    integrated_sources: Mapping[str, str],
    guard: Callable[[dict[str, str]], None],
    expected_changed: set[str],
) -> dict[str, str]:
    files = dict(parent)
    files.update(pure_sources)
    files.update(integrated_sources)
    files["src/deepwide_agent/runtime.py"] = module.patch_runtime(
        files["src/deepwide_agent/runtime.py"]
    )
    files["scripts/preflight_deepwide.py"] = module.patch_preflight(
        files["scripts/preflight_deepwide.py"]
    )
    guard(files)
    parse_all(files)
    _expect_changed(_changed(parent, files), expected_changed, module.__name__)
    return files


def build_schema71(parent: Mapping[str, str]) -> dict[str, str]:
    files = dict(parent)
    files["src/deepwide_agent/runtime.py"] = v108.patch_runtime(files["src/deepwide_agent/runtime.py"])
    files["scripts/preflight_deepwide.py"] = v108.patch_preflight(files["scripts/preflight_deepwide.py"])
    for relative in (
        "tests/test_v2406_integrated_bridge_completion.py",
        "tests/test_v2407_integrated_anchor_completion.py",
        "tests/test_v2408_integrated_fresh_stage_evidence.py",
    ):
        files[relative] = v108._extend_version_guard(files[relative], relative)
    rank = files["tests/test_v2410_integrated_rank_slot_recovery.py"]
    files["tests/test_v2410_integrated_rank_slot_recovery.py"] = rank.replace(
        'PIPELINE_VERSION.endswith("-fixed-rank-occupant-recovery")',
        'PIPELINE_VERSION.endswith("-fixed-rank-occupant-recovery")\n'
        '            or PIPELINE_VERSION.endswith('
        '"-post-verification-positive-partial-release")',
    ).replace(
        "self.assertEqual(STATE_SCHEMA_VERSION, 68)",
        "self.assertIn(STATE_SCHEMA_VERSION, {68, 71})",
    )
    files[v108.PURE_MODULE] = repo_text(v108.PURE_MODULE)
    files[v108.PURE_TEST] = repo_text(v108.PURE_TEST)
    files[v108.INTEGRATED_TEST] = v108.INTEGRATED_TEST_SOURCE
    expected = {
        "scripts/preflight_deepwide.py", "src/deepwide_agent/runtime.py",
        v108.PURE_MODULE, v108.PURE_TEST, v108.INTEGRATED_TEST,
        "tests/test_v2406_integrated_bridge_completion.py",
        "tests/test_v2407_integrated_anchor_completion.py",
        "tests/test_v2408_integrated_fresh_stage_evidence.py",
        "tests/test_v2410_integrated_rank_slot_recovery.py",
    }
    _expect_changed(_changed(parent, files), expected, "schema71")
    parse_all(files)
    return files


def build_schema72(parent: Mapping[str, str]) -> dict[str, str]:
    files = dict(parent)
    files["src/deepwide_agent/runtime.py"] = v127.patch_runtime(files["src/deepwide_agent/runtime.py"])
    files["scripts/preflight_deepwide.py"] = v127.patch_preflight(files["scripts/preflight_deepwide.py"])
    for relative in (
        "tests/test_v2406_integrated_bridge_completion.py",
        "tests/test_v2407_integrated_anchor_completion.py",
        "tests/test_v2408_integrated_fresh_stage_evidence.py",
    ):
        files[relative] = v127._extend_version_guard(files[relative], relative)
    rank = "tests/test_v2410_integrated_rank_slot_recovery.py"
    files[rank] = v127.replace_once(
        files[rank],
        '            or PIPELINE_VERSION.endswith("-post-verification-positive-partial-release")\n',
        '            or PIPELINE_VERSION.endswith("-post-verification-positive-partial-release")\n'
        '            or PIPELINE_VERSION.endswith("-exact-identity-provenance-merge")\n',
        "rank suffix",
    )
    files[rank] = v127.replace_once(files[rank], "self.assertIn(STATE_SCHEMA_VERSION, {68, 71})", "self.assertIn(STATE_SCHEMA_VERSION, {68, 71, 72})", "rank schema")
    partial = "tests/test_v24108_integrated_post_verification_partial_release.py"
    files[partial] = v127.replace_once(
        files[partial],
        '            PIPELINE_VERSION.endswith(\n                "-post-verification-positive-partial-release"\n            )\n',
        '            PIPELINE_VERSION.endswith(\n                "-post-verification-positive-partial-release"\n            )\n'
        '            or PIPELINE_VERSION.endswith(\n                "-exact-identity-provenance-merge"\n            )\n',
        "partial suffix",
    )
    files[partial] = v127.replace_once(files[partial], "self.assertEqual(STATE_SCHEMA_VERSION, 71)", "self.assertIn(STATE_SCHEMA_VERSION, {71, 72})", "partial schema")
    files[v127.PURE_MODULE] = repo_text(v127.PURE_MODULE_SOURCE)
    files[v127.PURE_TEST] = repo_text(v127.PURE_TEST).replace(
        "from scripts.prototype_v24127_exact_identity_merge import (",
        "from src.deepwide_agent.v24127 import (",
    )
    files[v127.INTEGRATED_TEST] = v127.INTEGRATED_TEST_SOURCE
    expected = {
        "scripts/preflight_deepwide.py", "src/deepwide_agent/runtime.py",
        v127.PURE_MODULE, v127.PURE_TEST, v127.INTEGRATED_TEST, rank, partial,
        "tests/test_v2406_integrated_bridge_completion.py",
        "tests/test_v2407_integrated_anchor_completion.py",
        "tests/test_v2408_integrated_fresh_stage_evidence.py",
    }
    _expect_changed(_changed(parent, files), expected, "schema72")
    parse_all(files)
    return files


def build_schema73(parent: Mapping[str, str]) -> dict[str, str]:
    files = dict(parent)
    files["src/deepwide_agent/runtime.py"] = v132.patch_runtime(files["src/deepwide_agent/runtime.py"])
    files["scripts/preflight_deepwide.py"] = v132.patch_preflight(files["scripts/preflight_deepwide.py"])
    for relative in (
        "tests/test_v2406_integrated_bridge_completion.py",
        "tests/test_v2407_integrated_anchor_completion.py",
        "tests/test_v2408_integrated_fresh_stage_evidence.py",
    ):
        files[relative] = v132._extend_version_guard(files[relative], relative)
    rank = files["tests/test_v2410_integrated_rank_slot_recovery.py"]
    files["tests/test_v2410_integrated_rank_slot_recovery.py"] = rank.replace(
        'PIPELINE_VERSION.endswith("-fixed-rank-occupant-recovery")',
        'PIPELINE_VERSION.endswith("-fixed-rank-occupant-recovery")\n'
        '            or PIPELINE_VERSION.endswith('
        '"-membership-gap-fresh-evidence-priority")',
    ).replace("self.assertEqual(STATE_SCHEMA_VERSION, 68)", "self.assertIn(STATE_SCHEMA_VERSION, {68, 73})")
    files[v132.PURE_MODULE] = repo_text(v132.PURE_MODULE_SOURCE)
    files[v132.PURE_TEST] = repo_text("tests/test_prototype_v24132_membership_fresh_evidence.py").replace(
        "from scripts.prototype_v24132_membership_fresh_evidence import (",
        "from src.deepwide_agent.v24132 import (",
    )
    files[v132.INTEGRATED_TEST] = v132.INTEGRATED_TEST_SOURCE
    expected = {
        "scripts/preflight_deepwide.py", "src/deepwide_agent/runtime.py",
        v132.PURE_MODULE, v132.PURE_TEST, v132.INTEGRATED_TEST,
        "tests/test_v2406_integrated_bridge_completion.py",
        "tests/test_v2407_integrated_anchor_completion.py",
        "tests/test_v2408_integrated_fresh_stage_evidence.py",
        "tests/test_v2410_integrated_rank_slot_recovery.py",
    }
    _expect_changed(_changed(parent, files), expected, "schema73")
    parse_all(files)
    return files


def build_schema74(parent: Mapping[str, str]) -> dict[str, str]:
    files = dict(parent)
    files["src/deepwide_agent/runtime.py"] = v144.patch_runtime(files["src/deepwide_agent/runtime.py"])
    files["scripts/preflight_deepwide.py"] = v144.patch_preflight(files["scripts/preflight_deepwide.py"])
    for relative in (
        "tests/test_v2406_integrated_bridge_completion.py",
        "tests/test_v2407_integrated_anchor_completion.py",
        "tests/test_v2408_integrated_fresh_stage_evidence.py",
    ):
        files[relative] = v144._extend_version_guard(files[relative], relative)
    rank = files["tests/test_v2410_integrated_rank_slot_recovery.py"]
    files["tests/test_v2410_integrated_rank_slot_recovery.py"] = rank.replace(
        'PIPELINE_VERSION.endswith("-fixed-rank-occupant-recovery")',
        'PIPELINE_VERSION.endswith("-fixed-rank-occupant-recovery")\n'
        '            or PIPELINE_VERSION.endswith('
        '"-relation-aware-anchor-completion")',
    ).replace("self.assertEqual(STATE_SCHEMA_VERSION, 68)", "self.assertIn(STATE_SCHEMA_VERSION, {68, 74})")
    files[v144.PURE_MODULE] = repo_text(v144.PURE_MODULE_SOURCE)
    files[v144.PURE_TEST] = repo_text(v144.PURE_TEST).replace(
        "from scripts.prototype_v24144_p10_relation_aware import (",
        "from src.deepwide_agent.v24144 import (",
    )
    files[v144.INTEGRATED_TEST] = v144.INTEGRATED_TEST_SOURCE
    expected = {
        "scripts/preflight_deepwide.py", "src/deepwide_agent/runtime.py",
        v144.PURE_MODULE, v144.PURE_TEST, v144.INTEGRATED_TEST,
        "tests/test_v2406_integrated_bridge_completion.py",
        "tests/test_v2407_integrated_anchor_completion.py",
        "tests/test_v2408_integrated_fresh_stage_evidence.py",
        "tests/test_v2410_integrated_rank_slot_recovery.py",
    }
    _expect_changed(_changed(parent, files), expected, "schema74")
    parse_all(files)
    return files


def build_schema75(
    parent: Mapping[str, str], membership: Mapping[str, str], relation: Mapping[str, str]
) -> dict[str, str]:
    files = dict(parent)
    for relative in (v149.MEMBERSHIP_MODULE, v149.MEMBERSHIP_TEST, v149.MEMBERSHIP_INTEGRATED_TEST):
        files[relative] = membership[relative]
    for relative in (v149.RELATION_MODULE, v149.RELATION_TEST, v149.RELATION_INTEGRATED_TEST):
        files[relative] = relation[relative]
    files["src/deepwide_agent/runtime.py"] = v149.patch_runtime(files["src/deepwide_agent/runtime.py"])
    files["scripts/preflight_deepwide.py"] = v149.patch_preflight(files["scripts/preflight_deepwide.py"])
    v149._extend_parent_test_guards(files)
    v149._patch_successor_integrated_tests(files)
    files[v149.COMBINED_TEST] = v149.COMBINED_TEST_SOURCE
    expected = {
        "scripts/preflight_deepwide.py", "src/deepwide_agent/runtime.py",
        v149.MEMBERSHIP_MODULE, v149.MEMBERSHIP_TEST, v149.MEMBERSHIP_INTEGRATED_TEST,
        v149.RELATION_MODULE, v149.RELATION_TEST, v149.RELATION_INTEGRATED_TEST,
        v149.COMBINED_TEST,
        "tests/test_v2406_integrated_bridge_completion.py",
        "tests/test_v2407_integrated_anchor_completion.py",
        "tests/test_v2408_integrated_fresh_stage_evidence.py",
        "tests/test_v2410_integrated_rank_slot_recovery.py",
        "tests/test_v24108_integrated_post_verification_partial_release.py",
        "tests/test_v24127_integrated_exact_identity_merge.py",
    }
    _expect_changed(_changed(parent, files), expected, "schema75")
    parse_all(files)
    return files


def build_schema76(parent: Mapping[str, str], scope70: Mapping[str, str]) -> dict[str, str]:
    files = dict(parent)
    for relative in (v153.SCOPE_MODULE, v153.SCOPE_TEST, v153.SCOPE_INTEGRATED_TEST):
        files[relative] = scope70[relative]
    files[v153.SCOPE_INTEGRATED_TEST] = v153.replace_once(
        files[v153.SCOPE_INTEGRATED_TEST],
        "self.assertEqual(STATE_SCHEMA_VERSION, 70)",
        "self.assertEqual(STATE_SCHEMA_VERSION, 76)",
        "scope integrated schema",
    )
    files["src/deepwide_agent/runtime.py"] = v153.patch_runtime(files["src/deepwide_agent/runtime.py"])
    files["scripts/preflight_deepwide.py"] = v153.patch_preflight(files["scripts/preflight_deepwide.py"])
    v153._patch_version_guards(files)
    expected = {
        "scripts/preflight_deepwide.py", "src/deepwide_agent/runtime.py",
        v153.SCOPE_MODULE, v153.SCOPE_TEST, v153.SCOPE_INTEGRATED_TEST,
        "tests/test_v2406_integrated_bridge_completion.py",
        "tests/test_v2407_integrated_anchor_completion.py",
        "tests/test_v2408_integrated_fresh_stage_evidence.py",
        "tests/test_v2410_integrated_rank_slot_recovery.py",
        "tests/test_v24108_integrated_post_verification_partial_release.py",
        "tests/test_v24127_integrated_exact_identity_merge.py",
        "tests/test_v24132_integrated_membership_fresh_evidence.py",
        "tests/test_v24144_integrated_p10_relation_aware.py",
        "tests/test_v24149_integrated_combined_candidate.py",
    }
    _expect_changed(_changed(parent, files), expected, "schema76")
    parse_all(files)
    return files


def build_schema77(parent: Mapping[str, str]) -> dict[str, str]:
    files = dict(parent)
    files[v173.PREDICATE_MODULE] = v173.PREDICATE_MODULE_SOURCE
    files[v173.PREDICATE_TEST] = v173.PREDICATE_TEST_SOURCE
    files[v173.PREDICATE_INTEGRATED_TEST] = v173.PREDICATE_INTEGRATED_TEST_SOURCE
    files["src/deepwide_agent/runtime.py"] = v173.patch_runtime(files["src/deepwide_agent/runtime.py"])
    files["scripts/preflight_deepwide.py"] = v173.patch_preflight(files["scripts/preflight_deepwide.py"])
    v173._patch_version_guards(files)
    expected = {
        "scripts/preflight_deepwide.py", "src/deepwide_agent/runtime.py",
        v173.PREDICATE_MODULE, v173.PREDICATE_TEST, v173.PREDICATE_INTEGRATED_TEST,
        "tests/test_v2406_integrated_bridge_completion.py",
        "tests/test_v2407_integrated_anchor_completion.py",
        "tests/test_v2408_integrated_fresh_stage_evidence.py",
        "tests/test_v2410_integrated_rank_slot_recovery.py",
        "tests/test_v24108_integrated_post_verification_partial_release.py",
        "tests/test_v24127_integrated_exact_identity_merge.py",
        "tests/test_v24132_integrated_membership_fresh_evidence.py",
        "tests/test_v24144_integrated_p10_relation_aware.py",
        "tests/test_v24149_integrated_combined_candidate.py",
        "tests/test_v24104_integrated_scope_open_fallback.py",
    }
    _expect_changed(_changed(parent, files), expected, "schema77")
    parse_all(files)
    return files


def build_schema69(parent: Mapping[str, str]) -> dict[str, str]:
    files = dict(parent)
    files["src/deepwide_agent/runtime.py"] = v102.patch_runtime(files["src/deepwide_agent/runtime.py"])
    files["scripts/preflight_deepwide.py"] = v102.patch_preflight(files["scripts/preflight_deepwide.py"])
    for relative in (
        "tests/test_v2406_integrated_bridge_completion.py",
        "tests/test_v2407_integrated_anchor_completion.py",
        "tests/test_v2408_integrated_fresh_stage_evidence.py",
    ):
        files[relative] = v102._extend_version_guard(files[relative], relative)
    rank = "tests/test_v2410_integrated_rank_slot_recovery.py"
    files[rank] = v102.replace_once(
        files[rank],
        '        self.assertTrue(PIPELINE_VERSION.startswith("v2.41.0-"))\n'
        '        self.assertTrue(\n            PIPELINE_VERSION.endswith("-fixed-rank-occupant-recovery")\n        )\n'
        '        self.assertEqual(STATE_SCHEMA_VERSION, 68)',
        f'        self.assertEqual(PIPELINE_VERSION, "{v102.TARGET_PIPELINE_VERSION}")\n'
        '        self.assertEqual(STATE_SCHEMA_VERSION, 69)',
        "P12 version test",
    )
    files[v102.PURE_MODULE] = repo_text(v102.PURE_MODULE)
    files[v102.PURE_TEST] = repo_text(v102.PURE_TEST)
    files[v102.INTEGRATED_TEST] = v102.INTEGRATED_TEST_SOURCE
    expected = {
        "scripts/preflight_deepwide.py", "src/deepwide_agent/runtime.py",
        v102.PURE_MODULE, v102.PURE_TEST, v102.INTEGRATED_TEST, rank,
        "tests/test_v2406_integrated_bridge_completion.py",
        "tests/test_v2407_integrated_anchor_completion.py",
        "tests/test_v2408_integrated_fresh_stage_evidence.py",
    }
    _expect_changed(_changed(parent, files), expected, "schema69")
    parse_all(files)
    return files


def build_schema70(parent: Mapping[str, str]) -> dict[str, str]:
    files = dict(parent)
    files["src/deepwide_agent/runtime.py"] = v104.patch_runtime(files["src/deepwide_agent/runtime.py"])
    files["scripts/preflight_deepwide.py"] = v104.patch_preflight(files["scripts/preflight_deepwide.py"])
    for relative in (
        "tests/test_v2406_integrated_bridge_completion.py",
        "tests/test_v2407_integrated_anchor_completion.py",
        "tests/test_v2408_integrated_fresh_stage_evidence.py",
    ):
        files[relative] = v104._extend_version_guard(files[relative], relative)
    for relative in (
        "tests/test_v2410_integrated_rank_slot_recovery.py",
        "tests/test_v24102_integrated_markdown_rank_slot.py",
    ):
        files[relative] = files[relative].replace(
            v104.PARENT_PIPELINE_VERSION, v104.TARGET_PIPELINE_VERSION
        ).replace("STATE_SCHEMA_VERSION, 69", "STATE_SCHEMA_VERSION, 70")
    files[v104.PURE_MODULE] = repo_text(v104.PURE_MODULE)
    files[v104.PURE_TEST] = repo_text(v104.PURE_TEST)
    files[v104.INTEGRATED_TEST] = v104.INTEGRATED_TEST_SOURCE
    expected = {
        "scripts/preflight_deepwide.py", "src/deepwide_agent/runtime.py",
        v104.PURE_MODULE, v104.PURE_TEST, v104.INTEGRATED_TEST,
        "tests/test_v2406_integrated_bridge_completion.py",
        "tests/test_v2407_integrated_anchor_completion.py",
        "tests/test_v2408_integrated_fresh_stage_evidence.py",
        "tests/test_v2410_integrated_rank_slot_recovery.py",
        "tests/test_v24102_integrated_markdown_rank_slot.py",
    }
    _expect_changed(_changed(parent, files), expected, "schema70")
    parse_all(files)
    return files


def build_replay() -> tuple[dict[str, Any], dict[str, dict[str, str]]]:
    publications = {name: read_publication(spec) for name, spec in PUBLICATIONS.items()}
    p12, p12_report = build_p12(ROOT)
    schema68 = dict(p12)
    support = repository_support_files(publications["schema68"])
    if set(schema68) & set(support):
        raise RuntimeError("V2.42.01 generated and support file sets overlap")
    schema68.update(support)
    maps: dict[str, dict[str, str]] = {"schema68": schema68}
    maps["schema71"] = build_schema71(maps["schema68"])
    maps["schema72"] = build_schema72(maps["schema71"])
    maps["schema73"] = build_schema73(maps["schema68"])
    maps["schema74"] = build_schema74(maps["schema68"])
    maps["schema75"] = build_schema75(maps["schema72"], maps["schema73"], maps["schema74"])
    maps["schema69"] = build_schema69(maps["schema68"])
    maps["schema70"] = build_schema70(maps["schema69"])
    maps["schema76"] = build_schema76(maps["schema75"], maps["schema70"])
    maps["schema77"] = build_schema77(maps["schema76"])

    stages = {name: assert_matches(name, files, publications) for name, files in maps.items()}
    if p12_report.get("mapping_gold_category_evaluator_score_or_outcome_read") is not False:
        raise RuntimeError("V2.42.01 P12 build boundary drifted")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "label_blind": True,
        "build_only": True,
        "root": str(ROOT),
        "dag": {
            "schema68": [],
            "schema71": ["schema68"],
            "schema72": ["schema71"],
            "schema73": ["schema68"],
            "schema74": ["schema68"],
            "schema75": ["schema72", "schema73", "schema74"],
            "schema69": ["schema68"],
            "schema70": ["schema69"],
            "schema76": ["schema75", "schema70"],
            "schema77": ["schema76"],
        },
        "stages": stages,
        "all_stage_file_maps_byte_exact_to_frozen_publications": True,
        "sibling_candidate_tree_read": False,
        "candidate_tree_materialized": False,
        "runtime_task_state_prediction_or_result_read": False,
        "mapping_gold_category_question_type_evaluator_score_read": False,
        "credential_value_read_persisted_hashed_or_emitted": False,
        "network_model_search_fetch_evaluator_or_api_called": False,
        "benchmark_forward_or_full220_launch_allowed": False,
        "leaderboard_submission_or_sota_claim": False,
    }
    encoded = json.dumps(value, sort_keys=True).encode()
    if SECRET_LITERAL.search(encoded) or OPAQUE_ID.search(encoded):
        raise RuntimeError("V2.42.01 receipt would expose forbidden content")
    value["replay_payload_sha256"] = payload_sha256(value)
    return value, maps


def publish_new(path: Path, value: dict[str, Any]) -> None:
    target = path.resolve(strict=False)
    if target != (ROOT / OUTPUT).resolve(strict=False) or not target.is_relative_to(ROOT / "results"):
        raise RuntimeError("V2.42.01 output path is noncanonical")
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
    value, _ = build_replay()
    publish_new(target, value)
    print(json.dumps({"path": str(target), "sha256": file_sha256(target), "stages": len(value["stages"])}))


if __name__ == "__main__":
    main()
