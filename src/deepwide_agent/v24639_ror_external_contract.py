"""Visible-only frozen contract for the V2.46.39 harder ROR external gate."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from .v24639_ror_objective_runtime import extract_visible_entities


DATE = "20260806"
PROTOCOL_ID = "v24639_harder_ror_exact_table_objective_alignment_v1"
PROTOCOL = Path(f"results/v24639_ror_objective_alignment_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v24639_ror_objective_alignment_preactivation_audit_v1_{DATE}.json")
ACTIVATION = Path(f"results/v24639_ror_objective_alignment_activation_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v24639_ror_objective_alignment_execution_start_v1_{DATE}.json")
FORWARD_RESULT = Path(f"results/v24639_ror_objective_alignment_forward_result_v1_{DATE}.json")
FORWARD_AUDIT = Path(f"results/v24639_ror_objective_alignment_forward_audit_v1_{DATE}.json")
EVALUATOR_PROTOCOL = Path(f"results/v24639_ror_objective_alignment_evaluator_preregistration_v1_{DATE}.json")
RESULT = Path(f"results/v24639_ror_objective_alignment_result_v1_{DATE}.json")
POSTAUDIT = Path(f"results/v24639_ror_objective_alignment_postresult_audit_v1_{DATE}.json")
OUTPUT_ROOT = Path(f"outputs/v24639_ror_objective_alignment_v1_{DATE}")
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
TASK_ROOT = OUTPUT_ROOT / "tasks"
PREDICTIONS = OUTPUT_ROOT / "frozen_predictions.jsonl"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
RUN_SUMMARY = OUTPUT_ROOT / "run_summary.json"
LEASE_PATH = Path("outputs/deepwide_benchmark_api.lease.lock")
LEASE_OWNER = PROTOCOL_ID
LEASE_PURPOSE = "benchmark_external_harder_ror_exact_table_objective_alignment"
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
    "proxy_url": "http://127.0.0.1:9878/responses", "name": "gpt-5.6-sol",
    "reasoning_effort": "low", "service_tier": "priority",
    "timeout_seconds": 65, "max_retries": 2,
}
SEARCH = {
    "proxy_url": "http://127.0.0.1:9878/responses", "model": "gpt-5.6-sol",
    "workers": 1, "batch_size": 8, "context_size": "medium",
    "max_output_tokens": 7_000, "timeout_seconds": 65, "max_retries": 2,
    "fetch_workers": 8, "fetch_timeout_seconds": 20,
    "hard_fetch_deadline_seconds": 25,
}
LIMITS = {
    "wall_seconds": 240, "model_calls": 3, "search_queries": 4,
    "fetch_targets": 10, "search_results_per_query": 3,
    "evidence_chars": 60_000, "page_chars": 5_000,
    "plan_output_tokens": 4_000, "synthesis_output_tokens": 30_000,
    "repair_output_tokens": 12_000,
}

ENTITY_GROUPS = (
    ("Institut de Biologie et de Chimie des Protéines", "SINOPEC Beijing Research Institute of Chemical Industry", "Helmholtz Munich", "New Generation University"),
    ("Inspektorat Kabupaten Majalengka", "Swarma Research", "Islamic Azad University, Tehran", "Charité - Universitätsmedizin Berlin"),
    ("Sekolah Tinggi Teologi Anugrah Indonesia", "Black Doc Village", "Inaya Medical Colleges", "Canadian Virtual Hospice"),
    ("Politeknik Pelayaran Malahayati", "Geological Survey of South Australia", "Cancer Care Alberta", "Polish University Abroad"),
    ("Pragjyotish College", "Fundación EcoMinga - Red de Protección de Bosques Amenazados", "First Lviv Territorial Medical Union", "École Supérieure Africaine des TIC"),
    ("Ministère de la Culture", "Forever Vision Eye Centre", "Agência de Investigação Clínica e Inovação Biomédica", "Technology and Mental Health Hub"),
    ("Einstein Healthcare Network", "Entrepôts, Représentation et Ingénierie des Connaissances", "Institute of Geography", "Institute of Epigenetics and Stem Cells"),
    ("Shenzhen Traditional Chinese Medicine Hospital", "Silver Oak University", "Instituto de Investigación en Agrobiotecnología", "SENTRAL College Penang"),
    ("Government of British Columbia", "Instituto Tecnológico de Chetumal", "ABEx Bio-Research Center", "Instituto Español de Ciencias Histórico-Jurídicas"),
    ("Hospital de Urgencia Asistencia Pública", "Federal College of Animal Health and Production Technology, Vom", "Sandia National Laboratories", "Fundação Centro Médico de Campinas"),
    ("Tecnológico Nacional de México", "Bristol Royal Hospital for Children", "Baba Ahmed University", "Fundação Instituto de Pesquisas Contábeis, Atuariais e Financeiras"),
    ("Midnapore College", "Jose Maria College Foundation", "The Therapeutic Clinic at the Baruch Ivcher School of Psychology", "Reichman University"),
)


def _question(group: tuple[str, ...]) -> str:
    rows = "\n".join(f"{index}. {entity}" for index, entity in enumerate(group, 1))
    return (
        "Use public web sources to return one Markdown table about these organizations:\n"
        f"<ENTITIES>\n{rows}\n</ENTITIES>\n"
        "The column names are: Organization, ROR ID, Country code. Return one table only."
    )


QUESTIONS = tuple(_question(group) for group in ENTITY_GROUPS)


def payload_sha256(value: object) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def protected_watcher_snapshot(proc_root: Path = Path("/proc")) -> list[dict[str, Any]]:
    output = []
    for pid, marker in PROTECTED_WATCHERS:
        stat, cmdline = proc_root / str(pid) / "stat", proc_root / str(pid) / "cmdline"
        if not stat.is_file() or not cmdline.is_file():
            raise RuntimeError("V2.46.39 protected watcher is absent")
        raw = stat.read_text(encoding="utf-8")
        suffix = raw[raw.rfind(")") + 2 :].split()
        command = cmdline.read_bytes().replace(b"\0", b" ").decode(errors="replace")
        if len(suffix) <= 19 or marker not in command:
            raise RuntimeError("V2.46.39 protected watcher identity drifted")
        output.append({"pid": pid, "marker": marker, "start_ticks": int(suffix[19])})
    return output


def visible_task(ordinal: int) -> dict[str, str]:
    if isinstance(ordinal, bool) or not isinstance(ordinal, int) or not 1 <= ordinal <= SELECTED_COUNT:
        raise ValueError("V2.46.39 task ordinal drifted")
    value = {"opaque_id": f"task_{0x246390 + ordinal:024x}", "question": QUESTIONS[ordinal - 1]}
    if extract_visible_entities(value["question"]) != list(ENTITY_GROUPS[ordinal - 1]):
        raise ValueError("V2.46.39 visible task round trip drifted")
    return value


def task_vector() -> list[dict[str, str]]:
    return [visible_task(index) for index in range(1, SELECTED_COUNT + 1)]


__all__ = [name for name in tuple(globals()) if name.isupper()] + [
    "payload_sha256", "protected_watcher_snapshot", "sha256", "task_vector", "visible_task",
]
