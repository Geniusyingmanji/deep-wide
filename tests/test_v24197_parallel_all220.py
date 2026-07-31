from __future__ import annotations

import copy
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
CANONICAL_ID_PATHS = (
    ROOT / "configs/full220_v2403_r1_test_s01.ids",
    ROOT / "configs/full220_v2403_r1_test_s02.ids",
    ROOT / "configs/full220_v2403_r1_test_s03.ids",
    ROOT / "configs/full220_v2403_r1_devval_s04.ids",
)

from deepwide_agent.v24194_capacity_ladder import (
    PROBE_EXPECTED_OUTPUT,
    PROBE_INPUT_UTF8_BYTES,
    ProbeSettings,
    build_capacity_freeze,
    run_capacity_ladder,
)
from deepwide_agent.v24197_parallel_all220 import (
    _bytes_snapshot,
    EXPECTED_COUNTS,
    EXPECTED_SHARDS,
    compile_parallel_plan,
    file_sha256,
    payload_sha256,
    validate_candidate_bundle,
    validate_capacity_pair,
)


class FakeClient:
    def __init__(self, failure_at: int | None = None) -> None:
        self.failure_at = failure_at
        self.calls = 0
        self.active = 0
        self.maximum_active = 0
        self.lock = threading.Lock()

    def complete(self, system, user, *, max_output_tokens):
        with self.lock:
            self.calls += 1
            call = self.calls
            self.active += 1
            self.maximum_active = max(self.maximum_active, self.active)
        try:
            success = self.failure_at != call
            return SimpleNamespace(
                text=PROBE_EXPECTED_OUTPUT if success else "WRONG",
                attempts=1,
                output_truncated=False,
                input_utf8_bytes=len((system + user).encode("utf-8")),
                request_body_bytes=PROBE_INPUT_UTF8_BYTES + 100,
                max_output_tokens=max_output_tokens,
            )
        finally:
            with self.lock:
                self.active -= 1


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")


