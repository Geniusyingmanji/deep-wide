#!/usr/bin/env python3
"""One-shot V2.52.97 World Bank population freeze.

Importing this module performs no effect.  A separately pushed execution-start
must exist before :func:`main` may create the permanent attempt claim.  After
that claim, the run performs exactly one source-2 catalog GET.  Only a catalog
that self-proves one-page total coverage can select 24 fresh indicators.  The
run then attempts each of the 48 fixed target pages once, freezes every
successful raw body create-exclusively, and calls the already-audited V2.52.95
selector only when all 48 bodies are present and valid.
"""

from __future__ import annotations

import base64
import copy
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25267_production_only_exact220_contract as seal  # noqa: E402
from deepwide_agent import v25295_worldbank_monotone_fill_gate as runtime  # noqa: E402
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402
from scripts import v25297_worldbank_get_helper as helper  # noqa: E402


DATE = "20260813"
ROLE = "v25297_worldbank_population_freeze"
CLAIM_ROLE = "v25297_worldbank_population_attempt_claim"
OUTPUT_ROOT = Path(f"outputs/v25297_worldbank_population_v1_{DATE}")
CATALOG_RESPONSE = OUTPUT_ROOT / "catalog_response.bin"
TARGET_RESPONSE_ROOT = OUTPUT_ROOT / "target_responses"
POPULATION = OUTPUT_ROOT / "population.json"
ATTEMPT_CLAIM = Path(f"results/v25297_worldbank_population_attempt_claim_v1_{DATE}.json")
RESULT = Path(f"results/v25297_worldbank_population_freeze_v1_{DATE}.json")
PREACTIVATION = Path(f"results/v25298_worldbank_population_preactivation_audit_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v25299_worldbank_population_execution_start_v1_{DATE}.json")
POSTFREEZE_AUDIT = Path(f"results/v25300_worldbank_population_postfreeze_audit_v1_{DATE}.json")
SOURCE = Path("scripts/run_v25297_worldbank_population_freeze.py")
HELPER = Path("scripts/v25297_worldbank_get_helper.py")
TEST = Path("tests/test_run_v25297_worldbank_population_freeze.py")

CATALOG_URL = helper.CATALOG_URL
CATALOG_MAXIMUM_BYTES = helper.CATALOG_MAXIMUM_BYTES
TARGET_MAXIMUM_BYTES = helper.TARGET_MAXIMUM_BYTES
CATALOG_PER_PAGE = 50_000
CATALOG_SOCKET_TIMEOUT_SECONDS = 20.0
TARGET_SOCKET_TIMEOUT_SECONDS = 15.0
HELPER_HARD_TIMEOUT_SECONDS = 25.0
CATALOG_PHASE_HARD_WALL_SECONDS = 30.0
TARGET_PHASE_HARD_WALL_SECONDS = 110.0
WHOLE_FREEZE_HARD_WALL_SECONDS = 145.0
TARGET_CONCURRENCY = 12
CATALOG_SOURCE_ID = "2"
EXPECTED_WATCHERS = (
    {"marker": "scripts/watch_v2415_r1_checkpoint_liveness.py", "pid": 795336, "start_ticks": 713986317},
    {"marker": "scripts/watch_v24215_joint_package_recovery.py", "pid": 2808901, "start_ticks": 746680268},
    {"marker": "scripts/watch_v24216_package_gate.py", "pid": 2889939, "start_ticks": 746969965},
    {"marker": "scripts/watch_v24218_exact220_executor.py", "pid": 3061652, "start_ticks": 747569004},
)

