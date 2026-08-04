"""Execution-scoped memoization for immutable sealed result validators.

The V2.44.84 external gate showed that network effects close before workers
time out, while the frozen validation graph repeatedly revalidates identical
sealed results.  This append-only module does not weaken first validation: the
original validator must succeed once for each whitelisted layer and exact
sealed payload.  Later calls in the same single-worker execution may return
the original validator's copy semantics only after all of the following hold:

* the current outer SHA-256 seal recomputes exactly;
* canonical JSON bytes exactly equal the first validated input;
* a recursive type-shape digest exactly matches, preserving list/tuple and
  bool/int distinctions that JSON alone would conflate.

Any mismatch falls through to the unchanged validator.  The cache exists only
inside one context manager, has one entry per whitelisted layer, and patches
an explicit frozen list of 17 bindings.  All bindings are restored on exit,
including exceptions.  The module performs no filesystem, environment,
network, model, search, fetch, process, benchmark, evaluator, reward, score,
or credential access.
"""

from __future__ import annotations

import copy
import functools
import hashlib
import json
import math
import threading
from collections.abc import Mapping
from contextlib import AbstractContextManager
from dataclasses import dataclass
from typing import Any, Callable

from . import v24325_shared_prefix_revision_runtime as v24325
from . import v24342_semantic_active_runtime as v24342
from . import v24349_structural_semantic_runtime as v24349
from . import v24355_explicit_partition_runtime as v24355
from . import v24362_two_verifier_partition_runtime as v24362
from . import v24378_adaptive_heldout_verifier_runtime as v24378
from . import v24383_active_verifier_query_runtime as v24383
from . import v24390_uncertainty_active_evidence_runtime as v24390
from . import v24391_uncertainty_active_evidence_runner as v24391
from . import v24407_structured_uncertainty_recovery as v24407
from . import v24415_effect_equivalent_structured_runner as v24415
from . import v24429_title_anchor_uncertainty_recovery as v24429
from . import v24430_title_anchor_effect_runner as v24430
from . import v24437_narrative_title_uncertainty_recovery as v24437
from . import v24438_bounded_narrative_effect_runner as v24438
from . import v24447_third_source_entropy_to_decision as v24447


POLICY_ID = "v24485_execution_scoped_sealed_validation_memo_v1"
MAXIMUM_LAYER_COUNT = 8
EXPECTED_BINDING_COUNT = 17
HEX64 = frozenset("0123456789abcdef")
Validator = Callable[[Mapping[str, Any]], Any]


@dataclass(frozen=True)
class LayerSpec:
    name: str
    owner: Any
    original: Validator
    copy_mode: str


@dataclass(frozen=True)
class BindingSpec:
    owner: Any
    attribute: str
    layer: str


LAYERS = (
    LayerSpec("v24325", v24325, v24325.validate_result, "none"),
    LayerSpec("v24342", v24342, v24342.validate_result, "shallow"),
    LayerSpec("v24349", v24349, v24349.validate_result, "shallow"),
    LayerSpec("v24390", v24390, v24390.validate_result, "deep"),
    LayerSpec("v24407", v24407, v24407.validate_result, "deep"),
    LayerSpec("v24429", v24429, v24429.validate_result, "deep"),
    LayerSpec("v24437", v24437, v24437.validate_result, "deep"),
    LayerSpec("v24447", v24447, v24447.validate_result, "deep"),
)
BINDINGS = (
    BindingSpec(v24325, "validate_result", "v24325"),
    BindingSpec(v24342, "validate_result", "v24342"),
    BindingSpec(v24349, "validate_result", "v24349"),
    BindingSpec(v24355, "validate_parent_result", "v24349"),
    BindingSpec(v24362, "validate_parent_result", "v24349"),
    BindingSpec(v24378, "validate_parent_result", "v24349"),
    BindingSpec(v24383, "validate_parent_result", "v24349"),
    BindingSpec(v24390, "validate_parent_result", "v24349"),
    BindingSpec(v24390, "validate_result", "v24390"),
    BindingSpec(v24391, "validate_result", "v24390"),
    BindingSpec(v24407, "validate_result", "v24407"),
    BindingSpec(v24415, "validate_recovery_result", "v24407"),
    BindingSpec(v24429, "validate_result", "v24429"),
    BindingSpec(v24430, "validate_recovery_result", "v24429"),
    BindingSpec(v24437, "validate_result", "v24437"),
    BindingSpec(v24438, "validate_recovery_result", "v24437"),
    BindingSpec(v24447, "validate_result", "v24447"),
)


