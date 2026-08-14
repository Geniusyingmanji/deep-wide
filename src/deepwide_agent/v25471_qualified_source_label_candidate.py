"""Pure qualified-source-label candidates over V2.54.64.

V2.54.70 observed row-key/page binding on 16/20 tasks and 30 pages, but no
structured field surface.  The narrow missing shape was a two-cell pipe row
whose left label ended in one requested visible column after exactly one
source qualifier (for example, ``TLD type`` for visible column ``Type``).

This successor preserves every V2.54.64 candidate and adds only that grammar.
The requested field tokens must be a complete suffix of the source label with
exactly one preceding qualifier token.  The label and value must be the two
cells of one source line on an already unique URL-path-and-surface-bound page.
No vocabulary, synonym, ontology, host rule, task rule, or model inference is
used.  Exact labels remain the parent's responsibility; multiple observations
for one coordinate, conflicts, Unknown, surface-only edits, and list collapse
fail closed under the frozen V2.54.64 conflict resolver.

The module has no filesystem, process, environment, network, model, search,
fetch, evaluator, benchmark-label, mapping, gold, score, reward, credential,
or historical-outcome capability.  Entropy/information gain assigns no signed
credit and this build authorizes no launch.
"""

from __future__ import annotations

import copy
import re
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from typing import Any

from . import v25004_identity_bound_detail_fields as identity_parent
from . import v25432_source_authoritative_field_candidate as source_parent
from . import v25464_row_key_bound_structured_source_candidate as parent


POLICY_ID = "v25471_qualified_source_label_candidate_v1"
REGISTRY_ROLE = "v25471_qualified_source_label_candidate_registry"
REGISTRY_RECEIPT_ROLE = "v25471_content_free_candidate_registry_receipt"
APPLICATION_ROLE = "v25471_qualified_source_label_candidate_application"
APPLICATION_RECEIPT_ROLE = "v25471_content_free_candidate_application_receipt"

PAGE_KEYS = parent.PAGE_KEYS
MAXIMUM_CANDIDATES = parent.MAXIMUM_CANDIDATES
_SOURCE_KINDS = frozenset({*parent._SOURCE_KINDS, "qualified_source_label_pipe_record"})
_IDENTITY_BINDING_KINDS = parent._IDENTITY_BINDING_KINDS
_CANDIDATE_ID = re.compile(r"C[0-9]{3}")

_COUNT_FIELDS = (
    *parent._COUNT_FIELDS,
    "qualified_label_surface_count",
    "qualified_label_observation_count",
)


payload_sha256 = parent.payload_sha256


def _qualified_field(label: str, columns: Sequence[str]) -> tuple[int, str] | None:
    label_tokens = identity_parent._tokens(label)
    if not label_tokens:
        return None
    matches: list[tuple[int, str]] = []
    for index, field in enumerate(columns):
        if index == 0:
            continue
        field_tokens = identity_parent._tokens(field)
        if (
            field_tokens
            and len(label_tokens) == len(field_tokens) + 1
            and tuple(label_tokens[-len(field_tokens):]) == tuple(field_tokens)
            and len(label_tokens[0]) >= 2
        ):
            matches.append((index, str(field)))
    return matches[0] if len(matches) == 1 else None