HISTORICAL_SOURCE_HASHES = {
    Path("results/v24721_worldbank_transport_preregistration_v1_20260806.json"): "30162a63fb61aa7ecc7444b7f53a21484840384d5a4949774ca8d6f0fa09c157",
    Path("src/deepwide_agent/v24724_fresh_indicator_transport.py"): "0e81fcd6538a01e9944611194b7318827630142aab09d81202f43fba7f3e9223",
    Path("src/deepwide_agent/v24809_worldbank_budget_ladder_smoke_contract.py"): "812aa9298079b5c4ee8c5c8d41dc63819893f8e54d7b009defde87b4b5da6cd8",
    Path("results/v24829_target_cell_disjoint_worldbank_population_design_v1_20260807.json"): "3710fd775ab9a6d5cf27f5e81ef66a993bf6446e93c5187f0ac27cca47b915d1",
    Path("src/deepwide_agent/v24923_target_value_external_contract.py"): "01a028de8d7c0f24f96684e1d8ce19fc82745a28f0ecfe0b32cc80172a458467",
    Path("src/deepwide_agent/v24925_sparse_target_value_external_contract.py"): "7ad3fa80723565f167c19bba646359b7bd0ce87d221342051ab97d5462467041",
    Path("scripts/control_v24926_snapshot_transport_gate.py"): "02bb38bab8b1f03b2798d20b90902221e711833adad26f96801ce9896e7ab324",
    Path("src/deepwide_agent/v24937_layout_diverse_contextual_external_contract.py"): "430398bb185734cfc14028c97ab3e876f878139277a0762e390dd6210b871306",
    Path("src/deepwide_agent/v24940_open_world_ledger_external_contract.py"): "cbb698144fd7927d79b6a256c14006437b403cd035831f0dc581251ece529bac",
    Path("src/deepwide_agent/v24951_partial_signature_external_contract.py"): "1e7ddababde35484e16eb8cdac073c5b7d95a9af5976e5016b88d902a0805177",
    Path("scripts/audit_v24952_bounded_snapshot_transport_build.py"): "44b946a6a966efc3ded78c31eb0ec45821cc7a486ecd6c3546d4f75f052cbc6a",
}
INDICATOR_LITERAL = re.compile(
    r"(?<![A-Z0-9.])([A-Z][A-Z0-9]{0,7}(?:\.[A-Z0-9]{1,12}){2,8})(?![A-Z0-9.])"
)
EXPECTED_HISTORICAL_INDICATORS = frozenset(
    {
        "AG.LND.AGRI.ZS",
        "AG.LND.FRST.ZS",
        "AG.SRF.TOTL.K2",
        "EG.ELC.ACCS.ZS",
        "EN.POP.DNST",
        "IT.CEL.SETS.P2",
        "IT.NET.USER.ZS",
        "NY.GDP.MKTP.CD",
        "NY.GDP.PCAP.CD",
        "NY.GNP.PCAP.CD",
        "SE.PRM.ENRR",
        "SE.SEC.ENRR",
        "SH.DYN.MORT",
        "SH.H2O.BASW.ZS",
        "SH.IMM.MEAS",
        "SH.STA.BASS.ZS",
        "SL.UEM.TOTL.FE.ZS",
        "SL.UEM.TOTL.MA.ZS",
        "SL.UEM.TOTL.ZS",
        "SP.DYN.IMRT.IN",
        "SP.DYN.LE00.IN",
        "SP.DYN.TFRT.IN",
        "SP.POP.0014.TO.ZS",
        "SP.POP.1564.TO.ZS",
        "SP.POP.65UP.TO.ZS",
        "SP.POP.DPND",
        "SP.POP.GROW",
        "SP.POP.TOTL",
        "SP.POP.TOTL.FE.IN",
        "SP.POP.TOTL.FE.ZS",
        "SP.POP.TOTL.MA.IN",
        "SP.POP.TOTL.MA.ZS",
        "SP.RUR.TOTL.ZS",
        "SP.URB.TOTL.IN.ZS",
        "TG.VAL.TOTL.GD.ZS",
    }
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def payload_sha256(value: object) -> str:
    return seal.payload_sha256(value)


def _ordinary(relative: Path, *, required: bool = True) -> Path:
    path = ROOT / relative
    if path != ROOT / Path(str(relative)) or path.is_symlink():
        raise ValueError("V2.52.97 path drifted")
    if required and (not path.is_file() or not os.path.isfile(path)):
        raise FileNotFoundError(relative)
    return path


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=20,
        check=True,
    ).stdout.strip()


def _protected_watchers_match() -> bool:
    for row in EXPECTED_WATCHERS:
        try:
            stat = (Path("/proc") / str(row["pid"]) / "stat").read_text(encoding="utf-8")
            suffix = stat[stat.rfind(")") + 2 :].split()
            start_ticks = int(suffix[19]) if len(suffix) > 19 else None
            command = (Path("/proc") / str(row["pid"]) / "cmdline").read_bytes().replace(b"\0", b" ").decode()
        except (OSError, UnicodeDecodeError, ValueError):
            return False
        if start_ticks != row["start_ticks"] or row["marker"] not in command:
            return False
    return True


