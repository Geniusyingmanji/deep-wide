from __future__ import annotations

import copy
import gzip
import hashlib
import json
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import evaluate_v25551_visible_constraint_quality as target  # noqa: E402


def pypi_payload(
    identity: str,
    *,
    releases: dict[str, list[dict[str, object]]] | None = None,
) -> bytes:
    values = releases or {
        "1.9": [{"upload_time_iso_8601": "2026-01-03T01:00:00Z"}],
        "1.10rc1": [{"upload_time_iso_8601": "2026-02-01T01:00:00Z"}],
        "1.10": [
            {"upload_time_iso_8601": "2026-03-02T10:00:00Z"},
            {"upload_time_iso_8601": "2026-03-01T23:00:00+00:00"},
        ],
    }
    return json.dumps(
        {"info": {"name": identity}, "releases": values}, sort_keys=True
    ).encode()


def hf_payload(
    identity: str, *, total: int = 1_234_500_000, breakdown: int | None = None
) -> bytes:
    parameter = total if breakdown is None else breakdown
    return json.dumps(
        {
            "id": identity,
            "safetensors": {"total": total, "parameters": {"BF16": parameter}},
        },
        sort_keys=True,
    ).encode()


def complete_truth() -> dict[str, dict[str, object]]:
    output: dict[str, dict[str, object]] = {}
    for task_index, pair in enumerate(target.contract.population.pair_vector()):
        for row_index, identity in enumerate(pair):
            if task_index < target.contract.population.DATE_TASK_COUNT:
                day = 20 - row_index
                iso = f"2026-01-{day:02d}"
                output[identity] = {
                    "source": "pypi",
                    "identity": identity,
                    "latest_stable_version": "1.0",
                    "release_file_count": 1,
                    "release_date_iso": iso,
                    "canonical_value": target._date_canonical(iso),
                    "sort_key": iso,
                }
            else:
                total = (2 - row_index) * 1_000_000_000 + task_index
                output[identity] = {
                    "source": "huggingface",
                    "identity": identity,
                    "safetensors_total": total,
                    "parameter_breakdown_sum_verified": True,
                    "canonical_value": target._canonical_million(total),
                    "sort_key": total,
                }
    return output


def metric_aggregate(*, exact_delta: int = 1, composite_delta: float = 0.0):
    control = {
        "tasks": 20,
        "valid_tasks": 20,
        "invalid_tasks": 0,
        "fallback_tasks": 0,
        "exact_table_successes": 5,
        "entity_coverage": 0.8,
        "row_f1": 0.6,
        "item_f1": 0.7,
        "column_f1": 1.0,
        "quality_composite": 0.775,
    }
    candidate = copy.deepcopy(control)
    candidate["exact_table_successes"] += exact_delta
    candidate["quality_composite"] += composite_delta
    return {
        "evaluation_count": 40,
        "truth_identity_count": 40,
        "truth_complete_tasks": 20,
        "arms": {target.BASE_ARM: control, target.CANDIDATE_ARM: candidate},
        "candidate_minus_control": target._delta(candidate, control),
        "candidate_vs_control_exact_disposition": {
            "candidate_win": max(0, exact_delta),
            "tie": 20 - abs(exact_delta),
            "candidate_loss": max(0, -exact_delta),
        },
        "candidate_vs_control_composite_disposition": {
            "candidate_win": int(composite_delta > 0),
            "tie": 20 - int(composite_delta != 0),
            "candidate_loss": int(composite_delta < 0),
        },
        "family_metrics": {},
        "shared_parent_treatment_comparison": True,
    }