def _qualified_observations(
    rows: Sequence[Sequence[str]],
    pages: Sequence[Mapping[str, Any]],
    *,
    columns: Sequence[str],
    counts: Counter[str],
) -> list[dict[str, Any]]:
    bound, _bound_counts = parent._bound_pages(rows, pages)
    row_map = {source_parent._key(row[0]): index for index, row in enumerate(rows)}
    output: list[dict[str, Any]] = []
    for page in bound:
        row_index = row_map[source_parent._key(page["row_identity"])]
        for start, end, line in source_parent._line_spans(str(page["content"])):
            cells = source_parent._pipe_cells(line)
            if cells is None or len(cells) != 2 or source_parent._separator(cells):
                continue
            qualified = _qualified_field(cells[0], columns)
            if qualified is None:
                continue
            counts["qualified_label_surface_count"] += 1
            column_index, field = qualified
            counts["raw_observation_count"] += 1
            value = source_parent._safe_cell(cells[1])
            quote = str(page["content"])[start:end]
            if (
                value is None
                or not 1 <= len(quote) <= source_parent.MAXIMUM_QUOTE_CHARACTERS
                or str(page["content"]).count(quote) != 1
                or cells[0] not in quote
                or value not in quote
            ):
                continue
            output.append(
                {
                    "page_ordinal": int(page["page_ordinal"]),
                    "source_url": str(page["url"]),
                    "source_host": str(page["source_host"]),
                    "quote_start": int(start),
                    "quote_end": int(end),
                    "exact_quote": quote,
                    "row_identity": str(rows[row_index][0]),
                    "source_field": str(cells[0]),
                    "field": field,
                    "old_value": str(rows[row_index][column_index]),
                    "exact_value": value,
                    "source_kind": "qualified_source_label_pipe_record",
                    "identity_binding_kind": "unique_url_path_and_surface_page_binding",
                    "row_index": row_index,
                    "column_index": column_index,
                    "origin": "qualified_label",
                }
            )
            counts["evidence_closed_observation_count"] += 1
            counts["qualified_label_observation_count"] += 1
    return output


def _parent_observations(registry: Mapping[str, Any], rows: Sequence[Sequence[str]], columns: Sequence[str]) -> list[dict[str, Any]]:
    checked = parent.validate_registry(registry)
    row_map = {source_parent._key(row[0]): index for index, row in enumerate(rows)}
    column_map = {source_parent._key(field): index for index, field in enumerate(columns)}
    output: list[dict[str, Any]] = []
    for item in checked["candidates"]:
        row_index = row_map[source_parent._key(item["row_identity"])]
        column_index = column_map[source_parent._key(item["field"])]
        output.append(
            {
                **{name: copy.deepcopy(item[name]) for name in (
                    "page_ordinal", "source_url", "source_host", "quote_start",
                    "quote_end", "exact_quote", "row_identity", "source_field",
                    "field", "old_value", "exact_value", "source_kind",
                    "identity_binding_kind",
                )},
                "row_index": row_index,
                "column_index": column_index,
                "origin": "parent",
            }
        )
    return output


def _candidate(observation: Mapping[str, Any], candidate_id: str) -> dict[str, Any]:
    value: dict[str, Any] = {
        "candidate_id": candidate_id,
        **{name: copy.deepcopy(observation[name]) for name in (
            "page_ordinal", "source_url", "source_host", "quote_start", "quote_end",
            "exact_quote", "row_identity", "source_field", "field", "old_value",
            "exact_value", "source_kind", "identity_binding_kind",
        )},
        "source_coordinate_is_unique": True,
        "target_table_coordinate_is_unique": True,
        "value_is_source_extracted_not_model_generated": True,
        "material_semantic_change_not_surface_only": True,
        "list_cardinality_noncollapse": True,
    }
    value["candidate_payload_sha256"] = payload_sha256(value)
    return validate_candidate(value)


