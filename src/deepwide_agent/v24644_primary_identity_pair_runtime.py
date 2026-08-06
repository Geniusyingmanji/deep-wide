"""Primary-identity-bound ROR pair discovery for V2.46.44.

V2.46.42 showed that an official ROR URL and a target name somewhere in the
body can describe an affiliation rather than the page's primary identity.
This append-only successor therefore admits a pair through exactly two routes:

* the normalized whole fetched-page title equals the visible target and the
  URL is the corresponding canonical ``ror.org/<id>`` profile; or
* an official ``api.ror.org`` top-level JSON record binds the URL identifier,
  record identifier, and unique ``ror_display`` name to the visible target.

Body-only co-occurrence is counted as rejected telemetry and has no factual
authority.  Search-lead titles are blanked before the fetch effect so an
adapter's empty-page-title fallback cannot masquerade as fetched-page title
evidence.  Existing non-Unknown ROR cells and all country cells remain
immutable.  The runtime has no file, benchmark, gold, evaluator, reward, or
score capability; entropy remains shadow-only.
"""

from __future__ import annotations

import copy
import json
import re
import unicodedata
from collections import Counter, defaultdict
from collections.abc import Callable, Mapping, Sequence
from types import FunctionType
from typing import Any
from urllib.parse import urlsplit

from . import v24639_ror_objective_runtime as ror
from . import v24642_deterministic_pair_runtime as frozen
from .v24640_evidence_constrained_runtime import (
    UNKNOWN,
    _contains_exact_phrase,
    _render,
    _ror_suffix,
)


POLICY_ID = "v24644_primary_identity_bound_ror_pair_discovery_v1"
ROLE = "v24644_primary_identity_pair_ror_task_result"
RECEIPT_ROLE = "v24644_primary_identity_pair_content_free_receipt"
ARMS = frozen.ARMS

_ROR_PROFILE_PATH = re.compile(r"/(0[0-9a-z]{8})/?", re.IGNORECASE)
_ROR_API_PATH = re.compile(
    r"/(?:v[0-9]+/)?organizations/(0[0-9a-z]{8})/?", re.IGNORECASE
)


def normalized_identity(value: object) -> str:
    """Return a punctuation- and accent-folded whole identity surface."""

    decomposed = unicodedata.normalize("NFKD", str(value)).casefold()
    without_marks = "".join(
        character for character in decomposed if not unicodedata.combining(character)
    )
    return " ".join(
        re.sub(r"[^\w]+", " ", without_marks, flags=re.UNICODE).split()
    )


def _official_profile_suffix(url: object) -> str | None:
    try:
        parsed = urlsplit(str(url))
    except ValueError:
        return None
    if (
        parsed.scheme.casefold() != "https"
        or (parsed.hostname or "").casefold() not in {"ror.org", "www.ror.org"}
        or parsed.query
        or parsed.fragment
    ):
        return None
    match = _ROR_PROFILE_PATH.fullmatch(parsed.path)
    return _ror_suffix(match.group(1)) if match else None


def _official_structured_record_suffix(
    page: Mapping[str, object], entity: str
) -> str | None:
    """Validate one complete official ROR API record and its primary name."""

    try:
        parsed = urlsplit(str(page.get("url", "")))
    except ValueError:
        return None
    if (
        parsed.scheme.casefold() != "https"
        or (parsed.hostname or "").casefold() != "api.ror.org"
        or parsed.query
        or parsed.fragment
    ):
        return None
    match = _ROR_API_PATH.fullmatch(parsed.path)
    if not match:
        return None
    url_suffix = _ror_suffix(match.group(1))
    try:
        record = json.loads(str(page.get("content", "")))
    except (json.JSONDecodeError, TypeError, ValueError):
        return None
    if not isinstance(record, Mapping):
        return None
    record_suffix = _ror_suffix(record.get("id"))
    names = record.get("names")
    if (
        url_suffix is None
        or record_suffix != url_suffix
        or not isinstance(names, Sequence)
        or isinstance(names, (str, bytes))
    ):
        return None
    displays: set[str] = set()
    for raw in names:
        if not isinstance(raw, Mapping):
            continue
        types = raw.get("types")
        if (
            isinstance(types, Sequence)
            and not isinstance(types, (str, bytes))
            and "ror_display" in {str(value).casefold() for value in types}
        ):
            display = normalized_identity(raw.get("value"))
            if display:
                displays.add(display)
    target = normalized_identity(entity)
    return url_suffix if len(displays) == 1 and displays == {target} else None


