"""Visible-only frozen contract for the V2.46.40 ROR revision gate."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .v24639_ror_objective_runtime import extract_visible_entities


DATE = "20260806"
PROTOCOL_ID = "v24640_evidence_constrained_missing_ror_revision_v1"
PROTOCOL = Path(f"results/v24640_evidence_constrained_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v24640_evidence_constrained_preactivation_audit_v1_{DATE}.json")
ACTIVATION = Path(f"results/v24640_evidence_constrained_activation_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v24640_evidence_constrained_execution_start_v1_{DATE}.json")
FORWARD_RESULT = Path(f"results/v24640_evidence_constrained_forward_result_v1_{DATE}.json")
FORWARD_AUDIT = Path(f"results/v24640_evidence_constrained_forward_audit_v1_{DATE}.json")
OUTPUT_ROOT = Path(f"outputs/v24640_evidence_constrained_v1_{DATE}")
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
TASK_ROOT = OUTPUT_ROOT / "tasks"
PREDICTIONS = OUTPUT_ROOT / "frozen_predictions.jsonl"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
RUN_SUMMARY = OUTPUT_ROOT / "run_summary.json"
LEASE_PATH = Path("outputs/deepwide_benchmark_api.lease.lock")
LEASE_OWNER = PROTOCOL_ID
LEASE_PURPOSE = "benchmark_external_evidence_constrained_missing_ror_revision"
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

ENTITY_GROUPS = (
    (
        "Acharya Prafulla Chandra Roy Government College",
        "Open Source Medicine Foundation",
        "Institute of Computational Biology",
        "Australian Bureau of Agricultural and Resource Economics and Sciences",
    ),
    (
        "Centre de Recherche Astrophysique de Lyon",
        "Ministry of Health of the Republic of Uzbekistan",
        "McCreary Centre Society",
        "Instituto Superior Tecnológico Escuela de los Chefs de Guayaquil",
    ),
    (
        "Institut des Sciences de la Terre",
        "Cluster University Srinagar",
        "National Metrology Institute of Japan",
        "Institute of Bioinformatics and Systems Biology",
    ),
    (
        "Institut Teknologi Bisnis dan Kesehatan Bhakti Putra Bangsa Indonesia",
        "Kampala International University in Tanzania",
        "Central Regional Referral Hospital",
        "Kaduna State College of Education Gidan Waya",
    ),
    (
        "Universidad de Sotavento Coatzacoalcos Campus",
        "Burke Museum of Natural History and Culture",
        "Colegio de Farmacéuticos de la Provincia de Buenos Aires",
        "Stațiunea de Cercetare Dezvoltare Agricolă Turda",
    ),
    (
        "Sekolah Tinggi Ilmu Farmasi Pelita Mas Palu",
        "Alzheimer Society of BC and Yukon",
        "Faculdade EBRAMEC",
        "Prefeitura Municipal de Porto Alegre",
    ),
    (
        "Sekolah Tinggi Ilmu Manajemen Budi Bakti",
        "College of Education Warri",
        "Geological Experiment and Testing Center of Hunan Province",
        "Brisbane Institute of Strengths Based Practice",
    ),
    (
        "Bundelkhand Medical College",
        "Shared Health",
        "National Institute of Advanced Industrial Science and Technology",
        "Rubinstein Center for Constitutional Challenges",
    ),
    (
        "Hospices Civils de Lyon",
        "Easterseals",
        "Research Centre for Smallholder Farmers",
        "Ministry of Agriculture, Food and Rural Affairs",
    ),
    (
        "NTT Medical Center Sapporo",
        "Xinyang Normal University",
        "Medicare Laboratories",
        "PHAETHON Centre of Excellence",
    ),
    (
        "China Meteorological Administration",
        "Mid-America Reformed Seminary",
        "South Bristol Community Hospital",
        "University Hospital Zurich",
    ),
    (
        "Université Lumumba",
        "Instituto Federal de Educação, Ciência e Tecnologia Baiano",
        "Kattakurgan State Pedagogical Institute",
        "Georgian Farmers' Association",
    ),
)


def _question(group: tuple[str, ...]) -> str:
    rows = "\n".join(f"{index}. {entity}" for index, entity in enumerate(group, 1))
    return (
        "Use public web sources to return one Markdown table about these organizations:\n"
        f"<ENTITIES>\n{rows}\n</ENTITIES>\n"
        "The column names are: Organization, ROR ID, Country code. "
        "Use the 9-character ROR ID suffix, not the full URL, and the ISO 3166-1 alpha-2 country code. "
        "Return one table only."
    )


QUESTIONS = tuple(_question(group) for group in ENTITY_GROUPS)


def payload_sha256(value: object) -> str:
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


def protected_watcher_snapshot(proc_root: Path = Path("/proc")) -> list[dict[str, Any]]:
    output = []
    for pid, marker in PROTECTED_WATCHERS:
        stat = proc_root / str(pid) / "stat"
        cmdline = proc_root / str(pid) / "cmdline"
        if not stat.is_file() or not cmdline.is_file():
            raise RuntimeError("V2.46.40 protected watcher is absent")
        raw = stat.read_text(encoding="utf-8")
        suffix = raw[raw.rfind(")") + 2 :].split()
        command = cmdline.read_bytes().replace(b"\0", b" ").decode(errors="replace")
        if len(suffix) <= 19 or marker not in command:
            raise RuntimeError("V2.46.40 protected watcher identity drifted")
        output.append({"pid": pid, "marker": marker, "start_ticks": int(suffix[19])})
    return output


def visible_task(ordinal: int) -> dict[str, str]:
    if (
        isinstance(ordinal, bool)
        or not isinstance(ordinal, int)
        or not 1 <= ordinal <= SELECTED_COUNT
    ):
        raise ValueError("V2.46.40 task ordinal drifted")
    value = {
        "opaque_id": f"task_{0x246400 + ordinal:024x}",
        "question": QUESTIONS[ordinal - 1],
    }
    if extract_visible_entities(value["question"]) != list(ENTITY_GROUPS[ordinal - 1]):
        raise ValueError("V2.46.40 visible task round trip drifted")
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
