from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import diagnose_v24785_v24784_projection_closure as diagnosis  # noqa: E402


class V24785ProjectionClosureDiagnosisTests(unittest.TestCase):
    def test_parent_is_tracked_counts_only_no_go(self) -> None:
        value = diagnosis._parent()
        self.assertTrue(value["forward_health_go"])
        self.assertFalse(value["mechanism_go"])
        self.assertEqual(
            value["replayed_summary_counts"][
                "projection_unknown_target_value_group_count"
            ],
            1,
        )

    def test_intersection_bounds_do_not_invent_joint_cooccurrence(self) -> None:
        self.assertEqual(diagnosis._intersection_bounds(1, 2, 16), (0, 1))
        self.assertEqual(diagnosis._intersection_bounds(2, 3, 3), (2, 2))
        self.assertEqual(diagnosis._intersection_bounds(0, 2, 16), (0, 0))
        with self.assertRaises(ValueError):
            diagnosis._intersection_bounds(17, 2, 16)

    def test_synthetic_founded_and_country_close_end_to_end(self) -> None:
        value = diagnosis.synthetic_closure()
        self.assertTrue(value["all_cases_close_two_source_unknown_proposal"])
        self.assertEqual(
            {row["column_kind"] for row in value["cases"]},
            {"founded", "country"},
        )
        for row in value["cases"]:
            self.assertEqual(row["semantic_projection_count"], 2)
            self.assertEqual(row["projection_backed_eligible_support_set_count"], 1)
            self.assertEqual(
                row["unconflicted_projection_backed_unknown_proposal_count"], 1
            )

    def test_source_key_implementations_match_synthetic_cases(self) -> None:
        value = diagnosis.source_key_equivalence()
        self.assertTrue(value["common_suffix_sets_equal"])
        self.assertTrue(value["all_synthetic_source_keys_equal"])
        self.assertEqual(value["synthetic_host_case_count"], 6)

    def test_diagnosis_freezes_uncertainty_and_no_launch(self) -> None:
        value = diagnosis.build_diagnosis(now=0)
        diagnosis.validate_diagnosis(value)
        self.assertEqual(
            value["identifiability"][
                "unknown_and_multisource_group_intersection_lower_bound"
            ],
            0,
        )
        self.assertEqual(
            value["identifiability"][
                "unknown_and_multisource_group_intersection_upper_bound"
            ],
            1,
        )
        self.assertFalse(value["authorization"]["activation_or_external_launch"])
        self.assertFalse(value["authorization"]["paired_dev64"])
        self.assertFalse(value["authorization"]["exact220"])

    def test_resealed_false_certainty_or_launch_tamper_is_rejected(self) -> None:
        value = diagnosis.build_diagnosis(now=0)
        for mutate in (
            lambda item: item["identifiability"].__setitem__(
                "unknown_group_is_proven_single_source", True
            ),
            lambda item: item["authorization"].__setitem__(
                "activation_or_external_launch", True
            ),
        ):
            altered = copy.deepcopy(value)
            mutate(altered)
            altered.pop("diagnosis_payload_sha256")
            altered["diagnosis_payload_sha256"] = diagnosis.contract.payload_sha256(
                altered
            )
            with self.assertRaises(RuntimeError):
                diagnosis.validate_diagnosis(altered)

    def test_outputs_and_private_surfaces_are_not_sources(self) -> None:
        self.assertFalse(any(path.parts[:1] == ("outputs",) for path in diagnosis.SOURCES))
        self.assertFalse(any(path.parts[:1] == ("evaluation",) for path in diagnosis.SOURCES))
        self.assertFalse(any("private" in path.name for path in diagnosis.SOURCES))
        with patch.object(diagnosis, "_read", wraps=diagnosis._read) as read:
            diagnosis.build_diagnosis(now=0)
        self.assertEqual([call.args[0] for call in read.call_args_list], [diagnosis.PARENT])

    def test_create_only_publish_rejects_overwrite(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            path = Path(directory) / "diagnosis.json"
            diagnosis.publish_new(path, {})
            with self.assertRaises(FileExistsError):
                diagnosis.publish_new(path, {})


if __name__ == "__main__":
    unittest.main()
