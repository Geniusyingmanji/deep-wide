from __future__ import annotations

import ast
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24308_child_exit_observability import parent_receipt  # noqa: E402
from deepwide_agent.v24315_forward_contract import source_selected_ids  # noqa: E402
from deepwide_agent.v24325_shared_prefix_revision_runtime import (  # noqa: E402
    run_v24325_task,
)
from deepwide_agent.v24330_forward_contract import (  # noqa: E402
    ARMS,
    PREDICTION_FREEZE,
    RUNTIME_PREDICTIONS,
    RUN_SUMMARY,
    SELECTED_COUNT,
    payload_sha256,
    selected_tasks,
    sha256,
)
from scripts import run_v24330_shared_prefix_exact220 as runner  # noqa: E402
from test_v24325_shared_prefix_revision_runtime import (  # noqa: E402
    BASELINE_UNKNOWN,
    Clock,
    FakeModel,
    FakeSearch,
    PLAN,
    candidate,
    proposal,
)


def pair_result(*, changed: bool = True) -> dict:
    revision = (
        proposal(candidate("2025"), ["R0001", "R0002"])
        if changed
        else json.dumps({"candidate_table": BASELINE_UNKNOWN, "cell_evidence": []})
    )
    return run_v24325_task(
        {
            "opaque_id": "task_0123456789abcdef01234567",
            "question": (
                "Use web evidence to complete the table. The column names are: "
                "Name, Year. Return one Markdown table only."
            ),
        },
        model=FakeModel([PLAN, BASELINE_UNKNOWN, revision]),
        search=FakeSearch(),
        monotonic=Clock(),
    )


def success_parent() -> dict:
    return parent_receipt(
        return_code=0,
        timed_out=False,
        elapsed_seconds=12.0,
        subprocess_exception=False,
        child_terminal_receipt_present=True,
        child_terminal_receipt_valid=True,
        result_envelope_present=True,
        result_envelope_valid=True,
        model_receipt_present=True,
        model_receipt_valid=True,
        transport_receipt_present=True,
        transport_receipt_valid=True,
    )


def model_receipt(result: dict) -> dict:
    receipt = result["shared_prefix_revision_receipt"]
    return {
        "acquisitions": int(receipt["provider_model_requests"]),
        "slot_timeouts": int(receipt["pre_provider_model_rejections"]),
        "provider_deadline_failures": 0,
        "total_wait_seconds": 0.25,
        "max_wait_seconds": 0.1,
    }


def transport(result: dict) -> dict:
    fetches = int(result["cost"]["search"]["fetch_calls"])
    return {
        "hosted_search_attempts": 1,
        "hosted_search_deadline_failures": 0,
        "hard_fetch_helper_calls": fetches,
        "hard_fetch_deadline_failures": 0,
        "fetch_deadline_rejections": 0,
        "fetch_helper_failures": 0,
        "deadline_exhausted": False,
    }


