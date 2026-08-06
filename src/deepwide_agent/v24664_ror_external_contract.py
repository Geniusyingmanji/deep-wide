"""Visible-only contract for V2.46.64 strict support closure."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .v24639_ror_objective_runtime import extract_visible_entities


DATE = "20260806"
PROTOCOL_ID = "v24664_strict_support_closure_ror_external_v1"
PROTOCOL = Path(f"results/v24664_strict_support_closure_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v24664_strict_support_closure_preactivation_audit_v1_{DATE}.json")
ACTIVATION = Path(f"results/v24664_strict_support_closure_activation_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v24664_strict_support_closure_execution_start_v1_{DATE}.json")
FORWARD_RESULT = Path(f"results/v24664_strict_support_closure_forward_result_v1_{DATE}.json")
FORWARD_AUDIT = Path(f"results/v24664_strict_support_closure_forward_audit_v1_{DATE}.json")
OUTPUT_ROOT = Path(f"outputs/v24664_strict_support_closure_v1_{DATE}")
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
TASK_ROOT = OUTPUT_ROOT / "tasks"
PREDICTIONS = OUTPUT_ROOT / "frozen_predictions.jsonl"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
RUN_SUMMARY = OUTPUT_ROOT / "run_summary.json"
LEASE_PATH = Path("outputs/deepwide_benchmark_api.lease.lock")
LEASE_OWNER = PROTOCOL_ID
LEASE_PURPOSE = "fresh_external_strict_support_closure_ror"
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
    "unknown_target_cell_cap": 2,
    "targeted_query_cap": 2,
    "targeted_fetch_cap": 4,
    "minimum_independent_local_exact_support_sources": 2,
    "strict_support_closure_preserves_all_declared_evidence_ids": True,
    "uses_only_same_pass_already_fetched_pages": True,
    "entropy_or_task_credit_used": False,
}

ENTITY_GROUPS = (('Sekolah Tinggi Ilmu Tarbiyah Miftahul Ulum Bangkalan',
  'Mrs. Kesharbai Sonajirao Kshirsagar Alias Kaku Arts, Science & Commerce College, Beed',
  'Helmholtz Center for Information Security',
  'Shenzhen International Quantum Academy'),
 ('Akademie für Tierschutz des Deutschen Tierschutzbundes e.V.',
  'ARTHritEs, Microchimérisme et InflammationS',
  'Kurdistan Higher Council of Medical Specialties',
  'SA Genome Editing Facility'),
 ('Akademi Kebidanan Tahirah Al Baeti Bulukumba',
  'Boyle Street Community Services',
  'Wuhan Surveying-Geotechnical Research Institute',
  'Grandview Kids'),
 ('Universitas Asa Indonesia',
  'Jefferson Einstein Philadelphia Hospital',
  'Universidad del País Innova',
  'National Academy of Medical Sciences of Ukraine'),
 ('Akademi Pelayaran Nasional Surakarta',
  'Matériaux Ingénierie et Science',
  'Clevedon Hospital',
  'Weston General Hospital'),
 ('St. Vincent Pallotti College of Engineering & Technology',
  'Vidyasagar Metropolitan College',
  "Waasegiizhig Nanaandawe'iyewigamig",
  'Instituto Tecnológico Superior de Villa la Venta'),
 ('Mindanao State University',
  'Centre for European Economic Research',
  'Engineering Science Lyon Tohoku, Materials under eXtreme conditions',
  'Geneva College of Longevity Science'),
 ('Saraswathi Institute of Medical Sciences',
  'Lyon 1 Université',
  'Institut zur Erforschung von Mission und Kirche',
  'Visoka škola za turizam i menadžment Konjic'),
 ('Center for Economic and Policy Research',
  'Institut des Sciences Cognitives Marc Jeannerod',
  'Arrhenius Research Institute',
  'Nakhchivan Teachers Institute'),
 ('Al-Nasiriyah Teaching Hospital',
  'Research Center Future Energy Materials and Systems',
  'NOAA Office of Modeling and Development',
  'Odesa Military Academy'),
 ('University Of Bristol Dental Hospital',
  'NOAA Weather Program Office',
  'The Bahamas Agriculture and Marine Science Institute',
  'International Brain Laboratory'),
 ('Bristol Royal Infirmary',
  'Texila American University Zambia',
  'BC Housing',
  'Federal University of Agriculture, Abeokuta'))
QUESTIONS = ('Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Sekolah Tinggi Ilmu Tarbiyah Miftahul Ulum Bangkalan\n'
 '2. Mrs. Kesharbai Sonajirao Kshirsagar Alias Kaku Arts, Science & Commerce College, Beed\n'
 '3. Helmholtz Center for Information Security\n'
 '4. Shenzhen International Quantum Academy\n'
 '</ENTITIES>\n'
 'The column names are: Organization, ROR ID, Country code. Use the 9-character ROR ID suffix, not '
 'the full URL, and the ISO 3166-1 alpha-2 country code. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Akademie für Tierschutz des Deutschen Tierschutzbundes e.V.\n'
 '2. ARTHritEs, Microchimérisme et InflammationS\n'
 '3. Kurdistan Higher Council of Medical Specialties\n'
 '4. SA Genome Editing Facility\n'
 '</ENTITIES>\n'
 'The column names are: Organization, ROR ID, Country code. Use the 9-character ROR ID suffix, not '
 'the full URL, and the ISO 3166-1 alpha-2 country code. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Akademi Kebidanan Tahirah Al Baeti Bulukumba\n'
 '2. Boyle Street Community Services\n'
 '3. Wuhan Surveying-Geotechnical Research Institute\n'
 '4. Grandview Kids\n'
 '</ENTITIES>\n'
 'The column names are: Organization, ROR ID, Country code. Use the 9-character ROR ID suffix, not '
 'the full URL, and the ISO 3166-1 alpha-2 country code. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Universitas Asa Indonesia\n'
 '2. Jefferson Einstein Philadelphia Hospital\n'
 '3. Universidad del País Innova\n'
 '4. National Academy of Medical Sciences of Ukraine\n'
 '</ENTITIES>\n'
 'The column names are: Organization, ROR ID, Country code. Use the 9-character ROR ID suffix, not '
 'the full URL, and the ISO 3166-1 alpha-2 country code. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Akademi Pelayaran Nasional Surakarta\n'
 '2. Matériaux Ingénierie et Science\n'
 '3. Clevedon Hospital\n'
 '4. Weston General Hospital\n'
 '</ENTITIES>\n'
 'The column names are: Organization, ROR ID, Country code. Use the 9-character ROR ID suffix, not '
 'the full URL, and the ISO 3166-1 alpha-2 country code. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. St. Vincent Pallotti College of Engineering & Technology\n'
 '2. Vidyasagar Metropolitan College\n'
 "3. Waasegiizhig Nanaandawe'iyewigamig\n"
 '4. Instituto Tecnológico Superior de Villa la Venta\n'
 '</ENTITIES>\n'
 'The column names are: Organization, ROR ID, Country code. Use the 9-character ROR ID suffix, not '
 'the full URL, and the ISO 3166-1 alpha-2 country code. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Mindanao State University\n'
 '2. Centre for European Economic Research\n'
 '3. Engineering Science Lyon Tohoku, Materials under eXtreme conditions\n'
 '4. Geneva College of Longevity Science\n'
 '</ENTITIES>\n'
 'The column names are: Organization, ROR ID, Country code. Use the 9-character ROR ID suffix, not '
 'the full URL, and the ISO 3166-1 alpha-2 country code. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Saraswathi Institute of Medical Sciences\n'
 '2. Lyon 1 Université\n'
 '3. Institut zur Erforschung von Mission und Kirche\n'
 '4. Visoka škola za turizam i menadžment Konjic\n'
 '</ENTITIES>\n'
 'The column names are: Organization, ROR ID, Country code. Use the 9-character ROR ID suffix, not '
 'the full URL, and the ISO 3166-1 alpha-2 country code. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Center for Economic and Policy Research\n'
 '2. Institut des Sciences Cognitives Marc Jeannerod\n'
 '3. Arrhenius Research Institute\n'
 '4. Nakhchivan Teachers Institute\n'
 '</ENTITIES>\n'
 'The column names are: Organization, ROR ID, Country code. Use the 9-character ROR ID suffix, not '
 'the full URL, and the ISO 3166-1 alpha-2 country code. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Al-Nasiriyah Teaching Hospital\n'
 '2. Research Center Future Energy Materials and Systems\n'
 '3. NOAA Office of Modeling and Development\n'
 '4. Odesa Military Academy\n'
 '</ENTITIES>\n'
 'The column names are: Organization, ROR ID, Country code. Use the 9-character ROR ID suffix, not '
 'the full URL, and the ISO 3166-1 alpha-2 country code. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. University Of Bristol Dental Hospital\n'
 '2. NOAA Weather Program Office\n'
 '3. The Bahamas Agriculture and Marine Science Institute\n'
 '4. International Brain Laboratory\n'
 '</ENTITIES>\n'
 'The column names are: Organization, ROR ID, Country code. Use the 9-character ROR ID suffix, not '
 'the full URL, and the ISO 3166-1 alpha-2 country code. Return one table only.',
 'Use public web sources to return one Markdown table about these organizations:\n'
 '<ENTITIES>\n'
 '1. Bristol Royal Infirmary\n'
 '2. Texila American University Zambia\n'
 '3. BC Housing\n'
 '4. Federal University of Agriculture, Abeokuta\n'
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
            raise RuntimeError("V2.46.64 protected watcher is absent")
        raw = stat.read_text(encoding="utf-8")
        suffix = raw[raw.rfind(")") + 2 :].split()
        command = cmdline.read_bytes().replace(b"\0", b" ").decode(errors="replace")
        if len(suffix) <= 19 or marker not in command:
            raise RuntimeError("V2.46.64 protected watcher identity drifted")
        output.append({"pid": pid, "marker": marker, "start_ticks": int(suffix[19])})
    return output


def visible_task(ordinal: int) -> dict[str, str]:
    if isinstance(ordinal, bool) or not isinstance(ordinal, int) or not 1 <= ordinal <= SELECTED_COUNT:
        raise ValueError("V2.46.64 task ordinal drifted")
    value = {
        "opaque_id": f"task_{0x246640 + ordinal:024x}",
        "question": QUESTIONS[ordinal - 1],
    }
    if extract_visible_entities(value["question"]) != list(ENTITY_GROUPS[ordinal - 1]):
        raise ValueError("V2.46.64 visible task round trip drifted")
    return value


def task_vector() -> list[dict[str, str]]:
    return [visible_task(index) for index in range(1, SELECTED_COUNT + 1)]


__all__ = [name for name in tuple(globals()) if name.isupper()] + [
    "payload_sha256", "protected_watcher_snapshot", "sha256", "task_vector", "visible_task",
]
