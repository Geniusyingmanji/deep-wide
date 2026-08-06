#!/usr/bin/env python3
"""Exact-allowlist helper for the fresh V2.47.50 visible population."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24745_cross_domain_adapters as runtime  # noqa: E402
from deepwide_agent import v24744_cross_domain_contract as prior_contract  # noqa: E402
from deepwide_agent import v24750_host_local_contract as contract  # noqa: E402
from scripts import v24746_public_get_helper as base  # noqa: E402


ALLOWED_URLS = frozenset(
    url for task in contract.task_vector() for url in runtime.request_urls(task)
)
PRIOR_ALLOWED_URLS = frozenset(
    url
    for task in prior_contract.task_vector()
    for url in runtime.request_urls(task)
)
ALLOWED_HOSTS = base.ALLOWED_HOSTS
MAX_STDIN_BYTES = base.MAX_STDIN_BYTES
INPUT_KEYS = base.INPUT_KEYS
OUTPUT_KEYS = base.OUTPUT_KEYS

base.contract = contract
base.runtime = runtime
base.ALLOWED_URLS = ALLOWED_URLS

_validate_url = base._validate_url
_output = base._output


if __name__ == "__main__":
    base.main()
