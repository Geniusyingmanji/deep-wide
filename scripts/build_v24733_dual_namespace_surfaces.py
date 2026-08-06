#!/usr/bin/env python3
"""Append-only parser-compatible successor to the quarantined V2.47.30 surfaces."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import build_v24730_dual_namespace_surfaces as frozen  # noqa: E402


DATE = "20260806"
FAILURE_AUDIT = Path(f"results/v24732_v24730_surface_failure_audit_v1_{DATE}.json")
AUTHORIZATION = Path(f"results/v24734_dual_namespace_surface_build_audit_v1_{DATE}.json")
CONTRACT = Path("src/deepwide_agent/v24733_dual_namespace_contract.py")
EVALUATOR = Path("src/deepwide_agent/v24733_dual_namespace_evaluator.py")
ROR_GOLD = Path("evaluation/v24733_ror_gold_v1.csv")
WB_GOLD = Path("evaluation/v24733_worldbank_gold_v1.csv")
PROVENANCE = Path("evaluation/v24733_dual_namespace_gold_provenance_v1.json")
SURFACES = (CONTRACT, EVALUATOR, ROR_GOLD, WB_GOLD, PROVENANCE)
QUARANTINE = Path("quarantine/DO_NOT_USE_v24730_parser_incompatible_20260806")
OLD_BASE = 0x247300
NEW_BASE = 0x247330
TASK_COUNT = frozen.TOTAL_TASKS


def payload_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()
    ).hexdigest()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"V2.47.33 expected ordinary file: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.47.33 expected object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _failure_parent_valid() -> bool:
    value = _read(ROOT / FAILURE_AUDIT)
    hashes = value.get("quarantined_surface_sha256")
    if not isinstance(hashes, Mapping):
        return False
    for original, expected in hashes.items():
        if not isinstance(original, str) or not isinstance(expected, str):
            return False
        path = ROOT / QUARANTINE / Path(original).name
        if not path.is_file() or path.is_symlink() or sha256(path) != expected:
            return False
    return (
        value.get("role") == "v24732_v24730_surface_failure_audit"
        and value.get("failed_stage") == "postpublication_visible_contract_roundtrip"
        and value.get("failure_type")
        == "strict_ror_visible_question_parser_incompatibility"
        and value.get("forward_launches") == 0
        and value.get("model_calls") == 0
        and value.get("search_calls") == 0
        and value.get("evaluator_calls") == 0
        and value.get("usable_surface_count") == 0
        and value.get("authorization")
        == {
            "append_only_surface_successor_implementation": True,
            "surface_publication": False,
            "forward_launch": False,
            "evaluator": False,
            "benchmark_dev64_or_exact220": False,
            "entropy_or_credit_claim": False,
            "leaderboard_or_sota": False,
        }
        and _sealed(value, "audit_payload_sha256")
    )


def _ror_question(group: Sequence[str]) -> str:
    rows = "\n".join(f"{index}. {entity}" for index, entity in enumerate(group, 1))
    return (
        "Use public web sources to return one Markdown table about these organizations:\n"
        f"<ENTITIES>\n{rows}\n</ENTITIES>\n"
        "The column names are: Organization, ROR ID, Country code. "
        "Use the 9-character ROR ID suffix, not the full URL, and the ISO 3166-1 "
        "alpha-2 country code. Return one table only."
    )


def _new_id(ordinal: int) -> str:
    if isinstance(ordinal, bool) or not isinstance(ordinal, int) or not 1 <= ordinal <= TASK_COUNT:
        raise ValueError("V2.47.33 task ordinal drifted")
    return f"task_{NEW_BASE + ordinal:024x}"


def _replace_ids(text: str) -> str:
    output = text
    for ordinal in range(1, TASK_COUNT + 1):
        old = f"task_{OLD_BASE + ordinal:024x}"
        new = _new_id(ordinal)
        if old not in output:
            continue
        output = output.replace(old, new)
    return output


def _rebind_source(text: str) -> str:
    output = text.replace("V2.47.30", "V2.47.33")
    output = output.replace("v24730", "v24733")
    output = output.replace("0x247300", "0x247330")
    output = output.replace(
        'if "<ENTITIES>" in question and "official ROR registry" in question:',
        'if "<ENTITIES>" in question and "The column names are: Organization, ROR ID, Country code." in question:',
    )
    output = output.replace(
        "from .v24686_worldbank_target_value_runtime import _visible_contract",
        "import re",
    )
    parser = r'''
_WORLD_BANK_QUESTION = re.compile(
    r"Use public web sources to return one Markdown table about these countries:\n"
    r"<COUNTRIES>\n(?P<countries>.*?)\n</COUNTRIES>\n"
    r"Please output one Markdown table with the columns, in this exact order:\n"
    r"(?P<columns>[^\n]+)\n"
    r"Use the World Bank API values\. Preserve the decimal representation returned by "
    r"the official API\. Use Unknown when unavailable\. Return one table only\.",
    flags=re.DOTALL,
)
_WORLD_BANK_COUNTRY = re.compile(
    r"(?P<ordinal>[1-4])\. (?P<name>[^\[\]|\r\n]+) \[(?P<iso3>[A-Z]{3})\]"
)
_WORLD_BANK_TARGET = re.compile(
    r"(?P<label>[^|\[\]\r\n]{1,120})\s*"
    r"\[(?P<indicator>[A-Z][A-Z0-9.]{4,40})\]\s*@(?P<year>20[0-3][0-9])"
)


def parse_worldbank_visible_contract(question: str) -> dict[str, object]:
    match = _WORLD_BANK_QUESTION.fullmatch(str(question or "").strip())
    if match is None:
        raise ValueError("V2.47.33 visible World Bank syntax drifted")
    countries = []
    for expected, line in enumerate(match.group("countries").splitlines(), 1):
        parsed = _WORLD_BANK_COUNTRY.fullmatch(line)
        if parsed is None or int(parsed.group("ordinal")) != expected:
            raise ValueError("V2.47.33 visible country vector drifted")
        countries.append({"name": parsed.group("name").strip(), "iso3": parsed.group("iso3")})
    if (
        len(countries) != 4
        or len({item["name"].casefold() for item in countries}) != 4
        or len({item["iso3"] for item in countries}) != 4
    ):
        raise ValueError("V2.47.33 visible country identity drifted")
    columns = [value.strip() for value in match.group("columns").split("|")]
    if len(columns) != 3 or columns[0] != "Country":
        raise ValueError("V2.47.33 visible column vector drifted")
    targets = []
    for column in columns[1:]:
        parsed = _WORLD_BANK_TARGET.fullmatch(column)
        if parsed is None:
            raise ValueError("V2.47.33 visible target address drifted")
        targets.append(
            {
                "label": parsed.group("label").strip(),
                "indicator": parsed.group("indicator"),
                "year": parsed.group("year"),
            }
        )
    if targets != list(WORLD_BANK_TARGETS):
        raise ValueError("V2.47.33 visible target vector drifted")
    return {"countries": countries, "columns": columns, "targets": targets}


'''
    output = output.replace("def visible_namespace(question: str) -> str:\n", parser + "def visible_namespace(question: str) -> str:\n")
    output = output.replace(
        'contract = _visible_contract(question)\n        if len(contract["countries"]) == 4 and contract["targets"] == list(WORLD_BANK_TARGETS):',
        'contract = parse_worldbank_visible_contract(question)\n        if len(contract["countries"]) == 4 and contract["targets"] == list(WORLD_BANK_TARGETS):',
    )
    output = _replace_ids(output)
    return output


def _rebind_provenance(text: str) -> str:
    value = json.loads(text)
    if not isinstance(value, dict):
        raise RuntimeError("V2.47.33 provenance predecessor drifted")
    value.pop("provenance_payload_sha256", None)
    value["role"] = "v24733_dual_namespace_gold_provenance"
    value["predecessor_failure_audit_sha256"] = sha256(ROOT / FAILURE_AUDIT)
    for section in ("ror_source", "worldbank_source"):
        records = value.get(section, {}).get("records", [])
        for record in records:
            opaque_id = str(record.get("opaque_id", ""))
            for ordinal in range(1, TASK_COUNT + 1):
                if opaque_id == f"task_{OLD_BASE + ordinal:024x}":
                    record["opaque_id"] = _new_id(ordinal)
                    break
    value["provenance_payload_sha256"] = payload_sha256(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n"


def build_surfaces() -> dict[Path, str]:
    if not _failure_parent_valid():
        raise RuntimeError("V2.47.33 failure parent drifted")
    previous = {
        "CONTRACT": frozen.CONTRACT,
        "scoring_module_path": frozen.EVALUATOR,
        "ROR_GOLD": frozen.ROR_GOLD,
        "WB_GOLD": frozen.WB_GOLD,
        "PROVENANCE": frozen.PROVENANCE,
        "SURFACES": frozen.SURFACES,
        "ror_question": frozen._ror_question,
    }
    frozen.CONTRACT = CONTRACT
    frozen.EVALUATOR = EVALUATOR
    frozen.ROR_GOLD = ROR_GOLD
    frozen.WB_GOLD = WB_GOLD
    frozen.PROVENANCE = PROVENANCE
    frozen.SURFACES = SURFACES
    frozen._ror_question = _ror_question
    try:
        raw = frozen.build_surfaces()
    finally:
        frozen.CONTRACT = previous["CONTRACT"]
        frozen.EVALUATOR = previous["scoring_module_path"]
        frozen.ROR_GOLD = previous["ROR_GOLD"]
        frozen.WB_GOLD = previous["WB_GOLD"]
        frozen.PROVENANCE = previous["PROVENANCE"]
        frozen.SURFACES = previous["SURFACES"]
        frozen._ror_question = previous["ror_question"]
    if set(raw) != set(SURFACES):
        raise RuntimeError("V2.47.33 predecessor surface set drifted")
    output = {
        CONTRACT: _rebind_source(raw[CONTRACT]),
        EVALUATOR: _rebind_source(raw[EVALUATOR]),
        ROR_GOLD: _replace_ids(raw[ROR_GOLD]),
        WB_GOLD: _replace_ids(raw[WB_GOLD]),
        PROVENANCE: _rebind_provenance(raw[PROVENANCE]),
    }
    if (
        any("v24730" in text or "V2.47.30" in text for text in output.values())
        or any(f"task_{OLD_BASE + ordinal:024x}" in text for text in output.values() for ordinal in range(1, TASK_COUNT + 1))
    ):
        raise RuntimeError("V2.47.33 successor version binding drifted")
    return output


def _authorization_valid() -> bool:
    try:
        value = _read(ROOT / AUTHORIZATION)
    except (OSError, RuntimeError, json.JSONDecodeError):
        return False
    return (
        value.get("role") == "v24734_dual_namespace_surface_build_audit"
        and value.get("audit_valid") is True
        and value.get("findings") == []
        and value.get("authorization")
        == {
            "one_successor_surface_publication": True,
            "reachability_protocol_design": True,
            "forward_launch": False,
            "evaluator_execution": False,
            "benchmark_dev64_or_exact220": False,
            "leaderboard_or_sota": False,
        }
        and _sealed(value, "audit_payload_sha256")
    )


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=20,
    ).stdout.strip()


def _publish(path: Path, text: str) -> None:
    target = ROOT / path
    if target.exists() or target.is_symlink():
        raise FileExistsError(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())


def main() -> None:
    if _git("status", "--porcelain") or _git("rev-parse", "HEAD") != _git(
        "rev-parse", "target/main"
    ):
        raise RuntimeError("V2.47.33 requires clean pushed HEAD")
    if not _authorization_valid():
        raise RuntimeError("V2.47.33 successor publication is not authorized")
    surfaces = build_surfaces()
    if set(surfaces) != set(SURFACES) or any(
        (ROOT / path).exists() or (ROOT / path).is_symlink() for path in SURFACES
    ):
        raise RuntimeError("V2.47.33 successor surface is not pristine")
    created = []
    try:
        for path, text in surfaces.items():
            _publish(path, text)
            created.append(ROOT / path)
    except BaseException:
        for path in reversed(created):
            path.unlink(missing_ok=True)
        raise


if __name__ == "__main__":
    main()