class V25551VisibleConstraintQualityTests(unittest.TestCase):
    def test_endpoint_vector_is_fixed_unique_forty_with_two_sources(self) -> None:
        values = target.endpoint_vector()
        self.assertEqual(len(values), 40)
        self.assertEqual(len({row["url"] for row in values}), 40)
        self.assertEqual([row["index"] for row in values], list(range(40)))
        self.assertEqual(sum(row["source"] == "pypi" for row in values), 20)
        self.assertEqual(sum(row["source"] == "huggingface" for row in values), 20)

    def test_pypi_parser_selects_latest_stable_and_earliest_file_date(self) -> None:
        record = target.parse_pypi_response(pypi_payload("demo_pkg"), "demo-pkg")
        self.assertEqual(record["latest_stable_version"], "1.10")
        self.assertEqual(record["release_file_count"], 2)
        self.assertEqual(record["release_date_iso"], "2026-03-01")
        self.assertEqual(record["canonical_value"], "2026年3月1日")
        shifted = target.parse_pypi_response(
            pypi_payload(
                "demo",
                releases={
                    "1.0": [
                        {"upload_time_iso_8601": "2026-03-01T00:30:00+02:00"}
                    ]
                },
            ),
            "demo",
        )
        self.assertEqual(shifted["release_date_iso"], "2026-02-28")

    def test_pypi_parser_rejects_identity_timezone_and_release_conflicts(self) -> None:
        cases = (
            (pypi_payload("wrong"), "demo"),
            (
                pypi_payload(
                    "demo",
                    releases={"1.0": [{"upload_time": "2026-01-01T00:00:00"}]},
                ),
                "demo",
            ),
            (
                pypi_payload(
                    "demo",
                    releases={
                        "1.0": [{"upload_time_iso_8601": "2026-01-01T00:00:00Z"}],
                        "1.0.0": [{"upload_time_iso_8601": "2026-01-02T00:00:00Z"}],
                    },
                ),
                "demo",
            ),
        )
        for raw, identity in cases:
            with self.subTest(identity=identity), self.assertRaises(ValueError):
                target.parse_pypi_response(raw, identity)

    def test_huggingface_parser_uses_safetensors_total_and_rejects_conflict(self) -> None:
        identity = "owner/model"
        record = target.parse_huggingface_response(hf_payload(identity), identity)
        self.assertEqual(record["safetensors_total"], 1_234_500_000)
        self.assertEqual(record["canonical_value"], "1234.5 million")
        self.assertTrue(record["parameter_breakdown_sum_verified"])
        for raw in (hf_payload("wrong/model"), hf_payload(identity, breakdown=1)):
            with self.assertRaises(ValueError):
                target.parse_huggingface_response(raw, identity)

    def test_date_scoring_requires_canonical_format_and_descending_order_for_exact(self) -> None:
        truth = complete_truth()
        first, second = target.contract.population.PYPI_PAIRS[0]
        canonical = (
            "| Package | Latest Stable Release Date |\n|---|---|\n"
            f"| {first} | 2026年1月20日 |\n| {second} | 2026年1月19日 |"
        )
        equivalent_noncanonical = canonical.replace("2026年1月20日", "2026-01-20")
        reversed_rows = "\n".join(canonical.splitlines()[:2] + canonical.splitlines()[2:][::-1])
        exact = target.evaluate_prediction(canonical, 0, truth)
        formatted = target.evaluate_prediction(equivalent_noncanonical, 0, truth)
        reversed_value = target.evaluate_prediction(reversed_rows, 0, truth)
        self.assertEqual(exact["exact_table_success"], 1)
        self.assertEqual(formatted["exact_table_success"], 0)
        self.assertEqual(formatted["row_f1"], 1.0)
        self.assertEqual(reversed_value["exact_table_success"], 0)
        self.assertEqual(reversed_value["quality_composite"], 1.0)

    def test_scale_scoring_treats_commas_as_semantically_equivalent_not_fake_gain(self) -> None:
        truth = complete_truth()
        index = 10
        first, second = target.contract.population.HUGGINGFACE_PAIRS[0]
        first_value = truth[first]["canonical_value"]
        second_value = truth[second]["canonical_value"]
        canonical = (
            "| Model | Parameter Count |\n|---|---|\n"
            f"| {first} | {first_value} |\n| {second} | {second_value} |"
        )
        comma = canonical.replace("2000.00001", "2,000.00001")
        metric = target.evaluate_prediction(comma, index, truth)
        self.assertEqual(metric["row_f1"], 1.0)
        self.assertEqual(metric["exact_table_success"], 1)

    def test_quality_gate_requires_exact_gain_all_nonregressions_and_complete_truth(self) -> None:
        passing = metric_aggregate()
        self.assertTrue(target.quality_decision(passing)["quality_gate_passed"])
        for kind in ("exact", "soft", "truth", "invalid"):
            changed = copy.deepcopy(passing)
            if kind == "exact":
                changed["candidate_minus_control"]["exact_table_successes"] = 0
            elif kind == "soft":
                changed["candidate_minus_control"]["row_f1"] = -0.01
            elif kind == "truth":
                changed["truth_complete_tasks"] = 19
            else:
                changed["candidate_minus_control"]["invalid_tasks"] = 1
            with self.subTest(kind=kind):
                self.assertFalse(target.quality_decision(changed)["quality_gate_passed"])

    def test_frozen_rows_evaluate_all_forty_once_without_selecting_changed_tasks(self) -> None:
        metrics = target.evaluate_rows(target._read_rows(), complete_truth())
        self.assertEqual(metrics["evaluation_count"], 40)
        self.assertEqual(metrics["truth_identity_count"], 40)
        self.assertEqual(metrics["truth_complete_tasks"], 20)
        self.assertEqual(metrics["arms"][target.BASE_ARM]["tasks"], 20)
        self.assertEqual(metrics["arms"][target.CANDIDATE_ARM]["tasks"], 20)

    def test_truth_snapshot_replays_all_raw_hashes_and_tamper_fails(self) -> None:
        fetched = []
        for spec in target.endpoint_vector():
            raw = (
                pypi_payload(spec["identity"])
                if spec["source"] == "pypi"
                else hf_payload(spec["identity"])
            )
            fetched.append(
                {
                    **spec,
                    "attempt_count": 1,
                    "http_status": 200,
                    "transport_failure_type": None,
                    "raw": raw,
                }
            )
        compressed, value = target._truth_artifact(fetched, now=1)
        self.assertEqual(target.validate_truth(value, compressed), value)
        changed = bytearray(compressed)
        changed[-1] ^= 1
        with self.assertRaises(ValueError):
            target.validate_truth(value, bytes(changed))
        resealed = copy.deepcopy(value)
        resealed["records"].pop(next(iter(resealed["records"])))
        resealed.pop("truth_payload_sha256")
        resealed = target.contract.seal(resealed, "truth_payload_sha256")
        with self.assertRaises(ValueError):
            target.validate_truth(resealed, compressed)

    def test_result_zero_credit_and_build_audit_only_authorizes_protocol(self) -> None:
        truth = {
            "compressed_snapshot_sha256": "b" * 64,
            "truth_payload_sha256": "c" * 64,
            "attempt_count": 40,
        }
        protocol = {
            "forward_audit_sha256": target.FORWARD_AUDIT_SHA256,
            "forward_result_sha256": target.FORWARD_RESULT_SHA256,
            "task_rows_sha256": target.TASK_ROWS_SHA256,
            "prediction_freeze_sha256": target.PREDICTION_FREEZE_SHA256,
        }
        value = target._result_artifact(
            protocol, truth, metric_aggregate(), now=1, protocol_sha256="a" * 64
        )
        self.assertEqual(
            target.validate_result(value, expected_protocol_sha256="a" * 64), value
        )
        self.assertEqual(value["positive_signed_credit_count"], 0)
        self.assertFalse(value["authorization"]["deepwidebench_forward_or_evaluator"])
        self.assertTrue(target._source_network_contract(ROOT / target.SOURCE))
        test = {
            "pattern": target.TEST.name,
            "expected": 10,
            "observed": 10,
            "returncode": 0,
            "passed": True,
            "output_sha256": hashlib.sha256(b"ok").hexdigest(),
        }
        with (
            mock.patch.object(target, "_test", return_value=test),
            mock.patch.object(target, "_future_pristine", return_value=True),
            mock.patch.object(target, "_active_conflicts", return_value=[]),
            mock.patch.object(target.forward_control, "_lease_inactive", return_value=True),
        ):
            build = target.build_audit(now=1, require_clean=False)
        self.assertEqual(target.validate_build_audit(build), build)
        self.assertTrue(
            build["authorization"]["postfreeze_quality_protocol_generation"]
        )
        self.assertFalse(build["authorization"]["one_truth_fetch_or_quality_evaluation"])


if __name__ == "__main__":
    unittest.main()
