from __future__ import annotations

import copy
import json
import multiprocessing
import os
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from deepwide_agent.v24232_webswarm_total_budget import (  # noqa: E402
    build_cost_vector,
    object_sha256,
)
from deepwide_agent.v24233_webswarm_effect_preauthorization import (  # noqa: E402
    initialize_effect_preauthorization_state,
    issue_effect_permit,
    settle_effect_permit,
)
from deepwide_agent.v24241_durable_preauthorization_journal import (  # noqa: E402
    ACTIVE_FORWARD_INTEGRATION_AUTHORIZED,
    ACTIVE_HARNESS_DURABILITY_INTEGRATED,
    BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED,
    DEV64_OR_EXACT220_LAUNCH_AUTHORIZED,
    EXTERNAL_SIDE_EFFECT_AUTHORIZED,
    LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED,
    PRODUCTION_PACKAGE_AUTHORIZED,
    SHARED_API_LEASE_ACQUIRE_AUTHORIZED,
    DurableJournalCASConflict,
    DurableJournalPoisoned,
    DurablePreauthorizationJournal,
)
from tests.test_v24232_webswarm_total_budget import (  # noqa: E402
    contract,
    digest,
    guidance,
    ledger,
)


def cost(**overrides: int) -> dict[str, int]:
    values = {
        "model_calls": 1,
        "model_attempts": 2,
        "search_calls": 3,
        "fetch_calls": 4,
        "other_tool_calls": 1,
        "orchestrator_calls": 1,
        "input_tokens": 500,
        "output_tokens": 100,
        "wall_milliseconds": 10_000,
    }
    values.update(overrides)
    return build_cost_vector(**values)


def append_worker(
    root: str,
    namespace: str,
    shared: dict[str, object],
    expected_state_sha256: str,
    current_state: dict[str, object],
    gate,
    outcomes,
) -> None:
    journal = DurablePreauthorizationJournal(
        root=Path(root),
        journal_namespace_sha256=namespace,
        **shared,
    )
    gate.wait(timeout=10)
    try:
        result = journal.compare_and_append(
            expected_state_sha256=expected_state_sha256,
            current_state=current_state,
        )
    except DurableJournalCASConflict:
        outcomes.put(("conflict", None))
    except BaseException as error:  # pragma: no cover - reported to parent
        outcomes.put(("error", type(error).__name__))
    else:
        outcomes.put(("committed", result["resulting_state_sha256"]))


class InjectedCrash(RuntimeError):
    pass


class V24241DurablePreauthorizationJournalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(dir=ROOT)
        self.root = Path(self.temporary.name).resolve()
        self.budget = contract()
        self.policy, _, arms, self.sources = guidance(self.budget)
        self.arm = next(arm for arm in arms if arm["arm_name"] == "full")
        self.source = self.sources["full"]
        self.initial = initialize_effect_preauthorization_state(
            initial_budget_ledger=ledger(
                self.budget,
                self.policy,
                self.arm,
                self.source,
            ),
            **self.shared,
        )
        self.journal = self.new_journal("main")
        self.journal.initialize(self.initial)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    @property
    def shared(self) -> dict[str, object]:
        return {
            "contract": self.budget,
            "guidance_policy": self.policy,
            "guidance_arm": self.arm,
            "scouts": self.source["scouts"],
            "probe": self.source["probe"],
            "experience": self.source["experience"],
        }

    def new_journal(self, suffix: str) -> DurablePreauthorizationJournal:
        return DurablePreauthorizationJournal(
            root=self.root,
            journal_namespace_sha256=digest(f"journal-{suffix}"),
            **self.shared,
        )

    def initialized_journal(self, suffix: str) -> DurablePreauthorizationJournal:
        journal = self.new_journal(suffix)
        journal.initialize(self.initial)
        return journal

    def issue(
        self,
        previous: dict[str, object] | None = None,
        *,
        suffix: str = "1",
    ) -> dict[str, object]:
        return issue_effect_permit(
            self.initial if previous is None else previous,
            **self.shared,
            permit_ref_sha256=digest(f"permit-{suffix}"),
            charge_kind="fanout_execution",
            charge_ref_sha256=digest(f"charge-{suffix}"),
            estimate_source_sha256=digest(f"estimate-{suffix}"),
            reserved_cost=cost(),
        )

    def settle(
        self,
        previous: dict[str, object],
        *,
        permit_suffix: str = "1",
        suffix: str = "1",
    ) -> dict[str, object]:
        return settle_effect_permit(
            previous,
            **self.shared,
            permit_ref_sha256=digest(f"permit-{permit_suffix}"),
            effect_receipt_sha256=digest(f"effect-{suffix}"),
            actual_cost_source_sha256=digest(f"actual-{suffix}"),
            actual_cost=cost(
                model_attempts=1,
                search_calls=2,
                fetch_calls=3,
                other_tool_calls=0,
                input_tokens=400,
                output_tokens=80,
                wall_milliseconds=8_000,
            ),
        )

    @staticmethod
    def crash_at(stage: str):
        def hook(current: str) -> None:
            if current == stage:
                raise InjectedCrash(stage)

        return hook

    def append(
        self,
        journal: DurablePreauthorizationJournal,
        previous: dict[str, object],
        current: dict[str, object],
        *,
        fault_hook=None,
    ) -> dict[str, object]:
        return journal.compare_and_append(
            expected_state_sha256=str(previous["state_sha256"]),
            current_state=current,
            fault_hook=fault_hook,
        )

    def test_initialize_load_and_content_free_status(self) -> None:
        loaded = self.journal.load()
        self.assertEqual(loaded, self.initial)
        status = self.journal.status()
        self.assertEqual(status["generation"], 0)
        self.assertEqual(status["current_state_sha256"], self.initial["state_sha256"])
        self.assertIsNone(status["last_entry_sha256"])
        self.assertEqual(status["pending_permit_count"], 0)
        self.assertEqual(status["recovered_pending_file_count"], 0)
        self.assertNotIn("initial_state", status)
        self.assertNotIn("events", status)
        with self.assertRaises(FileExistsError):
            self.journal.initialize(self.initial)

    def test_permit_and_settlement_append_replay_exactly(self) -> None:
        issued = self.issue()
        first = self.append(self.journal, self.initial, issued)
        self.assertEqual(first["generation"], 1)
        self.assertEqual(self.journal.load(), issued)

        settled = self.settle(issued)
        second = self.append(self.journal, issued, settled)
        self.assertEqual(second["generation"], 2)
        self.assertEqual(self.journal.load(), settled)
        status = self.journal.status()
        self.assertEqual(status["generation"], 2)
        self.assertEqual(status["pending_permit_count"], 0)

    def test_entry_is_incremental_and_does_not_duplicate_full_state(self) -> None:
        issued = self.issue()
        self.append(self.journal, self.initial, issued)
        entry_path = self.journal.entries_directory / f"{1:020d}.json"
        entry = json.loads(entry_path.read_text(encoding="utf-8"))
        self.assertEqual(entry["transition_event"], issued["events"][-1])
        self.assertEqual(entry["previous_state_sha256"], self.initial["state_sha256"])
        self.assertEqual(entry["resulting_state_sha256"], issued["state_sha256"])
        for forbidden in (
            "initial_state",
            "initial_budget_ledger",
            "current_budget_ledger",
            "events",
            "pending_permit_refs",
        ):
            self.assertNotIn(forbidden, entry)

    def test_stale_compare_and_swap_is_rejected_without_new_generation(self) -> None:
        issued = self.issue(suffix="winner")
        self.append(self.journal, self.initial, issued)
        stale = self.issue(suffix="stale")
        with self.assertRaisesRegex(DurableJournalCASConflict, "stale"):
            self.append(self.journal, self.initial, stale)
        self.assertEqual(self.journal.load(), issued)
        self.assertEqual(
            sorted(path.name for path in self.journal.entries_directory.iterdir()),
            [f"{1:020d}.json"],
        )

    def test_two_process_same_state_contention_commits_exactly_one(self) -> None:
        if "fork" not in multiprocessing.get_all_start_methods():
            self.skipTest("requires POSIX fork and flock")
        context = multiprocessing.get_context("fork")
        gate = context.Barrier(2)
        outcomes = context.Queue()
        first = self.issue(suffix="process-a")
        second = self.issue(suffix="process-b")
        processes = [
            context.Process(
                target=append_worker,
                args=(
                    str(self.root),
                    self.journal.namespace,
                    self.shared,
                    str(self.initial["state_sha256"]),
                    current,
                    gate,
                    outcomes,
                ),
            )
            for current in (first, second)
        ]
        for process in processes:
            process.start()
        for process in processes:
            process.join(timeout=15)
            self.assertFalse(process.is_alive())
            self.assertEqual(process.exitcode, 0)
        observed = sorted(outcomes.get(timeout=5)[0] for _ in processes)
        self.assertEqual(observed, ["committed", "conflict"])
        loaded = self.journal.load()
        self.assertIn(loaded["state_sha256"], {first["state_sha256"], second["state_sha256"]})
        self.assertEqual(loaded["event_count"], 1)

    def test_crash_after_pending_fsync_promotes_unique_complete_entry(self) -> None:
        issued = self.issue(suffix="pending-crash")
        with self.assertRaisesRegex(InjectedCrash, "pending"):
            self.append(
                self.journal,
                self.initial,
                issued,
                fault_hook=self.crash_at("after_pending_directory_fsync"),
            )
        status = self.journal.status()
        self.assertEqual(status["recovered_pending_file_count"], 1)
        self.assertEqual(status["current_state_sha256"], issued["state_sha256"])
        self.assertEqual(self.journal.load(), issued)
        self.assertEqual(
            sorted(path.name for path in self.journal.entries_directory.iterdir()),
            [f"{1:020d}.json"],
        )

    def test_crash_after_final_fsync_cleans_duplicate_link(self) -> None:
        issued = self.issue(suffix="linked-crash")
        with self.assertRaisesRegex(InjectedCrash, "final"):
            self.append(
                self.journal,
                self.initial,
                issued,
                fault_hook=self.crash_at("after_final_directory_fsync"),
            )
        names = sorted(path.name for path in self.journal.entries_directory.iterdir())
        self.assertEqual(len(names), 2)
        status = self.journal.status()
        self.assertEqual(status["recovered_pending_file_count"], 1)
        final_path = self.journal.entries_directory / f"{1:020d}.json"
        self.assertEqual(final_path.stat().st_nlink, 1)
        self.assertEqual(self.journal.load(), issued)

    def test_crash_after_cleanup_reports_error_but_commit_is_recoverable(self) -> None:
        issued = self.issue(suffix="cleanup-crash")
        with self.assertRaisesRegex(InjectedCrash, "cleanup"):
            self.append(
                self.journal,
                self.initial,
                issued,
                fault_hook=self.crash_at("after_cleanup_directory_fsync"),
            )
        status = self.journal.status()
        self.assertEqual(status["recovered_pending_file_count"], 0)
        self.assertEqual(status["current_state_sha256"], issued["state_sha256"])

    def test_partial_and_ambiguous_pending_entries_poison(self) -> None:
        partial = self.initialized_journal("partial-pending")
        partial_path = partial.entries_directory / (
            f".pending-{1:020d}-{digest('partial-seal')}.json"
        )
        partial_path.write_bytes(b'{"incomplete":')
        with self.assertRaises(DurableJournalPoisoned):
            partial.load()

        ambiguous = self.initialized_journal("ambiguous-pending")
        for suffix in ("a", "b"):
            path = ambiguous.entries_directory / (
                f".pending-{1:020d}-{digest('ambiguous-' + suffix)}.json"
            )
            path.write_text("{}\n", encoding="utf-8")
        with self.assertRaisesRegex(DurableJournalPoisoned, "ambiguous"):
            ambiguous.load()

    def test_generation_zero_pending_is_poison_not_internal_key_error(self) -> None:
        path = self.journal.entries_directory / (
            f".pending-{0:020d}-{digest('zero-generation')}.json"
        )
        path.write_text("{}\n", encoding="utf-8")
        with self.assertRaises(DurableJournalPoisoned):
            self.journal.load()

    def test_content_equal_published_pending_must_be_same_hard_link(self) -> None:
        issued = self.issue(suffix="copied-pending")
        commit = self.append(self.journal, self.initial, issued)
        final_path = self.journal.entries_directory / f"{1:020d}.json"
        pending_path = self.journal.entries_directory / (
            f".pending-{1:020d}-{commit['entry_sha256']}.json"
        )
        pending_path.write_bytes(final_path.read_bytes())
        self.assertFalse(pending_path.samefile(final_path))
        with self.assertRaisesRegex(DurableJournalPoisoned, "not the final link"):
            self.journal.load()

    def test_unexpected_residue_and_generation_gap_poison(self) -> None:
        residue = self.initialized_journal("residue")
        (residue.entries_directory / "unexpected.tmp").write_text(
            "residue",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(DurableJournalPoisoned, "residue"):
            residue.load()

        gap = self.initialized_journal("gap")
        issued = self.issue(suffix="gap")
        self.append(gap, self.initial, issued)
        (gap.entries_directory / f"{1:020d}.json").rename(
            gap.entries_directory / f"{2:020d}.json"
        )
        with self.assertRaisesRegex(DurableJournalPoisoned, "contiguous"):
            gap.load()

    def test_entry_tamper_symlink_and_external_hardlink_poison(self) -> None:
        tampered = self.initialized_journal("tamper")
        issued = self.issue(suffix="tamper")
        self.append(tampered, self.initial, issued)
        tampered_path = tampered.entries_directory / f"{1:020d}.json"
        value = json.loads(tampered_path.read_text(encoding="utf-8"))
        value["resulting_state_sha256"] = digest("forged-result")
        tampered_path.write_text(json.dumps(value) + "\n", encoding="utf-8")
        with self.assertRaises(DurableJournalPoisoned):
            tampered.load()

        symlinked = self.initialized_journal("symlink")
        symlink_state = self.issue(suffix="symlink")
        self.append(symlinked, self.initial, symlink_state)
        symlink_path = symlinked.entries_directory / f"{1:020d}.json"
        symlink_path.unlink()
        os.symlink(symlinked.initial_path, symlink_path)
        with self.assertRaises(DurableJournalPoisoned):
            symlinked.load()

        hardlinked = self.initialized_journal("hardlink")
        hardlink_state = self.issue(suffix="hardlink")
        self.append(hardlinked, self.initial, hardlink_state)
        hardlink_path = hardlinked.entries_directory / f"{1:020d}.json"
        os.link(hardlink_path, self.root / "external-hardlink.json")
        with self.assertRaisesRegex(DurableJournalPoisoned, "link count"):
            hardlinked.load()

    def test_resealed_invalid_event_and_initial_state_are_poisoned(self) -> None:
        invalid_event = self.initialized_journal("invalid-event")
        issued = self.issue(suffix="invalid-event")
        self.append(invalid_event, self.initial, issued)
        entry_path = invalid_event.entries_directory / f"{1:020d}.json"
        entry = json.loads(entry_path.read_text(encoding="utf-8"))
        entry["transition_event"]["role"] = "invalid-transition-role"
        entry.pop("entry_sha256")
        entry["entry_sha256"] = object_sha256(entry)
        entry_path.write_text(json.dumps(entry) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(DurableJournalPoisoned, "event seal"):
            invalid_event.load()

        invalid_initial = self.initialized_journal("invalid-initial")
        record = json.loads(invalid_initial.initial_path.read_text(encoding="utf-8"))
        record["initial_state"]["unexpected"] = False
        record["initial_state"].pop("state_sha256")
        record["initial_state"]["state_sha256"] = object_sha256(
            record["initial_state"]
        )
        record["initial_state_sha256"] = record["initial_state"]["state_sha256"]
        record.pop("initial_sha256")
        record["initial_sha256"] = object_sha256(record)
        invalid_initial.initial_path.write_text(
            json.dumps(record) + "\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(DurableJournalPoisoned, "validation failed"):
            invalid_initial.load()

    def test_lock_symlink_and_hardlink_poison_before_replay(self) -> None:
        symlinked = self.initialized_journal("lock-symlink")
        symlinked.lock_path.unlink()
        os.symlink(symlinked.initial_path, symlinked.lock_path)
        with self.assertRaisesRegex(DurableJournalPoisoned, "opened safely"):
            symlinked.load()

        hardlinked = self.initialized_journal("lock-hardlink")
        os.link(hardlinked.lock_path, self.root / "external-lock-link")
        with self.assertRaisesRegex(DurableJournalPoisoned, "lock file"):
            hardlinked.load()

    def test_initialization_partial_write_remains_fail_closed_poison(self) -> None:
        journal = self.new_journal("initialization-crash")

        def partial_write(path, value) -> None:
            del value
            path.write_bytes(b'{"partial":')
            raise InjectedCrash("initial publication")

        with mock.patch(
            "deepwide_agent.v24241_durable_preauthorization_journal._publish_new",
            side_effect=partial_write,
        ):
            with self.assertRaisesRegex(InjectedCrash, "initial publication"):
                journal.initialize(self.initial)
        with self.assertRaises(FileExistsError):
            journal.initialize(self.initial)
        with self.assertRaises(DurableJournalPoisoned):
            journal.load()

    def test_invalid_transition_does_not_publish_pending_or_final_bytes(self) -> None:
        issued = self.issue(suffix="invalid")
        invalid = copy.deepcopy(issued)
        invalid["state_sha256"] = digest("invalid-state")
        with self.assertRaises(ValueError):
            self.append(self.journal, self.initial, invalid)
        self.assertEqual(list(self.journal.entries_directory.iterdir()), [])
        self.assertEqual(self.journal.load(), self.initial)

    def test_caller_mutation_during_lock_wait_cannot_change_validated_candidate(self) -> None:
        issued = self.issue(suffix="mutable-candidate")
        lock_entered = threading.Event()
        continue_lock = threading.Event()
        original_locked = self.journal._locked

        def delayed_locked():
            manager = original_locked()

            class Delayed:
                def __enter__(self_inner):
                    value = manager.__enter__()
                    lock_entered.set()
                    continue_lock.wait(timeout=10)
                    return value

                def __exit__(self_inner, *args):
                    return manager.__exit__(*args)

            return Delayed()

        outcome: list[object] = []

        def append_candidate() -> None:
            try:
                outcome.append(self.append(self.journal, self.initial, issued))
            except BaseException as error:  # pragma: no cover - asserted below
                outcome.append(error)

        with mock.patch.object(self.journal, "_locked", side_effect=delayed_locked):
            worker = threading.Thread(target=append_candidate)
            worker.start()
            self.assertTrue(lock_entered.wait(timeout=10))
            issued["state_sha256"] = digest("caller-mutated-after-entry")
            continue_lock.set()
            worker.join(timeout=10)
        self.assertFalse(worker.is_alive())
        self.assertEqual(len(outcome), 1)
        self.assertIsInstance(outcome[0], dict)
        loaded = self.journal.load()
        self.assertNotEqual(loaded["state_sha256"], issued["state_sha256"])
        self.assertEqual(loaded["event_count"], 1)

    def test_all_runtime_and_benchmark_authorizations_remain_false(self) -> None:
        for authorization in (
            PRODUCTION_PACKAGE_AUTHORIZED,
            ACTIVE_FORWARD_INTEGRATION_AUTHORIZED,
            EXTERNAL_SIDE_EFFECT_AUTHORIZED,
            BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED,
            DEV64_OR_EXACT220_LAUNCH_AUTHORIZED,
            SHARED_API_LEASE_ACQUIRE_AUTHORIZED,
            LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED,
            ACTIVE_HARNESS_DURABILITY_INTEGRATED,
        ):
            self.assertFalse(authorization)


if __name__ == "__main__":
    unittest.main()
