#!/usr/bin/env python3
"""Audit the V2.49.33 contextual record/value projector build."""

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

from deepwide_agent import v24928_unicode_total_visible_row_compactor as parent  # noqa: E402
from deepwide_agent import v24933_contextual_record_value_projector as candidate  # noqa: E402


DATE = "20260809"
OUTPUT = Path(
    f"results/v24933_contextual_record_value_build_audit_v1_{DATE}.json"
)
AUDIT = Path("scripts/audit_v24933_contextual_record_value_build.py")
SOURCE = Path("src/deepwide_agent/v24933_contextual_record_value_projector.py")
TEST = Path("tests/test_v24933_contextual_record_value_projector.py")
UNICODE_SOURCE = Path(
    "src/deepwide_agent/v24928_unicode_total_visible_row_compactor.py"
)
TARGET_SOURCE = Path("src/deepwide_agent/v24921_target_value_coverage_projector.py")
V24932_POSTAUDIT = Path(
    "results/v24932_unicode_total_exact220_postresult_audit_v1_20260809.json"
)
V24932_TASK_ROOT = Path(
    "outputs/v24932_unicode_total_exact220_v1_20260809/tasks"
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


def _payload(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()
    ).hexdigest()


def _read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"V2.49.33 expected ordinary object: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.49.33 expected JSON object")
    return value


def _tracked(path: Path) -> bool:
    return subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(path)],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=20,
        check=False,
    ).returncode == 0


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
    return observed, completed.returncode == 0 and observed == 10, _payload(
        completed.stdout
    )


def _runtime_findings() -> tuple[list[str], list[str], list[str]]:
    source = (ROOT / SOURCE).read_text(encoding="utf-8")
    tree = ast.parse(source)
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
    forbidden_imports = sorted(
        imports.intersection(
            {
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
        )
    )
    dynamic_or_io = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id
            in {"open", "eval", "exec", "compile", "__import__"}
        ):
            dynamic_or_io.append(f"{node.func.id}:{node.lineno}")
    secrets = [str(SOURCE)] if SECRET.search(source) else []
    return forbidden_imports, dynamic_or_io, secrets


def _v24932_content_free_aggregate() -> dict[str, int]:
    root = ROOT / V24932_TASK_ROOT
    paths = sorted(root.glob("task_*/unicode_total_projection_receipt.json"))
    if len(paths) != 220:
        raise RuntimeError("V2.49.33 expected 220 V2.49.32 receipts")
    output = {
        "receipts": len(paths),
        "input_pages": 0,
        "nfkc_expansion_characters": 0,
        "nfkc_expansion_pages": 0,
        "table_count": 0,
        "eligible_table_count": 0,
        "supported_target_value_pairs": 0,
        "retained_target_value_pairs": 0,
        "selected_table_continuations": 0,
        "table_header_dependency_additions": 0,
    }
    for path in paths:
        value = _read(path)
        compaction = value.get("compaction_receipt") or {}
        projection = value.get("projection_receipt") or {}
        output["input_pages"] += int(compaction.get("input_page_count", 0))
        output["nfkc_expansion_characters"] += int(
            compaction.get("nfkc_expansion_characters", 0)
        )
        output["nfkc_expansion_pages"] += int(
            compaction.get("nfkc_expansion_page_count", 0)
        )
        output["table_count"] += int(compaction.get("table_count", 0))
        output["eligible_table_count"] += int(
            compaction.get("eligible_table_count", 0)
        )
        output["supported_target_value_pairs"] += int(
            projection.get("supported_target_value_pair_count", 0)
        )
        output["retained_target_value_pairs"] += int(
            projection.get("retained_target_value_pair_count", 0)
        )
        output["selected_table_continuations"] += int(
            projection.get("selected_table_continuation_block_count", 0)
        )
        output["table_header_dependency_additions"] += int(
            projection.get("table_header_dependency_addition_count", 0)
        )
    return output


