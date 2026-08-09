#!/usr/bin/env python3
"""Run one V2.50.23 label-blind task and publish content-free sidecars."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25023_distinct_coverage_exact220_contract as contract  # noqa: E402
from deepwide_agent.v24257_score_first_runtime import validate_visible_task  # noqa: E402
from deepwide_agent.v24796_deadline_tavily_search import empty_receipt  # noqa: E402
from deepwide_agent.v24852_rate_aware_tavily_search import empty_rate_aware_receipt  # noqa: E402
from deepwide_agent.v24856_pacing_aware_admission import validate_receipt as validate_pacing_receipt  # noqa: E402
from deepwide_agent.v24981_late_page_bound_fetch import validate_receipt as validate_projection_receipt  # noqa: E402
from deepwide_agent.v25019_production_distinct_coverage_selection import validate_receipt as validate_distinct_receipt  # noqa: E402
from deepwide_agent.v25021_rate_aware_multi_identity_search import (  # noqa: E402
    RateAwareMultiIdentityDetailSearchClient,
    validate_search_class,
)
from deepwide_agent.v25022_production_distinct_coverage_task import (  # noqa: E402
    run_production_distinct_coverage_task,
    validate_isolation,
)
from scripts import run_v24635_exact220_task as algorithm  # noqa: E402


_CREDENTIAL_ENVIRONMENT = "TAVILY_API_KEYS"


def _credentials_from_environment() -> tuple[str, ...]:
    serialized = os.environ.pop(_CREDENTIAL_ENVIRONMENT, "")
    try:
        values = tuple(line.strip() for line in serialized.splitlines() if line.strip())
    finally:
        serialized = ""
    if len(values) != contract.TAVILY_KEY_SLOT_CAP or len(set(values)) != len(values):
        raise RuntimeError("V2.50.23 child credential pool shape drifted")
    return values


def _result_directory(argv: list[str]) -> Path:
    try:
        value = Path(argv[argv.index("--result") + 1]).resolve(strict=False)
    except (IndexError, ValueError):
        raise RuntimeError("V2.50.23 child result argument is absent") from None
    root = (ROOT / contract.TASK_ROOT).resolve()
    if value.name != "result.json" or not value.parent.is_relative_to(root):
        raise RuntimeError("V2.50.23 child result path escaped task root")
    return value.parent


def _visible_question(directory: Path) -> str:
    path = directory / "visible_task.json"
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("V2.50.23 visible task is absent")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.50.23 visible task is not an object")
    return validate_visible_task(value)["question"]


def configure(argv: list[str] | None = None) -> Path:
    credentials = _credentials_from_environment()
    directory = _result_directory(list(sys.argv if argv is None else argv))
    question = _visible_question(directory)

    class ConfiguredSearch(RateAwareMultiIdentityDetailSearchClient):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(
                *args,
                visible_question=question,
                credentials=credentials,
                key_slot_directory=ROOT / contract.KEY_SLOT_DIRECTORY,
                output_root=ROOT / contract.OUTPUT_ROOT,
                direct_timeout_seconds=contract.SEARCH["direct_timeout_seconds"],
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
        "ThinSameResponseCitationTitleBackfillSearchClient": ConfiguredSearch,
        "validate_thin_search_class": validate_search_class,
    }
    for name, value in bindings.items():
        setattr(algorithm, name, value)

    paths = {
        "direct": directory / contract.DIRECT_RECEIPT_NAME,
        "rate": directory / contract.RATE_RECEIPT_NAME,
        "pacing": directory / contract.PACING_RECEIPT_NAME,
        "distinct": directory / contract.DISTINCT_RECEIPT_NAME,
        "projection": directory / contract.PROJECTION_RECEIPT_NAME,
    }
    client: ConfiguredSearch | None = None
    observed: dict[str, dict[str, Any] | None] = {
        "pacing": None,
        "distinct": None,
        "projection": None,
    }

    def write_receipts(search: ConfiguredSearch | None) -> None:
        if search is not None:
            pacing = getattr(search, "_v25022_pacing_admission_receipt", None)
            distinct = getattr(search, "_v25022_distinct_coverage_receipt", None)
            if pacing is not None:
                observed["pacing"] = validate_pacing_receipt(pacing)
            if distinct is not None:
                observed["distinct"] = validate_distinct_receipt(distinct)
            observed["projection"] = validate_projection_receipt(
                search.late_page_projection_receipt()
            )
        if not paths["direct"].exists() and not paths["direct"].is_symlink():
            algorithm._atomic_new(
                paths["direct"],
                search.direct_search_receipt()
                if search is not None
                else empty_receipt(contract.TAVILY_KEY_SLOT_CAP),
            )
        if not paths["rate"].exists() and not paths["rate"].is_symlink():
            algorithm._atomic_new(
                paths["rate"],
                search.rate_aware_search_receipt()
                if search is not None
                else empty_rate_aware_receipt(),
            )
        validators = {
            "pacing": validate_pacing_receipt,
            "distinct": validate_distinct_receipt,
            "projection": validate_projection_receipt,
        }
        for name, validator in validators.items():
            value = observed[name]
            path = paths[name]
            if value is not None and not path.exists() and not path.is_symlink():
                algorithm._atomic_new(path, validator(value))

    def run_task(*args: Any, **kwargs: Any) -> Any:
        nonlocal client
        search = kwargs.get("search")
        if not isinstance(search, ConfiguredSearch):
            raise TypeError("V2.50.23 expected configured composed search")
        client = search
        try:
            return run_production_distinct_coverage_task(*args, **kwargs)
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
    validate_search_class()
    configure()
    algorithm.main()


if __name__ == "__main__":
    main()
