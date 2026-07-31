#!/usr/bin/env python3
"""Versioned recovery publisher after the sealed V2.42.12 activation failure."""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24200_successor import payload_sha256  # noqa: E402
from scripts.publish_v24212_entropy_component import (  # noqa: E402
    build_selected_publication,
    file_sha256,
    load_selected_inputs,
    publish_new,
)


OUTPUT = Path("results/v24213_selected_entropy_component_publication_v1_20260731.json")
CANDIDATE_ROOT = ROOT / "outputs/v24213_selected_entropy_candidate_v1_20260731"
FAILED_ACTIVATION_AUDIT = Path(
    "results/v24212_selected_entropy_component_failed_activation_audit_v1_20260731.json"
)
FAILED_ACTIVATION_AUDIT_SHA256 = (
    "1239de2de45cd1b0c1a1d2fb0e8333145f4ac9cf9f2c2841160b2a010f026307"
)


def build_recovery_publication(
    selected: Mapping[str, Any],
    entropy_order: Mapping[str, Any] | None,
    search_order: Mapping[str, Any],
    markdown: Mapping[str, Any],
    scope: Mapping[str, Any],
    search_publication: Mapping[str, Any],
    *,
    candidate: Path = CANDIDATE_ROOT,
) -> dict[str, Any]:
    """Build the ordinary component under a new, failure-bound namespace."""

    value = build_selected_publication(
        selected,
        entropy_order,
        search_order,
        markdown,
        scope,
        search_publication,
        candidate=candidate,
    )
    unsigned = copy.deepcopy(value)
    seal = unsigned.pop("publication_payload_sha256", None)
    if (
        value.get("role") != "v24212_selected_entropy_component_publication"
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.42.13 base entropy publication drifted")
    value.pop("publication_payload_sha256")
    value["role"] = "v24213_selected_entropy_component_recovery_publication"
    value["recovery_parent"] = {
        "path": str(FAILED_ACTIVATION_AUDIT),
        "sha256": FAILED_ACTIVATION_AUDIT_SHA256,
        "failure_classification": (
            "successor_envelope_field_name_mismatch_fail_closed"
        ),
    }
    value["v24212_activation_state_or_candidate_reused_overwritten_or_resumed"] = False
    value["recovery_delta"] = (
        "validate_v24210_frozen_false_field_under_its_exact_registered_name"
    )
    value["publication_payload_sha256"] = payload_sha256(value)
    return value


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
        raise RuntimeError("V2.42.13 CLI path drifted")
    selected, order, search_order, markdown, scope, search = load_selected_inputs(
        ROOT
    )
    value = build_recovery_publication(
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
