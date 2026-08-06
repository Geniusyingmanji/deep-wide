"""Visible-only contract for V2.46.71 information-gain acquisition."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .v24639_ror_objective_runtime import extract_visible_entities


DATE = "20260806"
PROTOCOL_ID = "v24671_visible_surface_information_gain_ror_external_v1"
PROTOCOL = Path(f"results/v24671_information_gain_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v24671_information_gain_preactivation_audit_v1_{DATE}.json")
ACTIVATION = Path(f"results/v24671_information_gain_activation_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v24671_information_gain_execution_start_v1_{DATE}.json")
FORWARD_RESULT = Path(f"results/v24671_information_gain_forward_result_v1_{DATE}.json")
FORWARD_AUDIT = Path(f"results/v24671_information_gain_forward_audit_v1_{DATE}.json")
OUTPUT_ROOT = Path(f"outputs/v24671_information_gain_v1_{DATE}")
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
TASK_ROOT = OUTPUT_ROOT / "tasks"
PREDICTIONS = OUTPUT_ROOT / "frozen_predictions.jsonl"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
RUN_SUMMARY = OUTPUT_ROOT / "run_summary.json"
LEASE_PATH = Path("outputs/deepwide_benchmark_api.lease.lock")
LEASE_OWNER = PROTOCOL_ID
LEASE_PURPOSE = "fresh_external_visible_surface_information_gain_ror"
SELECTED_COUNT = 12
ARM_COUNT = 2
EXECUTOR_CONCURRENCY = 12
MODEL_SLOT_CAP = 8
MODEL_SLOT_POOL_ID = "v24263_score_first_global_model_slots_v1"
TASK_WALL_SECONDS = 180
PARENT_TIMEOUT_SECONDS = 200
CLEANUP_RESERVE_SECONDS = 5.0
MINIMUM_ATTEMPT_SECONDS = 0.05
PROTECTED_WATCHERS = (
    (795336, "scripts/watch_v2415_r1_checkpoint_liveness.py"),
    (3061652, "scripts/watch_v24218_exact220_executor.py"),
)
MODEL = {
    "proxy_url": "http://127.0.0.1:9878/responses",
    "name": "gpt-5.6-sol",
    "reasoning_effort": "low",
    "service_tier": "priority",
    "timeout_seconds": 180,
    "max_retries": 2,
}
SEARCH = {
    "proxy_url": "http://127.0.0.1:9878/responses",
    "model": "gpt-5.6-sol",
    "workers": 1,
    "batch_size": 8,
    "context_size": "medium",
    "max_output_tokens": 7_000,
    "timeout_seconds": 180,
    "max_retries": 2,
    "fetch_workers": 8,
    "fetch_timeout_seconds": 20,
    "hard_fetch_deadline_seconds": 25,
}
LIMITS = {
    "wall_seconds": 180,
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
    "generic_query_cap": 2,
    "generic_fetch_cap": 6,
    "unknown_target_cell_cap": 1,
    "targeted_query_cap": 1,
    "targeted_fetch_cap": 4,
    "targeted_fetch_capacity_concentrated_on_one_target": True,
    "visible_title_and_normalized_url_path_information_gain_priority": True,
    "query_text_cannot_self_prove_surface_alignment": True,
    "fetched_page_text_is_only_active_support": True,
    "minimum_independent_local_exact_support_sources": 2,
    "strict_support_closure_preserves_all_declared_evidence_ids": True,
    "proposal_value_changed": False,
    "support_threshold_relaxed": False,
    "epistemic_action_credit_may_be_positive": True,
    "decision_credit_before_safe_change_and_postfreeze_outer_utility": False,
}

ENTITY_GROUPS = (('Sekolah Tinggi Ilmu Kesehatan Gunung Sari',
  'Institut de Génomique Fonctionnelle de Lyon',
  'Asia Pacific Network Information Centre',
  'Instytut Antropologii Seksualnej'),
 ('Sekolah Tinggi Ilmu Administrasi Pembangunan Palu',
  'Rheinland-Pfälzische Technische Universität Kaiserslautern-Landau',
  'Easterseals Southern California',
  'Universidad de Salamanca'),
 ('Universitas Mayasari Bakti',
  'Choosing Wisely Canada',
  'Gonoshasthaya Kendra',
  'Phenomics Australia'),
 ('Sekolah Tinggi Teologi dan Entrepreneurship Pringgading',
  'NOAA National Weather Service',
  'Centro de Investigación Mente, Cerebro y Comportamiento',
  'LEAPS'),
 ('Unité Mixte de Recherche Epidémiologique et de Surveillance Transport Travail Environnement',
  'Center for Integrated Nanotechnologies',
  'Amiri Medical Complex',
  'Harbin Electric Power Generation Equipment National Engineering Research Center'),
 ('Gobardanga Hindu College',
  'Medizinische Universität Lausitz - Carl Thiem',
  'Harbin Sport University',
  "St Michael's Hospital"),
 ('Kanyashree University',
  'Bundesverband für Wohnen und Stadtentwicklung e.V.',
  'Instituto Superior Cristal',
  'Federacja Naukowa WSB-DSW Merito'),
 ('Technische Sammlungen Dresden',
  'KidsAbility',
  'Directorate of Agricultural Research',
  'Mindanao State University - Maigo College of Education, Science and Technology'),
 ('Anthropologie Bio-Culturelle, Droit, Éthique & Santé',
  'University of Colorado Anschutz Medical Campus',
  'Scuola Superiore Meridionale',
  'Guangzhou University of Chinese Medicine'),
 ('SMBT College of Pharmacy',
  'Managing African Research Network',
  'Research Institute of Geodesy and Cartography',
  'Universidad FUCS'),
 ('Aska Science College',
  'Canadian Mental Health Association',
  'Global Academic Research Institute',
  'British Academy'),
 ("Laboratoire de Mécanique des Fluides et d'Acoustique",
  'Canadian Mental Health Association Thames Valley Addiction and Mental Health Services',
  'Republic Central Colleges',
  'Fundación Centro Interdisciplinario en Ética, Política y Economía'))
QUESTIONS = ('Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Sekolah Tinggi Ilmu Kesehatan Gunung Sari\n'
 '2. Institut de Génomique Fonctionnelle de Lyon\n'
 '3. Asia Pacific Network Information Centre\n'
 '4. Instytut Antropologii Seksualnej\n'
 '</ENTITIES>\n'
 'The column names are: Organization, ROR ID, Country code. Use the 9-character ROR ID suffix, not '
 'the full URL, and the ISO 3166-1 alpha-2 country code. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Sekolah Tinggi Ilmu Administrasi Pembangunan Palu\n'
 '2. Rheinland-Pfälzische Technische Universität Kaiserslautern-Landau\n'
 '3. Easterseals Southern California\n'
 '4. Universidad de Salamanca\n'
 '</ENTITIES>\n'
 'The column names are: Organization, ROR ID, Country code. Use the 9-character ROR ID suffix, not '
 'the full URL, and the ISO 3166-1 alpha-2 country code. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Universitas Mayasari Bakti\n'
 '2. Choosing Wisely Canada\n'
 '3. Gonoshasthaya Kendra\n'
 '4. Phenomics Australia\n'
 '</ENTITIES>\n'
 'The column names are: Organization, ROR ID, Country code. Use the 9-character ROR ID suffix, not '
 'the full URL, and the ISO 3166-1 alpha-2 country code. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Sekolah Tinggi Teologi dan Entrepreneurship Pringgading\n'
 '2. NOAA National Weather Service\n'
 '3. Centro de Investigación Mente, Cerebro y Comportamiento\n'
 '4. LEAPS\n'
 '</ENTITIES>\n'
 'The column names are: Organization, ROR ID, Country code. Use the 9-character ROR ID suffix, not '
 'the full URL, and the ISO 3166-1 alpha-2 country code. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Unité Mixte de Recherche Epidémiologique et de Surveillance Transport Travail Environnement\n'
 '2. Center for Integrated Nanotechnologies\n'
 '3. Amiri Medical Complex\n'
 '4. Harbin Electric Power Generation Equipment National Engineering Research Center\n'
 '</ENTITIES>\n'
 'The column names are: Organization, ROR ID, Country code. Use the 9-character ROR ID suffix, not '
 'the full URL, and the ISO 3166-1 alpha-2 country code. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Gobardanga Hindu College\n'
 '2. Medizinische Universität Lausitz - Carl Thiem\n'
 '3. Harbin Sport University\n'
 "4. St Michael's Hospital\n"
 '</ENTITIES>\n'
 'The column names are: Organization, ROR ID, Country code. Use the 9-character ROR ID suffix, not '
 'the full URL, and the ISO 3166-1 alpha-2 country code. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Kanyashree University\n'
 '2. Bundesverband für Wohnen und Stadtentwicklung e.V.\n'
 '3. Instituto Superior Cristal\n'
 '4. Federacja Naukowa WSB-DSW Merito\n'
 '</ENTITIES>\n'
 'The column names are: Organization, ROR ID, Country code. Use the 9-character ROR ID suffix, not '
 'the full URL, and the ISO 3166-1 alpha-2 country code. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Technische Sammlungen Dresden\n'
 '2. KidsAbility\n'
 '3. Directorate of Agricultural Research\n'
 '4. Mindanao State University - Maigo College of Education, Science and Technology\n'
 '</ENTITIES>\n'
 'The column names are: Organization, ROR ID, Country code. Use the 9-character ROR ID suffix, not '
 'the full URL, and the ISO 3166-1 alpha-2 country code. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Anthropologie Bio-Culturelle, Droit, Éthique & Santé\n'
 '2. University of Colorado Anschutz Medical Campus\n'
 '3. Scuola Superiore Meridionale\n'
 '4. Guangzhou University of Chinese Medicine\n'
 '</ENTITIES>\n'
 'The column names are: Organization, ROR ID, Country code. Use the 9-character ROR ID suffix, not '
 'the full URL, and the ISO 3166-1 alpha-2 country code. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. SMBT College of Pharmacy\n'
 '2. Managing African Research Network\n'
 '3. Research Institute of Geodesy and Cartography\n'
 '4. Universidad FUCS\n'
 '</ENTITIES>\n'
 'The column names are: Organization, ROR ID, Country code. Use the 9-character ROR ID suffix, not '
 'the full URL, and the ISO 3166-1 alpha-2 country code. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Aska Science College\n'
 '2. Canadian Mental Health Association\n'
 '3. Global Academic Research Institute\n'
 '4. British Academy\n'
 '</ENTITIES>\n'
 'The column names are: Organization, ROR ID, Country code. Use the 9-character ROR ID suffix, not '
 'the full URL, and the ISO 3166-1 alpha-2 country code. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 "1. Laboratoire de Mécanique des Fluides et d'Acoustique\n"
 '2. Canadian Mental Health Association Thames Valley Addiction and Mental Health Services\n'
 '3. Republic Central Colleges\n'
 '4. Fundación Centro Interdisciplinario en Ética, Política y Economía\n'
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


def protected_watcher_snapshot(proc_root: Path = Path("/proc")) -> list[dict[str, object]]:
    output = []
    for pid, marker in PROTECTED_WATCHERS:
        stat = proc_root / str(pid) / "stat"
        cmdline = proc_root / str(pid) / "cmdline"
        if not stat.is_file() or not cmdline.is_file():
            raise RuntimeError("V2.46.71 protected watcher is absent")
        raw = stat.read_text(encoding="utf-8")
        suffix = raw[raw.rfind(")") + 2 :].split()
        command = cmdline.read_bytes().replace(b"\0", b" ").decode(errors="replace")
        if len(suffix) <= 19 or marker not in command:
            raise RuntimeError("V2.46.71 protected watcher identity drifted")
        output.append({"pid": pid, "marker": marker, "start_ticks": int(suffix[19])})
    return output


def visible_task(ordinal: int) -> dict[str, str]:
    if isinstance(ordinal, bool) or not isinstance(ordinal, int) or not 1 <= ordinal <= SELECTED_COUNT:
        raise ValueError("V2.46.71 task ordinal drifted")
    value = {
        "opaque_id": f"task_{0x246710 + ordinal:024x}",
        "question": QUESTIONS[ordinal - 1],
    }
    if extract_visible_entities(value["question"]) != list(ENTITY_GROUPS[ordinal - 1]):
        raise ValueError("V2.46.71 visible task round trip drifted")
    return value


def task_vector() -> list[dict[str, str]]:
    return [visible_task(index) for index in range(1, SELECTED_COUNT + 1)]


__all__ = [name for name in tuple(globals()) if name.isupper()] + [
    "payload_sha256", "protected_watcher_snapshot", "sha256", "task_vector", "visible_task",
]
