#!/usr/bin/env python3
"""Run one verbose-versus-compact schema-ledger task."""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24939_schema_bound_record_ledger as verbose  # noqa: E402
from deepwide_agent import v24942_compact_schema_bound_record_ledger as compact  # noqa: E402
from deepwide_agent import v24943_compact_ledger_external_contract as contract  # noqa: E402
from scripts import run_v24923_target_value_external_task as engine  # noqa: E402
from scripts import run_v24940_open_world_ledger_external_task as prompt_parent  # noqa: E402
from scripts.run_v24941_open_world_ledger_external_task import select_task_page  # noqa: E402


def _receipt(value: dict[str, Any], *, arm: str) -> dict[str, Any]:
    content = copy.deepcopy(value["content_free_receipt"])
    receipt: dict[str, Any] = {
        "artifact_version": 1,
        "role": f"v24943_content_free_{arm}_schema_bound_receipt",
        "policy_id": str(value["policy_id"]),
        "candidate_receipt": content,
        "supported_target_value_pair_count": int(content["admissible_bound_observation_count"]),
        "retained_target_value_pair_count": int(content["retained_admissible_bound_observation_count"]),
        "admissible_bound_observation_count": int(content["admissible_bound_observation_count"]),
        "retained_admissible_bound_observation_count": int(content["retained_admissible_bound_observation_count"]),
        "discovered_row_key_count": int(content["discovered_row_key_count"]),
        "same_forward_page_bytes_only": True,
        "entropy_or_information_gain_assigns_credit": False,
        "contains_question_query_url_host_page_projection_prediction_or_hash": False,
        "benchmark_metadata_answer_evaluator_score_reward_read": False,
    }
    receipt["receipt_payload_sha256"] = contract.payload_sha256(receipt)
    return receipt


def build_projections(question: str, pages: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    baseline = verbose.build_projection(question, pages)
    treatment = compact.build_projection(question, pages)
    return {
        "parent_30k": {"projection": baseline["projection"], "receipt": _receipt(baseline, arm="verbose")},
        "target_value_30k": {"projection": treatment["projection"], "receipt": _receipt(treatment, arm="compact")},
    }


def configure() -> None:
    engine.contract = contract
    engine.parent = verbose
    engine.candidate = compact
    engine._prompt = prompt_parent._prompt
    engine.build_projections = build_projections
    inherited = engine._read

    def aligned_read(path: Path) -> dict[str, Any]:
        value = inherited(path)
        if path.name != "frozen_pages.json":
            return value
        task_path = Path(sys.argv[sys.argv.index("--task") + 1])
        task = json.loads(task_path.read_text(encoding="utf-8"))
        pages = value.get("pages")
        if not isinstance(pages, list):
            raise RuntimeError("V2.49.43 frozen page vector drifted")
        copied = dict(value)
        copied["pages"] = select_task_page(str(task["question"]), pages)
        return copied

    engine._read = aligned_read


def main() -> None:
    configure()
    task_path = Path(sys.argv[sys.argv.index("--task") + 1])
    opaque = str(json.loads(task_path.read_text(encoding="utf-8"))["opaque_id"])
    contract.ARMS = contract.arm_order(opaque)
    engine.main()


if __name__ == "__main__":
    main()
