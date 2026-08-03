#!/usr/bin/env python3
"""Network-free real child for the V2.43.24 subprocess matrix."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24309_runner_exit_integration import (  # noqa: E402
    run_child_with_terminal_receipt,
)
from deepwide_agent.v24323_shared_prefix_cell_entropy import (  # noqa: E402
    AnonymousCellBelief,
    ReserveEvidenceSignal,
    admit_reserve_evidence,
    payload_sha256,
)
from deepwide_agent.v24324_shared_prefix_runner import (  # noqa: E402
    build_branch_effect_receipt,
    build_branch_envelope,
    build_no_external_transport_receipt,
    validate_prefix_bundle,
)


def read(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    validate_prefix_bundle(value)
    return value


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_new(path: Path, value: dict) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=(
            "success",
            "unreliable_candidate",
            "wrong_prefix",
            "duplicate_upstream",
            "nonzero",
            "timeout",
            "missing_result",
        ),
        required=True,
    )
    parser.add_argument("--arm", choices=("baseline", "candidate"), required=True)
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--result", required=True)
    parser.add_argument("--effect", required=True)
    parser.add_argument("--transport", required=True)
    parser.add_argument("--terminal", required=True)
    parser.add_argument("--output-root", required=True)
    args = parser.parse_args()
    prefix_path = Path(args.prefix)

    def action() -> None:
        if args.mode == "timeout":
            time.sleep(5)
            return
        if args.mode == "nonzero":
            raise RuntimeError("content-free synthetic nonzero")
        before = sha256(prefix_path)
        bundle = read(prefix_path)
        admission = None
        if args.arm == "candidate":
            reliability = 0.20 if args.mode == "unreliable_candidate" else 0.95
            admission = admit_reserve_evidence(
                AnonymousCellBelief((0.55, 0.30, 0.15), 0),
                ReserveEvidenceSignal(
                    likelihood_ratios=(8.0, 1.0, 0.5),
                    source_reliability=reliability,
                    source_independence=reliability,
                    fetch_integrity=True,
                    independent_sources=3,
                    corroborating_sources=3,
                    conflicting_sources=0,
                    evidence_chars=1_000_000 if reliability < 0.5 else 1200,
                ),
            )
        effect = build_branch_effect_receipt(
            args.arm,
            shared_prefix_receipt_sha256=bundle["shared_prefix_receipt_sha256"],
        )
        transport = build_no_external_transport_receipt(args.arm)
        after = sha256(prefix_path)
        envelope = build_branch_envelope(
            arm=args.arm,
            prefix_bundle=bundle,
            prefix_file_sha256_before=before,
            prefix_file_sha256_after=after,
            effect_receipt=effect,
            transport_receipt=transport,
            admission_receipt=admission,
        )
        if args.mode == "duplicate_upstream":
            # Start from a valid cross-artifact bundle, then reseal both
            # artifacts after injecting a repeated upstream effect.  This lets
            # the real parent observe and classify the invalid result instead
            # of having the child fail while trying to construct it.
            effect["repeated_plan_model_effects"] = 1
            unsigned_effect = dict(effect)
            unsigned_effect.pop("receipt_sha256", None)
            effect["receipt_sha256"] = payload_sha256(unsigned_effect)
            envelope["branch_effect_receipt_sha256"] = effect["receipt_sha256"]
            envelope["shared_upstream_effects_repeated"] = True
            unsigned = dict(envelope)
            unsigned.pop("envelope_payload_sha256", None)
            envelope["envelope_payload_sha256"] = payload_sha256(unsigned)
        if args.mode == "wrong_prefix":
            envelope["shared_prefix_receipt_sha256"] = "f" * 64
            unsigned = dict(envelope)
            unsigned.pop("envelope_payload_sha256", None)
            envelope["envelope_payload_sha256"] = payload_sha256(unsigned)
        write_new(Path(args.effect), effect)
        write_new(Path(args.transport), transport)
        if args.mode != "missing_result":
            write_new(Path(args.result), envelope)

    run_child_with_terminal_receipt(
        output_root=Path(args.output_root),
        directory=Path(args.terminal).parent,
        action=action,
        result_name=Path(args.result).name,
        model_receipt_name=Path(args.effect).name,
        transport_receipt_name=Path(args.transport).name,
        terminal_name=Path(args.terminal).name,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
