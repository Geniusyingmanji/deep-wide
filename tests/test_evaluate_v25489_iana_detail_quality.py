from __future__ import annotations

import copy
import gzip
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import evaluate_v25489_iana_detail_quality as target  # noqa: E402


def html(*, missing: str | None = None, conflict: str | None = None) -> str:
    rows = []
    for index, identity in enumerate(target._mapping()):
        if identity == missing:
            continue
        rows.append(
            f"<tr><td>{identity}</td><td>country-code</td>"
            f"<td>Manager {index}</td></tr>"
        )
        if identity == conflict:
            rows.append(
                f"<tr><td>{identity}</td><td>country-code</td>"
                f"<td>Conflicting Manager</td></tr>"
            )
    return "<html><title>IANA Root Zone Database</title><table>" + "".join(rows) + "</table></html>"


def truth() -> dict[str, dict[str, str]]:
    return target.parse_iana_page(html())


def metric_aggregate(*, exact_delta: int = 1, composite_delta: float = 0.05):
    base = {
        "tasks": 20,
        "valid_tasks": 20,
        "invalid_tasks": 0,
        "fallback_tasks": 0,
        "exact_table_successes": 5,
        "entity_coverage": 0.7,
        "row_exact": 0.25,
        "cell_accuracy": 0.5,
        "column_accuracy": 0.6,
        "quality_composite": 0.5125,
    }
    candidate = copy.deepcopy(base)
    candidate["exact_table_successes"] += exact_delta
    candidate["quality_composite"] += composite_delta
    delta = target._delta(candidate, base)
    return {
        "evaluation_count": 40,
        "truth_record_count": 20,
        "truth_complete_tasks": 20,
        "arms": {target.BASE_ARM: base, target.CANDIDATE_ARM: candidate},
        "candidate_minus_base": delta,
        "candidate_vs_base_exact_disposition": {
            "candidate_win": max(0, exact_delta),
            "tie": 20 - max(0, exact_delta),
            "candidate_loss": 0,
        },
        "candidate_vs_base_composite_disposition": {
            "candidate_win": int(composite_delta > 0),
            "tie": 20 - int(composite_delta != 0),
            "candidate_loss": int(composite_delta < 0),
        },
        "shared_parent_treatment_comparison": True,
    }


