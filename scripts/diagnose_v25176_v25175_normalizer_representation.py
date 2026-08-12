#!/usr/bin/env python3
"""Aggregate-only diagnosis and representation design after V2.51.75.

The diagnosis reads only the frozen aggregate/audit and public parser source.
It never opens per-task rows, predictions, questions, package identities,
mapping, gold, evaluator output, score, reward, or credentials.  Synthetic
strings establish parser behavior; they do not identify the natural reject.
"""

from __future__ import annotations

import copy
import csv
import json
import os
import re
import sys
import time
from collections.abc import Mapping, Sequence
from io import StringIO
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24257_score_first_runtime as score  # noqa: E402
from deepwide_agent import v24259_deterministic_table_normalizer as normalizer  # noqa: E402
from deepwide_agent import v25175_production_normalizer_external_contract as contract  # noqa: E402
from scripts import run_v25175_production_normalizer_external as runner  # noqa: E402


DATE = "20260812"
ROLE = "v25176_v25175_normalizer_representation_aggregate_only_diagnosis"
OUTPUT = Path(
    f"results/v25176_v25175_normalizer_representation_diagnosis_v1_{DATE}.json"
)
SOURCE = Path("scripts/diagnose_v25176_v25175_normalizer_representation.py")
TEST = Path("tests/test_diagnose_v25176_v25175_normalizer_representation.py")
PUBLIC_LOADER = Path(
    "external/Marco-Search-Agent/Marco-DeepResearch-Family/DeepWideSearch/"
    "eval/evaluation/data_loader.py"
)
PARSER_SOURCE = Path("src/deepwide_agent/v24257_score_first_runtime.py")
NORMALIZER_SOURCE = Path(
    "src/deepwide_agent/v24259_deterministic_table_normalizer.py"
)
FORBIDDEN_SURFACES = (
    contract.EVALUATOR,
    contract.EVALUATOR_TEST,
    contract.EVALUATOR_PROTOCOL,
    contract.RESULT,
    contract.POSTAUDIT,
    contract.POSTFREEZE_GOLD,
)
COLUMNS = ("Package", "Version", "License", "NeedsCompilation")
SYNTHETIC_VALUES = ("alpha", "1.0", 'MIT "special" | Apache-2.0', "no")
INTERNAL_PIPE = "&#124;"


def _ordinary(relative: Path) -> Path:
    path = ROOT / relative
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(ROOT.resolve())
    ):
        raise RuntimeError("V2.51.76 expected ordinary repository file")
    return path


