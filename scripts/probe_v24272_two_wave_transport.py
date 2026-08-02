#!/usr/bin/env python3
"""Run one neutral, content-free V2.42.72 transport latency probe."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.native_search import AzureNativeSearchClient  # noqa: E402
from deepwide_agent.v24272_two_wave_entropy_voc import (  # noqa: E402
    TwoWavePolicy,
    object_sha256,
)
from deepwide_agent.v24272_two_wave_retrieval import (  # noqa: E402
    run_two_wave_retrieval,
    validate_retrieval_receipt,
)
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402
from scripts.run_v24257_score_first_smoke import sha256  # noqa: E402


OUTPUT = Path("results/v24272_neutral_two_wave_transport_probe_v1_20260802.json")
NEUTRAL_QUERIES = (
    "Python 3.13 official release notes",
    "Python 3.13 official documentation what's new",
    "Python 3.13 official release schedule PEP",
    "Python 3.13 official download documentation",
)
CLIENT_COUNTERS = (
    "calls",
    "failures",
    "tool_calls",
    "fetch_calls",
    "fetch_failures",
    "input_tokens",
    "output_tokens",
    "total_tokens",
)
RESULT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "created_at_unix",
        "probe_scope",
        "provider",
        "model",
        "reasoning_effort",
        "neutral_query_count",
        "wall_seconds",
        "client_counters",
        "retrieval_receipt",
        "source_policy",
        "authorization",
        "result_payload_sha256",
    }
)


def _counter_snapshot(client: Any) -> dict[str, int]:
    return {
        name: max(0, int(getattr(client, name, 0) or 0))
        for name in CLIENT_COUNTERS
    }


def _publish_new(path: Path, value: dict[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    parent = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(parent)
    finally:
        os.close(parent)


def validate_result(value: dict[str, Any]) -> None:
    source = value.get("source_policy")
    authorization = value.get("authorization")
    counters = value.get("client_counters")
    receipt = value.get("retrieval_receipt")
    unsigned = dict(value)
    seal = unsigned.pop("result_payload_sha256", None)
    if (
        set(value) != RESULT_KEYS
        or value.get("artifact_version") != 1
        or value.get("role") != "v24272_neutral_two_wave_transport_probe"
        or value.get("probe_scope")
        != "neutral_public_documentation_transport_latency_only"
        or value.get("provider") != "azure-native-keyless-batched"
        or value.get("model") != "gpt-5.6-sol"
        or value.get("reasoning_effort") != "low"
        or value.get("neutral_query_count") != len(NEUTRAL_QUERIES)
        or not isinstance(value.get("wall_seconds"), (int, float))
        or isinstance(value.get("wall_seconds"), bool)
        or float(value["wall_seconds"]) < 0
        or not isinstance(counters, dict)
        or set(counters) != set(CLIENT_COUNTERS)
        or any(
            isinstance(counters[name], bool)
            or not isinstance(counters[name], int)
            or counters[name] < 0
            for name in CLIENT_COUNTERS
        )
        or not isinstance(receipt, dict)
        or not isinstance(source, dict)
        or source.get("benchmark_manifest_mapping_gold_prediction_or_evaluator_read")
        is not False
        or source.get("query_url_host_page_or_answer_persisted") is not False
        or source.get("credential_value_read_persisted_hashed_or_emitted") is not False
        or source.get("official_evaluator_called") is not False
        or source.get("shared_api_lease_acquired") is not True
        or not isinstance(authorization, dict)
        or any(authorization.values())
        or seal != object_sha256(unsigned)
    ):
        raise RuntimeError("V2.42.72 neutral transport probe drifted")
    validate_retrieval_receipt(receipt)
    total = receipt["total"]
    if (
        counters["fetch_calls"] != total["fetches_attempted"]
        or counters["failures"] < counters["fetch_failures"]
        or total["queries_executed"] > 4
        or total["fetches_attempted"] > 10
    ):
        raise RuntimeError("V2.42.72 neutral transport probe accounting drifted")


def run_probe(
    root: Path = ROOT,
    *,
    output: Path = OUTPUT,
    proxy_url: str = "http://127.0.0.1:9878/responses",
) -> dict[str, Any]:
    root = root.resolve()
    if output.is_absolute() or ".." in output.parts:
        raise ValueError("V2.42.72 probe output must be repository-relative")
    client = AzureNativeSearchClient(
        proxy_url,
        "gpt-5.6-sol",
        reasoning_effort="low",
        service_tier="priority",
        timeout=180,
        max_retries=2,
        max_workers=1,
        batch_size=8,
        search_context_size="medium",
        max_output_tokens=7_000,
        fetch_pages=False,
        fetch_workers=8,
        fetch_timeout=20,
        max_page_chars=5_000,
    )
    started = time.monotonic()
    with acquire_deepwide_api_lease(
        root,
        owner="v24272_neutral_two_wave_transport_probe_v1",
        purpose="neutral_nonbenchmark_two_wave_latency_probe",
    ):
        retrieval = run_two_wave_retrieval(
            NEUTRAL_QUERIES,
            search=client,
            required_column_count=3,
            explicit_row_target=0,
            search_results_per_query=3,
            policy=TwoWavePolicy(),
        )
    value = {
        "artifact_version": 1,
        "role": "v24272_neutral_two_wave_transport_probe",
        "created_at_unix": int(time.time()),
        "probe_scope": "neutral_public_documentation_transport_latency_only",
        "provider": "azure-native-keyless-batched",
        "model": "gpt-5.6-sol",
        "reasoning_effort": "low",
        "neutral_query_count": len(NEUTRAL_QUERIES),
        "wall_seconds": round(max(0.0, time.monotonic() - started), 6),
        "client_counters": _counter_snapshot(client),
        "retrieval_receipt": retrieval["receipt"],
        "source_policy": {
            "benchmark_manifest_mapping_gold_prediction_or_evaluator_read": False,
            "query_url_host_page_or_answer_persisted": False,
            "credential_value_read_persisted_hashed_or_emitted": False,
            "official_evaluator_called": False,
            "shared_api_lease_acquired": True,
        },
        "authorization": {
            "dev_benchmark_launch": False,
            "exact220_launch": False,
            "leaderboard_submission": False,
            "sota_claim": False,
            "training_credit_assignment": False,
        },
    }
    value["result_payload_sha256"] = object_sha256(value)
    validate_result(value)
    _publish_new(root / output, value)
    return value


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--output", default=str(OUTPUT))
    parser.add_argument("--proxy-url", default="http://127.0.0.1:9878/responses")
    args = parser.parse_args()
    result = run_probe(
        Path(args.root), output=Path(args.output), proxy_url=args.proxy_url
    )
    print(
        json.dumps(
            {
                "path": str(args.output),
                "sha256": sha256(Path(args.root).resolve() / args.output),
                "wall_seconds": result["wall_seconds"],
                "decision": result["retrieval_receipt"]["controller"]["decision"],
                "queries_executed": result["retrieval_receipt"]["total"][
                    "queries_executed"
                ],
                "fetches_attempted": result["retrieval_receipt"]["total"][
                    "fetches_attempted"
                ],
            },
            sort_keys=True,
        )
    )
