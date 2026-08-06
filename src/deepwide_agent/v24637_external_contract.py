"""Frozen constants and pure contracts for the V2.46.37 external gate."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from .v24637_objective_alignment_runtime import extract_visible_entities


DATE = "20260806"
PROTOCOL_ID = "v24637_external_exact_table_objective_alignment_v1"
FORWARD_ROLE = "v24637_external_objective_alignment_forward_contract"
PROTOCOL = Path(f"results/v24637_objective_alignment_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v24637_objective_alignment_preactivation_audit_v1_{DATE}.json")
ACTIVATION = Path(f"results/v24637_objective_alignment_activation_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v24637_objective_alignment_execution_start_v1_{DATE}.json")
FORWARD_RESULT = Path(f"results/v24637_objective_alignment_forward_result_v1_{DATE}.json")
FORWARD_AUDIT = Path(f"results/v24637_objective_alignment_forward_audit_v1_{DATE}.json")
EVALUATOR_PROTOCOL = Path(f"results/v24637_objective_alignment_evaluator_preregistration_v1_{DATE}.json")
RESULT = Path(f"results/v24637_objective_alignment_result_v1_{DATE}.json")
POSTAUDIT = Path(f"results/v24637_objective_alignment_postresult_audit_v1_{DATE}.json")
OUTPUT_ROOT = Path(f"outputs/v24637_objective_alignment_v1_{DATE}")
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
TASK_ROOT = OUTPUT_ROOT / "tasks"
PREDICTIONS = OUTPUT_ROOT / "frozen_predictions.jsonl"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
RUN_SUMMARY = OUTPUT_ROOT / "run_summary.json"
LEASE_PATH = Path("outputs/deepwide_benchmark_api.lease.lock")
LEASE_OWNER = PROTOCOL_ID
LEASE_PURPOSE = "benchmark_external_exact_table_objective_alignment"
RUNNER_MARKER = "scripts/run_v24637_objective_alignment.py"
CHILD_MARKER = "scripts/run_v24637_objective_alignment_task.py"
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
OPAQUE = re.compile(r"task_[0-9a-f]{24}")

ENTITY_GROUPS = (
    ("John F. Kennedy International Airport", "Los Angeles International Airport", "Chicago O'Hare International Airport", "Hartsfield Jackson Atlanta International Airport", "Dallas Fort Worth International Airport", "Denver International Airport", "San Francisco International Airport", "Boston Logan International Airport"),
    ("Seattle–Tacoma International Airport", "Phoenix Sky Harbor International Airport", "Minneapolis–Saint Paul International Airport / Wold–Chamberlain Field", "Miami International Airport", "Orlando International Airport", "Washington Dulles International Airport", "George Bush Intercontinental Airport", "Harry Reid International Airport"),
    ("London Heathrow Airport", "Charles de Gaulle International Airport", "Amsterdam Airport Schiphol", "Rome–Fiumicino Leonardo da Vinci International Airport", "Munich Airport", "Zürich Airport", "Josep Tarradellas Barcelona-El Prat Airport", "Adolfo Suárez Madrid–Barajas Airport"),
    ("Dublin Airport", "Copenhagen Kastrup Airport", "Helsinki Vantaa Airport", "Brussels Airport", "Vienna International Airport", "Lisbon Humberto Delgado Airport", "Warsaw Chopin Airport", "Václav Havel Airport Prague"),
    ("Frankfurt Main Airport", "İstanbul Airport", "Athens Eleftherios Venizelos International Airport", "Stockholm-Arlanda Airport", "Oslo-Gardermoen International Airport", "Berlin Brandenburg Airport", "Milan Malpensa International Airport", "Manchester Airport"),
    ("Singapore Changi Airport", "Hong Kong International Airport", "Incheon International Airport", "Narita International Airport", "Suvarnabhumi Airport", "Kuala Lumpur International Airport", "Chhatrapati Shivaji Maharaj International Airport", "Hamad International Airport"),
    ("Dubai International Airport", "Zayed International Airport", "King Abdulaziz International Airport", "Beijing Capital International Airport", "Shanghai Pudong International Airport", "Guangzhou Baiyun International Airport", "Taiwan Taoyuan International Airport", "Ninoy Aquino International Airport"),
    ("Soekarno-Hatta International Airport", "Noi Bai International Airport", "Tan Son Nhat International Airport", "Cairo International Airport", "O.R. Tambo International Airport", "Jomo Kenyatta International Airport", "Kotoka International Airport", "Mohammed V International Airport"),
    ("Addis Ababa Bole International Airport", "Murtala Muhammed International Airport", "Cape Town International Airport", "Blaise Diagne International Airport", "Houari Boumediene Airport", "Tunis Carthage International Airport", "Kigali International Airport", "Entebbe International Airport"),
    ("São Paulo/Guarulhos–Governor André Franco Montoro International Airport", "El Dorado International Airport", "Jorge Chávez International Airport", "Comodoro Arturo Merino Benítez International Airport", "Mariscal Sucre International Airport", "Tancredo Neves International Airport", "Porto Alegre-Salgado Filho International Airport", "Recife/Guararapes - Gilberto Freyre International Airport"),
    ("Auckland International Airport", "Sydney Kingsford Smith International Airport", "Melbourne Airport", "Brisbane International Airport", "Perth International Airport", "Adelaide International Airport", "Wellington International Airport", "Christchurch International Airport"),
    ("Toronto Pearson International Airport", "Vancouver International Airport", "Mexico City Benito Juárez International Airport", "Tocumen International Airport", "Juan Santamaría International Airport", "José Martí International Airport", "Punta Cana International Airport", "Philip S. W. Goldson International Airport"),
)


def _question(group: Sequence[str]) -> str:
    return (
        "Use public web sources to return one Markdown table about "
        + ", ".join(group[:-1]) + ", and " + group[-1]
        + ". The column names are: Airport, ICAO code, IATA code. Return one table only."
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
        stat = proc_root / str(pid) / "stat"
        cmdline = proc_root / str(pid) / "cmdline"
        if not stat.is_file() or not cmdline.is_file():
            raise RuntimeError("V2.46.37 protected watcher is absent")
        raw = stat.read_text(encoding="utf-8")
        suffix = raw[raw.rfind(")") + 2 :].split()
        command = cmdline.read_bytes().replace(b"\0", b" ").decode(errors="replace")
        if len(suffix) <= 19 or marker not in command:
            raise RuntimeError("V2.46.37 protected watcher identity drifted")
        output.append({"pid": pid, "marker": marker, "start_ticks": int(suffix[19])})
    return output


def visible_task(ordinal: int) -> dict[str, str]:
    if isinstance(ordinal, bool) or not isinstance(ordinal, int) or not 1 <= ordinal <= SELECTED_COUNT:
        raise ValueError("V2.46.37 task ordinal drifted")
    value = {"opaque_id": f"task_{0x246370 + ordinal:024x}", "question": QUESTIONS[ordinal - 1]}
    if extract_visible_entities(value["question"]) != list(ENTITY_GROUPS[ordinal - 1]):
        raise ValueError("V2.46.37 task round-trip drifted")
    return value


def task_vector() -> list[dict[str, str]]:
    return [visible_task(index) for index in range(1, SELECTED_COUNT + 1)]


__all__ = [name for name in tuple(globals()) if name.isupper()] + [
    "payload_sha256", "protected_watcher_snapshot", "sha256", "task_vector", "visible_task",
]
