"""Pure contracts for the V2.42.18 single-owner exact-220 executor.

The forward boundary is deliberately small: an opaque task ID, its visible
question, and evidence produced during that task.  Package selection and
capacity are frozen by prior aggregate gates; no benchmark category, mapping,
gold answer, evaluator row, or per-task score is accepted here.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable, Mapping


EXPECTED_SHARDS = ("test_s01", "test_s02", "test_s03", "devval")
EXPECTED_COUNTS = {
    "test_s01": 52,
    "test_s02": 52,
    "test_s03": 52,
    "devval": 64,
}
CANONICAL_ALL220_SHA256 = (
    "cace8746d5a817a467e7cb70e715ee599a242cc88ce4474802b9d93a9221082b"
)
OPAQUE_ID = re.compile(r"task_[0-9a-f]{24}")
SHA256 = re.compile(r"[0-9a-f]{64}")


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def validate_identity(value: object, *, name: str) -> dict[str, str]:
    if not isinstance(value, Mapping) or set(value) != {"path", "sha256"}:
        raise RuntimeError(f"V2.42.18 {name} identity is malformed")
    path = value.get("path")
    digest = value.get("sha256")
    if (
        not isinstance(path, str)
        or not path
        or Path(path).is_absolute()
        or ".." in Path(path).parts
        or not isinstance(digest, str)
        or SHA256.fullmatch(digest) is None
    ):
        raise RuntimeError(f"V2.42.18 {name} identity is invalid")
    return {"path": path, "sha256": digest}


def read_opaque_ids(path: Path, expected: int) -> list[str]:
    values = [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if (
        len(values) != expected
        or len(set(values)) != expected
        or any(OPAQUE_ID.fullmatch(value) is None for value in values)
    ):
        raise RuntimeError("V2.42.18 shard is not an exact opaque-ID list")
    return values


def validate_exact_partition(rows: Mapping[str, Iterable[str]]) -> str:
    if set(rows) != set(EXPECTED_SHARDS):
        raise RuntimeError("V2.42.18 shard topology drifted")
    flattened: list[str] = []
    for tag in EXPECTED_SHARDS:
        values = list(rows[tag])
        if (
            len(values) != EXPECTED_COUNTS[tag]
            or len(set(values)) != EXPECTED_COUNTS[tag]
            or any(OPAQUE_ID.fullmatch(value) is None for value in values)
        ):
            raise RuntimeError("V2.42.18 shard count or opaque ID drifted")
        flattened.extend(values)
    if len(flattened) != 220 or len(set(flattened)) != 220:
        raise RuntimeError("V2.42.18 partition is not disjoint exact-220")
    digest = payload_sha256(sorted(flattened))
    if digest != CANONICAL_ALL220_SHA256:
        raise RuntimeError("V2.42.18 partition is not the canonical all-220")
    return digest


def compile_schedule(capacity: Mapping[str, Any]) -> dict[str, Any]:
    selected = capacity.get("selected")
    workers = capacity.get("workers")
    shard_cap = capacity.get("shards")
    if any(
        isinstance(value, bool) or not isinstance(value, int) or value <= 0
        for value in (selected, workers, shard_cap)
    ):
        raise RuntimeError("V2.42.18 cannot schedule from capacity NO-GO")
    width = min(len(EXPECTED_SHARDS), int(shard_cap))
    if width * int(workers) > int(selected):
        raise RuntimeError("V2.42.18 schedule exceeds model capacity")
    waves = [
        list(EXPECTED_SHARDS[index : index + width])
        for index in range(0, len(EXPECTED_SHARDS), width)
    ]
    return {
        "executor_concurrency": width,
        "agent_width": 1,
        "candidate_model_workers_per_task": int(workers),
        "row_model_workers_per_task": int(workers),
        "model_request_concurrency_cap": int(selected),
        "worst_case_model_request_concurrency": width * int(workers),
        "waves": waves,
        "fixed_for_entire_exact220": True,
    }


def validate_terminal_shard(
    *,
    tag: str,
    ids: list[str],
    runtime_rows: list[dict[str, Any]],
    summary: Mapping[str, Any],
) -> dict[str, int]:
    if tag not in EXPECTED_COUNTS or len(ids) != EXPECTED_COUNTS[tag]:
        raise RuntimeError("V2.42.18 terminal shard identity drifted")
    by_id: dict[str, dict[str, Any]] = {}
    for row in runtime_rows:
        opaque_id = row.get("opaque_id") if isinstance(row, dict) else None
        if not isinstance(opaque_id, str) or opaque_id in by_id:
            raise RuntimeError("V2.42.18 runtime envelope IDs are invalid")
        by_id[opaque_id] = row
    completed = summary.get("completed")
    failed = summary.get("failed")
    if (
        set(by_id) != set(ids)
        or summary.get("selected") != len(ids)
        or isinstance(completed, bool)
        or not isinstance(completed, int)
        or isinstance(failed, bool)
        or not isinstance(failed, int)
        or completed + failed != len(ids)
        or any(row.get("status") not in {"completed", "failed"} for row in by_id.values())
        or sum(row.get("status") == "completed" for row in by_id.values()) != completed
        or any(
            row.get("status") == "completed"
            and not str(row.get("prediction", "")).strip()
            for row in by_id.values()
        )
    ):
        raise RuntimeError("V2.42.18 shard is not exact terminal")
    return {"selected": len(ids), "completed": completed, "failed": failed}


def _normalized(value: object) -> str:
    return " ".join(str(value or "").casefold().split())


def evidence_width(evidence: object) -> dict[str, int]:
    """Count de-duplicated evidence dimensions without returning content."""

    rows = evidence if isinstance(evidence, list) else []
    queries: set[str] = set()
    urls: set[str] = set()
    contents: set[str] = set()
    sources: set[str] = set()
    evidence_sets: set[tuple[str, str, str]] = set()
    for raw in rows:
        if not isinstance(raw, Mapping):
            continue
        raw_queries = raw.get("queries")
        if not isinstance(raw_queries, list):
            raw_queries = [raw.get("query")]
        for query in raw_queries:
            normalized = _normalized(query)
            if normalized:
                queries.add(normalized)
        url = _normalized(raw.get("url"))
        if url:
            urls.add(url)
        fingerprint = _normalized(
            raw.get("content_fingerprint") or raw.get("fingerprint")
        )
        if not fingerprint:
            text = _normalized(raw.get("text") or raw.get("raw_content"))
            if text:
                fingerprint = hashlib.sha256(text.encode()).hexdigest()
        if fingerprint:
            contents.add(fingerprint)
        source = _normalized(raw.get("source_family") or raw.get("provider"))
        if source:
            sources.add(source)
        evidence_sets.add((url, fingerprint, source))
    evidence_sets.discard(("", "", ""))
    return {
        "raw_evidence_items": len(rows),
        "unique_query_intents": len(queries),
        "unique_urls": len(urls),
        "unique_content_fingerprints": len(contents),
        "unique_source_dependencies": len(sources),
        "effective_evidence_width": len(evidence_sets),
    }


def aggregate_evidence_width(task_states: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    rows = [evidence_width(state.get("evidence")) for state in task_states]
    fields = (
        "raw_evidence_items",
        "unique_query_intents",
        "unique_urls",
        "unique_content_fingerprints",
        "unique_source_dependencies",
        "effective_evidence_width",
    )
    total = len(rows)
    return {
        "task_count": total,
        "definition": (
            "per-task unique (normalized URL, content fingerprint, source dependency); "
            "query intents, URLs, contents, and sources are also reported separately"
        ),
        "totals": {field: sum(row[field] for row in rows) for field in fields},
        "means": {
            field: (sum(row[field] for row in rows) / total if total else 0.0)
            for field in fields
        },
        "post_terminal_task_state_files_opened": True,
        "question_or_prediction_fields_used": False,
        "mapping_gold_category_evaluator_score_read": False,
        "evidence_content_or_identifier_emitted": False,
    }
