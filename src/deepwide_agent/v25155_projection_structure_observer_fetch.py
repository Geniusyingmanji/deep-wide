"""Observed fetch seam for the V2.51.55 three-layer structure receipt.

This append-only client preserves the frozen V2.49.85 fetch, byte, deadline,
page, redirect, and projection boundaries.  Its isolated helper additionally
returns a sealed content-free raw-markup -> extracted-text -> projected-text
structure observation.  The client exposes only an aggregate count receipt;
page identity, URL, question, labels, values, text, and predictions are not
part of that receipt.
"""

from __future__ import annotations

import copy
import json
import os
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .clients import canonicalize_url
from .v24981_late_page_bound_fetch import LatePageBoundFetchMixin
from .v24985_robust_late_page_fetch import RobustLatePageBoundSearchClient
from .v25155_projection_structure_observer import (
    aggregate_observations,
    validate_observation,
)


POLICY_ID = "v25155_projection_structure_observer_fetch_v1"
ROOT = Path(__file__).resolve().parents[2]
HELPER = ROOT / "scripts/run_v25155_projection_structure_observer_fetch_helper.py"
HELPER_RESULT_KEYS = frozenset(
    {
        "status",
        "url",
        "title",
        "text",
        "links",
        "projection_receipt",
        "parent_prefix",
        "structure_observation",
    }
)


def _ordinary_helper(path: Path = HELPER) -> Path:
    expected = HELPER.resolve()
    resolved = path.resolve()
    if (
        path.is_symlink()
        or not path.is_file()
        or resolved != expected
        or not resolved.is_relative_to(ROOT)
    ):
        raise ValueError("V2.51.55 helper identity drifted")
    return resolved


def _failure(status: str) -> dict[str, Any]:
    return {"status": status, "url": "", "title": "", "text": "", "links": []}


def validate_helper_result(value: object) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != HELPER_RESULT_KEYS:
        raise ValueError("V2.51.55 helper result schema drifted")
    copied = copy.deepcopy(dict(value))
    from .v24981_late_page_bound_fetch import (
        validate_helper_result as validate_parent_helper_result,
    )

    parent = validate_parent_helper_result(
        {name: copied[name] for name in copied if name != "structure_observation"}
    )
    structure = copied.get("structure_observation")
    if parent["status"] == "ok":
        if not isinstance(structure, Mapping):
            raise ValueError("V2.51.55 successful helper omitted structure receipt")
        copied["structure_observation"] = validate_observation(structure)
    elif structure is not None:
        raise ValueError("V2.51.55 failed helper retained structure receipt")
    return copied


class ProjectionStructureObservedSearchClient(RobustLatePageBoundSearchClient):
    """V2.49.85-compatible client with content-free layer observations."""

    def __init__(
        self,
        *args: Any,
        projection_structure_helper: Path = HELPER,
        late_page_fetch_popen: Any = subprocess.Popen,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            *args,
            late_page_fetch_popen=late_page_fetch_popen,
            **kwargs,
        )
        self._v24981_fetch_helper = _ordinary_helper(projection_structure_helper)
        self._v25155_structure_observations: list[dict[str, Any]] = []

    def _fetch_url_late_page_bound(self, url: str) -> dict[str, Any]:
        """Run the observed helper under the unchanged inherited deadline."""

        self._increment("fetch_calls")
        remaining = self.remaining_effect_seconds()
        if remaining < self.minimum_attempt_seconds:
            self._increment("fetch_failures")
            self._increment("fetch_deadline_rejections")
            return _failure("task_deadline_exhausted")
        self._increment("hard_fetch_helper_calls")
        process = self._v24981_fetch_popen(
            [
                self.fetch_python_executable,
                "-I",
                "-B",
                str(self._v24981_fetch_helper),
            ],
            cwd=self._v24981_fetch_helper.parents[1],
            env={
                "HOME": os.environ.get("HOME", str(Path.home())),
                "USER": os.environ.get("USER", "azureuser"),
                "LOGNAME": os.environ.get("LOGNAME", "azureuser"),
                "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONNOUSERSITE": "1",
                "PYTHONSAFEPATH": "1",
            },
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            text=True,
        )
        remaining_after_launch = self.remaining_effect_seconds()
        if remaining_after_launch < self.minimum_attempt_seconds:
            self._terminate_group(process)
            self._increment("fetch_failures")
            self._increment("hard_fetch_deadline_failures")
            return _failure("task_deadline_exhausted_after_helper_launch")
        try:
            stdout, _ = process.communicate(
                json.dumps(
                    {
                        "url": str(url),
                        "question": self._v24981_visible_question,
                    },
                    ensure_ascii=False,
                ),
                timeout=min(
                    float(self.hard_fetch_deadline_seconds),
                    remaining_after_launch,
                ),
            )
        except subprocess.TimeoutExpired:
            self._terminate_group(process)
            self._increment("fetch_failures")
            self._increment("hard_fetch_deadline_failures")
            return _failure("hard_deadline_exceeded")
        if process.returncode != 0:
            self._increment("fetch_failures")
            self._increment("fetch_helper_failures")
            return _failure("helper_nonzero_exit")
        try:
            result = validate_helper_result(json.loads(stdout))
        except (json.JSONDecodeError, TypeError, ValueError):
            self._increment("fetch_failures")
            self._increment("fetch_helper_failures")
            return _failure("helper_invalid_result")
        with self._v24981_receipt_lock:
            self._v24981_helper_result_count += 1
            receipt = result.get("projection_receipt")
            structure = result.get("structure_observation")
            if isinstance(receipt, Mapping) and isinstance(structure, Mapping):
                self._v24981_projection_receipts.append(copy.deepcopy(dict(receipt)))
                self._v25155_structure_observations.append(
                    validate_observation(structure)
                )
                prefix = str(result.get("parent_prefix") or "")
                aliases = {
                    canonicalize_url(str(url)),
                    canonicalize_url(str(result.get("url") or "")),
                } - {""}
                for alias in aliases:
                    previous = self._v24981_parent_prefixes.get(alias)
                    if previous is not None and previous != prefix:
                        self._increment("fetch_failures")
                        self._increment("fetch_helper_failures")
                        return _failure("shadow_prefix_identity_conflict")
                    self._v24981_parent_prefixes[alias] = prefix
        if result["status"] != "ok":
            self._increment("fetch_failures")
        return {
            name: copy.deepcopy(result[name])
            for name in ("status", "url", "title", "text", "links")
        }

    def projection_structure_observation_receipt(self) -> dict[str, Any]:
        with self._v24981_receipt_lock:
            values = copy.deepcopy(self._v25155_structure_observations)
        return aggregate_observations(values)


def validate_search_class() -> None:
    from .v24985_robust_late_page_fetch import (
        validate_search_class as validate_parent_search_class,
    )

    validate_parent_search_class()
    owner = next(
        base
        for base in ProjectionStructureObservedSearchClient.__mro__
        if "_fetch_url" in base.__dict__
    )
    if (
        owner is not LatePageBoundFetchMixin
        or not issubclass(
            ProjectionStructureObservedSearchClient,
            RobustLatePageBoundSearchClient,
        )
        or _ordinary_helper() != HELPER.resolve()
    ):
        raise RuntimeError("V2.51.55 observed search MRO or helper drifted")


__all__ = [
    "HELPER",
    "HELPER_RESULT_KEYS",
    "POLICY_ID",
    "ProjectionStructureObservedSearchClient",
    "validate_helper_result",
    "validate_search_class",
]
