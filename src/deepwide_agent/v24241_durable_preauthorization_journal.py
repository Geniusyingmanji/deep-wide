"""Crash-recoverable local journal for V2.42.33 state transitions.

The V2.42.35 harness serializes mutations only inside one Python process.  This
candidate store supplies a narrower missing primitive: cooperative processes
on one local POSIX filesystem serialize through ``flock``, compare an expected
V2.42.33 state hash under that lock, and publish exactly one immutable
generation file.  The initial state is stored once; each later file contains
only the appended V2.42.33 event and the before/after state hashes.

Publication uses a content-bound pending file, file and directory ``fsync``,
and a no-clobber hard link.  A complete pending entry is recovered after a
crash; a partial, ambiguous, or unexpected file poisons the journal and blocks
further writes.  The immutable generation sequence, not a mutable HEAD file,
is authoritative.

This is not a distributed lock, a hardware durability attestation, an
independent transparency log, or protection from a malicious same-user writer
who can reseal JSON.  It is not connected to the active harness, clients,
runner, launcher, benchmark, or evaluator and authorizes no external effect.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import stat
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping, Sequence

from deepwide_agent.v24232_webswarm_total_budget import object_sha256
from deepwide_agent.v24233_webswarm_effect_preauthorization import (
    PERMIT_ROLE,
    SETTLEMENT_ROLE,
    issue_effect_permit,
    settle_effect_permit,
    validate_effect_preauthorization_state,
    validate_effect_preauthorization_transition,
)


POLICY_ID = "v24241_durable_preauthorization_journal_v1"
INITIAL_ROLE = "v24241_durable_preauthorization_initial"
ENTRY_ROLE = "v24241_durable_preauthorization_entry"

PRODUCTION_PACKAGE_AUTHORIZED = False
ACTIVE_FORWARD_INTEGRATION_AUTHORIZED = False
EXTERNAL_SIDE_EFFECT_AUTHORIZED = False
BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED = False
DEV64_OR_EXACT220_LAUNCH_AUTHORIZED = False
SHARED_API_LEASE_ACQUIRE_AUTHORIZED = False
LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED = False

LOCAL_POSIX_ADVISORY_LOCK_IMPLEMENTED = True
CROSS_PROCESS_CAS_FOR_COOPERATING_WRITERS_IMPLEMENTED = True
IMMUTABLE_NO_CLOBBER_GENERATION_FILES_IMPLEMENTED = True
CONTENT_BOUND_PENDING_RECOVERY_IMPLEMENTED = True
FILE_AND_DIRECTORY_FSYNC_IMPLEMENTED = True
INCREMENTAL_EVENT_STORAGE_IMPLEMENTED = True
CRASH_RECOVERY_AFTER_INITIALIZATION_IMPLEMENTED = True
INITIALIZATION_CRASH_AUTOMATIC_RECOVERY_IMPLEMENTED = False
NETWORK_OR_DISTRIBUTED_FILESYSTEM_SEMANTICS_PROVEN = False
HARDWARE_STABLE_STORAGE_INDEPENDENTLY_ATTESTED = False
MALICIOUS_SAME_USER_RESEALING_EXCLUDED = False
INDEPENDENT_APPEND_ONLY_TRANSPARENCY_LOG_USED = False
ACTIVE_HARNESS_DURABILITY_INTEGRATED = False

INITIAL_FILE = "initial.json"
LOCK_FILE = "journal.lock"
ENTRIES_DIRECTORY = "entries"
FINAL_NAME = re.compile(r"^(?P<generation>[0-9]{20})\.json$")
PENDING_NAME = re.compile(
    r"^\.pending-(?P<generation>[0-9]{20})-(?P<seal>[0-9a-f]{64})\.json$"
)
MAX_FILE_BYTES = 128_000_000
MAX_GENERATIONS = 1_000_000

INITIAL_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "journal_namespace_sha256",
        "contract_sha256",
        "guidance_policy_sha256",
        "arm_name",
        "arm_sha256",
        "generation",
        "initial_state",
        "initial_state_sha256",
        "incremental_event_storage",
        "external_side_effect_authorized",
        "active_forward_integration_authorized",
        "benchmark_forward_or_evaluator_authorized",
        "initial_sha256",
    }
)
ENTRY_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "journal_namespace_sha256",
        "generation",
        "previous_entry_sha256",
        "previous_state_sha256",
        "transition_event",
        "transition_event_sha256",
        "resulting_state_sha256",
        "local_posix_advisory_lock_held_when_published",
        "immutable_generation_file_created_no_clobber",
        "file_and_directory_fsync_attempted",
        "independent_append_only_transparency_log_used",
        "hardware_stable_storage_independently_attested",
        "network_or_distributed_filesystem_semantics_proven",
        "malicious_same_user_resealing_excluded",
        "active_harness_durability_integrated",
        "external_side_effect_authorized",
        "active_forward_integration_authorized",
        "benchmark_forward_or_evaluator_authorized",
        "entry_sha256",
    }
)


class DurableJournalError(RuntimeError):
    """Safe base error without journal payload content."""


class DurableJournalCASConflict(DurableJournalError):
    """The caller's expected state is no longer current."""


