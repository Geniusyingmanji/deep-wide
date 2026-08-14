#!/usr/bin/env python3
"""Question-only exact-220 transfer audit for visible index bootstrap.

This audit reads the fixed DeepWideBench task vector through its frozen
``opaque_id``/``question`` boundary and persists aggregate exposure counts
plus the pre-existing vector hashes.  It does not retain a question, opaque
id, URL, host, path, schema, feature vector, prediction, page, answer, truth,
score, reward, evaluator row, or per-task outcome.  It performs no network,
model, search, fetch, benchmark, or evaluator effect and authorizes no
forward.  Entropy/information gain remains shadow-only with zero credit.
"""

from __future__ import annotations

import copy
import ipaddress
import json
import os
import re
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25110_exact_visible_schema as visible_schema  # noqa: E402
from deepwide_agent import v25406_grounded_membership_exact220_contract as tasks  # noqa: E402
from deepwide_agent import v25496_visible_row_key_detail_external_contract as external  # noqa: E402
from scripts import diagnose_v25497_v25496_visible_detail_no_go as diagnosis  # noqa: E402


DATE = "20260814"
ROLE = "v25498_exact220_visible_index_question_only_transfer_audit"
OUTPUT = Path(
    f"results/v25498_exact220_visible_index_transfer_audit_v1_{DATE}.json"
)
DIAGNOSIS = diagnosis.OUTPUT
DIAGNOSIS_SHA256 = (
    "12b9cae3688bb3da0456ff08c72dbb17ad6301bd4ec6f99034b3791ebc1df564"
)
TASK_COUNT = 220
OPAQUE_VECTOR_SHA256 = (
    "3c4b3eeb6cadbc9ce8b22552f294a0322e820dbb4be29c3e7fb2f99a4f83665a"
)
QUESTION_VECTOR_SHA256 = (
    "d009f9f13b51e48e249f6698b3b1417d3a62c7100c8551b1cb025e726bcd82b7"
)
URL_RE = re.compile(r"(?i)https?://[^\s<>\[\]{}\"']+")
SIGNALS = {
    "index": re.compile(r"(?i)\b(?:index|indexed)\b"),
    "directory": re.compile(r"(?i)\b(?:directory|catalog(?:ue)?|listing)\b"),
    "registry": re.compile(
        r"(?i)\b(?:registry|register|database|repository|archive)\b"
    ),
    "official": re.compile(
        r"(?i)\b(?:official|authoritative|authority|government|agency)\b"
    ),
    "navigation": re.compile(
        r"(?i)\b(?:website|webpage|web\s+page|homepage|site|url|link|online|portal|lookup)\b"
    ),
}
INDEX_PATH_RE = re.compile(
    r"(?i)(?:index|director|catalog|registr|database|archive|repository|list|lookup)"
)
EXPECTED_EXPOSURE_COUNTS = {
    "explicit_http_url_tasks": 3,
    "explicit_http_url_count_total": 6,
    "public_http_url_tasks": 3,
    "public_http_url_count_total": 6,
    "single_public_http_url_tasks": 1,
    "multiple_public_http_url_tasks": 2,
    "path_bearing_public_http_url_tasks": 1,
    "index_like_path_public_http_url_tasks": 0,
    "index_signal_tasks": 0,
    "directory_signal_tasks": 1,
    "registry_signal_tasks": 1,
    "official_signal_tasks": 24,
    "navigation_signal_tasks": 6,
    "public_http_url_and_index_signal_tasks": 0,
    "public_http_url_and_directory_signal_tasks": 0,
    "public_http_url_and_registry_signal_tasks": 0,
    "public_http_url_and_official_signal_tasks": 1,
    "public_http_url_and_navigation_signal_tasks": 1,
    "public_http_url_and_any_source_signal_tasks": 1,
    "single_public_http_url_and_any_source_signal_tasks": 0,
    "public_http_url_and_exact_schema_tasks": 2,
    "single_public_http_url_and_exact_schema_tasks": 1,
    "question_only_visible_index_bootstrap_reachable_upper_bound_tasks": 0,
}


def _diagnosis_barrier() -> dict[str, Any]:
    path = external.ordinary(ROOT, DIAGNOSIS, tracked=True)
    value = json.loads(path.read_text(encoding="utf-8"))
    if (
        external.sha256(path) != DIAGNOSIS_SHA256
        or diagnosis.validate_diagnosis(value) != value
        or value.get("audit_valid") is not True
        or value.get("findings") != []
        or value.get("authorization", {}).get(
            "exact220_question_only_visible_signal_transfer_audit"
        )
        is not True
        or value.get("authorization", {}).get("external_protocol_or_forward")
        is not False
    ):
        raise RuntimeError("V2.54.98 diagnosis barrier drifted")
    return value


def _trim_url(raw: str) -> str:
    return str(raw).rstrip(".,;:!?)]}'\"")


