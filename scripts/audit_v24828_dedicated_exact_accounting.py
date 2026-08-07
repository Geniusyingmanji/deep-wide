#!/usr/bin/env python3
"""Build-only audit for V2.48.28 cross-transport accounting."""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24804_shared_prefix_budget_ladder import payload_sha256  # noqa: E402


DATE = "20260807"
OUTPUT = Path(f"results/v24828_dedicated_exact_accounting_build_audit_v1_{DATE}.json")
PARENT = Path(f"results/v24827_worldbank_exact_transport_probe_postresult_audit_v1_{DATE}.json")
RUNTIME = Path("src/deepwide_agent/v24828_dedicated_exact_accounting.py")
TEST = Path("tests/test_v24828_dedicated_exact_accounting.py")
AUDIT = Path("scripts/audit_v24828_dedicated_exact_accounting.py")
DEPENDENCIES = (
    Path("src/deepwide_agent/v24823_quality_first_accounting.py"),
    Path("src/deepwide_agent/v24826_worldbank_exact_api_transport.py"),
)
SOURCES = (PARENT, RUNTIME, TEST, AUDIT, *DEPENDENCIES)
EXPECTED_TESTS = 7
PROTECTED_WATCHERS = (
    (795336, 713986317, "scripts/watch_v2415_r1_checkpoint_liveness.py"),
    (3061652, 747569004, "scripts/watch_v24218_exact220_executor.py"),
    (2808901, 746680268, "scripts/watch_v24215_joint_package_recovery.py"),
    (2889939, 746969965, "scripts/watch_v24216_package_gate.py"),
)
PRIVILEGED = frozenset({
    "answer_key", "benchmark_question_type", "category", "evaluator", "gold",
    "ground_truth", "mapping", "question_type", "reward", "score", "split",
    "task_category",
})
EVALUATOR_MARKERS = ("official_eval", "official_evaluator", "external_evaluator", "evaluator_mapping", "finalize_v24")
SECRET_PREFIXES = ("gh" + "p_", "github_" + "pat_", "tvly-" + "dev-", "s" + "k-")
SECRET = re.compile(r"(?<![A-Za-z0-9])(?:" + "|".join(re.escape(v) for v in SECRET_PREFIXES) + r")[A-Za-z0-9_-]{16,}")


def ordinary(relative: Path) -> Path:
    path = ROOT / relative
    if (
        relative.is_absolute() or ".." in relative.parts or path.is_symlink()
        or not path.is_file() or not path.resolve().is_relative_to(ROOT.resolve())
    ):
        raise RuntimeError(f"V2.48.28 expected repository file: {relative}")
    return path


def sha256(relative: Path) -> str:
    digest = hashlib.sha256()
    with ordinary(relative).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read(relative: Path) -> dict[str, Any]:
    value = json.loads(ordinary(relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.48.28 expected JSON object")
    return value


def sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
        timeout=20, check=True,
    ).stdout.strip()


def tracked(relative: Path) -> bool:
    return subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(relative)], cwd=ROOT,
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, timeout=20, check=False,
    ).returncode == 0


def watchers() -> list[dict[str, Any]]:
    output = []
    for pid, ticks, marker in PROTECTED_WATCHERS:
        stat = Path("/proc") / str(pid) / "stat"
        cmdline = Path("/proc") / str(pid) / "cmdline"
        if not stat.is_file() or not cmdline.is_file():
            raise RuntimeError("V2.48.28 protected watcher absent")
        raw = stat.read_text(encoding="utf-8")
        suffix = raw[raw.rfind(")") + 2:].split()
        command = cmdline.read_bytes().replace(b"\0", b" ").decode(errors="replace")
        if len(suffix) <= 19 or int(suffix[19]) != ticks or marker not in command:
            raise RuntimeError("V2.48.28 protected watcher drifted")
        output.append({"pid": pid, "start_ticks": ticks, "marker": marker})
    return output


def ast_findings(relative: Path) -> tuple[list[str], list[str]]:
    tree = ast.parse(ordinary(relative).read_text(encoding="utf-8"))
    fields: list[str] = []
    imports: list[str] = []
    for node in ast.walk(tree):
        key = None
        if (
            isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and node.func.attr in {"get", "pop", "setdefault"} and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            key = node.args[0].value.casefold()
        elif isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str):
            key = node.slice.value.casefold()
        if key in PRIVILEGED:
            fields.append(f"{relative}:{node.lineno}:{key}")
        names = (
            [alias.name for alias in node.names] if isinstance(node, ast.Import)
            else [node.module or "", *(alias.name for alias in node.names)] if isinstance(node, ast.ImportFrom)
            else []
        )
        for name in names:
            if any(marker in name.casefold() for marker in EVALUATOR_MARKERS):
                imports.append(f"{relative}:{node.lineno}:{name}")
    return sorted(fields), sorted(imports)


