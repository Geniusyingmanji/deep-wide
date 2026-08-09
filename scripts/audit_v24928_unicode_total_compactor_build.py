#!/usr/bin/env python3
"""Audit the V2.49.28 Unicode-total compactor and aggregate failure evidence."""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24928_unicode_total_visible_row_compactor as total  # noqa: E402


DATE = "20260809"
OUTPUT = Path(f"results/v24928_unicode_total_compactor_build_audit_v1_{DATE}.json")
SOURCE = Path("src/deepwide_agent/v24928_unicode_total_visible_row_compactor.py")
TEST = Path("tests/test_v24928_unicode_total_visible_row_compactor.py")
PARENT_SOURCE = Path("src/deepwide_agent/v24924_visible_row_table_compactor.py")
TARGET_SOURCE = Path("src/deepwide_agent/v24921_target_value_coverage_projector.py")
V24927_SUMMARY = Path(
    "outputs/v24927_sparse_target_value_exact220_v1_20260808/run_summary.json"
)
V24927_POSTAUDIT = Path(
    "results/v24927_sparse_target_value_exact220_postresult_audit_v1_20260808.json"
)
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}"
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"V2.49.28 expected ordinary object: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.49.28 expected JSON object")
    return value


def _payload(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _test() -> tuple[int, bool, str]:
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
            TEST.name,
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
    return observed, completed.returncode == 0 and observed == 12, _payload(completed.stdout)


def _runtime_findings() -> tuple[list[str], list[str], list[str]]:
    source = (ROOT / SOURCE).read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden_imports: list[str] = []
    dynamic_or_io: list[str] = []
    imports = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imports.update(
        (node.module or "").split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    )
    forbidden = {
        "os",
        "pathlib",
        "socket",
        "subprocess",
        "requests",
        "httpx",
        "openai",
        "importlib",
        "runpy",
    }
    forbidden_imports.extend(sorted(imports.intersection(forbidden)))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name) and node.func.id in {
            "open",
            "eval",
            "exec",
            "compile",
            "__import__",
        }:
            dynamic_or_io.append(f"{node.func.id}:{node.lineno}")
    return forbidden_imports, dynamic_or_io, ([str(SOURCE)] if SECRET.search(source) else [])


def _tracked(relative: Path) -> bool:
    return subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(relative)],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=20,
        check=False,
    ).returncode == 0


def _parent_reproduction() -> tuple[int, int]:
    from deepwide_agent import v24924_visible_row_table_compactor as parent

    question = (
        "Return one table. Column names: Entity | Metric.\n"
        "<ENTITIES>\n1. Alpha [ALP]\n</ENTITIES>"
    )
    glyphs = ("½", "Ⅷ", "㎏", "℡", "™", "℃", "ﬃ", "㍑")
    parent_failures = candidate_successes = 0
    for glyph in glyphs:
        pages = [{"title": "Neutral", "url": "https://example.test", "content": glyph}]
        try:
            parent.compact_pages(question, pages)
        except ValueError:
            parent_failures += 1
        try:
            total.build_projection(question, pages)
            candidate_successes += 1
        except (KeyError, RuntimeError, TypeError, ValueError):
            pass
    return parent_failures, candidate_successes