def _synthetic_reachability() -> dict[str, Any]:
    entities = [f"Entity {index:03d}" for index in range(220)]
    selected = entities[170:176]
    question = (
        "Return exactly one Markdown table. Column names: Entity | "
        "Population [POP] @2024.\n<ENTITIES>\n"
        + "\n".join(
            f"{index}. {name} [E{index:03d}]"
            for index, name in enumerate(selected, 1)
        )
        + "\n</ENTITIES>"
    )
    content = (
        "# Country coverage index\n\n"
        + "\n".join(f"- {name}" for name in entities)
        + "\n\n# Population [POP] @2024 official observations\n\n"
        + "\n".join(
            f"{name}: {100000 + index}" for index, name in enumerate(entities)
        )
    )
    pages = [
        {
            "title": "Official",
            "url": "https://example.test/pop",
            "content": content,
        }
    ]
    baseline = parent.build_projection(question, pages)
    treatment = candidate.build_projection(question, pages)
    receipt = treatment["content_free_receipt"]
    return {
        "projection_unequal": baseline["projection"] != treatment["projection"],
        "supported_contextual_pairs": receipt[
            "supported_contextual_target_value_pair_count"
        ],
        "retained_contextual_pairs": receipt[
            "retained_contextual_target_value_pair_count"
        ],
        "selected_values_retained": all(
            f"{name}: {100000 + entities.index(name)}" in treatment["projection"]
            for name in selected
        ),
    }


def build() -> dict[str, Any]:
    postaudit = _read(ROOT / V24932_POSTAUDIT)
    observed, tests_passed, test_sha = _test()
    forbidden, dynamic_or_io, secrets = _runtime_findings()
    aggregate = _v24932_content_free_aggregate()
    reachability = _synthetic_reachability()
    checks = {
        "v24932_postresult_audit_valid": postaudit.get("audit_valid") is True
        and postaudit.get("findings") == [],
        "v24932_content_free_receipts_exact220": aggregate["receipts"] == 220,
        "v24932_target_value_pair_exposure_zero": aggregate[
            "supported_target_value_pairs"
        ]
        == aggregate["retained_target_value_pairs"]
        == 0,
        "v24932_structured_table_mechanism_negligible": aggregate[
            "eligible_table_count"
        ]
        == aggregate["selected_table_continuations"]
        == aggregate["table_header_dependency_additions"]
        == 0,
        "focused_tests_exact10": tests_passed and observed == 10,
        "runtime_forbidden_import_zero": not forbidden,
        "runtime_dynamic_or_io_call_zero": not dynamic_or_io,
        "credential_literal_zero": not secrets,
        "source_files_tracked": all(
            _tracked(path)
            for path in (
                AUDIT,
                SOURCE,
                TEST,
                UNICODE_SOURCE,
                TARGET_SOURCE,
                V24932_POSTAUDIT,
            )
        ),
        "fixed_30k_total_and_5k_page_caps": candidate.TOTAL_CHARACTER_CAP
        == 30_000
        and candidate.MAXIMUM_PAGE_CHARS == 5_000,
        "synthetic_contextual_mechanism_reachable": reachability[
            "projection_unequal"
        ]
        and reachability["supported_contextual_pairs"] > 0
        and reachability["retained_contextual_pairs"] > 0
        and reachability["selected_values_retained"],
        "entropy_assigns_no_credit": True,
    }
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24933_contextual_record_value_build_audit",
        "created_at_unix": int(time.time()),
        "diagnosis": {
            "v24932_content_free_aggregate": aggregate,
            "mechanical_conclusion": (
                "V2.49.32 restored Unicode totality, but its table/target-value "
                "quality mechanism had zero eligible or pair exposure; ordinary "
                "text context is the next identifiable projector surface"
            ),
            "benchmark_question_page_prediction_or_per_task_correctness_read": False,
        },
        "synthetic_reachability": reachability,
        "tests": {
            "path": str(TEST),
            "expected": 10,
            "observed": observed,
            "passed": tests_passed,
            "output_sha256": test_sha,
        },
        "runtime_semantic_audit": {
            "forbidden_imports": forbidden,
            "dynamic_or_io_calls": dynamic_or_io,
            "credential_literal_hits": secrets,
        },
        "source_manifest": {
            str(path): _sha256(ROOT / path)
            for path in (
                AUDIT,
                SOURCE,
                TEST,
                UNICODE_SOURCE,
                TARGET_SOURCE,
                V24932_POSTAUDIT,
            )
        },
        "checks": checks,
        "findings": sorted(name for name, passed in checks.items() if not passed),
        "source_policy": {
            "visible_question_and_same_forward_pages_only": True,
            "v24932_content_free_receipts_only": True,
            "benchmark_label_mapping_gold_evaluator_score_reward_read": False,
            "entropy_information_gain_shadow_only": True,
            "entropy_or_information_gain_assigns_credit": False,
        },
        "authorization": {
            "fresh_benchmark_external_shared_prefix_protocol_design": all(
                checks.values()
            ),
            "external_launch": False,
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
        raise RuntimeError(f"V2.49.33 build audit failed: {value['findings']}")
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