def _seal(value: Mapping[str, Any]) -> str:
    seal = value.get("result_sha256")
    if (
        not isinstance(seal, str)
        or len(seal) != 64
        or any(character not in HEX64 for character in seal)
    ):
        raise ValueError("V2.44.85 result seal is absent")
    unsigned = dict(value)
    unsigned.pop("result_sha256", None)
    recomputed = hashlib.sha256(
        json.dumps(
            unsigned,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()
    if recomputed != seal:
        raise ValueError("V2.44.85 result seal drifted")
    return seal


def _canonical_bytes(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _shape(value: object, output: bytearray) -> None:
    kind = type(value)
    if kind is dict:
        output.extend(b"d")
        output.extend(str(len(value)).encode("ascii"))
        output.extend(b":")
        for key in sorted(value):
            if type(key) is not str:
                raise TypeError("V2.44.85 mapping key is not text")
            encoded = key.encode("utf-8")
            output.extend(b"k")
            output.extend(str(len(encoded)).encode("ascii"))
            output.extend(b":")
            output.extend(encoded)
            _shape(value[key], output)
    elif kind is list or kind is tuple:
        output.extend(b"l" if kind is list else b"t")
        output.extend(str(len(value)).encode("ascii"))
        output.extend(b":")
        for item in value:
            _shape(item, output)
    elif kind is str:
        output.extend(b"s")
    elif kind is bool:
        output.extend(b"b")
    elif kind is int:
        output.extend(b"i")
    elif kind is float:
        if not math.isfinite(value):
            raise ValueError("V2.44.85 nonfinite float is not cacheable")
        output.extend(b"f")
    elif value is None:
        output.extend(b"n")
    else:
        raise TypeError("V2.44.85 result contains an unsupported type")


def _snapshot(value: Mapping[str, Any]) -> tuple[str, bytes, str]:
    if not isinstance(value, Mapping):
        raise TypeError("V2.44.85 result is not a mapping")
    seal = _seal(value)
    raw = _canonical_bytes(value)
    shape = bytearray()
    _shape(value, shape)
    return seal, raw, hashlib.sha256(shape).hexdigest()


def _copy_result(mode: str, value: Any) -> Any:
    if mode == "none":
        if value is not None:
            raise RuntimeError("V2.44.85 void validator changed return type")
        return None
    if not isinstance(value, Mapping):
        raise RuntimeError("V2.44.85 mapping validator changed return type")
    if mode == "shallow":
        return dict(value)
    if mode == "deep":
        return copy.deepcopy(dict(value))
    raise RuntimeError("V2.44.85 unknown copy mode")


class ExecutionValidationMemo(AbstractContextManager["ExecutionValidationMemo"]):
    """Patch the exact frozen validator graph for one worker execution."""

    def __init__(self) -> None:
        self._active = False
        self._lock = threading.RLock()
        self._cache: dict[str, tuple[str, bytes, str, Any]] = {}
        self._wrappers: dict[str, Validator] = {}
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
                    return _copy_result(spec.copy_mode, cached[3])
                if cached is not None:
                    stats["mismatches"] += 1
                stats["misses"] += 1
                validated = spec.original(value)
                after_seal, after_raw, after_shape = _snapshot(value)
                if (after_seal, after_raw, after_shape) != (seal, raw, shape):
                    raise RuntimeError("V2.44.85 validator mutated its input")
                self._cache[spec.name] = (
                    seal,
                    raw,
                    shape,
                    _copy_result(spec.copy_mode, validated),
                )
                return _copy_result(spec.copy_mode, validated)

        return memoized

    def __enter__(self) -> "ExecutionValidationMemo":
        if self._active:
            raise RuntimeError("V2.44.85 memo context is already active")
        if len(LAYERS) != MAXIMUM_LAYER_COUNT or len(BINDINGS) != EXPECTED_BINDING_COUNT:
            raise RuntimeError("V2.44.85 frozen validator surface drifted")
        layers = {spec.name: spec for spec in LAYERS}
        if len(layers) != len(LAYERS):
            raise RuntimeError("V2.44.85 validator layer names collide")
        for binding in BINDINGS:
            spec = layers.get(binding.layer)
            if spec is None or getattr(binding.owner, binding.attribute) is not spec.original:
                raise RuntimeError("V2.44.85 validator binding drifted")
        self._wrappers = {
            name: self._wrapper(spec) for name, spec in layers.items()
        }
        try:
            for binding in BINDINGS:
                original = getattr(binding.owner, binding.attribute)
                self._restorations.append(
                    (binding.owner, binding.attribute, original)
                )
                setattr(
                    binding.owner,
                    binding.attribute,
                    self._wrappers[binding.layer],
                )
        except BaseException:
            self._restore()
            raise
        self._active = True
        return self

    def _restore(self) -> None:
        for owner, attribute, original in reversed(self._restorations):
            setattr(owner, attribute, original)
        self._restorations.clear()
        self._wrappers.clear()
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
            "binding_count": len(BINDINGS),
            "layers": layers,
            "total_calls": sum(item["calls"] for item in layers.values()),
            "total_misses": sum(item["misses"] for item in layers.values()),
            "total_hits": sum(item["hits"] for item in layers.values()),
            "total_mismatches": sum(
                item["mismatches"] for item in layers.values()
            ),
            "first_validation_uses_unchanged_frozen_validator": True,
            "cache_hit_recomputes_outer_seal_and_compares_exact_bytes_and_type_shape": True,
            "cache_scope_single_context_single_worker_execution": True,
            "cache_entries_per_layer_at_most_one": all(
                name not in self._cache or self._cache[name] is not None
                for name in layers
            ),
            "bindings_restored": not self._active and not self._restorations,
            "task_question_opaque_id_query_url_page_prediction_or_value_emitted": False,
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
            "file_environment_network_model_search_fetch_process_or_evaluator_accessed": False,
            "benchmark_launch_or_evaluator_authorized": False,
        }


def binding_contract() -> dict[str, Any]:
    return {
        "policy_id": POLICY_ID,
        "layer_names": [spec.name for spec in LAYERS],
        "copy_modes": {spec.name: spec.copy_mode for spec in LAYERS},
        "binding_names": [
            f"{binding.owner.__name__}:{binding.attribute}:{binding.layer}"
            for binding in BINDINGS
        ],
        "layer_count": len(LAYERS),
        "binding_count": len(BINDINGS),
        "first_validation_unchanged": True,
        "cache_scope_one_worker_execution": True,
        "all_bindings_restored_on_exit": True,
        "same_seal_without_exact_bytes_and_type_shape_is_not_a_hit": True,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "file_environment_network_model_search_fetch_process_or_evaluator_accessed": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }


__all__ = [
    "BINDINGS",
    "EXPECTED_BINDING_COUNT",
    "ExecutionValidationMemo",
    "LAYERS",
    "MAXIMUM_LAYER_COUNT",
    "POLICY_ID",
    "binding_contract",
]
