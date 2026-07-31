"""Frozen package binding for the V2.42.11 entropy runtime.

The controller kernel remains pure.  This module is the narrow package edge
used by the runner, preflight and launcher to open one bundled model file and
verify its byte hash, internal content seal, training-job binding and selected
parent manifest before a forward runtime can be constructed.

No discovery is performed: the relative model path and exact binding schema
are constants.  The binding contains no task content, benchmark label,
prediction, evaluator result or credential.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from .v24211_entropy_controller import POLICY_ID, validate_action_model
from .v24211_entropy_runtime import RUNTIME_POLICY_ID


BINDING_ROLE = "v24212_entropy_runtime_freeze_binding"
MODEL_BUNDLE_PATH = "src/deepwide_agent/v24211_entropy_action_model.json"
BINDING_KEYS = {
    "artifact_version",
    "role",
    "policy_id",
    "runtime_policy_id",
    "policy_branch",
    "action_model_path",
    "action_model_file_sha256",
    "action_model_sha256",
    "action_model_job_manifest_sha256",
    "selected_parent_manifest_sha256",
    "production_package_authorized",
    "mapping_gold_category_question_type_evaluator_score_or_reward_read",
}


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and set(value).issubset(set("0123456789abcdef"))
    )


def canonical_model_bytes(model: Mapping[str, Any]) -> bytes:
    """Serialize one sealed model into the frozen package representation."""

    return (
        json.dumps(
            dict(model),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def build_entropy_binding(
    model: Mapping[str, Any],
    *,
    selected_parent_manifest_sha256: str,
) -> tuple[dict[str, Any], bytes]:
    """Build a content-free freeze binding and its canonical model bytes."""

    if not isinstance(model, Mapping):
        raise ValueError("V2.42.12 action model is not an object")
    model_sha256 = model.get("model_sha256")
    job_sha256 = model.get("job_manifest_sha256")
    clean = validate_action_model(
        dict(model),
        expected_model_sha256=str(model_sha256),
        expected_job_manifest_sha256=str(job_sha256),
    )
    if not _is_sha256(selected_parent_manifest_sha256):
        raise ValueError("V2.42.12 selected parent manifest is invalid")
    payload = canonical_model_bytes(clean)
    binding: dict[str, Any] = {
        "artifact_version": 1,
        "role": BINDING_ROLE,
        "policy_id": POLICY_ID,
        "runtime_policy_id": RUNTIME_POLICY_ID,
        "policy_branch": "full_entropy",
        "action_model_path": MODEL_BUNDLE_PATH,
        "action_model_file_sha256": hashlib.sha256(payload).hexdigest(),
        "action_model_sha256": clean["model_sha256"],
        "action_model_job_manifest_sha256": clean["job_manifest_sha256"],
        "selected_parent_manifest_sha256": selected_parent_manifest_sha256,
        "production_package_authorized": True,
        "mapping_gold_category_question_type_evaluator_score_or_reward_read": False,
    }
    return binding, payload


def load_entropy_binding(
    value: object,
    *,
    root: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Validate one exact binding and open only its fixed bundled model."""

    if not isinstance(value, dict) or set(value) != BINDING_KEYS:
        raise ValueError("V2.42.12 entropy binding schema is not exact")
    if (
        value.get("artifact_version") != 1
        or value.get("role") != BINDING_ROLE
        or value.get("policy_id") != POLICY_ID
        or value.get("runtime_policy_id") != RUNTIME_POLICY_ID
        or value.get("policy_branch") != "full_entropy"
        or value.get("action_model_path") != MODEL_BUNDLE_PATH
        or value.get("production_package_authorized") is not True
        or value.get(
            "mapping_gold_category_question_type_evaluator_score_or_reward_read"
        )
        is not False
        or any(
            not _is_sha256(value.get(key))
            for key in (
                "action_model_file_sha256",
                "action_model_sha256",
                "action_model_job_manifest_sha256",
                "selected_parent_manifest_sha256",
            )
        )
    ):
        raise ValueError("V2.42.12 entropy binding contract drifted")

    root = root.resolve()
    relative = Path(MODEL_BUNDLE_PATH)
    model_path = root / relative
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or model_path.resolve(strict=False) != model_path.absolute()
        or not model_path.resolve(strict=False).is_relative_to(root)
        or model_path.is_symlink()
        or not model_path.is_file()
    ):
        raise ValueError("V2.42.12 bundled model path is noncanonical")
    payload = model_path.read_bytes()
    if hashlib.sha256(payload).hexdigest() != value["action_model_file_sha256"]:
        raise ValueError("V2.42.12 bundled model bytes drifted")
    try:
        model = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("V2.42.12 bundled model is not JSON") from exc
    clean = validate_action_model(
        model,
        expected_model_sha256=value["action_model_sha256"],
        expected_job_manifest_sha256=value[
            "action_model_job_manifest_sha256"
        ],
    )
    if payload != canonical_model_bytes(clean):
        raise ValueError("V2.42.12 bundled model encoding drifted")
    return dict(value), clean


__all__ = [
    "BINDING_KEYS",
    "BINDING_ROLE",
    "MODEL_BUNDLE_PATH",
    "build_entropy_binding",
    "canonical_model_bytes",
    "load_entropy_binding",
]
