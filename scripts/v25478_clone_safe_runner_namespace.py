"""Pure clone-safe namespace assembly for versioned external runners.

Several external runners reuse frozen function bodies through
``types.FunctionType``.  Copying only the visible wrapper module globals is
insufficient because an already-cloned source function may execute in a
private namespace containing standard-library modules and helper classes that
the wrapper module never exports.  V2.54.76 exposed this at the first lease
check: the cloned body referenced ``fcntl`` but its new globals did not.

This helper merges the actual ``__globals__`` mappings of every source
function, then overlays the visible source module and explicit successor
bindings.  It recursively inspects nested code objects and fails before any
effect if a non-builtin ``LOAD_GLOBAL`` cannot be resolved.  All cloned
functions share one immutable-at-construction namespace so cross-calls bind
to the successor clones rather than the frozen parent functions.

The module performs no file, environment, process, network, model, search,
fetch, evaluator, benchmark, or credential access and authorizes no launch.
"""

from __future__ import annotations

import builtins
import copy
import dis
import types
from collections.abc import Callable, Mapping, Sequence
from typing import Any


POLICY_ID = "v25478_clone_safe_runner_namespace_v1"


def _code_global_names(code: types.CodeType) -> set[str]:
    output = {
        str(instruction.argval)
        for instruction in dis.get_instructions(code)
        if instruction.opname in {"LOAD_GLOBAL", "STORE_GLOBAL", "DELETE_GLOBAL"}
        and isinstance(instruction.argval, str)
    }
    for constant in code.co_consts:
        if isinstance(constant, types.CodeType):
            output.update(_code_global_names(constant))
    return output


def referenced_global_names(function: Callable[..., Any]) -> tuple[str, ...]:
    if not isinstance(function, types.FunctionType):
        raise TypeError("V2.54.78 source must be a Python function")
    return tuple(sorted(_code_global_names(function.__code__)))


def build_namespace(
    functions: Sequence[Callable[..., Any]],
    *,
    visible_globals: Mapping[str, Any],
    overrides: Mapping[str, Any],
) -> dict[str, Any]:
    if isinstance(functions, (str, bytes)) or not functions:
        raise ValueError("V2.54.78 source function vector is empty")
    namespace: dict[str, Any] = {}
    for function in functions:
        if not isinstance(function, types.FunctionType):
            raise TypeError("V2.54.78 source function vector drifted")
        namespace.update(function.__globals__)
    namespace.update(dict(visible_globals))
    namespace.update(dict(overrides))
    required = set().union(*(referenced_global_names(function) for function in functions))
    missing = sorted(
        name
        for name in required
        if name not in namespace and not hasattr(builtins, name)
    )
    if missing:
        raise RuntimeError(f"V2.54.78 unresolved clone globals: {missing}")
    return namespace


def clone_group(
    sources: Mapping[str, Callable[..., Any]],
    *,
    visible_globals: Mapping[str, Any],
    overrides: Mapping[str, Any],
    rename_from: str,
    rename_to: str,
) -> tuple[dict[str, Any], dict[str, Callable[..., Any]]]:
    if not sources or any(not isinstance(name, str) or not name for name in sources):
        raise ValueError("V2.54.78 source mapping drifted")
    functions = list(sources.values())
    namespace = build_namespace(
        functions, visible_globals=visible_globals, overrides=overrides
    )
    clones: dict[str, Callable[..., Any]] = {}
    for name, function in sources.items():
        cloned = types.FunctionType(
            function.__code__,
            namespace,
            name=function.__name__.replace(str(rename_from), str(rename_to)),
            argdefs=function.__defaults__,
            closure=function.__closure__,
        )
        cloned.__kwdefaults__ = dict(function.__kwdefaults__ or {})
        cloned.__annotations__ = copy.deepcopy(function.__annotations__)
        cloned.__doc__ = function.__doc__
        clones[name] = cloned
    namespace.update(clones)
    unresolved = {
        name: tuple(
            global_name
            for global_name in referenced_global_names(function)
            if global_name not in namespace and not hasattr(builtins, global_name)
        )
        for name, function in clones.items()
    }
    unresolved = {name: values for name, values in unresolved.items() if values}
    if unresolved:
        raise RuntimeError(f"V2.54.78 cloned namespace unresolved: {unresolved}")
    return namespace, clones


def content_free_receipt(
    sources: Mapping[str, Callable[..., Any]], namespace: Mapping[str, Any]
) -> dict[str, Any]:
    required = {
        name: referenced_global_names(function) for name, function in sources.items()
    }
    unresolved = {
        name: [
            item
            for item in names
            if item not in namespace and not hasattr(builtins, item)
        ]
        for name, names in required.items()
    }
    unresolved = {name: items for name, items in unresolved.items() if items}
    return {
        "policy_id": POLICY_ID,
        "source_function_count": len(sources),
        "required_global_name_count": len(set().union(*map(set, required.values()))),
        "unresolved_function_count": len(unresolved),
        "unresolved_global_name_count": sum(len(items) for items in unresolved.values()),
        "fcntl_resolved": "fcntl" in namespace,
        "socket_resolved": "socket" in namespace,
        "subprocess_resolved": "subprocess" in namespace,
        "thread_pool_executor_resolved": "ThreadPoolExecutor" in namespace,
        "as_completed_resolved": "as_completed" in namespace,
        "lease_helper_resolved": "acquire_deepwide_api_lease" in namespace,
        "contains_prompt_question_query_url_page_prediction_answer_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "file_environment_process_network_model_search_fetch_or_evaluator_accessed": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }


__all__ = [
    "POLICY_ID",
    "build_namespace",
    "clone_group",
    "content_free_receipt",
    "referenced_global_names",
]
