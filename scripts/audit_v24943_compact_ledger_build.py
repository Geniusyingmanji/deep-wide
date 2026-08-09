#!/usr/bin/env python3
"""Build audit for the V2.49.42 compact ledger."""

from __future__ import annotations

import ast
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24942_compact_schema_bound_record_ledger as candidate  # noqa: E402
from deepwide_agent import v24943_compact_ledger_external_contract as contract  # noqa: E402


def main() -> None:
    output = ROOT / contract.CANDIDATE_AUDIT
    if output.exists() or subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, stdout=subprocess.PIPE, text=True, check=True).stdout.strip():
        raise RuntimeError("V2.49.43 compact audit requires pristine clean surface")
    completed = subprocess.run(
        [str(ROOT / ".venv-eval/bin/python"), "-I", "-B", "-m", "unittest", "discover", "-s", "tests", "-p", "test_v24942_compact_schema_bound_record_ledger.py", "-v"],
        cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=180,
        env={"HOME": os.environ.get("HOME", str(Path.home())), "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin", "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1", "PYTHONSAFEPATH": "1"},
    )
    source_path = ROOT / "src/deepwide_agent/v24942_compact_schema_bound_record_ledger.py"
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {alias.name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
    imports.update((node.module or "").split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.ImportFrom))
    forbidden_imports = sorted(imports & {"os", "pathlib", "socket", "subprocess", "requests", "httpx", "openai", "runpy", "importlib"})
    checks = {
        "focused_tests_exact8": completed.returncode == 0 and "Ran 8 tests" in completed.stdout,
        "runtime_forbidden_import_zero": not forbidden_imports,
        "runtime_privileged_literal_zero": not any(value in source for value in ("ground_truth", "question_type", "answer_key", "results.csv")),
        "policy_id_exact": candidate.POLICY_ID == "v24942_compact_schema_bound_open_world_record_ledger_v1",
        "entropy_information_gain_shadow_only": True,
        "external_or_public_launch_not_authorized": True,
    }
    manifest = {str(source_path.relative_to(ROOT)): hashlib.sha256(source_path.read_bytes()).hexdigest(), "tests/test_v24942_compact_schema_bound_record_ledger.py": hashlib.sha256((ROOT / "tests/test_v24942_compact_schema_bound_record_ledger.py").read_bytes()).hexdigest()}
    value = {
        "artifact_version": 1,
        "role": "v24943_compact_schema_bound_ledger_build_audit",
        "created_at_unix": int(time.time()),
        "candidate_policy_id": candidate.POLICY_ID,
        "source_manifest": manifest,
        "tests": {"expected": 8, "passed": checks["focused_tests_exact8"], "output_sha256": contract.payload_sha256(completed.stdout)},
        "runtime_semantic_audit": {"forbidden_imports": forbidden_imports},
        "checks": checks,
        "findings": sorted(name for name, passed in checks.items() if not passed),
        "authorization": {"fresh_external_protocol_design": all(checks.values()), "external_launch": False, "public_exact220": False},
    }
    value["audit_valid"] = not value["findings"]
    value["audit_payload_sha256"] = contract.payload_sha256(value)
    if not value["audit_valid"]:
        raise RuntimeError(value["findings"])
    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True); handle.write("\n"); handle.flush(); os.fsync(handle.fileno())
    print(json.dumps({"path": str(contract.CANDIDATE_AUDIT), "audit_valid": True}, sort_keys=True))


if __name__ == "__main__":
    main()
