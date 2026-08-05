"""Execution-scoped memo for the three repeated high-level validators.

V2.45.07 measured 107 V2.44.57, 11 V2.44.90 and 5 V2.44.96 validator
calls in one synthetic V2.45.03 child.  The existing V2.44.85 memo protects
the lower historical graph but each high-level call still recomputes its own
projection, posterior, receipt and deep-copy graph.

This successor does not weaken first validation.  For each of the three
explicit layers, the unchanged validator must succeed once.  A later hit in
the same context still recomputes the outer result seal and compares exact
canonical bytes and recursive Python type shape with the first input before
returning the original validator's deep-copy semantics.  Any drift falls
through to the unchanged validator and is recorded as a mismatch.  All
bindings are restored on every exit path.

The module performs no file, environment, network, model, search, fetch,
process, benchmark, evaluator, reward, score or credential access.
"""

from __future__ import annotations

import copy
import functools
import threading
from collections.abc import Mapping
from contextlib import AbstractContextManager
from dataclasses import dataclass
from typing import Any, Callable

from . import v24457_adaptive_entropy_support as adaptive
from . import v24490_entropy_targeted_support_search as targeted
from . import v24496_targeted_reserve_contradiction as reserve
from .v24485_execution_scoped_validation_memo import _snapshot


POLICY_ID = "v24508_execution_scoped_high_level_sealed_validation_memo_v1"
EXPECTED_LAYER_COUNT = 3
Validator = Callable[[Mapping[str, Any]], Any]


@dataclass(frozen=True)
class LayerSpec:
    name: str
    owner: Any
    original: Validator


LAYERS = (
    LayerSpec("v24457", adaptive, adaptive.validate_result),
    LayerSpec("v24490", targeted, targeted.validate_result),
    LayerSpec("v24496", reserve, reserve.validate_result),
)


