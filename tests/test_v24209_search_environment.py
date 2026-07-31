from __future__ import annotations

import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24209_search_environment import (  # noqa: E402
    ANTHROPIC_CITATION_POLICY,
    ANTHROPIC_CREDENTIAL_POLICY,
    ANTHROPIC_QUERY_POLICY,
    EXPECTED_COUNTS,
    EXPECTED_SHARDS,
    build_all220_environment_attestation,
    build_search_environment_contract,
    compile_environment_bound_prelaunch,
    payload_sha256,
    validate_search_environment_contract,
)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")


class V24209SearchEnvironmentTests(unittest.TestCase):
    def make_root(
        self,
        *,
        provider: str = "anthropic",
    ) -> tuple[tempfile.TemporaryDirectory[str], Path, dict[str, dict[str, str]]]:
        directory = tempfile.TemporaryDirectory()
        root = Path(directory.name)
        source_payloads = {
            "src/deepwide_agent/clients.py": "CLIENT = 1\n",
            "src/deepwide_agent/native_search.py": "NATIVE = 1\n",
            "src/deepwide_agent/anthropic_search.py": "ANTHROPIC = 1\n",
            "src/deepwide_agent/runtime.py": "RUNTIME = 1\n",
            "scripts/run_deepwide_agent.py": "RUNNER = 1\n",
            "scripts/launch_frozen_deepwide.py": "LAUNCHER = 1\n",
        }
        for relative, payload in source_payloads.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(payload, encoding="utf-8")
        code = {
            relative: file_sha256(root / relative)
            for relative in source_payloads
        }
        if provider == "anthropic":
            search = {
                "provider": "anthropic",
                "model": "claude-haiku-4-5-20251001",
                "timeout_seconds": 180,
                "max_retries": 5,
                "results_per_query": 8,
                "max_uses": 2,
                "max_output_tokens": 1400,
                "fetch_pages": True,
                "fetch_workers": 4,
                "fetch_timeout": 45,
                "workers": 2,
                "query_policy": ANTHROPIC_QUERY_POLICY,
                "citation_policy": ANTHROPIC_CITATION_POLICY,
                "credential_policy": ANTHROPIC_CREDENTIAL_POLICY,
            }
        elif provider == "azure-native":
            search = {
                "provider": "azure-native",
                "context_size": "medium",
                "results_per_query": 8,
                "batch_size": 6,
                "max_output_tokens": 5000,
                "fetch_pages": True,
                "fetch_workers": 4,
                "fetch_timeout": 45,
                "workers": 6,
                "citation_policy": (
                    "query-local URL citation only; citation text is a lead and "
                    "cannot satisfy page-evidence gates"
                ),
                "page_policy": (
                    "public HTTP(S) only; redirect revalidation; HTML/PDF direct extraction"
                ),
            }
        else:
            search = {
                "provider": "tavily",
                "depth": "advanced",
                "results_per_query": 8,
                "include_raw_content": True,
                "workers": 6,
            }

        references: dict[str, dict[str, str]] = {}
        for tag in EXPECTED_SHARDS:
            path = root / f"configs/candidate/{tag}.json"
            freeze = {
                "pipeline_version": "v2.future",
                "state_schema_version": 99,
                "selected_count": EXPECTED_COUNTS[tag],
                "selected_ids_sha256": hashlib.sha256(tag.encode()).hexdigest(),
                "code_sha256": code,
                "model": {
                    "proxy_url": "http://127.0.0.1:9878/responses",
                    "name": "gpt-5.6-sol",
                },
                "search": search,
            }
            write_json(path, freeze)
            references[tag] = {
                "path": str(path.relative_to(root)),
                "sha256": file_sha256(path),
            }
        return directory, root, references

    def make_plan(
        self,
        attestation: dict,
        *,
        width: int = 2,
    ) -> dict:
        waves = [
            list(EXPECTED_SHARDS[index : index + width])
            for index in range(0, len(EXPECTED_SHARDS), width)
        ]
        plan = {
            "artifact_version": 1,
            "role": "v24197_capacity_bound_fresh_all220_parallel_plan",
            "label_blind": True,
            "candidate_bundle": {"path": "results/bundle.json", "sha256": "c" * 64},
            "capacity_freeze": {"path": "results/capacity.json", "sha256": "d" * 64},
            "target_name": "fresh_all220_v1",
            "pipeline_version": "v2.future",
            "state_schema_version": 99,
            "candidate_method_contract_sha256": "e" * 64,
            "opaque_partition_sha256": "f" * 64,
            "shards": {
                tag: {
                    "freeze": copy.deepcopy(attestation["shards"][tag]["freeze"]),
                    "selected_ids": {
                        "path": f"configs/candidate/{tag}.ids",
                        "sha256": attestation["shards"][tag]["selected_ids_sha256"],
                        "count": EXPECTED_COUNTS[tag],
                    },
                    "output_directory": f"outputs/fresh/{tag}",
                }
                for tag in EXPECTED_SHARDS
            },
            "schedule": {
                "model_request_concurrency_cap": 8,
                "parallel_shards": width,
                "candidate_model_workers_per_shard": 4,
                "row_model_workers_per_shard": 4,
                "worst_case_model_request_concurrency": width * 4,
                "waves": waves,
                "fixed_for_entire_all220": True,
            },
            "selected_total": 220,
            "new_output_roots_required": True,
            "resume_or_selective_rerun_allowed": False,
            "forward_failure_scored_as_zero": True,
            "search_capacity_preflight_required": True,
            "full220_launch_allowed": False,
            "separate_identity_bound_executor_activation_required": True,
            "single_parent_shared_lease_owner_required": True,
            "leaderboard_submission_or_sota_claim": False,
        }
        plan["plan_payload_sha256"] = payload_sha256(plan)
        return plan

    def compile(self, plan: dict, attestation: dict) -> dict:
        return compile_environment_bound_prelaunch(
            plan,
            attestation,
            plan_path="results/plan.json",
            plan_sha256="a" * 64,
            attestation_path="results/environment.json",
            attestation_sha256="b" * 64,
        )

    def test_four_shards_bind_one_live_web_environment_without_launch(self) -> None:
        directory, root, references = self.make_root()
        with directory:
            attestation = build_all220_environment_attestation(root, references)
            prelaunch = self.compile(self.make_plan(attestation), attestation)
        environment = attestation["search_environment"]
        self.assertEqual(attestation["selected_total"], 220)
        self.assertTrue(attestation["one_environment_across_all_shards"])
        self.assertFalse(attestation["provider_index_snapshot_pinned"])
        self.assertEqual(environment["provider"]["tool_schema"], "web_search_20250305")
        self.assertEqual(
            environment["provider"]["endpoint"],
            "https://api.anthropic.com/v1/messages",
        )
        self.assertEqual(
            environment["corpus"]["reproducibility_class"],
            "provider_managed_live_index_not_exactly_replayable",
        )
        self.assertFalse(prelaunch["benchmark_forward_or_full220_launch_allowed"])
        self.assertTrue(prelaunch["fixed_concurrency_for_entire_all220"])
        self.assertTrue(prelaunch["forward_failure_scored_as_zero"])
        self.assertFalse(prelaunch["resume_or_selective_rerun_allowed"])

    def test_provider_config_or_adapter_drift_fails_closed(self) -> None:
        for mutation in ("search", "adapter"):
            with self.subTest(mutation=mutation):
                directory, root, references = self.make_root()
                with directory:
                    tag = EXPECTED_SHARDS[-1]
                    freeze_path = root / references[tag]["path"]
                    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
                    if mutation == "search":
                        freeze["search"]["results_per_query"] = 9
                        write_json(freeze_path, freeze)
                    else:
                        adapter = root / "src/deepwide_agent/anthropic_search.py"
                        adapter.write_text("ANTHROPIC = 2\n", encoding="utf-8")
                    references[tag]["sha256"] = file_sha256(freeze_path)
                    with self.assertRaisesRegex(
                        RuntimeError,
                        "not identical|source bytes drifted|environment source bytes drifted",
                    ):
                        build_all220_environment_attestation(root, references)

    def test_sensitive_or_unknown_search_metadata_is_rejected_recursively(self) -> None:
        directory, root, references = self.make_root()
        with directory:
            freeze = json.loads((root / references[EXPECTED_SHARDS[0]]["path"]).read_text())
            for key, value in (
                ("question_type", "wide"),
                ("credential", "tvly" + "-dev-" + "A" * 24),
                ("innocent_unknown", "x"),
            ):
                with self.subTest(key=key):
                    candidate = copy.deepcopy(freeze)
                    candidate["search"][key] = value
                    with self.assertRaisesRegex(
                        RuntimeError, "credential key|schema drifted"
                    ):
                        build_search_environment_contract(candidate)

    def test_resealed_endpoint_tool_schema_or_snapshot_tamper_is_rejected(self) -> None:
        directory, root, references = self.make_root()
        with directory:
            freeze = json.loads((root / references[EXPECTED_SHARDS[0]]["path"]).read_text())
            original = build_search_environment_contract(freeze)
            for mutation in ("endpoint", "tool", "snapshot"):
                with self.subTest(mutation=mutation):
                    value = copy.deepcopy(original)
                    if mutation == "endpoint":
                        value["provider"]["endpoint"] = "https://example.com/messages"
                    elif mutation == "tool":
                        value["provider"]["tool_schema"] = "other_tool"
                    else:
                        value["corpus"]["snapshot_pinned"] = True
                    value["environment_fingerprint_sha256"] = payload_sha256(
                        {
                            key: item
                            for key, item in value.items()
                            if key != "environment_fingerprint_sha256"
                        }
                    )
                    with self.assertRaisesRegex(
                        RuntimeError,
                        "endpoint drifted|provider identity drifted|inputs drifted",
                    ):
                        validate_search_environment_contract(value)

    def test_resealed_attestation_unknown_or_sensitive_metadata_is_rejected(self) -> None:
        directory, root, references = self.make_root()
        with directory:
            original = build_all220_environment_attestation(root, references)
            for key, value in (
                ("question_type", "wide"),
                ("innocent_unknown", "x"),
            ):
                with self.subTest(key=key):
                    attestation = copy.deepcopy(original)
                    attestation[key] = value
                    attestation["attestation_payload_sha256"] = payload_sha256(
                        {
                            name: item
                            for name, item in attestation.items()
                            if name != "attestation_payload_sha256"
                        }
                    )
                    plan = self.make_plan(original)
                    with self.assertRaisesRegex(RuntimeError, "attestation is invalid"):
                        self.compile(plan, attestation)

    def test_plan_must_remain_exact220_fixed_no_resume_failure_zero(self) -> None:
        directory, root, references = self.make_root()
        with directory:
            attestation = build_all220_environment_attestation(root, references)
            for mutation in (
                "resume",
                "failure",
                "fixed",
                "waves",
                "launch",
                "pipeline",
                "output",
                "freeze_path",
            ):
                with self.subTest(mutation=mutation):
                    plan = self.make_plan(attestation)
                    if mutation == "resume":
                        plan["resume_or_selective_rerun_allowed"] = True
                    elif mutation == "failure":
                        plan["forward_failure_scored_as_zero"] = False
                    elif mutation == "fixed":
                        plan["schedule"]["fixed_for_entire_all220"] = False
                    elif mutation == "waves":
                        plan["schedule"]["waves"][-1].pop()
                    elif mutation == "launch":
                        plan["full220_launch_allowed"] = True
                    elif mutation == "pipeline":
                        plan["pipeline_version"] = "v2.other"
                    elif mutation == "output":
                        plan["shards"][EXPECTED_SHARDS[-1]]["output_directory"] = (
                            plan["shards"][EXPECTED_SHARDS[0]]["output_directory"]
                        )
                    else:
                        plan["shards"][EXPECTED_SHARDS[-1]]["freeze"]["path"] = (
                            "../escape.json"
                        )
                    plan["plan_payload_sha256"] = payload_sha256(
                        {
                            key: item
                            for key, item in plan.items()
                            if key != "plan_payload_sha256"
                        }
                    )
                    with self.assertRaisesRegex(
                        RuntimeError,
                        "plan boundary|fixed|waves|method identities|freeze references|reference is invalid",
                    ):
                        self.compile(plan, attestation)

    def test_freeze_path_hash_and_environment_code_closure_are_fail_closed(self) -> None:
        for mutation in ("hash", "path", "closure"):
            with self.subTest(mutation=mutation):
                directory, root, references = self.make_root()
                with directory:
                    tag = EXPECTED_SHARDS[0]
                    if mutation == "hash":
                        references[tag]["sha256"] = "0" * 64
                    elif mutation == "path":
                        references[tag]["path"] = "../outside.json"
                    else:
                        freeze_path = root / references[tag]["path"]
                        freeze = json.loads(freeze_path.read_text())
                        del freeze["code_sha256"]["src/deepwide_agent/native_search.py"]
                        write_json(freeze_path, freeze)
                        references[tag]["sha256"] = file_sha256(freeze_path)
                    with self.assertRaises(RuntimeError):
                        build_all220_environment_attestation(root, references)

    def test_supported_provider_contracts_are_explicit(self) -> None:
        for provider, identity in (
            ("anthropic", "anthropic-server-web-search"),
            ("azure-native", "azure-responses-web-search"),
            ("tavily", "tavily-search-api"),
        ):
            with self.subTest(provider=provider):
                directory, root, references = self.make_root(provider=provider)
                with directory:
                    freeze = json.loads(
                        (root / references[EXPECTED_SHARDS[0]]["path"]).read_text()
                    )
                    contract = build_search_environment_contract(freeze)
                    self.assertEqual(contract["provider"]["runtime_identity"], identity)
                    self.assertFalse(contract["corpus"]["snapshot_pinned"])


if __name__ == "__main__":
    unittest.main()
