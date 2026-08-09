"""Fresh benchmark-external production-isomorphic Unicode-total gate."""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from . import v24909_keyless_fixed_budget_exact220_contract as parent


DATE = "20260809"
PROTOCOL_ID = "v24929_unicode_total_neutral_reliability_gate_v1"
PROTOCOL = Path(f"results/v24929_unicode_total_neutral_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v24929_unicode_total_neutral_preactivation_audit_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v24929_unicode_total_neutral_execution_start_v1_{DATE}.json")
RESULT = Path(f"results/v24929_unicode_total_neutral_result_v1_{DATE}.json")
POSTAUDIT = Path(f"results/v24929_unicode_total_neutral_postresult_audit_v1_{DATE}.json")
OUTPUT_ROOT = Path(f"outputs/v24929_unicode_total_neutral_v1_{DATE}")
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
TASK_ROOT = OUTPUT_ROOT / "tasks"
SAFE_PROGRESS = OUTPUT_ROOT / "safe_forward_progress.json"
PROJECTION_RECEIPT_NAME = "unicode_total_projection_receipt.json"
LEASE_PATH = parent.LEASE_PATH
LEASE_OWNER = "v24929_unicode_total_neutral_reliability_v1"
LEASE_PURPOSE = "fresh_benchmark_external_unicode_total_production_gate"
RUNNER_MARKER = "scripts/run_v24929_unicode_total_neutral_gate.py"
CHILD_MARKER = "scripts/run_v24929_unicode_total_neutral_task.py"

TASK_COUNT = 20
SELECTED_COUNT = TASK_COUNT
EXECUTOR_CONCURRENCY = 20
MODEL_SLOT_CAP = 8
TASK_WALL_SECONDS = 240
PARENT_DEADLINE_GRACE_SECONDS = 30.0
LIMITS = copy.deepcopy(parent.LIMITS)
MODEL = copy.deepcopy(parent.MODEL)
SEARCH = copy.deepcopy(parent.SEARCH)
TWO_WAVE_POLICY = copy.deepcopy(parent.TWO_WAVE_POLICY)
PROTECTED_WATCHERS = parent.PROTECTED_WATCHERS
PARENT_PROTOCOL = parent.PROTOCOL

MINIMUM_ACCEPTED_PARENT_SUCCESSES = 20
MINIMUM_MODEL_GENERATED_TABLES = 20
MINIMUM_VALID_PROJECTION_RECEIPTS = 20
MINIMUM_VALID_RETRIEVAL_RECEIPTS = 20
MINIMUM_LOGICAL_QUERIES = 72
MINIMUM_USABLE_PAGES = 80
MINIMUM_REAL_NFKC_EXPANSION_TASKS = 1
MINIMUM_REAL_NFKC_EXPANSION_CHARACTERS = 1
MAXIMUM_HARD_TIMEOUTS = 0
MAXIMUM_HOSTED_SEARCH_DEADLINE_FAILURES = 0
MAXIMUM_MODEL_SLOT_TIMEOUTS = 0
MAXIMUM_FORWARD_WALL_SECONDS = 300.0

TOPICS = (
    ("Unicode Standard Annex #15 normalization forms", "½", "Ⅷ", "℡", "ﬃ"),
    ("Unicode Character Database compatibility decompositions", "㎏", "℃", "™", "㍑"),
    ("Python unicodedata normalize", "½", "Ⅷ", "℡", "ﬃ"),
    ("ICU Normalizer2", "㎏", "℃", "™", "㍑"),
    ("Java java.text.Normalizer", "½", "Ⅷ", "℡", "ﬃ"),
    (".NET Unicode normalization", "㎏", "℃", "™", "㍑"),
    ("ECMAScript String normalize", "½", "Ⅷ", "℡", "ﬃ"),
    ("Go x text unicode norm", "㎏", "℃", "™", "㍑"),
    ("Rust unicode-normalization", "½", "Ⅷ", "℡", "ﬃ"),
    ("Ruby String unicode_normalize", "㎏", "℃", "™", "㍑"),
    ("PHP Intl Normalizer", "½", "Ⅷ", "℡", "ﬃ"),
    ("Qt QString normalized", "㎏", "℃", "™", "㍑"),
    ("PostgreSQL normalize function", "½", "Ⅷ", "℡", "ﬃ"),
    ("W3C Character Model normalization", "㎏", "℃", "™", "㍑"),
    ("MDN String normalize", "½", "Ⅷ", "℡", "ﬃ"),
    ("Perl Unicode Normalize", "㎏", "℃", "™", "㍑"),
    ("Swift Unicode normalization", "½", "Ⅷ", "℡", "ﬃ"),
    ("Apple string normalization APIs", "㎏", "℃", "™", "㍑"),
    ("Unicode normalization test data", "½", "Ⅷ", "℡", "ﬃ"),
    ("Unicode names list compatibility characters", "㎏", "℃", "™", "㍑"),
)