class V25489IanaDetailQualityTests(unittest.TestCase):
    def test_mapping_and_parser_select_exact_frozen_cohort(self) -> None:
        mapping = target._mapping()
        records = target.parse_iana_page(html())
        self.assertEqual(len(mapping), 20)
        self.assertEqual(len(set(mapping)), 20)
        self.assertEqual(tuple(records), mapping)
        self.assertEqual(records[".gm"]["TLD Manager"], "Manager 0")
        self.assertEqual(records[".ly"]["TLD Manager"], "Manager 19")

    def test_parser_rejects_missing_conflicting_and_non_table_truth(self) -> None:
        for raw in (
            html(missing=".gm"),
            html(conflict=".ge"),
            "<html><p>.gm country-code Manager</p></html>",
        ):
            with self.subTest(raw=raw[:40]), self.assertRaises(ValueError):
                target.parse_iana_page(raw)

    def test_prediction_metrics_require_one_exact_three_column_row(self) -> None:
        records = truth()
        exact = target.evaluate_prediction(
            "| Domain | Type | TLD Manager |\n|---|---|---|\n"
            "| .gm | country-code | Manager 0 |",
            ".gm",
            records,
        )
        wrong = target.evaluate_prediction(
            "| Domain | Type | TLD Manager |\n|---|---|---|\n"
            "| .gm | country-code | Wrong |",
            ".gm",
            records,
        )
        invalid = target.evaluate_prediction("not a table", ".gm", records)
        self.assertEqual(exact["exact_table_success"], 1)
        self.assertEqual(wrong["exact_table_success"], 0)
        self.assertGreater(exact["quality_composite"], wrong["quality_composite"])
        self.assertFalse(invalid["valid"])
        self.assertEqual(invalid["quality_composite"], 0.0)

    def test_quality_gate_requires_exact_gain_and_all_nonregressions(self) -> None:
        passing = metric_aggregate()
        self.assertTrue(target.quality_decision(passing)["quality_gate_passed"])
        for kind in ("exact", "soft", "truth", "invalid"):
            changed = copy.deepcopy(passing)
            if kind == "exact":
                changed["candidate_minus_base"]["exact_table_successes"] = 0
            elif kind == "soft":
                changed["candidate_minus_base"]["cell_accuracy"] = -0.01
            elif kind == "truth":
                changed["truth_complete_tasks"] = 19
            else:
                changed["candidate_minus_base"]["invalid_tasks"] = 1
            with self.subTest(kind=kind):
                self.assertFalse(
                    target.quality_decision(changed)["quality_gate_passed"]
                )

    def test_frozen_rows_evaluate_all_forty_predictions_once(self) -> None:
        rows = target._read_rows()
        metrics = target.evaluate_rows(rows, truth())
        self.assertEqual(metrics["evaluation_count"], 40)
        self.assertEqual(metrics["truth_complete_tasks"], 20)
        self.assertEqual(metrics["arms"][target.BASE_ARM]["tasks"], 20)
        self.assertEqual(metrics["arms"][target.CANDIDATE_ARM]["tasks"], 20)
        self.assertTrue(metrics["shared_parent_treatment_comparison"])

    def test_truth_snapshot_replays_and_tamper_fails(self) -> None:
        raw = html().encode()
        compressed, value = target._truth_artifact(
            raw, 200, None, "utf-8", truth(), now=1
        )
        self.assertEqual(target.validate_truth(value, compressed), value)
        with self.assertRaises(ValueError):
            target.validate_truth(value, gzip.compress(raw + b"x", mtime=0))
        changed = copy.deepcopy(value)
        changed["records"][".gm"]["TLD Manager"] = "tampered"
        changed.pop("truth_payload_sha256")
        changed = target.contract.seal(changed, "truth_payload_sha256")
        with self.assertRaises(ValueError):
            target.validate_truth(changed, compressed)

    def test_result_is_sealed_zero_credit_and_never_directly_authorizes_220(self) -> None:
        raw = html().encode()
        _compressed, truth_value = target._truth_artifact(
            raw, 200, None, "utf-8", truth(), now=1
        )
        protocol = {
            "forward_audit_sha256": target.FORWARD_AUDIT_SHA256,
            "forward_result_sha256": target.FORWARD_RESULT_SHA256,
            "task_rows_sha256": target.TASK_ROWS_SHA256,
            "prediction_freeze_sha256": target.PREDICTION_FREEZE_SHA256,
        }
        value = target._result_artifact(
            protocol,
            truth_value,
            metric_aggregate(),
            now=1,
            protocol_sha256="a" * 64,
        )
        self.assertEqual(
            target.validate_result(value, expected_protocol_sha256="a" * 64), value
        )
        self.assertEqual(value["positive_signed_credit_count"], 0)
        self.assertFalse(value["authorization"]["deepwidebench_forward_or_evaluator"])
        changed = copy.deepcopy(value)
        changed["positive_signed_credit_count"] = 1
        changed.pop("result_payload_sha256")
        changed = target.contract.seal(changed, "result_payload_sha256")
        with self.assertRaises(ValueError):
            target.validate_result(changed, expected_protocol_sha256="a" * 64)

    def test_contract_and_build_audit_authorize_protocol_only(self) -> None:
        self.assertTrue(target._source_network_contract(ROOT / target.SOURCE))
        self.assertEqual(target.truth_fetch_contract()["attempt_count"], 1)
        self.assertFalse(target.truth_fetch_contract()["allow_redirects"])
        test = {
            "pattern": target.TEST.name,
            "expected": 8,
            "observed": 8,
            "returncode": 0,
            "passed": True,
            "output_sha256": "a" * 64,
        }
        with (
            mock.patch.object(target, "_clean_pushed", return_value=("a", "a")),
            mock.patch.object(target, "_test", return_value=test),
            mock.patch.object(target, "_future_pristine", return_value=True),
            mock.patch.object(target.forward_control, "_lease_inactive", return_value=True),
            mock.patch.object(target.forward_control, "_active_conflicts", return_value=[]),
        ):
            value = target.build_audit(now=1, require_clean=False)
        self.assertEqual(target.validate_build_audit(value), value)
        self.assertTrue(
            value["authorization"]["postfreeze_quality_protocol_generation"]
        )
        self.assertFalse(
            value["authorization"]["one_truth_fetch_or_quality_evaluation"]
        )


if __name__ == "__main__":
    unittest.main()
