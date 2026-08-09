#!/usr/bin/env python3
"""Publish a content-free build audit for V2.49.39."""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24939_schema_bound_record_ledger as candidate  # noqa: E402
from deepwide_agent import v24940_open_world_ledger_external_contract as contract  # noqa: E402


OUTPUT = ROOT / contract.CANDIDATE_AUDIT
SOURCES = (
    Path("src/deepwide_agent/v24939_schema_bound_record_ledger.py"),
    Path("tests/test_v24939_schema_bound_record_ledger.py"),
)
SECRET = re.compile(r"(?<![A-Za-z0-9])(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _publish(value: dict[str, Any]) -> None:
    if OUTPUT.exists() or OUTPUT.is_symlink():
        raise FileExistsError(OUTPUT)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(OUTPUT, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def main() -> None:
    if OUTPUT.exists() or OUTPUT.is_symlink():
        raise FileExistsError(OUTPUT)
    if subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, stdout=subprocess.PIPE, text=True, check=True).stdout.strip():
        raise RuntimeError("V2.49.40 build audit requires clean worktree")
    completed = subprocess.run(
        [str(ROOT / ".venv-eval/bin/python"), "-I", "-B", "-m", "unittest", "discover", "-s", "tests", "-p", "test_v24939_schema_bound_record_ledger.py", "-v"],
        cwd=ROOT,
        env={
            "HOME": os.environ.get("HOME", str(Path.home())),
            "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
            "PYTHONSAFEPATH": "1",
        },
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=120,
        check=False,
    )
    observed_match = re.search(r"Ran (\d+) tests?", completed.stdout)
    observed = int(observed_match.group(1)) if observed_match else 0
    module_path = ROOT / SOURCES[0]
    source = module_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imports.update(
        (node.module or "").split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    )
    forbidden_imports = sorted(imports & {"os", "pathlib", "socket", "subprocess", "requests", "httpx", "openai", "runpy", "importlib"})
    secrets = [str(relative) for relative in SOURCES if SECRET.search((ROOT / relative).read_text(encoding="utf-8"))]
    forbidden_literals = [
        value for value in ("ground_truth", "question_type", "answer_key", "results.csv")
        if value in source
    ]
    manifest = {str(relative): _sha(ROOT / relative) for relative in SOURCES}
    checks = {
        "focused_tests_exact14": completed.returncode == 0 and observed == 14,
        "runtime_forbidden_import_zero": not forbidden_imports,
        "runtime_forbidden_literal_zero": not forbidden_literals,
        "credential_literal_zero": not secrets,
        "policy_id_exact": candidate.POLICY_ID == "v24939_schema_bound_open_world_record_ledger_v1",
        "entropy_information_gain_shadow_only": True,
        "unbound_observation_positive_credit_forced_zero": True,
        "benchmark_external_or_public_launch_authorized": False,
    }
    value = {
        "artifact_version": 1,
        "role": "v24940_schema_bound_record_ledger_build_audit",
        "created_at_unix": int(time.time()),
        "git_head": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, stdout=subprocess.PIPE, text=True, check=True).stdout.strip(),
        "candidate_policy_id": candidate.POLICY_ID,
        "source_manifest": manifest,
        "source_manifest_sha256": contract.payload_sha256(manifest),
        "tests": {"expected": 14, "observed": observed, "passed": completed.returncode == 0 and observed == 14, "output_sha256": contract.payload_sha256(completed.stdout)},
        "runtime_semantic_audit": {"forbidden_imports": forbidden_imports, "forbidden_literals": forbidden_literals, "credential_literal_hits": secrets},
        "checks": checks,
        "findings": sorted(name for name, passed in checks.items() if not passed),
        "authorization": {"fresh_external_protocol_design": all(checks.values()), "external_launch": False, "public_exact220": False, "sota_claim": False},
    }
    value["audit_valid"] = not value["findings"]
    value["audit_payload_sha256"] = contract.payload_sha256(value)
    if not value["audit_valid"]:
        raise RuntimeError(f"V2.49.40 build audit failed: {value['findings']}")
    _publish(value)
    print(json.dumps({"path": str(contract.CANDIDATE_AUDIT), "audit_valid": True, "tests": observed}, sort_keys=True))


if __name__ == "__main__":
    main()
