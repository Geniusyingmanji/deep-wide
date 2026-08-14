#!/usr/bin/env python3
"""Execute the frozen V2.55.27 public IANA page-shape study once.

The study vector was committed and pushed before this effectful runner was
created.  It performs exactly one redirect-disabled public HTTPS GET for each
fixed URL, applies the production HTML extractor, and freezes the resulting
public text.  Failures remain in the fixed denominator and are never retried,
replaced, or backfilled.  No benchmark task, prediction, truth, evaluator,
model, search provider, credential, or API is opened.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import requests


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import native_search  # noqa: E402
from deepwide_agent import v25004_identity_bound_detail_fields as identity  # noqa: E402
from deepwide_agent import v25068_quote_verified_external_contract as watchers  # noqa: E402
from deepwide_agent import v25527_independent_iana_shape_study as contract  # noqa: E402


DATE = "20260814"
ROLE = "v25528_independent_iana_page_shape_snapshot"
OUTPUT = Path(f"results/v25528_independent_iana_shape_snapshot_v1_{DATE}.json")
CONTRACT_SOURCE = Path(
    "src/deepwide_agent/v25527_independent_iana_shape_study.py"
)
CONTRACT_COMMIT = "0459c6dce8d46c4aefbca52306fb1435f241e57f"
CONTRACT_SHA256 = (
    "24f8c993639e47d63bb692a87e6e801f0f1bd1b490a08c7f907eba7a6cec5dc6"
)
USER_AGENT = "DeepWideResearch/1.0 (+independent public IANA shape study)"


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
    history = set(_git("rev-list", "HEAD").splitlines())
    if (
        _git("status", "--porcelain", "--untracked-files=all")
        or head != target
        or CONTRACT_COMMIT not in history
        or _sha256(ROOT / CONTRACT_SOURCE) != CONTRACT_SHA256
    ):
        raise RuntimeError("V2.55.28 requires the clean pushed frozen study contract")
    return head


def _one(
    index: int,
    research_identity: str,
    url: str,
    *,
    get: Callable[..., Any],
) -> dict[str, Any]:
    status = 0
    raw = b""
    title = ""
    content = ""
    final_url = ""
    content_type = ""
    error: str | None = None
    try:
        response = get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=(
                contract.CONNECT_TIMEOUT_SECONDS,
                contract.READ_TIMEOUT_SECONDS,
            ),
            allow_redirects=False,
        )
        try:
            status = int(response.status_code)
            final_url = str(response.url or "")
            content_type = str(response.headers.get("Content-Type", ""))
            raw = bytes(response.content)
            if status != 200:
                error = f"http_{status}"
            elif final_url != url:
                error = "final_url_drifted"
            elif not raw:
                error = "empty_response"
            elif len(raw) > contract.MAXIMUM_RESPONSE_BYTES:
                error = "response_too_large"
            else:
                decoded = native_search.decode_web_text(
                    raw, getattr(response, "encoding", None)
                )
                title, content, _links = native_search.html_to_document(
                    decoded, url
                )
                content = content.replace("\x00", "").strip()
                if not content:
                    error = "empty_production_extraction"
        finally:
            response.close()
    except (requests.RequestException, OSError, RuntimeError, ValueError) as exc:
        error = type(exc).__name__.casefold()

    bound = bool(
        error is None
        and identity._page_identity_bound(
            {"title": title, "content": content}, research_identity
        )
    )
    if error is None and not bound:
        error = "identity_surface_unbound"
    valid = error is None
    return {
        "index": int(index),
        "identity": research_identity,
        "requested_url": url,
        "http_attempt_count": 1,
        "http_status": status,
        "final_url_exact": final_url == url,
        "content_type": content_type,
        "response_bytes": len(raw),
        "response_sha256": hashlib.sha256(raw).hexdigest() if raw else None,
        "production_extraction_valid": valid,
        "identity_surface_bound": bound,
        "title": title if valid else "",
        "content": content if valid else "",
        "content_sha256": hashlib.sha256(content.encode()).hexdigest()
        if valid
        else None,
        "line_count": len(content.splitlines()) if valid else 0,
        "pipe_line_count": sum(" | " in line for line in content.splitlines())
        if valid
        else 0,
        "error": error,
    }


def fetch_vector(
    *,
    get: Callable[..., Any] = requests.get,
    workers: int = 8,
) -> list[dict[str, Any]]:
    identities = contract.identity_vector()
    urls = contract.url_vector()
    if workers < 1 or workers > len(urls):
        raise ValueError("V2.55.28 worker count drifted")
    ordered: list[dict[str, Any] | None] = [None] * len(urls)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(_one, index, name, url, get=get): index
            for index, (name, url) in enumerate(
                zip(identities, urls, strict=True)
            )
        }
        for future in as_completed(futures):
            row = future.result()
            ordered[int(row["index"])] = row
    rows = [row for row in ordered if row is not None]
    if (
        len(rows) != len(urls)
        or [row["identity"] for row in rows] != identities
        or [row["requested_url"] for row in rows] != urls
        or any(row["http_attempt_count"] != 1 for row in rows)
    ):
        raise RuntimeError("V2.55.28 fixed fetch denominator drifted")
    return rows


def build_snapshot(
    rows: Sequence[Mapping[str, Any]],
    *,
    now: int | None = None,
    head: str = "test-head",
) -> dict[str, Any]:
    copied = [copy.deepcopy(dict(row)) for row in rows]
    identities = contract.identity_vector()
    urls = contract.url_vector()
    if (
        len(copied) != len(identities)
        or [row.get("index") for row in copied] != list(range(len(identities)))
        or [row.get("identity") for row in copied] != identities
        or [row.get("requested_url") for row in copied] != urls
        or any(row.get("http_attempt_count") != 1 for row in copied)
    ):
        raise ValueError("V2.55.28 snapshot rows drifted")
    aggregate = {
        "fixed_identity_count": len(identities),
        "http_attempt_count": sum(int(row["http_attempt_count"]) for row in copied),
        "http_200_count": sum(row.get("http_status") == 200 for row in copied),
        "final_url_exact_count": sum(row.get("final_url_exact") is True for row in copied),
        "production_extraction_valid_count": sum(
            row.get("production_extraction_valid") is True for row in copied
        ),
        "identity_surface_bound_count": sum(
            row.get("identity_surface_bound") is True for row in copied
        ),
        "total_response_bytes": sum(int(row.get("response_bytes", 0)) for row in copied),
        "total_extracted_characters": sum(len(str(row.get("content", ""))) for row in copied),
        "total_extracted_lines": sum(int(row.get("line_count", 0)) for row in copied),
        "total_pipe_lines": sum(int(row.get("pipe_line_count", 0)) for row in copied),
        "failed_count": sum(row.get("production_extraction_valid") is not True for row in copied),
    }
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "implementation_head": head,
        "frozen_contract_commit": CONTRACT_COMMIT,
        "frozen_contract_sha256": CONTRACT_SHA256,
        "manifest": contract.manifest(),
        "pages": copied,
        "aggregate": aggregate,
        "effect_receipt": {
            "ordinary_public_https_get_count": aggregate["http_attempt_count"],
            "search_model_fetch_provider_evaluator_benchmark_or_api_call_count": 0,
            "maximum_one_attempt_per_exact_url": True,
            "redirect_retry_refetch_replacement_backfill_or_selective_retention": False,
            "production_html_extractor_used": True,
            "v25525_task_rows_questions_pages_predictions_or_per_task_outcomes_read": False,
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read": False,
            "entropy_or_information_gain_assigns_signed_credit": False,
            "positive_signed_credit_count": 0,
        },
        "authorization": {
            "pure_mechanical_parser_build_from_this_research_snapshot_and_synthetic_fixtures": True,
            "reuse_research_identities_in_future_mechanism_or_quality_population": False,
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
    pages = copied.get("pages")
    aggregate = copied.get("aggregate")
    effect = copied.get("effect_receipt")
    valid_count = (
        sum(row.get("production_extraction_valid") is True for row in pages)
        if isinstance(pages, list)
        else -1
    )
    if (
        copied.get("role") != ROLE
        or copied.get("frozen_contract_commit") != CONTRACT_COMMIT
        or copied.get("frozen_contract_sha256") != CONTRACT_SHA256
        or copied.get("manifest") != contract.manifest()
        or not isinstance(pages, list)
        or len(pages) != len(contract.STUDY_IDENTITIES)
        or [row.get("index") for row in pages]
        != list(range(len(contract.STUDY_IDENTITIES)))
        or [row.get("identity") for row in pages] != contract.identity_vector()
        or [row.get("requested_url") for row in pages] != contract.url_vector()
        or any(row.get("http_attempt_count") != 1 for row in pages)
        or any(
            row.get("content_sha256")
            != (
                hashlib.sha256(str(row.get("content", "")).encode()).hexdigest()
                if row.get("production_extraction_valid") is True
                else None
            )
            for row in pages
        )
        or not isinstance(aggregate, Mapping)
        or aggregate.get("fixed_identity_count") != len(pages)
        or aggregate.get("http_attempt_count") != len(pages)
        or aggregate.get("production_extraction_valid_count") != valid_count
        or aggregate.get("failed_count") != len(pages) - valid_count
        or not isinstance(effect, Mapping)
        or effect.get("ordinary_public_https_get_count") != len(pages)
        or effect.get(
            "search_model_fetch_provider_evaluator_benchmark_or_api_call_count"
        )
        != 0
        or effect.get("maximum_one_attempt_per_exact_url") is not True
        or effect.get(
            "redirect_retry_refetch_replacement_backfill_or_selective_retention"
        )
        is not False
        or effect.get("positive_signed_credit_count") != 0
        or copied.get("authorization")
        != {
            "pure_mechanical_parser_build_from_this_research_snapshot_and_synthetic_fixtures": True,
            "reuse_research_identities_in_future_mechanism_or_quality_population": False,
            "external_mechanism_or_quality_forward": False,
            "deepwidebench_forward_or_evaluator": False,
            "leaderboard_or_sota": False,
        }
        or seal != contract.payload_sha256(unsigned)
    ):
        raise ValueError("V2.55.28 snapshot drifted")
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
    rows = fetch_vector()
    after = watchers.watcher_snapshot()
    if before != after:
        raise RuntimeError("V2.55.28 protected watcher identity drifted")
    value = build_snapshot(rows, head=head)
    _publish(value)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "aggregate": value["aggregate"],
                "authorization": value["authorization"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