def _read_json(relative: Path) -> dict[str, Any]:
    value = json.loads(_ordinary(relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.51.76 expected JSON object")
    return value


def _absent(relative: Path) -> bool:
    path = ROOT / relative
    return not path.exists() and not path.is_symlink()


def _render(values: Sequence[str]) -> str:
    return (
        "```markdown\n| "
        + " | ".join(COLUMNS)
        + " |\n| "
        + " | ".join("---" for _ in COLUMNS)
        + " |\n| "
        + " | ".join(values)
        + " |\n```"
    )


def _csv_cell(value: str) -> str:
    text = str(value)
    return '"' + text.replace('"', '""') + '"' if "|" in text or '"' in text else text


def _official_like_cells(markdown: str) -> list[str]:
    """Mirror only the public loader's line/split/CSV table semantics."""

    fenced = str(markdown).replace("```markdown", "").replace("```", "")
    lines = [line.strip() for line in fenced.splitlines()]
    lines = [
        "|".join(part.strip() for part in line.split("|"))
        for line in lines
        if "|" in line and not set(line.strip()).issubset(set("|- :"))
    ]
    if len(lines) != 2:
        raise ValueError("V2.51.76 synthetic loader table drifted")
    rows = list(csv.reader(StringIO("\n".join(lines)), delimiter="|"))
    if len(rows) != 2:
        raise ValueError("V2.51.76 synthetic CSV row drifted")
    header = [value.strip() for value in rows[0] if value.strip()]
    values = [value.strip() for value in rows[1] if value.strip()]
    if header != list(COLUMNS):
        raise ValueError("V2.51.76 synthetic header drifted")
    return values


def representation_experiment() -> dict[str, Any]:
    escaped = list(SYNTHETIC_VALUES)
    escaped[2] = escaped[2].replace("|", r"\|")
    escaped_table = _render(escaped)
    frozen, _diagnostics = normalizer.normalize_candidate_table(
        escaped_table, COLUMNS, unknown_marker="Unknown"
    )
    exact, _errors = score.extract_valid_markdown_table(escaped_table, COLUMNS)

    internal = [value.replace("|", INTERNAL_PIPE) for value in SYNTHETIC_VALUES]
    internal_table = _render(internal)
    internal_exact, _errors = score.extract_valid_markdown_table(
        internal_table, COLUMNS
    )

    quoted_table = _render([_csv_cell(value) for value in SYNTHETIC_VALUES])
    quoted_values = _official_like_cells(quoted_table)
    escaped_values = _official_like_cells(escaped_table)
    loader_normalized = list(SYNTHETIC_VALUES)
    loader_normalized[2] = re.sub(r"\s*\|\s*", "|", loader_normalized[2])
    return {
        "synthetic_case_only": True,
        "frozen_exact_parser_accepts_backslash_escaped_pipe": exact is not None,
        "frozen_normalizer_accepts_backslash_escaped_pipe": frozen is not None,
        "public_loader_semantics_preserve_backslash_escaped_pipe_shape": escaped_values
        == list(SYNTHETIC_VALUES),
        "internal_numeric_entity_is_frozen_parser_compatible": internal_exact
        is not None,
        "internal_numeric_entity_roundtrips_to_semantic_values": [
            value.replace(INTERNAL_PIPE, "|") for value in internal
        ]
        == list(SYNTHETIC_VALUES),
        "csv_quoted_pipe_is_public_loader_column_shape_compatible": len(
            quoted_values
        )
        == len(COLUMNS),
        "csv_quoted_pipe_preserves_nonwhitespace_literal_and_delimiter": quoted_values
        == loader_normalized,
        "public_loader_strips_whitespace_adjacent_to_internal_pipe": quoted_values
        != list(SYNTHETIC_VALUES),
        "csv_quoted_pipe_exactly_preserves_full_cell": quoted_values[2]
        == SYNTHETIC_VALUES[2],
        "html_entity_must_not_be_final_evaluator_representation": True,
    }


def _validate_parents() -> tuple[dict[str, Any], dict[str, Any]]:
    forward = runner.validate_forward_result(_read_json(contract.FORWARD_RESULT))
    audit = _read_json(contract.FORWARD_AUDIT)
    decision = forward["mechanism_decision"]
    authorization = audit.get("authorization") or {}
    if (
        not contract.sealed(audit, "audit_payload_sha256")
        or audit.get("audit_valid") is not True
        or audit.get("findings") != []
        or audit.get("forward_result_sha256")
        != contract.sha256(_ordinary(contract.FORWARD_RESULT))
        or audit.get("task_rows_sha256") != forward.get("task_rows_sha256")
        or audit.get("prediction_freeze_sha256")
        != forward.get("prediction_freeze_sha256")
        or decision.get("normalizer_localization_gate_passed") is not True
        or decision.get("production_reliability_gate_passed") is not True
        or decision.get("normalizer_repair_design") is not True
        or authorization
        != {
            "normalizer_repair_design": True,
            "binding_successor_design": False,
            "postfreeze_external_evaluator_implementation_and_protocol": False,
            "vertical_binding_policy_change": False,
            "deepwidebench_dev64_exact220_or_sota": False,
            "retry_resume_skip_population_replacement_or_selective_revaluation": False,
        }
        or not all(_absent(path) for path in FORBIDDEN_SURFACES)
    ):
        raise RuntimeError("V2.51.76 frozen parent barrier drifted")
    return forward, audit


def build_diagnosis(*, now: int | None = None) -> dict[str, Any]:
    forward, _audit = _validate_parents()
    aggregate = copy.deepcopy(forward["aggregate"])
    expected_dispositions = {
        name: int(name == "exact_table_accepted") * 19
        + int(name == "malformed_row_or_escaped_pipe_reject")
        for name in contract.runtime.observer.DISPOSITION_NAMES
    }
    expected_parser_counts = {
        "pipe_group_count": 20,
        "separator_row_count": 20,
        "header_bound_separator_count": 20,
        "width_bound_separator_count": 20,
        "data_bearing_separator_count": 20,
        "malformed_candidate_count": 1,
        "normalizer_candidate_count": 19,
    }
    if (
        aggregate.get("task_count") != 20
        or aggregate.get("terminal_tasks") != 20
        or aggregate.get("completed_runtime_tasks") != 20
        or aggregate.get("observer_entry_tasks") != 20
        or aggregate.get("observer_completed_tasks") != 20
        or aggregate.get("observer_failure_tasks") != 0
        or aggregate.get("production_model_generated_tasks") != 19
        or aggregate.get("production_fallback_tasks") != 1
        or aggregate.get("disposition_counts") != expected_dispositions
        or aggregate.get("parser_count_totals") != expected_parser_counts
        or aggregate.get("disposition_accounting_error") != 0
        or aggregate.get("parent_behavior_drift_tasks") != 0
        or aggregate.get("positive_signed_credit_count") != 0
    ):
        raise RuntimeError("V2.51.76 aggregate drifted")

    sources = {
        "frozen_parser": PARSER_SOURCE,
        "frozen_normalizer": NORMALIZER_SOURCE,
        "public_official_loader": PUBLIC_LOADER,
    }
    source_hashes = {
        name: contract.sha256(_ordinary(path)) for name, path in sources.items()
    }
    experiment = representation_experiment()
    if not (
        experiment["synthetic_case_only"]
        and not experiment[
            "frozen_exact_parser_accepts_backslash_escaped_pipe"
        ]
        and not experiment[
            "frozen_normalizer_accepts_backslash_escaped_pipe"
        ]
        and not experiment[
            "public_loader_semantics_preserve_backslash_escaped_pipe_shape"
        ]
        and experiment[
            "internal_numeric_entity_is_frozen_parser_compatible"
        ]
        and experiment[
            "internal_numeric_entity_roundtrips_to_semantic_values"
        ]
        and experiment[
            "csv_quoted_pipe_is_public_loader_column_shape_compatible"
        ]
        and experiment[
            "csv_quoted_pipe_preserves_nonwhitespace_literal_and_delimiter"
        ]
        and experiment[
            "public_loader_strips_whitespace_adjacent_to_internal_pipe"
        ]
        and not experiment["csv_quoted_pipe_exactly_preserves_full_cell"]
    ):
        raise RuntimeError("V2.51.76 representation experiment drifted")

    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parents": {
            "forward_result_sha256": contract.sha256(
                _ordinary(contract.FORWARD_RESULT)
            ),
            "forward_audit_sha256": contract.sha256(
                _ordinary(contract.FORWARD_AUDIT)
            ),
            "prediction_freeze_sha256_bound_but_freeze_not_opened": forward[
                "prediction_freeze_sha256"
            ],
            "task_rows_sha256_bound_but_rows_not_opened": forward[
                "task_rows_sha256"
            ],
            "audit_valid": True,
            "normalizer_localization_gate_passed": True,
            "production_reliability_gate_passed": True,
            "normalizer_repair_design_authorized": True,
        },
        "aggregate": aggregate,
        "source_hashes": source_hashes,
        "representation_experiment": experiment,
        "diagnosis": {
            "one_natural_reject_reached_a_valid_header_separator_width_and_data_region": True,
            "aggregate_cannot_distinguish_row_width_mismatch_from_backslash_escaped_pipe": True,
            "natural_reject_is_not_claimed_to_be_an_escaped_pipe": True,
            "backslash_escaped_pipe_is_a_synthetic_reproduced_failure_mode": True,
            "direct_html_entity_final_output_would_change_the_evaluator_visible_literal": True,
            "csv_quoting_preserves_pipe_quote_and_column_shape_but_not_adjacent_whitespace_under_public_loader": True,
            "frozen_internal_parser_requires_a_reversible_pipe_free_transport_representation": True,
            "repair_must_activate_only_on_unambiguous_backslash_escaped_pipe_tables": True,
            "row_width_ambiguity_existing_entity_collision_partial_row_and_mixed_candidate_tables_fail_closed": True,
            "repair_must_preserve_header_row_count_row_order_nonpipe_cells_and_decoded_internal_cell_values": True,
            "fresh_gate_must_measure_any_final_whitespace_canonicalization_effect": True,
            "repair_must_not_change_prompt_search_fetch_model_context_token_wall_or_network_caps": True,
            "fresh_disjoint_external_gate_is_required_before_claiming_natural_fallback_recovery": True,
            "old_v25175_population_must_not_be_retried_resumed_or_reused": True,
            "quality_effect_is_unknown_and_evaluator_remains_forbidden": True,
            "entropy_or_information_gain_signed_credit": 0,
        },
        "content_policy": {
            "decoded_surfaces": [
                "v25175_content_free_aggregate_and_gate_decision",
                "public_frozen_parser_source",
                "public_frozen_normalizer_source",
                "public_official_loader_source",
                "synthetic_parser_strings",
            ],
            "v25175_task_rows_predictions_questions_identities_pages_mapping_gold_evaluator_score_reward_or_credentials_opened": False,
            "network_model_search_fetch_process_or_evaluator_effect": False,
        },
        "authorization": {
            "quote_aware_literal_preserving_normalizer_build_only": True,
            "runtime_integration_or_external_protocol": False,
            "old_population_retry_resume_rerun_or_reuse": False,
            "binding_successor_design": False,
            "vertical_binding_policy_change": False,
            "evaluator_or_quality_result": False,
            "deepwidebench_dev64_exact220_leaderboard_or_sota": False,
        },
        "findings": [],
        "diagnosis_valid": True,
    }
    value["diagnosis_payload_sha256"] = contract.payload_sha256(value)
    return validate_diagnosis(value)


