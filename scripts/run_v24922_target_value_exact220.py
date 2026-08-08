#!/usr/bin/env python3
"""Run one fresh label-blind V2.49.22 exact-220 forward."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24922_target_value_exact220_contract as contract  # noqa: E402
from scripts import run_v24857_pacing_aware_exact220 as base  # noqa: E402
from scripts import run_v24800_exact220 as engine  # noqa: E402
from scripts import run_v24635_exact220 as algorithm  # noqa: E402


def _projection_receipt_totals(root: Path) -> dict:
    return contract.projection_receipt_summary(root)


def configure() -> None:
    base.contract = contract
    base.configure()
    inherited_summary = engine._direct_search_totals

    def direct_search_totals(root: Path) -> dict:
        value = inherited_summary(root)
        value["target_value_projection"] = _projection_receipt_totals(root)
        return value

    engine._direct_search_totals = direct_search_totals


def _reseal_forward_artifacts() -> None:
    summary_path = ROOT / contract.RUN_SUMMARY
    summary = engine._read(summary_path)
    summary["role"] = "v24922_target_value_exact220_run_summary"
    summary.pop("summary_payload_sha256", None)
    summary["summary_payload_sha256"] = contract.payload_sha256(summary)
    algorithm._atomic_json(summary_path, summary)

    freeze_path = ROOT / contract.PREDICTION_FREEZE
    freeze = engine._read(freeze_path)
    freeze["role"] = "v24922_target_value_exact220_prediction_freeze"
    freeze["run_summary_sha256"] = contract.sha256(summary_path)
    freeze.pop("freeze_payload_sha256", None)
    freeze["freeze_payload_sha256"] = contract.payload_sha256(freeze)
    algorithm._atomic_json(freeze_path, freeze)

    forward_path = ROOT / contract.FORWARD_RESULT
    forward = engine._read(forward_path)
    forward["role"] = "v24922_target_value_exact220_forward_result"
    forward["run_summary_sha256"] = contract.sha256(summary_path)
    forward["prediction_freeze_sha256"] = contract.sha256(freeze_path)
    forward.pop("result_payload_sha256", None)
    forward["result_payload_sha256"] = contract.payload_sha256(forward)
    algorithm._atomic_json(forward_path, forward)


def main() -> None:
    configure()
    engine.main()
    _reseal_forward_artifacts()


if __name__ == "__main__":
    main()
