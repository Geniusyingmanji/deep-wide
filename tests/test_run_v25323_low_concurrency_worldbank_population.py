from __future__ import annotations

import ast
import hashlib
import json
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import run_v25323_low_concurrency_worldbank_population as target  # noqa: E402


def code3(value: int) -> str:
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    return "".join(
        (
            alphabet[(value // (36 * 36)) % 36],
            alphabet[(value // 36) % 36],
            alphabet[value % 36],
        )
    )


ALL_CODES = tuple(code3(index) for index in range(265))


def _catalog(authority: dict) -> bytes:
    excluded = {
        item.rsplit("@", 1)[0].upper()
        for item in authority["consumed_target_keys"]
    }
    excluded.update(
        item.rsplit("@", 1)[0].upper() for item in target.HISTORICAL_TARGET_KEYS
    )
    records = [
        {"id": value, "name": f"Excluded {index}", "source": {"id": "2"}}
        for index, value in enumerate(sorted(excluded))
    ]
    records.extend(
        {
            "id": f"ZZ.LOW.{index}",
            "name": f"Low concurrency metric {index}",
            "source": {"id": "2"},
        }
        for index in range(80)
    )
    return json.dumps(
        [
            {"page": 1, "pages": 1, "per_page": 50000, "total": len(records)},
            records,
        ],
        separators=(",", ":"),
    ).encode()


def _page(indicator: str, page: int, consumed_entities: set[str]) -> bytes:
    codes = ALL_CODES[:200] if page == 1 else ALL_CODES[200:]
    return json.dumps(
        [
            {"page": page, "pages": 2, "per_page": 200, "total": 265},
            [
                {
                    "countryiso3code": code,
                    "indicator": {"id": indicator},
                    "date": "2022",
                    "value": None
                    if code in consumed_entities
                    else f"{indicator}-{page}-{position}",
                }
                for position, code in enumerate(codes)
            ],
        ],
        separators=(",", ":"),
    ).encode()


def _receipt(url: str, maximum: int, body: bytes | None):
    return body, {
        "url_sha256": hashlib.sha256(url.encode()).hexdigest(),
        "maximum_response_bytes": maximum,
        "provider_attempt_count": 1,
        "outcome": "success" if body is not None else "failure",
        "failure_code": None if body is not None else "synthetic_failure",
        "http_status": 200 if body is not None else None,
        "elapsed_seconds": 0.01,
        "response_bytes": len(body) if body is not None else 0,
        "response_sha256": hashlib.sha256(body).hexdigest() if body is not None else None,
        "redirect_retry_refetch_count": 0,
    }


class V25323LowConcurrencyWorldBankPopulationTests(unittest.TestCase):
    def _get(self, *, fail_one: bool = False, reuse_one: bool = False):
        authority = target._authority()
        catalog = _catalog(authority)
        consumed_entities = set(authority["consumed_entity_codes"])
        first_result = json.loads((ROOT / target.FIRST_RESULT).read_text())
        old_body = (
            ROOT / first_result["target_transport"]["rows"][0]["response_path"]
        ).read_bytes()
        calls = []

        def get(url: str, maximum: int, timeout: float):
            del timeout
            calls.append(url)
            if url == target.CATALOG_URL:
                return _receipt(url, maximum, catalog)
            indicator = url.split("/indicator/", 1)[1].split("?", 1)[0]
            page = int(url.split("page=", 1)[1].split("&", 1)[0])
            body = _page(indicator, page, consumed_entities)
            if fail_one and len(calls) == 2:
                body = None
            if reuse_one and len(calls) == 2:
                body = old_body
            return _receipt(url, maximum, body)

        return get, calls

    def test_authority_merges_exact48_144_84_and_diagnosis(self) -> None:
        value = target._authority()
        self.assertEqual(len(value["consumed_target_keys"]), 48)
        self.assertEqual(len(value["consumed_entity_codes"]), 144)
        self.assertEqual(len(value["consumed_response_sha256"]), 84)
        self.assertEqual(value["consumed_target_keys_sha256"], target.EXPECTED_TARGET_VECTOR_SHA256)
        self.assertEqual(value["consumed_response_vector_sha256"], target.EXPECTED_RESPONSE_VECTOR_SHA256)

    def test_request_executor_never_exceeds_six_workers(self) -> None:
        specs = tuple(
            target.selector.TargetSpec(
                label=f"Metric {index}",
                indicator=f"ZZ.CAP.{index}",
                year="2022",
                urls=target.selector.target_urls(f"ZZ.CAP.{index}"),
            )
            for index in range(24)
        )
        lock = threading.Lock()
        active = 0
        maximum = 0

        def get(url: str, cap: int, timeout: float):
            nonlocal active, maximum
            del timeout
            with lock:
                active += 1
                maximum = max(maximum, active)
            time.sleep(0.005)
            with lock:
                active -= 1
            return _receipt(url, cap, b"{}")

        _grouped, _bodies, rows, _elapsed = target._request_target_pages(
            specs, get=get
        )
        self.assertEqual(len(rows), 48)
        self.assertGreater(maximum, 1)
        self.assertLessEqual(maximum, 6)

    def test_complete_batch_freezes_twice_disjoint_population(self) -> None:
        get, calls = self._get()
        value = target.execute_freeze(
            head="a" * 40,
            execution_start_sha256="b" * 64,
            attempt_claim_sha256="c" * 64,
            get=get,
            persist=False,
            now=1,
        )
        self.assertEqual(len(calls), 49)
        self.assertEqual(value["decision"], "go")
        self.assertEqual(value["target_transport"]["concurrency"], 6)
        self.assertEqual(value["target_transport"]["provider_attempt_count"], 48)
        self.assertEqual(value["target_transport"]["successful_response_count"], 48)
        self.assertEqual(value["population"]["selected_target_count"], 4)
        self.assertIn(value["population"]["entity_count"], {96, 108})
        self.assertEqual(value["population"]["task_count"], 12)
        self.assertTrue(value["authorization"]["postfreeze_audit"])
        self.assertFalse(value["authorization"]["external_monotone_fill_protocol_or_forward"])

    def test_one_failure_is_nogo_without_backfill(self) -> None:
        get, calls = self._get(fail_one=True)
        value = target.execute_freeze(
            head="a" * 40,
            execution_start_sha256="b" * 64,
            attempt_claim_sha256="c" * 64,
            get=get,
            persist=False,
            now=1,
        )
        self.assertEqual(len(calls), 49)
        self.assertEqual(value["decision"], "no_go")
        self.assertEqual(value["target_transport"]["provider_attempt_count"], 48)
        self.assertEqual(value["population"]["task_count"], 0)
        self.assertFalse(value["authorization"]["postfreeze_audit"])

    def test_consumed_body_reuse_is_nogo(self) -> None:
        get, _calls = self._get(reuse_one=True)
        value = target.execute_freeze(
            head="a" * 40,
            execution_start_sha256="b" * 64,
            attempt_claim_sha256="c" * 64,
            get=get,
            persist=False,
            now=1,
        )
        self.assertEqual(value["decision"], "no_go")
        self.assertEqual(value["failure_code"], "consumed_response_overlap")
        self.assertEqual(value["target_transport"]["consumed_response_overlap_count"], 1)

    def test_claim_and_result_tamper_fail_closed(self) -> None:
        claim = target.build_attempt_claim(
            head="a" * 40, execution_start_sha256="b" * 64, now=1
        )
        changed = dict(claim)
        changed["target_concurrency"] = 12
        changed.pop("claim_payload_sha256")
        changed["claim_payload_sha256"] = target.payload_sha256(changed)
        with self.assertRaises(ValueError):
            target.validate_attempt_claim(changed)
        get, _calls = self._get()
        value = target.execute_freeze(
            head="a" * 40,
            execution_start_sha256="b" * 64,
            attempt_claim_sha256="c" * 64,
            get=get,
            persist=False,
            now=1,
        )
        changed = json.loads(json.dumps(value))
        changed["target_transport"]["concurrency"] = 12
        changed.pop("freeze_payload_sha256")
        changed["freeze_payload_sha256"] = target.payload_sha256(changed)
        with self.assertRaises(ValueError):
            target.validate_result(changed)

    def test_result_rejects_resealed_nested_schema_and_negative_counts(self) -> None:
        get, _calls = self._get()
        value = target.execute_freeze(
            head="a" * 40,
            execution_start_sha256="b" * 64,
            attempt_claim_sha256="c" * 64,
            get=get,
            persist=False,
            now=1,
        )
        mutations = (
            lambda item: item["execution_start"].update({"extra": True}),
            lambda item: item["attempt_claim"].update({"extra": True}),
            lambda item: item["catalog"].update({"extra": True}),
            lambda item: item["target_transport"].update(
                {"consumed_response_overlap_count": -1}
            ),
            lambda item: item["target_transport"].update(
                {"response_body_receipt_mismatch_count": -1}
            ),
            lambda item: item.update({"whole_elapsed_seconds": -1.0}),
            lambda item: item["authorization"].update({"hidden": False}),
        )
        for mutate in mutations:
            changed = json.loads(json.dumps(value))
            mutate(changed)
            changed.pop("freeze_payload_sha256")
            changed["freeze_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                target.validate_result(changed)

    def test_preactivation_authority_rejects_resealed_relaxation(self) -> None:
        source_manifest = target._source_manifest()
        value = {
            "artifact_version": 1,
            "role": "v25325_low_concurrency_worldbank_population_preactivation_audit",
            "created_at_unix": 1,
            "git": {
                "head": "a" * 40,
                "target_main": "a" * 40,
                "equal": True,
                "clean": True,
            },
            "fixed_inputs": {},
            "implementation_commit": {"commit": "b" * 40, "paths": []},
            "build_audit": {"path": str(target.BUILD_AUDIT), "sha256": "c" * 64},
            "source_manifest": source_manifest,
            "tests": {},
            "runtime_dependency_vector": [],
            "runtime_dependency_vector_sha256": "d" * 64,
            "runtime_dependency_path_sha256": "e" * 64,
            "semantic_audit": {
                "privileged_runtime_field_accesses": [],
                "evaluator_capabilities": [],
                "credential_literal_hits": [],
                "allowed_provider_rank_access": [],
                "auditor_or_explicit_file_credential_literal_hits": [],
                "untracked_sources": [],
            },
            "runtime_invariants": {},
            "consumed_manifest_contract": {
                "target_count": 48,
                "entity_count": 144,
                "response_count": 84,
                "preferred_entity_count": 108,
                "minimum_entity_count": 96,
                "task_count": 12,
                "all_overlap_counts_must_be_zero": True,
            },
            "protected_watchers": {
                str(row["pid"]): {
                    "present": True,
                    "start_ticks": row["start_ticks"],
                    "matches_frozen_identity": True,
                }
                for row in target.EXPECTED_WATCHERS
            },
            "shared_api_lease_inactive": True,
            "active_conflicts": [],
            "future_surfaces_pristine": True,
            "checks": {
                name: True for name in target.PREACTIVATION_CHECK_NAMES
            },
            "findings": [],
            "audit_valid": True,
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read": False,
            "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
            "entropy_or_information_gain_assigns_signed_credit": False,
            "authorization": {
                "execution_start_generation": True,
                "single_low_concurrency_population_freeze": False,
                "external_forward_or_evaluator": False,
                "deepwidebench_dev64_exact220_forward_or_evaluator": False,
                "retry_resume_backfill_replacement_or_second_attempt": False,
            },
        }
        value["audit_payload_sha256"] = target.payload_sha256(value)
        changed = json.loads(json.dumps(value))
        changed["consumed_manifest_contract"]["response_count"] = 83
        changed.pop("audit_payload_sha256")
        changed["audit_payload_sha256"] = target.payload_sha256(changed)
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            fake = Path(directory) / "preactivation.json"
            fake_build = Path(directory) / "build.json"
            relative = fake.relative_to(ROOT)
            relative_build = fake_build.relative_to(ROOT)
            fake_build.write_text("{}\n", encoding="utf-8")
            value["build_audit"] = {
                "path": str(relative_build),
                "sha256": target.sha256(fake_build),
            }
            value.pop("audit_payload_sha256")
            value["audit_payload_sha256"] = target.payload_sha256(value)
            changed = json.loads(json.dumps(value))
            changed["consumed_manifest_contract"]["response_count"] = 83
            changed.pop("audit_payload_sha256")
            changed["audit_payload_sha256"] = target.payload_sha256(changed)
            fake.write_text(json.dumps(value), encoding="utf-8")
            with mock.patch.object(target, "PREACTIVATION", relative), mock.patch.object(
                target, "BUILD_AUDIT", relative_build
            ):
                self.assertTrue(target._preactivation_authority())
            fake.write_text(json.dumps(changed), encoding="utf-8")
            with mock.patch.object(target, "PREACTIVATION", relative), mock.patch.object(
                target, "BUILD_AUDIT", relative_build
            ):
                self.assertFalse(target._preactivation_authority())

    def test_source_changes_only_scheduling_and_is_label_blind(self) -> None:
        source = (ROOT / target.SOURCE).read_text(encoding="utf-8")
        tree = ast.parse(source)
        self.assertEqual(target.TARGET_CONCURRENCY, 6)
        self.assertEqual(target.TARGET_SOCKET_TIMEOUT_SECONDS, 15.0)
        self.assertEqual(target.WHOLE_FREEZE_HARD_WALL_SECONDS, 145.0)
        for forbidden in (
            '.get("category")',
            '.get("question_type")',
            '.get("split")',
            '.get("gold")',
            '.get("score")',
            "run_official_eval_local",
            "AzureNativeSearchClient(",
            ".complete(system",
        ):
            self.assertNotIn(forbidden, source)
        self.assertTrue(any(isinstance(node, ast.FunctionDef) and node.name == "main" for node in ast.walk(tree)))


if __name__ == "__main__":
    unittest.main()
