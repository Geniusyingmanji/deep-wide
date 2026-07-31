from __future__ import annotations

import copy
import math
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24211_entropy_controller import (  # noqa: E402
    CONTEXT_ACTIONS,
    FEATURE_KEYS,
    MODEL_ROLE,
    NO_ENTROPY_FEATURE_KEYS,
    object_sha256,
)
from deepwide_agent.v24212_entropy_binding import (  # noqa: E402
    MODEL_BUNDLE_PATH,
    build_entropy_binding,
    load_entropy_binding,
)


SHA_B = "b" * 64
SHA_C = "c" * 64


def _action_model(feature_keys: tuple[str, ...]) -> dict[str, object]:
    width = len(feature_keys) + 1
    return {
        "fit_records": 5,
        "calibration_records": 3,
        "raw_coefficients": {
            "task_contribution": [0.0] * width,
            "log_action_system_tokens": [0.0] * width,
        },
        "affine_calibrators": {
            "task_contribution": [0.1, 0.0],
            "log_action_system_tokens": [math.log1p(100), 0.0],
        },
    }


def _branch(feature_keys: tuple[str, ...]) -> dict[str, object]:
    return {
        "feature_keys": list(feature_keys),
        "models": {
            context: {
                action: _action_model(feature_keys) for action in actions
            }
            for context, actions in CONTEXT_ACTIONS.items()
        },
    }


def sealed_model() -> dict[str, object]:
    value: dict[str, object] = {
        "artifact_version": 1,
        "role": MODEL_ROLE,
        "job_manifest_sha256": SHA_B,
        "model_ready": True,
        "blockers": [],
        "full_model": _branch(FEATURE_KEYS),
        "no_entropy_baseline": _branch(NO_ENTROPY_FEATURE_KEYS),
        "fit_record_count": 45,
        "calibration_record_count": 27,
        "fit_task_clusters": 16,
        "calibration_task_clusters": 8,
        "ridge_lambda": 0.001,
        "minimum_fit_records_per_context_action": 5,
        "minimum_calibration_records_per_context_action": 3,
        "fit_calibration_aggregate_sha256": SHA_C,
        "audit_outcomes_read": False,
        "controller_or_training_authorized": False,
    }
    value["model_sha256"] = object_sha256(value)
    return value


class V24212EntropyBindingTests(unittest.TestCase):
    def _tree(self, model: dict[str, object]) -> tuple[tempfile.TemporaryDirectory, Path]:
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        binding, payload = build_entropy_binding(
            model, selected_parent_manifest_sha256="a" * 64
        )
        path = root / MODEL_BUNDLE_PATH
        path.parent.mkdir(parents=True)
        path.write_bytes(payload)
        self.binding = binding
        return temporary, root

    def test_round_trip_binds_model_job_and_parent(self) -> None:
        temporary, root = self._tree(sealed_model())
        with temporary:
            binding, model = load_entropy_binding(self.binding, root=root)
        self.assertEqual(model["model_sha256"], binding["action_model_sha256"])
        self.assertEqual(
            model["job_manifest_sha256"],
            binding["action_model_job_manifest_sha256"],
        )
        self.assertEqual(binding["selected_parent_manifest_sha256"], "a" * 64)
        self.assertTrue(binding["production_package_authorized"])

    def test_model_byte_tamper_fails_before_use(self) -> None:
        temporary, root = self._tree(sealed_model())
        with temporary:
            path = root / MODEL_BUNDLE_PATH
            path.write_bytes(path.read_bytes() + b" ")
            with self.assertRaisesRegex(ValueError, "bytes drifted"):
                load_entropy_binding(self.binding, root=root)

    def test_extra_binding_field_and_resealed_model_fail(self) -> None:
        temporary, root = self._tree(sealed_model())
        with temporary:
            extra = dict(self.binding)
            extra["question_type"] = "x"
            with self.assertRaisesRegex(ValueError, "schema is not exact"):
                load_entropy_binding(extra, root=root)
            model = sealed_model()
            model["model_ready"] = False
            model["model_sha256"] = object_sha256(
                {
                    key: value
                    for key, value in model.items()
                    if key != "model_sha256"
                }
            )
            with self.assertRaisesRegex(ValueError, "seal or provenance"):
                build_entropy_binding(
                    model, selected_parent_manifest_sha256="a" * 64
                )

    def test_binding_copy_cannot_redirect_model_path(self) -> None:
        temporary, root = self._tree(sealed_model())
        with temporary:
            redirected = copy.deepcopy(self.binding)
            redirected["action_model_path"] = "results/model.json"
            with self.assertRaisesRegex(ValueError, "contract drifted"):
                load_entropy_binding(redirected, root=root)


if __name__ == "__main__":
    unittest.main()
