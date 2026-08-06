from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24714_sparse_full220_order_join as contract  # noqa: E402
from scripts import preregister_v24714_sparse_full220 as preregister  # noqa: E402
from scripts import run_v24714_sparse_full220 as runner  # noqa: E402
from test_v24711_sparse_full220_package import vectors  # noqa: E402


class V24714SparseFull220OrderJoinTests(unittest.TestCase):
    def test_actual_files_share_set_but_not_raw_order(self) -> None:
        visible = contract.validate_visible_rows(ROOT)
        control = contract.validate_control_rows(ROOT)
        visible_ids = [row["opaque_id"] for row in visible]
        control_ids = [row["opaque_id"] for row in control]
        self.assertEqual(set(visible_ids), set(control_ids))
        self.assertNotEqual(visible_ids, control_ids)

    def test_actual_ordered_join_matches_control_order(self) -> None:
        visible = contract.ordered_visible_rows(ROOT)
        control = contract.validate_control_rows(ROOT)
        self.assertEqual(
            [row["opaque_id"] for row in visible],
            [row["opaque_id"] for row in control],
        )

    def test_reverse_order_synthetic_join_is_exact(self) -> None:
        visible, control = vectors()
        reverse = list(reversed(visible))
        with (
            patch.object(contract, "validate_visible_rows", return_value=reverse),
            patch.object(contract, "validate_control_rows", return_value=control),
        ):
            ordered = contract.ordered_visible_rows(ROOT)
        self.assertEqual(
            [row["opaque_id"] for row in ordered],
            [row["opaque_id"] for row in control],
        )

    def test_missing_or_duplicate_id_fails_closed(self) -> None:
        visible, control = vectors()
        with (
            patch.object(contract, "validate_visible_rows", return_value=visible[:-1]),
            patch.object(contract, "validate_control_rows", return_value=control),
        ):
            with self.assertRaisesRegex(RuntimeError, "set drifted"):
                contract.ordered_visible_rows(ROOT)
        duplicate = copy.deepcopy(visible)
        duplicate[-1]["opaque_id"] = duplicate[0]["opaque_id"]
        with (
            patch.object(contract, "validate_visible_rows", return_value=duplicate),
            patch.object(contract, "validate_control_rows", return_value=control),
        ):
            with self.assertRaisesRegex(RuntimeError, "set drifted"):
                contract.ordered_visible_rows(ROOT)

    def test_reordered_vector_still_yields_one_treatment(self) -> None:
        visible, control = vectors()
        reverse = list(reversed(visible))
        with (
            patch.object(contract, "validate_visible_rows", return_value=reverse),
            patch.object(contract, "validate_control_rows", return_value=control),
        ):
            ordered = contract.ordered_visible_rows(ROOT)
        from test_v24709_sparse_worldbank_adapter import bundle
        from scripts.run_v24711_sparse_full220 import build_candidate_rows

        rows, summary = build_candidate_rows(ordered, control, bundle())
        self.assertEqual(len(rows), 220)
        self.assertEqual(summary["applied_tasks"], 1)
        self.assertEqual(summary["unchanged_prediction_hash_tasks"], 219)

    def test_protocol_contract_freezes_only_join_change_and_no_launch(self) -> None:
        visible, control = vectors()
        existing = tuple(
            value
            for value in preregister.DEPENDENCIES
            if (ROOT / value).is_file() and not (ROOT / value).is_symlink()
        )
        with (
            patch.object(preregister, "DEPENDENCIES", existing),
            patch.object(preregister, "_parent", return_value={}),
            patch.object(preregister, "_failure_parent", return_value={}),
            patch.object(contract, "ordered_visible_rows", return_value=visible),
            patch.object(contract, "validate_control_rows", return_value=control),
            patch.object(
                contract,
                "sha256",
                side_effect=lambda path: (
                    "a" * 64
                    if Path(path) in {ROOT / contract.PACKAGE_BUILD, ROOT / contract.ORDER_FAILURE}
                    else __import__("hashlib").sha256(Path(path).read_bytes()).hexdigest()
                ),
            ),
        ):
            value = preregister.build_protocol(
                now=0, require_clean=False, require_pristine=False
            )
        self.assertEqual(value["task_contract"]["join_key"], "opaque_id")
        self.assertEqual(
            value["task_contract"]["canonical_output_order"],
            "frozen_control_prediction_order",
        )
        self.assertFalse(value["task_contract"]["raw_file_order_equality_required"])
        self.assertTrue(value["task_contract"]["unique_id_set_equality_required"])
        self.assertFalse(value["authorization"]["activation_or_forward_launch"])

    def test_successor_summary_and_download_receipts_are_newly_sealed(self) -> None:
        summary = {
            "role": "v24714_sparse_full220_run_summary",
            "protocol_id": contract.PROTOCOL_ID,
            "selected": 220,
            "completed": 220,
            "failed": 0,
            "route_eligible_tasks": 1,
            "applied_tasks": 1,
            "unchanged_prediction_hash_tasks": 219,
            "changed_prediction_hash_tasks": 1,
            "adapter_bulk_callback_invocations": 1,
            "model_calls": 0,
            "search_calls": 0,
            "per_country_requests": 0,
            "runtime_input_keys": ["opaque_id", "question"],
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
            "official_evaluator_called": False,
            "resume_retry_skip_or_selective_rerun": False,
        }
        summary["summary_payload_sha256"] = contract.payload_sha256(summary)
        runner.validate_summary(summary)
        tampered = copy.deepcopy(summary)
        tampered["protocol_id"] = "wrong"
        tampered.pop("summary_payload_sha256")
        tampered["summary_payload_sha256"] = contract.payload_sha256(tampered)
        with self.assertRaisesRegex(ValueError, "summary drifted"):
            runner.validate_summary(tampered)


if __name__ == "__main__":
    unittest.main()
