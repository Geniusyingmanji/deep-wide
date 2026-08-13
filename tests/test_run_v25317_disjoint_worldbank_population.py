from __future__ import annotations

import ast
import base64
import contextlib
import copy
import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import run_v25317_disjoint_worldbank_population as target  # noqa: E402


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
    excluded.update(item.rsplit("@", 1)[0].upper() for item in target.HISTORICAL_TARGET_KEYS)
    records = [
        {"id": value, "name": f"Excluded {index}", "source": {"id": "2"}}
        for index, value in enumerate(sorted(excluded))
    ]
    records.extend(
        {
            "id": f"ZZ.FRESH.{index}",
            "name": f"Fresh metric {index}",
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


class V25317DisjointWorldBankPopulationTests(unittest.TestCase):
    def _get(
        self,
        *,
        fail_one: bool = False,
        overlap_one: bool = False,
        mismatch_one: bool = False,
    ):
        authority = target._build_authority()
        catalog = _catalog(authority)
        consumed_entities = set(authority["consumed_entity_codes"])
        old_result = json.loads(
            (ROOT / target.transport.RESULT).read_text(encoding="utf-8")
        )
        old_body = (
            ROOT / old_result["target_transport"]["rows"][0]["response_path"]
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
            if overlap_one and len(calls) == 2:
                return _receipt(url, maximum, old_body)
            if mismatch_one and len(calls) == 2:
                raw_body, receipt = _receipt(url, maximum, body)
                receipt["response_sha256"] = "f" * 64
                return raw_body, receipt
            return _receipt(url, maximum, body)

        return get, calls

    def test_build_authority_binds_exact_consumed_manifests(self) -> None:
        value = target._build_authority()
        self.assertEqual(len(value["consumed_target_keys"]), 24)
        self.assertEqual(len(value["consumed_entity_codes"]), 144)
        self.assertEqual(len(value["consumed_response_sha256"]), 48)

    def test_complete_batch_freezes_disjoint_twelve_task_population(self) -> None:
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
        self.assertEqual(value["target_transport"]["provider_attempt_count"], 48)
        self.assertEqual(
            value["target_transport"]["response_body_receipt_mismatch_count"], 0
        )
        self.assertEqual(value["target_transport"]["consumed_response_overlap_count"], 0)
        self.assertEqual(value["population"]["selected_target_count"], 4)
        self.assertIn(value["population"]["entity_count"], {96, 108})
        self.assertEqual(value["population"]["task_count"], 12)
        self.assertEqual(value["population"]["selected_target_overlap_count"], 0)
        self.assertEqual(value["population"]["selected_entity_overlap_count"], 0)
        self.assertFalse(value["authorization"]["external_forward_or_evaluator"])

    def test_one_failed_target_consumes_batch_and_is_no_go_without_backfill(self) -> None:
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
        self.assertEqual(value["failure_code"], "target_transport_or_hard_wall")
        self.assertEqual(value["target_transport"]["provider_attempt_count"], 48)
        self.assertEqual(value["population"]["task_count"], 0)

    def test_consumed_response_receipt_hash_is_strict_no_go(self) -> None:
        get, _calls = self._get(overlap_one=True)
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

    def test_response_body_receipt_mismatch_is_strict_no_go(self) -> None:
        get, _calls = self._get(mismatch_one=True)
        value = target.execute_freeze(
            head="a" * 40,
            execution_start_sha256="b" * 64,
            attempt_claim_sha256="c" * 64,
            get=get,
            persist=False,
            now=1,
        )
        self.assertEqual(value["decision"], "no_go")
        self.assertEqual(value["failure_code"], "response_body_receipt_mismatch")
        self.assertEqual(
            value["target_transport"]["response_body_receipt_mismatch_count"], 1
        )

    def test_claim_and_result_tamper_fail_closed(self) -> None:
        claim = target.build_attempt_claim(
            head="a" * 40, execution_start_sha256="b" * 64, now=1
        )
        changed = copy.deepcopy(claim)
        changed["retry_resume_backfill_replacement_or_second_attempt"] = True
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
        changed = copy.deepcopy(value)
        changed["population"]["selected_entity_overlap_count"] = 1
        changed.pop("freeze_payload_sha256")
        changed["freeze_payload_sha256"] = target.payload_sha256(changed)
        with self.assertRaises(ValueError):
            target.validate_result(changed)

    def test_publish_is_create_exclusive(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            path = Path(directory) / "artifact.bin"
            target.publish_exclusive(path, b"first")
            self.assertEqual(path.read_bytes(), b"first")
            with self.assertRaises(FileExistsError):
                target.publish_exclusive(path, b"second")

    def test_source_is_label_blind_claim_before_effect_and_lease_wrapped(self) -> None:
        path = ROOT / target.SOURCE
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        main = next(
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "main"
        )
        main_source = ast.get_source_segment(source, main) or ""
        self.assertLess(
            main_source.index("publish_json_exclusive(ROOT / ATTEMPT_CLAIM"),
            main_source.index("execute_freeze("),
        )
        self.assertLess(
            main_source.index("with acquire_deepwide_api_lease("),
            main_source.index("publish_json_exclusive(ROOT / ATTEMPT_CLAIM"),
        )
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

    def test_main_without_preactivation_or_start_cannot_effect(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            fake_root = Path(directory)
            def git(*args: str) -> str:
                if args in {("rev-parse", "HEAD"), ("rev-parse", "target/main")}:
                    return "a" * 40
                if args == ("status", "--porcelain"):
                    return ""
                raise AssertionError(args)

            with mock.patch.object(target, "ROOT", fake_root), mock.patch.object(
                target, "_git", side_effect=git
            ), mock.patch.object(target, "invoke_helper") as helper:
                with self.assertRaises(FileNotFoundError):
                    target.main()
            helper.assert_not_called()


if __name__ == "__main__":
    unittest.main()
