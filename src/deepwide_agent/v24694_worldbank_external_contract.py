"""Visible-only frozen contract for V2.46.94 World Bank gate."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .v24686_worldbank_target_value_runtime import _visible_contract


DATE = "20260806"
PROTOCOL_ID = "v24694_worldbank_target_value_external_v1"
PROTOCOL = Path(f"results/v24694_worldbank_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v24694_worldbank_preactivation_audit_v1_{DATE}.json")
ACTIVATION = Path(f"results/v24694_worldbank_activation_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v24694_worldbank_execution_start_v1_{DATE}.json")
FORWARD_RESULT = Path(f"results/v24694_worldbank_forward_result_v1_{DATE}.json")
FORWARD_AUDIT = Path(f"results/v24694_worldbank_forward_audit_v1_{DATE}.json")
OUTPUT_ROOT = Path(f"outputs/v24694_worldbank_v1_{DATE}")
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
TASK_ROOT = OUTPUT_ROOT / "tasks"
PREDICTIONS = OUTPUT_ROOT / "frozen_predictions.jsonl"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
RUN_SUMMARY = OUTPUT_ROOT / "run_summary.json"
LEASE_PATH = Path("outputs/deepwide_benchmark_api.lease.lock")
LEASE_OWNER = PROTOCOL_ID
LEASE_PURPOSE = "benchmark_external_worldbank_target_value"
SELECTED_COUNT = 12
ARM_COUNT = 3
EXECUTOR_CONCURRENCY = 12
MODEL_SLOT_CAP = 8
PARENT_TIMEOUT_SECONDS = 255.0
PROTECTED_WATCHERS = (
    (795336, "scripts/watch_v2415_r1_checkpoint_liveness.py"),
    (3061652, "scripts/watch_v24218_exact220_executor.py"),
)
MODEL = {
    "proxy_url": "http://127.0.0.1:9878/responses",
    "name": "gpt-5.6-sol",
    "reasoning_effort": "low",
    "service_tier": "priority",
    "timeout_seconds": 65,
    "max_retries": 2,
}
SEARCH = {
    "proxy_url": "http://127.0.0.1:9878/responses",
    "model": "gpt-5.6-sol",
    "workers": 1,
    "batch_size": 8,
    "context_size": "medium",
    "max_output_tokens": 7_000,
    "timeout_seconds": 65,
    "max_retries": 2,
    "fetch_workers": 10,
    "fetch_timeout_seconds": 35,
    "hard_fetch_deadline_seconds": 40,
}
LIMITS = {
    "wall_seconds": 240,
    "model_calls": 3,
    "search_queries": 4,
    "fetch_targets": 10,
    "search_results_per_query": 3,
    "evidence_chars": 60_000,
    "page_chars": 5_000,
    "plan_output_tokens": 4_000,
    "synthesis_output_tokens": 30_000,
    "repair_output_tokens": 12_000,
}
TARGETS = ({'indicator': 'NY.GDP.PCAP.CD', 'label': 'GDP per capita (current US$)', 'year': '2023'},
 {'indicator': 'SP.URB.TOTL.IN.ZS', 'label': 'Urban population (%)', 'year': '2023'})
COUNTRY_GROUPS = ((('St. Vincent and the Grenadines', 'VCT'),
  ('Tajikistan', 'TJK'),
  ('Malaysia', 'MYS'),
  ('Israel', 'ISR')),
 (('Namibia', 'NAM'), ('Nepal', 'NPL'), ('Curacao', 'CUW'), ('Serbia', 'SRB')),
 (('Cambodia', 'KHM'), ('Libya', 'LBY'), ('Sao Tome and Principe', 'STP'), ('Sri Lanka', 'LKA')),
 (('Guatemala', 'GTM'), ('Kosovo', 'XKX'), ('Samoa', 'WSM'), ('Tunisia', 'TUN')),
 (('Seychelles', 'SYC'), ('Bangladesh', 'BGD'), ('Nicaragua', 'NIC'), ('Portugal', 'PRT')),
 (('Thailand', 'THA'), ('Oman', 'OMN'), ('Mozambique', 'MOZ'), ('St. Kitts and Nevis', 'KNA')),
 (('Netherlands', 'NLD'), ('Singapore', 'SGP'), ('Morocco', 'MAR'), ('Nigeria', 'NGA')),
 (('Colombia', 'COL'), ('Kyrgyz Republic', 'KGZ'), ('Solomon Islands', 'SLB'), ('Iraq', 'IRQ')),
 (('Uganda', 'UGA'), ('Peru', 'PER'), ('Greenland', 'GRL'), ('Viet Nam', 'VNM')),
 (('Algeria', 'DZA'),
  ('Central African Republic', 'CAF'),
  ('Venezuela, RB', 'VEN'),
  ('Greece', 'GRC')),
 (('Kiribati', 'KIR'), ('West Bank and Gaza', 'PSE'), ('Lesotho', 'LSO'), ('Grenada', 'GRD')),
 (('Azerbaijan', 'AZE'), ('Timor-Leste', 'TLS'), ('Kuwait', 'KWT'), ('Tanzania', 'TZA')))
QUESTIONS = ('Use public web sources to return one Markdown table about these countries:\n'
 '<COUNTRIES>\n'
 '1. St. Vincent and the Grenadines [VCT]\n'
 '2. Tajikistan [TJK]\n'
 '3. Malaysia [MYS]\n'
 '4. Israel [ISR]\n'
 '</COUNTRIES>\n'
 'Please output one Markdown table with the columns, in this exact order:\n'
 'Country | GDP per capita (current US$) [NY.GDP.PCAP.CD] @2023 | Urban population (%) '
 '[SP.URB.TOTL.IN.ZS] @2023\n'
 'Use the World Bank API values. Preserve the decimal representation returned by the official API. '
 'Use Unknown when unavailable. Return one table only.',
 'Use public web sources to return one Markdown table about these countries:\n'
 '<COUNTRIES>\n'
 '1. Namibia [NAM]\n'
 '2. Nepal [NPL]\n'
 '3. Curacao [CUW]\n'
 '4. Serbia [SRB]\n'
 '</COUNTRIES>\n'
 'Please output one Markdown table with the columns, in this exact order:\n'
 'Country | GDP per capita (current US$) [NY.GDP.PCAP.CD] @2023 | Urban population (%) '
 '[SP.URB.TOTL.IN.ZS] @2023\n'
 'Use the World Bank API values. Preserve the decimal representation returned by the official API. '
 'Use Unknown when unavailable. Return one table only.',
 'Use public web sources to return one Markdown table about these countries:\n'
 '<COUNTRIES>\n'
 '1. Cambodia [KHM]\n'
 '2. Libya [LBY]\n'
 '3. Sao Tome and Principe [STP]\n'
 '4. Sri Lanka [LKA]\n'
 '</COUNTRIES>\n'
 'Please output one Markdown table with the columns, in this exact order:\n'
 'Country | GDP per capita (current US$) [NY.GDP.PCAP.CD] @2023 | Urban population (%) '
 '[SP.URB.TOTL.IN.ZS] @2023\n'
 'Use the World Bank API values. Preserve the decimal representation returned by the official API. '
 'Use Unknown when unavailable. Return one table only.',
 'Use public web sources to return one Markdown table about these countries:\n'
 '<COUNTRIES>\n'
 '1. Guatemala [GTM]\n'
 '2. Kosovo [XKX]\n'
 '3. Samoa [WSM]\n'
 '4. Tunisia [TUN]\n'
 '</COUNTRIES>\n'
 'Please output one Markdown table with the columns, in this exact order:\n'
 'Country | GDP per capita (current US$) [NY.GDP.PCAP.CD] @2023 | Urban population (%) '
 '[SP.URB.TOTL.IN.ZS] @2023\n'
 'Use the World Bank API values. Preserve the decimal representation returned by the official API. '
 'Use Unknown when unavailable. Return one table only.',
 'Use public web sources to return one Markdown table about these countries:\n'
 '<COUNTRIES>\n'
 '1. Seychelles [SYC]\n'
 '2. Bangladesh [BGD]\n'
 '3. Nicaragua [NIC]\n'
 '4. Portugal [PRT]\n'
 '</COUNTRIES>\n'
 'Please output one Markdown table with the columns, in this exact order:\n'
 'Country | GDP per capita (current US$) [NY.GDP.PCAP.CD] @2023 | Urban population (%) '
 '[SP.URB.TOTL.IN.ZS] @2023\n'
 'Use the World Bank API values. Preserve the decimal representation returned by the official API. '
 'Use Unknown when unavailable. Return one table only.',
 'Use public web sources to return one Markdown table about these countries:\n'
 '<COUNTRIES>\n'
 '1. Thailand [THA]\n'
 '2. Oman [OMN]\n'
 '3. Mozambique [MOZ]\n'
 '4. St. Kitts and Nevis [KNA]\n'
 '</COUNTRIES>\n'
 'Please output one Markdown table with the columns, in this exact order:\n'
 'Country | GDP per capita (current US$) [NY.GDP.PCAP.CD] @2023 | Urban population (%) '
 '[SP.URB.TOTL.IN.ZS] @2023\n'
 'Use the World Bank API values. Preserve the decimal representation returned by the official API. '
 'Use Unknown when unavailable. Return one table only.',
 'Use public web sources to return one Markdown table about these countries:\n'
 '<COUNTRIES>\n'
 '1. Netherlands [NLD]\n'
 '2. Singapore [SGP]\n'
 '3. Morocco [MAR]\n'
 '4. Nigeria [NGA]\n'
 '</COUNTRIES>\n'
 'Please output one Markdown table with the columns, in this exact order:\n'
 'Country | GDP per capita (current US$) [NY.GDP.PCAP.CD] @2023 | Urban population (%) '
 '[SP.URB.TOTL.IN.ZS] @2023\n'
 'Use the World Bank API values. Preserve the decimal representation returned by the official API. '
 'Use Unknown when unavailable. Return one table only.',
 'Use public web sources to return one Markdown table about these countries:\n'
 '<COUNTRIES>\n'
 '1. Colombia [COL]\n'
 '2. Kyrgyz Republic [KGZ]\n'
 '3. Solomon Islands [SLB]\n'
 '4. Iraq [IRQ]\n'
 '</COUNTRIES>\n'
 'Please output one Markdown table with the columns, in this exact order:\n'
 'Country | GDP per capita (current US$) [NY.GDP.PCAP.CD] @2023 | Urban population (%) '
 '[SP.URB.TOTL.IN.ZS] @2023\n'
 'Use the World Bank API values. Preserve the decimal representation returned by the official API. '
 'Use Unknown when unavailable. Return one table only.',
 'Use public web sources to return one Markdown table about these countries:\n'
 '<COUNTRIES>\n'
 '1. Uganda [UGA]\n'
 '2. Peru [PER]\n'
 '3. Greenland [GRL]\n'
 '4. Viet Nam [VNM]\n'
 '</COUNTRIES>\n'
 'Please output one Markdown table with the columns, in this exact order:\n'
 'Country | GDP per capita (current US$) [NY.GDP.PCAP.CD] @2023 | Urban population (%) '
 '[SP.URB.TOTL.IN.ZS] @2023\n'
 'Use the World Bank API values. Preserve the decimal representation returned by the official API. '
 'Use Unknown when unavailable. Return one table only.',
 'Use public web sources to return one Markdown table about these countries:\n'
 '<COUNTRIES>\n'
 '1. Algeria [DZA]\n'
 '2. Central African Republic [CAF]\n'
 '3. Venezuela, RB [VEN]\n'
 '4. Greece [GRC]\n'
 '</COUNTRIES>\n'
 'Please output one Markdown table with the columns, in this exact order:\n'
 'Country | GDP per capita (current US$) [NY.GDP.PCAP.CD] @2023 | Urban population (%) '
 '[SP.URB.TOTL.IN.ZS] @2023\n'
 'Use the World Bank API values. Preserve the decimal representation returned by the official API. '
 'Use Unknown when unavailable. Return one table only.',
 'Use public web sources to return one Markdown table about these countries:\n'
 '<COUNTRIES>\n'
 '1. Kiribati [KIR]\n'
 '2. West Bank and Gaza [PSE]\n'
 '3. Lesotho [LSO]\n'
 '4. Grenada [GRD]\n'
 '</COUNTRIES>\n'
 'Please output one Markdown table with the columns, in this exact order:\n'
 'Country | GDP per capita (current US$) [NY.GDP.PCAP.CD] @2023 | Urban population (%) '
 '[SP.URB.TOTL.IN.ZS] @2023\n'
 'Use the World Bank API values. Preserve the decimal representation returned by the official API. '
 'Use Unknown when unavailable. Return one table only.',
 'Use public web sources to return one Markdown table about these countries:\n'
 '<COUNTRIES>\n'
 '1. Azerbaijan [AZE]\n'
 '2. Timor-Leste [TLS]\n'
 '3. Kuwait [KWT]\n'
 '4. Tanzania [TZA]\n'
 '</COUNTRIES>\n'
 'Please output one Markdown table with the columns, in this exact order:\n'
 'Country | GDP per capita (current US$) [NY.GDP.PCAP.CD] @2023 | Urban population (%) '
 '[SP.URB.TOTL.IN.ZS] @2023\n'
 'Use the World Bank API values. Preserve the decimal representation returned by the official API. '
 'Use Unknown when unavailable. Return one table only.')


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def protected_watcher_snapshot(proc_root: Path = Path("/proc")) -> list[dict[str, Any]]:
    output = []
    for pid, marker in PROTECTED_WATCHERS:
        stat = proc_root / str(pid) / "stat"
        cmdline = proc_root / str(pid) / "cmdline"
        if not stat.is_file() or not cmdline.is_file():
            raise RuntimeError("V2.46.94 protected watcher is absent")
        raw = stat.read_text(encoding="utf-8")
        suffix = raw[raw.rfind(")") + 2 :].split()
        command = cmdline.read_bytes().replace(b"\0", b" ").decode(errors="replace")
        if len(suffix) <= 19 or marker not in command:
            raise RuntimeError("V2.46.94 protected watcher identity drifted")
        output.append({"pid": pid, "marker": marker, "start_ticks": int(suffix[19])})
    return output


def visible_task(ordinal: int) -> dict[str, str]:
    if isinstance(ordinal, bool) or not isinstance(ordinal, int) or not 1 <= ordinal <= SELECTED_COUNT:
        raise ValueError("V2.46.94 task ordinal drifted")
    value = {
        "opaque_id": f"task_{0x246940 + ordinal:024x}",
        "question": QUESTIONS[ordinal - 1],
    }
    contract = _visible_contract(value["question"])
    expected = [{"name": name, "iso3": iso3} for name, iso3 in COUNTRY_GROUPS[ordinal - 1]]
    if contract["countries"] != expected:
        raise ValueError("V2.46.94 visible task round trip drifted")
    return value


def task_vector() -> list[dict[str, str]]:
    return [visible_task(index) for index in range(1, SELECTED_COUNT + 1)]


__all__ = [name for name in tuple(globals()) if name.isupper()] + [
    "payload_sha256", "protected_watcher_snapshot", "sha256", "task_vector", "visible_task"
]
