#!/usr/bin/env python3
"""One-shot V2.42.58 wrapper for the byte-frozen V2.42.57 runner."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from scripts import run_v24257_score_first_smoke as frozen  # noqa: E402
from scripts.activate_v24258_score_first_smoke_successor import (  # noqa: E402
    validate_activation,
)
from scripts.audit_v24195_lease_owner_compatibility import (  # noqa: E402
    lease_observation,
)
from scripts.preregister_v24257_score_first_smoke import (  # noqa: E402
    EXECUTION_START,
    OUTPUT_ROOT,
    RESULT,
    RUNNER_MARKER,
)
from scripts.preregister_v24258_score_first_smoke_successor import (  # noqa: E402
    OUTPUT as SUCCESSOR_PROTOCOL,
    WRAPPER,
    validate_protocol,
)


def preflight() -> None:
    if Path(__file__).resolve() != (ROOT / WRAPPER).resolve():
        raise RuntimeError("V2.42.58 wrapper path drifted")
    protocol = validate_protocol(ROOT, SUCCESSOR_PROTOCOL)
    validate_activation(ROOT)
    lease = lease_observation(ROOT, Path("/proc"))
    if (
        protocol["execution"]["compatible_process_script_suffix"] != RUNNER_MARKER
        or lease.get("active") is not False
        or any(
            (ROOT / path).exists() or (ROOT / path).is_symlink()
            for path in (EXECUTION_START, OUTPUT_ROOT, RESULT)
        )
    ):
        raise RuntimeError("V2.42.58 corrected launch boundary drifted")


def main() -> None:
    preflight()
    frozen.RUNNER_MARKER = RUNNER_MARKER
    frozen.main()


if __name__ == "__main__":
    main()