class V24330SharedPrefixExact220Tests(unittest.TestCase):
    def test_exact220_visible_boundary_and_frozen_order(self) -> None:
        ids = source_selected_ids(ROOT)
        self.assertEqual(len(ids), SELECTED_COUNT)
        contract = {
            "task_contract": {
                "selected_opaque_ids": ids,
                "selected_opaque_ids_sha256": payload_sha256(ids),
                "manifest_sha256": sha256(
                    ROOT / "outputs/runtime_manifest_v1_repro/manifest.jsonl"
                ),
            }
        }
        tasks = selected_tasks(ROOT, contract)
        self.assertEqual(len(tasks), SELECTED_COUNT)
        self.assertEqual([task["opaque_id"] for task in tasks], ids)
        self.assertTrue(
            all(set(task) == {"opaque_id", "question"} for task in tasks)
        )

    def test_one_pair_result_yields_two_aligned_predictions(self) -> None:
        result = pair_result(changed=True)
        task = {
            "opaque_id": result["opaque_id"],
            "question": "The column names are: Name, Year. Return one table.",
        }
        rows = {
            arm: runner._runtime_row(
                task, arm=arm, result=result, parent_taxonomy="success"
            )
            for arm in ARMS
        }
        self.assertEqual(rows["baseline"]["opaque_id"], rows["candidate"]["opaque_id"])
        self.assertEqual(rows["baseline"]["status"], "completed")
        self.assertEqual(rows["candidate"]["status"], "completed")
        self.assertNotEqual(
            rows["baseline"]["prediction_sha256"],
            rows["candidate"]["prediction_sha256"],
        )
        self.assertFalse(rows["candidate"]["candidate_identity_handoff"])
        self.assertGreater(rows["candidate"]["admitted_cell_changes"], 0)

    def test_identity_handoff_is_byte_identical(self) -> None:
        result = pair_result(changed=False)
        task = {
            "opaque_id": result["opaque_id"],
            "question": "The column names are: Name, Year. Return one table.",
        }
        baseline = runner._runtime_row(
            task, arm="baseline", result=result, parent_taxonomy="success"
        )
        candidate_row = runner._runtime_row(
            task, arm="candidate", result=result, parent_taxonomy="success"
        )
        self.assertTrue(baseline["candidate_identity_handoff"])
        self.assertEqual(baseline["prediction"], candidate_row["prediction"])
        self.assertEqual(
            baseline["prediction_sha256"], candidate_row["prediction_sha256"]
        )

    def test_parent_failure_makes_both_arms_failed_without_retry(self) -> None:
        task = {
            "opaque_id": "task_0123456789abcdef01234567",
            "question": "The column names are: Name, Year. Return one table.",
        }
        parent = parent_receipt(
            return_code=-15,
            timed_out=True,
            elapsed_seconds=200.0,
            subprocess_exception=False,
            child_terminal_receipt_present=False,
            child_terminal_receipt_valid=False,
            result_envelope_present=False,
            result_envelope_valid=False,
            model_receipt_present=True,
            model_receipt_valid=True,
            transport_receipt_present=False,
            transport_receipt_valid=False,
        )
        outcome = runner._failure_outcome(
            1, task, taxonomy="hard_deadline_timeout", parent=parent
        )
        for arm in ARMS:
            self.assertEqual(outcome.rows[arm]["status"], "failed")
            self.assertEqual(outcome.rows[arm]["error"], "hard_deadline_timeout")
            self.assertEqual(outcome.rows[arm]["cost"]["system_total_tokens"], 0)
            self.assertEqual(outcome.rows[arm]["elapsed_seconds"], 200.0)
        self.assertEqual(
            outcome.rows["baseline"]["prediction"],
            outcome.rows["candidate"]["prediction"],
        )

    def test_pair_summary_closes_220_and_model_conservation(self) -> None:
        result = pair_result(changed=True)
        parent = success_parent()
        task = {
            "opaque_id": result["opaque_id"],
            "question": "The column names are: Name, Year. Return one table.",
        }
        rows = {
            arm: runner._runtime_row(
                task, arm=arm, result=result, parent_taxonomy="success"
            )
            for arm in ARMS
        }
        prototype = runner.PairOutcome(
            position=1,
            task=task,
            rows=rows,
            parent_exit=parent,
            result=result,
            model_receipt=model_receipt(result),
            transport_health=transport(result),
        )
        outcomes = [
            runner.dataclasses.replace(prototype, position=index)
            for index in range(1, SELECTED_COUNT + 1)
        ]
        summary = runner._pair_summary(outcomes, 900.0)
        self.assertEqual(summary["terminal_pair_tasks"], SELECTED_COUNT)
        self.assertEqual(summary["prediction_rows_per_arm"], {arm: 220 for arm in ARMS})
        self.assertTrue(summary["model_conservation_on_complete_tasks"])
        self.assertEqual(summary["repeated_upstream_effects"], 0)

    def test_prediction_freeze_requires_exact_order_and_220_rows(self) -> None:
        ids = source_selected_ids(ROOT)
        contract = {
            "task_contract": {
                "selected_opaque_ids": ids,
                "selected_opaque_ids_sha256": payload_sha256(ids),
            }
        }
        result = pair_result(changed=False)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for path in (*RUNTIME_PREDICTIONS.values(), *RUN_SUMMARY.values(), *PREDICTION_FREEZE.values()):
                (root / path).parent.mkdir(parents=True, exist_ok=True)
            rows_by_arm = {}
            for arm in ARMS:
                rows = []
                for opaque_id in ids:
                    visible = {"opaque_id": opaque_id, "question": "The column names are: Name, Year."}
                    copied = dict(result)
                    copied["opaque_id"] = opaque_id
                    unsigned = dict(copied)
                    unsigned.pop("result_sha256")
                    copied["result_sha256"] = payload_sha256(unsigned)
                    rows.append(
                        runner._runtime_row(
                            visible,
                            arm=arm,
                            result=copied,
                            parent_taxonomy="success",
                        )
                    )
                rows_by_arm[arm] = rows
                (root / RUNTIME_PREDICTIONS[arm]).write_text(
                    "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
                    encoding="utf-8",
                )
                summary = runner._arm_summary(arm, rows, [], 10.0)
                (root / RUN_SUMMARY[arm]).write_text(
                    json.dumps(summary, sort_keys=True) + "\n", encoding="utf-8"
                )
                freeze = {
                    "artifact_version": 1,
                    "role": "v24330_shared_prefix_exact220_prediction_freeze",
                    "protocol_id": runner.PROTOCOL_ID,
                    "arm": arm,
                    "selected": SELECTED_COUNT,
                    "terminal": SELECTED_COUNT,
                    "selected_opaque_ids_sha256": payload_sha256(ids),
                    "runtime_predictions_sha256": sha256(root / RUNTIME_PREDICTIONS[arm]),
                    "run_summary_sha256": sha256(root / RUN_SUMMARY[arm]),
                    "prediction_hashes_sha256": payload_sha256(
                        [row["prediction_sha256"] for row in rows]
                    ),
                    "both_arms_terminal_before_mapping_gold_or_evaluator_open": True,
                    "mapping_gold_or_evaluator_opened_or_hashed": False,
                    "label_blind": True,
                }
                freeze["freeze_payload_sha256"] = payload_sha256(freeze)
                runner.validate_prediction_freeze(root, contract, arm, freeze)
            altered = dict(rows_by_arm["candidate"][0])
            altered["opaque_id"] = ids[1]
            rows_by_arm["candidate"][0] = altered
            (root / RUNTIME_PREDICTIONS["candidate"]).write_text(
                "".join(
                    json.dumps(row, sort_keys=True) + "\n"
                    for row in rows_by_arm["candidate"]
                ),
                encoding="utf-8",
            )
            with self.assertRaises(RuntimeError):
                runner.validate_prediction_freeze(root, contract, "candidate", freeze)

    def test_forward_runtime_imports_no_evaluator_or_mapping_module(self) -> None:
        paths = (
            ROOT / "src/deepwide_agent/v24330_forward_contract.py",
            ROOT / "scripts/run_v24330_shared_prefix_exact220_task.py",
            ROOT / "scripts/run_v24330_shared_prefix_exact220.py",
        )
        imported: list[str] = []
        for path in paths:
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom):
                    imported.append(node.module or "")
        self.assertFalse(
            any(
                token in name.casefold()
                for name in imported
                for token in ("finalize", "evaluator", "mapping", "official_eval")
            ),
            imported,
        )


if __name__ == "__main__":
    unittest.main()
