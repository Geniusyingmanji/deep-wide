"""Visible-only frozen contract for the V2.46.45 primary-identity gate."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .v24639_ror_objective_runtime import extract_visible_entities


DATE = "20260806"
PROTOCOL_ID = "v24645_primary_identity_bound_ror_pair_external_v1"
PROTOCOL = Path(f"results/v24645_primary_identity_pair_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v24645_primary_identity_pair_preactivation_audit_v1_{DATE}.json")
ACTIVATION = Path(f"results/v24645_primary_identity_pair_activation_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v24645_primary_identity_pair_execution_start_v1_{DATE}.json")
FORWARD_RESULT = Path(f"results/v24645_primary_identity_pair_forward_result_v1_{DATE}.json")
FORWARD_AUDIT = Path(f"results/v24645_primary_identity_pair_forward_audit_v1_{DATE}.json")
OUTPUT_ROOT = Path(f"outputs/v24645_primary_identity_pair_v1_{DATE}")
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
TASK_ROOT = OUTPUT_ROOT / "tasks"
PREDICTIONS = OUTPUT_ROOT / "frozen_predictions.jsonl"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
RUN_SUMMARY = OUTPUT_ROOT / "run_summary.json"
LEASE_PATH = Path("outputs/deepwide_benchmark_api.lease.lock")
LEASE_OWNER = PROTOCOL_ID
LEASE_PURPOSE = "benchmark_external_primary_identity_bound_ror_pair"
SELECTED_COUNT = 12
ARM_COUNT = 2
EXECUTOR_CONCURRENCY = 12
MODEL_SLOT_CAP = 8
PARENT_TIMEOUT_SECONDS = 255.0
CLEANUP_RESERVE_SECONDS = 5.0
MINIMUM_MODEL_ATTEMPT_SECONDS = 0.05
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
    "fetch_workers": 8,
    "fetch_timeout_seconds": 20,
    "hard_fetch_deadline_seconds": 25,
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

ENTITY_GROUPS = (('Politeknik LP3I Medan',
  'Hôpital de Jonquière',
  'Yokosuka Council on Asia Pacific Studies',
  'Universidad de Granada'),
 ('Institut Al Fithrah Surabaya',
  'Helmholtz Alliance Imaging and Curing Environmental Metabolic Diseases',
  'Østfold University of Applied Sciences',
  'Onaizah Colleges'),
 ('Akademie für Altersforschung am Haus der Barmherzigkeit',
  'Haldia Government College',
  'East Jeddah Hospital',
  'Statewide California Earthquake Center'),
 ('Institut des Sciences Analytiques',
  'Polymer Processing Institute',
  'Visoka škola "Logos centar" Mostaru',
  'National Cereals Research Institute'),
 ('Politeknik Astra',
  'Cossham Hospital',
  'Contraception & Abortion Research Team – Groupe de recherche sur l’avortement et la '
  'contraception',
  'Baoshan University'),
 ('Laboratoire Reproduction et Développement des Plantes',
  'University of Kalyani',
  'International Center for Monetary and Banking Studies',
  'Corporación Centro de Desarrollo Tecnológico del Gas'),
 ('Warith International Cancer Institute',
  'Black Health Alliance',
  'American Society for Emergency Contraception',
  'Universidade do Porto'),
 ("Equipe de recherche de Lyon en Sciences de l'Information et de la Communication",
  'Chitralada Technology Institute',
  'Université de Saida Dr Moulay Tahar',
  'Frenchay Hospital'),
 ('Rapti Academy of Health Sciences, Dang, Nepal',
  'Fundación Saimiri de Costa Rica',
  'Huzhou Normal University',
  'Leipzig University'),
 ('Government of South Australia',
  'German Reproducibility Network',
  'Trường Đại học Nghệ An',
  'Jeddah First Health Cluster'),
 ('Université Privée de Marrakech',
  "Ad-din Women's Medical College",
  'State Institution "V. Danilevsky Institute for Endocrine Pathology Problems of NAMS of Ukraine"',
  'Süleyman Demirel Üniversitesi'),
 ('Bharathiar University',
  'CEF.- Santo Domingo',
  'Holo Global Health Research Institute',
  'Surigao del Norte State University'))
QUESTIONS = ('Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Politeknik LP3I Medan\n'
 '2. Hôpital de Jonquière\n'
 '3. Yokosuka Council on Asia Pacific Studies\n'
 '4. Universidad de Granada\n'
 '</ENTITIES>\n'
 'The column names are: Organization, ROR ID, Country code. Use the 9-character ROR ID suffix, not '
 'the full URL, and the ISO 3166-1 alpha-2 country code. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Institut Al Fithrah Surabaya\n'
 '2. Helmholtz Alliance Imaging and Curing Environmental Metabolic Diseases\n'
 '3. Østfold University of Applied Sciences\n'
 '4. Onaizah Colleges\n'
 '</ENTITIES>\n'
 'The column names are: Organization, ROR ID, Country code. Use the 9-character ROR ID suffix, not '
 'the full URL, and the ISO 3166-1 alpha-2 country code. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Akademie für Altersforschung am Haus der Barmherzigkeit\n'
 '2. Haldia Government College\n'
 '3. East Jeddah Hospital\n'
 '4. Statewide California Earthquake Center\n'
 '</ENTITIES>\n'
 'The column names are: Organization, ROR ID, Country code. Use the 9-character ROR ID suffix, not '
 'the full URL, and the ISO 3166-1 alpha-2 country code. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Institut des Sciences Analytiques\n'
 '2. Polymer Processing Institute\n'
 '3. Visoka škola "Logos centar" Mostaru\n'
 '4. National Cereals Research Institute\n'
 '</ENTITIES>\n'
 'The column names are: Organization, ROR ID, Country code. Use the 9-character ROR ID suffix, not '
 'the full URL, and the ISO 3166-1 alpha-2 country code. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Politeknik Astra\n'
 '2. Cossham Hospital\n'
 '3. Contraception & Abortion Research Team – Groupe de recherche sur l’avortement et la '
 'contraception\n'
 '4. Baoshan University\n'
 '</ENTITIES>\n'
 'The column names are: Organization, ROR ID, Country code. Use the 9-character ROR ID suffix, not '
 'the full URL, and the ISO 3166-1 alpha-2 country code. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Laboratoire Reproduction et Développement des Plantes\n'
 '2. University of Kalyani\n'
 '3. International Center for Monetary and Banking Studies\n'
 '4. Corporación Centro de Desarrollo Tecnológico del Gas\n'
 '</ENTITIES>\n'
 'The column names are: Organization, ROR ID, Country code. Use the 9-character ROR ID suffix, not '
 'the full URL, and the ISO 3166-1 alpha-2 country code. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Warith International Cancer Institute\n'
 '2. Black Health Alliance\n'
 '3. American Society for Emergency Contraception\n'
 '4. Universidade do Porto\n'
 '</ENTITIES>\n'
 'The column names are: Organization, ROR ID, Country code. Use the 9-character ROR ID suffix, not '
 'the full URL, and the ISO 3166-1 alpha-2 country code. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 "1. Equipe de recherche de Lyon en Sciences de l'Information et de la Communication\n"
 '2. Chitralada Technology Institute\n'
 '3. Université de Saida Dr Moulay Tahar\n'
 '4. Frenchay Hospital\n'
 '</ENTITIES>\n'
 'The column names are: Organization, ROR ID, Country code. Use the 9-character ROR ID suffix, not '
 'the full URL, and the ISO 3166-1 alpha-2 country code. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Rapti Academy of Health Sciences, Dang, Nepal\n'
 '2. Fundación Saimiri de Costa Rica\n'
 '3. Huzhou Normal University\n'
 '4. Leipzig University\n'
 '</ENTITIES>\n'
 'The column names are: Organization, ROR ID, Country code. Use the 9-character ROR ID suffix, not '
 'the full URL, and the ISO 3166-1 alpha-2 country code. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Government of South Australia\n'
 '2. German Reproducibility Network\n'
 '3. Trường Đại học Nghệ An\n'
 '4. Jeddah First Health Cluster\n'
 '</ENTITIES>\n'
 'The column names are: Organization, ROR ID, Country code. Use the 9-character ROR ID suffix, not '
 'the full URL, and the ISO 3166-1 alpha-2 country code. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Université Privée de Marrakech\n'
 "2. Ad-din Women's Medical College\n"
 '3. State Institution "V. Danilevsky Institute for Endocrine Pathology Problems of NAMS of '
 'Ukraine"\n'
 '4. Süleyman Demirel Üniversitesi\n'
 '</ENTITIES>\n'
 'The column names are: Organization, ROR ID, Country code. Use the 9-character ROR ID suffix, not '
 'the full URL, and the ISO 3166-1 alpha-2 country code. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Bharathiar University\n'
 '2. CEF.- Santo Domingo\n'
 '3. Holo Global Health Research Institute\n'
 '4. Surigao del Norte State University\n'
 '</ENTITIES>\n'
 'The column names are: Organization, ROR ID, Country code. Use the 9-character ROR ID suffix, not '
 'the full URL, and the ISO 3166-1 alpha-2 country code. Return one table only.')


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
            raise RuntimeError("V2.46.45 protected watcher is absent")
        raw = stat.read_text(encoding="utf-8")
        suffix = raw[raw.rfind(")") + 2 :].split()
        command = cmdline.read_bytes().replace(b"\0", b" ").decode(errors="replace")
        if len(suffix) <= 19 or marker not in command:
            raise RuntimeError("V2.46.45 protected watcher identity drifted")
        output.append({"pid": pid, "marker": marker, "start_ticks": int(suffix[19])})
    return output


def visible_task(ordinal: int) -> dict[str, str]:
    if (
        isinstance(ordinal, bool)
        or not isinstance(ordinal, int)
        or not 1 <= ordinal <= SELECTED_COUNT
    ):
        raise ValueError("V2.46.45 task ordinal drifted")
    value = {
        "opaque_id": f"task_{0x246450 + ordinal:024x}",
        "question": QUESTIONS[ordinal - 1],
    }
    if extract_visible_entities(value["question"]) != list(ENTITY_GROUPS[ordinal - 1]):
        raise ValueError("V2.46.45 visible task round trip drifted")
    return value


def task_vector() -> list[dict[str, str]]:
    return [visible_task(index) for index in range(1, SELECTED_COUNT + 1)]


__all__ = [name for name in tuple(globals()) if name.isupper()] + [
    "payload_sha256",
    "protected_watcher_snapshot",
    "sha256",
    "task_vector",
    "visible_task",
]
