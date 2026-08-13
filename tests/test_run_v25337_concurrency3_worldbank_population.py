from __future__ import annotations

import ast
import hashlib
import json
import sys
import threading
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import run_v25337_concurrency3_worldbank_population as target  # noqa: E402


def code3(value: int) -> str:
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    return "".join((alphabet[(value // 1296) % 36], alphabet[(value // 36) % 36], alphabet[value % 36]))


ALL_CODES = tuple(code3(index) for index in range(265))


def _catalog(authority: dict) -> bytes:
    excluded = {item.rsplit("@", 1)[0].upper() for item in authority["consumed_target_keys"]}
    excluded.update(item.rsplit("@", 1)[0].upper() for item in target.HISTORICAL_TARGET_KEYS)
    records = [{"id": value, "name": f"Excluded {index}", "source": {"id": "2"}} for index, value in enumerate(sorted(excluded))]
    records.extend({"id": f"ZZ.PACE.{index}", "name": f"Paced metric {index}", "source": {"id": "2"}} for index in range(80))
    return json.dumps([{"page": 1, "pages": 1, "per_page": 50000, "total": len(records)}, records], separators=(",", ":")).encode()


def _page(indicator: str, page: int, consumed: set[str]) -> bytes:
    codes = ALL_CODES[:200] if page == 1 else ALL_CODES[200:]
    return json.dumps([{"page": page, "pages": 2, "per_page": 200, "total": 265}, [{"countryiso3code": code, "indicator": {"id": indicator}, "date": "2022", "value": None if code in consumed else f"{indicator}-{code}"} for code in codes]], separators=(",", ":")).encode()


def _receipt(url: str, maximum: int, body: bytes | None):
    return body, {"url_sha256": hashlib.sha256(url.encode()).hexdigest(), "maximum_response_bytes": maximum, "provider_attempt_count": 1, "outcome": "success" if body is not None else "failure", "failure_code": None if body is not None else "synthetic_failure", "http_status": 200 if body is not None else None, "elapsed_seconds": 0.01, "response_bytes": len(body) if body is not None else 0, "response_sha256": hashlib.sha256(body).hexdigest() if body is not None else None, "redirect_retry_refetch_count": 0}


class V25337Concurrency3WorldBankPopulationTests(unittest.TestCase):
    @staticmethod
    def _logical_start(ticket: int, started: float) -> float:
        return started

    def _get(self, *, fail_one: bool = False, reuse_one: bool = False):
        authority = target._authority()
        catalog = _catalog(authority)
        consumed_entities = set(authority["consumed_entity_codes"])
        first_result = json.loads((ROOT / target.FIRST_RESULT).read_text())
        old_body = (ROOT / first_result["target_transport"]["rows"][0]["response_path"]).read_bytes()
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

    def test_authority_merges_exact96_144_169(self) -> None:
        value = target._authority()
        self.assertEqual(len(value["consumed_target_keys"]), 96)
        self.assertEqual(len(value["consumed_entity_codes"]), 144)
        self.assertEqual(len(value["consumed_response_sha256"]), 169)
        self.assertEqual(value["consumed_target_keys_sha256"], target.EXPECTED_TARGET_VECTOR_SHA256)
        self.assertEqual(value["consumed_response_vector_sha256"], target.EXPECTED_RESPONSE_VECTOR_SHA256)

    def test_request_executor_orders_actual_starts_and_caps_concurrency3(self) -> None:
        specs = tuple(target.selector.TargetSpec(label=f"Metric {index}", indicator=f"ZZ.CAP.{index}", year="2022", urls=target.selector.target_urls(f"ZZ.CAP.{index}")) for index in range(24))
        lock = threading.Lock()
        starts = []
        active = 0
        maximum = 0

        def get(url: str, cap: int, timeout: float):
            nonlocal active, maximum
            del timeout
            with lock:
                starts.append((url, time.monotonic()))
                active += 1
                maximum = max(maximum, active)
            time.sleep(0.002)
            with lock:
                active -= 1
            return _receipt(url, cap, b"{}")

        _grouped, _bodies, rows, _elapsed, schedule = target._request_target_pages(
            specs, get=get, logical_start=self._logical_start
        )
        self.assertEqual(len(rows), 48)
        self.assertEqual(len(starts), 48)
        self.assertEqual([item[0] for item in starts], [url for spec in specs for url in spec.urls])
        self.assertLessEqual(maximum, 3)
        self.assertLessEqual(schedule["maximum_observed_concurrency"], 3)
        self.assertEqual(schedule["configured_minimum_start_interval_seconds"], 0.0)
        self.assertGreaterEqual(schedule["observed_minimum_start_interval_seconds"], 0.0)
        self.assertTrue(all(schedule["request_start_offsets_seconds"][index] >= schedule["request_start_offsets_seconds"][index - 1] for index in range(1, 48)))

    def test_complete_batch_freezes_four_attempt_disjoint_population(self) -> None:
        get, calls = self._get()
        value = target.execute_freeze(head="a" * 40, execution_start_sha256="b" * 64, attempt_claim_sha256="c" * 64, get=get, logical_start=self._logical_start, persist=False, now=1)
        self.assertEqual(len(calls), 49)
        self.assertEqual(value["decision"], "go")
        self.assertEqual(value["target_transport"]["provider_attempt_count"], 48)
        self.assertEqual(value["population"]["selected_target_count"], 4)
        self.assertIn(value["population"]["entity_count"], {96, 108})
        self.assertEqual(value["population"]["task_count"], 12)

    def test_one_failure_is_nogo_without_backfill(self) -> None:
        get, calls = self._get(fail_one=True)
        value = target.execute_freeze(head="a" * 40, execution_start_sha256="b" * 64, attempt_claim_sha256="c" * 64, get=get, logical_start=self._logical_start, persist=False, now=1)
        self.assertEqual(len(calls), 49)
        self.assertEqual(value["decision"], "no_go")
        self.assertEqual(value["target_transport"]["provider_attempt_count"], 48)
        self.assertEqual(value["population"]["task_count"], 0)

    def test_consumed_body_reuse_is_nogo(self) -> None:
        get, _calls = self._get(reuse_one=True)
        value = target.execute_freeze(head="a" * 40, execution_start_sha256="b" * 64, attempt_claim_sha256="c" * 64, get=get, logical_start=self._logical_start, persist=False, now=1)
        self.assertEqual(value["decision"], "no_go")
        self.assertEqual(value["failure_code"], "consumed_response_overlap")

    def test_claim_and_result_tamper_fail_closed(self) -> None:
        claim = target.build_attempt_claim(head="a" * 40, execution_start_sha256="b" * 64, now=1)
        changed = copy_json(claim)
        changed["request_start_interval_seconds"] = 1.0
        changed.pop("claim_payload_sha256")
        changed["claim_payload_sha256"] = target.payload_sha256(changed)
        with self.assertRaises(ValueError):
            target.validate_attempt_claim(changed)

    def test_logical_clock_cannot_persist_or_reach_provider(self) -> None:
        calls = []

        def get(url: str, maximum: int, timeout: float):
            calls.append((url, maximum, timeout))
            raise AssertionError("provider must remain unreachable")

        with self.assertRaisesRegex(ValueError, "synthetic-only"):
            target.execute_freeze(
                head="a" * 40,
                execution_start_sha256="b" * 64,
                attempt_claim_sha256="c" * 64,
                get=get,
                logical_start=self._logical_start,
                persist=True,
                now=1,
            )
        self.assertEqual(calls, [])

    def test_source_is_label_blind_one_attempt_and_concurrency3(self) -> None:
        source = (ROOT / target.SOURCE).read_text(encoding="utf-8")
        tree = ast.parse(source)
        self.assertEqual(target.TARGET_CONCURRENCY, 3)
        self.assertEqual(target.REQUEST_START_INTERVAL_SECONDS, 0.0)
        self.assertEqual(target.TARGET_SOCKET_TIMEOUT_SECONDS, 15.0)
        for forbidden in ('.get("category")', '.get("question_type")', '.get("split")', '.get("gold")', '.get("score")', "run_official_eval_local", "AzureNativeSearchClient(", ".complete(system"):
            self.assertNotIn(forbidden, source)
        self.assertIn("next_allowed_start = actual + REQUEST_START_INTERVAL_SECONDS", source)
        self.assertIn("ThreadPoolExecutor(max_workers=TARGET_CONCURRENCY)", source)
        self.assertTrue(any(isinstance(node, ast.FunctionDef) and node.name == "main" for node in ast.walk(tree)))


def copy_json(value):
    return json.loads(json.dumps(value))


if __name__ == "__main__":
    unittest.main()
