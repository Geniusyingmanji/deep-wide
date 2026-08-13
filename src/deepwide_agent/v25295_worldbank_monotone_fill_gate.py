"""Build-only World Bank shared-prefix monotone-fill causal gate.

This module has three narrow surfaces:

* pure parsing/rendering of already-supplied official World Bank JSON bytes;
* a deterministic in-memory snapshot search client that preserves the frozen
  V2.48.57 two-wave receipts without performing network effects; and
* one same-forward paired runtime: the control is the validated two-call
  V2.48.57 parent prediction and the candidate may spend only its unused third
  model slot through V2.52.90.

The module cannot select a live population, read benchmark labels/gold, run an
evaluator, or authorize an external launch.  Entropy/information gain remains
shadow-only and assigns no signed credit.
"""

from __future__ import annotations

import copy
import hashlib
import itertools
import json
import math
import re
import types
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Callable
from urllib.parse import parse_qsl, urlsplit

from . import v24273_two_wave_task_runtime as retrieval_runtime
from . import v24318_deadline_conservation_runtime as conservation_runtime
from . import v24319_runner_integration as runner_integration
from . import v24630_exact220_task_integration as task_integration
from . import v24857_pacing_aware_exact220_contract as parent_contract
from . import v25290_monotone_unknown_fill_integration as candidate
from .clients import canonicalize_url
from .v24257_score_first_runtime import ScoreFirstLimits, validate_visible_task
from .v24263_global_model_limiter import payload_sha256
from .v24272_two_wave_entropy_voc import TwoWavePolicy
from .v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter
from .v24630_exact220_task_integration import (
    IntegratedExact220TaskOutcome,
    build_envelope as build_parent_envelope,
    validate_envelope as validate_parent_envelope,
)
from .v24630_thin_backfill_search import (
    ThinSameResponseCitationTitleBackfillSearchClient,
)
from .v24796_deadline_tavily_search import empty_receipt as empty_direct_receipt
from .v24796_deadline_tavily_search import (
    validate_receipt as validate_direct_receipt,
)
from .v24852_rate_aware_tavily_search import (
    empty_rate_aware_receipt,
    validate_receipt as validate_rate_receipt,
)
from .v24856_pacing_aware_admission import (
    run_pacing_aware_two_wave_retrieval,
    validate_receipt as validate_pacing_receipt,
)
from .v24859_full_evidence_coverage_revision import (
    EvidencePage,
    prepare_evidence_pages,
)


POLICY_ID = "v25295_worldbank_shared_prefix_monotone_fill_gate_v1"
RESULT_ROLE = "v25295_worldbank_monotone_fill_paired_task_result"
RECEIPT_ROLE = "v25295_content_free_worldbank_monotone_fill_paired_receipt"
SNAPSHOT_RECEIPT_ROLE = "v25295_content_free_worldbank_snapshot_transport_receipt"
PAGE_ATTRIBUTE = "_v25295_same_forward_evidence_pages"

TARGET_COUNT = 4
TASK_COUNT = 12
ROWS_PER_TASK = 12
ENTITY_ROW_COUNT = TASK_COUNT * ROWS_PER_TASK
VALUE_CELL_COUNT = ENTITY_ROW_COUNT * TARGET_COUNT
TARGET_YEAR = "2022"
MINIMUM_TARGET_OVERSAMPLE = 24
PAGES_PER_TARGET = 2
PAGE_COUNT = TARGET_COUNT * PAGES_PER_TARGET
WORLD_BANK_PER_PAGE = 200
MAXIMUM_PAGE_CHARS = 5_000
MAXIMUM_EVIDENCE_CHARS = 40_000
SELECTION_SEED = "v25294-fresh-worldbank-monotone-fill-v1"
INDICATOR = re.compile(r"[A-Z][A-Z0-9.]{4,40}")


@dataclass(frozen=True)
class TargetSpec:
    label: str
    indicator: str
    year: str
    urls: tuple[str, str]

    @property
    def key(self) -> str:
        return f"{self.indicator}@{self.year}"

    @property
    def column(self) -> str:
        return f"{self.label} [{self.indicator}] @{self.year}"

    def validate(self) -> None:
        if (
            not isinstance(self.label, str)
            or not self.label.strip()
            or len(self.label) > 80
            or any(character in self.label for character in "|\r\n`")
            or not isinstance(self.indicator, str)
            or INDICATOR.fullmatch(self.indicator) is None
            or self.year != TARGET_YEAR
            or len(self.urls) != PAGES_PER_TARGET
            or len(set(self.urls)) != PAGES_PER_TARGET
            or any(
                not _target_url_matches(url, target=self, page=page)
                for page, url in enumerate(self.urls, 1)
            )
        ):
            raise ValueError("V2.52.95 target spec drifted")


