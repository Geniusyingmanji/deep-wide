#!/usr/bin/env python3
"""Activate V2.42.75 only after a clean strict label-blind audit."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24275_forward_contract import (  # noqa: E402
    ACTIVATION,
    EXECUTOR_CONCURRENCY,
    FORWARD_PROTOCOL,
    MODEL_SLOT_CAP,
    PREAUDIT,
    RUNNER_MARKER,
    SELECTED_COUNT,
    sha256,
)
from scripts.audit_v24187_phase_liveness import process_snapshot  # noqa: E402
from scripts.audit_v24195_lease_owner_compatibility import (  # noqa: E402
    lease_observation,
)
from scripts.preregister_v24259_deterministic_normalizer_smoke import (  # noqa: E402
    _matching,
)
from scripts.preregister_v24275_two_wave_dev64 import (  # noqa: E402
    FINALIZER_MARKER,
    FUTURE_PATHS,
    OUTPUT,
    publish_new,
    validate_protocol,
)
from scripts.run_v24257_score_first_smoke import (  # noqa: E402
    payload_sha256,
    read_object,
)


def build_activation(root: Path = ROOT, *, now: int | None = None) -> dict:
    root = root.resolve()
    protocol = validate_protocol(root, OUTPUT)
    preaudit = read_object(root / PREAUDIT)
    unsigned = dict(preaudit)
    seal = unsigned.pop("audit_payload_sha256", None)
    if (
        preaudit.get("role") != "v24275_two_wave_dev64_preactivation_audit"
        or preaudit.get("audit_valid") is not True
        or preaudit.get("launch_authorized") is not True
        or preaudit.get("protocol_sha256") != sha256(root / OUTPUT)
        or preaudit.get("forward_contract_sha256")
        != sha256(root / FORWARD_PROTOCOL)
        or preaudit.get("forward_contract_payload_sha256")
        != protocol["forward_runtime_contract"]["payload_sha256"]
        or preaudit.get(
            "historical_per_task_control_prediction_freeze_runtime_summary_opened_or_hashed"
        )
        is not False
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.42.75 preactivation audit drifted")
    rows = process_snapshot()
    lease = lease_observation(root, Path("/proc"))
    present = [
        str(path)
        for path in FUTURE_PATHS
        if path not in {PREAUDIT, ACTIVATION}
        and ((root / path).exists() or (root / path).is_symlink())
    ]
    if (
        present
        or (root / ACTIVATION).exists()
        or (root / ACTIVATION).is_symlink()
        or lease.get("active") is not False
        or _matching(rows, RUNNER_MARKER)
        or _matching(rows, FINALIZER_MARKER)
    ):
        raise RuntimeError("V2.42.75 activation boundary is not clean")
    value = {
        "artifact_version": 1,
        "role": "v24275_two_wave_dev64_activation",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "active",
        "forward_contract_sha256": sha256(root / FORWARD_PROTOCOL),
        "forward_contract_payload_sha256": protocol["forward_runtime_contract"][
            "payload_sha256"
        ],
        "preactivation_audit_sha256": sha256(root / PREAUDIT),
        "forward_manifest_sha256": protocol["forward_surface"][
            "dependency_manifest_sha256"
        ],
        "selected_count": SELECTED_COUNT,
        "executor_concurrency": EXECUTOR_CONCURRENCY,
        "global_model_slot_cap": MODEL_SLOT_CAP,
        "shared_api_lease_active_before_activation": False,
        "network_model_search_fetch_evaluator_or_api_called": False,
        "mapping_control_prediction_gold_category_question_type_split_evaluator_score_read": False,
        "new_exact220_or_sota_authorized": False,
    }
    value["activation_payload_sha256"] = payload_sha256(value)
    return value


if __name__ == "__main__":
    publish_new(ROOT / ACTIVATION, build_activation())
    print(json.dumps({"path": str(ACTIVATION), "sha256": sha256(ROOT / ACTIVATION)}))
