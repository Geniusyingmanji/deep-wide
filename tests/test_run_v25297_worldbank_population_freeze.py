from __future__ import annotations

import copy
import contextlib
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import run_v25297_worldbank_population_freeze as target  # noqa: E402
from scripts import v25297_worldbank_get_helper as helper  # noqa: E402


def _catalog(*, pages: int = 1, total_delta: int = 0) -> bytes:
    records = [
        {
            "id": f"ZZ.TEST.{index:04d}",
            "name": f"Synthetic public indicator {index}",
            "source": {"id": "2", "value": "World Development Indicators"},
        }
        for index in range(40)
    ]
    return json.dumps(
        [
            {"page": 1, "pages": pages, "per_page": 50000, "total": len(records) + total_delta},
            records,
        ],
        separators=(",", ":"),
    ).encode()


def _codes() -> list[str]:
    values = []
    for first in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        for second in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            code = "Z" + first + second
            values.append(code)
            if len(values) == 160:
                return values
    raise AssertionError


def _page(indicator: str, page: int) -> bytes:
    codes = _codes()
    valid = codes[:130] if page == 1 else codes[130:]
    invalid_count = 200 - len(valid) if page == 1 else 65 - len(valid)
    records = [
        {
            "countryiso3code": code,
            "indicator": {"id": indicator, "value": "Synthetic"},
            "date": "2022",
            "value": index + page,
        }
        for index, code in enumerate(valid)
    ]
    records.extend(
        {
            "countryiso3code": "",
            "indicator": {"id": indicator, "value": "Synthetic"},
            "date": "2022",
            "value": index,
        }
        for index in range(invalid_count)
    )
    return json.dumps(
        [
            {"page": page, "pages": 2, "per_page": 200, "total": 265},
            records,
        ],
        separators=(",", ":"),
    ).encode()


def _receipt(url: str, maximum: int, body: bytes | None) -> tuple[bytes | None, dict]:
    return body, {
        "url_sha256": hashlib.sha256(url.encode()).hexdigest(),
        "maximum_response_bytes": maximum,
        "provider_attempt_count": 1,
        "outcome": "success" if body is not None else "failure",
        "failure_code": None if body is not None else "synthetic_failure",
        "http_status": 200 if body is not None else None,
        "elapsed_seconds": 0.001,
        "response_bytes": len(body) if body is not None else 0,
        "response_sha256": hashlib.sha256(body).hexdigest() if body is not None else None,
        "redirect_retry_refetch_count": 0,
    }


