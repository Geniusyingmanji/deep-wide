#!/usr/bin/env python3
"""Append-only post-forward audit adapter for frozen V2.54.06.

The frozen V2.54.06 finalizer delegates its native forward audit to the
V2.52.67 shell.  That inherited function reads its own module-level
``EVALUATOR_ROOT``.  After historical V2.52.67 evaluation completed, that
directory legitimately exists, so the inherited future-surface check reports
a false positive even though every V2.54.06 evaluator surface is pristine.

This adapter changes no frozen forward dependency, task, prediction, budget,
or protocol.  It binds only the inherited read-only audit function's evaluator
root to the already-frozen V2.54.06 output root, restores the old module value
afterward, and records its own hash in the sealed audit artifact.  It does not
open mapping, gold, answer, score, or evaluator resources.
"""

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

from deepwide_agent import v25406_grounded_membership_exact220_contract as contract  # noqa: E402
from scripts import finalize_v25406_grounded_membership_exact220 as frozen  # noqa: E402


ADAPTER = Path("scripts/audit_v25409_v25406_grounded_membership_exact220_forward.py")
FROZEN_FINALIZER_SHA256 = (
    "b5429cf703d3e0e871c07b9a87498eb17e24ca63184b79ef6bfbd49d95819e20"
)


def _read(relative: Path) -> dict[str, Any]:
    value = json.loads(
        contract.ordinary(ROOT, relative, tracked=True).read_text(encoding="utf-8")
    )
    if not isinstance(value, dict):
        raise RuntimeError("V2.54.09 expected JSON object")
    return value


def _future_surfaces() -> tuple[Path, ...]:
    return (
        contract.FORWARD_AUDIT,
        contract.EVALUATOR_PROTOCOL,
        contract.RESULT,
        contract.POSTAUDIT,
        frozen.EVALUATOR_ROOT,
    )


def _future_pristine() -> bool:
    return all(
        not (ROOT / path).exists() and not (ROOT / path).is_symlink()
        for path in _future_surfaces()
    )


def _native_with_v25406_evaluator_root() -> tuple[dict[str, Any], Path]:
    """Temporarily bind only the inherited audit's module-level root."""

    frozen.configure()
    inherited_root = frozen.base.EVALUATOR_ROOT
    try:
        frozen.base.EVALUATOR_ROOT = frozen.EVALUATOR_ROOT
        value = frozen._build_native_forward_audit()
    finally:
        frozen.base.EVALUATOR_ROOT = inherited_root
    return value, inherited_root


def build_forward_audit() -> dict[str, Any]:
    protocol = contract.validate_protocol(ROOT, _read(contract.PROTOCOL))
    live_finalizer_sha256 = contract.sha256(ROOT / contract.FINALIZER)
    protocol_finalizer_sha256 = protocol["dependency_manifest"].get(
        str(contract.FINALIZER)
    )
    adapter_path = contract.ordinary(ROOT, ADAPTER, tracked=True)
    head = contract.git(ROOT, "rev-parse", "HEAD")
    target = contract.git(ROOT, "rev-parse", "target/main")
    pristine_before_audit = _future_pristine()

    value, inherited_root = _native_with_v25406_evaluator_root()
    copied = copy.deepcopy(dict(value))
    copied.pop("audit_payload_sha256", None)
    checks = dict(copied["checks"])
    checks.update(
        {
            "postforward_adapter_committed_and_pushed": head == target,
            "frozen_finalizer_matches_protocol_manifest": (
                live_finalizer_sha256
                == protocol_finalizer_sha256
                == FROZEN_FINALIZER_SHA256
            ),
            "frozen_forward_dependency_manifest_live": (
                protocol["dependency_manifest"]
                == contract.dependency_manifest(ROOT, tracked=True)
            ),
            "v25406_future_evaluator_surface_pristine": pristine_before_audit,
            "inherited_historical_evaluator_root_not_used": (
                inherited_root != frozen.EVALUATOR_ROOT
                and frozen.base.EVALUATOR_ROOT == inherited_root
            ),
        }
    )
    findings = sorted(name for name, passed in checks.items() if not passed)
    authorization = dict(copied["authorization"])
    authorization["postfreeze_exact220_evaluator_protocol"] = not findings
    copied.update(
        {
            "checks": checks,
            "findings": findings,
            "audit_valid": not findings,
            "authorization": authorization,
            "postforward_audit_adapter": {
                "path": str(ADAPTER),
                "sha256": contract.sha256(adapter_path),
                "reason": "bind inherited audit root to frozen v25406 evaluator root",
                "frozen_forward_dependency_prediction_or_protocol_modified": False,
                "mapping_gold_answer_score_or_evaluator_resource_opened": False,
            },
        }
    )
    sealed = contract.seal(copied, "audit_payload_sha256")
    frozen.configure()
    frozen.base.base.validate_forward_audit(sealed)
    return sealed


def main() -> None:
    value = build_forward_audit()
    if not value["audit_valid"]:
        raise RuntimeError(value["findings"])
    frozen.base._publish_new(ROOT / contract.FORWARD_AUDIT, value)
    print(
        json.dumps(
            {
                "path": str(contract.FORWARD_AUDIT),
                "audit_valid": True,
                "findings": [],
                "postfreeze_exact220_evaluator_protocol": value["authorization"][
                    "postfreeze_exact220_evaluator_protocol"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
