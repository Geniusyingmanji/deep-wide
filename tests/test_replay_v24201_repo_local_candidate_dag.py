from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.replay_v24201_repo_local_candidate_dag import (
    PUBLICATIONS,
    build_replay,
    publish_new,
)


class ReplayV24201RepoLocalCandidateDagTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value, cls.maps = build_replay()

    def test_every_frozen_stage_is_byte_exact(self) -> None:
        self.assertEqual(set(self.value["stages"]), set(PUBLICATIONS))
        self.assertEqual(len(self.value["stages"]), 10)
        self.assertTrue(
            self.value["all_stage_file_maps_byte_exact_to_frozen_publications"]
        )
        self.assertTrue(all(row["byte_exact"] for row in self.value["stages"].values()))

    def test_expected_dag_and_schema_sizes(self) -> None:
        self.assertEqual(
            {name: len(files) for name, files in self.maps.items()},
            {
                "schema68": 44,
                "schema71": 47,
                "schema72": 50,
                "schema73": 47,
                "schema74": 47,
                "schema75": 57,
                "schema69": 47,
                "schema70": 50,
                "schema76": 60,
                "schema77": 63,
            },
        )

    def test_replay_has_no_execution_or_privileged_read_authority(self) -> None:
        for field in (
            "sibling_candidate_tree_read",
            "candidate_tree_materialized",
            "runtime_task_state_prediction_or_result_read",
            "mapping_gold_category_question_type_evaluator_score_read",
            "credential_value_read_persisted_hashed_or_emitted",
            "network_model_search_fetch_evaluator_or_api_called",
            "benchmark_forward_or_full220_launch_allowed",
            "leaderboard_submission_or_sota_claim",
        ):
            self.assertFalse(self.value[field], field)

    def test_receipt_contains_no_credential_or_opaque_task_literal(self) -> None:
        encoded = repr(self.value).encode()
        from scripts.replay_v24201_repo_local_candidate_dag import OPAQUE_ID, SECRET_LITERAL

        self.assertIsNone(SECRET_LITERAL.search(encoded))
        self.assertIsNone(OPAQUE_ID.search(encoded))

    def test_publish_rejects_noncanonical_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeError, "noncanonical"):
                publish_new(Path(directory) / "receipt.json", self.value)


if __name__ == "__main__":
    unittest.main()
