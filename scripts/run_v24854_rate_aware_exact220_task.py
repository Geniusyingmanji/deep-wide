#!/usr/bin/env python3
"""Run one V2.48.54 task with the provider-wide rate-aware Tavily client."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24854_rate_aware_exact220_contract as contract  # noqa: E402
from deepwide_agent.v24796_deadline_tavily_search import (  # noqa: E402
    empty_receipt,
)
from deepwide_agent.v24852_rate_aware_tavily_search import (  # noqa: E402
    RateAwareDeadlineTavilyThinCompatibilityClient,
    empty_rate_aware_receipt,
    validate_search_class,
)
from scripts import run_v24635_exact220_task as algorithm  # noqa: E402


_PARENT_RUN_TASK = algorithm.run_v24630_task
_CREDENTIAL_ENVIRONMENT = "TAVILY_API_KEYS"


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
        raise RuntimeError("V2.48.54 child credential pool shape drifted")
    return values


def _result_directory(argv: list[str]) -> Path:
    try:
        value = Path(argv[argv.index("--result") + 1]).resolve(strict=False)
    except (IndexError, ValueError):
        raise RuntimeError("V2.48.54 child result argument is absent") from None
    root = (ROOT / contract.TASK_ROOT).resolve()
    if value.name != "result.json" or not value.parent.is_relative_to(root):
        raise RuntimeError("V2.48.54 child result path escaped task root")
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
    client: ConfiguredTavilySearch | None = None

    def write_receipts(search: ConfiguredTavilySearch | None) -> None:
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

    def run_task(*args: Any, **kwargs: Any) -> Any:
        nonlocal client
        search = kwargs.get("search")
        if not isinstance(search, ConfiguredTavilySearch):
            raise TypeError("V2.48.54 expected configured rate-aware Tavily")
        client = search
        try:
            return _PARENT_RUN_TASK(*args, **kwargs)
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
    configure()
    algorithm.main()


if __name__ == "__main__":
    main()