def parent_valid() -> bool:
    value = read(PARENT)
    return bool(
        value.get("role") == "v24827_worldbank_exact_transport_probe_postresult_audit"
        and value.get("audit_valid") is True and value.get("findings") == []
        and value.get("result_status") == "transport_probe_go"
        and value.get("authorization", {}).get("accounting_successor_design") is True
        and value.get("authorization", {}).get("external_population_or_public_exact220") is False
        and sealed(value, "audit_payload_sha256")
    )


def run_tests() -> tuple[int, bool, str]:
    environment = {
        "HOME": os.environ.get("HOME", str(Path.home())), "USER": os.environ.get("USER", "azureuser"),
        "LOGNAME": os.environ.get("LOGNAME", "azureuser"),
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1", "PYTHONSAFEPATH": "1",
    }
    completed = subprocess.run(
        [str(ROOT / ".venv-eval/bin/python"), "-I", "-B", "-m", "unittest", "discover", "-s", "tests", "-p", TEST.name, "-v"],
        cwd=ROOT, env=environment, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        timeout=180, check=False,
    )
    match = re.search(r"Ran (\d+) tests?", completed.stdout)
    observed = int(match.group(1)) if match else 0
    return observed, completed.returncode == 0 and observed == EXPECTED_TESTS, completed.stdout


def validate(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    unsigned = dict(copied)
    seal = unsigned.pop("audit_payload_sha256", None)
    checks = copied.get("checks")
    if (
        copied.get("role") != "v24828_dedicated_exact_accounting_build_audit"
        or not isinstance(checks, Mapping)
        or copied.get("findings") != sorted(name for name, passed in checks.items() if not passed)
        or copied.get("audit_valid") is not (copied.get("findings") == [])
        or copied.get("authorization") != {
            "fresh_target_cell_disjoint_external_design": bool(copied.get("audit_valid")),
            "external_population_launch": False,
            "same_population_retry_resume_rerun_or_revaluation": False,
            "public_exact220": False,
            "sota_claim": False,
        }
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.48.28 build audit drifted")
    return copied


def build(*, now: int | None = None, require_clean: bool = True, require_tracked: bool = True) -> dict[str, Any]:
    before = watchers()
    fields, imports = ast_findings(RUNTIME)
    observed, passed, output = run_tests()
    after = watchers()
    source_text = "\n".join(ordinary(path).read_text(encoding="utf-8") for path in SOURCES)
    runtime_text = ordinary(RUNTIME).read_text(encoding="utf-8")
    checks = {
        "parent_probe_go_authority_valid": parent_valid(),
        "clean_pushed_head": (not require_clean) or (not git("status", "--porcelain") and git("rev-parse", "HEAD") == git("rev-parse", "target/main")),
        "sources_tracked": (not require_tracked) or all(tracked(path) for path in SOURCES),
        "focused_tests_7_of_7": passed and observed == EXPECTED_TESTS,
        "runtime_privileged_access_absent": fields == [],
        "runtime_evaluator_import_absent": imports == [],
        "credential_literal_absent": SECRET.search(source_text) is None,
        "fixed_two_plus_eight_equals_ten": all(token in runtime_text for token in ("GENERIC_FETCH_TARGETS = 2", "DEDICATED_EXACT_FETCH_TARGETS = EXPECTED_TARGET_COUNT", "TOTAL_FETCH_TARGETS = 10")),
        "exact_receipt_cryptographically_bound": "exact_transport_receipt_sha256" in runtime_text,
        "entropy_remains_shadow_only": "entropy_shadow_only_not_signed_credit" in runtime_text,
        "protected_watchers_unchanged": before == after,
    }
    value = {
        "artifact_version": 1,
        "role": "v24828_dedicated_exact_accounting_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "base_commit": git("rev-parse", "HEAD"),
        "parent_sha256": sha256(PARENT),
        "source_manifest": {str(path): sha256(path) for path in SOURCES},
        "tests": {"expected": EXPECTED_TESTS, "observed": observed, "passed": passed, "output_sha256": payload_sha256(output)},
        "runtime_privileged_accesses": fields,
        "runtime_evaluator_imports": imports,
        "checks": checks,
        "findings": sorted(name for name, passed_check in checks.items() if not passed_check),
        "audit_valid": all(checks.values()),
        "protected_watchers_before": before,
        "protected_watchers_after": after,
        "effect_boundary": {
            "in_memory_fake_transport_only": True,
            "network_model_search_fetch_or_evaluator_called_by_audit": False,
            "benchmark_or_external_population_opened": False,
        },
        "authorization": {
            "fresh_target_cell_disjoint_external_design": all(checks.values()),
            "external_population_launch": False,
            "same_population_retry_resume_rerun_or_revaluation": False,
            "public_exact220": False,
            "sota_claim": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return validate(value)


def publish(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    artifact = build()
    if artifact["findings"]:
        raise RuntimeError(f"V2.48.28 audit rejected: {artifact['findings']}")
    publish(ROOT / OUTPUT, artifact)
    print(json.dumps({"path": str(OUTPUT), "tests": artifact["tests"], "findings": artifact["findings"], "authorization": artifact["authorization"]}, sort_keys=True))
