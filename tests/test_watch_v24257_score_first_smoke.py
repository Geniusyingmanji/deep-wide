from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from scripts import watch_v24257_score_first_smoke as target
from scripts.run_v24257_score_first_smoke import payload_sha256, sha256


def _prepare(root: Path) -> dict:
    protocol_path = root / target.OUTPUT
    protocol_path.parent.mkdir(parents=True, exist_ok=True)
    protocol_path.write_text("{}\n", encoding="utf-8")
    activation = {
        "artifact_version": 1,
        "role": "v24257_score_first_smoke_activation",
        "created_at_unix": 1,
        "status": "active",
        "protocol_sha256": sha256(protocol_path),
    }
    activation["activation_payload_sha256"] = payload_sha256(activation)
    activation_path = root / target.ACTIVATION
    activation_path.parent.mkdir(parents=True, exist_ok=True)
    activation_path.write_text(json.dumps(activation), encoding="utf-8")
    return {"protocol_id": "v24257_score_first_smoke16_v1"}


def _legacy(findings: list[str]) -> dict:
    return {"overall_status": "critical" if findings else "healthy", "critical_findings": findings}


class WatchV24257ScoreFirstSmokeTests(unittest.TestCase):
    def _state(
        self,
        root: Path,
        *,
        overlay: dict,
        legacy_findings: list[str],
    ) -> dict:
        protocol = _prepare(root)
        with mock.patch.object(
            target, "validate_protocol", return_value=protocol
        ), mock.patch.object(target, "process_snapshot", return_value=[]), mock.patch.object(
            target, "lease_observation", return_value={"active": False}
        ), mock.patch.object(target, "lease_overlay", return_value=overlay), mock.patch.object(
            target, "build_legacy_report", return_value=_legacy(legacy_findings)
        ):
            return target.build_state(root, now=2, proc_root=root / "proc")

    def test_waiting_state_suppresses_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            value = self._state(
                Path(directory),
                overlay={
                    "identity_valid": False,
                    "legacy_finding_suppression_allowed": False,
                },
                legacy_findings=["unrelated_finding"],
            )
        self.assertEqual(value["status"], "waiting_for_smoke_launch")
        self.assertEqual(
            value["legacy_liveness"]["effective_critical_findings"],
            ["unrelated_finding"],
        )
        self.assertEqual(value["legacy_liveness"]["suppressed_exact_findings"], [])

    def test_running_state_suppresses_only_expected_unknown_owner(self) -> None:
        expected = target.EXPECTED_LEGACY_ACTIVE_FINDING
        with tempfile.TemporaryDirectory() as directory:
            value = self._state(
                Path(directory),
                overlay={
                    "identity_valid": True,
                    "legacy_finding_suppression_allowed": True,
                },
                legacy_findings=[expected, "unrelated_finding"],
            )
        self.assertEqual(value["status"], "running_smoke_under_registered_lease")
        self.assertEqual(
            value["legacy_liveness"]["suppressed_exact_findings"], [expected]
        )
        self.assertEqual(
            value["legacy_liveness"]["effective_critical_findings"],
            ["unrelated_finding"],
        )
        self.assertTrue(value["legacy_liveness"]["all_unrelated_findings_preserved"])

    def test_missing_expected_legacy_finding_becomes_critical(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            value = self._state(
                Path(directory),
                overlay={
                    "identity_valid": True,
                    "legacy_finding_suppression_allowed": True,
                },
                legacy_findings=[],
            )
        self.assertIn(
            "v24257:expected_legacy_unknown_owner_finding_absent",
            value["legacy_liveness"]["effective_critical_findings"],
        )

    def test_atomic_state_publication_replaces_only_the_state_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            relative = Path("outputs/state.json")
            path = root / relative
            with mock.patch.object(target, "ROOT", root), mock.patch.object(
                target, "STATE", relative
            ):
                target.publish_atomic(path, {"cycle": 1})
                target.publish_atomic(path, {"cycle": 2})
            self.assertEqual(json.loads(path.read_text()), {"cycle": 2})
            self.assertEqual(list(path.parent.glob("*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