@dataclass(frozen=True)
class ParsedWorldBankPage:
    page: int
    pages: int
    per_page: int
    total: int
    record_count: int
    entity_codes: frozenset[str]
    indicator: str
    year: str
    values: dict[str, str]


def _target_url_matches(url: object, *, target: TargetSpec, page: int) -> bool:
    try:
        parsed = urlsplit(str(url))
        pairs = parse_qsl(parsed.query, keep_blank_values=True)
    except ValueError:
        return False
    parts = parsed.path.strip("/").split("/")
    return bool(
        parsed.scheme == "https"
        and (parsed.hostname or "").casefold() == "api.worldbank.org"
        and parsed.port is None
        and parsed.username is None
        and parsed.password is None
        and not parsed.fragment
        and parts == ["v2", "country", "all", "indicator", target.indicator]
        and pairs
        == [
            ("date", target.year),
            ("format", "json"),
            ("page", str(page)),
            ("per_page", str(WORLD_BANK_PER_PAGE)),
        ]
        and canonicalize_url(str(url)) == str(url)
    )


def _rank(namespace: str, value: str) -> str:
    normalized = " ".join(str(value).casefold().split())
    if namespace not in {"target", "entity"} or not normalized or len(normalized) > 160:
        raise ValueError("V2.52.95 deterministic rank input drifted")
    return hashlib.sha256(
        f"{SELECTION_SEED}\0{namespace}\0{normalized}".encode()
    ).hexdigest()


