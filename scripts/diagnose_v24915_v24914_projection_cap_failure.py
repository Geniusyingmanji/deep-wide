#!/usr/bin/env python3
"""Aggregate-only diagnosis of V2.49.14 projection-cap failures."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24911_long_page_evidence_packer as packer  # noqa: E402
from deepwide_agent import v24913_observable_long_page_packer as observable  # noqa: E402
from scripts.audit_v24635_exact220 import (  # noqa: E402
    _accesses,
    _evaluator_capabilities,
)


DATE = "20260808"
OUTPUT = Path(f"results/v24915_v24914_projection_cap_failure_diagnosis_v1_{DATE}.json")
RESULT = Path(f"results/v24914_cap_bound_long_page_exact220_result_v1_{DATE}.json")
POSTAUDIT = Path(
    f"results/v24914_cap_bound_long_page_exact220_postresult_audit_v1_{DATE}.json"
)
OUTPUT_ROOT = Path(f"outputs/v24914_cap_bound_long_page_exact220_v1_{DATE}")
SOURCE_FILES = (
    Path("src/deepwide_agent/v24911_long_page_evidence_packer.py"),
    Path("src/deepwide_agent/v24842_atomic_table_header_closure.py"),
    Path("src/deepwide_agent/v24913_observable_long_page_packer.py"),
    Path("src/deepwide_agent/v24913_long_page_runtime_binding.py"),
    Path("scripts/diagnose_v24915_v24914_projection_cap_failure.py"),
)
SECRET_PREFIXES = ("gh" + "p_", "github_" + "pat_", "tvly-" + "dev-", "s" + "k-")
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:"
    + "|".join(re.escape(value) for value in SECRET_PREFIXES)
    + r")[A-Za-z0-9_-]{16,}"
)


def _ordinary(relative: Path) -> Path:
    path = ROOT / relative
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(ROOT.resolve())
    ):
        raise RuntimeError(f"V2.49.15 expected ordinary file: {relative}")
    return path


def _read(relative: Path) -> dict[str, Any]:
    value = json.loads(_ordinary(relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.49.15 expected JSON object")
    return value


def _sha(relative: Path) -> str:
    return hashlib.sha256(_ordinary(relative).read_bytes()).hexdigest()


def _sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == packer.payload_sha256(unsigned)


def _result_rows() -> list[dict[str, Any]]:
    paths = sorted((ROOT / OUTPUT_ROOT / "tasks").glob("task_*/result.json"))
    rows = []
    for path in paths:
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict) or not isinstance(value.get("result"), dict):
            raise RuntimeError("V2.49.15 task result drifted")
        rows.append(value["result"])
    if len(rows) != 220:
        raise RuntimeError("V2.49.15 requires exact-220 terminal rows")
    return rows


def _progress_rows() -> list[dict[str, Any]]:
    paths = sorted((ROOT / OUTPUT_ROOT / "tasks").glob("task_*/safe_progress.json"))
    rows = []
    for path in paths:
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise RuntimeError("V2.49.15 progress row drifted")
        rows.append(value)
    if len(rows) != 220:
        raise RuntimeError("V2.49.15 requires exact-220 progress rows")
    return rows


def _receipt_rows() -> list[dict[str, Any]]:
    paths = sorted(
        (ROOT / OUTPUT_ROOT / "tasks").glob("task_*/projection_receipt.json")
    )
    rows = [
        observable.validate_receipt(json.loads(path.read_text(encoding="utf-8")))
        for path in paths
    ]
    if len(rows) != 220:
        raise RuntimeError("V2.49.15 requires exact-220 projection receipts")
    return rows


def _synthetic_reproduction() -> dict[str, Any]:
    question = "Return one table. Columns: Entity, Value"
    failures = 0
    first_error = ""
    tested = 0
    for lines in (120, 200, 400, 800):
        for width in (5, 10, 20, 40, 80):
            content = (("Entity Value " + "x" * width) + "\n\n") * lines
            content = content[:12_000]
            if len(content) <= 5_000:
                continue
            tested += 1
            try:
                observable.build_observable_packing(
                    question,
                    [
                        {
                            "title": "synthetic public page",
                            "url": "https://example.invalid/data",
                            "content": content,
                        }
                    ],
                )
            except RuntimeError as error:
                failures += 1
                first_error = first_error or str(error)
    return {
        "production_shaped_cases": tested,
        "projection_cap_failures": failures,
        "failure_reproduced": failures > 0,
        "first_error_class": "RuntimeError" if failures else "",
        "first_error_matches_structural_selection_cap": (
            first_error == "V2.49.11 structural selection exceeded per-page cap"
        ),
        "question_page_or_generated_content_persisted": False,
    }


def build(*, now: int | None = None) -> dict[str, Any]:
    result = _read(RESULT)
    audit = _read(POSTAUDIT)
    rows = _result_rows()
    progress = _progress_rows()
    receipts = _receipt_rows()
    result_valid = (
        result.get("status") == "exact220_single_rollout_complete"
        and result.get("selected") == 220
        and result.get("claims", {}).get("public_exact220_single_rollout") is True
        and result.get("authorization", {}).get("selective_retry_or_revaluation")
        is False
        and _sealed(result, "result_payload_sha256")
        and audit.get("audit_valid") is True
        and audit.get("findings") == []
        and _sealed(audit, "audit_payload_sha256")
    )
    fallback = [row for row in rows if row.get("completion_kind") == "worker_failure_fallback"]
    generated = [row for row in rows if row.get("completion_kind") != "worker_failure_fallback"]
    retrieval_terminal = [row for row in progress if row.get("stage") == "retrieval_terminal"]
    later = [row for row in progress if row.get("stage") != "retrieval_terminal"]
    synthetic = _synthetic_reproduction()
    source_accesses: list[str] = []
    evaluator_capabilities: list[str] = []
    secrets: list[str] = []
    for relative in SOURCE_FILES:
        path = _ordinary(relative)
        source_accesses.extend(_accesses(path, ROOT))
        evaluator_capabilities.extend(_evaluator_capabilities(path, ROOT))
        if SECRET.search(path.read_text(encoding="utf-8")):
            secrets.append(str(relative))
    checks = {
        "parent_exact220_result_and_postaudit_valid": result_valid,
        "terminal_result_vector_exact220": len(rows) == 220,
        "fallback_count_exact174": len(fallback) == 174,
        "model_generated_count_exact46": len(generated) == 46,
        "all_fallbacks_stop_after_plan_before_synthesis": all(
            row.get("cost", {}).get("model", {}).get("requests") == 1
            and row.get("evidence", {}).get("projected_chars") == 0
            and row.get("failures")
            == [{"stage": "v24318_deadline_totality", "type": "ValidationError"}]
            for row in fallback
        ),
        "all_generated_rows_reach_projection_and_synthesis": all(
            row.get("cost", {}).get("model", {}).get("requests", 0) >= 2
            and row.get("evidence", {}).get("projected_chars", 0) > 0
            for row in generated
        ),
        "progress_partition_matches_174_46": (
            len(retrieval_terminal) == 174 and len(later) == 46
        ),
        "all_220_projection_receipts_valid": len(receipts) == 220,
        "projection_mechanism_naturally_engaged": sum(
            row["long_page_mechanism_engaged"] for row in receipts
        )
        == 4,
        "production_shaped_cap_failure_reproduced": synthetic[
            "failure_reproduced"
        ],
        "failure_message_matches_structural_selection_cap": synthetic[
            "first_error_matches_structural_selection_cap"
        ],
        "source_privileged_access_zero": not source_accesses,
        "source_evaluator_capability_zero": not evaluator_capabilities,
        "source_secret_literal_zero": not secrets,
    }
    manifest = {str(path): _sha(path) for path in (*SOURCE_FILES, RESULT, POSTAUDIT)}
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24915_v24914_projection_cap_failure_aggregate_diagnosis",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parent": {
            "result": {"path": str(RESULT), "sha256": _sha(RESULT)},
            "postresult_audit": {
                "path": str(POSTAUDIT),
                "sha256": _sha(POSTAUDIT),
            },
        },
        "observed": {
            "selected": len(rows),
            "worker_failure_fallbacks": len(fallback),
            "model_generated_tables": len(generated),
            "last_safe_progress_stage_counts": dict(
                sorted(Counter(str(row.get("stage")) for row in progress).items())
            ),
            "fallback_model_request_count_distribution": dict(
                sorted(
                    Counter(
                        int(row["cost"]["model"]["requests"]) for row in fallback
                    ).items()
                )
            ),
            "fallback_projected_character_count_distribution": dict(
                sorted(
                    Counter(
                        int(row["evidence"]["projected_chars"]) for row in fallback
                    ).items()
                )
            ),
            "projection_receipts": len(receipts),
            "long_page_mechanism_engaged_tasks": sum(
                row["long_page_mechanism_engaged"] for row in receipts
            ),
        },
        "synthetic_reproduction": synthetic,
        "root_cause": {
            "location": "v24911_long_page_evidence_packer._pack_long_page",
            "trigger": "real_12000_character_page_activates_multi_block_structural_selection",
            "mechanism": "selector_accounts_block_content_but_join_inserts_unaccounted_newlines",
            "effect": "joined_excerpt_can_exceed_5000_and_raise_before_synthesis",
            "v24911_nonengagement_masked_bug": True,
            "transport_or_gpt56_endpoint_failure": False,
            "evaluator_failure": False,
        },
        "checks": checks,
        "findings": sorted(name for name, passed in checks.items() if not passed),
        "diagnosis_valid": all(checks.values()),
        "source_manifest": manifest,
        "source_manifest_sha256": packer.payload_sha256(manifest),
        "source_policy": {
            "aggregate_only_no_question_query_url_page_prediction_or_opaque_id_emitted": True,
            "runtime_mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "network_model_search_fetch_or_evaluator_called_by_diagnosis": False,
            "credential_value_read_persisted_hashed_or_emitted": False,
            "entropy_or_information_gain_assigns_signed_credit": False,
        },
        "authorization": {
            "prefix_totality_repair_build": all(checks.values()),
            "benchmark_external_gate": False,
            "public_dev64_or_exact220": False,
            "evaluator": False,
            "leaderboard_submission": False,
            "sota_claim": False,
        },
    }
    value["diagnosis_payload_sha256"] = packer.payload_sha256(value)
    return value


def publish(value: dict[str, Any]) -> None:
    path = ROOT / OUTPUT
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    report = build()
    if report["findings"]:
        raise RuntimeError(f"V2.49.15 diagnosis rejected: {report['findings']}")
    publish(report)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "diagnosis_valid": report["diagnosis_valid"],
                "findings": report["findings"],
                "authorization": report["authorization"],
            },
            sort_keys=True,
        )
    )
