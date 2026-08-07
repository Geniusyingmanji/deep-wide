#!/usr/bin/env python3
"""Append-only transport successor for the V2.48.20 population freeze.

V2.48.20 produced no population artifact because a public World Bank bulk
snapshot exceeded the inherited 30-second read timeout.  This successor changes
only snapshot transport and output paths: up to three attempts per immutable URL,
a 90-second timeout per attempt, short bounded backoff, and content-free attempt
receipts.  Targets, rank, denominator, disjointness, privacy, and selection are
delegated unchanged to V2.48.20.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import (  # noqa: E402
    design_v24820_cell_disjoint_worldbank_population as parent,
)


DATE = parent.DATE
FAILURE_AUDIT = Path(
    f"results/v24821_v24820_population_zero_publication_failure_audit_v1_{DATE}.json"
)
AUTHORIZATION = Path(
    f"results/v24822_bounded_snapshot_transport_population_build_audit_v1_{DATE}.json"
)
PRIVATE = Path(
    f"evaluation/v24822_cell_disjoint_worldbank_population_private_v1_{DATE}.json"
)
OUTPUT = Path(
    f"results/v24822_cell_disjoint_worldbank_population_design_v1_{DATE}.json"
)
ATTEMPT_TIMEOUT_SECONDS = 90
MAX_ATTEMPTS = 3
BACKOFF_SECONDS = (0.5, 1.0)
MAX_RESPONSE_BYTES = 32 * 1024 * 1024

TARGETS = parent.TARGETS
TASK_SIZE = parent.TASK_SIZE
TASK_COUNT = parent.TASK_COUNT
SELECTED_COUNT = parent.SELECTED_COUNT


def payload_sha256(value: object) -> str:
    return parent.payload_sha256(value)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
        check=True,
    ).stdout.strip()


def _read(path: Path) -> dict[str, Any]:
    target = ROOT / path
    if (
        target.is_symlink()
        or not target.is_file()
        or not target.resolve().is_relative_to(ROOT.resolve())
    ):
        raise RuntimeError(f"V2.48.22 expected repository object: {path}")
    value = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.48.22 expected JSON object")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with (ROOT / path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def fetch_bytes_bounded(
    url: str,
    *,
    opener: Callable[..., Any] = urllib.request.urlopen,
    sleeper: Callable[[float], None] = time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
) -> tuple[bytes, dict[str, Any]]:
    """Fetch one immutable public URL with bounded, content-free receipts."""

    if not isinstance(url, str) or not url.startswith(
        "https://api.worldbank.org/"
    ):
        raise ValueError("V2.48.22 public snapshot URL drifted")
    attempts: list[dict[str, Any]] = []
    started = float(monotonic())
    for index in range(1, MAX_ATTEMPTS + 1):
        attempt_started = float(monotonic())
        status: int | None = None
        error_type: str | None = None
        retryable = False
        try:
            request = urllib.request.Request(
                url, headers={"User-Agent": "deepwide-v24822/1"}
            )
            with opener(request, timeout=ATTEMPT_TIMEOUT_SECONDS) as response:
                status = int(getattr(response, "status", 200))
                if status != 200:
                    raise urllib.error.HTTPError(
                        url, status, "unexpected status", {}, None
                    )
                raw = response.read(MAX_RESPONSE_BYTES + 1)
            if len(raw) == 0 or len(raw) > MAX_RESPONSE_BYTES:
                raise ValueError("V2.48.22 snapshot response size drifted")
            attempts.append(
                {
                    "attempt": index,
                    "status": status,
                    "outcome": "success",
                    "error_type": None,
                    "retryable": False,
                    "elapsed_seconds": round(
                        max(0.0, float(monotonic()) - attempt_started), 6
                    ),
                    "response_bytes": len(raw),
                    "response_sha256": hashlib.sha256(raw).hexdigest(),
                }
            )
            receipt = {
                "url_sha256": hashlib.sha256(url.encode()).hexdigest(),
                "attempt_timeout_seconds": ATTEMPT_TIMEOUT_SECONDS,
                "maximum_attempts": MAX_ATTEMPTS,
                "attempt_count": len(attempts),
                "attempts": attempts,
                "terminal_outcome": "success",
                "elapsed_seconds": round(
                    max(0.0, float(monotonic()) - started), 6
                ),
                "response_bytes": len(raw),
                "response_sha256": hashlib.sha256(raw).hexdigest(),
                "url_or_response_content_emitted": False,
            }
            receipt["receipt_sha256"] = payload_sha256(receipt)
            return raw, receipt
        except urllib.error.HTTPError as exc:
            status = int(exc.code)
            error_type = type(exc).__name__
            retryable = status in {408, 425, 429} or 500 <= status <= 599
        except (TimeoutError, socket.timeout, urllib.error.URLError) as exc:
            error_type = type(exc).__name__
            retryable = True
        attempts.append(
            {
                "attempt": index,
                "status": status,
                "outcome": "failure",
                "error_type": error_type,
                "retryable": retryable,
                "elapsed_seconds": round(
                    max(0.0, float(monotonic()) - attempt_started), 6
                ),
                "response_bytes": 0,
                "response_sha256": None,
            }
        )
        if not retryable or index == MAX_ATTEMPTS:
            break
        sleeper(BACKOFF_SECONDS[index - 1])
    raise RuntimeError(
        "V2.48.22 bounded public snapshot acquisition exhausted: "
        + payload_sha256(attempts)
    )


def build_artifacts(
    selected: list[Mapping[str, Any]],
    *,
    transport_receipts: list[Mapping[str, Any]],
    catalog_metadata: Mapping[str, Any],
    snapshot_metadata: list[Mapping[str, Any]],
    historical_manifest: Mapping[str, str],
    metrics: Mapping[str, Any],
    created_at: int,
    git_head: str,
    authorization_audit_sha256: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if (
        len(transport_receipts) != 3
        or any(
            receipt.get("terminal_outcome") != "success"
            or receipt.get("url_or_response_content_emitted") is not False
            for receipt in transport_receipts
        )
    ):
        raise ValueError("V2.48.22 transport receipt vector drifted")
    private, public = parent.build_artifacts(
        selected,
        authorization_audit_sha256=authorization_audit_sha256,
        catalog_metadata=catalog_metadata,
        snapshot_metadata=snapshot_metadata,
        historical_manifest=historical_manifest,
        metrics=metrics,
        created_at=created_at,
        git_head=git_head,
    )
    private = copy.deepcopy(private)
    public = copy.deepcopy(public)
    successor = {
        "predecessor": "v24820",
        "predecessor_failure_audit_sha256": _sha256(FAILURE_AUDIT),
        "only_change": "bounded_public_snapshot_transport_and_fresh_surfaces",
        "targets_selection_rank_denominator_disjointness_and_privacy_unchanged": True,
        "predecessor_population_or_task_vector_consumed": False,
        "same_predecessor_publication_retried_or_resumed": False,
    }
    private["role"] = (
        "v24822_cell_disjoint_worldbank_evaluator_only_population"
    )
    private["append_only_transport_successor"] = successor
    private.pop("private_payload_sha256")
    private["private_payload_sha256"] = payload_sha256(private)
    public["role"] = "v24822_cell_disjoint_worldbank_population_design"
    public["authorization_audit_sha256"] = authorization_audit_sha256
    public["append_only_transport_successor"] = successor
    public["transport"] = {
        "attempt_timeout_seconds": ATTEMPT_TIMEOUT_SECONDS,
        "maximum_attempts_per_url": MAX_ATTEMPTS,
        "maximum_response_bytes": MAX_RESPONSE_BYTES,
        "url_count": 3,
        "total_attempt_count": sum(
            int(receipt["attempt_count"]) for receipt in transport_receipts
        ),
        "receipts": [copy.deepcopy(dict(receipt)) for receipt in transport_receipts],
    }
    return private, public


def _authorized() -> bool:
    value = _read(AUTHORIZATION)
    return (
        value.get("role")
        == "v24822_bounded_snapshot_transport_population_build_audit"
        and value.get("audit_valid") is True
        and value.get("findings") == []
        and value.get("authorization", {}).get("one_population_publication")
        is True
        and value.get("authorization", {}).get("external_launch") is False
        and _sealed(value, "audit_payload_sha256")
    )


def _publish(path: Path, value: Mapping[str, Any]) -> None:
    target = ROOT / path
    if target.exists() or target.is_symlink():
        raise FileExistsError(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        target,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def main() -> None:
    if _git("status", "--porcelain") or _git("rev-parse", "HEAD") != _git(
        "rev-parse", "target/main"
    ):
        raise RuntimeError("V2.48.22 publication requires clean pushed HEAD")
    if not _authorized():
        raise RuntimeError("V2.48.22 publication is not authorized")
    if any(
        (ROOT / path).exists() or (ROOT / path).is_symlink()
        for path in (parent.PRIVATE, parent.OUTPUT, PRIVATE, OUTPUT)
    ):
        raise FileExistsError("V2.48.22 population surface is not pristine")
    entities, cells, targets, manifest = parent.historical_boundary()
    catalog_raw, catalog_receipt = fetch_bytes_bounded(
        parent.base.COUNTRY_CATALOG_URL
    )
    countries, catalog_metadata = parent.base.parse_country_catalog(catalog_raw)
    snapshots: list[dict[str, dict[str, Any]]] = []
    snapshot_metadata: list[dict[str, Any]] = []
    receipts: list[dict[str, Any]] = [catalog_receipt]
    for target in TARGETS:
        url = parent.base.indicator_url(target["indicator"], target["year"])
        raw, receipt = fetch_bytes_bounded(url)
        records, metadata = parent.base.parse_indicator_snapshot(
            raw,
            indicator=target["indicator"],
            year=target["year"],
            source_url=url,
        )
        snapshots.append(records)
        snapshot_metadata.append(metadata)
        receipts.append(receipt)
    selected, metrics = parent.select_population(
        countries, snapshots, entities, cells, targets
    )
    authorization_digest = _sha256(AUTHORIZATION)
    private, public = build_artifacts(
        selected,
        transport_receipts=receipts,
        catalog_metadata=catalog_metadata,
        snapshot_metadata=snapshot_metadata,
        historical_manifest=manifest,
        metrics=metrics,
        created_at=int(time.time()),
        git_head=_git("rev-parse", "HEAD"),
        authorization_audit_sha256=authorization_digest,
    )
    _publish(PRIVATE, private)
    public["private_population_file_sha256"] = hashlib.sha256(
        (ROOT / PRIVATE).read_bytes()
    ).hexdigest()
    public["design_payload_sha256"] = payload_sha256(public)
    _publish(OUTPUT, public)
    print(
        json.dumps(
            {
                "private": str(PRIVATE),
                "output": str(OUTPUT),
                "total_transport_attempts": public["transport"][
                    "total_attempt_count"
                ],
                **metrics,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
