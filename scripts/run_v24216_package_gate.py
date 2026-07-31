#!/usr/bin/env python3
"""Execute the V2.42.16 paired cold-start package gate once authorized.

Both arms use the same opaque dev64 IDs and the same model/search/runtime
template.  Mapping and evaluator inputs stay closed until both forward arms are
exact terminal.  Forward or evaluator residue is never resumed or selectively
rerun; mixed partial states fail closed.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Mapping


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24216_package_gate import (  # noqa: E402
    evaluate_package_gate,
    payload_sha256,
    validate_arm_result,
)
from scripts.audit_v24205_markdown_rebase_feasibility import (  # noqa: E402
    runtime_identity,
)
from scripts.build_v2410_rank_slot_candidate import (  # noqa: E402
    candidate_regular_file_manifest,
)
from scripts.compare_v24126_post_verification_partial_paired_dev import (  # noqa: E402
    validate_paired_evaluator_identity,
)
from scripts.finalize_fullset_rollout import (  # noqa: E402
    read_jsonl,
    validate_evaluator_contract,
)
from scripts.finalize_v2408_combined_dev64 import (  # noqa: E402
    _initialize_empty_evaluator,
    _prepare_exact64,
    _summarize_exact64,
    _validate_prepare,
)
from scripts.preflight_deepwide import REQUIRED_FORWARD_CODE_PATHS  # noqa: E402
from scripts.preregister_v2408_combined_fasttrack import (  # noqa: E402
    R1_FINAL_SEAL,
    R1_FREEZES,
    R1_RESULT,
)
from scripts.publish_v24206_markdown_component import _write_candidate  # noqa: E402
from scripts.publish_v24215_joint_package_recovery import (  # noqa: E402
    CANDIDATE_ROOT as PARENT_CANDIDATE_ROOT,
    OUTPUT as PARENT_PUBLICATION,
)
from scripts.replay_v24201_repo_local_candidate_dag import (  # noqa: E402
    PUBLICATIONS,
    build_replay,
    manifest_sha256,
    publication_manifest,
    read_publication,
    text_manifest,
)
from scripts.run_official_eval_local import validate_committed_eval_rows  # noqa: E402
from scripts.v2410_avg4_common import read_object  # noqa: E402


PARENT_STATE = Path(
    "outputs/v24215_selected_joint_package_recovery_state_v1_20260731.json"
)
SOURCE_MANIFEST = Path("outputs/runtime_manifest_v1_repro/manifest.jsonl")
SOURCE_IDS = Path("configs/full220_v2403_r1_devval_s04.ids")
MAPPING = Path("outputs/runtime_manifest_v1_repro/evaluator_mapping.jsonl")
BASELINE_ROOT = ROOT / "outputs/v24216_package_gate_baseline_arm_v1_20260731"
CANDIDATE_ROOT = ROOT / "outputs/v24216_package_gate_candidate_arm_v1_20260731"
PAIR_PREPARE = Path("results/v24216_package_gate_pair_prepare_v1_20260731.json")
FORWARD_BARRIER = Path(
    "results/v24216_package_gate_forward_terminal_barrier_v1_20260731.json"
)
BASELINE_RESULT = Path("results/v24216_package_gate_baseline_dev64_v1_20260731.json")
CANDIDATE_RESULT = Path("results/v24216_package_gate_candidate_dev64_v1_20260731.json")
GATE_DECISION = Path("results/v24216_package_gate_decision_v1_20260731.json")
ARM_ROOTS = {"baseline": BASELINE_ROOT, "candidate": CANDIDATE_ROOT}
ARM_TARGETS = {
    "baseline": "dev64_v24216_selected_baseline_cold_v1_20260731",
    "candidate": "dev64_v24216_joint_package_cold_v1_20260731",
}
BASELINE_REPLAY_KEYS = {
    "p12": "schema68",
    "schema76": "schema76",
    "schema77": "schema77",
}
OPAQUE_ID_PREFIX = "task_"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_new_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def publish_new(path: Path, value: Mapping[str, Any]) -> None:
    _write_new_text(
        path,
        json.dumps(dict(value), ensure_ascii=False, indent=2) + "\n",
    )


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    _write_new_text(
        path,
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
    )


def _read_ids(path: Path) -> list[str]:
    values = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if (
        len(values) != 64
        or len(values) != len(set(values))
        or any(not value.startswith(OPAQUE_ID_PREFIX) for value in values)
    ):
        raise RuntimeError("V2.42.16 opaque dev64 partition drifted")
    return values


def validate_parent_publication(root: Path = ROOT) -> dict[str, Any]:
    """Validate only terminal control/publication data, never benchmark rows."""

    state = read_object(root / PARENT_STATE)
    state_unsigned = dict(state)
    state_seal = state_unsigned.pop("state_payload_sha256", None)
    if (
        state.get("role") != "v24215_selected_joint_package_recovery_state"
        or state.get("terminal") is not True
        or state.get("status")
        not in {
            "complete_selected_baseline_identity_handoff_recovered",
            "complete_joint_package_recovery_revalidated",
        }
        or state.get("joint_package_publication_created") is not True
        or state.get("package_gate_evaluated_or_launched") is not False
        or state.get("dev64_launch_allowed") is not False
        or state.get("mapping_gold_category_question_type_evaluator_score_or_reward_read")
        is not False
        or state_seal != payload_sha256(state_unsigned)
    ):
        raise RuntimeError("V2.42.16 parent terminal envelope drifted")
    publication_path = root / PARENT_PUBLICATION
    publication = read_object(publication_path)
    unsigned = dict(publication)
    seal = unsigned.pop("publication_payload_sha256", None)
    false_fields = (
        "component_directory_overlay_used",
        "silent_component_drop_or_baseline_fallback_used",
        "package_gate_evaluated_or_launched",
        "dev64_launch_allowed",
        "shared_api_lease_acquired",
        "network_model_search_fetch_evaluator_or_api_called",
        "mapping_gold_category_question_type_evaluator_score_or_reward_read",
        "benchmark_forward_or_full220_launch_allowed",
        "leaderboard_submission_or_sota_claim",
    )
    if (
        publication.get("role")
        != "v24215_selected_joint_package_recovery_publication"
        or publication.get("label_blind") is not True
        or publication.get("all_selected_components_covered_exactly_once") is not True
        or publication.get("single_deepest_cumulative_graph_used") is not True
        or any(publication.get(field) is not False for field in false_fields)
        or seal != payload_sha256(unsigned)
        or state.get("publication", {}).get("sha256") != sha256(publication_path)
    ):
        raise RuntimeError("V2.42.16 parent publication drifted")
    order = publication.get("joint_package_order")
    if not isinstance(order, dict):
        raise RuntimeError("V2.42.16 parent joint order is absent")
    identity = bool(order.get("identity_handoff_only"))
    component = publication.get("component_publication")
    if (
        identity != bool(publication.get("identity_handoff_only"))
        or (component is None) is not identity
        or not identity
        and (
            publication.get("joint_package_materialized") is not True
            or publication.get("complete_parent_and_component_regression_rerun")
            is not True
            or publication.get("strict_component_activation_validated") is not True
        )
    ):
        raise RuntimeError("V2.42.16 parent package disposition drifted")
    return publication


def _baseline_files(publication: Mapping[str, Any]) -> dict[str, str]:
    order = publication["joint_package_order"]
    baseline_name = str(order["baseline_name"])
    key = BASELINE_REPLAY_KEYS.get(baseline_name)
    if key is None:
        raise RuntimeError("V2.42.16 baseline is unregistered")
    replay, maps = build_replay()
    if replay.get("all_stage_file_maps_byte_exact_to_frozen_publications") is not True:
        raise RuntimeError("V2.42.16 baseline replay failed")
    files = dict(maps[key])
    frozen = read_publication(PUBLICATIONS[key])
    baseline = order["baseline_publication"]
    path = ROOT / str(baseline["path"])
    if (
        path.is_symlink()
        or not path.is_file()
        or sha256(path) != baseline["sha256"]
        or publication_manifest(frozen) != text_manifest(files)
        or publication_manifest(read_object(path)) != text_manifest(files)
    ):
        raise RuntimeError("V2.42.16 selected baseline bytes drifted")
    return files


def _candidate_files(publication: Mapping[str, Any]) -> dict[str, str]:
    component = publication.get("component_publication")
    if not isinstance(component, Mapping):
        raise RuntimeError("V2.42.16 nonempty package candidate is absent")
    source = Path(str(component.get("candidate_root", ""))).resolve()
    expected_manifest = component.get("candidate_regular_file_manifest")
    if (
        source != PARENT_CANDIDATE_ROOT.resolve()
        or source.is_symlink()
        or not source.is_dir()
        or not isinstance(expected_manifest, Mapping)
        or candidate_regular_file_manifest(source, source_only=True)
        != dict(expected_manifest)
    ):
        raise RuntimeError("V2.42.16 joint candidate source drifted")
    output: dict[str, str] = {}
    for relative, digest in expected_manifest.items():
        path = source / str(relative)
        if (
            path.is_symlink()
            or not path.is_file()
            or not path.resolve().is_relative_to(source)
            or sha256(path) != str(digest)
        ):
            raise RuntimeError("V2.42.16 joint candidate file drifted")
        output[str(relative)] = path.read_text(encoding="utf-8")
    return output


def execution_template(root: Path = ROOT) -> dict[str, Any]:
    """Freeze model/search/runtime from the original preregistered R1 envelope."""

    source = read_object(root / R1_FREEZES[-1])
    model = copy.deepcopy(source.get("model"))
    search = copy.deepcopy(source.get("search"))
    runtime = copy.deepcopy(source.get("runtime"))
    launch_gates = copy.deepcopy(source.get("launch_gates"))
    if not all(isinstance(value, dict) and value for value in (model, search, runtime, launch_gates)):
        raise RuntimeError("V2.42.16 execution template is incomplete")
    if (
        model.get("name") != "gpt-5.6-sol"
        or model.get("proxy_url") != "http://127.0.0.1:9878/responses"
        or model.get("reasoning_effort") != "high"
        or runtime.get("candidate_tokens") != 20000
    ):
        raise RuntimeError("V2.42.16 execution template drifted")
    return {
        "model": model,
        "search": search,
        "runtime": runtime,
        "launch_gates": launch_gates,
    }


def build_arm_freeze(
    arm: str,
    files: Mapping[str, str],
    *,
    manifest_sha: str,
    ids_sha: str,
    template: Mapping[str, Any],
) -> dict[str, Any]:
    if arm not in ARM_ROOTS:
        raise RuntimeError("V2.42.16 arm name is invalid")
    missing = sorted(REQUIRED_FORWARD_CODE_PATHS - set(files))
    if missing:
        raise RuntimeError(f"V2.42.16 arm forward closure is incomplete: {missing}")
    schema, version = runtime_identity(files["src/deepwide_agent/runtime.py"])
    value = {
        "freeze_status": "preregistered-v24216-paired-cold-dev64",
        "pipeline_version": version,
        "state_schema_version": schema,
        "experiment_role": (
            "paired consumed development package gate; exact64; failure-as-zero; "
            "not fresh, held-out, full220, Avg@4, leaderboard, or SOTA"
        ),
        "runtime_boundary": ["opaque_id", "question"],
        "selection_rule": "exact preregistered opaque dev64 IDs without content or outcome selection",
        "selected_count": 64,
        "selected_ids_file": f"configs/{ARM_TARGETS[arm]}/devval.ids",
        "selected_ids_sha256": ids_sha,
        "manifest": "data/runtime_manifest.jsonl",
        "manifest_sha256": manifest_sha,
        "code_sha256": {
            relative: hashlib.sha256(files[relative].encode()).hexdigest()
            for relative in sorted(REQUIRED_FORWARD_CODE_PATHS)
        },
        "model": copy.deepcopy(template["model"]),
        "search": copy.deepcopy(template["search"]),
        "runtime": copy.deepcopy(template["runtime"]),
        "launch_gates": copy.deepcopy(template["launch_gates"]),
        "reporting": {
            "cold_start_required": True,
            "consumed_online_diagnostic": False,
            "freshness_claim_allowed": False,
            "quality_comparison_claim_allowed": True,
            "leaderboard_or_sota_claim_allowed": False,
            "failed_or_unresolved_tasks_count_as_zero": True,
            "evaluator_join_only_after_both_forward_arms_terminal": True,
            "forward_resume_or_selective_rerun_allowed": False,
        },
        "v24216_arm": arm,
    }
    value["freeze_payload_sha256"] = payload_sha256(value)
    return value


def _materialize_arm(
    arm: str,
    files: Mapping[str, str],
    *,
    template: Mapping[str, Any],
    source_manifest: Path,
    source_ids: Path,
) -> dict[str, Any]:
    target = ARM_ROOTS[arm]
    if target.exists() or target.is_symlink():
        raise FileExistsError(target)
    target.mkdir(parents=True, exist_ok=False)
    try:
        (target / ".venv-eval").symlink_to(
            (ROOT / ".venv-eval").resolve(), target_is_directory=True
        )
        _write_candidate(target, files)
        input_manifest = target / "data/runtime_manifest.jsonl"
        input_manifest.parent.mkdir(parents=True, exist_ok=False)
        shutil.copyfile(source_manifest, input_manifest)
        ids = target / f"configs/{ARM_TARGETS[arm]}/devval.ids"
        ids.parent.mkdir(parents=True, exist_ok=False)
        shutil.copyfile(source_ids, ids)
        freeze = build_arm_freeze(
            arm,
            files,
            manifest_sha=sha256(input_manifest),
            ids_sha=sha256(ids),
            template=template,
        )
        freeze_path = ids.with_name("devval.json")
        publish_new(freeze_path, freeze)
        live = candidate_regular_file_manifest(target, source_only=True)
        expected = text_manifest(files)
        if live != expected:
            raise RuntimeError("V2.42.16 materialized arm source drifted")
        return {
            "arm": arm,
            "root": str(target),
            "source_manifest_sha256": manifest_sha256(expected),
            "pipeline_version": freeze["pipeline_version"],
            "state_schema_version": freeze["state_schema_version"],
            "freeze_path": str(freeze_path.relative_to(target)),
            "freeze_sha256": sha256(freeze_path),
            "ids_sha256": sha256(ids),
            "manifest_sha256": sha256(input_manifest),
            "execution_template_sha256": payload_sha256(
                {name: freeze[name] for name in ("model", "search", "runtime", "launch_gates")}
            ),
            "output_absent": True,
        }
    except BaseException:
        shutil.rmtree(target, ignore_errors=True)
        raise


def prepare_pair(
    publication: Mapping[str, Any],
    *,
    root: Path = ROOT,
) -> dict[str, Any]:
    """Create both sealed fresh roots before either forward arm runs."""

    if publication.get("identity_handoff_only") is True:
        raise RuntimeError("V2.42.16 identity handoff does not require dev64")
    target = root / PAIR_PREPARE
    if target.exists() or target.is_symlink():
        raise FileExistsError(target)
    if any(path.exists() or path.is_symlink() for path in ARM_ROOTS.values()):
        raise RuntimeError("V2.42.16 paired cold roots are not pristine")
    source_manifest = root / SOURCE_MANIFEST
    source_ids = root / SOURCE_IDS
    _read_ids(source_ids)
    if not source_manifest.is_file() or source_manifest.is_symlink():
        raise RuntimeError("V2.42.16 runtime manifest is unavailable")
    template = execution_template(root)
    baseline_files = _baseline_files(publication)
    candidate_files = _candidate_files(publication)
    created: list[Path] = []
    try:
        baseline = _materialize_arm(
            "baseline",
            baseline_files,
            template=template,
            source_manifest=source_manifest,
            source_ids=source_ids,
        )
        created.append(BASELINE_ROOT)
        candidate = _materialize_arm(
            "candidate",
            candidate_files,
            template=template,
            source_manifest=source_manifest,
            source_ids=source_ids,
        )
        created.append(CANDIDATE_ROOT)
        if (
            baseline["ids_sha256"] != candidate["ids_sha256"]
            or baseline["manifest_sha256"] != candidate["manifest_sha256"]
            or baseline["execution_template_sha256"]
            != candidate["execution_template_sha256"]
        ):
            raise RuntimeError("V2.42.16 paired execution identity differs")
        value: dict[str, Any] = {
            "artifact_version": 1,
            "role": "v24216_package_gate_pair_prepare",
            "label_blind": True,
            "parent_publication": {
                "path": str(PARENT_PUBLICATION),
                "sha256": sha256(root / PARENT_PUBLICATION),
                "decision_sha256": publication["joint_package_order"]["decision_sha256"],
            },
            "arms": {"baseline": baseline, "candidate": candidate},
            "same_opaque_dev64_ids": True,
            "same_runtime_manifest": True,
            "same_model_search_prompt_budget_threshold": True,
            "both_roots_cold_and_outputs_absent": True,
            "historical_baseline_result_reused": False,
            "mapping_or_evaluator_opened": False,
            "network_model_search_fetch_evaluator_or_api_called": False,
            "resume_or_selective_rerun_allowed": False,
            "full220_launch_allowed": False,
            "leaderboard_submission_or_sota_claim": False,
        }
        value["prepare_payload_sha256"] = payload_sha256(value)
        publish_new(target, value)
        return value
    except BaseException:
        for path in reversed(created):
            shutil.rmtree(path, ignore_errors=True)
        raise


def validate_pair_prepare(root: Path = ROOT) -> dict[str, Any]:
    value = read_object(root / PAIR_PREPARE)
    unsigned = dict(value)
    seal = unsigned.pop("prepare_payload_sha256", None)
    if (
        value.get("role") != "v24216_package_gate_pair_prepare"
        or value.get("same_opaque_dev64_ids") is not True
        or value.get("same_runtime_manifest") is not True
        or value.get("same_model_search_prompt_budget_threshold") is not True
        or value.get("both_roots_cold_and_outputs_absent") is not True
        or value.get("historical_baseline_result_reused") is not False
        or value.get("mapping_or_evaluator_opened") is not False
        or value.get("resume_or_selective_rerun_allowed") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.42.16 pair prepare drifted")
    rows = value.get("arms") or {}
    if set(rows) != set(ARM_ROOTS):
        raise RuntimeError("V2.42.16 pair prepare arms drifted")
    for arm, arm_root in ARM_ROOTS.items():
        row = rows[arm]
        freeze = arm_root / row["freeze_path"]
        live_manifest = candidate_regular_file_manifest(arm_root, source_only=True)
        if (
            Path(row["root"]).resolve() != arm_root.resolve()
            or not freeze.is_file()
            or freeze.is_symlink()
            or sha256(freeze) != row["freeze_sha256"]
            or not live_manifest
            or manifest_sha256(live_manifest) != row["source_manifest_sha256"]
        ):
            raise RuntimeError("V2.42.16 prepared arm drifted")
    return value


def _arm_paths(arm: str) -> dict[str, Path]:
    root = ARM_ROOTS[arm]
    target = ARM_TARGETS[arm]
    return {
        "root": root,
        "freeze": root / f"configs/{target}/devval.json",
        "ids": root / f"configs/{target}/devval.ids",
        "preflight": root / f"outputs/{target}_preflight.json",
        "preflight_log": root / f"outputs/{target}_preflight.log",
        "forward_log": root / f"outputs/{target}_forward.log",
        "out": root / f"outputs/{target}_devval",
        "final": root / f"outputs/{target}_dev64_final",
        "eval": root / f"outputs/{target}_dev64_eval",
        "eval_log": root / f"outputs/{target}_dev64_evaluate.log",
    }


def terminal_arm(arm: str) -> dict[str, Any] | None:
    paths = _arm_paths(arm)
    out = paths["out"]
    if not out.exists():
        return None
    if not out.is_dir():
        raise RuntimeError("V2.42.16 arm output is noncanonical")
    ids = _read_ids(paths["ids"])
    summary_path = out / "run_summary.json"
    runtime_path = out / "runtime_predictions.jsonl"
    if not summary_path.is_file() or not runtime_path.is_file():
        raise RuntimeError("V2.42.16 partial forward residue forbids rerun")
    summary = read_object(summary_path)
    completed = summary.get("completed")
    failed = summary.get("failed")
    if (
        summary.get("selected") != 64
        or isinstance(completed, bool)
        or not isinstance(completed, int)
        or isinstance(failed, bool)
        or not isinstance(failed, int)
        or completed + failed != 64
    ):
        raise RuntimeError("V2.42.16 arm is not exact terminal")
    rows = read_jsonl(runtime_path)
    projected = [
        (row.get("opaque_id"), row.get("status"))
        for row in rows
        if isinstance(row, dict)
    ]
    if (
        len(projected) != 64
        or len({item[0] for item in projected}) != 64
        or {item[0] for item in projected} != set(ids)
        or any(item[1] not in {"completed", "failed"} for item in projected)
        or sum(item[1] == "completed" for item in projected) != completed
    ):
        raise RuntimeError("V2.42.16 arm terminal envelopes drifted")
    return {
        "arm": arm,
        "selected": 64,
        "completed": completed,
        "failed": failed,
        "ids_sha256": sha256(paths["ids"]),
        "freeze_sha256": sha256(paths["freeze"]),
        "runtime_predictions_sha256": sha256(runtime_path),
        "run_summary_sha256": sha256(summary_path),
        "contents_emitted": False,
    }


def _run_logged(
    command: list[str],
    *,
    cwd: Path,
    log: Path,
    runner: Callable[..., subprocess.CompletedProcess[Any]] = subprocess.run,
) -> None:
    environment = {key: value for key, value in os.environ.items() if key != "PYTHONPATH"}
    environment.update(
        PYTHONDONTWRITEBYTECODE="1",
        PYTHONNOUSERSITE="1",
        PYTHONSAFEPATH="1",
    )
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("ab") as handle:
        completed = runner(
            command,
            cwd=cwd,
            env=environment,
            stdout=handle,
            stderr=subprocess.STDOUT,
            check=False,
        )
        handle.flush()
        os.fsync(handle.fileno())
    if completed.returncode != 0:
        raise RuntimeError(f"V2.42.16 command failed: {log}")


def run_forward_arm(
    arm: str,
    *,
    runner: Callable[..., subprocess.CompletedProcess[Any]] = subprocess.run,
) -> dict[str, Any]:
    """Run one arm exactly once; existing nonterminal output is fatal."""

    if terminal_arm(arm) is not None:
        raise RuntimeError("V2.42.16 arm already ran; rerun is forbidden")
    paths = _arm_paths(arm)
    if paths["preflight"].exists() or paths["out"].exists():
        raise RuntimeError("V2.42.16 arm residue forbids retry")
    python = str(paths["root"] / ".venv-eval/bin/python")
    preflight = [
        python,
        "-I",
        "-B",
        str(paths["root"] / "scripts/preflight_deepwide.py"),
        "--freeze",
        str(paths["freeze"]),
        "--report",
        str(paths["preflight"]),
        "--consecutive",
        "2",
    ]
    _run_logged(preflight, cwd=paths["root"], log=paths["preflight_log"], runner=runner)
    launch = [
        python,
        "-I",
        "-B",
        str(paths["root"] / "scripts/launch_frozen_deepwide.py"),
        "--freeze",
        str(paths["freeze"]),
        "--preflight-report",
        str(paths["preflight"]),
        "--out-dir",
        str(paths["out"]),
    ]
    _run_logged(launch, cwd=paths["root"], log=paths["forward_log"], runner=runner)
    terminal = terminal_arm(arm)
    if terminal is None:
        raise RuntimeError("V2.42.16 forward returned without exact terminal output")
    return terminal


def build_forward_barrier(
    baseline: Mapping[str, Any], candidate: Mapping[str, Any], *, root: Path = ROOT
) -> dict[str, Any]:
    """Seal both exact-terminal forwards before any mapping read."""

    if baseline.get("arm") != "baseline" or candidate.get("arm") != "candidate":
        raise RuntimeError("V2.42.16 forward barrier arm binding drifted")
    if (
        baseline.get("selected") != 64
        or candidate.get("selected") != 64
        or baseline.get("ids_sha256") != candidate.get("ids_sha256")
    ):
        raise RuntimeError("V2.42.16 forward barrier partition drifted")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24216_package_gate_forward_terminal_barrier",
        "pair_prepare": {"path": str(PAIR_PREPARE), "sha256": sha256(root / PAIR_PREPARE)},
        "arms": {"baseline": dict(baseline), "candidate": dict(candidate)},
        "both_forward_arms_exact_terminal": True,
        "same_opaque_dev64_ids": True,
        "mapping_path_opened_or_hashed": False,
        "evaluator_input_or_result_opened": False,
        "resume_or_selective_rerun_used": False,
        "full220_launch_allowed": False,
        "leaderboard_submission_or_sota_claim": False,
    }
    value["barrier_payload_sha256"] = payload_sha256(value)
    return value


def publish_forward_barrier(root: Path = ROOT) -> dict[str, Any]:
    target = root / FORWARD_BARRIER
    if target.exists() or target.is_symlink():
        raise FileExistsError(target)
    baseline = terminal_arm("baseline")
    candidate = terminal_arm("candidate")
    if baseline is None or candidate is None:
        raise RuntimeError("V2.42.16 mapping barrier lacks both terminal arms")
    value = build_forward_barrier(baseline, candidate, root=root)
    publish_new(target, value)
    return value


def validate_forward_barrier(root: Path = ROOT) -> dict[str, Any]:
    value = read_object(root / FORWARD_BARRIER)
    unsigned = dict(value)
    seal = unsigned.pop("barrier_payload_sha256", None)
    if (
        value.get("role") != "v24216_package_gate_forward_terminal_barrier"
        or value.get("both_forward_arms_exact_terminal") is not True
        or value.get("same_opaque_dev64_ids") is not True
        or value.get("mapping_path_opened_or_hashed") is not False
        or value.get("evaluator_input_or_result_opened") is not False
        or value.get("resume_or_selective_rerun_used") is not False
        or seal != payload_sha256(unsigned)
        or value.get("pair_prepare", {}).get("sha256") != sha256(root / PAIR_PREPARE)
        or value.get("arms", {}).get("baseline") != terminal_arm("baseline")
        or value.get("arms", {}).get("candidate") != terminal_arm("candidate")
    ):
        raise RuntimeError("V2.42.16 forward barrier drifted")
    return value


def validate_r1_evaluator_release(root: Path = ROOT) -> dict[str, Any]:
    """Open only the released seal/provenance after the paired forward barrier."""

    result_path = root / R1_RESULT
    seal_path = root / R1_FINAL_SEAL
    mapping = root / MAPPING
    if any(path.is_symlink() or not path.is_file() for path in (result_path, seal_path, mapping)):
        raise RuntimeError("V2.42.16 R1 evaluator release is absent")
    seal = read_object(seal_path)
    exact = seal.get("exact_terminal_partition") or {}
    if (
        seal.get("role") != "full220_rollout1_finalization_seal"
        or seal.get("released_result")
        != {"path": str(R1_RESULT), "sha256": sha256(result_path)}
        or exact.get("selected") != 220
        or exact.get("terminal") != 220
        or exact.get("exact_terminal_220") is not True
        or exact.get("mapping_or_gold_read") is not False
        or seal.get("mapping_sha256") != sha256(mapping)
    ):
        raise RuntimeError("V2.42.16 R1 evaluator release drifted")
    return {
        "result_sha256": sha256(result_path),
        "finalization_seal_sha256": sha256(seal_path),
        "mapping_sha256": sha256(mapping),
        "exact_terminal_220": True,
        "released_result_bytes_hashed_but_not_parsed": True,
        "metric_values_read": False,
    }


def _evaluate_arm(
    arm: str,
    *,
    root: Path = ROOT,
    runner: Callable[..., subprocess.CompletedProcess[Any]] = subprocess.run,
) -> dict[str, Any]:
    paths = _arm_paths(arm)
    result_path = root / (BASELINE_RESULT if arm == "baseline" else CANDIDATE_RESULT)
    if result_path.exists() or paths["final"].exists() or paths["eval"].exists():
        raise RuntimeError("V2.42.16 evaluator residue forbids resume")
    barrier = validate_forward_barrier(root)
    release = validate_r1_evaluator_release(root)
    _prepare_exact64(
        manifest_path=paths["root"] / "data/runtime_manifest.jsonl",
        mapping_path=root / MAPPING,
        ids_path=paths["ids"],
        runtime_path=paths["out"] / "runtime_predictions.jsonl",
        summary_path=paths["out"] / "run_summary.json",
        out_dir=paths["final"],
        launch_seal_sha256=sha256(root / PAIR_PREPARE),
        freeze_sha256=sha256(paths["freeze"]),
    )
    prepare = _validate_prepare(
        paths["final"] / "prepare_attestation.json",
        manifest=paths["root"] / "data/runtime_manifest.jsonl",
        mapping=root / MAPPING,
        runtime=paths["out"] / "runtime_predictions.jsonl",
        summary=paths["out"] / "run_summary.json",
        freeze_sha256=sha256(paths["freeze"]),
        seal_sha256=sha256(root / PAIR_PREPARE),
    )
    evaluate = [
        str(paths["root"] / ".venv-eval/bin/python"),
        "-I",
        "-B",
        str(root / "scripts/run_official_eval_local.py"),
        "--predictions",
        str(paths["final"] / "official_predictions.jsonl"),
        "--out-dir",
        str(paths["eval"]),
        "--proxy-url",
        "http://127.0.0.1:9878/responses",
        "--model",
        "gpt-5.6-sol",
        "--reasoning-effort",
        "low",
        "--judge-max-output-tokens",
        "8192",
        "--judge-timeout",
        "600",
        "--judge-max-retries",
        "12",
    ]
    if prepare["completed_predictions_exported"] == 0:
        _initialize_empty_evaluator(
            active_root=root,
            evaluate=evaluate,
            predictions=paths["final"] / "official_predictions.jsonl",
        )
        _write_new_text(paths["eval_log"], "{\"event\":\"zero_prediction_evaluator_terminal\"}\n")
    else:
        _run_logged(evaluate, cwd=paths["root"], log=paths["eval_log"], runner=runner)
    evaluator = validate_evaluator_contract(
        paths["eval"] / "run_config.json",
        expected_predictions_path=paths["final"] / "official_predictions.jsonl",
        expected_predictions_sha256=prepare["official_predictions_sha256"],
        expected_selected_count=prepare["completed_predictions_exported"],
    )
    eval_rows = read_jsonl(paths["eval"] / "official_eval_results.jsonl")
    prediction_rows = read_jsonl(paths["final"] / "official_predictions.jsonl")
    validate_committed_eval_rows(
        eval_rows, [str(row["instance_id"]) for row in prediction_rows]
    )
    if len(eval_rows) != len(prediction_rows):
        raise RuntimeError("V2.42.16 evaluator did not commit every selected prediction")
    metrics = _summarize_exact64(
        read_jsonl(paths["final"] / "terminal_outcomes_evaluator_joined.jsonl"),
        eval_rows,
    )
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24216_package_gate_dev64_arm_result",
        "arm": arm,
        "status": "exact64_released_not_full220_not_sota",
        "selected": 64,
        "conservative_denominator": 64,
        "exact_terminal_before_mapping": True,
        "other_arm_exact_terminal_before_mapping": True,
        "failure_as_zero": True,
        "resume_or_selective_rerun_used": False,
        "full220_launch_allowed": False,
        "leaderboard_submission_or_sota_claim": False,
        "metrics": metrics,
        "provenance": {
            "pair_prepare_sha256": sha256(root / PAIR_PREPARE),
            "forward_barrier_sha256": sha256(root / FORWARD_BARRIER),
            "freeze_sha256": sha256(paths["freeze"]),
            "runtime_predictions_sha256": sha256(paths["out"] / "runtime_predictions.jsonl"),
            "run_summary_sha256": sha256(paths["out"] / "run_summary.json"),
            "prepare_attestation_sha256": sha256(paths["final"] / "prepare_attestation.json"),
            "official_eval_results_sha256": sha256(paths["eval"] / "official_eval_results.jsonl"),
            "evaluator_run_contract_sha256": evaluator["run_contract_sha256"],
            "r1_release_sha256": release["result_sha256"],
            "parent_publication_sha256": sha256(root / PARENT_PUBLICATION),
        },
    }
    validate_arm_result(value, arm=arm)
    publish_new(result_path, value)
    return {"value": value, "evaluator": evaluator, "barrier": barrier}


def evaluate_pair_and_gate(
    publication: Mapping[str, Any],
    *,
    root: Path = ROOT,
    runner: Callable[..., subprocess.CompletedProcess[Any]] = subprocess.run,
) -> dict[str, Any]:
    """Evaluate both arms once and publish the immutable aggregate decision."""

    targets = (root / BASELINE_RESULT, root / CANDIDATE_RESULT, root / GATE_DECISION)
    if any(path.exists() or path.is_symlink() for path in targets):
        raise RuntimeError("V2.42.16 aggregate/evaluator residue forbids rerun")
    baseline = _evaluate_arm("baseline", root=root, runner=runner)
    candidate = _evaluate_arm("candidate", root=root, runner=runner)
    evaluator_identity = validate_paired_evaluator_identity(
        baseline["evaluator"], candidate["evaluator"]
    )
    identity = {
        "same_opaque_dev64_ids": True,
        "same_execution_contract": True,
        "same_evaluator_contract": evaluator_identity[
            "all_required_fields_identical"
        ],
        "both_exact_terminal_before_mapping": True,
        "mapping_join_after_both_terminal": True,
        "outcome_or_score_used_for_execution": False,
        "identity_payload_sha256": payload_sha256(evaluator_identity),
    }
    order = publication["joint_package_order"]
    activation = {
        "identity_handoff_only": False,
        "eligible_component_count": len(order["eligible_components"]),
        "all_selected_components_covered_exactly_once": publication[
            "all_selected_components_covered_exactly_once"
        ],
        "single_deepest_cumulative_graph_used": publication[
            "single_deepest_cumulative_graph_used"
        ],
        "component_directory_overlay_used": publication[
            "component_directory_overlay_used"
        ],
        "complete_parent_and_component_regression_rerun": publication[
            "complete_parent_and_component_regression_rerun"
        ],
        "strict_component_activation_validated": publication[
            "strict_component_activation_validated"
        ],
        "silent_component_drop_or_baseline_fallback_used": publication[
            "silent_component_drop_or_baseline_fallback_used"
        ],
    }
    decision = evaluate_package_gate(
        baseline["value"],
        candidate["value"],
        package_activation=activation,
        evaluator_identity=identity,
    )
    decision["provenance"] = {
        "parent_publication": {
            "path": str(PARENT_PUBLICATION),
            "sha256": sha256(root / PARENT_PUBLICATION),
        },
        "pair_prepare": {"path": str(PAIR_PREPARE), "sha256": sha256(root / PAIR_PREPARE)},
        "forward_barrier": {
            "path": str(FORWARD_BARRIER),
            "sha256": sha256(root / FORWARD_BARRIER),
        },
        "baseline_result": {
            "path": str(BASELINE_RESULT),
            "sha256": sha256(root / BASELINE_RESULT),
        },
        "candidate_result": {
            "path": str(CANDIDATE_RESULT),
            "sha256": sha256(root / CANDIDATE_RESULT),
        },
    }
    decision["decision_payload_sha256"] = payload_sha256(
        {key: item for key, item in decision.items() if key != "decision_payload_sha256"}
    )
    publish_new(root / GATE_DECISION, decision)
    return decision


__all__ = [
    "ARM_ROOTS",
    "ARM_TARGETS",
    "BASELINE_RESULT",
    "CANDIDATE_RESULT",
    "FORWARD_BARRIER",
    "GATE_DECISION",
    "PAIR_PREPARE",
    "build_arm_freeze",
    "build_forward_barrier",
    "evaluate_pair_and_gate",
    "execution_template",
    "prepare_pair",
    "publish_forward_barrier",
    "run_forward_arm",
    "sha256",
    "terminal_arm",
    "validate_forward_barrier",
    "validate_pair_prepare",
    "validate_parent_publication",
    "validate_r1_evaluator_release",
]