class DurableJournalPoisoned(DurableJournalError):
    """Unexpected, partial, or ambiguous durable bytes block progress."""


def _clone(value: object) -> Any:
    return json.loads(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    )


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _sha256(value: object, *, label: str) -> str:
    if not _is_sha256(value):
        raise ValueError(f"V2.42.41 {label} is not SHA-256")
    return str(value)


def _exact(value: Mapping[str, Any], *, keys: frozenset[str], label: str) -> None:
    if not isinstance(value, Mapping) or set(value) != keys:
        raise DurableJournalPoisoned(f"V2.42.41 {label} schema drifted")


def _sealed(value: Mapping[str, Any], *, key: str) -> bool:
    seal = value.get(key)
    if not _is_sha256(seal):
        return False
    unsigned = dict(value)
    unsigned.pop(key)
    return seal == object_sha256(unsigned)


def _event_sha256(event: Mapping[str, Any]) -> str:
    if event.get("role") == PERMIT_ROLE:
        return _sha256(event.get("permit_sha256"), label="permit event seal")
    if event.get("role") == SETTLEMENT_ROLE:
        return _sha256(event.get("settlement_sha256"), label="settlement event seal")
    raise ValueError("V2.42.41 transition event role is invalid")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise DurableJournalPoisoned("V2.42.41 duplicate JSON key rejected")
        value[key] = item
    return value


def _reject_constant(value: str) -> None:
    raise DurableJournalPoisoned("V2.42.41 non-finite JSON constant rejected")