def _deep_mapping(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise RuntimeError("V2.45.08 validator changed return type")
    return copy.deepcopy(dict(value))


class HighLevelValidationMemo(
    AbstractContextManager["HighLevelValidationMemo"]
):
    """Patch exactly three high-level validators for one worker execution."""

    def __init__(self) -> None:
        self._active = False
        self._lock = threading.RLock()
        self._cache: dict[str, tuple[str, bytes, str, dict[str, Any]]] = {}
        self._restorations: list[tuple[Any, str, Any]] = []
        self._stats = {
            spec.name: {"calls": 0, "misses": 0, "hits": 0, "mismatches": 0}
            for spec in LAYERS
        }

    def _wrapper(self, spec: LayerSpec) -> Validator:
        @functools.wraps(spec.original)
        def memoized(value: Mapping[str, Any]) -> Any:
            with self._lock:
                stats = self._stats[spec.name]
                stats["calls"] += 1
                try:
                    seal, raw, shape = _snapshot(value)
                except (TypeError, ValueError, OverflowError):
                    stats["misses"] += 1
                    stats["mismatches"] += 1
                    return spec.original(value)
                cached = self._cache.get(spec.name)
                if (
                    cached is not None
                    and cached[0] == seal
                    and cached[1] == raw
                    and cached[2] == shape
                ):
                    stats["hits"] += 1
                    return _deep_mapping(cached[3])
                if cached is not None:
                    stats["mismatches"] += 1
                stats["misses"] += 1
                validated = spec.original(value)
                after = _snapshot(value)
                if after != (seal, raw, shape):
                    raise RuntimeError("V2.45.08 validator mutated its input")
                frozen = _deep_mapping(validated)
                self._cache[spec.name] = (seal, raw, shape, frozen)
                return _deep_mapping(frozen)

        return memoized

    def __enter__(self) -> "HighLevelValidationMemo":
        if self._active:
            raise RuntimeError("V2.45.08 memo context is already active")
        if len(LAYERS) != EXPECTED_LAYER_COUNT:
            raise RuntimeError("V2.45.08 frozen validator surface drifted")
        if len({spec.name for spec in LAYERS}) != len(LAYERS):
            raise RuntimeError("V2.45.08 validator layer names collide")
        if any(spec.owner.validate_result is not spec.original for spec in LAYERS):
            raise RuntimeError("V2.45.08 validator binding drifted")
        try:
            for spec in LAYERS:
                self._restorations.append(
                    (spec.owner, "validate_result", spec.original)
                )
                setattr(spec.owner, "validate_result", self._wrapper(spec))
        except BaseException:
            self._restore()
            raise
        self._active = True
        return self

    def _restore(self) -> None:
        for owner, attribute, original in reversed(self._restorations):
            setattr(owner, attribute, original)
        self._restorations.clear()
        self._active = False

    def __exit__(self, *_: object) -> None:
        self._restore()
        self._cache.clear()

    def content_free_receipt(self) -> dict[str, Any]:
        layers = {
            name: dict(counts) for name, counts in sorted(self._stats.items())
        }
        return {
            "policy_id": POLICY_ID,
            "layer_count": len(LAYERS),
            "layers": layers,
            "total_calls": sum(item["calls"] for item in layers.values()),
            "total_misses": sum(item["misses"] for item in layers.values()),
            "total_hits": sum(item["hits"] for item in layers.values()),
            "total_mismatches": sum(
                item["mismatches"] for item in layers.values()
            ),
            "first_validation_uses_unchanged_frozen_validator": True,
            "cache_hit_recomputes_outer_seal_and_compares_exact_bytes_and_type_shape": True,
            "cache_hit_preserves_deep_copy_return_semantics": True,
            "cache_scope_single_context_single_worker_execution": True,
            "cache_entries_per_layer_at_most_one": True,
            "bindings_restored": not self._active and not self._restorations,
            "task_question_opaque_id_query_url_page_prediction_or_value_emitted": False,
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
            "file_environment_network_model_search_fetch_process_or_evaluator_accessed": False,
            "benchmark_launch_or_evaluator_authorized": False,
        }


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    layers = copied.get("layers")
    true_fields = (
        "first_validation_uses_unchanged_frozen_validator",
        "cache_hit_recomputes_outer_seal_and_compares_exact_bytes_and_type_shape",
        "cache_hit_preserves_deep_copy_return_semantics",
        "cache_scope_single_context_single_worker_execution",
        "cache_entries_per_layer_at_most_one",
        "bindings_restored",
    )
    false_fields = (
        "task_question_opaque_id_query_url_page_prediction_or_value_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "file_environment_network_model_search_fetch_process_or_evaluator_accessed",
        "benchmark_launch_or_evaluator_authorized",
    )
    if (
        copied.get("policy_id") != POLICY_ID
        or copied.get("layer_count") != EXPECTED_LAYER_COUNT
        or not isinstance(layers, Mapping)
        or set(layers) != {spec.name for spec in LAYERS}
        or any(
            not isinstance(item, Mapping)
            or any(
                isinstance(item.get(name), bool)
                or not isinstance(item.get(name), int)
                or item[name] < 0
                for name in ("calls", "misses", "hits", "mismatches")
            )
            or item["calls"] != item["misses"] + item["hits"]
            or item["mismatches"] > item["misses"]
            for item in layers.values()
        )
        or copied.get("total_calls")
        != sum(int(item["calls"]) for item in layers.values())
        or copied.get("total_misses")
        != sum(int(item["misses"]) for item in layers.values())
        or copied.get("total_hits")
        != sum(int(item["hits"]) for item in layers.values())
        or copied.get("total_mismatches")
        != sum(int(item["mismatches"]) for item in layers.values())
        or any(copied.get(name) is not True for name in true_fields)
        or any(copied.get(name) is not False for name in false_fields)
    ):
        raise ValueError("V2.45.08 high-level memo receipt drifted")
    return copied


def binding_contract() -> dict[str, Any]:
    return {
        "policy_id": POLICY_ID,
        "layer_names": [spec.name for spec in LAYERS],
        "layer_count": len(LAYERS),
        "copy_mode": "deep",
        "first_validation_unchanged": True,
        "cache_scope_one_worker_execution": True,
        "all_bindings_restored_on_exit": True,
        "same_seal_without_exact_bytes_and_type_shape_is_not_a_hit": True,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "file_environment_network_model_search_fetch_process_or_evaluator_accessed": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }


__all__ = [
    "EXPECTED_LAYER_COUNT",
    "HighLevelValidationMemo",
    "LAYERS",
    "POLICY_ID",
    "binding_contract",
    "validate_receipt",
]
