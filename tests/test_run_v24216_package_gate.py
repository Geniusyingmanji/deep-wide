from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.run_v24216_package_gate import (
    ARM_ROOTS,
    _materialize_arm,
    build_arm_freeze,
    build_forward_barrier,
)


FORWARD_FILES = {
    "src/deepwide_agent/__init__.py": "",
    "src/deepwide_agent/anthropic_search.py": "",
    "src/deepwide_agent/clients.py": "",
    "src/deepwide_agent/native_search.py": "",
    "src/deepwide_agent/prompts.py": "",
    "src/deepwide_agent/runtime.py": (
        'STATE_SCHEMA_VERSION = 99\nPIPELINE_VERSION = "v-test"\n'
    ),
    "src/deepwide_agent/shadow_risk.py": "",
    "scripts/run_deepwide_agent.py": "",
    "scripts/preflight_deepwide.py": "",
    "scripts/launch_frozen_deepwide.py": "",
}
TEMPLATE = {
    "model": {"name": "gpt-5.6-sol"},
    "search": {"provider": "anthropic"},
    "runtime": {"candidate_tokens": 20000},
    "launch_gates": {"preflight_consecutive_successes": 2},
}


class RunV24216PackageGateTests(unittest.TestCase):
    def test_arm_freezes_share_execution_identity_and_ids(self) -> None:
        baseline = build_arm_freeze(
            "baseline",
            FORWARD_FILES,
            manifest_sha="m" * 64,
            ids_sha="i" * 64,
            template=TEMPLATE,
        )
        candidate = build_arm_freeze(
            "candidate",
            {**FORWARD_FILES, "src/deepwide_agent/runtime.py": 'STATE_SCHEMA_VERSION = 100\nPIPELINE_VERSION = "v-candidate"\n'},
            manifest_sha="m" * 64,
            ids_sha="i" * 64,
            template=TEMPLATE,
        )
        self.assertEqual(baseline["selected_ids_sha256"], candidate["selected_ids_sha256"])
        self.assertEqual(
            {key: baseline[key] for key in ("model", "search", "runtime", "launch_gates")},
            {key: candidate[key] for key in ("model", "search", "runtime", "launch_gates")},
        )
        self.assertNotEqual(baseline["state_schema_version"], candidate["state_schema_version"])
        self.assertEqual(baseline["manifest"], "data/runtime_manifest.jsonl")
        self.assertFalse(baseline["reporting"]["forward_resume_or_selective_rerun_allowed"])

    def test_forward_barrier_contains_no_mapping_or_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pair = root / "results/v24216_package_gate_pair_prepare_v1_20260731.json"
            pair.parent.mkdir(parents=True)
            pair.write_text("{}\n", encoding="utf-8")
            row = {
                "selected": 64,
                "completed": 1,
                "failed": 63,
                "ids_sha256": "i" * 64,
                "freeze_sha256": "f" * 64,
                "runtime_predictions_sha256": "r" * 64,
                "run_summary_sha256": "s" * 64,
                "contents_emitted": False,
            }
            value = build_forward_barrier(
                {"arm": "baseline", **row},
                {"arm": "candidate", **row},
                root=root,
            )
        encoded = json.dumps(value, sort_keys=True)
        self.assertTrue(value["both_forward_arms_exact_terminal"])
        self.assertFalse(value["mapping_path_opened_or_hashed"])
        self.assertNotIn("entity_acc", encoded)
        self.assertEqual(
            value["pair_prepare"]["sha256"],
            hashlib.sha256(b"{}\n").hexdigest(),
        )

    def test_materialized_data_and_config_do_not_enter_source_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            arm_root = base / "arm"
            environment = base / ".venv-eval"
            environment.mkdir()
            manifest = base / "manifest.jsonl"
            ids = base / "ids.txt"
            manifest.write_text(
                '{"opaque_id":"task_000000000000000000000000","question":"q"}\n',
                encoding="utf-8",
            )
            ids.write_text(
                "\n".join(f"task_{index:024x}" for index in range(64)) + "\n",
                encoding="utf-8",
            )
            files = {**FORWARD_FILES, "README.test": "source"}
            with mock.patch.dict(ARM_ROOTS, {"baseline": arm_root}), mock.patch(
                "scripts.run_v24216_package_gate.ROOT", base
            ):
                row = _materialize_arm(
                    "baseline",
                    files,
                    template=TEMPLATE,
                    source_manifest=manifest,
                    source_ids=ids,
                )
            self.assertEqual(row["source_manifest_sha256"], hashlib.sha256(
                json.dumps(
                    {
                        name: hashlib.sha256(text.encode()).hexdigest()
                        for name, text in sorted(files.items())
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode()
            ).hexdigest())
            self.assertTrue((arm_root / "data/runtime_manifest.jsonl").is_file())
            self.assertTrue((arm_root / "configs/dev64_v24216_selected_baseline_cold_v1_20260731/devval.ids").is_file())


if __name__ == "__main__":
    unittest.main()