class V24197ParallelAll220Tests(unittest.TestCase):
    def capacity_pair(self, *, serial: bool = False):
        settings = ProbeSettings(
            levels=(1, 2, 4),
            waves_per_level=2,
            absolute_latency_ceiling_seconds=999,
            baseline_p95_multiplier=999,
            baseline_median_multiplier=999,
            maximum_parallel_shards=4,
            per_shard_model_workers=2,
        )
        report = run_capacity_ladder(
            FakeClient(failure_at=3 if serial else None), settings=settings
        )
        report.update(
            protocol={
                "path": "results/v24196_capacity_executor_preregistration_v1_20260731.json",
                "sha256": "p" * 64,
            },
            r1_release={"result_sha256": "r" * 64},
            quality_campaign_terminal={"terminal": True},
            execution_activation={"sha256": "a" * 64},
            shared_api_lease_owner="v24194_neutral_gpt56_capacity_ladder_v1",
            shared_api_lease_acquired=True,
            created_at_unix=1,
        )
        report["report_payload_sha256"] = payload_sha256(report)
        report_bytes = json.dumps(report, sort_keys=True).encode()
        report_sha = __import__("hashlib").sha256(report_bytes).hexdigest()
        freeze = build_capacity_freeze(
            report,
            report_path="results/v24196_capacity_ladder_report_v1_20260731.json",
            report_sha256=report_sha,
            protocol_path="results/v24196_capacity_executor_preregistration_v1_20260731.json",
            protocol_sha256="p" * 64,
        )
        freeze["freeze_payload_sha256"] = payload_sha256(freeze)
        return report, freeze, report_sha

    def candidate(self, root: Path, freeze: dict, *, workers: int):
        all_ids = [
            value.strip()
            for path in CANONICAL_ID_PATHS
            for value in path.read_text(encoding="utf-8").splitlines()
            if value.strip()
        ]
        method_contract = "d" * 64
        go = {
            "artifact_version": 1,
            "role": "v24197_candidate_quality_go_receipt",
            "label_blind": True,
            "decision": "go",
            "candidate_freeze_allowed": True,
            "benchmark_forward_launch_allowed": False,
            "candidate_pipeline_version": "v2.future",
            "candidate_state_schema_version": 99,
            "all220_opaque_partition_sha256": payload_sha256(sorted(all_ids)),
            "candidate_method_contract_sha256": method_contract,
            "runtime_mapping_gold_category_question_type_evaluator_score_read": False,
        }
        go["receipt_payload_sha256"] = payload_sha256(go)
        go_path = root / "results/go.json"
        write_json(go_path, go)

        manifest_path = root / "configs/candidate/manifest.jsonl"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text("{}\n", encoding="utf-8")
        code_path = root / "src/candidate/runtime.py"
        code_path.parent.mkdir(parents=True, exist_ok=True)
        code_path.write_text("VERSION = 1\n", encoding="utf-8")

        rows = {}
        cursor = 0
        for tag in EXPECTED_SHARDS:
            count = EXPECTED_COUNTS[tag]
            ids = all_ids[cursor : cursor + count]
            cursor += count
            ids_path = root / f"configs/candidate/{tag}.ids"
            ids_path.parent.mkdir(parents=True, exist_ok=True)
            ids_path.write_text("\n".join(ids) + "\n", encoding="utf-8")
            freeze_path = root / f"configs/candidate/{tag}.json"
            candidate_freeze = {
                "pipeline_version": "v2.future",
                "state_schema_version": 99,
                "manifest": "configs/candidate/manifest.jsonl",
                "manifest_sha256": file_sha256(manifest_path),
                "selected_ids_file": str(ids_path.relative_to(root)),
                "selected_ids_sha256": file_sha256(ids_path),
                "selected_count": count,
                "code_sha256": {
                    "src/candidate/runtime.py": file_sha256(code_path)
                },
                "model": {
                    "proxy_url": freeze["endpoint"],
                    "name": freeze["model"],
                    "reasoning_effort": freeze["reasoning_effort"],
                    "service_tier": freeze["service_tier"],
                    "timeout_seconds": 180,
                    "max_retries": 1,
                },
                "search": {"provider": "tavily", "workers": 8},
                "runtime": {
                    "candidate_model_workers": workers,
                    "row_model_workers": workers,
                    "candidate_tokens": 20000,
                },
            }
            write_json(freeze_path, candidate_freeze)
            rows[tag] = {
                "freeze": {
                    "path": str(freeze_path.relative_to(root)),
                    "sha256": file_sha256(freeze_path),
                },
                "selected_ids": {
                    "path": str(ids_path.relative_to(root)),
                    "sha256": file_sha256(ids_path),
                    "count": count,
                },
                "output_directory": f"outputs/fresh_{tag}",
            }
        bundle = {
            "artifact_version": 1,
            "role": "v24197_fresh_all220_execution_bundle",
            "label_blind": True,
            "target_name": "fresh_all220_v1",
            "pipeline_version": "v2.future",
            "state_schema_version": 99,
            "candidate_method_contract_sha256": method_contract,
            "capacity_freeze": {
                "path": "results/capacity.json",
                "sha256": "f" * 64,
            },
            "candidate_quality_go_receipt": {
                "path": str(go_path.relative_to(root)),
                "sha256": file_sha256(go_path),
            },
            "model": {
                "endpoint": freeze["endpoint"],
                "name": freeze["model"],
                "reasoning_effort": freeze["reasoning_effort"],
                "service_tier": freeze["service_tier"],
            },
            "shard_order": list(EXPECTED_SHARDS),
            "shards": rows,
            "selected_total": 220,
            "all_output_directories_absent_at_bundle": True,
            "same_pipeline_code_prompt_search_budget_threshold": True,
            "forward_failure_scored_as_zero": True,
            "resume_or_selective_rerun_allowed": False,
            "dev64_is_gate_not_primary_result": True,
            "all220_is_primary_result": True,
            "search_capacity_preflight_required": True,
            "full220_launch_allowed": False,
            "separate_executor_activation_required": True,
            "leaderboard_submission_or_sota_claim": False,
        }
        bundle["bundle_payload_sha256"] = payload_sha256(bundle)
        return bundle

    def validate_candidate(self, root: Path, bundle: dict, freeze: dict, capacity):
        return validate_candidate_bundle(
            root,
            bundle,
            bundle_path="results/bundle.json",
            bundle_sha256="b" * 64,
            capacity_path="results/capacity.json",
            capacity_sha256="f" * 64,
            capacity=capacity,
            capacity_freeze=freeze,
        )

    def test_exact_all220_compiles_fixed_parallel_waves(self) -> None:
        report, freeze, report_sha = self.capacity_pair()
        capacity = validate_capacity_pair(
            report, freeze, report_sha256=report_sha, protocol_sha256="p" * 64
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = self.candidate(root, freeze, workers=capacity["workers"])
            candidate = self.validate_candidate(root, bundle, freeze, capacity)
            plan = compile_parallel_plan(
                candidate,
                capacity,
                capacity_freeze_path="results/capacity.json",
                capacity_freeze_sha256="f" * 64,
            )
        self.assertEqual(plan["selected_total"], 220)
        self.assertEqual(plan["schedule"]["waves"], [[*EXPECTED_SHARDS[:2]], [*EXPECTED_SHARDS[2:]]])
        self.assertEqual(plan["schedule"]["worst_case_model_request_concurrency"], 4)
        self.assertFalse(plan["full220_launch_allowed"])
        self.assertTrue(plan["search_capacity_preflight_required"])
        self.assertTrue(plan["single_parent_shared_lease_owner_required"])

    def test_serial_capacity_compiles_four_single_shard_waves(self) -> None:
        report, freeze, report_sha = self.capacity_pair(serial=True)
        capacity = validate_capacity_pair(
            report, freeze, report_sha256=report_sha, protocol_sha256="p" * 64
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate = self.validate_candidate(
                root,
                self.candidate(root, freeze, workers=1),
                freeze,
                capacity,
            )
            plan = compile_parallel_plan(
                candidate,
                capacity,
                capacity_freeze_path="results/capacity.json",
                capacity_freeze_sha256="f" * 64,
            )
        self.assertEqual(plan["schedule"]["waves"], [[tag] for tag in EXPECTED_SHARDS])

    def test_resealed_capacity_summary_tamper_is_rejected(self) -> None:
        report, freeze, report_sha = self.capacity_pair()
        report["selected_model_request_concurrency"] = 1
        report["report_payload_sha256"] = payload_sha256(
            {key: value for key, value in report.items() if key != "report_payload_sha256"}
        )
        with self.assertRaisesRegex(RuntimeError, "summary"):
            validate_capacity_pair(
                report, freeze, report_sha256=report_sha, protocol_sha256="p" * 64
            )

    def test_candidate_worker_or_method_drift_is_rejected(self) -> None:
        report, freeze, report_sha = self.capacity_pair()
        capacity = validate_capacity_pair(
            report, freeze, report_sha256=report_sha, protocol_sha256="p" * 64
        )
        for mutate in ("worker", "pipeline"):
            with self.subTest(mutate=mutate), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                bundle = self.candidate(root, freeze, workers=capacity["workers"])
                tag = EXPECTED_SHARDS[-1]
                freeze_path = root / bundle["shards"][tag]["freeze"]["path"]
                value = json.loads(freeze_path.read_text(encoding="utf-8"))
                if mutate == "worker":
                    value["runtime"]["row_model_workers"] += 1
                else:
                    value["pipeline_version"] = "different"
                write_json(freeze_path, value)
                bundle["shards"][tag]["freeze"]["sha256"] = file_sha256(freeze_path)
                bundle["bundle_payload_sha256"] = payload_sha256(
                    {key: item for key, item in bundle.items() if key != "bundle_payload_sha256"}
                )
                with self.assertRaisesRegex(RuntimeError, "capacity binding|one frozen method"):
                    self.validate_candidate(root, bundle, freeze, capacity)

    def test_duplicate_partition_and_existing_output_are_rejected(self) -> None:
        report, freeze, report_sha = self.capacity_pair()
        capacity = validate_capacity_pair(
            report, freeze, report_sha256=report_sha, protocol_sha256="p" * 64
        )
        for mutate in ("duplicate", "output"):
            with self.subTest(mutate=mutate), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                bundle = self.candidate(root, freeze, workers=capacity["workers"])
                tag = EXPECTED_SHARDS[-1]
                if mutate == "duplicate":
                    ids_path = root / bundle["shards"][tag]["selected_ids"]["path"]
                    lines = ids_path.read_text(encoding="utf-8").splitlines()
                    lines[-1] = lines[-2]
                    ids_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
                    bundle["shards"][tag]["selected_ids"]["sha256"] = file_sha256(ids_path)
                else:
                    (root / bundle["shards"][tag]["output_directory"]).mkdir(parents=True)
                bundle["bundle_payload_sha256"] = payload_sha256(
                    {key: item for key, item in bundle.items() if key != "bundle_payload_sha256"}
                )
                with self.assertRaisesRegex(RuntimeError, "opaque-ID|not fresh"):
                    self.validate_candidate(root, bundle, freeze, capacity)

    def test_go_receipt_cannot_authorize_forward(self) -> None:
        report, freeze, report_sha = self.capacity_pair()
        capacity = validate_capacity_pair(
            report, freeze, report_sha256=report_sha, protocol_sha256="p" * 64
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = self.candidate(root, freeze, workers=capacity["workers"])
            go_path = root / bundle["candidate_quality_go_receipt"]["path"]
            go = json.loads(go_path.read_text(encoding="utf-8"))
            go["benchmark_forward_launch_allowed"] = True
            go["receipt_payload_sha256"] = payload_sha256(
                {key: value for key, value in go.items() if key != "receipt_payload_sha256"}
            )
            write_json(go_path, go)
            bundle["candidate_quality_go_receipt"]["sha256"] = file_sha256(go_path)
            bundle["bundle_payload_sha256"] = payload_sha256(
                {key: value for key, value in bundle.items() if key != "bundle_payload_sha256"}
            )
            with self.assertRaisesRegex(RuntimeError, "GO receipt"):
                self.validate_candidate(root, bundle, freeze, capacity)

    def test_evaluator_only_or_unknown_metadata_is_rejected(self) -> None:
        report, freeze, report_sha = self.capacity_pair()
        capacity = validate_capacity_pair(
            report, freeze, report_sha256=report_sha, protocol_sha256="p" * 64
        )
        for field in ("category", "innocent_unknown"):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                bundle = self.candidate(root, freeze, workers=capacity["workers"])
                bundle[field] = "forbidden"
                bundle["bundle_payload_sha256"] = payload_sha256(
                    {key: value for key, value in bundle.items() if key != "bundle_payload_sha256"}
                )
                with self.assertRaisesRegex(RuntimeError, "header|evaluator-only"):
                    self.validate_candidate(root, bundle, freeze, capacity)

    def test_candidate_freeze_cannot_point_to_credentials_or_evaluator(self) -> None:
        report, freeze, report_sha = self.capacity_pair()
        capacity = validate_capacity_pair(
            report, freeze, report_sha256=report_sha, protocol_sha256="p" * 64
        )
        for mutate in ("manifest_path", "credential_value"):
            with self.subTest(mutate=mutate), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                bundle = self.candidate(root, freeze, workers=capacity["workers"])
                tag = EXPECTED_SHARDS[0]
                freeze_path = root / bundle["shards"][tag]["freeze"]["path"]
                value = json.loads(freeze_path.read_text(encoding="utf-8"))
                if mutate == "manifest_path":
                    secret = root / ".env"
                    secret.write_text("SECRET", encoding="utf-8")
                    value["manifest"] = ".env"
                    value["manifest_sha256"] = file_sha256(secret)
                else:
                    value["model"]["credential"] = "tvly-dev-" + "A" * 24
                write_json(freeze_path, value)
                bundle["shards"][tag]["freeze"]["sha256"] = file_sha256(freeze_path)
                bundle["bundle_payload_sha256"] = payload_sha256(
                    {key: item for key, item in bundle.items() if key != "bundle_payload_sha256"}
                )
                with self.assertRaisesRegex(RuntimeError, "workspace path|credential-like"):
                    self.validate_candidate(root, bundle, freeze, capacity)

    def test_byte_snapshot_rejects_mid_read_identity_change(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "value.json"
            path.write_text("{}", encoding="utf-8")
            real_fstat = __import__("os").fstat
            calls = 0

            def drifting(descriptor):
                nonlocal calls
                value = real_fstat(descriptor)
                calls += 1
                if calls == 2:
                    from types import SimpleNamespace

                    return SimpleNamespace(
                        st_mode=value.st_mode,
                        st_dev=value.st_dev,
                        st_ino=value.st_ino,
                        st_size=value.st_size,
                        st_mtime_ns=value.st_mtime_ns + 1,
                    )
                return value

            with mock.patch(
                "deepwide_agent.v24197_parallel_all220.os.fstat",
                side_effect=drifting,
            ), self.assertRaisesRegex(RuntimeError, "changed during"):
                _bytes_snapshot(path)


if __name__ == "__main__":
    unittest.main()
