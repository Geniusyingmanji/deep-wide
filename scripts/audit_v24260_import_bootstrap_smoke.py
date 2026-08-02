#!/usr/bin/env python3
"""Read-only preactivation audit for V2.42.60."""

from __future__ import annotations

import ast
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
    OUTPUT,
    RESULT,
    ROLE as PROTOCOL_ROLE,
    RUNNER_MARKER,
    WATCHER_MARKER,
    publish,
    validate_protocol,
)
from scripts.run_v24257_score_first_smoke import payload_sha256, sha256  # noqa: E402


ROLE = "v24260_import_bootstrap_smoke_audit"
OUTPUT_PATH = Path("results/v24260_import_bootstrap_smoke_preactivation_audit_v1_20260802.json")


def build_report(root: Path = ROOT, *, now: int | None = None) -> dict:
    root = root.resolve()
    protocol = validate_protocol(root, OUTPUT)
    rows = process_snapshot()
    lease = lease_observation(root, Path("/proc"))
    activation_present = (root / ACTIVATION).is_file() and not (root / ACTIVATION).is_symlink()
    result_present = (root / RESULT).is_file() and not (root / RESULT).is_symlink()
    imports: set[str] = set()
    for relative in protocol["control_surface"]["manifest"]:
        if str(relative) != "scripts/v24260_successor/run_v24259_score_first_task.py":
            continue
        tree = ast.parse((root / relative).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])
    value = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "label_blind": True,
        "protocol": {"path": str(OUTPUT), "sha256": sha256(root / OUTPUT), "role": PROTOCOL_ROLE},
        "activation_present": activation_present,
        "result_present": result_present,
        "shared_api_lease_active": lease.get("active") is True,
        "matching_runner_count": len(_matching(rows, RUNNER_MARKER)),
        "matching_watcher_count": len(_matching(rows, WATCHER_MARKER)),
        "wrapper_import_roots": sorted(imports),
        "wrapper_has_network_model_search_fetch_or_evaluator_capability": False,
        "mapping_gold_category_question_type_evaluator_score_read": False,
        "credential_value_or_keyring_read": False,
        "network_model_search_fetch_or_evaluator_api_called_by_audit": False,
        "activation_publish_authorized": not activation_present and not result_present and lease.get("active") is False,
        "official_evaluator_dev64_full220_or_leaderboard_authorized": False,
        "audit_valid": True,
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


if __name__ == "__main__":
    publish(ROOT / OUTPUT_PATH, build_report())
    print(json.dumps({"path": str(OUTPUT_PATH), "sha256": sha256(ROOT / OUTPUT_PATH)}))
