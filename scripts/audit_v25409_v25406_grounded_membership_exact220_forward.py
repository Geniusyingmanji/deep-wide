#!/usr/bin/env python3
"""Append-only post-forward control adapter for frozen V2.54.06.

The frozen V2.54.06 finalizer delegates its native forward audit to the
V2.52.67 shell.  That inherited function reads its own module-level
``EVALUATOR_ROOT``.  After historical V2.52.67 evaluation completed, that
directory legitimately exists, so the inherited future-surface check reports
a false positive even though every V2.54.06 evaluator surface is pristine.

The same inheritance layer also leaves the bottom V2.47.91 validator's
``contract`` global bound to V2.47.91.  The frozen V2.54.06 finalizer correctly
binds its paths and barrier but its eventual validator therefore compares a
V2.54.06 artifact with historical V2.47.91 hashes.  This adapter explicitly
binds that post-forward shell to V2.54.06 in-process.

It changes no frozen forward dependency, task, prediction, budget, or
protocol.  The ``audit`` command does not open mapping, gold, answer, score,
or evaluator resources.  Only after a pushed valid forward audit may the
``protocol`` command open and hash evaluator resources; ``evaluate`` then
uses the fixed 32-way exactly-once shell, and ``postaudit`` is read-only except
for its new audit artifact.
"""

from __future__ import annotations

import copy
import argparse
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
ADAPTER_TEST = Path(
    "tests/test_audit_v25409_v25406_grounded_membership_exact220_forward.py"
)
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


def configure_postforward() -> None:
    """Bind every inherited post-forward global to frozen V2.54.06."""

    frozen.configure()
    bottom = frozen.base.base
    bottom.contract = contract
    bottom._forward_barrier = frozen._forward_barrier
    controls = tuple(bottom.CONTROL_FILES)
    additions = (str(ADAPTER), str(ADAPTER_TEST))
    bottom.CONTROL_FILES = controls + tuple(
        path for path in additions if path not in controls
    )


def _native_with_v25406_evaluator_root() -> tuple[dict[str, Any], Path]:
    """Temporarily bind only the inherited audit's module-level root."""

    configure_postforward()
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
    configure_postforward()
    frozen.base.base.validate_forward_audit(sealed)
    return sealed


def build_evaluator_protocol() -> dict[str, Any]:
    configure_postforward()
    value = frozen.base.base.build_evaluator_protocol()
    return frozen.base.base.validate_evaluator_protocol(value)


def evaluate() -> dict[str, Any]:
    configure_postforward()
    return frozen.base.base.evaluate()


def build_postresult_audit() -> dict[str, Any]:
    configure_postforward()
    value = frozen.base.base.build_postresult_audit()
    return frozen.base.base.validate_postresult_audit(value)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("audit", "protocol", "evaluate", "postaudit"))
    args = parser.parse_args()
    if args.command == "audit":
        value = build_forward_audit()
        if not value["audit_valid"]:
            raise RuntimeError(value["findings"])
        path = contract.FORWARD_AUDIT
        output = {
            "path": str(path),
            "audit_valid": True,
            "findings": [],
            "postfreeze_exact220_evaluator_protocol": value["authorization"][
                "postfreeze_exact220_evaluator_protocol"
            ],
        }
    elif args.command == "protocol":
        value = build_evaluator_protocol()
        path = contract.EVALUATOR_PROTOCOL
        output = {"path": str(path), "authorization": value["authorization"]}
    elif args.command == "evaluate":
        value = evaluate()
        print(
            json.dumps(
                {
                    "path": str(contract.RESULT),
                    "status": value["status"],
                    "metrics": value["metrics"]["all_220"],
                },
                sort_keys=True,
            )
        )
        return
    else:
        value = build_postresult_audit()
        path = contract.POSTAUDIT
        output = {
            "path": str(path),
            "audit_valid": value["audit_valid"],
            "findings": value["findings"],
        }
    frozen.base._publish_new(ROOT / path, value)
    print(json.dumps(output, sort_keys=True))


if __name__ == "__main__":
    main()
