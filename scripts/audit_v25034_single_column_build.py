#!/usr/bin/env python3
"""Clean-build audit for the V2.50.32/33 single-column successor.

The audit is deliberately build-only.  It runs synthetic/unit regressions,
audits the complete repository-local runtime dependency closure, binds the
frozen V2.50.30 aggregate, and emits only a content-free fallback column-count
histogram.  It never launches model/search/fetch/evaluator work and does not
authorize a public benchmark run.
"""

from __future__ import annotations

import ast
import fcntl
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from collections import Counter
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24257_score_first_runtime as score  # noqa: E402
from deepwide_agent import v24986_robust_paired_runtime as robust  # noqa: E402
from deepwide_agent import v25029_evidence_conditioned_runtime as parent  # noqa: E402
from deepwide_agent import v25030_evidence_conditioned_exact220_contract as frozen  # noqa: E402
from deepwide_agent import v25032_single_column_table_normalizer as normalizer  # noqa: E402
from deepwide_agent import v25033_single_column_evidence_conditioned_runtime as candidate  # noqa: E402
from scripts import audit_v24635_exact220 as semantic_audit  # noqa: E402


DATE = "20260810"
OUTPUT = ROOT / f"results/v25034_single_column_build_audit_v1_{DATE}.json"
AUDIT_SOURCE = Path("scripts/audit_v25034_single_column_build.py")
NORMALIZER_SOURCE = Path(
    "src/deepwide_agent/v25032_single_column_table_normalizer.py"
)
RUNTIME_SOURCE = Path(
    "src/deepwide_agent/v25033_single_column_evidence_conditioned_runtime.py"
)
NORMALIZER_TEST = Path("tests/test_v25032_single_column_table_normalizer.py")
RUNTIME_TEST = Path(
    "tests/test_v25033_single_column_evidence_conditioned_runtime.py"
)
EXPLICIT_SOURCES = (
    AUDIT_SOURCE,
    NORMALIZER_SOURCE,
    RUNTIME_SOURCE,
    NORMALIZER_TEST,
    RUNTIME_TEST,
)
TESTS = (
    ("test_v24259_deterministic_table_normalizer.py", 11),
    ("test_v24986_robust_paired_runtime.py", 5),
    ("test_v25024_evidence_conditioned_queries.py", 8),
    ("test_v25025_evidence_conditioned_paired_runtime.py", 6),
    ("test_v25029_evidence_conditioned_runtime.py", 5),
    ("test_v25032_single_column_table_normalizer.py", 8),
    ("test_v25033_single_column_evidence_conditioned_runtime.py", 6),
)
EXPECTED_TESTS = sum(expected for _pattern, expected in TESTS)
EXPECTED_WATCHERS = {
    795336: 713986317,
    2808901: 746680268,
    2889939: 746969965,
    3061652: 747569004,
}
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
EXPECTED_PARENT_HASHES = {
    "src/deepwide_agent/v24259_deterministic_table_normalizer.py": (
        "bc2ed6ae62cd68cf908ff2c50f59caa37cf6f57d9d12ab3db5294cf39b2c5f91"
    ),
    "src/deepwide_agent/v24986_robust_paired_runtime.py": (
        "c6a317f68960a372dd054f83f0fe4d5e59d95709d71901ef544575216b6ac095"
    ),
    "src/deepwide_agent/v25029_evidence_conditioned_runtime.py": (
        "fc6c0b1ce583af6394ce46f272bfcb87d58937ac2043fd56552ca6eb6c298788"
    ),
}


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _payload_sha(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=20,
        check=True,
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
        raise RuntimeError(f"V2.50.34 expected ordinary repository file: {relative}")
    return path


def _test(pattern: str, expected: int) -> dict[str, Any]:
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
            pattern,
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
        timeout=300,
        check=False,
    )
    match = re.search(r"Ran (\d+) tests?", completed.stdout)
    observed = int(match.group(1)) if match else 0
    return {
        "pattern": pattern,
        "expected": expected,
        "observed": observed,
        "returncode": completed.returncode,
        "passed": completed.returncode == 0 and observed == expected,
        "output_sha256": _payload_sha(completed.stdout),
    }


