"""Visible-only frozen contract for the V2.46.51 unknown-target gate."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .v24639_ror_objective_runtime import extract_visible_entities


DATE = "20260806"
PROTOCOL_ID = "v24651_unknown_target_official_structured_ror_external_v1"
PROTOCOL = Path(f"results/v24651_unknown_target_structured_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v24651_unknown_target_structured_preactivation_audit_v1_{DATE}.json")
ACTIVATION = Path(f"results/v24651_unknown_target_structured_activation_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v24651_unknown_target_structured_execution_start_v1_{DATE}.json")
FORWARD_RESULT = Path(f"results/v24651_unknown_target_structured_forward_result_v1_{DATE}.json")
FORWARD_AUDIT = Path(f"results/v24651_unknown_target_structured_forward_audit_v1_{DATE}.json")
OUTPUT_ROOT = Path(f"outputs/v24651_unknown_target_structured_v1_{DATE}")
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
TASK_ROOT = OUTPUT_ROOT / "tasks"
PREDICTIONS = OUTPUT_ROOT / "frozen_predictions.jsonl"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
RUN_SUMMARY = OUTPUT_ROOT / "run_summary.json"
LEASE_PATH = Path("outputs/deepwide_benchmark_api.lease.lock")
LEASE_OWNER = PROTOCOL_ID
LEASE_PURPOSE = "benchmark_external_unknown_target_official_structured_ror"
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
TREATMENT = {
    "generic_fetch_cap": 6,
    "unknown_target_lookup_cap": 4,
    "candidate_uses_only_new_lookup_projection": True,
    "official_query_mode": "ror_v2_advanced_exact_name_active",
}

ENTITY_GROUPS = (('Universitas Mahakarya Asia',
  'FACT Research Center',
  'Guru Jambheshwar University Moradabad',
  'Rwanda Standards Board'),
 ('Universitas Islam Negeri Sultanah Nahrasiyah Lhokseumawe',
  'Fédération de Recherche PhotoVoltaïque',
  'JCHO Sapporo Hokushin Hospital',
  'Voice of Doctors Research School'),
 ('Universitas Uluwiyah Mojokerto',
  'Algoma Public Health',
  'More Institute',
  'Paul Langerhans Institute Dresden'),
 ('Universitas Yuppentek Indonesia',
  'P.G. Centre for Management Studies',
  'Hospital Universitario Infantil San José',
  'City College of Tagaytay'),
 ('CaixaResearch Institute',
  'McGill University Research Centre for Studies in Aging',
  'International Association for Cryptologic Research',
  'Vyatka State Agrotechnological University'),
 ('Centre de Recherche en CardioVasculaire et Nutrition',
  'Martin Luther University Halle-Wittenberg',
  'Instituto Tecnológico Superior de El Mante',
  'Shandong University of Aeronautics'),
 ('Vulture Conservation Foundation',
  'Upper Canada College',
  'Rural Cancer Institute',
  'Transylvanian Institute of Neuroscience'),
 ('Bristol NHS Foundation Trust',
  'Dum Dum Motijheel College',
  'Occidental Mindoro State University',
  'Center for the Analysis of Politics and Enterprise'),
 ('Interoceanmetal Joint Organization',
  'Fédération Informatique de Lyon',
  'Consejo de Ciencia y Tecnología del Estado de Morelos',
  'Baylor Scott & White Health'),
 ('Centre International de Recherche en Infectiologie',
  'HQ Toronto',
  'Kazakh Technology and Business University named after K.Kulazhanov',
  'Institute of Functional Epigenetics'),
 ('Mental Health Hospital',
  'Southmead Hospital',
  'King Abdulaziz Hospital',
  'Centro de Enseñanza Superior Alberta Giménez'),
 ('Universidad de Sotavento',
  'Debraj Roy College',
  'Ministerio Público de Honduras',
  'DSW Ideis University'))
QUESTIONS = ('Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Universitas Mahakarya Asia\n'
 '2. FACT Research Center\n'
 '3. Guru Jambheshwar University Moradabad\n'
 '4. Rwanda Standards Board\n'
 '</ENTITIES>\n'
 'The column names are: Organization, ROR ID, Country code. Use the 9-character ROR ID suffix, not '
 'the full URL, and the ISO 3166-1 alpha-2 country code. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Universitas Islam Negeri Sultanah Nahrasiyah Lhokseumawe\n'
 '2. Fédération de Recherche PhotoVoltaïque\n'
 '3. JCHO Sapporo Hokushin Hospital\n'
 '4. Voice of Doctors Research School\n'
 '</ENTITIES>\n'
 'The column names are: Organization, ROR ID, Country code. Use the 9-character ROR ID suffix, not '
 'the full URL, and the ISO 3166-1 alpha-2 country code. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Universitas Uluwiyah Mojokerto\n'
 '2. Algoma Public Health\n'
 '3. More Institute\n'
 '4. Paul Langerhans Institute Dresden\n'
 '</ENTITIES>\n'
 'The column names are: Organization, ROR ID, Country code. Use the 9-character ROR ID suffix, not '
 'the full URL, and the ISO 3166-1 alpha-2 country code. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Universitas Yuppentek Indonesia\n'
 '2. P.G. Centre for Management Studies\n'
 '3. Hospital Universitario Infantil San José\n'
 '4. City College of Tagaytay\n'
 '</ENTITIES>\n'
 'The column names are: Organization, ROR ID, Country code. Use the 9-character ROR ID suffix, not '
 'the full URL, and the ISO 3166-1 alpha-2 country code. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. CaixaResearch Institute\n'
 '2. McGill University Research Centre for Studies in Aging\n'
 '3. International Association for Cryptologic Research\n'
 '4. Vyatka State Agrotechnological University\n'
 '</ENTITIES>\n'
 'The column names are: Organization, ROR ID, Country code. Use the 9-character ROR ID suffix, not '
 'the full URL, and the ISO 3166-1 alpha-2 country code. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Centre de Recherche en CardioVasculaire et Nutrition\n'
 '2. Martin Luther University Halle-Wittenberg\n'
 '3. Instituto Tecnológico Superior de El Mante\n'
 '4. Shandong University of Aeronautics\n'
 '</ENTITIES>\n'
 'The column names are: Organization, ROR ID, Country code. Use the 9-character ROR ID suffix, not '
 'the full URL, and the ISO 3166-1 alpha-2 country code. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Vulture Conservation Foundation\n'
 '2. Upper Canada College\n'
 '3. Rural Cancer Institute\n'
 '4. Transylvanian Institute of Neuroscience\n'
 '</ENTITIES>\n'
 'The column names are: Organization, ROR ID, Country code. Use the 9-character ROR ID suffix, not '
 'the full URL, and the ISO 3166-1 alpha-2 country code. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Bristol NHS Foundation Trust\n'
 '2. Dum Dum Motijheel College\n'
 '3. Occidental Mindoro State University\n'
 '4. Center for the Analysis of Politics and Enterprise\n'
 '</ENTITIES>\n'
 'The column names are: Organization, ROR ID, Country code. Use the 9-character ROR ID suffix, not '
 'the full URL, and the ISO 3166-1 alpha-2 country code. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Interoceanmetal Joint Organization\n'
 '2. Fédération Informatique de Lyon\n'
 '3. Consejo de Ciencia y Tecnología del Estado de Morelos\n'
 '4. Baylor Scott & White Health\n'
 '</ENTITIES>\n'
 'The column names are: Organization, ROR ID, Country code. Use the 9-character ROR ID suffix, not '
 'the full URL, and the ISO 3166-1 alpha-2 country code. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Centre International de Recherche en Infectiologie\n'
 '2. HQ Toronto\n'
 '3. Kazakh Technology and Business University named after K.Kulazhanov\n'
 '4. Institute of Functional Epigenetics\n'
 '</ENTITIES>\n'
 'The column names are: Organization, ROR ID, Country code. Use the 9-character ROR ID suffix, not '
 'the full URL, and the ISO 3166-1 alpha-2 country code. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Mental Health Hospital\n'
 '2. Southmead Hospital\n'
 '3. King Abdulaziz Hospital\n'
 '4. Centro de Enseñanza Superior Alberta Giménez\n'
 '</ENTITIES>\n'
 'The column names are: Organization, ROR ID, Country code. Use the 9-character ROR ID suffix, not '
 'the full URL, and the ISO 3166-1 alpha-2 country code. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Universidad de Sotavento\n'
 '2. Debraj Roy College\n'
 '3. Ministerio Público de Honduras\n'
 '4. DSW Ideis University\n'
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
            raise RuntimeError("V2.46.51 protected watcher is absent")
        raw = stat.read_text(encoding="utf-8")
        suffix = raw[raw.rfind(")") + 2 :].split()
        command = cmdline.read_bytes().replace(b"\0", b" ").decode(errors="replace")
        if len(suffix) <= 19 or marker not in command:
            raise RuntimeError("V2.46.51 protected watcher identity drifted")
        output.append({"pid": pid, "marker": marker, "start_ticks": int(suffix[19])})
    return output


def visible_task(ordinal: int) -> dict[str, str]:
    if (
        isinstance(ordinal, bool)
        or not isinstance(ordinal, int)
        or not 1 <= ordinal <= SELECTED_COUNT
    ):
        raise ValueError("V2.46.51 task ordinal drifted")
    value = {
        "opaque_id": f"task_{0x246510 + ordinal:024x}",
        "question": QUESTIONS[ordinal - 1],
    }
    if extract_visible_entities(value["question"]) != list(ENTITY_GROUPS[ordinal - 1]):
        raise ValueError("V2.46.51 visible task round trip drifted")
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