def parse_worldbank_page(blob: bytes, *, target: TargetSpec, page: int) -> ParsedWorldBankPage:
    """Parse one exact official page without filesystem or network access."""

    target.validate()
    if page not in {1, 2} or not isinstance(blob, bytes) or not blob or len(blob) > 2_000_000:
        raise ValueError("V2.52.95 raw World Bank page drifted")
    try:
        value = json.loads(blob)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("V2.52.95 World Bank JSON is invalid") from exc
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError("V2.52.95 World Bank response envelope drifted")
    metadata, records = value
    if not isinstance(metadata, Mapping) or not isinstance(records, list):
        raise ValueError("V2.52.95 World Bank response schema drifted")
    try:
        observed_page = int(metadata["page"])
        observed_pages = int(metadata["pages"])
        per_page = int(metadata["per_page"])
        total = int(metadata["total"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("V2.52.95 World Bank pagination drifted") from exc
    if (
        observed_page != page
        or observed_pages != PAGES_PER_TARGET
        or per_page != WORLD_BANK_PER_PAGE
        or total <= WORLD_BANK_PER_PAGE
        or total > PAGES_PER_TARGET * WORLD_BANK_PER_PAGE
        or observed_pages != math.ceil(total / per_page)
        or not 0 < len(records) <= per_page
        or (page < observed_pages and len(records) != per_page)
    ):
        raise ValueError("V2.52.95 World Bank pagination contract drifted")
    values: dict[str, str] = {}
    seen_codes: set[str] = set()
    for record in records:
        if not isinstance(record, Mapping):
            raise ValueError("V2.52.95 World Bank record drifted")
        code = str(record.get("countryiso3code") or "").strip().upper()
        indicator = record.get("indicator") or {}
        observed_indicator = str(
            indicator.get("id") if isinstance(indicator, Mapping) else ""
        ).strip()
        observed_year = str(record.get("date") or "").strip()
        raw_value = record.get("value")
        if observed_indicator != target.indicator or observed_year != target.year:
            raise ValueError("V2.52.95 World Bank target binding drifted")
        if not code or len(code) != 3 or not code.isalnum():
            continue
        if code in seen_codes:
            raise ValueError("V2.52.95 duplicate entity in one target page")
        seen_codes.add(code)
        if raw_value is not None:
            text = str(raw_value).strip()
            if not text or "|" in text or "\n" in text or len(text) > 160:
                raise ValueError("V2.52.95 World Bank value drifted")
            values[code] = text
    return ParsedWorldBankPage(
        page=observed_page,
        pages=observed_pages,
        per_page=per_page,
        total=total,
        record_count=len(records),
        entity_codes=frozenset(seen_codes),
        indicator=target.indicator,
        year=target.year,
        values=values,
    )


def parse_target_pages(
    blobs: Sequence[bytes], *, target: TargetSpec
) -> tuple[ParsedWorldBankPage, ParsedWorldBankPage]:
    if isinstance(blobs, (str, bytes)) or len(blobs) != PAGES_PER_TARGET:
        raise ValueError("V2.52.95 target page vector drifted")
    first = parse_worldbank_page(blobs[0], target=target, page=1)
    second = parse_worldbank_page(blobs[1], target=target, page=2)
    if (
        first.total != second.total
        or first.record_count + second.record_count != first.total
    ):
        raise ValueError("V2.52.95 target page coverage drifted")
    if first.entity_codes.intersection(second.entity_codes):
        raise ValueError("V2.52.95 entity crosses target pages")
    return first, second


def _render_page(
    parsed: ParsedWorldBankPage,
    *,
    target: TargetSpec,
    selected_entities: set[str],
    url: str,
) -> dict[str, Any]:
    rows = [
        (code, parsed.values[code])
        for code in sorted(parsed.values)
        if code in selected_entities
    ]
    lines = [
        f"| Entity code | {target.column} |",
        "| --- | --- |",
        *(f"| {code} | {value} |" for code, value in rows),
    ]
    content = "\n".join(lines)
    if not rows or len(content) > MAXIMUM_PAGE_CHARS:
        raise ValueError("V2.52.95 rendered page capacity drifted")
    return {
        "url": canonicalize_url(url),
        "title": "Official World Bank indicator page",
        "content": content,
        "fetch_integrity": True,
    }


def _target_values(
    pages: Sequence[ParsedWorldBankPage],
) -> dict[str, str]:
    output: dict[str, str] = {}
    for page in pages:
        if set(output).intersection(page.values):
            raise ValueError("V2.52.95 target entity duplication drifted")
        output.update(page.values)
    return output


def select_and_render_population(
    candidates: Mapping[TargetSpec, Sequence[bytes]],
    *,
    historical_target_keys: Sequence[str],
) -> dict[str, Any]:
    """Choose the first pre-ranked viable target quartet, entirely in memory."""

    if len(candidates) != MINIMUM_TARGET_OVERSAMPLE:
        raise ValueError("V2.52.95 requires exactly 24 consumed target candidates")
    old = {" ".join(str(value).casefold().split()) for value in historical_target_keys}
    parsed: dict[str, tuple[TargetSpec, tuple[ParsedWorldBankPage, ParsedWorldBankPage]]] = {}
    for target, blobs in candidates.items():
        target.validate()
        normalized = target.key.casefold()
        if normalized in parsed:
            raise ValueError("V2.52.95 duplicate target key")
        parsed[normalized] = (target, parse_target_pages(blobs, target=target))
    eligible = [key for key in parsed if key not in old]
    if len(eligible) < TARGET_COUNT:
        raise RuntimeError("V2.52.95 fresh target capacity is insufficient")
    ranked = sorted(eligible, key=lambda key: (_rank("target", key), key))
    selected: tuple[str, ...] | None = None
    entities: list[str] | None = None
    pages: list[dict[str, Any]] | None = None
    for combination in itertools.combinations(ranked, TARGET_COUNT):
        common = set.intersection(
            *(
                set(_target_values(parsed[key][1]))
                for key in combination
            )
        )
        if len(common) < ENTITY_ROW_COUNT:
            continue
        chosen_entities = sorted(
            common, key=lambda code: (_rank("entity", code), code)
        )[:ENTITY_ROW_COUNT]
        rendered: list[dict[str, Any]] = []
        try:
            for key in combination:
                target, target_pages = parsed[key]
                for index, target_page in enumerate(target_pages):
                    rendered.append(
                        _render_page(
                            target_page,
                            target=target,
                            selected_entities=set(chosen_entities),
                            url=target.urls[index],
                        )
                    )
        except ValueError:
            continue
        if (
            len(rendered) == PAGE_COUNT
            and sum(len(page["content"]) for page in rendered)
            <= MAXIMUM_EVIDENCE_CHARS
        ):
            selected = combination
            entities = chosen_entities
            pages = rendered
            break
    if selected is None or entities is None or pages is None:
        raise RuntimeError("V2.52.95 no viable four-target combination")
    tasks = []
    columns = ["Entity code", *(parsed[key][0].column for key in selected)]
    for index in range(TASK_COUNT):
        codes = entities[index * ROWS_PER_TASK : (index + 1) * ROWS_PER_TASK]
        question = (
            "Return exactly one Markdown table and no prose. Column names: "
            + " | ".join(columns)
            + ". Include exactly these entity-code rows in this order: "
            + ", ".join(codes)
            + ". Use Unknown only when the supplied official pages do not show a value."
        )
        opaque = "task_" + hashlib.sha256(
            f"v25295:{','.join(selected)}:{','.join(codes)}".encode()
        ).hexdigest()[:24]
        tasks.append({"opaque_id": opaque, "question": question})
    return {
        "target_keys": list(selected),
        "target_columns": columns[1:],
        "entities": entities,
        "pages": pages,
        "tasks": tasks,
    }


class FrozenWorldBankSnapshotSearchClient(
    ThinSameResponseCitationTitleBackfillSearchClient
):
    """No-network two-wave search facade over eight frozen rendered pages."""

    def __init__(
        self,
        pages: Sequence[Mapping[str, Any]],
        *,
        absolute_deadline: float,
        monotonic: Callable[[], float],
    ) -> None:
        super().__init__(
            "http://unused.invalid/responses",
            "frozen-worldbank-snapshot",
            reasoning_effort="low",
            service_tier="",
            timeout=30,
            max_retries=1,
            fetch_pages=False,
            fetch_workers=8,
            max_page_chars=MAXIMUM_PAGE_CHARS,
            hard_fetch_deadline_seconds=25,
            absolute_deadline=absolute_deadline,
            cleanup_reserve_seconds=5,
            minimum_attempt_seconds=0.01,
            monotonic=monotonic,
            sleeper=lambda _seconds: None,
        )
        raw_pages: list[EvidencePage] = []
        self._snapshot_by_url: dict[str, EvidencePage] = {}
        for index, value in enumerate(pages, 1):
            if not isinstance(value, Mapping) or value.get("fetch_integrity") is not True:
                raise ValueError("V2.52.95 snapshot page integrity drifted")
            page = EvidencePage(
                evidence_id=f"E{index:04d}",
                url=str(value.get("url") or ""),
                content=str(value.get("content") or ""),
                fetch_integrity=True,
            )
            page.validate()
            canonical = canonicalize_url(page.url)
            if canonical in self._snapshot_by_url or len(page.content) > MAXIMUM_PAGE_CHARS:
                raise ValueError("V2.52.95 snapshot page vector drifted")
            raw_pages.append(page)
            self._snapshot_by_url[canonical] = page
        prepared = prepare_evidence_pages(raw_pages)
        if len(prepared) != PAGE_COUNT or sum(len(page.content) for page in prepared) > MAXIMUM_EVIDENCE_CHARS:
            raise ValueError("V2.52.95 snapshot page capacity drifted")
        self._snapshot_pages = prepared
        self._snapshot_search_invocations = 0
        self._snapshot_fetch_hits = 0

    def search_many(
        self,
        queries: Sequence[str],
        *,
        max_results: int,
        search_depth: str = "advanced",
        include_raw_content: bool = False,
    ) -> list[dict[str, Any]]:
        logical = [" ".join(str(value).split()) for value in queries if str(value).strip()]
        if (
            len(logical) != 2
            or len(set(value.casefold() for value in logical)) != 2
            or max_results != 3
            or search_depth != "advanced"
            or include_raw_content is not False
            or self._snapshot_search_invocations >= 2
        ):
            raise ValueError("V2.52.95 snapshot search invocation drifted")
        invocation = self._snapshot_search_invocations
        self._snapshot_search_invocations += 1
        chosen = self._snapshot_pages[:6] if invocation == 0 else self._snapshot_pages[6:]
        outputs = []
        for index, query in enumerate(logical):
            assigned = chosen[index::2]
            outputs.append(
                {
                    "query": query,
                    "answer": "",
                    "results": [
                        {
                            "title": "Official World Bank indicator page",
                            "url": canonicalize_url(page.url),
                            "fetch_url": page.url,
                            "content": "",
                            "raw_content": "",
                            "score": None,
                            "source_type": "frozen_worldbank_snapshot_lead",
                        }
                        for page in assigned
                    ],
                    "error": None,
                    "provider": "v25295-frozen-worldbank-snapshot",
                }
            )
        self._increment("multi_query_chunks")
        self._increment("citation_backfill_multi_query_payload_count")
        return outputs

    def _fetch_url(self, url: str) -> dict[str, Any]:
        self._increment("fetch_calls")
        canonical = canonicalize_url(url)
        page = self._snapshot_by_url.get(canonical)
        if page is None:
            self._increment("fetch_failures")
            return {"status": "snapshot_miss", "url": "", "title": "", "text": "", "links": []}
        self._snapshot_fetch_hits += 1
        return {
            "status": "ok",
            "url": page.url,
            "title": "Official World Bank indicator page",
            "text": page.content,
            "links": [],
        }

    def rate_aware_search_receipt(self) -> dict[str, Any]:
        return empty_rate_aware_receipt()

    def direct_search_receipt(self) -> dict[str, Any]:
        return empty_direct_receipt(parent_contract.TAVILY_KEY_SLOT_CAP)

    def snapshot_transport_receipt(self) -> dict[str, Any]:
        value: dict[str, Any] = {
            "artifact_version": 1,
            "role": SNAPSHOT_RECEIPT_ROLE,
            "policy_id": POLICY_ID,
            "frozen_page_count": len(self._snapshot_pages),
            "search_invocations": int(self._snapshot_search_invocations),
            "fetch_hits": int(self._snapshot_fetch_hits),
            "network_search_calls": 0,
            "network_fetch_calls": 0,
            "snapshot_pages_are_only_active_evidence": True,
            "contains_query_url_page_value_prediction_answer_or_credential": False,
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
            "entropy_or_information_gain_assigns_signed_credit": False,
            "benchmark_launch_or_evaluator_authorized": False,
        }
        value["receipt_payload_sha256"] = payload_sha256(value)
        return validate_snapshot_receipt(value)


def validate_snapshot_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    signature = unsigned.pop("receipt_payload_sha256", None)
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "policy_id",
            "frozen_page_count",
            "search_invocations",
            "fetch_hits",
            "network_search_calls",
            "network_fetch_calls",
            "snapshot_pages_are_only_active_evidence",
            "contains_query_url_page_value_prediction_answer_or_credential",
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
            "entropy_or_information_gain_assigns_signed_credit",
            "benchmark_launch_or_evaluator_authorized",
            "receipt_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != SNAPSHOT_RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("frozen_page_count") != PAGE_COUNT
        or copied.get("search_invocations") not in {0, 1, 2}
        or copied.get("fetch_hits") < 0
        or copied.get("fetch_hits") > PAGE_COUNT
        or copied.get("network_search_calls") != 0
        or copied.get("network_fetch_calls") != 0
        or copied.get("snapshot_pages_are_only_active_evidence") is not True
        or any(
            copied.get(name) is not False
            for name in (
                "contains_query_url_page_value_prediction_answer_or_credential",
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
                "entropy_or_information_gain_assigns_signed_credit",
                "benchmark_launch_or_evaluator_authorized",
            )
        )
        or signature != payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.95 snapshot receipt drifted")
    return copied


def _isolated_function(original: Any, **bindings: Any) -> Any:
    if original.__closure__:
        raise RuntimeError("V2.52.95 frozen parent unexpectedly has closure state")
    namespace = dict(original.__globals__)
    namespace.update(bindings)
    value = types.FunctionType(
        original.__code__,
        namespace,
        name=f"v25295_isolated_{original.__name__}",
        argdefs=original.__defaults__,
        closure=None,
    )
    value.__kwdefaults__ = copy.deepcopy(original.__kwdefaults__)
    value.__annotations__ = copy.deepcopy(original.__annotations__)
    return value


def _pacing_retrieval(*args: Any, **kwargs: Any) -> dict[str, Any]:
    search = kwargs.get("search")
    if search is None and len(args) >= 2:
        search = args[1]
    if search is None:
        raise TypeError("V2.52.95 pacing search binding is absent")
    value = run_pacing_aware_two_wave_retrieval(*args, **kwargs)
    receipt = validate_pacing_receipt(value["pacing_admission_receipt"])
    setattr(search, "_v25295_pacing_admission_receipt", receipt)
    output = copy.deepcopy(value)
    output.pop("pacing_admission_receipt", None)
    return output


_PACING_SEARCH_MANY = _isolated_function(
    retrieval_runtime.TwoWaveCachingSearchClient.search_many,
    run_two_wave_retrieval=_pacing_retrieval,
)


class MonotoneFillCachingSearchClient(retrieval_runtime.TwoWaveCachingSearchClient):
    """Pacing-aware cache that exports this task's exact fetched page prefix."""

    def search_many(self, queries: Sequence[str], **kwargs: Any) -> list[dict[str, Any]]:
        setattr(self.inner, PAGE_ATTRIBUTE, ())
        output = _PACING_SEARCH_MANY(self, queries, **kwargs)
        pages: list[EvidencePage] = []
        for batch in output:
            if not isinstance(batch, Mapping):
                continue
            for result in batch.get("results") or []:
                if not isinstance(result, Mapping):
                    continue
                url = canonicalize_url(str(result.get("url") or ""))
                cached = self._page_cache.get(url)
                if not url or not isinstance(cached, Mapping):
                    continue
                content = str(cached.get("raw_content") or cached.get("content") or "")
                if content:
                    pages.append(
                        EvidencePage(
                            evidence_id=f"E{len(pages) + 1:04d}",
                            url=url,
                            content=content,
                            fetch_integrity=True,
                        )
                    )
        try:
            prepared = prepare_evidence_pages(pages)
        except (TypeError, ValueError):
            prepared = ()
        setattr(self.inner, PAGE_ATTRIBUTE, prepared)
        return output


_ISOLATED_RUN_PARENT = _isolated_function(
    conservation_runtime._run_parent,
    TwoWaveCachingSearchClient=MonotoneFillCachingSearchClient,
)
_ISOLATED_RUN_V24318_TASK = _isolated_function(
    conservation_runtime.run_v24318_task,
    _run_parent=_ISOLATED_RUN_PARENT,
)
_ISOLATED_RUN_V24319_TASK = _isolated_function(
    runner_integration.run_v24319_task,
    run_v24318_task=_ISOLATED_RUN_V24318_TASK,
)
_PARENT_RUN_TASK = _isolated_function(
    task_integration.run_v24630_task,
    run_v24319_task=_ISOLATED_RUN_V24319_TASK,
)


def validate_isolation() -> None:
    if (
        retrieval_runtime.TwoWaveCachingSearchClient.search_many is _PACING_SEARCH_MANY
        or conservation_runtime._run_parent is _ISOLATED_RUN_PARENT
        or runner_integration.run_v24319_task is _ISOLATED_RUN_V24319_TASK
        or task_integration.run_v24630_task is _PARENT_RUN_TASK
        or _PACING_SEARCH_MANY.__globals__["run_two_wave_retrieval"] is not _pacing_retrieval
    ):
        raise RuntimeError("V2.52.95 isolated integration binding drifted")


def _paired_receipt(
    parent: Mapping[str, Any],
    integration: Mapping[str, Any],
    snapshot: Mapping[str, Any],
    transport: Mapping[str, Any],
) -> dict[str, Any]:
    checked_integration = candidate.validate_integration_receipt(integration)
    checked_snapshot = validate_snapshot_receipt(snapshot)
    checked_transport = _validate_transport_receipts(transport)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "shared_parent_forward_count": 1,
        "control_prediction_is_parent_prediction": True,
        "candidate_prediction_changed": bool(checked_integration["prediction_changed"]),
        "candidate_disposition": str(checked_integration["disposition"]),
        "parent_logical_model_calls": int(checked_integration["logical_parent_model_calls"]),
        "candidate_logical_revision_calls": int(checked_integration["logical_revision_call_admitted"]),
        "final_logical_model_calls": int(checked_integration["logical_final_model_calls"]),
        "physical_query_count": 2 * int(checked_snapshot["search_invocations"]),
        "physical_fetch_count": int(checked_snapshot["fetch_hits"]),
        "supported_unknown_fill_count": int(
            checked_integration["monotone_unknown_fill_receipt"]["admitted_unknown_fill_count"]
        ),
        "query_effect_shared_and_candidate_additional_query_count": 0,
        "fetch_effect_shared_and_candidate_additional_fetch_count": 0,
        "same_parent_prediction_queries_search_responses_fetched_pages_and_caps": True,
        "snapshot_transport_receipt": copy.deepcopy(checked_snapshot),
        "content_free_parent_transport_receipts": copy.deepcopy(
            checked_transport
        ),
        "known_cells_schema_row_keys_order_and_count_immutable": True,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "positive_signed_credit_count": 0,
        "contains_question_query_url_page_value_prediction_answer_opaque_id_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_payload_sha256"] = payload_sha256(value)
    return validate_paired_receipt(value)


def validate_paired_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    signature = unsigned.pop("receipt_payload_sha256", None)
    snapshot = copied.get("snapshot_transport_receipt")
    transport = copied.get("content_free_parent_transport_receipts")
    integer_fields = (
        "shared_parent_forward_count",
        "parent_logical_model_calls",
        "candidate_logical_revision_calls",
        "final_logical_model_calls",
        "physical_query_count",
        "physical_fetch_count",
        "supported_unknown_fill_count",
        "query_effect_shared_and_candidate_additional_query_count",
        "fetch_effect_shared_and_candidate_additional_fetch_count",
        "positive_signed_credit_count",
    )
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "policy_id",
            *integer_fields,
            "control_prediction_is_parent_prediction",
            "candidate_prediction_changed",
            "candidate_disposition",
            "same_parent_prediction_queries_search_responses_fetched_pages_and_caps",
            "snapshot_transport_receipt",
            "content_free_parent_transport_receipts",
            "known_cells_schema_row_keys_order_and_count_immutable",
            "entropy_or_information_gain_assigns_signed_credit",
            "contains_question_query_url_page_value_prediction_answer_opaque_id_or_credential",
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
            "benchmark_launch_or_evaluator_authorized",
            "receipt_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in integer_fields
        )
        or copied.get("shared_parent_forward_count") != 1
        or copied.get("control_prediction_is_parent_prediction") is not True
        or not isinstance(copied.get("candidate_prediction_changed"), bool)
        or copied.get("candidate_disposition") not in candidate.DISPOSITIONS
        or copied.get("parent_logical_model_calls") not in {0, 1, 2, 3}
        or copied.get("candidate_logical_revision_calls") not in {0, 1}
        or copied.get("final_logical_model_calls")
        != copied.get("parent_logical_model_calls")
        + copied.get("candidate_logical_revision_calls")
        or copied.get("final_logical_model_calls") > 3
        or copied.get("physical_query_count") > 4
        or copied.get("physical_fetch_count") > 10
        or copied.get("candidate_prediction_changed")
        is not (copied.get("supported_unknown_fill_count") > 0)
        or copied.get("query_effect_shared_and_candidate_additional_query_count") != 0
        or copied.get("fetch_effect_shared_and_candidate_additional_fetch_count") != 0
        or copied.get("same_parent_prediction_queries_search_responses_fetched_pages_and_caps") is not True
        or not isinstance(snapshot, Mapping)
        or validate_snapshot_receipt(snapshot) != dict(snapshot)
        or not isinstance(transport, Mapping)
        or _validate_transport_receipts(transport) != dict(transport)
        or copied.get("physical_query_count")
        != 2 * int(snapshot.get("search_invocations", -1))
        or snapshot.get("fetch_hits") != copied.get("physical_fetch_count")
        or (transport.get("pacing_admission_receipt") is None)
        is not (int(snapshot.get("search_invocations", 0)) == 0)
        or copied.get("known_cells_schema_row_keys_order_and_count_immutable") is not True
        or any(
            copied.get(name) is not False
            for name in (
                "entropy_or_information_gain_assigns_signed_credit",
                "contains_question_query_url_page_value_prediction_answer_opaque_id_or_credential",
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
                "benchmark_launch_or_evaluator_authorized",
            )
        )
        or copied.get("positive_signed_credit_count") != 0
        or signature != payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.95 paired receipt drifted")
    return copied


