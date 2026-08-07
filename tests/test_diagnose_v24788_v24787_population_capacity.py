from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import diagnose_v24788_v24787_population_capacity as target  # noqa: E402


class V24788V24787PopulationCapacityDiagnosisTests(unittest.TestCase):
    def test_capacity_curve_and_minimum_cap(self) -> None:
        curve = target.capacity_curve({"AA": 20, "BB": 8, "CC": 4})
        self.assertEqual(curve["8"], 20)
        self.assertEqual(curve["20"], 32)
        self.assertEqual(target.minimum_feasible_cap(curve), 20)

    def test_invalid_country_counts_fail_closed(self) -> None:
        for value in ({}, {"AA": 0}, {"": 2}, {"AA": True}):
            with self.assertRaises(ValueError):
                target.capacity_curve(value)

    def test_build_freezes_failed_reads_and_successor_only(self) -> None:
        value = target.build_diagnosis(
            eligible_count=40,
            canonical_unique_count=40,
            country_counts={"AA": 20, "BB": 8, "CC": 4},
            tree_bytes_sha256="a" * 64,
            tree_record_count=3_482,
            now=0,
            git_head="b" * 40,
        )
        failed = value["failed_publication"]
        self.assertEqual(failed["first_attempt_immutable_ror_tree_reads_before_failure"], 1)
        self.assertEqual(failed["first_attempt_immutable_ror_record_reads_before_failure"], 3_482)
        self.assertEqual(failed["cumulative_v24787_plus_v24788_record_reads"], 6_964)
        self.assertTrue(
            value["authorization"]["append_only_fresh_population_successor_design"]
        )
        self.assertFalse(value["authorization"]["activation_or_external_launch"])
        self.assertFalse(value["authorization"]["trusted_child_integration_or_runner_build"])

    def test_resealed_launch_or_read_tamper_is_rejected(self) -> None:
        value = target.build_diagnosis(
            eligible_count=40,
            canonical_unique_count=40,
            country_counts={"AA": 20, "BB": 8, "CC": 4},
            tree_bytes_sha256="a" * 64,
            tree_record_count=3_482,
            now=0,
            git_head="b" * 40,
        )
        for mutate in (
            lambda item: item["failed_publication"].__setitem__(
                "first_attempt_immutable_ror_record_reads_before_failure", 0
            ),
            lambda item: item["authorization"].__setitem__(
                "activation_or_external_launch", True
            ),
        ):
            altered = copy.deepcopy(value)
            mutate(altered)
            altered.pop("diagnosis_payload_sha256")
            altered["diagnosis_payload_sha256"] = target.payload_sha256(altered)
            with self.assertRaises(RuntimeError):
                target.validate_diagnosis(altered)

    def test_failed_surfaces_are_currently_pristine(self) -> None:
        self.assertTrue(
            all(
                not (ROOT / path).exists() and not (ROOT / path).is_symlink()
                for path in target.FAILED_SURFACES
            )
        )

    def test_create_only_publication(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            path = Path(directory) / "diagnosis.json"
            target._publish(path, b"{}\n")
            with self.assertRaises(FileExistsError):
                target._publish(path, b"{}\n")


if __name__ == "__main__":
    unittest.main()
