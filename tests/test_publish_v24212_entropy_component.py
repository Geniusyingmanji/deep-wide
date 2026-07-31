from __future__ import annotations

import ast
import math
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24211_entropy_controller import (  # noqa: E402
    CONTEXT_ACTIONS,
    FEATURE_KEYS,
    MODEL_ROLE,
    NO_ENTROPY_FEATURE_KEYS,
    object_sha256,
)
from scripts.audit_v24205_markdown_rebase_feasibility import (  # noqa: E402
    rebase_markdown_production,
    runtime_identity,
)
from scripts.audit_v24208_search_rebase_feasibility import (  # noqa: E402
    patch_search_production,
)
from scripts.publish_v24212_entropy_component import (  # noqa: E402
    FORWARD_ADDITIONS,
    INTEGRATED_TEST,
    materialize_candidate,
    parent_regression_contract,
    patch_entropy_production,
)
from scripts.replay_v24201_repo_local_candidate_dag import (  # noqa: E402
    build_replay,
    manifest_sha256,
    text_manifest,
)


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
        "job_manifest_sha256": "b" * 64,
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
        "fit_calibration_aggregate_sha256": "c" * 64,
        "audit_outcomes_read": False,
        "controller_or_training_authorized": False,
    }
    value["model_sha256"] = object_sha256(value)
    return value


class PublishV24212EntropyComponentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        replay, maps = build_replay()
        if replay.get("all_stage_file_maps_byte_exact_to_frozen_publications") is not True:
            raise RuntimeError("test parent replay failed")
        parents = {
            schema: dict(maps[f"schema{schema}"])
            for schema in (68, 69, 70, 76, 77)
        }
        for source, target in ((76, 78), (77, 79)):
            parents[target] = rebase_markdown_production(
                parents[source],
                target_schema=target,
                target_suffix="-selected-markdown-rank-slot",
            )
        for source, target in (
            (68, 80),
            (69, 81),
            (76, 82),
            (78, 83),
            (77, 84),
            (79, 85),
            (70, 86),
        ):
            parents[target] = patch_search_production(
                parents[source], target_schema=target
            )
        cls.parents = parents
        cls.parent = parents[68]

    def test_rebase_binds_all_execution_surfaces(self) -> None:
        parent_sha = manifest_sha256(text_manifest(self.parent))
        files, report = patch_entropy_production(
            self.parent,
            model=sealed_model(),
            target_schema=87,
            selected_parent_manifest_sha256=parent_sha,
        )
        schema, version = runtime_identity(files["src/deepwide_agent/runtime.py"])
        self.assertEqual(schema, 87)
        self.assertTrue(version.endswith("-label-blind-entropy-voc-controller"))
        self.assertTrue(set(FORWARD_ADDITIONS).issubset(files))
        self.assertIn(INTEGRATED_TEST, files)
        self.assertTrue(report["real_state_transition_adapters_included"])
        self.assertTrue(report["runtime_constructor_hooked"])
        self.assertTrue(report["preflight_and_launcher_model_binding_enforced"])
        self.assertTrue(
            report[
                "historical_module_containing_revoked_projection_arm_present_as_adapter_dependency"
            ]
        )
        self.assertFalse(
            report["projection_only_action_arm_selected_instantiated_or_called"]
        )
        self.assertIn("runtime = V24211EntropyRuntime(", files["scripts/run_deepwide_agent.py"])
        self.assertNotIn("PRODUCTION_PACKAGE_AUTHORIZED = False", files["src/deepwide_agent/v24211_entropy_runtime.py"])
        for relative, source in files.items():
            if relative.endswith(".py"):
                ast.parse(source, filename=relative)

    def test_parent_manifest_and_model_fail_closed(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "parent manifest drifted"):
            patch_entropy_production(
                self.parent,
                model=sealed_model(),
                target_schema=87,
                selected_parent_manifest_sha256="0" * 64,
            )
        broken = sealed_model()
        broken["model_ready"] = False
        with self.assertRaisesRegex(ValueError, "seal or provenance"):
            patch_entropy_production(
                self.parent,
                model=broken,
                target_schema=87,
                selected_parent_manifest_sha256=manifest_sha256(
                    text_manifest(self.parent)
                ),
            )

    def test_all_fourteen_parent_graphs_rebase_append_only(self) -> None:
        self.assertEqual(set(self.parents), set(range(68, 87)) - set(range(71, 76)))
        targets = dict(zip(sorted(self.parents), range(87, 101), strict=True))
        output_manifests: set[str] = set()
        for source_schema, parent in sorted(self.parents.items()):
            with self.subTest(source_schema=source_schema):
                parent_sha = manifest_sha256(text_manifest(parent))
                files, report = patch_entropy_production(
                    parent,
                    model=sealed_model(),
                    target_schema=targets[source_schema],
                    selected_parent_manifest_sha256=parent_sha,
                )
                self.assertEqual(
                    runtime_identity(files["src/deepwide_agent/runtime.py"])[0],
                    targets[source_schema],
                )
                self.assertEqual(
                    report["parent_state_schema_version"], source_schema
                )
                output_manifests.add(
                    report["candidate_regular_file_manifest_sha256"]
                )
        self.assertEqual(len(output_manifests), 14)

    def test_schema68_candidate_runs_parent_plus_entropy_regression(self) -> None:
        parent_sha = manifest_sha256(text_manifest(self.parent))
        files, report = patch_entropy_production(
            self.parent,
            model=sealed_model(),
            target_schema=87,
            selected_parent_manifest_sha256=parent_sha,
        )
        parent_modules, parent_tests = parent_regression_contract(
            {
                "search_component_selected": False,
                "baseline_name": "p12",
                "semantic_parent_variant": "selected_baseline",
            },
            {},
            {},
        )
        with tempfile.TemporaryDirectory(
            dir=ROOT / "outputs", prefix="v24212-synthetic-regression-"
        ) as directory:
            candidate = Path(directory) / "candidate"
            receipt = materialize_candidate(
                files,
                report,
                parent_modules=parent_modules,
                parent_tests=parent_tests,
                candidate=candidate,
            )
        self.assertEqual(receipt["integrated_tests"]["parent_tests_run"], 28)
        self.assertEqual(receipt["integrated_tests"]["entropy_tests_added"], 37)
        self.assertEqual(receipt["integrated_tests"]["tests_run"], 65)
        self.assertIn(
            "src/deepwide_agent/v24211_entropy_action_model.json",
            receipt["candidate_forward_manifest"],
        )


if __name__ == "__main__":
    unittest.main()