def _validate_transport_receipts(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    direct = copied.get("direct_search_receipt")
    rate = copied.get("rate_aware_search_receipt")
    pacing = copied.get("pacing_admission_receipt")
    if (
        set(copied)
        != {
            "direct_search_receipt",
            "rate_aware_search_receipt",
            "pacing_admission_receipt",
        }
        or not isinstance(direct, Mapping)
        or not isinstance(rate, Mapping)
        or validate_direct_receipt(direct) != dict(direct)
        or validate_rate_receipt(rate) != dict(rate)
        or int(direct["provider_attempts"]) != 0
        or int(rate["provider_start_reservations"]) != 0
        or pacing is not None
        and (
            not isinstance(pacing, Mapping)
            or validate_pacing_receipt(pacing) != dict(pacing)
            or pacing[
                "question_query_url_page_prediction_answer_or_credential_read_or_emitted"
            ]
            is not False
            or pacing[
                "mapping_gold_category_question_type_split_evaluator_score_reward_read"
            ]
            is not False
            or pacing["benchmark_launch_or_evaluator_authorized"] is not False
        )
    ):
        raise ValueError("V2.52.95 parent transport receipt drifted")
    return copied


def _build_result(
    *,
    parent: IntegratedExact220TaskOutcome,
    revision: candidate.MonotoneUnknownFillOutcome,
    snapshot_receipt: Mapping[str, Any],
    transport_receipts: Mapping[str, Any],
) -> dict[str, Any]:
    parent_envelope = build_parent_envelope(parent, arm="baseline")
    paired = _paired_receipt(
        parent.result,
        revision.integration_receipt,
        snapshot_receipt,
        transport_receipts,
    )
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": RESULT_ROLE,
        "policy_id": POLICY_ID,
        "opaque_id": str(parent.result["opaque_id"]),
        "status": "terminal",
        "parent_envelope": parent_envelope,
        "candidate_result": copy.deepcopy(revision.result),
        "candidate_final_model_slot_receipt": copy.deepcopy(
            revision.final_model_slot_receipt
        ),
        "content_free_paired_receipt": paired,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["result_payload_sha256"] = payload_sha256(value)
    return validate_result(value)


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    signature = unsigned.pop("result_payload_sha256", None)
    parent_raw = copied.get("parent_envelope")
    candidate_raw = copied.get("candidate_result")
    slot_raw = copied.get("candidate_final_model_slot_receipt")
    receipt_raw = copied.get("content_free_paired_receipt")
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "policy_id",
            "opaque_id",
            "status",
            "parent_envelope",
            "candidate_result",
            "candidate_final_model_slot_receipt",
            "content_free_paired_receipt",
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
            "entropy_or_information_gain_assigns_signed_credit",
            "benchmark_launch_or_evaluator_authorized",
            "result_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != RESULT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("status") != "terminal"
        or not isinstance(parent_raw, Mapping)
        or not isinstance(candidate_raw, Mapping)
        or not isinstance(slot_raw, Mapping)
        or not isinstance(receipt_raw, Mapping)
        or any(
            copied.get(name) is not False
            for name in (
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
                "entropy_or_information_gain_assigns_signed_credit",
                "benchmark_launch_or_evaluator_authorized",
            )
        )
        or signature != payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.95 paired result envelope drifted")
    parent = validate_parent_envelope(parent_raw)
    candidate_result = candidate.validate_result(
        candidate_raw, final_model_slot_receipt=slot_raw
    )
    receipt = validate_paired_receipt(receipt_raw)
    parent_result = parent["result"]
    integration = candidate.validate_integration_receipt(
        candidate_result["monotone_unknown_fill_receipt"]
    )
    if (
        copied.get("opaque_id") != parent_result["opaque_id"]
        or candidate_result["opaque_id"] != parent_result["opaque_id"]
        or candidate_result["parent_result"] != parent_result
        or receipt["candidate_prediction_changed"]
        is not (candidate_result["prediction"] != parent_result["prediction"])
        or receipt["candidate_disposition"] != integration["disposition"]
        or receipt["parent_logical_model_calls"]
        != integration["logical_parent_model_calls"]
        or receipt["final_logical_model_calls"]
        != integration["logical_final_model_calls"]
        or receipt["physical_fetch_count"]
        != parent_result["evidence"]["fetch_target_count"]
    ):
        raise ValueError("V2.52.95 paired result binding drifted")
    return copied


def run_paired_task(
    task: Mapping[str, Any],
    *,
    model: DeadlineAwareGlobalModelSlotLimiter,
    search: ThinSameResponseCitationTitleBackfillSearchClient,
    limits: ScoreFirstLimits,
    two_wave_policy: TwoWavePolicy,
    monotonic: Callable[[], float],
    progress: Any = None,
) -> dict[str, Any]:
    visible = validate_visible_task(task)
    limits.validate()
    two_wave_policy.validate()
    if not isinstance(model, DeadlineAwareGlobalModelSlotLimiter):
        raise ValueError("V2.52.95 requires the inherited global model limiter")
    if not isinstance(search, ThinSameResponseCitationTitleBackfillSearchClient):
        raise ValueError("V2.52.95 requires the inherited thin search client")
    if (
        limits.__dict__ != parent_contract.LIMITS
        or two_wave_policy.__dict__ != parent_contract.TWO_WAVE_POLICY
    ):
        raise ValueError("V2.52.95 inherited budget or two-wave policy drifted")
    validate_isolation()
    parent = _PARENT_RUN_TASK(
        visible,
        arm="baseline",
        model=model,
        search=search,
        limits=limits,
        two_wave_policy=two_wave_policy,
        monotonic=monotonic,
        progress=progress,
    )
    pages = getattr(search, PAGE_ATTRIBUTE, ())
    if not isinstance(pages, tuple) or any(not isinstance(page, EvidencePage) for page in pages):
        pages = ()
    revision = candidate.run_monotone_unknown_fill(
        visible,
        parent_result=parent.result,
        parent_model_slot_receipt=parent.model_slot_receipt,
        model=model,
        pages=pages,
        limits=limits,
        monotonic=monotonic,
    )
    snapshot_method = getattr(search, "snapshot_transport_receipt", None)
    if not callable(snapshot_method):
        raise TypeError("V2.52.95 snapshot transport receipt is absent")
    pacing_receipt = getattr(search, "_v25295_pacing_admission_receipt", None)
    transport_receipts = _validate_transport_receipts(
        {
            "direct_search_receipt": search.direct_search_receipt(),
            "rate_aware_search_receipt": search.rate_aware_search_receipt(),
            "pacing_admission_receipt": pacing_receipt,
        }
    )
    return _build_result(
        parent=parent,
        revision=revision,
        snapshot_receipt=snapshot_method(),
        transport_receipts=transport_receipts,
    )


__all__ = [
    "ENTITY_ROW_COUNT",
    "FrozenWorldBankSnapshotSearchClient",
    "MAXIMUM_EVIDENCE_CHARS",
    "MAXIMUM_PAGE_CHARS",
    "PAGE_COUNT",
    "POLICY_ID",
    "RESULT_ROLE",
    "ROWS_PER_TASK",
    "SNAPSHOT_RECEIPT_ROLE",
    "TASK_COUNT",
    "TARGET_COUNT",
    "TARGET_YEAR",
    "TargetSpec",
    "VALUE_CELL_COUNT",
    "parse_target_pages",
    "parse_worldbank_page",
    "run_paired_task",
    "select_and_render_population",
    "validate_isolation",
    "validate_paired_receipt",
    "validate_result",
    "validate_snapshot_receipt",
]