def _primary_binding(
    page: Mapping[str, object], entity: str
) -> tuple[tuple[str, ...], tuple[str, ...], bool, bool]:
    title = str(page.get("title", ""))
    content = str(page.get("content", ""))
    target = normalized_identity(entity)
    suffixes: set[str] = set()
    types: set[str] = set()

    profile_suffix = _official_profile_suffix(page.get("url"))
    if target and normalized_identity(title) == target and profile_suffix is not None:
        suffixes.add(profile_suffix)
        types.add("exact_normalized_whole_title")

    structured_suffix = _official_structured_record_suffix(page, entity)
    if structured_suffix is not None:
        suffixes.add(structured_suffix)
        types.add("official_structured_primary_identity")

    entity_visible = _contains_exact_phrase(f"{title} {content}", entity)
    explicit = frozen.explicit_ror_suffixes(page)
    body_only_rejected = (
        _contains_exact_phrase(content, entity)
        and bool(explicit)
        and not suffixes
    )
    return (
        tuple(sorted(suffixes)),
        tuple(sorted(types)),
        body_only_rejected,
        entity_visible,
    )


def primary_identity_bound_ror_suffixes(
    page: Mapping[str, object], entity: str
) -> tuple[str, ...]:
    """Return only ROR values whose page primary identity is the target."""

    return _primary_binding(page, entity)[0]


def _page_title_only_lead_requests(
    batches: Sequence[Mapping[str, Any]], limit: int
) -> list[dict[str, str]]:
    """Use official API records for discovered ROR profiles and blank titles."""

    values = frozen._lead_requests(batches, limit)
    output: list[dict[str, str]] = []
    for value in values:
        projected = {**value, "title": ""}
        suffix = _official_profile_suffix(projected.get("url"))
        if suffix is not None:
            projected["url"] = f"https://api.ror.org/v2/organizations/{suffix}"
        output.append(projected)
    return output