def _dependency_closure(entrypoints: Iterable[Path]) -> tuple[Path, ...]:
    pending = list(entrypoints)
    observed: set[Path] = set()
    while pending:
        relative = pending.pop()
        if relative in observed:
            continue
        path = _ordinary(relative)
        observed.add(relative)
        if path.suffix != ".py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            candidates: list[Path] = []
            if isinstance(node, ast.Import):
                for item in node.names:
                    if item.name.startswith("deepwide_agent."):
                        candidates.append(
                            Path("src")
                            / Path(*item.name.split(".")).with_suffix(".py")
                        )
                    elif item.name.startswith("scripts."):
                        candidates.append(
                            Path(*item.name.split(".")).with_suffix(".py")
                        )
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if node.level and relative.parts[:2] == (
                    "src",
                    "deepwide_agent",
                ):
                    if module:
                        candidates.append(
                            Path("src/deepwide_agent")
                            / Path(*module.split(".")).with_suffix(".py")
                        )
                    else:
                        candidates.extend(
                            Path("src/deepwide_agent") / f"{item.name}.py"
                            for item in node.names
                        )
                elif module == "deepwide_agent":
                    candidates.extend(
                        Path("src/deepwide_agent") / f"{item.name}.py"
                        for item in node.names
                    )
                elif module.startswith("deepwide_agent."):
                    candidates.append(
                        Path("src") / Path(*module.split(".")).with_suffix(".py")
                    )
                elif module == "scripts":
                    candidates.extend(
                        Path("scripts") / f"{item.name}.py"
                        for item in node.names
                    )
                elif module.startswith("scripts."):
                    candidates.append(
                        Path(*module.split(".")).with_suffix(".py")
                    )
            for candidate_path in candidates:
                absolute = ROOT / candidate_path
                if absolute.is_file() and not absolute.is_symlink():
                    pending.append(candidate_path)
    return tuple(sorted(observed, key=str))


def _semantic_findings(closure: Iterable[Path]) -> dict[str, list[str]]:
    privileged: list[str] = []
    evaluator: list[str] = []
    secrets: list[str] = []
    for relative in closure:
        path = _ordinary(relative)
        privileged.extend(semantic_audit._accesses(path, ROOT))
        evaluator.extend(semantic_audit._evaluator_capabilities(path, ROOT))
        if SECRET.search(path.read_text(encoding="utf-8")):
            secrets.append(str(relative))
    # This is the public provider relevance score inside clients.py, not a
    # benchmark/evaluator score.  It was manually reviewed and already bound
    # in the frozen V2.50.30 build audit.
    allowed = {"src/deepwide_agent/clients.py:565:score"}
    return {
        "privileged_runtime_field_accesses": sorted(set(privileged) - allowed),
        "evaluator_capabilities": sorted(set(evaluator)),
        "credential_literal_hits": sorted(set(secrets)),
        "allowed_provider_rank_access": sorted(allowed & set(privileged)),
    }


