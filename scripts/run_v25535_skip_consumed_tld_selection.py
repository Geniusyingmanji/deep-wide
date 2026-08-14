#!/usr/bin/env python3
"""Run the frozen V2.55.34 skip-consumed name selection once."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import sys
import time
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

import requests


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25068_quote_verified_external_contract as watchers  # noqa: E402
from deepwide_agent import v25534_skip_consumed_tld_selection as contract  # noqa: E402


DATE = "20260814"
ROLE = "v25535_skip_consumed_tld_population_selection_snapshot"
OUTPUT = Path(f"results/v25535_skip_consumed_tld_selection_v1_{DATE}.json")
CONTRACT_SOURCE = Path(
    "src/deepwide_agent/v25534_skip_consumed_tld_selection.py"
)
CONTRACT_COMMIT = "6d7118901d1d9e1103a4f4b405923817ca019c36"
CONTRACT_SHA256 = (
    "c99b7a3d8fff9626acbc932533c4c5ed379800545e5a8fd9dc63dfaa1545ea6b"
)
USER_AGENT = "DeepWideResearch/1.0 (+skip-consumed official TLD name freeze)"


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=20,
        check=True,
    ).stdout.strip()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _clean_pushed() -> str:
    head = _git("rev-parse", "HEAD")
    target = _git("rev-parse", "target/main")
    if (
        _git("status", "--porcelain", "--untracked-files=all")
        or head != target
        or CONTRACT_COMMIT not in set(_git("rev-list", "HEAD").splitlines())
        or _sha256(ROOT / CONTRACT_SOURCE) != CONTRACT_SHA256
    ):
        raise RuntimeError("V2.55.35 requires clean pushed frozen selection contract")
    return head


def fetch_name_list(
    *, get: Callable[..., Any] = requests.get
) -> tuple[bytes, int, str, str | None]:
    response = get(
        contract.OFFICIAL_ENDPOINT,
        headers={"User-Agent": USER_AGENT},
        timeout=(
            contract.CONNECT_TIMEOUT_SECONDS,
            contract.READ_TIMEOUT_SECONDS,
        ),
        allow_redirects=False,
    )
    try:
        raw = bytes(response.content)
        status = int(response.status_code)
        final_url = str(response.url or "")
        encoding = getattr(response, "encoding", None)
    finally:
        response.close()
    if (
        status != 200
        or final_url != contract.OFFICIAL_ENDPOINT
        or not raw
        or len(raw) > contract.MAXIMUM_RESPONSE_BYTES
    ):
        raise RuntimeError("V2.55.35 official name-list response invalid")
    return raw, status, final_url, encoding


def build_snapshot(
    raw: bytes,
    *,
    status: int,
    final_url: str,
    encoding: str | None,
    now: int | None = None,
    head: str = "test-head",
) -> dict[str, Any]:
    if not isinstance(raw, bytes) or not raw:
        raise ValueError("V2.55.35 raw name list absent")
    text = raw.decode(encoding or "utf-8", errors="strict")
    names = contract.parse_official_names(text)
    selected = contract.selected_identities(names)
    pairs = contract.validate_pairs(
        [tuple(selected[index : index + 2]) for index in range(0, 40, 2)]
    )
    consumed = contract.consumed_identities()
    predecessor_index = names.index(contract.PREDECESSOR)
    last_index = names.index(selected[-1])
    scanned = names[predecessor_index + 1 : last_index + 1]
    skipped = [value for value in scanned if value in consumed]
    retained = [value for value in scanned if value not in consumed]
    if retained != selected:
        raise RuntimeError("V2.55.35 scan disposition drifted")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "implementation_head": head,
        "frozen_contract_commit": CONTRACT_COMMIT,
        "frozen_contract_sha256": CONTRACT_SHA256,
        "manifest": contract.manifest(),
        "official_snapshot": {
            "endpoint": contract.OFFICIAL_ENDPOINT,
            "http_attempt_count": 1,
            "http_status": int(status),
            "final_url_exact": final_url == contract.OFFICIAL_ENDPOINT,
            "response_bytes": len(raw),
            "response_sha256": hashlib.sha256(raw).hexdigest(),
            "version_header": text.splitlines()[0],
            "official_identity_count": len(names),
            "official_identity_vector_sha256": contract.payload_sha256(names),
            "predecessor_index": predecessor_index,
        },
        "selection": {
            "predecessor": contract.PREDECESSOR,
            "selected_identity_count": len(selected),
            "pair_count": len(pairs),
            "selected_identities": selected,
            "pairs": [list(pair) for pair in pairs],
            "selected_identity_vector_sha256": contract.payload_sha256(selected),
            "pair_vector_sha256": contract.payload_sha256(pairs),
            "consumed_identity_overlap_count": len(set(selected) & consumed),
            "scanned_suffix_identity_count": len(scanned),
            "skipped_consumed_identity_count": len(skipped),
            "skipped_consumed_identity_vector_sha256": contract.payload_sha256(skipped),
            "first_selected_identity": selected[0],
            "last_selected_identity": selected[-1],
            "first_forty_unconsumed_in_official_order": retained == selected,
        },
        "effect_receipt": {
            "ordinary_public_https_get_count": 1,
            "v25533_old_name_list_attempt_retried_or_reused": False,
            "search_model_detail_fetch_provider_evaluator_benchmark_or_api_call_count": 0,
            "redirect_retry_refetch_replacement_backfill_or_selective_retention": False,
            "detail_endpoint_page_field_value_question_prediction_quality_or_outcome_read": False,
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read": False,
            "entropy_or_information_gain_assigns_signed_credit": False,
            "positive_signed_credit_count": 0,
        },
        "authorization": {
            "materialize_selected_population_module": True,
            "external_mechanism_or_quality_forward": False,
            "deepwidebench_forward_or_evaluator": False,
            "leaderboard_or_sota": False,
        },
    }
    value["snapshot_payload_sha256"] = contract.payload_sha256(value)
    return validate_snapshot(value)


def validate_snapshot(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("snapshot_payload_sha256", None)
    snapshot = copied.get("official_snapshot")
    selection = copied.get("selection")
    effect = copied.get("effect_receipt")
    selected = selection.get("selected_identities") if isinstance(selection, Mapping) else None
    pairs = selection.get("pairs") if isinstance(selection, Mapping) else None
    if (
        copied.get("role") != ROLE
        or copied.get("frozen_contract_commit") != CONTRACT_COMMIT
        or copied.get("frozen_contract_sha256") != CONTRACT_SHA256
        or copied.get("manifest") != contract.manifest()
        or not isinstance(snapshot, Mapping)
        or snapshot.get("endpoint") != contract.OFFICIAL_ENDPOINT
        or snapshot.get("http_attempt_count") != 1
        or snapshot.get("http_status") != 200
        or snapshot.get("final_url_exact") is not True
        or not isinstance(snapshot.get("response_sha256"), str)
        or len(snapshot["response_sha256"]) != 64
        or not isinstance(snapshot.get("version_header"), str)
        or not snapshot["version_header"].startswith("# Version ")
        or not isinstance(selection, Mapping)
        or selection.get("predecessor") != contract.PREDECESSOR
        or selection.get("selected_identity_count")
        != contract.SELECTED_IDENTITY_COUNT
        or selection.get("pair_count") != contract.TASK_COUNT
        or not isinstance(selected, list)
        or len(selected) != contract.SELECTED_IDENTITY_COUNT
        or not isinstance(pairs, list)
        or contract.validate_pairs(pairs) != [tuple(pair) for pair in pairs]
        or [identity for pair in pairs for identity in pair] != selected
        or selection.get("selected_identity_vector_sha256")
        != contract.payload_sha256(selected)
        or selection.get("pair_vector_sha256")
        != contract.payload_sha256([tuple(pair) for pair in pairs])
        or selection.get("consumed_identity_overlap_count") != 0
        or not isinstance(selection.get("scanned_suffix_identity_count"), int)
        or selection["scanned_suffix_identity_count"]
        != contract.SELECTED_IDENTITY_COUNT
        + selection.get("skipped_consumed_identity_count", -1)
        or not isinstance(selection.get("skipped_consumed_identity_count"), int)
        or selection["skipped_consumed_identity_count"] < 0
        or not isinstance(
            selection.get("skipped_consumed_identity_vector_sha256"), str
        )
        or len(selection["skipped_consumed_identity_vector_sha256"]) != 64
        or selection.get("first_selected_identity") != selected[0]
        or selection.get("last_selected_identity") != selected[-1]
        or selection.get("first_forty_unconsumed_in_official_order") is not True
        or not isinstance(effect, Mapping)
        or effect.get("ordinary_public_https_get_count") != 1
        or effect.get("v25533_old_name_list_attempt_retried_or_reused") is not False
        or effect.get(
            "search_model_detail_fetch_provider_evaluator_benchmark_or_api_call_count"
        )
        != 0
        or effect.get(
            "redirect_retry_refetch_replacement_backfill_or_selective_retention"
        )
        is not False
        or effect.get("positive_signed_credit_count") != 0
        or copied.get("authorization")
        != {
            "materialize_selected_population_module": True,
            "external_mechanism_or_quality_forward": False,
            "deepwidebench_forward_or_evaluator": False,
            "leaderboard_or_sota": False,
        }
        or seal != contract.payload_sha256(unsigned)
    ):
        raise ValueError("V2.55.35 selection snapshot drifted")
    return copied


def _publish(value: Mapping[str, Any]) -> None:
    path = ROOT / OUTPUT
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def main() -> None:
    head = _clean_pushed()
    if (ROOT / OUTPUT).exists() or (ROOT / OUTPUT).is_symlink():
        raise FileExistsError(ROOT / OUTPUT)
    before = watchers.watcher_snapshot()
    raw, status, final_url, encoding = fetch_name_list()
    after = watchers.watcher_snapshot()
    if before != after:
        raise RuntimeError("V2.55.35 protected watcher identity drifted")
    value = build_snapshot(
        raw,
        status=status,
        final_url=final_url,
        encoding=encoding,
        head=head,
    )
    _publish(value)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "selection": value["selection"],
                "authorization": value["authorization"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
