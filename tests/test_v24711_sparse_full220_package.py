from __future__ import annotations

import copy
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24709_sparse_worldbank_adapter as adapter  # noqa: E402
from deepwide_agent import v24711_sparse_full220_contract as contract  # noqa: E402
from scripts import preregister_v24711_sparse_full220 as preregister  # noqa: E402
from scripts import run_v24711_sparse_full220 as runner  # noqa: E402
from test_v24709_sparse_worldbank_adapter import (  # noqa: E402
    bundle,
    control_prediction,
    question,
)


def vectors():
    visible = []
    control = []
    for index in range(220):
        opaque_id = f"task_{index:024x}"
        treated = index == 103
        prediction = control_prediction() if treated else "```markdown\n| Result |\n| --- |\n| Unknown |\n```"
        visible.append(
            {
                "opaque_id": opaque_id,
                "question": question() if treated else "Return one table.",
            }
        )
        control.append(
            {
                "opaque_id": opaque_id,
                "prediction": prediction,
                "prediction_sha256": hashlib.sha256(prediction.encode()).hexdigest(),
            }
        )
    return visible, control


class V24711SparseFull220PackageTests(unittest.TestCase):
    def test_actual_control_freeze_is_complete_and_label_blind(self) -> None:
        value = contract.validate_control_freeze(ROOT)
        self.assertEqual(value["terminal"], 220)
        self.assertFalse(value["mapping_query_answer_gold_or_evaluator_opened_or_hashed"])

    def test_synthetic_full220_has_one_change_and_219_exact_reuses(self) -> None:
        visible, control = vectors()
        rows, summary = runner.build_candidate_rows(visible, control, bundle())
        self.assertEqual(len(rows), 220)
        self.assertEqual(summary["route_eligible_tasks"], 1)
        self.assertEqual(summary["applied_tasks"], 1)
        self.assertEqual(summary["unchanged_prediction_hash_tasks"], 219)
        self.assertEqual(summary["changed_prediction_hash_tasks"], 1)
        self.assertEqual(summary["official_target_value_count"], 212)
        self.assertEqual(summary["adapter_bulk_callback_invocations"], 1)
        self.assertEqual(summary["failure_reason_counts"], {"not_eligible": 219})

    def test_missing_archive_fails_closed_for_entire_changed_task(self) -> None:
        visible, control = vectors()
        data = bundle()
        data.pop(adapter.TARGETS[-1].url)
        rows, summary = runner.build_candidate_rows(visible, control, data)
        self.assertEqual(summary["applied_tasks"], 0)
        self.assertEqual(summary["unchanged_prediction_hash_tasks"], 220)
        self.assertEqual(summary["changed_prediction_hash_tasks"], 0)
        self.assertEqual(
            summary["failure_reason_counts"],
            {"bulk_bundle_invalid": 1, "not_eligible": 219},
        )
        self.assertTrue(all(row["candidate_prediction_identity"] for row in rows))

    def test_download_receipt_validates_exact_four_url_order(self) -> None:
        downloads = [
            {
                "indicator": spec.indicator,
                "url": spec.url,
                "attempts": 1,
                "success": True,
                "http_status": 200,
                "bytes": 10,
                "sha256": "a" * 64,
                "coarse_failure_type": None,
                "elapsed_seconds": 0.1,
                "response_value_or_credential_persisted": False,
            }
            for spec in adapter.TARGETS
        ]
        value = {
            "artifact_version": 1,
            "role": "v24711_worldbank_bulk_download_receipt",
            "requested": 4,
            "successful": 4,
            "failed": 0,
            "workers": 4,
            "timeout_seconds_each": 30,
            "per_country_requests": 0,
            "model_calls": 0,
            "search_calls": 0,
            "downloads": downloads,
            "wall_seconds": 0.1,
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
            "archive_content_or_credential_persisted": False,
        }
        value["receipt_payload_sha256"] = contract.payload_sha256(value)
        runner.validate_download_receipt(value)
        tampered = copy.deepcopy(value)
        tampered["downloads"].reverse()
        tampered.pop("receipt_payload_sha256")
        tampered["receipt_payload_sha256"] = contract.payload_sha256(tampered)
        with self.assertRaisesRegex(ValueError, "receipt drifted"):
            runner.validate_download_receipt(tampered)

    def test_nonfrozen_download_url_rejected_before_network(self) -> None:
        with patch.object(runner.urllib.request, "urlopen") as opened:
            with self.assertRaisesRegex(ValueError, "outside the frozen vector"):
                runner._download_one("https://example.com/value.zip")
        opened.assert_not_called()

    def test_runtime_row_entropy_or_identity_tamper_fails_closed(self) -> None:
        visible, control = vectors()
        rows, _summary = runner.build_candidate_rows(visible, control, bundle())
        tampered = copy.deepcopy(rows[0])
        tampered["entropy_credit_assigned"] = True
        with self.assertRaisesRegex(ValueError, "runtime row drifted"):
            runner.validate_runtime_row(tampered)
        tampered = copy.deepcopy(rows[0])
        tampered["candidate_prediction_identity"] = False
        with self.assertRaisesRegex(ValueError, "runtime row drifted"):
            runner.validate_runtime_row(tampered)

    def test_protocol_defaults_to_no_launch_and_exact_visible_boundary(self) -> None:
        visible, control = vectors()
        existing = tuple(
            value
            for value in preregister.DEPENDENCIES
            if (ROOT / value).is_file() and not (ROOT / value).is_symlink()
        )
        with (
            patch.object(preregister, "DEPENDENCIES", existing),
            patch.object(preregister, "_validate_build_parent", return_value={}),
            patch.object(preregister, "validate_control_rows", return_value=control),
            patch.object(preregister, "validate_visible_rows", return_value=visible),
            patch.object(
                preregister,
                "sha256",
                side_effect=lambda path: (
                    "a" * 64
                    if Path(path) == ROOT / preregister.PACKAGE_BUILD
                    else contract.sha256(Path(path))
                ),
            ),
        ):
            value = preregister.build_protocol(
                now=0, require_clean=False, require_pristine=False
            )
        self.assertEqual(value["task_contract"]["runtime_boundary"], ["opaque_id", "question"])
        self.assertEqual(value["task_contract"]["selected_count"], 220)
        self.assertEqual(value["execution"]["download_cap"], 4)
        self.assertFalse(value["authorization"]["activation_or_forward_launch"])
        self.assertFalse(value["authorization"]["evaluator"])
        self.assertFalse(value["mechanism"]["entropy_credit_assigned"])

    def test_stage_resealed_launch_authorization_tamper_fails(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            path = Path(directory) / "stage.json"
            value = {
                "artifact_version": 1,
                "role": "v24711_sparse_full220_execution_start",
                "protocol_id": contract.PROTOCOL_ID,
                "protocol_sha256": "0" * 64,
                "authorization": dict(contract.START_AUTHORIZATION),
            }
            value["execution_start_payload_sha256"] = contract.payload_sha256(value)
            path.write_text(__import__("json").dumps(value) + "\n", encoding="utf-8")
            tampered = copy.deepcopy(value)
            tampered["authorization"]["evaluator"] = True
            tampered.pop("execution_start_payload_sha256")
            tampered["execution_start_payload_sha256"] = contract.payload_sha256(tampered)
            path.write_text(__import__("json").dumps(tampered) + "\n", encoding="utf-8")
            with patch.object(contract, "PROTOCOL", Path("outputs/nonexistent_protocol.json")):
                with self.assertRaises((RuntimeError, FileNotFoundError)):
                    contract.validate_stage(
                        ROOT,
                        path.relative_to(ROOT),
                        role="v24711_sparse_full220_execution_start",
                        seal_field="execution_start_payload_sha256",
                        authorization=contract.START_AUTHORIZATION,
                    )


if __name__ == "__main__":
    unittest.main()