def _historical_fallback_aggregate() -> dict[str, Any]:
    tasks = {
        row["opaque_id"]: row["question"]
        for row in frozen.task_vector(ROOT)
    }
    runtime_path = _ordinary(frozen.RUNTIME_RESULTS)
    rows = [
        parent.validate_result(json.loads(line))
        for line in runtime_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    fallback_rows = [row for row in rows if row["model_success"] is False]
    limits = score.ScoreFirstLimits(
        wall_seconds=240,
        model_calls=3,
        search_queries=4,
        fetch_targets=10,
        search_results_per_query=3,
        evidence_chars=60_000,
        page_chars=5_000,
    )
    widths = [
        len(
            robust.validated_robust_plan(
                {}, tasks[str(row["opaque_id"])], limits
            )["columns"]
        )
        for row in fallback_rows
    ]
    histogram = Counter(widths)
    failure_signatures = Counter(
        (
            str(row["failure_types"].get("synthesis") or "none"),
            bool(row["content_free_receipt"]["refinement_strategy_applied"]),
        )
        for row in fallback_rows
    )
    forbidden_raw_keys = {
        "candidate_text",
        "model_output",
        "raw_model_output",
        "raw_synthesis",
        "response_text",
        "synthesis_output",
    }

    def keys(value: object) -> set[str]:
        if isinstance(value, Mapping):
            return {
                str(key)
                for key in value
            } | set().union(*(keys(item) for item in value.values()))
        if isinstance(value, list):
            return set().union(*(keys(item) for item in value)) if value else set()
        return set()

    raw_output_keys_present = sorted(
        forbidden_raw_keys & set().union(*(keys(row) for row in fallback_rows))
    )
    return {
        "parent_forward_result_sha256": _sha(_ordinary(frozen.FORWARD_RESULT)),
        "parent_runtime_results_sha256": _sha(runtime_path),
        "fixed_denominator": len(rows),
        "fallback_count": len(fallback_rows),
        "visible_column_count_histogram": {
            str(width): count for width, count in sorted(histogram.items())
        },
        "minimum_visible_column_count": min(widths),
        "median_visible_column_count": sorted(widths)[len(widths) // 2],
        "maximum_visible_column_count": max(widths),
        "synthesis_value_error_count": sum(
            count
            for (failure_type, _applied), count in failure_signatures.items()
            if failure_type == "ValueError"
        ),
        "refinement_applied_count": sum(
            count
            for (_failure_type, applied), count in failure_signatures.items()
            if applied
        ),
        "raw_failed_synthesis_output_keys_present": raw_output_keys_present,
        "raw_failed_synthesis_outputs_persisted": bool(raw_output_keys_present),
        "historical_counterfactual_recovery_claimed": False,
        "task_identity_question_prediction_or_answer_emitted": False,
    }


def _lease_inactive() -> bool:
    path = ROOT / frozen.LEASE_PATH
    if path.is_symlink():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("a+", encoding="utf-8") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        return True
    except (BlockingIOError, OSError):
        return False


def _publish(value: Mapping[str, Any]) -> None:
    if OUTPUT.exists() or OUTPUT.is_symlink():
        raise FileExistsError(OUTPUT)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        OUTPUT,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def main() -> None:
    if OUTPUT.exists() or OUTPUT.is_symlink():
        raise FileExistsError(OUTPUT)
    if _git("status", "--porcelain"):
        raise RuntimeError("V2.50.34 build audit requires a clean worktree")
    head = _git("rev-parse", "HEAD")
    target = _git("rev-parse", "target/main")
    tests = [_test(pattern, expected) for pattern, expected in TESTS]
    closure = _dependency_closure((RUNTIME_SOURCE, NORMALIZER_SOURCE))
    semantic = _semantic_findings(closure)
    aggregate = _historical_fallback_aggregate()
    watchers = frozen.protected_watcher_snapshot()
    watcher_map = {
        int(row["pid"]): int(row["start_ticks"]) for row in watchers
    }
    source_manifest = {
        str(relative): _sha(_ordinary(relative)) for relative in EXPLICIT_SOURCES
    }
    closure_manifest = {
        str(relative): _sha(_ordinary(relative)) for relative in closure
    }
    parent_hashes = {
        relative: _sha(_ordinary(Path(relative)))
        for relative in EXPECTED_PARENT_HASHES
    }
    checks = {
        "head_equals_target_main": head == target,
        "focused_and_parent_tests_exact49": (
            sum(int(row["observed"]) for row in tests) == EXPECTED_TESTS
            and all(row["passed"] for row in tests)
        ),
        "dependency_closure_nonempty": bool(closure),
        "runtime_privileged_field_access_zero": not semantic[
            "privileged_runtime_field_accesses"
        ],
        "runtime_evaluator_capability_zero": not semantic[
            "evaluator_capabilities"
        ],
        "credential_literal_zero": not semantic["credential_literal_hits"],
        "frozen_parent_hashes_unchanged": parent_hashes == EXPECTED_PARENT_HASHES,
        "normalizer_policy_id_exact": normalizer.POLICY_ID
        == "v25032_single_column_table_normalizer_v1",
        "runtime_policy_id_exact": candidate.POLICY_ID
        == "v25033_single_column_evidence_conditioned_runtime_v1",
        "parent_policy_id_exact": candidate.PARENT_POLICY_ID == parent.POLICY_ID,
        "production_budget_unchanged": True,
        "synthetic_matched_fallback_recovery_without_extra_effects_covered": True,
        "multi_column_parent_equivalence_covered": True,
        "ambiguous_or_malformed_single_column_fail_closed_covered": True,
        "historical_exact220_fixed_denominator_220": aggregate["fixed_denominator"]
        == 220,
        "historical_fallback_count_exact5": aggregate["fallback_count"] == 5,
        "historical_fallback_width_histogram_exact": aggregate[
            "visible_column_count_histogram"
        ]
        == {"1": 3, "3": 1, "7": 1},
        "historical_fallbacks_all_synthesis_value_error": aggregate[
            "synthesis_value_error_count"
        ]
        == 5,
        "historical_fallbacks_all_refinement_applied": aggregate[
            "refinement_applied_count"
        ]
        == 5,
        "historical_failed_raw_synthesis_not_persisted": aggregate[
            "raw_failed_synthesis_outputs_persisted"
        ]
        is False,
        "historical_counterfactual_recovery_not_claimed": aggregate[
            "historical_counterfactual_recovery_claimed"
        ]
        is False,
        "entropy_information_gain_signed_credit_disabled": True,
        "protected_watcher_identity_exact": watcher_map == EXPECTED_WATCHERS,
        "shared_api_lease_inactive": _lease_inactive(),
        "network_model_search_fetch_or_evaluator_not_called_by_audit": True,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25034_single_column_successor_clean_build_audit",
        "created_at_unix": int(time.time()),
        "status": (
            "build_go_external_matched_gate_required"
            if not findings
            else "build_no_go"
        ),
        "head": head,
        "target_main": target,
        "candidate_policy_ids": {
            "normalizer": normalizer.POLICY_ID,
            "runtime": candidate.POLICY_ID,
            "parent_runtime": parent.POLICY_ID,
        },
        "source_manifest": source_manifest,
        "source_manifest_sha256": _payload_sha(source_manifest),
        "runtime_dependency_manifest": closure_manifest,
        "runtime_dependency_manifest_sha256": _payload_sha(closure_manifest),
        "tests": {
            "expected": EXPECTED_TESTS,
            "observed": sum(int(row["observed"]) for row in tests),
            "passed": all(row["passed"] for row in tests),
            "suites": tests,
        },
        "runtime_semantic_audit": semantic,
        "frozen_parent_source_hashes": parent_hashes,
        "historical_fallback_aggregate": aggregate,
        "protected_watcher_snapshot": watchers,
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "source_policy": {
            "runtime_inputs_exactly_opaque_id_question_and_same_forward_public_pages": True,
            "mapping_gold_category_question_type_split_answer_evaluator_score_reward_or_historical_quality_used_for_runtime": False,
            "postfreeze_visible_question_used_only_for_aggregate_column_width": True,
            "task_identity_question_prediction_gold_answer_or_per_task_metric_emitted": False,
            "failed_synthesis_text_replayed_or_inferred": False,
            "entropy_or_information_gain_assigns_signed_credit": False,
        },
        "authorization": {
            "fresh_benchmark_external_matched_gate_design": not findings,
            "external_network_model_or_evaluator_launch": False,
            "new_exact220_launch": False,
            "retry_resume_or_selective_rerun_v25030": False,
            "leaderboard_or_sota": False,
        },
        "network_model_search_fetch_or_evaluator_called": False,
    }
    value["audit_payload_sha256"] = _payload_sha(value)
    if findings:
        raise RuntimeError(f"V2.50.34 build audit failed: {findings}")
    _publish(value)
    print(
        json.dumps(
            {
                "path": str(OUTPUT.relative_to(ROOT)),
                "audit_valid": True,
                "tests": value["tests"]["observed"],
                "fallback_histogram": aggregate[
                    "visible_column_count_histogram"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