def _encoded(value: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def _ordinary_directory(path: Path, *, label: str) -> Path:
    candidate = path.absolute()
    try:
        metadata = path.lstat()
    except FileNotFoundError as error:
        raise ValueError(f"V2.42.41 {label} is absent") from error
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or path.is_symlink()
        or path.resolve(strict=True) != candidate
    ):
        raise ValueError(f"V2.42.41 {label} is not an ordinary directory")
    return candidate


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _read_object(path: Path, *, allow_link_count_two: bool = False) -> dict[str, Any]:
    try:
        metadata = path.lstat()
    except FileNotFoundError as error:
        raise DurableJournalPoisoned("V2.42.41 required journal file is absent") from error
    allowed_links = {1, 2} if allow_link_count_two else {1}
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_nlink not in allowed_links
        or metadata.st_size > MAX_FILE_BYTES
    ):
        raise DurableJournalPoisoned("V2.42.41 journal file is nonordinary")
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    payload = bytearray()
    try:
        opened = os.fstat(descriptor)
        if (
            not stat.S_ISREG(opened.st_mode)
            or opened.st_nlink not in allowed_links
            or opened.st_dev != metadata.st_dev
            or opened.st_ino != metadata.st_ino
            or opened.st_size != metadata.st_size
        ):
            raise DurableJournalPoisoned("V2.42.41 journal file changed during open")
        while len(payload) <= MAX_FILE_BYTES:
            chunk = os.read(
                descriptor,
                min(65_536, MAX_FILE_BYTES + 1 - len(payload)),
            )
            if not chunk:
                break
            payload.extend(chunk)
        if len(payload) > MAX_FILE_BYTES or os.read(descriptor, 1):
            raise DurableJournalPoisoned("V2.42.41 journal file exceeds size cap")
        final = os.fstat(descriptor)
        if (
            final.st_dev != opened.st_dev
            or final.st_ino != opened.st_ino
            or final.st_size != opened.st_size
            or final.st_mtime_ns != opened.st_mtime_ns
            or final.st_ctime_ns != opened.st_ctime_ns
        ):
            raise DurableJournalPoisoned("V2.42.41 journal file changed during read")
    finally:
        os.close(descriptor)
    try:
        value = json.loads(
            bytes(payload).decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise DurableJournalPoisoned("V2.42.41 journal JSON is invalid") from error
    if not isinstance(value, dict):
        raise DurableJournalPoisoned("V2.42.41 journal value is not an object")
    return value


def _publish_new(path: Path, value: Mapping[str, Any]) -> None:
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(_encoded(value))
            handle.flush()
            os.fsync(handle.fileno())
        _fsync_directory(path.parent)
    except BaseException:
        try:
            os.close(descriptor)
        except OSError:
            pass
        raise


class DurablePreauthorizationJournal:
    """Persist one V2.42.33 transition chain below a fixed namespace."""

    def __init__(
        self,
        *,
        root: Path,
        journal_namespace_sha256: str,
        contract: Mapping[str, Any],
        guidance_policy: Mapping[str, Any],
        guidance_arm: Mapping[str, Any],
        scouts: Sequence[Mapping[str, Any]],
        probe: Mapping[str, Any] | None,
        experience: Mapping[str, Any] | None,
    ) -> None:
        self.root = _ordinary_directory(root, label="store root")
        self.namespace = _sha256(
            journal_namespace_sha256,
            label="journal namespace",
        )
        self.directory = self.root / self.namespace
        self.lock_path = self.directory / LOCK_FILE
        self.initial_path = self.directory / INITIAL_FILE
        self.entries_directory = self.directory / ENTRIES_DIRECTORY
        self._shared = {
            "contract": _clone(dict(contract)),
            "guidance_policy": _clone(dict(guidance_policy)),
            "guidance_arm": _clone(dict(guidance_arm)),
            "scouts": _clone(list(scouts)),
            "probe": _clone(probe),
            "experience": _clone(experience),
        }

    def _initial_record(self, state: Mapping[str, Any]) -> dict[str, Any]:
        validate_effect_preauthorization_state(state, **self._shared)
        if state.get("event_count") != 0 or state.get("events") != []:
            raise ValueError("V2.42.41 initial state must be pristine")
        value: dict[str, Any] = {
            "artifact_version": 1,
            "role": INITIAL_ROLE,
            "policy_id": POLICY_ID,
            "journal_namespace_sha256": self.namespace,
            "contract_sha256": self._shared["contract"]["contract_sha256"],
            "guidance_policy_sha256": self._shared["guidance_policy"]["policy_sha256"],
            "arm_name": self._shared["guidance_arm"]["arm_name"],
            "arm_sha256": self._shared["guidance_arm"]["arm_sha256"],
            "generation": 0,
            "initial_state": _clone(dict(state)),
            "initial_state_sha256": state["state_sha256"],
            "incremental_event_storage": True,
            "external_side_effect_authorized": False,
            "active_forward_integration_authorized": False,
            "benchmark_forward_or_evaluator_authorized": False,
        }
        value["initial_sha256"] = object_sha256(value)
        return value

    def initialize(self, initial_state: Mapping[str, Any]) -> dict[str, Any]:
        """Reserve a pristine namespace and durably publish generation zero."""

        record = self._initial_record(initial_state)
        if self.directory.exists() or self.directory.is_symlink():
            raise FileExistsError("V2.42.41 journal namespace is not pristine")
        os.mkdir(self.directory, 0o700)
        _fsync_directory(self.root)
        try:
            os.mkdir(self.entries_directory, 0o700)
            descriptor = os.open(
                self.lock_path,
                os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                0o600,
            )
            os.close(descriptor)
            _fsync_directory(self.directory)
            _publish_new(self.initial_path, record)
        except BaseException:
            # A reserved but incomplete namespace remains as fail-closed poison.
            raise
        return _clone(record)

    def _require_layout(self) -> None:
        _ordinary_directory(self.directory, label="journal directory")
        _ordinary_directory(self.entries_directory, label="entries directory")
        expected = {self.lock_path, self.initial_path, self.entries_directory}
        if set(self.directory.iterdir()) != expected:
            raise DurableJournalPoisoned("V2.42.41 journal directory contains residue")

    @contextmanager
    def _locked(self) -> Iterator[None]:
        self._require_layout()
        try:
            descriptor = os.open(self.lock_path, os.O_RDWR | os.O_NOFOLLOW)
        except OSError as error:
            raise DurableJournalPoisoned(
                "V2.42.41 lock file cannot be opened safely"
            ) from error
        try:
            metadata = os.fstat(descriptor)
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
                raise DurableJournalPoisoned("V2.42.41 lock file is nonordinary")
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            self._require_layout()
            yield
        finally:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
            finally:
                os.close(descriptor)

    def _load_initial(self) -> dict[str, Any]:
        record = _read_object(self.initial_path)
        _exact(record, keys=INITIAL_KEYS, label="initial record")
        state = record.get("initial_state")
        if (
            record.get("role") != INITIAL_ROLE
            or record.get("policy_id") != POLICY_ID
            or record.get("journal_namespace_sha256") != self.namespace
            or record.get("contract_sha256")
            != self._shared["contract"]["contract_sha256"]
            or record.get("guidance_policy_sha256")
            != self._shared["guidance_policy"]["policy_sha256"]
            or record.get("arm_name") != self._shared["guidance_arm"]["arm_name"]
            or record.get("arm_sha256") != self._shared["guidance_arm"]["arm_sha256"]
            or record.get("generation") != 0
            or not isinstance(state, Mapping)
            or record.get("initial_state_sha256") != state.get("state_sha256")
            or record.get("incremental_event_storage") is not True
            or record.get("external_side_effect_authorized") is not False
            or record.get("active_forward_integration_authorized") is not False
            or record.get("benchmark_forward_or_evaluator_authorized") is not False
            or not _sealed(record, key="initial_sha256")
        ):
            raise DurableJournalPoisoned("V2.42.41 initial record drifted")
        try:
            validate_effect_preauthorization_state(state, **self._shared)
        except (KeyError, TypeError, ValueError) as error:
            raise DurableJournalPoisoned(
                "V2.42.41 initial state validation failed"
            ) from error
        if state.get("event_count") != 0 or state.get("events") != []:
            raise DurableJournalPoisoned("V2.42.41 initial state is not pristine")
        return _clone(dict(state))

    def _entry_record(
        self,
        *,
        previous_state: Mapping[str, Any],
        current_state: Mapping[str, Any],
        previous_entry_sha256: str | None,
    ) -> dict[str, Any]:
        validate_effect_preauthorization_transition(
            previous_state,
            current_state,
            **self._shared,
        )
        generation = int(current_state["event_count"])
        if not 1 <= generation <= MAX_GENERATIONS:
            raise ValueError("V2.42.41 generation is outside the frozen range")
        if (generation == 1 and previous_entry_sha256 is not None) or (
            generation > 1 and not _is_sha256(previous_entry_sha256)
        ):
            raise ValueError("V2.42.41 previous entry binding is invalid")
        event = _clone(current_state["events"][-1])
        value: dict[str, Any] = {
            "artifact_version": 1,
            "role": ENTRY_ROLE,
            "policy_id": POLICY_ID,
            "journal_namespace_sha256": self.namespace,
            "generation": generation,
            "previous_entry_sha256": previous_entry_sha256,
            "previous_state_sha256": previous_state["state_sha256"],
            "transition_event": event,
            "transition_event_sha256": _event_sha256(event),
            "resulting_state_sha256": current_state["state_sha256"],
            "local_posix_advisory_lock_held_when_published": True,
            "immutable_generation_file_created_no_clobber": True,
            "file_and_directory_fsync_attempted": True,
            "independent_append_only_transparency_log_used": False,
            "hardware_stable_storage_independently_attested": False,
            "network_or_distributed_filesystem_semantics_proven": False,
            "malicious_same_user_resealing_excluded": False,
            "active_harness_durability_integrated": False,
            "external_side_effect_authorized": False,
            "active_forward_integration_authorized": False,
            "benchmark_forward_or_evaluator_authorized": False,
        }
        value["entry_sha256"] = object_sha256(value)
        return value

    def _apply_entry(
        self,
        previous_state: Mapping[str, Any],
        entry: Mapping[str, Any],
        *,
        expected_generation: int,
        expected_previous_entry_sha256: str | None,
    ) -> dict[str, Any]:
        _exact(entry, keys=ENTRY_KEYS, label="generation entry")
        event = entry.get("transition_event")
        if not isinstance(event, Mapping):
            raise DurableJournalPoisoned("V2.42.41 transition event is invalid")
        try:
            event_sha256 = _event_sha256(event)
        except (KeyError, TypeError, ValueError) as error:
            raise DurableJournalPoisoned(
                "V2.42.41 transition event seal is invalid"
            ) from error
        if (
            entry.get("role") != ENTRY_ROLE
            or entry.get("policy_id") != POLICY_ID
            or entry.get("journal_namespace_sha256") != self.namespace
            or entry.get("generation") != expected_generation
            or entry.get("previous_entry_sha256")
            != expected_previous_entry_sha256
            or entry.get("previous_state_sha256")
            != previous_state.get("state_sha256")
            or entry.get("transition_event_sha256") != event_sha256
            or entry.get("local_posix_advisory_lock_held_when_published") is not True
            or entry.get("immutable_generation_file_created_no_clobber") is not True
            or entry.get("file_and_directory_fsync_attempted") is not True
            or entry.get("independent_append_only_transparency_log_used") is not False
            or entry.get("hardware_stable_storage_independently_attested") is not False
            or entry.get("network_or_distributed_filesystem_semantics_proven") is not False
            or entry.get("malicious_same_user_resealing_excluded") is not False
            or entry.get("active_harness_durability_integrated") is not False
            or entry.get("external_side_effect_authorized") is not False
            or entry.get("active_forward_integration_authorized") is not False
            or entry.get("benchmark_forward_or_evaluator_authorized") is not False
            or not _sealed(entry, key="entry_sha256")
        ):
            raise DurableJournalPoisoned("V2.42.41 generation entry drifted")
        try:
            if event.get("role") == PERMIT_ROLE:
                current = issue_effect_permit(
                    previous_state,
                    **self._shared,
                    permit_ref_sha256=event["permit_ref_sha256"],
                    charge_kind=event["charge_kind"],
                    charge_ref_sha256=event["charge_ref_sha256"],
                    estimate_source_sha256=event["estimate_source_sha256"],
                    reserved_cost=event["reserved_cost"],
                )
            elif event.get("role") == SETTLEMENT_ROLE:
                current = settle_effect_permit(
                    previous_state,
                    **self._shared,
                    permit_ref_sha256=event["permit_ref_sha256"],
                    effect_receipt_sha256=event["effect_receipt_sha256"],
                    actual_cost_source_sha256=event["actual_cost_source_sha256"],
                    actual_cost=event["actual_cost"],
                )
            else:
                raise ValueError("transition event role")
        except (KeyError, TypeError, ValueError) as error:
            raise DurableJournalPoisoned("V2.42.41 transition replay failed") from error
        if (
            current["events"][-1] != event
            or current["state_sha256"] != entry.get("resulting_state_sha256")
        ):
            raise DurableJournalPoisoned("V2.42.41 replayed state binding drifted")
        return current

    def _scan_names(self) -> tuple[dict[int, Path], list[tuple[int, str, Path]]]:
        finals: dict[int, Path] = {}
        pending: list[tuple[int, str, Path]] = []
        for path in self.entries_directory.iterdir():
            final_match = FINAL_NAME.fullmatch(path.name)
            pending_match = PENDING_NAME.fullmatch(path.name)
            if final_match:
                generation = int(final_match.group("generation"))
                if generation < 1 or generation > MAX_GENERATIONS or generation in finals:
                    raise DurableJournalPoisoned("V2.42.41 final generation name is invalid")
                finals[generation] = path
            elif pending_match:
                generation = int(pending_match.group("generation"))
                if generation < 1 or generation > MAX_GENERATIONS:
                    raise DurableJournalPoisoned(
                        "V2.42.41 pending generation name is invalid"
                    )
                pending.append((generation, pending_match.group("seal"), path))
            else:
                raise DurableJournalPoisoned("V2.42.41 entries directory contains residue")
        if sorted(finals) != list(range(1, len(finals) + 1)):
            raise DurableJournalPoisoned("V2.42.41 final generations are not contiguous")
        return finals, sorted(pending, key=lambda item: (item[0], item[1]))

    def _replay_finals(
        self,
        state: Mapping[str, Any],
        finals: Mapping[int, Path],
    ) -> tuple[dict[str, Any], str | None]:
        current = _clone(dict(state))
        previous_entry_sha: str | None = None
        for generation in range(1, len(finals) + 1):
            entry = _read_object(
                finals[generation],
                allow_link_count_two=True,
            )
            current = self._apply_entry(
                current,
                entry,
                expected_generation=generation,
                expected_previous_entry_sha256=previous_entry_sha,
            )
            previous_entry_sha = str(entry["entry_sha256"])
        return current, previous_entry_sha

    def _recover_locked(
        self,
    ) -> tuple[dict[str, Any], str | None, int]:
        initial = self._load_initial()
        finals, pending = self._scan_names()
        current, previous_entry_sha = self._replay_finals(initial, finals)
        recovered = 0

        remaining: list[tuple[int, str, Path]] = []
        for generation, seal, path in pending:
            if generation <= len(finals):
                final_path = finals[generation]
                pending_value = _read_object(path, allow_link_count_two=True)
                final_value = _read_object(final_path, allow_link_count_two=True)
                if (
                    pending_value != final_value
                    or pending_value.get("entry_sha256") != seal
                ):
                    raise DurableJournalPoisoned("V2.42.41 published pending residue differs")
                try:
                    same_inode = path.samefile(final_path)
                except OSError as error:
                    raise DurableJournalPoisoned(
                        "V2.42.41 published pending linkage is unverifiable"
                    ) from error
                if not same_inode:
                    raise DurableJournalPoisoned(
                        "V2.42.41 published pending residue is not the final link"
                    )
                path.unlink()
                _fsync_directory(self.entries_directory)
                recovered += 1
            else:
                remaining.append((generation, seal, path))

        if remaining:
            if len(remaining) != 1 or remaining[0][0] != len(finals) + 1:
                raise DurableJournalPoisoned("V2.42.41 pending recovery is ambiguous")
            generation, seal, pending_path = remaining[0]
            entry = _read_object(pending_path)
            if entry.get("entry_sha256") != seal:
                raise DurableJournalPoisoned("V2.42.41 pending filename binding drifted")
            next_state = self._apply_entry(
                current,
                entry,
                expected_generation=generation,
                expected_previous_entry_sha256=previous_entry_sha,
            )
            final_path = self.entries_directory / f"{generation:020d}.json"
            try:
                os.link(pending_path, final_path, follow_symlinks=False)
            except FileExistsError as error:
                raise DurableJournalPoisoned("V2.42.41 recovery final unexpectedly exists") from error
            _fsync_directory(self.entries_directory)
            pending_path.unlink()
            _fsync_directory(self.entries_directory)
            current = next_state
            previous_entry_sha = str(entry["entry_sha256"])
            recovered += 1

        # Cleanup must leave every authoritative final with one link.
        finals_after, pending_after = self._scan_names()
        if pending_after or len(finals_after) != int(current["event_count"]):
            raise DurableJournalPoisoned("V2.42.41 recovery did not reach a clean prefix")
        for path in finals_after.values():
            if path.lstat().st_nlink != 1:
                raise DurableJournalPoisoned("V2.42.41 final entry link count drifted")
        return current, previous_entry_sha, recovered

    def load(self) -> dict[str, Any]:
        """Recover a unique complete pending entry and replay the clean prefix."""

        with self._locked():
            state, _, _ = self._recover_locked()
            return _clone(state)

    def status(self) -> dict[str, Any]:
        """Return a content-free status snapshot after recovery and replay."""

        with self._locked():
            state, last_entry, recovered = self._recover_locked()
            return {
                "artifact_version": 1,
                "role": "v24241_durable_preauthorization_status",
                "policy_id": POLICY_ID,
                "journal_namespace_sha256": self.namespace,
                "generation": state["event_count"],
                "current_state_sha256": state["state_sha256"],
                "last_entry_sha256": last_entry,
                "pending_permit_count": len(state["pending_permit_refs"]),
                "recovered_pending_file_count": recovered,
                "clean_contiguous_prefix": True,
                "local_posix_advisory_lock_used": True,
                "external_side_effect_authorized": False,
                "active_forward_integration_authorized": False,
                "benchmark_forward_or_evaluator_authorized": False,
            }

    def _publish_entry_locked(
        self,
        entry: Mapping[str, Any],
        *,
        fault_hook: Callable[[str], None] | None,
    ) -> None:
        generation = int(entry["generation"])
        seal = str(entry["entry_sha256"])
        pending_path = self.entries_directory / (
            f".pending-{generation:020d}-{seal}.json"
        )
        final_path = self.entries_directory / f"{generation:020d}.json"
        if final_path.exists() or final_path.is_symlink():
            raise DurableJournalPoisoned("V2.42.41 final generation already exists")
        descriptor = os.open(
            pending_path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
        )
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(_encoded(entry))
                handle.flush()
                os.fsync(handle.fileno())
            _fsync_directory(self.entries_directory)
        except BaseException:
            try:
                os.close(descriptor)
            except OSError:
                pass
            raise
        if fault_hook is not None:
            fault_hook("after_pending_directory_fsync")
        os.link(pending_path, final_path, follow_symlinks=False)
        _fsync_directory(self.entries_directory)
        if fault_hook is not None:
            fault_hook("after_final_directory_fsync")
        pending_path.unlink()
        _fsync_directory(self.entries_directory)
        if fault_hook is not None:
            fault_hook("after_cleanup_directory_fsync")

    def compare_and_append(
        self,
        *,
        expected_state_sha256: str,
        current_state: Mapping[str, Any],
        fault_hook: Callable[[str], None] | None = None,
    ) -> dict[str, Any]:
        """CAS one validated V2.42.33 transition into a new generation."""

        expected = _sha256(expected_state_sha256, label="expected state")
        candidate = _clone(dict(current_state))
        with self._locked():
            previous, previous_entry_sha, recovered = self._recover_locked()
            if previous["state_sha256"] != expected:
                raise DurableJournalCASConflict(
                    "V2.42.41 expected state is stale"
                )
            entry = self._entry_record(
                previous_state=previous,
                current_state=candidate,
                previous_entry_sha256=previous_entry_sha,
            )
            self._publish_entry_locked(entry, fault_hook=fault_hook)
            return {
                "artifact_version": 1,
                "role": "v24241_durable_preauthorization_commit",
                "policy_id": POLICY_ID,
                "journal_namespace_sha256": self.namespace,
                "generation": entry["generation"],
                "previous_state_sha256": entry["previous_state_sha256"],
                "resulting_state_sha256": entry["resulting_state_sha256"],
                "entry_sha256": entry["entry_sha256"],
                "recovered_pending_file_count_before_commit": recovered,
                "cross_process_cas_for_cooperating_writers": True,
                "immutable_generation_file_created_no_clobber": True,
                "file_and_directory_fsync_attempted": True,
                "active_harness_durability_integrated": False,
                "external_side_effect_authorized": False,
                "active_forward_integration_authorized": False,
                "benchmark_forward_or_evaluator_authorized": False,
            }
