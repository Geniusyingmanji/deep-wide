from __future__ import annotations

import ast
import copy
import gzip
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import (  # noqa: E402
    v25206_cran_dcf_quality_contract as contract,
)
from scripts import evaluate_v25206_cran_dcf_quality as target  # noqa: E402


class _Response:
    def __init__(self, endpoint: str, raw: bytes, *, status: int = 200) -> None:
        self.url = endpoint
        self.status_code = status
        self._raw = raw

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def raise_for_status(self) -> None:
        if self.status_code != 200:
            raise target.requests.HTTPError(str(self.status_code))

    def iter_content(self, chunk_size: int) -> list[bytes]:
        self.chunk_size = chunk_size
        return [self._raw]


class V25206PostEffectQualityEvaluatorTests(unittest.TestCase):
    @staticmethod
    def _record(package: str, *, version: str = "1.0") -> str:
        return (
            f"Package: {package}\n"
            f"Version: {version}\n"
            "License: GPL-2 | GPL-3\n"
            "NeedsCompilation: yes\n"
        )

    def _snapshot_text(self) -> str:
        return "\n".join(
            self._record(package, version=f"1.{index}")
            for index, package in enumerate(contract.PACKAGES)
        )

    def test_package_vector_is_exact_unique_visible_population(self) -> None:
        self.assertEqual(target.package_vector(), contract.PACKAGES)
        self.assertEqual(len(target.package_vector()), 20)
        self.assertEqual(len(set(target.package_vector())), 20)

    def test_protocol_build_is_network_free_and_parent_bound(self) -> None:
        with mock.patch.object(target.requests, "get") as get:
            value = target.build_evaluator_protocol(
                now=1,
                require_clean=False,
                require_implementation_tracked=False,
            )
        get.assert_not_called()
        self.assertEqual(value["population"]["fixed_denominator"], 20)
        self.assertEqual(value["evaluation"]["exact_http_get_calls"], 1)
        self.assertEqual(
            value["evaluation"]["retries_refetches_or_selective_revaluation"],
            0,
        )
        self.assertFalse(
            value["authorization"][
                "deepwidebench_dev64_exact220_leaderboard_or_sota_now"
            ]
        )

    def test_dcf_parser_unfolds_continuations_and_rejects_duplicates(self) -> None:
        records = target.parse_dcf_records(
            "Package: demo\nVersion: 1\nLicense: GPL-2 |\n GPL-3\nNeedsCompilation: yes\n"
        )
        self.assertEqual(records[0]["License"], "GPL-2 | GPL-3")
        with self.assertRaises(ValueError):
            target.parse_dcf_records("Package: demo\nPackage: duplicate\n")
        with self.assertRaises(ValueError):
            target.parse_dcf_records(" orphan\n")

    def test_dcf_parser_accepts_cran_underscore_control_fields(self) -> None:
        records = target.parse_dcf_records(
            "Package: demo\nVersion: 1\nLicense_is_FOSS: yes\n"
            "License_restricts_use: no\n"
        )
        self.assertEqual(records[0]["License_is_FOSS"], "yes")
        self.assertEqual(records[0]["License_restricts_use"], "no")

    def test_quote_aware_exact_prediction_scores_one(self) -> None:
        gold = {
            "package": "demo",
            "version": "1.0",
            "license": "GPL-2 | GPL-3",
            "needs_compilation": "yes",
        }
        prediction = (
            "```markdown\n"
            "| Package | Version | License | NeedsCompilation |\n"
            "| --- | --- | --- | --- |\n"
            '| demo | 1.0 | "GPL-2 | GPL-3" | yes |\n'
            "```"
        )
        exact = target.evaluate_prediction(prediction, gold)
        self.assertEqual(exact["exact_table_success"], 1)
        self.assertEqual(exact["composite"], 1.0)
        partial = target.evaluate_prediction(
            prediction.replace("1.0", "Unknown"), gold
        )
        self.assertEqual(partial["exact_table_success"], 0)
        self.assertEqual(partial["item_f1"], 2 / 3)

    def test_bad_header_or_extra_row_fails_closed(self) -> None:
        gold = {
            "package": "demo",
            "version": "1",
            "license": "GPL-2",
            "needs_compilation": "no",
        }
        bad = "| Package | Version | License | Build |\n|---|---|---|---|\n|demo|1|GPL-2|no|"
        self.assertEqual(target.evaluate_prediction(bad, gold)["composite"], 0.0)
        extra = (
            "| Package | Version | License | NeedsCompilation |\n"
            "|---|---|---|---|\n|demo|1|GPL-2|no|\n|other|1|GPL-2|no|"
        )
        value = target.evaluate_prediction(extra, gold)
        self.assertEqual(value["exact_table_success"], 0)
        self.assertLess(value["row_f1"], 1.0)

    def test_fetch_snapshot_makes_one_exact_nonredirecting_call(self) -> None:
        raw = gzip.compress(self._snapshot_text().encode())
        with mock.patch.object(
            target.requests,
            "get",
            return_value=_Response(target.GOLD_ENDPOINT, raw),
        ) as get:
            value = target._fetch_gold_snapshot()
        get.assert_called_once()
        self.assertFalse(get.call_args.kwargs["allow_redirects"])
        self.assertTrue(get.call_args.kwargs["stream"])
        self.assertEqual(value["attempts"], 1)
        self.assertEqual(value["valid_rows"], 20)
        self.assertIsNone(value["failure_stage"])
        self.assertTrue(value["parser_observation"]["parse_completed"])
        self.assertEqual(value["rows"][0]["license"], "GPL-2 | GPL-3")

    def test_failed_fetch_is_one_attempt_and_failure_as_zero_ready(self) -> None:
        with mock.patch.object(
            target.requests, "get", side_effect=target.requests.Timeout()
        ) as get:
            value = target._fetch_gold_snapshot()
        get.assert_called_once()
        self.assertEqual(value["attempts"], 1)
        self.assertEqual(value["valid_rows"], 0)
        self.assertEqual(value["failure_stage"], "transport")
        self.assertTrue(all(not row["valid"] for row in value["rows"]))

    def test_dcf_failure_stage_is_finite_and_parser_observation_content_free(self) -> None:
        malformed = gzip.compress(b"Package: demo\nBad key: value\n")
        with mock.patch.object(
            target.requests,
            "get",
            return_value=_Response(target.GOLD_ENDPOINT, malformed),
        ):
            value = target._fetch_gold_snapshot()
        self.assertEqual(value["failure_stage"], "dcf_invalid_field_name")
        self.assertFalse(value["parser_observation"]["parse_completed"])
        self.assertNotIn("Bad key", str(value["parser_observation"]))

    def test_snapshot_stage_or_parser_observation_tamper_fails_closed(self) -> None:
        raw = gzip.compress(self._snapshot_text().encode())
        with mock.patch.object(
            target.requests,
            "get",
            return_value=_Response(target.GOLD_ENDPOINT, raw),
        ):
            fetched = target._fetch_gold_snapshot()
        snapshot = contract.seal(
            {
                "artifact_version": 1,
                "role": "v25206_postfreeze_cran_gold_snapshot",
                "protocol_id": contract.PROTOCOL_ID,
                "created_at_unix": 1,
                "prediction_freeze_sha256": contract.sha256(
                    ROOT / contract.PREDICTION_FREEZE
                ),
                "package_vector_sha256": contract.payload_sha256(
                    target.package_vector()
                ),
                **fetched,
                "single_call_no_redirect_retry_refetch_or_selective_revaluation": True,
                "same_snapshot_for_both_frozen_arms": True,
                "created_only_after_prediction_freeze_and_pushed_forward_audit": True,
            },
            "snapshot_payload_sha256",
        )
        self.assertEqual(target.validate_gold_snapshot(snapshot), snapshot)
        for kind in ("stage", "observation"):
            changed = copy.deepcopy(snapshot)
            if kind == "stage":
                changed["failure_stage"] = "transport"
            else:
                changed["parser_observation"]["record_count"] = 0
                changed["parser_observation"].pop("observation_payload_sha256")
                changed["parser_observation"][
                    "observation_payload_sha256"
                ] = contract.payload_sha256(changed["parser_observation"])
            changed = contract.seal(changed, "snapshot_payload_sha256")
            with self.subTest(kind=kind), self.assertRaises(RuntimeError):
                target.validate_gold_snapshot(changed)

    def test_quality_gate_requires_ten_exact_gain_and_nonregression(self) -> None:
        arms = {
            contract.CONTROL_ARM: {
                "tasks": 20,
                "evaluator_valid": 20,
                "evaluator_invalid_or_not_run": 0,
                "fallback_tasks": 0,
                "exact_table_successes": 0,
                "exact_table_accuracy": 0.0,
                **{metric: 0.0 for metric in target.METRICS},
            },
            contract.CANDIDATE_ARM: {
                "tasks": 20,
                "evaluator_valid": 20,
                "evaluator_invalid_or_not_run": 0,
                "fallback_tasks": 0,
                "exact_table_successes": 10,
                "exact_table_accuracy": 0.5,
                **{metric: 0.8 for metric in target.METRICS},
            },
        }
        keys = (
            "exact_table_successes",
            "exact_table_accuracy",
            *target.METRICS,
            "evaluator_invalid_or_not_run",
            "fallback_tasks",
        )
        delta = {
            key: arms[contract.CANDIDATE_ARM][key]
            - arms[contract.CONTROL_ARM][key]
            for key in keys
        }
        metrics = {
            "arms": arms,
            f"{contract.CANDIDATE_ARM}_minus_{contract.CONTROL_ARM}": delta,
        }
        mechanism = {
            "same_response_mechanism_gate_passed": True,
            "checks": {"positive_signed_credit_zero": True},
        }
        decision = target.quality_decision(metrics, mechanism)
        self.assertTrue(decision["post_effect_tolerant_quality_gate_go"])
        arms[contract.CANDIDATE_ARM]["exact_table_successes"] = 9
        delta["exact_table_successes"] = 9
        self.assertFalse(
            target.quality_decision(metrics, mechanism)[
                "post_effect_tolerant_quality_gate_go"
            ]
        )
        arms[contract.CANDIDATE_ARM]["exact_table_successes"] = 10
        delta["exact_table_successes"] = 10
        delta["item_f1"] = -0.01
        self.assertFalse(
            target.quality_decision(metrics, mechanism)[
                "post_effect_tolerant_quality_gate_go"
            ]
        )

    def test_forward_parent_tamper_fails_closed(self) -> None:
        audit = target._read(contract.FORWARD_AUDIT, tracked=True)
        changed = copy.deepcopy(audit)
        changed["authorization"][
            "postfreeze_evaluator_implementation_and_protocol"
        ] = False
        changed = contract.seal(changed, "audit_payload_sha256")
        original_read = target._read

        def read_with_tamper(relative: Path, *, tracked: bool) -> dict:
            if relative == contract.FORWARD_AUDIT:
                return changed
            return original_read(relative, tracked=tracked)

        with mock.patch.object(target, "_read", side_effect=read_with_tamper):
            with self.assertRaises(RuntimeError):
                target._validate_forward_parents()

    def test_evaluator_network_and_privileged_capabilities_are_confined(self) -> None:
        audit = target.implementation_audit(require_tracked=False)
        self.assertTrue(audit["audit_valid"], audit["findings"])
        self.assertEqual(
            audit["request_calls"],
            [{"function": "_fetch_gold_snapshot", "method": "get"}],
        )
        self.assertEqual(audit["privileged_accesses"], [])
        tree = ast.parse((ROOT / contract.EVALUATOR).read_text(encoding="utf-8"))
        self.assertTrue(any(isinstance(node, ast.Import) for node in ast.walk(tree)))


if __name__ == "__main__":
    unittest.main()
