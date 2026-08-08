#!/usr/bin/env python3
"""Run one V2.48.57 task with pacing-aware first-wave admission."""

from __future__ import annotations

import copy
import os
import sys
import types
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24857_pacing_aware_exact220_contract as contract  # noqa: E402
from deepwide_agent.v24796_deadline_tavily_search import empty_receipt  # noqa: E402
from deepwide_agent.v24852_rate_aware_tavily_search import (  # noqa: E402
    RateAwareDeadlineTavilyThinCompatibilityClient,
    empty_rate_aware_receipt,
    validate_search_class,
)
from deepwide_agent.v24856_pacing_aware_admission import (  # noqa: E402
    run_pacing_aware_two_wave_retrieval,
    validate_receipt as validate_pacing_receipt,
)
from deepwide_agent import v24273_two_wave_task_runtime as retrieval_runtime  # noqa: E402
from deepwide_agent import v24318_deadline_conservation_runtime as conservation_runtime  # noqa: E402
from deepwide_agent import v24319_runner_integration as runner_integration  # noqa: E402
from deepwide_agent import v24630_exact220_task_integration as task_integration  # noqa: E402
from scripts import run_v24635_exact220_task as algorithm  # noqa: E402


_CREDENTIAL_ENVIRONMENT = "TAVILY_API_KEYS"


def _isolated_function(original: Any, **bindings: Any) -> Any:
    if original.__closure__:
        raise RuntimeError("V2.48.57 frozen parent unexpectedly has closure state")
    namespace = dict(original.__globals__)
    namespace.update(bindings)
    value = types.FunctionType(
        original.__code__,
        namespace,
        name=f"v24857_isolated_{original.__name__}",
        argdefs=original.__defaults__,
        closure=None,
    )
    value.__kwdefaults__ = copy.deepcopy(original.__kwdefaults__)
    return value


def _pacing_retrieval(*args: Any, **kwargs: Any) -> dict[str, Any]:
    search = kwargs.get("search")
    if search is None and len(args) >= 2:
        search = args[1]
    if search is None:
        raise TypeError("V2.48.57 pacing search binding is absent")
    value = run_pacing_aware_two_wave_retrieval(*args, **kwargs)
    receipt = validate_pacing_receipt(value["pacing_admission_receipt"])
    setattr(search, "_v24857_pacing_admission_receipt", receipt)
    output = copy.deepcopy(value)
    output.pop("pacing_admission_receipt", None)
    return output


_ISOLATED_SEARCH_MANY = _isolated_function(
    retrieval_runtime.TwoWaveCachingSearchClient.search_many,
    run_two_wave_retrieval=_pacing_retrieval,
)


class PacingAwareTwoWaveCachingSearchClient(
    retrieval_runtime.TwoWaveCachingSearchClient
):
    search_many = _ISOLATED_SEARCH_MANY


_ISOLATED_RUN_PARENT = _isolated_function(
    conservation_runtime._run_parent,
    TwoWaveCachingSearchClient=PacingAwareTwoWaveCachingSearchClient,
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
        retrieval_runtime.TwoWaveCachingSearchClient.search_many
        is _ISOLATED_SEARCH_MANY
        or conservation_runtime._run_parent is _ISOLATED_RUN_PARENT
        or runner_integration.run_v24319_task is _ISOLATED_RUN_V24319_TASK
        or task_integration.run_v24630_task is _PARENT_RUN_TASK
        or _ISOLATED_SEARCH_MANY.__globals__["run_two_wave_retrieval"]
        is not _pacing_retrieval
        or retrieval_runtime.TwoWaveCachingSearchClient.search_many.__globals__[
            "run_two_wave_retrieval"
        ]
        is _pacing_retrieval
    ):
        raise RuntimeError("V2.48.57 isolated integration binding drifted")


def run_pacing_aware_task(*args: Any, **kwargs: Any) -> Any:
    """Exercise the isolated production chain without mutating frozen modules."""

    validate_isolation()
    return _PARENT_RUN_TASK(*args, **kwargs)