def _public_url(raw: str) -> Any | None:
    try:
        parsed = urlsplit(_trim_url(raw))
        hostname = (parsed.hostname or "").rstrip(".").casefold()
        if (
            parsed.scheme.casefold() not in {"http", "https"}
            or not hostname
            or parsed.username
            or parsed.password
            or hostname == "localhost"
            or hostname.endswith(".localhost")
            or hostname.endswith(".local")
        ):
            return None
        try:
            address = ipaddress.ip_address(hostname.split("%", 1)[0])
        except ValueError:
            address = None
        if address is not None and not address.is_global:
            return None
        return parsed
    except ValueError:
        return None


def visible_exposure() -> dict[str, Any]:
    vector = tasks.task_vector(ROOT)
    if (
        len(vector) != TASK_COUNT
        or any(set(task) != {"opaque_id", "question"} for task in vector)
        or tasks.payload_sha256([task["opaque_id"] for task in vector])
        != OPAQUE_VECTOR_SHA256
        or tasks.payload_sha256([task["question"] for task in vector])
        != QUESTION_VECTOR_SHA256
    ):
        raise RuntimeError("V2.54.98 visible task vector drifted")

    counts = {name: 0 for name in EXPECTED_EXPOSURE_COUNTS}
    exact_schema_tasks = 0
    empty_exact_schema_tasks = 0
    for task in vector:
        question = str(task["question"])
        raw_urls = URL_RE.findall(question)
        public_urls = [
            parsed for raw in raw_urls if (parsed := _public_url(raw)) is not None
        ]
        exact_schema = bool(visible_schema.extract_exact_visible_columns(question))
        flags = {name: bool(pattern.search(question)) for name, pattern in SIGNALS.items()}
        any_source_signal = any(flags.values())

        exact_schema_tasks += int(exact_schema)
        empty_exact_schema_tasks += int(not exact_schema)
        counts["explicit_http_url_tasks"] += int(bool(raw_urls))
        counts["explicit_http_url_count_total"] += len(raw_urls)
        counts["public_http_url_tasks"] += int(bool(public_urls))
        counts["public_http_url_count_total"] += len(public_urls)
        counts["single_public_http_url_tasks"] += int(len(public_urls) == 1)
        counts["multiple_public_http_url_tasks"] += int(len(public_urls) > 1)
        counts["path_bearing_public_http_url_tasks"] += int(
            any(parsed.path not in {"", "/"} for parsed in public_urls)
        )
        counts["index_like_path_public_http_url_tasks"] += int(
            any(INDEX_PATH_RE.search(parsed.path or "") for parsed in public_urls)
        )
        for name, present in flags.items():
            counts[f"{name}_signal_tasks"] += int(present)
            counts[f"public_http_url_and_{name}_signal_tasks"] += int(
                bool(public_urls) and present
            )
        counts["public_http_url_and_any_source_signal_tasks"] += int(
            bool(public_urls) and any_source_signal
        )
        counts["single_public_http_url_and_any_source_signal_tasks"] += int(
            len(public_urls) == 1 and any_source_signal
        )
        counts["public_http_url_and_exact_schema_tasks"] += int(
            bool(public_urls) and exact_schema
        )
        counts["single_public_http_url_and_exact_schema_tasks"] += int(
            len(public_urls) == 1 and exact_schema
        )

    counts["question_only_visible_index_bootstrap_reachable_upper_bound_tasks"] = (
        counts["single_public_http_url_and_any_source_signal_tasks"]
    )
    return {
        "task_count": len(vector),
        "runtime_input_keys": ["opaque_id", "question"],
        "opaque_id_vector_sha256": OPAQUE_VECTOR_SHA256,
        "visible_question_vector_sha256": QUESTION_VECTOR_SHA256,
        "exact_visible_schema_tasks": exact_schema_tasks,
        "empty_exact_visible_schema_tasks": empty_exact_schema_tasks,
        **counts,
        "question_opaque_id_url_host_path_schema_or_per_task_feature_persisted": False,
    }


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    barrier = _diagnosis_barrier()
    exposure = visible_exposure()
    checks = {
        "v25497_hash_role_seal_and_question_only_authority_bound": bool(barrier),
        "fixed_visible_task_vector_exact220_and_hash_bound": exposure["task_count"]
        == TASK_COUNT,
        "visible_schema_accounting_exact220": exposure["exact_visible_schema_tasks"]
        + exposure["empty_exact_visible_schema_tasks"]
        == TASK_COUNT,
        "explicit_http_url_exposure_three_of_220": exposure[
            "explicit_http_url_tasks"
        ]
        == 3,
        "public_http_url_exposure_three_of_220": exposure["public_http_url_tasks"]
        == 3,
        "visible_source_signal_counts_exact": all(
            exposure[name] == amount
            for name, amount in EXPECTED_EXPOSURE_COUNTS.items()
        ),
        "single_public_url_source_bootstrap_reachable_upper_bound_zero": exposure[
            "question_only_visible_index_bootstrap_reachable_upper_bound_tasks"
        ]
        == 0,
        "question_only_visible_index_bootstrap_is_provably_identity_only": True,
        "no_task_retention_ranking_replacement_or_selective_rerun": True,
        "mapping_gold_label_truth_score_reward_evaluator_or_historical_result_not_read": True,
        "network_model_search_fetch_evaluator_benchmark_or_api_not_called": True,
        "entropy_information_gain_signed_credit_zero": True,
        "protected_watchers_unchanged": external.watcher_snapshot()
        == [
            {"pid": pid, "start_ticks": ticks, "marker": marker}
            for pid, ticks, marker in external.EXPECTED_WATCHERS
        ],
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "diagnosis_barrier": {
            "path": str(DIAGNOSIS),
            "sha256": DIAGNOSIS_SHA256,
            "aggregate_two_stage_bottleneck_frozen": True,
        },
        "visible_transfer": exposure,
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "transfer_decision": {
            "explicit_visible_index_bootstrap_for_fixed_exact220": "no_go",
            "reason": "only_three_of_220_questions_contain_public_urls_and_zero_have_one_unambiguous_url_plus_source_signal",
            "generic_parent_and_detail_visible_schema_grammar_remains_authorized_for_build": True,
        },
        "question_opaque_id_url_host_path_schema_or_per_task_feature_persisted": False,
        "mapping_gold_category_question_type_split_truth_evaluator_score_reward_or_historical_result_read": False,
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "positive_signed_credit_count": 0,
        "authorization": {
            "explicit_visible_index_bootstrap_exact220_successor_build": False,
            "generic_parent_and_detail_visible_schema_grammar_build": not findings,
            "new_external_protocol_or_forward": False,
            "deepwidebench_forward_or_evaluator": False,
            "retry_resume_replay_backfill_replacement_or_selective_rerun": False,
            "leaderboard_or_sota": False,
        },
    }
    value["audit_payload_sha256"] = external.payload_sha256(value)
    return validate_audit(value)


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("audit_payload_sha256", None)
    valid = copied.get("audit_valid") is True
    exposure = copied.get("visible_transfer") or {}
    if (
        copied.get("role") != ROLE
        or copied.get("diagnosis_barrier")
        != {
            "path": str(DIAGNOSIS),
            "sha256": DIAGNOSIS_SHA256,
            "aggregate_two_stage_bottleneck_frozen": True,
        }
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or exposure.get("task_count") != TASK_COUNT
        or exposure.get("opaque_id_vector_sha256") != OPAQUE_VECTOR_SHA256
        or exposure.get("visible_question_vector_sha256")
        != QUESTION_VECTOR_SHA256
        or any(
            exposure.get(name) != amount
            for name, amount in EXPECTED_EXPOSURE_COUNTS.items()
        )
        or exposure.get("exact_visible_schema_tasks") != 194
        or exposure.get("empty_exact_visible_schema_tasks") != 26
        or copied.get("transfer_decision")
        != {
            "explicit_visible_index_bootstrap_for_fixed_exact220": "no_go",
            "reason": "only_three_of_220_questions_contain_public_urls_and_zero_have_one_unambiguous_url_plus_source_signal",
            "generic_parent_and_detail_visible_schema_grammar_remains_authorized_for_build": True,
        }
        or copied.get(
            "question_opaque_id_url_host_path_schema_or_per_task_feature_persisted"
        )
        is not False
        or copied.get(
            "mapping_gold_category_question_type_split_truth_evaluator_score_reward_or_historical_result_read"
        )
        is not False
        or copied.get("network_model_search_fetch_evaluator_benchmark_or_api_called")
        is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit")
        is not False
        or copied.get("positive_signed_credit_count") != 0
        or copied.get("authorization")
        != {
            "explicit_visible_index_bootstrap_exact220_successor_build": False,
            "generic_parent_and_detail_visible_schema_grammar_build": valid,
            "new_external_protocol_or_forward": False,
            "deepwidebench_forward_or_evaluator": False,
            "retry_resume_replay_backfill_replacement_or_selective_rerun": False,
            "leaderboard_or_sota": False,
        }
        or seal != external.payload_sha256(unsigned)
    ):
        raise ValueError("V2.54.98 transfer audit drifted")
    return copied


def _publish(value: Mapping[str, Any]) -> None:
    path = ROOT / OUTPUT
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def main() -> None:
    value = build_audit()
    if value["findings"]:
        raise RuntimeError(value["findings"])
    _publish(value)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "audit_valid": value["audit_valid"],
                "visible_transfer": value["visible_transfer"],
                "transfer_decision": value["transfer_decision"],
                "authorization": value["authorization"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