def validate_candidate(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("candidate_payload_sha256", None)
    canonical = source_parent._canonical_url(copied.get("source_url"))
    strings = tuple(copied.get(name) for name in (
        "exact_quote", "row_identity", "source_field", "field", "old_value", "exact_value"
    ))
    if (
        set(copied) != parent._CANDIDATE_KEYS
        or _CANDIDATE_ID.fullmatch(str(copied.get("candidate_id", ""))) is None
        or not isinstance(copied.get("page_ordinal"), int)
        or isinstance(copied.get("page_ordinal"), bool)
        or copied["page_ordinal"] < 1
        or canonical is None
        or copied.get("source_url") != canonical[0]
        or copied.get("source_host") != canonical[1]
        or not isinstance(copied.get("quote_start"), int)
        or not isinstance(copied.get("quote_end"), int)
        or copied["quote_start"] < 0
        or copied["quote_end"] <= copied["quote_start"]
        or any(not isinstance(item, str) or not item or "\x00" in item for item in strings)
        or len(copied["exact_quote"]) != copied["quote_end"] - copied["quote_start"]
        or copied["source_field"] not in copied["exact_quote"]
        or copied["exact_value"] not in copied["exact_quote"]
        or source_parent._safe_cell(copied["exact_value"]) != copied["exact_value"]
        or parent._surface_equivalent(copied["field"], copied["old_value"], copied["exact_value"])
        or copied.get("source_kind") not in _SOURCE_KINDS
        or copied.get("identity_binding_kind") not in _IDENTITY_BINDING_KINDS
        or any(copied.get(name) is not True for name in (
            "source_coordinate_is_unique", "target_table_coordinate_is_unique",
            "value_is_source_extracted_not_model_generated",
            "material_semantic_change_not_surface_only", "list_cardinality_noncollapse",
        ))
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.54.71 candidate drifted")
    if copied["source_kind"] == "qualified_source_label_pipe_record":
        qualified = _qualified_field(copied["source_field"], ("__key__", copied["field"]))
        if qualified is None or qualified[1] != copied["field"]:
            raise ValueError("V2.54.71 qualified source label drifted")
    return copied


def _registry_receipt(counts: Mapping[str, int]) -> dict[str, Any]:
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": REGISTRY_RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        **{name: int(counts.get(name, 0)) for name in _COUNT_FIELDS},
        "parent_v25464_candidates_preserved": True,
        "qualified_label_is_exact_visible_field_token_suffix": True,
        "exactly_one_source_qualifier_token_required": True,
        "label_and_value_are_one_two_cell_pipe_source_line": True,
        "page_is_already_unique_url_path_and_surface_bound": True,
        "source_field_and_verbatim_value_remain_sealed": True,
        "synonym_ontology_host_task_or_model_alias_absent": True,
        "conflict_ambiguity_unknown_surface_only_list_collapse_or_shape_change_fails_closed": True,
        parent.CONTENT_FREE_FLAG: False,
        parent.PRIVILEGED_READ_FLAG: False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "file_environment_process_network_model_search_fetch_or_evaluator_accessed": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_payload_sha256"] = payload_sha256(value)
    return validate_registry_receipt(value)


def validate_registry_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    true_flags = (
        "parent_v25464_candidates_preserved",
        "qualified_label_is_exact_visible_field_token_suffix",
        "exactly_one_source_qualifier_token_required",
        "label_and_value_are_one_two_cell_pipe_source_line",
        "page_is_already_unique_url_path_and_surface_bound",
        "source_field_and_verbatim_value_remain_sealed",
        "synonym_ontology_host_task_or_model_alias_absent",
        "conflict_ambiguity_unknown_surface_only_list_collapse_or_shape_change_fails_closed",
    )
    false_flags = (
        parent.CONTENT_FREE_FLAG,
        parent.PRIVILEGED_READ_FLAG,
        "entropy_or_information_gain_assigns_signed_credit",
        "file_environment_process_network_model_search_fetch_or_evaluator_accessed",
        "benchmark_launch_or_evaluator_authorized",
    )
    expected = {"artifact_version", "role", "policy_id", *_COUNT_FIELDS, *true_flags, *false_flags, "receipt_payload_sha256"}
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != REGISTRY_RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or any(not isinstance(copied.get(name), int) or isinstance(copied.get(name), bool) or copied[name] < 0 for name in _COUNT_FIELDS)
        or copied["available_candidate_count"] > MAXIMUM_CANDIDATES
        or copied["applied_coordinate_count"] != copied["available_candidate_count"]
        or copied["positive_signed_credit_count"] != 0
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.54.71 registry receipt drifted")
    return copied


def build_candidate_registry(base_prediction: str, *, columns: Sequence[str], pages: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    required, rows = source_parent._canonical_table(str(base_prediction), columns)
    parent_registry = parent.build_candidate_registry(str(base_prediction), columns=required, pages=pages)
    parent_receipt = parent.validate_registry_receipt(parent_registry["content_free_receipt"])
    counts = Counter({name: int(parent_receipt.get(name, 0)) for name in parent._COUNT_FIELDS})
    observations = _parent_observations(parent_registry, rows, required)
    observations.extend(_qualified_observations(rows, pages, columns=required, counts=counts))
    dedup: dict[tuple[Any, ...], dict[str, Any]] = {}
    for item in observations:
        key = (item["page_ordinal"], item["quote_start"], item["quote_end"], item["row_index"], item["column_index"], source_parent._key(item["exact_value"]))
        if key in dedup:
            counts["exact_duplicate_observation_count"] += 1
        else:
            dedup[key] = item
    grouped: defaultdict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
    for item in dedup.values():
        grouped[(item["row_index"], item["column_index"])].append(item)
    counts["coordinate_group_count"] = len(grouped)
    retained: list[dict[str, Any]] = []
    for coordinate in sorted(grouped):
        items = grouped[coordinate]
        normalized = {source_parent._key(item["exact_value"]) for item in items}
        if len(items) != 1:
            counts["conflicting_value_coordinate_count" if len(normalized) > 1 else "ambiguous_same_value_coordinate_count"] += 1
            continue
        item = items[0]
        if source_parent._key(item["old_value"]) == source_parent._key(item["exact_value"]):
            counts["unchanged_coordinate_count"] += 1
            continue
        if parent._surface_equivalent(item["field"], item["old_value"], item["exact_value"]):
            counts["surface_equivalent_rejected_coordinate_count"] += 1
            continue
        if source_parent._column_key(item["field"]) in source_parent.LIST_COLUMN_KEYS and source_parent._list_cardinality(item["old_value"]) >= 2 and source_parent._list_cardinality(item["exact_value"]) < source_parent._list_cardinality(item["old_value"]):
            counts["list_collapse_rejected_coordinate_count"] += 1
            continue
        retained.append(item)
    retained.sort(key=lambda item: (item["row_index"], item["column_index"], item["page_ordinal"], item["quote_start"]))
    if len(retained) > MAXIMUM_CANDIDATES:
        counts["truncated_unique_candidate_count"] = len(retained) - MAXIMUM_CANDIDATES
        retained = retained[:MAXIMUM_CANDIDATES]
    candidates = [_candidate(item, f"C{index:03d}") for index, item in enumerate(retained, 1)]
    counts["available_candidate_count"] = len(candidates)
    counts["applied_coordinate_count"] = len(candidates)
    counts["positive_signed_credit_count"] = 0
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": REGISTRY_ROLE,
        "policy_id": POLICY_ID,
        "base_prediction_sha256": __import__("hashlib").sha256(str(base_prediction).encode()).hexdigest(),
        "columns": list(required),
        "candidates": candidates,
        "content_free_receipt": _registry_receipt(counts),
    }
    value["artifact_payload_sha256"] = payload_sha256(value)
    return validate_registry(value)


def validate_registry(value: Mapping[str, Any], *, base_prediction: str | None = None, columns: Sequence[str] | None = None, pages: Sequence[Mapping[str, Any]] | None = None) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value)); unsigned = dict(copied); seal = unsigned.pop("artifact_payload_sha256", None)
    candidates = copied.get("candidates"); receipt = copied.get("content_free_receipt")
    if (
        set(copied) != {"artifact_version", "role", "policy_id", "base_prediction_sha256", "columns", "candidates", "content_free_receipt", "artifact_payload_sha256"}
        or copied.get("artifact_version") != 1 or copied.get("role") != REGISTRY_ROLE or copied.get("policy_id") != POLICY_ID
        or not isinstance(copied.get("columns"), list) or len(copied["columns"]) < 1
        or not isinstance(candidates, list) or len(candidates) > MAXIMUM_CANDIDATES
        or [validate_candidate(item) for item in candidates] != candidates
        or [item["candidate_id"] for item in candidates] != [f"C{index:03d}" for index in range(1, len(candidates)+1)]
        or not isinstance(receipt, Mapping) or validate_registry_receipt(receipt) != dict(receipt)
        or receipt["available_candidate_count"] != len(candidates)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.54.71 registry drifted")
    if base_prediction is not None:
        if columns is None or pages is None:
            raise ValueError("V2.54.71 replay inputs incomplete")
        replay = build_candidate_registry(str(base_prediction), columns=columns, pages=pages)
        if replay != copied:
            raise ValueError("V2.54.71 registry replay drifted")
    return copied


def build_application(base_prediction: str, *, columns: Sequence[str], pages: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    registry = build_candidate_registry(base_prediction, columns=columns, pages=pages)
    required, rows = source_parent._canonical_table(str(base_prediction), columns)
    row_map = {source_parent._key(row[0]): index for index, row in enumerate(rows)}
    column_map = {source_parent._key(field): index for index, field in enumerate(required)}
    edited = [list(row) for row in rows]
    for item in registry["candidates"]:
        edited[row_map[source_parent._key(item["row_identity"])]][column_map[source_parent._key(item["field"])]] = item["exact_value"]
    candidate_prediction = source_parent.table_parent._render_table(required, edited)
    count = len(registry["candidates"])
    receipt = {
        "artifact_version": 1, "role": APPLICATION_RECEIPT_ROLE, "policy_id": POLICY_ID,
        "available_candidate_count": count, "selected_candidate_count": count,
        "applied_coordinate_count": count, "positive_signed_credit_count": 0,
        "candidate_prediction_changed": bool(count), "candidate_identity_handoff": not count,
        "all_candidates_applied_deterministically": True,
        "zero_candidate_preserves_parent_byte_exact": True,
        "schema_row_count_order_keys_and_other_cells_preserved": True,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    receipt["receipt_payload_sha256"] = payload_sha256(receipt)
    value = {
        "artifact_version": 1, "role": APPLICATION_ROLE, "policy_id": POLICY_ID,
        "control_prediction": str(base_prediction), "candidate_prediction": candidate_prediction,
        "control_prediction_sha256": __import__("hashlib").sha256(str(base_prediction).encode()).hexdigest(),
        "candidate_prediction_sha256": __import__("hashlib").sha256(candidate_prediction.encode()).hexdigest(),
        "private_candidate_registry": registry, "content_free_receipt": receipt,
    }
    value["artifact_payload_sha256"] = payload_sha256(value)
    return validate_application(value)


def validate_application(value: Mapping[str, Any], *, base_prediction: str | None = None, columns: Sequence[str] | None = None, pages: Sequence[Mapping[str, Any]] | None = None) -> dict[str, Any]:
    copied=copy.deepcopy(dict(value));unsigned=dict(copied);seal=unsigned.pop("artifact_payload_sha256",None);reg=copied.get("private_candidate_registry");receipt=copied.get("content_free_receipt")
    if not isinstance(reg,Mapping):raise ValueError("V2.54.71 application registry absent")
    checked=validate_registry(reg);count=len(checked["candidates"]);control=copied.get("control_prediction");candidate_prediction=copied.get("candidate_prediction")
    expected_receipt={"artifact_version":1,"role":APPLICATION_RECEIPT_ROLE,"policy_id":POLICY_ID,"available_candidate_count":count,"selected_candidate_count":count,"applied_coordinate_count":count,"positive_signed_credit_count":0,"candidate_prediction_changed":bool(count),"candidate_identity_handoff":not count,"all_candidates_applied_deterministically":True,"zero_candidate_preserves_parent_byte_exact":True,"schema_row_count_order_keys_and_other_cells_preserved":True,"entropy_or_information_gain_assigns_signed_credit":False,"benchmark_launch_or_evaluator_authorized":False}
    expected_receipt["receipt_payload_sha256"]=payload_sha256(expected_receipt)
    if set(copied)!={"artifact_version","role","policy_id","control_prediction","candidate_prediction","control_prediction_sha256","candidate_prediction_sha256","private_candidate_registry","content_free_receipt","artifact_payload_sha256"} or copied.get("role")!=APPLICATION_ROLE or copied.get("policy_id")!=POLICY_ID or not isinstance(control,str) or not isinstance(candidate_prediction,str) or copied.get("control_prediction_sha256")!=__import__("hashlib").sha256(control.encode()).hexdigest() or copied.get("candidate_prediction_sha256")!=__import__("hashlib").sha256(candidate_prediction.encode()).hexdigest() or receipt!=expected_receipt or (count==0 and candidate_prediction!=control) or (count>0 and candidate_prediction==control) or seal!=payload_sha256(unsigned):raise ValueError("V2.54.71 application drifted")
    if base_prediction is not None:
        if columns is None or pages is None:raise ValueError("V2.54.71 application replay inputs incomplete")
        replay=build_application(str(base_prediction),columns=columns,pages=pages)
        if replay!=copied:raise ValueError("V2.54.71 application replay drifted")
    return copied


__all__ = ["APPLICATION_RECEIPT_ROLE", "APPLICATION_ROLE", "POLICY_ID", "REGISTRY_RECEIPT_ROLE", "REGISTRY_ROLE", "build_application", "build_candidate_registry", "validate_application", "validate_candidate", "validate_registry", "validate_registry_receipt"]