def _credentials_from_environment() -> tuple[str, ...]:
    serialized = os.environ.pop(_CREDENTIAL_ENVIRONMENT, "")
    try:
        values = tuple(
            line.strip() for line in serialized.splitlines() if line.strip()
        )
    finally:
        serialized = ""
    if (
        len(values) != contract.TAVILY_KEY_SLOT_CAP
        or len(set(values)) != len(values)
    ):
        raise RuntimeError("V2.48.57 child credential pool shape drifted")
    return values


def _result_directory(argv: list[str]) -> Path:
    try:
        value = Path(argv[argv.index("--result") + 1]).resolve(strict=False)
    except (IndexError, ValueError):
        raise RuntimeError("V2.48.57 child result argument is absent") from None
    root = (ROOT / contract.TASK_ROOT).resolve()
    if value.name != "result.json" or not value.parent.is_relative_to(root):
        raise RuntimeError("V2.48.57 child result path escaped task root")
    return value.parent


def configure(argv: list[str] | None = None) -> Path:
    credentials = _credentials_from_environment()
    directory = _result_directory(list(sys.argv if argv is None else argv))

    class ConfiguredTavilySearch(
        RateAwareDeadlineTavilyThinCompatibilityClient
    ):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(
                *args,
                credentials=credentials,
                key_slot_directory=ROOT / contract.KEY_SLOT_DIRECTORY,
                output_root=ROOT / contract.OUTPUT_ROOT,
                direct_timeout_seconds=contract.SEARCH[
                    "direct_timeout_seconds"
                ],
                direct_workers=contract.SEARCH["direct_workers"],
                **kwargs,
            )

    bindings = {
        "OUTPUT_ROOT": contract.OUTPUT_ROOT,
        "TASK_ROOT": contract.TASK_ROOT,
        "MODEL_SLOT_DIRECTORY": contract.MODEL_SLOT_DIRECTORY,
        "LIMITS": contract.LIMITS,
        "MODEL": contract.MODEL,
        "SEARCH": contract.SEARCH,
        "TWO_WAVE_POLICY": contract.TWO_WAVE_POLICY,
        "ThinSameResponseCitationTitleBackfillSearchClient": (
            ConfiguredTavilySearch
        ),
        "validate_thin_search_class": validate_search_class,
    }
    for name, value in bindings.items():
        setattr(algorithm, name, value)

    direct_path = directory / contract.DIRECT_RECEIPT_NAME
    rate_path = directory / contract.RATE_RECEIPT_NAME
    pacing_path = directory / contract.PACING_RECEIPT_NAME
    client: ConfiguredTavilySearch | None = None
    pacing_receipt: dict[str, Any] | None = None

    def write_receipts(search: ConfiguredTavilySearch | None) -> None:
        nonlocal pacing_receipt
        if search is not None:
            observed = getattr(
                search, "_v24857_pacing_admission_receipt", None
            )
            if observed is not None:
                pacing_receipt = validate_pacing_receipt(observed)
        if not direct_path.exists() and not direct_path.is_symlink():
            direct = (
                search.direct_search_receipt()
                if search is not None
                else empty_receipt(contract.TAVILY_KEY_SLOT_CAP)
            )
            algorithm._atomic_new(direct_path, direct)
        if not rate_path.exists() and not rate_path.is_symlink():
            algorithm._atomic_new(
                rate_path,
                search.rate_aware_search_receipt()
                if search is not None
                else empty_rate_aware_receipt(),
            )
        if (
            pacing_receipt is not None
            and not pacing_path.exists()
            and not pacing_path.is_symlink()
        ):
            algorithm._atomic_new(pacing_path, pacing_receipt)

    def run_task(*args: Any, **kwargs: Any) -> Any:
        nonlocal client
        search = kwargs.get("search")
        if not isinstance(search, ConfiguredTavilySearch):
            raise TypeError("V2.48.57 expected configured rate-aware Tavily")
        client = search
        try:
            return run_pacing_aware_task(*args, **kwargs)
        finally:
            write_receipts(search)

    algorithm.run_v24630_task = run_task
    parent_main = algorithm.main

    def main_with_receipts() -> None:
        try:
            parent_main()
        finally:
            write_receipts(client)

    algorithm.main = main_with_receipts
    return directory


def main() -> None:
    validate_isolation()
    configure()
    algorithm.main()


if __name__ == "__main__":
    main()
