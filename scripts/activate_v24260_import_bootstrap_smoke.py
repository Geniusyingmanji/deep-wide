#!/usr/bin/env python3
"""Create-exclusive activation for the V2.42.60 smoke."""

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

from scripts.audit_v24187_phase_liveness import process_snapshot  # noqa: E402
from scripts.audit_v24195_lease_owner_compatibility import lease_observation  # noqa: E402
from scripts.preregister_v24259_deterministic_normalizer_smoke import _matching  # noqa: E402
from scripts.preregister_v24260_import_bootstrap_smoke import (  # noqa: E402
    ACTIVATION,
    FUTURE_PATHS,
    OUTPUT,
    RUNNER_MARKER,
    WATCHER_MARKER,
    publish,
    validate_protocol,
)
from scripts.run_v24257_score_first_smoke import payload_sha256, sha256  # noqa: E402


ROLE = "v24260_import_bootstrap_smoke_activation"


def build_activation(root: Path = ROOT, *, now: int | None = None) -> dict:
    root = root.resolve()
    protocol = validate_protocol(root, OUTPUT)
    rows = process_snapshot()
    lease = lease_observation(root, Path("/proc"))
    present = [str(path) for path in FUTURE_PATHS if path != ACTIVATION and ((root / path).exists() or (root / path).is_symlink())]
    if present or (root / ACTIVATION).exists() or lease.get("active") is not False or lease.get("ordinary") is not True or _matching(rows, RUNNER_MARKER) or _matching(rows, WATCHER_MARKER):
        raise RuntimeError("V2.42.60 activation boundary is not pristine")
    value = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "active",
        "protocol_sha256": sha256(root / OUTPUT),
        "decision_contract_sha256": protocol["decision_contract_sha256"],
        "control_manifest_sha256": protocol["control_surface"]["manifest_sha256"],
        "selected_opaque_ids_sha256": protocol["task_contract"]["selected_opaque_ids_sha256"],
        "shared_api_lease_active_before_activation": False,
        "network_model_search_fetch_evaluator_or_api_called": False,
        "benchmark_question_prediction_mapping_gold_category_evaluator_score_read": False,
        "official_evaluator_dev64_full220_or_leaderboard_authorized": False,
    }
    value["activation_payload_sha256"] = payload_sha256(value)
    return value


if __name__ == "__main__":
    publish(ROOT / ACTIVATION, build_activation())
    print(json.dumps({"path": str(ACTIVATION), "sha256": sha256(ROOT / ACTIVATION)}))