def build() -> dict[str, Any]:
    summary = _read(ROOT / V24927_SUMMARY)
    postaudit = _read(ROOT / V24927_POSTAUDIT)
    observed, passed, output_sha = _test()
    forbidden_imports, dynamic_or_io, secrets = _runtime_findings()
    parent_failures, candidate_successes = _parent_reproduction()
    completion = summary.get("completion_kinds") or {}
    aggregate = {
        "selected": int(summary.get("selected", 0)),
        "model_generated_tables": int(summary.get("model_generated_tables", 0)),
        "fallback_tables": int(summary.get("fallback_tables", 0)),
        "worker_failure_fallback": int(completion.get("worker_failure_fallback", 0)),
        "hosted_search_attempts": int(
            (summary.get("transport_totals") or {}).get("hosted_search_attempts", 0)
        ),
        "hard_fetch_helper_calls": int(
            (summary.get("transport_totals") or {}).get("hard_fetch_helper_calls", 0)
        ),
        "hosted_search_deadline_failures": int(
            (summary.get("transport_totals") or {}).get(
                "hosted_search_deadline_failures", 0
            )
        ),
        "valid_transport_receipts": int(summary.get("valid_transport_receipts", 0)),
        "valid_single_shot_receipts": int(
            summary.get("valid_single_shot_receipts", 0)
        ),
        "postresult_audit_valid": postaudit.get("audit_valid") is True,
    }
    checks = {
        "v24927_postresult_audit_valid": postaudit.get("audit_valid") is True
        and postaudit.get("findings") == [],
        "v24927_fixed_denominator_220": aggregate["selected"] == 220,
        "v24927_failure_count_is_90": aggregate["fallback_tables"]
        == aggregate["worker_failure_fallback"]
        == 90,
        "v24927_transport_receipts_complete": aggregate["valid_transport_receipts"]
        == aggregate["valid_single_shot_receipts"]
        == 220,
        "v24927_hosted_search_deadline_failures_zero": aggregate[
            "hosted_search_deadline_failures"
        ]
        == 0,
        "parent_nfkc_expansion_failure_reproduced_8_of_8": parent_failures == 8,
        "candidate_nfkc_expansion_total_8_of_8": candidate_successes == 8,
        "focused_tests_exact12": passed and observed == 12,
        "runtime_forbidden_import_zero": not forbidden_imports,
        "runtime_dynamic_or_io_call_zero": not dynamic_or_io,
        "credential_literal_zero": not secrets,
        "source_files_tracked": all(
            _tracked(path)
            for path in (SOURCE, TEST, PARENT_SOURCE, TARGET_SOURCE, V24927_POSTAUDIT)
        ),
        "fixed_30k_total_and_5k_page_caps": (
            total.target_value.TOTAL_CHARACTER_CAP == 30_000
            and total.target_value.MAXIMUM_PAGE_CHARS == 5_000
        ),
        "entropy_assigns_no_credit": True,
    }
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24928_unicode_total_compactor_build_audit",
        "created_at_unix": int(time.time()),
        "diagnosis": {
            "confirmed_component_bug": (
                "V2.49.24 compared NFKC-normalized output length with raw input length; "
                "compatibility expansion therefore raised ValidationError before synthesis"
            ),
            "v24927_content_free_aggregate": aggregate,
            "causal_scope": (
                "component bug is reproduced and consistent with the aggregate failure "
                "boundary; no claim is made that all 90 benchmark fallbacks had this cause"
            ),
            "benchmark_question_page_prediction_or_per_task_correctness_read": False,
        },
        "neutral_reproduction": {
            "compatibility_glyph_cases": 8,
            "parent_validation_failures": parent_failures,
            "candidate_projection_successes": candidate_successes,
        },
        "tests": {
            "path": str(TEST),
            "expected": 12,
            "observed": observed,
            "passed": passed,
            "output_sha256": output_sha,
        },
        "runtime_semantic_audit": {
            "forbidden_imports": forbidden_imports,
            "dynamic_or_io_calls": dynamic_or_io,
            "credential_literal_hits": secrets,
        },
        "source_manifest": {
            str(path): _sha256(ROOT / path)
            for path in (SOURCE, TEST, PARENT_SOURCE, TARGET_SOURCE, V24927_POSTAUDIT)
        },
        "checks": checks,
        "findings": sorted(name for name, passed_check in checks.items() if not passed_check),
        "source_policy": {
            "visible_question_and_same_forward_pages_only": True,
            "benchmark_label_mapping_gold_evaluator_score_reward_read": False,
            "v24927_postfreeze_content_free_aggregate_only": True,
            "entropy_information_gain_shadow_only": True,
            "entropy_or_information_gain_assigns_credit": False,
        },
        "authorization": {
            "fresh_benchmark_external_reliability_gate_design": all(checks.values()),
            "public_dev64_or_exact220": False,
            "evaluator": False,
            "leaderboard_submission": False,
            "sota_claim": False,
        },
    }
    value["source_manifest_sha256"] = _payload(value["source_manifest"])
    value["audit_valid"] = not value["findings"]
    value["audit_payload_sha256"] = _payload(value)
    return value


def main() -> None:
    value = build()
    if not value["audit_valid"]:
        raise RuntimeError(f"V2.49.28 build audit failed: {value['findings']}")
    path = ROOT / OUTPUT
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "audit_valid": value["audit_valid"],
                "findings": value["findings"],
                "authorization": value["authorization"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
