"""Non-contaminating controller bindings after the V2.46.12 failure.

V2.46.12 reused the V2.46.04 protocol builder by mutating attributes on the
real V2.46.07 proof module.  The mutation remained active while the external
parent validated a worker bundle, so V2.46.07 resolved its parent validator as
V2.45.90 instead of V2.45.99 and the one preregistered wave terminated.

This repair exposes two serialized views by rebinding only the controller
module.  The protocol view gives V2.46.04 its native V2.45.99/V2.46.00/
V2.46.01/V2.46.02 layer.  The runtime view gives it the V2.46.07--10
provenance layer.  Neither view ever writes a field on either proof module,
and every exit verifies that the real V2.46.07 parent and the frozen V2.46.09
validator binding retain their import-time identities.
"""

from __future__ import annotations

import threading
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from . import v24599_proof_carrying_title_funnel as protocol_proof
from . import v24600_total_title_funnel_projection as protocol_total
from . import v24601_bounded_title_funnel_parent as protocol_bounded
from . import v24607_proof_carrying_title_provenance as runtime_proof
from . import v24608_total_title_provenance_projection as runtime_total
from . import v24609_bounded_title_provenance_parent as runtime_bounded


POLICY_ID = "v24614_noncontaminating_title_provenance_controller_binding_v1"
PROTOCOL_BINDING_COUNT = 4
RUNTIME_BINDING_COUNT = 4
ORIGINAL_RUNTIME_PARENT_PROOF = runtime_proof.parent_proof
ORIGINAL_RUNTIME_VALIDATOR = runtime_proof.validate_proof_carrying_title_provenance_bundle
ORIGINAL_BOUNDED_PROOF = runtime_bounded.run_timed_subprocess.__globals__["proof"]
ORIGINAL_BOUNDED_TOTAL = runtime_bounded.run_timed_subprocess.__globals__["total"]
_GUARD = threading.RLock()


def _collectors() -> tuple[Any, Any]:
    # Imported lazily to avoid a src -> scripts import during ordinary runtime
    # module discovery.  The caller is an external controller process whose
    # repository root is already on sys.path.
    from scripts import v24602_title_funnel_collector_repair as protocol_collector
    from scripts import v24610_title_provenance_collector as runtime_collector

    return protocol_collector, runtime_collector


def invariant_valid() -> bool:
    return (
        runtime_proof.parent_proof is ORIGINAL_RUNTIME_PARENT_PROOF
        and runtime_proof.validate_proof_carrying_title_provenance_bundle
        is ORIGINAL_RUNTIME_VALIDATOR
        and runtime_bounded.run_timed_subprocess.__globals__["proof"]
        is ORIGINAL_BOUNDED_PROOF
        and runtime_bounded.run_timed_subprocess.__globals__["total"]
        is ORIGINAL_BOUNDED_TOTAL
        and ORIGINAL_BOUNDED_PROOF is runtime_proof
        and ORIGINAL_BOUNDED_TOTAL is runtime_total
    )


def binding_vector(*, protocol_compatibility: bool) -> dict[str, Any]:
    protocol_collector, runtime_collector = _collectors()
    if protocol_compatibility:
        return {
            "proof": protocol_proof,
            "total": protocol_total,
            "bounded": protocol_bounded,
            "collector_repair": protocol_collector,
        }
    return {
        "proof": runtime_proof,
        "total": runtime_total,
        "bounded": runtime_bounded,
        "collector_repair": runtime_collector,
    }


@contextmanager
def controller_bindings(
    controller: Any, *, protocol_compatibility: bool
) -> Iterator[None]:
    if not invariant_valid():
        raise RuntimeError("V2.46.14 runtime proof binding drifted before entry")
    expected = binding_vector(protocol_compatibility=protocol_compatibility)
    with _GUARD:
        missing = object()
        originals = {name: getattr(controller, name, missing) for name in expected}
        try:
            for name, value in expected.items():
                setattr(controller, name, value)
            if not invariant_valid():
                raise RuntimeError("V2.46.14 controller entry contaminated runtime proof")
            yield
        finally:
            for name, value in originals.items():
                if value is missing:
                    delattr(controller, name)
                else:
                    setattr(controller, name, value)
            if not invariant_valid():
                raise RuntimeError("V2.46.14 controller exit contaminated runtime proof")


__all__ = [
    "ORIGINAL_BOUNDED_PROOF",
    "ORIGINAL_BOUNDED_TOTAL",
    "ORIGINAL_RUNTIME_PARENT_PROOF",
    "ORIGINAL_RUNTIME_VALIDATOR",
    "POLICY_ID",
    "PROTOCOL_BINDING_COUNT",
    "RUNTIME_BINDING_COUNT",
    "binding_vector",
    "controller_bindings",
    "invariant_valid",
    "protocol_bounded",
    "protocol_proof",
    "protocol_total",
    "runtime_bounded",
    "runtime_proof",
    "runtime_total",
]