SOURCE = Path("src/deepwide_agent/v24929_unicode_total_neutral_contract.py")
PROJECTOR = Path("src/deepwide_agent/v24928_unicode_total_visible_row_compactor.py")
PROJECTOR_AUDIT = Path("results/v24928_unicode_total_compactor_build_audit_v1_20260809.json")
BINDING = Path("src/deepwide_agent/v24907_keyless_fixed_budget_binding.py")
CONTROL = Path("scripts/control_v24929_unicode_total_neutral_gate.py")
RUNNER = Path(RUNNER_MARKER)
CHILD = Path(CHILD_MARKER)
AUDIT = Path("scripts/audit_v24929_unicode_total_neutral_result.py")
TEST = Path("tests/test_v24929_unicode_total_neutral_gate.py")
LOCAL_SOURCES = (SOURCE, PROJECTOR, PROJECTOR_AUDIT, CONTROL, RUNNER, CHILD, AUDIT, TEST)
RUNTIME_SOURCES = (
    SOURCE,
    PROJECTOR,
    BINDING,
    CHILD,
    RUNNER,
    Path("scripts/run_v24635_exact220.py"),
    Path("scripts/run_v24635_exact220_task.py"),
    Path("src/deepwide_agent/v24921_target_value_coverage_projector.py"),
    Path("src/deepwide_agent/v24924_visible_row_table_compactor.py"),
    Path("src/deepwide_agent/v24839_structure_preserving_projector.py"),
    Path("src/deepwide_agent/v24842_atomic_table_header_closure.py"),
)
TEST_SUITES = (
    (TEST, 10),
    (Path("tests/test_v24928_unicode_total_visible_row_compactor.py"), 12),
    (Path("tests/test_v24924_visible_row_table_compactor.py"), 10),
    (Path("tests/test_v24921_target_value_coverage_projector.py"), 9),
    (Path("tests/test_v24909_keyless_fixed_budget_exact220.py"), 8),
    (Path("tests/test_v24635_exact220.py"), 10),
    (Path("tests/test_v24319_runner_integration.py"), 7),
    (Path("tests/test_v24468_total_wall_transport.py"), 8),
)
EXPECTED_TESTS = sum(expected for _path, expected in TEST_SUITES)


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
        check=True,
    ).stdout.strip()


def ordinary_tracked(root: Path, relative: Path) -> Path:
    path = root / relative
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or relative.parts[:1] in {("outputs",), ("evaluation",)}
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(root.resolve())
        or subprocess.run(
            ["git", "ls-files", "--error-unmatch", str(relative)],
            cwd=root,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=20,
            check=False,
        ).returncode
        != 0
    ):
        raise RuntimeError(f"V2.49.29 expected tracked source: {relative}")
    return path


def parent_protocol(root: Path) -> dict[str, Any]:
    path = root / PARENT_PROTOCOL
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("V2.49.29 parent protocol is absent")
    value = json.loads(path.read_text(encoding="utf-8"))
    unsigned = dict(value)
    seal = unsigned.pop("protocol_payload_sha256", None)
    if (
        value.get("protocol_id") != parent.PROTOCOL_ID
        or seal != parent.payload_sha256(unsigned)
        or value.get("dependency_manifest_sha256")
        != parent.payload_sha256(value.get("dependency_manifest"))
    ):
        raise RuntimeError("V2.49.29 parent protocol drifted")
    return value


def source_manifest(root: Path) -> dict[str, str]:
    base = parent_protocol(root)
    relatives = {Path(name) for name in base["dependency_manifest"]}
    relatives.add(PARENT_PROTOCOL)
    relatives.update(LOCAL_SOURCES)
    return {
        str(relative): sha256(ordinary_tracked(root, relative))
        for relative in sorted(relatives, key=str)
    }


def task_vector() -> list[dict[str, str]]:
    tasks = []
    aliases = ("HALF", "ROMAN_EIGHT", "TELEPHONE_SIGN", "LIGATURE_FFI")
    alternate = ("SQUARE_KG", "CELSIUS", "TRADEMARK", "SQUARE_LITRE")
    for index, (topic, *glyphs) in enumerate(TOPICS, start=1):
        labels = aliases if glyphs[0] == "½" else alternate
        rows = "\n".join(
            f"{position}. {glyph} [{label}]"
            for position, (glyph, label) in enumerate(zip(glyphs, labels, strict=True), 1)
        )
        tasks.append(
            {
                "opaque_id": f"task_{0x249290000000000000000000 + index:024x}",
                "question": (
                    f"Using official documentation for {topic}, report the requested "
                    "compatibility characters and their NFKC behavior. Return exactly one "
                    "Markdown table. Column names: Glyph | Unicode name | NFKC normalized "
                    f"sequence | Official reference.\n<ENTITIES>\n{rows}\n</ENTITIES>"
                ),
            }
        )
    if len(tasks) != TASK_COUNT or any(
        set(task) != {"opaque_id", "question"} for task in tasks
    ):
        raise RuntimeError("V2.49.29 neutral task vector drifted")
    return tasks


def protected_watcher_snapshot(proc_root: Path = Path("/proc")) -> list[dict[str, Any]]:
    return parent.protected_watcher_snapshot(proc_root)


__all__ = [name for name in globals() if name.isupper()] + [
    "git",
    "ordinary_tracked",
    "parent_protocol",
    "payload_sha256",
    "protected_watcher_snapshot",
    "sha256",
    "source_manifest",
    "task_vector",
]