def _final_url_page_vector(
    batches: object, *, prefix: str, page_chars: int
) -> list[dict[str, str]]:
    """Project identity from the fetched final URL, never the requested URL."""

    if not isinstance(batches, Sequence) or isinstance(batches, (str, bytes)):
        return []
    projected: list[dict[str, Any]] = []
    for raw_batch in batches:
        if not isinstance(raw_batch, Mapping):
            continue
        batch = dict(raw_batch)
        results: list[dict[str, Any]] = []
        for raw_result in raw_batch.get("results") or []:
            if not isinstance(raw_result, Mapping):
                continue
            result = dict(raw_result)
            final_url = str(result.get("url", "")).strip()
            result["requested_url"] = final_url
            result["fetch_url"] = final_url
            result["url"] = final_url
            raw_content = str(result.get("raw_content") or result.get("content") or "")
            try:
                record = json.loads(raw_content)
            except (json.JSONDecodeError, TypeError, ValueError):
                record = None
            if (
                isinstance(record, Mapping)
                and (urlsplit(final_url).hostname or "").casefold() == "api.ror.org"
            ):
                names = record.get("names")
                displays = []
                if isinstance(names, Sequence) and not isinstance(names, (str, bytes)):
                    displays = [
                        {"value": raw.get("value"), "types": list(raw.get("types"))}
                        for raw in names
                        if isinstance(raw, Mapping)
                        and isinstance(raw.get("types"), Sequence)
                        and not isinstance(raw.get("types"), (str, bytes))
                        and "ror_display"
                        in {str(value).casefold() for value in raw.get("types", ())}
                    ]
                result["raw_content"] = json.dumps(
                    {"id": record.get("id"), "names": displays},
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                result["content"] = ""
            results.append(result)
        batch["results"] = results
        projected.append(batch)
    return frozen._page_vector(projected, prefix=prefix, page_chars=page_chars)


def discover_pairs(
    baseline: str,
    *,
    entities: Sequence[str],
    pages: Sequence[Mapping[str, str]],
) -> tuple[str, dict[str, int | bool]]:
    """Fill Unknown ROR cells from unique primary-identity-bound pairs."""

    columns, rows = ror._matrix(baseline)
    if tuple(columns) != ror.EXPECTED_COLUMNS or len(rows) != len(entities):
        raise ValueError("V2.46.44 baseline projection drifted")
    output = [list(row) for row in rows]
    target_values: dict[str, set[str]] = defaultdict(set)
    entity_page_hits: Counter[str] = Counter()
    unique_page_pair_hits: Counter[str] = Counter()
    ambiguous_page_hits: Counter[str] = Counter()
    binding_type_counts: Counter[str] = Counter()
    pages_with_any_explicit_ror = 0
    official_api_pages = 0
    body_only_rejected = 0

    for page in pages:
        pages_with_any_explicit_ror += int(bool(frozen.explicit_ror_suffixes(page)))
        official_api_pages += int(
            (urlsplit(str(page.get("url", ""))).hostname or "").casefold()
            == "api.ror.org"
        )
        for entity in entities:
            suffixes, binding_types, rejected, entity_visible = _primary_binding(
                page, entity
            )
            entity_page_hits[entity] += int(entity_visible)
            body_only_rejected += int(rejected)
            if len(suffixes) == 1:
                target_values[entity].add(suffixes[0])
                unique_page_pair_hits[entity] += 1
                for binding_type in binding_types:
                    binding_type_counts[binding_type] += 1
            elif len(suffixes) > 1:
                ambiguous_page_hits[entity] += 1

    admitted = immutable = unique_targets = ambiguous_targets = no_pair_targets = 0
    for index, entity in enumerate(entities):
        if output[index][0] != entity:
            raise ValueError("V2.46.44 baseline visible order drifted")
        values = target_values.get(entity, set())
        if output[index][1].casefold() not in UNKNOWN:
            immutable += int(bool(values))
            continue
        if len(values) == 1 and ambiguous_page_hits[entity] == 0:
            output[index][1] = next(iter(values))
            admitted += 1
            unique_targets += 1
        elif len(values) > 1 or ambiguous_page_hits[entity] > 0:
            ambiguous_targets += 1
        else:
            no_pair_targets += 1

    changed_nonunknown = any(
        source[1].casefold() not in UNKNOWN and source[1] != target[1]
        for source, target in zip(rows, output, strict=True)
    )
    changed_country = any(
        source[2] != target[2] for source, target in zip(rows, output, strict=True)
    )
    unsupported = admitted > unique_targets
    if changed_nonunknown or changed_country or unsupported:
        raise RuntimeError("V2.46.44 primary-identity discovery violated monotonicity")

    return _render(columns, output), {
        "model_visible_page_count": len(pages),
        "page_with_any_explicit_ror_count": pages_with_any_explicit_ror,
        "official_api_page_count": official_api_pages,
        "entity_page_hit_count": sum(entity_page_hits.values()),
        "unique_page_pair_hit_count": sum(unique_page_pair_hits.values()),
        "ambiguous_page_hit_count": sum(ambiguous_page_hits.values()),
        "unknown_target_unique_pair_count": unique_targets,
        "unknown_target_ambiguous_pair_count": ambiguous_targets,
        "unknown_target_no_pair_count": no_pair_targets,
        "admitted_replacement_count": admitted,
        "nonunknown_target_pair_count": immutable,
        "exact_title_identity_pair_count": binding_type_counts[
            "exact_normalized_whole_title"
        ],
        "structured_primary_identity_pair_count": binding_type_counts[
            "official_structured_primary_identity"
        ],
        "body_only_identity_rejected_pair_count": body_only_rejected,
        "existing_nonunknown_cells_changed": changed_nonunknown,
        "country_code_cells_changed": changed_country,
        "fact_value_created_without_model_visible_unique_pair": unsupported,
    }


def _legacy_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    legacy = copy.deepcopy(dict(value))
    legacy.pop("receipt_sha256", None)
    legacy["role"] = frozen.RECEIPT_ROLE
    legacy["policy_id"] = frozen.POLICY_ID
    legacy["receipt_sha256"] = frozen.paired.payload_sha256(legacy)
    return legacy


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_sha256", None)
    discovery = copied.get("discovery", {})
    count_names = (
        "exact_title_identity_pair_count",
        "structured_primary_identity_pair_count",
        "body_only_identity_rejected_pair_count",
        "official_api_page_count",
    )
    if (
        copied.get("role") != RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("primary_identity_binding_required") is not True
        or copied.get("body_only_identity_binding_removed") is not True
        or copied.get("search_lead_title_blanked_before_fetch_effect") is not True
        or copied.get("ror_profile_lead_rewritten_to_official_api_before_fetch")
        is not True
        or copied.get("final_fetched_url_used_for_identity_binding") is not True
        or copied.get("official_api_identity_projected_before_shared_evidence")
        is not True
        or copied.get("official_profile_requires_exact_normalized_whole_title")
        is not True
        or copied.get("official_api_requires_url_record_id_and_ror_display_match")
        is not True
        or copied.get("identity_binding_precedes_entropy_or_task_credit") is not True
        or not isinstance(discovery, Mapping)
        or any(
            isinstance(discovery.get(name), bool)
            or not isinstance(discovery.get(name), int)
            or discovery.get(name, -1) < 0
            for name in count_names
        )
        or discovery.get("unique_page_pair_hit_count")
        != discovery.get("exact_title_identity_pair_count")
        + discovery.get("structured_primary_identity_pair_count")
        or discovery.get("admitted_replacement_count")
        != discovery.get("unknown_target_unique_pair_count")
        or discovery.get("admitted_replacement_count", 0)
        > discovery.get("unique_page_pair_hit_count", -1)
        or seal != frozen.paired.payload_sha256(unsigned)
    ):
        raise ValueError("V2.46.44 content-free receipt drifted")
    frozen.validate_receipt(_legacy_receipt(copied))
    return copied


def _receipt(**kwargs: Any) -> dict[str, Any]:
    value = frozen._receipt(**kwargs)
    value.pop("receipt_sha256")
    value["role"] = RECEIPT_ROLE
    value["policy_id"] = POLICY_ID
    value.update(
        {
            "primary_identity_binding_required": True,
            "body_only_identity_binding_removed": True,
            "search_lead_title_blanked_before_fetch_effect": True,
            "ror_profile_lead_rewritten_to_official_api_before_fetch": True,
            "final_fetched_url_used_for_identity_binding": True,
            "official_api_identity_projected_before_shared_evidence": True,
            "official_profile_requires_exact_normalized_whole_title": True,
            "official_api_requires_url_record_id_and_ror_display_match": True,
            "identity_binding_precedes_entropy_or_task_credit": True,
        }
    )
    value["receipt_sha256"] = frozen.paired.payload_sha256(value)
    return validate_receipt(value)


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("result_sha256", None)
    if (
        copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or seal != frozen.paired.payload_sha256(unsigned)
    ):
        raise ValueError("V2.46.44 primary-identity result drifted")
    validate_receipt(copied.get("receipt", {}))

    legacy = copy.deepcopy(copied)
    legacy.pop("result_sha256", None)
    legacy["role"] = frozen.ROLE
    legacy["policy_id"] = frozen.POLICY_ID
    legacy["receipt"] = _legacy_receipt(copied["receipt"])
    legacy["result_sha256"] = frozen.paired.payload_sha256(legacy)
    frozen.validate_result(legacy)
    return copied


def _frozen_function(
    function: Callable[..., Any], **overrides: Any
) -> Callable[..., Any]:
    if not isinstance(function, FunctionType) or function.__closure__ is not None:
        raise TypeError("V2.46.44 requires a closure-free Python function")
    namespace = dict(function.__globals__)
    namespace.update(overrides)
    copied = FunctionType(
        function.__code__,
        namespace,
        name=function.__name__,
        argdefs=function.__defaults__,
        closure=None,
    )
    copied.__kwdefaults__ = dict(function.__kwdefaults__ or {})
    copied.__annotations__ = dict(function.__annotations__)
    copied.__doc__ = function.__doc__
    copied.__module__ = __name__
    return copied


_RUN_TASK = _frozen_function(
    frozen.run_v24642_task,
    POLICY_ID=POLICY_ID,
    ROLE=ROLE,
    _lead_requests=_page_title_only_lead_requests,
    _page_vector=_final_url_page_vector,
    discover_pairs=discover_pairs,
    _receipt=_receipt,
    validate_result=validate_result,
)


def run_v24644_task(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """Run the inherited two-model-call task with the strict identity gate."""

    return _RUN_TASK(*args, **kwargs)


def binding_is_private_and_stable() -> bool:
    return (
        _RUN_TASK is not frozen.run_v24642_task
        and _RUN_TASK.__globals__["discover_pairs"] is discover_pairs
        and _RUN_TASK.__globals__["_lead_requests"]
        is _page_title_only_lead_requests
        and _RUN_TASK.__globals__["_page_vector"] is _final_url_page_vector
        and _RUN_TASK.__globals__["_receipt"] is _receipt
        and _RUN_TASK.__globals__["validate_result"] is validate_result
        and frozen.run_v24642_task.__globals__["discover_pairs"]
        is frozen.discover_pairs
        and frozen.run_v24642_task.__globals__["_lead_requests"]
        is frozen._lead_requests
        and frozen.run_v24642_task.__globals__["_page_vector"] is frozen._page_vector
        and frozen.run_v24642_task.__globals__["_receipt"] is frozen._receipt
        and frozen.run_v24642_task.__globals__["validate_result"]
        is frozen.validate_result
    )


if not binding_is_private_and_stable():
    raise RuntimeError("V2.46.44 private frozen binding drifted")


__all__ = [
    "ARMS",
    "POLICY_ID",
    "ROLE",
    "binding_is_private_and_stable",
    "discover_pairs",
    "normalized_identity",
    "primary_identity_bound_ror_suffixes",
    "run_v24644_task",
    "validate_receipt",
    "validate_result",
]