class V25297WorldBankPopulationFreezeTests(unittest.TestCase):
    def test_historical_manifest_is_hash_bound_and_indicator_complete(self) -> None:
        indicators, rows = target.historical_indicator_manifest()
        self.assertEqual(indicators, target.EXPECTED_HISTORICAL_INDICATORS)
        self.assertEqual(len(indicators), 35)
        self.assertEqual(len(rows), len(target.HISTORICAL_SOURCE_HASHES))

    def test_catalog_requires_single_page_exact_total_and_selects_exact24(self) -> None:
        specs, stats = target.parse_catalog(
            _catalog(), historical=target.EXPECTED_HISTORICAL_INDICATORS
        )
        self.assertEqual(len(specs), 24)
        self.assertEqual(len({spec.key for spec in specs}), 24)
        self.assertEqual(stats["catalog_total"], 40)
        self.assertEqual(stats["selected_candidate_count"], 24)
        for changed in (_catalog(pages=2), _catalog(total_delta=1)):
            with self.assertRaises(ValueError):
                target.parse_catalog(changed, historical=target.EXPECTED_HISTORICAL_INDICATORS)

    def test_complete_48_response_batch_freezes_viable_12_task_population(self) -> None:
        def get(url: str, maximum: int, timeout: float):
            del timeout
            if url == target.CATALOG_URL:
                return _receipt(url, maximum, _catalog())
            indicator = url.split("/indicator/", 1)[1].split("?", 1)[0]
            page = int(url.split("page=", 1)[1].split("&", 1)[0])
            return _receipt(url, maximum, _page(indicator, page))

        value = target.execute_freeze(
            head="a" * 40,
            execution_start_sha256="b" * 64,
            attempt_claim_sha256="c" * 64,
            get=get,
            persist=False,
            now=1,
        )
        self.assertEqual(value["decision"], "go")
        self.assertEqual(value["candidate_target_count"], 24)
        self.assertEqual(value["target_transport"]["provider_attempt_count"], 48)
        self.assertEqual(value["target_transport"]["successful_response_count"], 48)
        self.assertEqual(value["population"]["selected_target_count"], 4)
        self.assertEqual(value["population"]["entity_count"], 144)
        self.assertEqual(value["population"]["task_count"], 12)
        self.assertEqual(value["population"]["rendered_page_count"], 8)
        self.assertFalse(value["authorization"]["postfreeze_evaluator"])

    def test_one_failed_target_consumes_full_batch_but_never_selects_or_backfills(self) -> None:
        calls = []

        def get(url: str, maximum: int, timeout: float):
            del timeout
            calls.append(url)
            if url == target.CATALOG_URL:
                return _receipt(url, maximum, _catalog())
            indicator = url.split("/indicator/", 1)[1].split("?", 1)[0]
            page = int(url.split("page=", 1)[1].split("&", 1)[0])
            body = None if len(calls) == 2 else _page(indicator, page)
            return _receipt(url, maximum, body)

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
        self.assertEqual(value["target_transport"]["successful_response_count"], 47)
        self.assertEqual(value["population"]["selected_target_count"], 0)
        self.assertFalse(
            value["authorization"]["external_monotone_fill_forward_after_valid_postfreeze_audit"]
        )

    def test_attempt_claim_and_result_resealed_authority_or_credit_tamper_fails(self) -> None:
        claim = target.build_attempt_claim(
            head="a" * 40, execution_start_sha256="b" * 64, now=1
        )
        for kind in ("retry", "credit", "result_path"):
            changed = copy.deepcopy(claim)
            if kind == "retry":
                changed["retry_resume_backfill_replacement_or_second_attempt"] = True
            elif kind == "credit":
                changed["entropy_or_information_gain_assigns_signed_credit"] = True
            else:
                changed["fixed_result_path"] = "results/alternate.json"
            changed.pop("claim_payload_sha256")
            changed["claim_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_attempt_claim(changed)

    def test_resealed_result_nested_target_catalog_or_authority_tamper_fails(self) -> None:
        def get(url: str, maximum: int, timeout: float):
            del timeout
            if url == target.CATALOG_URL:
                return _receipt(url, maximum, _catalog())
            indicator = url.split("/indicator/", 1)[1].split("?", 1)[0]
            page = int(url.split("page=", 1)[1].split("&", 1)[0])
            return _receipt(url, maximum, _page(indicator, page))

        value = target.execute_freeze(
            head="a" * 40,
            execution_start_sha256="b" * 64,
            attempt_claim_sha256="c" * 64,
            get=get,
            persist=False,
            now=1,
        )
        for kind in ("row", "catalog", "manifest", "authority", "hidden"):
            changed = copy.deepcopy(value)
            if kind == "row":
                changed["target_transport"]["rows"][0]["page"] = 2
            elif kind == "catalog":
                changed["catalog"]["self_proved_one_page_complete"] = False
            elif kind == "manifest":
                changed["historical_indicator_manifest"][0]["indicator_count"] += 1
            elif kind == "authority":
                changed["authorization"]["postfreeze_evaluator"] = True
            else:
                changed["population"]["hidden"] = True
            changed.pop("freeze_payload_sha256")
            changed["freeze_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_result(changed)

    def test_execution_start_binds_preactivation_and_exact_source_manifest(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            fake = Path(directory) / "preactivation.json"
            fake.write_text("{}\n", encoding="utf-8")
            value = {
                "artifact_version": 1,
                "role": "v25303_worldbank_population_execution_start",
                "created_at_unix": 1,
                "git_parent": "b" * 40,
                "preactivation_audit": {
                    "path": str(target.PREACTIVATION),
                    "sha256": target.sha256(fake),
                },
                "source_manifest": target._source_manifest(),
                "runtime_state": {
                    "protected_watchers": list(target.EXPECTED_WATCHERS),
                    "shared_api_lease_inactive": True,
                },
                "transport_contract": {
                    "catalog_url": target.CATALOG_URL,
                    "catalog_provider_attempt_count": 1,
                    "candidate_target_count": target.runtime.MINIMUM_TARGET_OVERSAMPLE,
                    "target_provider_attempt_count": 48,
                    "target_concurrency": target.TARGET_CONCURRENCY,
                    "catalog_phase_hard_wall_seconds": target.CATALOG_PHASE_HARD_WALL_SECONDS,
                    "target_phase_hard_wall_seconds": target.TARGET_PHASE_HARD_WALL_SECONDS,
                    "whole_freeze_hard_wall_seconds": target.WHOLE_FREEZE_HARD_WALL_SECONDS,
                },
                "fixed_attempt_claim_path": str(target.ATTEMPT_CLAIM),
                "fixed_result_path": str(target.RESULT),
                "fixed_output_root": str(target.OUTPUT_ROOT),
                "single_catalog_then_single_48_target_response_batch": True,
                "retry_resume_refetch_backfill_replacement_or_second_attempt": False,
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read": False,
                "entropy_or_information_gain_assigns_signed_credit": False,
                "authorization": {
                    "single_worldbank_population_freeze": True,
                    "external_forward_or_evaluator": False,
                },
            }
            value["start_payload_sha256"] = target.payload_sha256(value)
            original_ordinary = target._ordinary

            def ordinary(path: Path, *, required: bool = True) -> Path:
                if path == target.PREACTIVATION:
                    return fake
                return original_ordinary(path, required=required)

            with mock.patch.object(target, "_ordinary", side_effect=ordinary), mock.patch.object(
                target, "_preactivation_authority", return_value=True
            ), mock.patch.object(target, "_revocation_barrier", return_value=True):
                checked = target._validate_execution_start(value, current_head="a" * 40)
            self.assertEqual(checked, value)
            changed = copy.deepcopy(value)
            changed["source_manifest"][str(target.SOURCE)] = "0" * 64
            changed.pop("start_payload_sha256")
            changed["start_payload_sha256"] = target.payload_sha256(changed)
            with mock.patch.object(target, "_ordinary", side_effect=ordinary), mock.patch.object(
                target, "_preactivation_authority", return_value=True
            ), mock.patch.object(target, "_revocation_barrier", return_value=True), self.assertRaises(ValueError):
                target._validate_execution_start(changed, current_head="a" * 40)

    def test_revocation_barrier_proves_old_start_failed_before_all_effects(self) -> None:
        self.assertTrue(target._revocation_barrier())
        self.assertNotEqual(
            target.ATTEMPT_CLAIM,
            Path("results/v25297_worldbank_population_attempt_claim_v1_20260813.json"),
        )
        self.assertNotEqual(
            target.RESULT,
            Path("results/v25297_worldbank_population_freeze_v1_20260813.json"),
        )
        self.assertNotEqual(
            target.OUTPUT_ROOT,
            Path("outputs/v25297_worldbank_population_v1_20260813"),
        )

    def test_main_valid_single_file_start_reaches_claim_then_execute_without_git_head_field(self) -> None:
        head = "a" * 40
        parent = "b" * 40
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            fake_root = Path(directory)
            start = fake_root / "start.json"
            start.write_text("{}\n", encoding="utf-8")
            published = []

            def git(*args: str) -> str:
                if args in {("rev-parse", "HEAD"), ("rev-parse", "target/main")}:
                    return head
                if args == ("status", "--porcelain"):
                    return ""
                if args == ("rev-parse", f"{head}^"):
                    return parent
                if args == ("diff-tree", "--no-commit-id", "--name-only", "-r", head):
                    return str(target.EXECUTION_START)
                raise AssertionError(args)

            result = {
                "decision": "go",
                "failure_code": None,
                "effect_accounting": {
                    "catalog_provider_attempt_count": 1,
                    "target_provider_attempt_count": 48,
                },
                "target_transport": {"successful_response_count": 48},
                "population": {"selected_target_count": 4, "task_count": 12},
            }
            with mock.patch.object(target, "ROOT", fake_root), mock.patch.object(
                target, "_git", side_effect=git
            ), mock.patch.object(target, "_ordinary", return_value=start), mock.patch.object(
                target, "_validate_execution_start", return_value={"git_parent": parent}
            ), mock.patch.object(
                target, "_protected_watchers_match", return_value=True
            ), mock.patch.object(
                target, "sha256", return_value="c" * 64
            ), mock.patch.object(
                target,
                "acquire_deepwide_api_lease",
                return_value=contextlib.nullcontext({}),
            ), mock.patch.object(
                target, "build_attempt_claim", return_value={"claim": True}
            ), mock.patch.object(
                target,
                "publish_json_exclusive",
                side_effect=lambda path, value: published.append((path, value)),
            ), mock.patch.object(
                target, "execute_freeze", return_value=result
            ) as execute:
                target.main()
            self.assertEqual([path for path, _value in published], [fake_root / target.ATTEMPT_CLAIM, fake_root / target.RESULT])
            execute.assert_called_once()

    def test_raw_and_json_publish_are_create_exclusive(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            path = Path(directory) / "artifact.bin"
            target.publish_exclusive(path, b"first")
            self.assertEqual(path.read_bytes(), b"first")
            with self.assertRaises(FileExistsError):
                target.publish_exclusive(path, b"second")

    def test_helper_rejects_unrelated_url_before_provider_attempt(self) -> None:
        completed = subprocess.run(
            [sys.executable, "-I", "-B", str(ROOT / target.HELPER)],
            cwd=ROOT,
            env={
                "HOME": os.environ.get("HOME", str(Path.home())),
                "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
                "DEEPWIDE_EXPECTED_PARENT_PID": str(os.getpid()),
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONNOUSERSITE": "1",
                "PYTHONSAFEPATH": "1",
            },
            input=json.dumps(
                {
                    "url": "https://example.org/",
                    "socket_timeout_seconds": 1,
                    "maximum_response_bytes": helper.TARGET_MAXIMUM_BYTES,
                }
            ),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5,
            check=False,
        )
        value = json.loads(completed.stdout)
        self.assertEqual(value["kind"], "invalid_input")
        self.assertEqual(value["provider_attempt_count"], 0)
        self.assertEqual(value["body_base64"], "")

    def test_helper_allowlist_accepts_exact_catalog_and_two_target_pages(self) -> None:
        self.assertEqual(
            helper._url_kind(helper.CATALOG_URL, helper.CATALOG_MAXIMUM_BYTES),
            "catalog",
        )
        for page, url in enumerate(target.target_urls("ZZ.TEST.0001"), 1):
            with self.subTest(page=page):
                self.assertTrue(helper._target_url(url))
                self.assertEqual(
                    helper._url_kind(url, helper.TARGET_MAXIMUM_BYTES), "target"
                )
        self.assertIsNone(
            helper._url_kind(
                target.target_urls("ZZ.TEST.0001")[0] + "&extra=1",
                helper.TARGET_MAXIMUM_BYTES,
            )
        )

    def test_selection_source_is_label_blind_and_has_no_model_or_evaluator(self) -> None:
        source = (ROOT / target.SOURCE).read_text(encoding="utf-8")
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


if __name__ == "__main__":
    unittest.main()