def publish_exclusive(path: Path, data: bytes) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def publish_json_exclusive(path: Path, value: Mapping[str, Any]) -> None:
    publish_exclusive(
        path,
        (json.dumps(dict(value), ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(),
    )


def historical_indicator_manifest() -> tuple[frozenset[str], list[dict[str, Any]]]:
    found: set[str] = set()
    rows: list[dict[str, Any]] = []
    for relative, expected in HISTORICAL_SOURCE_HASHES.items():
        path = _ordinary(relative)
        observed = sha256(path)
        if observed != expected:
            raise RuntimeError("V2.52.97 historical source hash drifted")
        indicators = sorted(set(INDICATOR_LITERAL.findall(path.read_text(encoding="utf-8"))))
        indicators = [
            value
            for value in indicators
            if runtime.INDICATOR.fullmatch(value) and not value.startswith("V2.")
        ]
        found.update(indicators)
        rows.append(
            {
                "path": str(relative),
                "sha256": observed,
                "indicator_count": len(indicators),
                "indicators_sha256": payload_sha256(indicators),
            }
        )
    if found != set(EXPECTED_HISTORICAL_INDICATORS):
        raise RuntimeError("V2.52.97 historical indicator manifest drifted")
    return frozenset(found), rows


def target_urls(indicator: str) -> tuple[str, str]:
    if runtime.INDICATOR.fullmatch(indicator) is None:
        raise ValueError("V2.52.97 indicator drifted")
    prefix = f"https://api.worldbank.org/v2/country/all/indicator/{indicator}"
    return tuple(
        f"{prefix}?date={runtime.TARGET_YEAR}&format=json&page={page}"
        f"&per_page={runtime.WORLD_BANK_PER_PAGE}"
        for page in (1, 2)
    )  # type: ignore[return-value]


def parse_catalog(blob: bytes, *, historical: Sequence[str]) -> tuple[list[runtime.TargetSpec], dict[str, int]]:
    if not isinstance(blob, bytes) or not blob or len(blob) > CATALOG_MAXIMUM_BYTES:
        raise ValueError("V2.52.97 catalog bytes drifted")
    try:
        value = json.loads(blob)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("V2.52.97 catalog JSON invalid") from exc
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError("V2.52.97 catalog envelope drifted")
    metadata, records = value
    if not isinstance(metadata, Mapping) or not isinstance(records, list):
        raise ValueError("V2.52.97 catalog schema drifted")
    try:
        page = int(metadata["page"])
        pages = int(metadata["pages"])
        per_page = int(metadata["per_page"])
        total = int(metadata["total"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("V2.52.97 catalog metadata drifted") from exc
    if (
        page != 1
        or pages != 1
        or per_page != CATALOG_PER_PAGE
        or total != len(records)
        or not runtime.MINIMUM_TARGET_OVERSAMPLE <= total <= CATALOG_PER_PAGE
    ):
        raise ValueError("V2.52.97 catalog does not self-prove complete coverage")
    old = {str(item).strip().upper() for item in historical}
    observed: set[str] = set()
    compatible: list[runtime.TargetSpec] = []
    for record in records:
        if not isinstance(record, Mapping):
            raise ValueError("V2.52.97 catalog record drifted")
        indicator = str(record.get("id") or "").strip().upper()
        source = record.get("source") or {}
        source_id = str(source.get("id") if isinstance(source, Mapping) else "").strip()
        if not indicator or indicator in observed or source_id != CATALOG_SOURCE_ID:
            raise ValueError("V2.52.97 catalog identity/source drifted")
        observed.add(indicator)
        label = " ".join(str(record.get("name") or "").split())
        if (
            runtime.INDICATOR.fullmatch(indicator) is None
            or indicator in old
            or not label
            or len(label) > 80
            or any(character in label for character in "|`\r\n")
        ):
            continue
        spec = runtime.TargetSpec(
            label=label,
            indicator=indicator,
            year=runtime.TARGET_YEAR,
            urls=target_urls(indicator),
        )
        spec.validate()
        compatible.append(spec)
    ranked = sorted(
        compatible,
        key=lambda item: (runtime._rank("target", item.key), item.key),
    )
    selected = ranked[: runtime.MINIMUM_TARGET_OVERSAMPLE]
    if len(selected) != runtime.MINIMUM_TARGET_OVERSAMPLE:
        raise RuntimeError("V2.52.97 fresh catalog capacity is insufficient")
    return selected, {
        "catalog_total": total,
        "runtime_compatible_fresh_count": len(compatible),
        "selected_candidate_count": len(selected),
    }


def _transport_receipt(url: str, maximum: int, value: Mapping[str, Any], *, elapsed: float) -> tuple[bytes | None, dict[str, Any]]:
    kind = value.get("kind")
    attempted = value.get("provider_attempt_count")
    status = value.get("status_code")
    content_type = str(value.get("content_type") or "").split(";", 1)[0].strip().casefold()
    final_url = value.get("final_url")
    encoded = value.get("body_base64")
    body: bytes | None = None
    failure: str | None = None
    try:
        decoded = base64.b64decode(str(encoded), validate=True) if encoded else b""
    except (ValueError, TypeError):
        decoded = b""
        failure = "helper_body_encoding"
    if failure is None and (
        kind != "response"
        or attempted != 1
        or status != 200
        or content_type != "application/json"
        or final_url != url
        or not decoded
        or len(decoded) > maximum
    ):
        failure = str(kind) if isinstance(kind, str) and kind else "helper_response_contract"
    if failure is None:
        body = decoded
    receipt = {
        "url_sha256": hashlib.sha256(url.encode()).hexdigest(),
        "maximum_response_bytes": maximum,
        "provider_attempt_count": attempted if isinstance(attempted, int) else 0,
        "outcome": "success" if body is not None else "failure",
        "failure_code": failure,
        "http_status": status if isinstance(status, int) else None,
        "elapsed_seconds": round(max(0.0, float(elapsed)), 6),
        "response_bytes": len(body) if body is not None else 0,
        "response_sha256": hashlib.sha256(body).hexdigest() if body is not None else None,
        "redirect_retry_refetch_count": 0,
    }
    return body, receipt


def invoke_helper(url: str, maximum: int, socket_timeout: float) -> tuple[bytes | None, dict[str, Any]]:
    started = time.monotonic()
    env = {
        "HOME": os.environ.get("HOME", str(Path.home())),
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "DEEPWIDE_EXPECTED_PARENT_PID": str(os.getpid()),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "PYTHONSAFEPATH": "1",
    }
    try:
        completed = subprocess.run(
            [sys.executable, "-I", "-B", str(ROOT / HELPER)],
            cwd=ROOT,
            env=env,
            input=json.dumps(
                {
                    "url": url,
                    "socket_timeout_seconds": socket_timeout,
                    "maximum_response_bytes": maximum,
                }
            ),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=HELPER_HARD_TIMEOUT_SECONDS,
            check=False,
        )
        value = json.loads(completed.stdout) if completed.returncode == 0 else {}
        if not isinstance(value, Mapping):
            value = {}
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
        value = {}
    return _transport_receipt(url, maximum, value, elapsed=time.monotonic() - started)


def _request_target_pages(
    targets: Sequence[runtime.TargetSpec],
    *,
    get: Callable[[str, int, float], tuple[bytes | None, dict[str, Any]]],
) -> tuple[
    dict[runtime.TargetSpec, tuple[bytes, bytes]],
    dict[tuple[int, int], bytes],
    list[dict[str, Any]],
    float,
]:
    if len(targets) != runtime.MINIMUM_TARGET_OVERSAMPLE:
        raise ValueError("V2.52.97 target vector drifted")
    work = [(index, target, page, target.urls[page - 1]) for index, target in enumerate(targets, 1) for page in (1, 2)]
    started = time.monotonic()
    bodies: dict[tuple[int, int], bytes] = {}
    rows: dict[tuple[int, int], dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=TARGET_CONCURRENCY) as executor:
        futures = {
            executor.submit(get, url, TARGET_MAXIMUM_BYTES, TARGET_SOCKET_TIMEOUT_SECONDS): (index, target, page)
            for index, target, page, url in work
        }
        for future in as_completed(futures):
            index, target, page = futures[future]
            try:
                body, receipt = future.result()
            except BaseException:
                body, receipt = None, {
                    "url_sha256": hashlib.sha256(target.urls[page - 1].encode()).hexdigest(),
                    "maximum_response_bytes": TARGET_MAXIMUM_BYTES,
                    "provider_attempt_count": 0,
                    "outcome": "failure",
                    "failure_code": "supervisor_error",
                    "http_status": None,
                    "elapsed_seconds": 0.0,
                    "response_bytes": 0,
                    "response_sha256": None,
                    "redirect_retry_refetch_count": 0,
                }
            row = {
                "candidate_ordinal": index,
                "target_key": target.key,
                "page": page,
                **copy.deepcopy(receipt),
            }
            rows[(index, page)] = row
            if body is not None:
                bodies[(index, page)] = body
    elapsed = time.monotonic() - started
    ordered = [rows[(index, page)] for index, _target, page, _url in work]
    grouped: dict[runtime.TargetSpec, tuple[bytes, bytes]] = {}
    if len(bodies) == len(work):
        for index, target in enumerate(targets, 1):
            grouped[target] = (bodies[(index, 1)], bodies[(index, 2)])
    return grouped, bodies, ordered, elapsed


def build_attempt_claim(*, head: str, execution_start_sha256: str, now: int | None = None) -> dict[str, Any]:
    if re.fullmatch(r"[0-9a-f]{40}", head) is None or re.fullmatch(r"[0-9a-f]{64}", execution_start_sha256) is None:
        raise ValueError("V2.52.97 claim authority drifted")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": CLAIM_ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git_head": head,
        "execution_start": {"path": str(EXECUTION_START), "sha256": execution_start_sha256},
        "fixed_result_path": str(RESULT),
        "fixed_output_root": str(OUTPUT_ROOT),
        "claim_created_before_catalog_or_target_network_effect": True,
        "claim_is_permanent_even_on_crash_or_no_go": True,
        "single_catalog_and_single_48_response_batch_only": True,
        "retry_resume_backfill_replacement_or_second_attempt": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
    }
    value["claim_payload_sha256"] = payload_sha256(value)
    return validate_attempt_claim(value)


def validate_attempt_claim(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    signature = unsigned.pop("claim_payload_sha256", None)
    if (
        set(copied)
        != {
            "artifact_version", "role", "created_at_unix", "git_head", "execution_start",
            "fixed_result_path", "fixed_output_root", "claim_created_before_catalog_or_target_network_effect",
            "claim_is_permanent_even_on_crash_or_no_go", "single_catalog_and_single_48_response_batch_only",
            "retry_resume_backfill_replacement_or_second_attempt",
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read",
            "entropy_or_information_gain_assigns_signed_credit", "claim_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != CLAIM_ROLE
        or isinstance(copied.get("created_at_unix"), bool)
        or not isinstance(copied.get("created_at_unix"), int)
        or re.fullmatch(r"[0-9a-f]{40}", str(copied.get("git_head"))) is None
        or not isinstance(copied.get("execution_start"), Mapping)
        or set(copied["execution_start"]) != {"path", "sha256"}
        or copied.get("execution_start", {}).get("path") != str(EXECUTION_START)
        or re.fullmatch(r"[0-9a-f]{64}", str(copied.get("execution_start", {}).get("sha256"))) is None
        or copied.get("fixed_result_path") != str(RESULT)
        or copied.get("fixed_output_root") != str(OUTPUT_ROOT)
        or copied.get("claim_created_before_catalog_or_target_network_effect") is not True
        or copied.get("claim_is_permanent_even_on_crash_or_no_go") is not True
        or copied.get("single_catalog_and_single_48_response_batch_only") is not True
        or copied.get("retry_resume_backfill_replacement_or_second_attempt") is not False
        or copied.get("mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read") is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit") is not False
        or signature != payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.97 attempt claim drifted")
    return copied


def execute_freeze(
    *,
    head: str,
    execution_start_sha256: str,
    attempt_claim_sha256: str,
    get: Callable[[str, int, float], tuple[bytes | None, dict[str, Any]]] = invoke_helper,
    persist: bool = True,
    now: int | None = None,
) -> dict[str, Any]:
    started = time.monotonic()
    historical, manifest = historical_indicator_manifest()
    catalog_started = time.monotonic()
    catalog_body, catalog_receipt = get(CATALOG_URL, CATALOG_MAXIMUM_BYTES, CATALOG_SOCKET_TIMEOUT_SECONDS)
    catalog_elapsed = time.monotonic() - catalog_started
    candidates: list[runtime.TargetSpec] = []
    catalog_stats = {"catalog_total": 0, "runtime_compatible_fresh_count": 0, "selected_candidate_count": 0}
    failure: str | None = None
    if catalog_body is not None and persist:
        publish_exclusive(ROOT / CATALOG_RESPONSE, catalog_body)
    if catalog_body is None:
        failure = "catalog_transport"
    elif catalog_elapsed > CATALOG_PHASE_HARD_WALL_SECONDS:
        failure = "catalog_hard_wall"
    else:
        try:
            candidates, catalog_stats = parse_catalog(catalog_body, historical=historical)
        except (RuntimeError, ValueError):
            failure = "catalog_validation_or_capacity"
    candidate_keys = [target.key for target in candidates]
    target_rows: list[dict[str, Any]] = []
    candidate_bodies: dict[runtime.TargetSpec, tuple[bytes, bytes]] = {}
    target_elapsed = 0.0
    population_value: dict[str, Any] | None = None
    if failure is None:
        candidate_bodies, successful_bodies, target_rows, target_elapsed = _request_target_pages(candidates, get=get)
        for row in target_rows:
            key = (int(row["candidate_ordinal"]), int(row["page"]))
            if key in successful_bodies:
                body = successful_bodies[key]
                relative = TARGET_RESPONSE_ROOT / f"response_{key[0]:02d}_page_{key[1]}.bin"
                row["response_path"] = str(relative)
                if persist:
                    publish_exclusive(ROOT / relative, body)
            else:
                row["response_path"] = None
        if (
            len(target_rows) != 48
            or len(candidate_bodies) != runtime.MINIMUM_TARGET_OVERSAMPLE
            or any(row["outcome"] != "success" for row in target_rows)
            or target_elapsed > TARGET_PHASE_HARD_WALL_SECONDS
        ):
            failure = "target_transport_or_hard_wall"
    if failure is None:
        try:
            population_value = runtime.select_and_render_population(
                candidate_bodies,
                historical_target_keys=[f"{indicator}@{runtime.TARGET_YEAR}" for indicator in historical],
            )
        except (RuntimeError, ValueError):
            failure = "population_capacity_or_rendering"
    elapsed = time.monotonic() - started
    if elapsed > WHOLE_FREEZE_HARD_WALL_SECONDS and failure is None:
        failure = "whole_freeze_hard_wall"
        population_value = None
    population_sha: str | None = None
    if population_value is not None and failure is None:
        envelope = {
            "artifact_version": 1,
            "role": "v25297_private_frozen_worldbank_population",
            "candidate_target_keys": candidate_keys,
            "historical_indicator_manifest_sha256": payload_sha256(sorted(historical)),
            "population": population_value,
        }
        envelope["population_payload_sha256"] = payload_sha256(envelope)
        encoded = (json.dumps(envelope, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
        population_sha = hashlib.sha256(encoded).hexdigest()
        if persist:
            publish_exclusive(ROOT / POPULATION, encoded)
    selected_keys = list(population_value["target_keys"]) if population_value else []
    entities = list(population_value["entities"]) if population_value else []
    tasks = list(population_value["tasks"]) if population_value else []
    decision = "go" if failure is None and population_value is not None else "no_go"
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git_head": head,
        "execution_start": {"path": str(EXECUTION_START), "sha256": execution_start_sha256},
        "attempt_claim": {"path": str(ATTEMPT_CLAIM), "sha256": attempt_claim_sha256},
        "decision": decision,
        "failure_code": failure,
        "catalog": {
            **catalog_receipt,
            **catalog_stats,
            "phase_elapsed_seconds": round(catalog_elapsed, 6),
            "url": CATALOG_URL,
            "response_path": str(CATALOG_RESPONSE) if catalog_body is not None else None,
            "self_proved_one_page_complete": bool(candidates),
        },
        "historical_indicator_manifest": manifest,
        "historical_indicator_count": len(historical),
        "historical_indicators_sha256": payload_sha256(sorted(historical)),
        "candidate_target_keys": candidate_keys,
        "candidate_target_count": len(candidate_keys),
        "target_transport": {
            "fixed_request_count": 48,
            "concurrency": TARGET_CONCURRENCY,
            "elapsed_seconds": round(target_elapsed, 6),
            "rows": target_rows,
            "successful_response_count": sum(row.get("outcome") == "success" for row in target_rows),
            "provider_attempt_count": sum(int(row.get("provider_attempt_count") or 0) for row in target_rows),
        },
        "population": {
            "private_path": str(POPULATION) if population_sha else None,
            "private_sha256": population_sha,
            "selected_target_keys": selected_keys,
            "selected_target_count": len(selected_keys),
            "entity_count": len(entities),
            "entities_sha256": payload_sha256(entities) if entities else None,
            "task_count": len(tasks),
            "task_vector_sha256": payload_sha256(tasks) if tasks else None,
            "rendered_page_count": len(population_value["pages"]) if population_value else 0,
        },
        "effect_accounting": {
            "catalog_provider_attempt_count": int(catalog_receipt.get("provider_attempt_count") or 0),
            "target_provider_attempt_count": sum(int(row.get("provider_attempt_count") or 0) for row in target_rows),
            "redirect_retry_refetch_resume_backfill_replacement_count": 0,
            "model_search_evaluator_or_benchmark_effect_count": 0,
            "public_worldbank_network_or_api_called": bool(
                int(catalog_receipt.get("provider_attempt_count") or 0)
                + sum(int(row.get("provider_attempt_count") or 0) for row in target_rows)
            ),
        },
        "whole_elapsed_seconds": round(elapsed, 6),
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "authorization": {
            "external_monotone_fill_forward_after_valid_postfreeze_audit": decision == "go",
            "postfreeze_evaluator": False,
            "deepwidebench_dev64_exact220_forward_or_evaluator": False,
            "retry_resume_backfill_replacement_or_second_population_attempt": False,
            "avg_at_4_leaderboard_or_sota": False,
        },
    }
    value["freeze_payload_sha256"] = payload_sha256(value)
    return validate_result(value)


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    signature = unsigned.pop("freeze_payload_sha256", None)
    decision = copied.get("decision")
    catalog = copied.get("catalog") or {}
    target = copied.get("target_transport") or {}
    population = copied.get("population") or {}
    effects = copied.get("effect_accounting") or {}
    authorization = copied.get("authorization") or {}
    rows = target.get("rows")
    manifest = copied.get("historical_indicator_manifest")
    go = decision == "go"
    expected_manifest = historical_indicator_manifest()[1]
    top_keys = {
        "artifact_version", "role", "created_at_unix", "git_head", "execution_start",
        "attempt_claim", "decision", "failure_code", "catalog",
        "historical_indicator_manifest", "historical_indicator_count",
        "historical_indicators_sha256", "candidate_target_keys",
        "candidate_target_count", "target_transport", "population",
        "effect_accounting", "whole_elapsed_seconds",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read",
        "entropy_or_information_gain_assigns_signed_credit", "authorization",
        "freeze_payload_sha256",
    }
    receipt_keys = {
        "url_sha256", "maximum_response_bytes", "provider_attempt_count", "outcome",
        "failure_code", "http_status", "elapsed_seconds", "response_bytes",
        "response_sha256", "redirect_retry_refetch_count",
    }
    catalog_keys = receipt_keys | {
        "catalog_total", "runtime_compatible_fresh_count", "selected_candidate_count",
        "phase_elapsed_seconds", "url", "response_path", "self_proved_one_page_complete",
    }
    row_keys = receipt_keys | {"candidate_ordinal", "target_key", "page", "response_path"}
    candidate_keys = copied.get("candidate_target_keys")
    execution_start = copied.get("execution_start")
    attempt_claim = copied.get("attempt_claim")
    row_shape_valid = isinstance(rows, list) and all(
        isinstance(row, Mapping)
        and set(row) == row_keys
        and isinstance(row.get("candidate_ordinal"), int)
        and not isinstance(row.get("candidate_ordinal"), bool)
        and row.get("page") in {1, 2}
        and row.get("outcome") in {"success", "failure"}
        and row.get("provider_attempt_count") in {0, 1}
        and row.get("maximum_response_bytes") == TARGET_MAXIMUM_BYTES
        and row.get("redirect_retry_refetch_count") == 0
        and isinstance(row.get("elapsed_seconds"), (int, float))
        and not isinstance(row.get("elapsed_seconds"), bool)
        and math.isfinite(float(row["elapsed_seconds"]))
        and 0 <= float(row["elapsed_seconds"]) <= HELPER_HARD_TIMEOUT_SECONDS + 2
        for row in (rows or [])
    )
    row_identity_valid = False
    if row_shape_valid and isinstance(candidate_keys, list):
        expected_pairs = {(index, page) for index in range(1, len(candidate_keys) + 1) for page in (1, 2)}
        observed_pairs = {(row["candidate_ordinal"], row["page"]) for row in rows}
        row_identity_valid = observed_pairs == (expected_pairs if rows else set())
        for row in rows:
            index = int(row["candidate_ordinal"])
            key = candidate_keys[index - 1] if 0 < index <= len(candidate_keys) else ""
            if row["target_key"] != key or not key.endswith("@2022"):
                row_identity_valid = False
                break
            indicator = key.rsplit("@", 1)[0]
            expected_url = target_urls(indicator)[int(row["page"]) - 1]
            expected_path = TARGET_RESPONSE_ROOT / f"response_{index:02d}_page_{row['page']}.bin"
            success = row["outcome"] == "success"
            if (
                row["url_sha256"] != hashlib.sha256(expected_url.encode()).hexdigest()
                or (success and (
                    row["provider_attempt_count"] != 1
                    or row["failure_code"] is not None
                    or row["http_status"] != 200
                    or not isinstance(row["response_bytes"], int)
                    or row["response_bytes"] <= 0
                    or re.fullmatch(r"[0-9a-f]{64}", str(row["response_sha256"])) is None
                    or row["response_path"] != str(expected_path)
                ))
                or (not success and (
                    not isinstance(row["failure_code"], str)
                    or row["response_bytes"] != 0
                    or row["response_sha256"] is not None
                    or row["response_path"] is not None
                ))
            ):
                row_identity_valid = False
                break
    catalog_success = catalog.get("outcome") == "success"
    catalog_shape_valid = bool(
        isinstance(catalog, Mapping)
        and set(catalog) == catalog_keys
        and catalog.get("url") == CATALOG_URL
        and catalog.get("url_sha256") == hashlib.sha256(CATALOG_URL.encode()).hexdigest()
        and catalog.get("maximum_response_bytes") == CATALOG_MAXIMUM_BYTES
        and catalog.get("provider_attempt_count") in {0, 1}
        and catalog.get("redirect_retry_refetch_count") == 0
        and isinstance(catalog.get("elapsed_seconds"), (int, float))
        and isinstance(catalog.get("phase_elapsed_seconds"), (int, float))
        and not isinstance(catalog.get("elapsed_seconds"), bool)
        and not isinstance(catalog.get("phase_elapsed_seconds"), bool)
        and math.isfinite(float(catalog["elapsed_seconds"]))
        and math.isfinite(float(catalog["phase_elapsed_seconds"]))
        and 0 <= float(catalog["elapsed_seconds"]) <= HELPER_HARD_TIMEOUT_SECONDS + 2
        and 0 <= float(catalog["phase_elapsed_seconds"])
        and all(
            isinstance(catalog.get(name), int) and not isinstance(catalog.get(name), bool)
            for name in ("catalog_total", "runtime_compatible_fresh_count", "selected_candidate_count")
        )
        and (not catalog_success or (
            catalog.get("provider_attempt_count") == 1
            and catalog.get("failure_code") is None
            and catalog.get("http_status") == 200
            and isinstance(catalog.get("response_bytes"), int)
            and catalog["response_bytes"] > 0
            and re.fullmatch(r"[0-9a-f]{64}", str(catalog.get("response_sha256"))) is not None
            and catalog.get("response_path") == str(CATALOG_RESPONSE)
        ))
        and (catalog_success or (
            isinstance(catalog.get("failure_code"), str)
            and catalog.get("response_bytes") == 0
            and catalog.get("response_sha256") is None
            and catalog.get("response_path") is None
        ))
    )
    if (
        set(copied) != top_keys
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or isinstance(copied.get("created_at_unix"), bool)
        or not isinstance(copied.get("created_at_unix"), int)
        or re.fullmatch(r"[0-9a-f]{40}", str(copied.get("git_head"))) is None
        or not isinstance(execution_start, Mapping)
        or set(execution_start) != {"path", "sha256"}
        or execution_start.get("path") != str(EXECUTION_START)
        or re.fullmatch(r"[0-9a-f]{64}", str(execution_start.get("sha256"))) is None
        or not isinstance(attempt_claim, Mapping)
        or set(attempt_claim) != {"path", "sha256"}
        or attempt_claim.get("path") != str(ATTEMPT_CLAIM)
        or re.fullmatch(r"[0-9a-f]{64}", str(attempt_claim.get("sha256"))) is None
        or decision not in {"go", "no_go"}
        or (copied.get("failure_code") is None) is not go
        or not catalog_shape_valid
        or catalog.get("self_proved_one_page_complete")
        is not (copied.get("candidate_target_count") == runtime.MINIMUM_TARGET_OVERSAMPLE)
        or not isinstance(candidate_keys, list)
        or len(candidate_keys) != len(set(candidate_keys))
        or any(
            not isinstance(key, str)
            or not key.endswith("@2022")
            or runtime.INDICATOR.fullmatch(key.rsplit("@", 1)[0]) is None
            for key in candidate_keys
        )
        or copied.get("historical_indicator_count") != len(EXPECTED_HISTORICAL_INDICATORS)
        or copied.get("historical_indicators_sha256") != payload_sha256(sorted(EXPECTED_HISTORICAL_INDICATORS))
        or manifest != expected_manifest
        or copied.get("candidate_target_count") != len(copied.get("candidate_target_keys") or [])
        or not isinstance(target, Mapping)
        or set(target) != {
            "fixed_request_count", "concurrency", "elapsed_seconds", "rows",
            "successful_response_count", "provider_attempt_count",
        }
        or target.get("fixed_request_count") != 48
        or target.get("concurrency") != TARGET_CONCURRENCY
        or not isinstance(target.get("elapsed_seconds"), (int, float))
        or isinstance(target.get("elapsed_seconds"), bool)
        or not math.isfinite(float(target["elapsed_seconds"]))
        or not 0 <= float(target["elapsed_seconds"])
        or not row_shape_valid
        or not row_identity_valid
        or len(rows) not in {0, 48}
        or target.get("successful_response_count") != sum(row.get("outcome") == "success" for row in rows)
        or target.get("provider_attempt_count") != sum(int(row.get("provider_attempt_count") or 0) for row in rows)
        or not isinstance(population, Mapping)
        or set(population) != {
            "private_path", "private_sha256", "selected_target_keys", "selected_target_count",
            "entity_count", "entities_sha256", "task_count", "task_vector_sha256",
            "rendered_page_count",
        }
        or population.get("selected_target_count") != len(population.get("selected_target_keys") or [])
        or any(
            not isinstance(key, str)
            or key != key.casefold()
            or key not in {candidate.casefold() for candidate in candidate_keys}
            for key in (population.get("selected_target_keys") or [])
        )
        or not isinstance(effects, Mapping)
        or set(effects) != {
            "catalog_provider_attempt_count", "target_provider_attempt_count",
            "redirect_retry_refetch_resume_backfill_replacement_count",
            "model_search_evaluator_or_benchmark_effect_count",
            "public_worldbank_network_or_api_called",
        }
        or effects.get("catalog_provider_attempt_count") not in {0, 1}
        or effects.get("target_provider_attempt_count") != target.get("provider_attempt_count")
        or effects.get("redirect_retry_refetch_resume_backfill_replacement_count") != 0
        or effects.get("model_search_evaluator_or_benchmark_effect_count") != 0
        or effects.get("public_worldbank_network_or_api_called") is not bool(
            effects.get("catalog_provider_attempt_count") + effects.get("target_provider_attempt_count")
        )
        or not isinstance(copied.get("whole_elapsed_seconds"), (int, float))
        or isinstance(copied.get("whole_elapsed_seconds"), bool)
        or not math.isfinite(float(copied["whole_elapsed_seconds"]))
        or not 0 <= float(copied["whole_elapsed_seconds"])
        or copied.get("mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read") is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit") is not False
        or authorization
        != {
            "external_monotone_fill_forward_after_valid_postfreeze_audit": go,
            "postfreeze_evaluator": False,
            "deepwidebench_dev64_exact220_forward_or_evaluator": False,
            "retry_resume_backfill_replacement_or_second_population_attempt": False,
            "avg_at_4_leaderboard_or_sota": False,
        }
        or (go and (
            len(rows) != 48
            or target.get("successful_response_count") != 48
            or target.get("provider_attempt_count") != 48
            or copied.get("candidate_target_count") != 24
            or population.get("selected_target_count") != 4
            or population.get("entity_count") != 144
            or population.get("task_count") != 12
            or population.get("rendered_page_count") != 8
            or not population.get("private_sha256")
        ))
        or (not go and population != {
            "private_path": None,
            "private_sha256": None,
            "selected_target_keys": [],
            "selected_target_count": 0,
            "entity_count": 0,
            "entities_sha256": None,
            "task_count": 0,
            "task_vector_sha256": None,
            "rendered_page_count": 0,
        })
        or signature != payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.97 population result drifted")
    return copied


def _source_manifest() -> dict[str, str]:
    return {str(path): sha256(_ordinary(path)) for path in (SOURCE, HELPER, TEST)}


def _preactivation_authority() -> bool:
    try:
        path = _ordinary(PREACTIVATION)
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, Mapping):
            return False
        unsigned = dict(value)
        signature = unsigned.pop("audit_payload_sha256", None)
        authorization = value.get("authorization") or {}
        return bool(
            value.get("artifact_version") == 1
            and value.get("role") == "v25298_worldbank_population_preactivation_audit"
            and value.get("audit_valid") is True
            and value.get("findings") == []
            and value.get("source_manifest") == _source_manifest()
            and value.get("mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read") is False
            and value.get("network_model_search_fetch_evaluator_benchmark_or_api_called") is False
            and value.get("entropy_or_information_gain_assigns_signed_credit") is False
            and authorization
            == {
                "execution_start_generation": True,
                "single_worldbank_population_freeze": False,
                "external_monotone_fill_forward_or_postfreeze_evaluator": False,
                "deepwidebench_dev64_exact220_forward_or_evaluator": False,
                "retry_resume_refetch_backfill_replacement_or_second_attempt": False,
                "avg_at_4_leaderboard_or_sota": False,
            }
            and signature == payload_sha256(unsigned)
        )
    except (FileNotFoundError, OSError, TypeError, ValueError, json.JSONDecodeError):
        return False


def _validate_execution_start(value: Mapping[str, Any], *, current_head: str) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    signature = unsigned.pop("start_payload_sha256", None)
    authorization = copied.get("authorization") or {}
    expected_keys = {
        "artifact_version", "role", "created_at_unix", "git_parent",
        "preactivation_audit", "source_manifest", "runtime_state",
        "transport_contract", "fixed_attempt_claim_path", "fixed_result_path",
        "fixed_output_root", "single_catalog_then_single_48_target_response_batch",
        "retry_resume_refetch_backfill_replacement_or_second_attempt",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read",
        "entropy_or_information_gain_assigns_signed_credit", "authorization",
        "start_payload_sha256",
    }
    if (
        set(copied) != expected_keys
        or copied.get("artifact_version") != 1
        or copied.get("role") != "v25299_worldbank_population_execution_start"
        or isinstance(copied.get("created_at_unix"), bool)
        or not isinstance(copied.get("created_at_unix"), int)
        or re.fullmatch(r"[0-9a-f]{40}", current_head) is None
        or re.fullmatch(r"[0-9a-f]{40}", str(copied.get("git_parent"))) is None
        or not isinstance(copied.get("preactivation_audit"), Mapping)
        or set(copied["preactivation_audit"]) != {"path", "sha256"}
        or copied["preactivation_audit"].get("path") != str(PREACTIVATION)
        or copied["preactivation_audit"].get("sha256") != sha256(_ordinary(PREACTIVATION))
        or copied.get("source_manifest") != _source_manifest()
        or copied.get("runtime_state")
        != {"protected_watchers": list(EXPECTED_WATCHERS), "shared_api_lease_inactive": True}
        or copied.get("transport_contract")
        != {
            "catalog_url": CATALOG_URL,
            "catalog_provider_attempt_count": 1,
            "candidate_target_count": runtime.MINIMUM_TARGET_OVERSAMPLE,
            "target_provider_attempt_count": 48,
            "target_concurrency": TARGET_CONCURRENCY,
            "catalog_phase_hard_wall_seconds": CATALOG_PHASE_HARD_WALL_SECONDS,
            "target_phase_hard_wall_seconds": TARGET_PHASE_HARD_WALL_SECONDS,
            "whole_freeze_hard_wall_seconds": WHOLE_FREEZE_HARD_WALL_SECONDS,
        }
        or copied.get("fixed_attempt_claim_path") != str(ATTEMPT_CLAIM)
        or copied.get("fixed_result_path") != str(RESULT)
        or copied.get("fixed_output_root") != str(OUTPUT_ROOT)
        or copied.get("single_catalog_then_single_48_target_response_batch") is not True
        or copied.get("retry_resume_refetch_backfill_replacement_or_second_attempt") is not False
        or authorization.get("single_worldbank_population_freeze") is not True
        or authorization.get("external_forward_or_evaluator") is not False
        or copied.get("mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read") is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit") is not False
        or not _preactivation_authority()
        or signature != payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.99 execution start drifted")
    return copied


def main() -> None:
    head = _git("rev-parse", "HEAD")
    if _git("status", "--porcelain") or head != _git("rev-parse", "target/main"):
        raise RuntimeError("V2.52.97 requires clean pushed HEAD")
    if any((ROOT / path).exists() or (ROOT / path).is_symlink() for path in (ATTEMPT_CLAIM, RESULT, OUTPUT_ROOT, POSTFREEZE_AUDIT)):
        raise FileExistsError("V2.52.97 future surface is not pristine")
    start_path = _ordinary(EXECUTION_START)
    start = _validate_execution_start(json.loads(start_path.read_text(encoding="utf-8")), current_head=head)
    if (
        _git("rev-parse", f"{head}^") != start["git_parent"]
        or sorted(
            line
            for line in _git("diff-tree", "--no-commit-id", "--name-only", "-r", head).splitlines()
            if line
        )
        != [str(EXECUTION_START)]
    ):
        raise RuntimeError("V2.52.99 execution-start commit boundary drifted")
    if not _protected_watchers_match():
        raise RuntimeError("V2.52.97 protected watcher identity drifted")
    start_sha = sha256(start_path)
    if start.get("git_head") != head:
        raise RuntimeError("V2.52.97 start/head boundary drifted")
    with acquire_deepwide_api_lease(
        ROOT,
        owner="v25297_worldbank_population_freeze",
        purpose="single_catalog_and_single_48_target_response_population_freeze",
    ):
        claim = build_attempt_claim(head=head, execution_start_sha256=start_sha)
        publish_json_exclusive(ROOT / ATTEMPT_CLAIM, claim)
        result = execute_freeze(
            head=head,
            execution_start_sha256=start_sha,
            attempt_claim_sha256=sha256(ROOT / ATTEMPT_CLAIM),
        )
        publish_json_exclusive(ROOT / RESULT, result)
    print(
        json.dumps(
            {
                "result": str(RESULT),
                "decision": result["decision"],
                "failure_code": result["failure_code"],
                "catalog_attempts": result["effect_accounting"]["catalog_provider_attempt_count"],
                "target_attempts": result["effect_accounting"]["target_provider_attempt_count"],
                "successful_target_responses": result["target_transport"]["successful_response_count"],
                "selected_targets": result["population"]["selected_target_count"],
                "tasks": result["population"]["task_count"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
