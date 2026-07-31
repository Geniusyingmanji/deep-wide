from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.preregister_v24198_candidate_bundle import (
    CONTROL_FILES,
    DECISION_FIELDS,
    ROOT,
    build_protocol,
    publish_new,
    validate_protocol,
)
from deepwide_agent.v24197_parallel_all220 import payload_sha256


class PreregisterV24198CandidateBundleTests(unittest.TestCase):
    def test_protocol_separates_selection_compilation_and_execution(self) -> None:
        with mock.patch(
            "scripts.preregister_v24198_candidate_bundle.protected_processes",
            return_value={},
        ):
            value = build_protocol(
                ROOT,
                created_at_unix=1,
                require_pristine=False,
            )
        self.assertTrue(
            value["selection_contract"][
                "compiler_has_no_candidate_selection_discretion"
            ]
        )
        self.assertTrue(
            value["compilation_contract"]["exact_disjoint_all220_required"]
        )
        self.assertFalse(value["authorization"]["candidate_selection_or_gate_evaluation"])
        self.assertFalse(value["authorization"]["shared_api_lease_acquire"])
        self.assertFalse(value["authorization"]["benchmark_forward_or_full220_launch"])
        self.assertTrue(
            value["authorization"][
                "future_executor_requires_separate_preregistration_and_activation"
            ]
        )
        self.assertEqual(set(value["control_surface"]["manifest"]), set(CONTROL_FILES))

    def test_parent_drift_fails_closed(self) -> None:
        with mock.patch(
            "scripts.preregister_v24198_candidate_bundle.PARENT_PROTOCOL_SHA256",
            "0" * 64,
        ), self.assertRaisesRegex(RuntimeError, "drifted"):
            build_protocol(ROOT, created_at_unix=1, require_pristine=False)

    def test_publish_is_create_exclusive(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "protocol.json"
            publish_new(path, {"ok": True})
            with self.assertRaises(FileExistsError):
                publish_new(path, {"ok": False})

    def test_resealed_selection_or_launch_authority_is_rejected(self) -> None:
        protected = {
            name: {
                "marker": marker,
                "pid": index + 1,
                "start_ticks": 100 + index,
                "python_isolated_no_bytecode_required": name
                not in {"r1_launcher", "r1_forward"},
                "command_line_emitted": False,
            }
            for index, (name, marker) in enumerate(
                __import__(
                    "scripts.preregister_v24198_candidate_bundle",
                    fromlist=["PROTECTED_PROCESS_MARKERS"],
                ).PROTECTED_PROCESS_MARKERS.items()
            )
        }
        with mock.patch(
            "scripts.preregister_v24198_candidate_bundle.protected_processes",
            return_value=protected,
        ):
            value = build_protocol(ROOT, created_at_unix=1, require_pristine=False)
        value["authorization"]["candidate_selection_or_gate_evaluation"] = True
        value["authorization"]["benchmark_forward_or_full220_launch"] = True
        value["decision_contract_sha256"] = payload_sha256(
            {key: value[key] for key in DECISION_FIELDS}
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "protocol.json"
            path.write_text(__import__("json").dumps(value), encoding="utf-8")
            with mock.patch(
                "scripts.preregister_v24198_candidate_bundle.OUTPUT", path
            ), self.assertRaisesRegex(RuntimeError, "contract"):
                validate_protocol(ROOT, path)


if __name__ == "__main__":
    unittest.main()