def validate_diagnosis(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("diagnosis_payload_sha256", None)
    forward, _audit = _validate_parents()
    diagnosis = copied.get("diagnosis") or {}
    experiment = copied.get("representation_experiment") or {}
    authorization = copied.get("authorization") or {}
    if (
        copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("parents")
        != {
            "forward_result_sha256": contract.sha256(
                _ordinary(contract.FORWARD_RESULT)
            ),
            "forward_audit_sha256": contract.sha256(
                _ordinary(contract.FORWARD_AUDIT)
            ),
            "prediction_freeze_sha256_bound_but_freeze_not_opened": forward[
                "prediction_freeze_sha256"
            ],
            "task_rows_sha256_bound_but_rows_not_opened": forward[
                "task_rows_sha256"
            ],
            "audit_valid": True,
            "normalizer_localization_gate_passed": True,
            "production_reliability_gate_passed": True,
            "normalizer_repair_design_authorized": True,
        }
        or copied.get("aggregate", {}).get("task_count") != 20
        or copied.get("aggregate", {}).get("production_fallback_tasks") != 1
        or diagnosis.get(
            "aggregate_cannot_distinguish_row_width_mismatch_from_backslash_escaped_pipe"
        )
        is not True
        or diagnosis.get("natural_reject_is_not_claimed_to_be_an_escaped_pipe")
        is not True
        or diagnosis.get("entropy_or_information_gain_signed_credit") != 0
        or experiment.get(
            "csv_quoted_pipe_is_public_loader_column_shape_compatible"
        )
        is not True
        or experiment.get("csv_quoted_pipe_exactly_preserves_full_cell")
        is not False
        or copied.get("source_hashes")
        != {
            "frozen_parser": contract.sha256(_ordinary(PARSER_SOURCE)),
            "frozen_normalizer": contract.sha256(_ordinary(NORMALIZER_SOURCE)),
            "public_official_loader": contract.sha256(_ordinary(PUBLIC_LOADER)),
        }
        or authorization
        != {
            "quote_aware_literal_preserving_normalizer_build_only": True,
            "runtime_integration_or_external_protocol": False,
            "old_population_retry_resume_rerun_or_reuse": False,
            "binding_successor_design": False,
            "vertical_binding_policy_change": False,
            "evaluator_or_quality_result": False,
            "deepwidebench_dev64_exact220_leaderboard_or_sota": False,
        }
        or copied.get("findings") != []
        or copied.get("diagnosis_valid") is not True
        or seal != contract.payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.51.76 diagnosis drifted")
    return copied


def publish_exclusive(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def main() -> None:
    value = build_diagnosis()
    publish_exclusive(ROOT / OUTPUT, value)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "role": ROLE,
                "diagnosis_valid": value["diagnosis_valid"],
                "authorization": value["authorization"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
