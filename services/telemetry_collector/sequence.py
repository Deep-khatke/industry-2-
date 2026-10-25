"""Sequence tracker and observable sequence gap detector."""

import threading
from dataclasses import dataclass


@dataclass
class SequenceStatus:
    """Result of evaluating a received sequence number against expectation."""

    is_valid: bool
    is_gap: bool
    is_duplicate_or_reorder: bool
    is_reset: bool
    gap_size: int
    expected_sequence: int
    received_sequence: int


class SequenceTracker:
    """
    Per-exporter observation domain sequence tracking.
    Detects dropped packets, sequence discontinuities, duplicates, and exporter reboots.
    """

    MAX_32BIT_INT = 4294967295

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # Key: (exporter_ip, observation_domain_id) -> (last_seq, boot_epoch, total_gaps)
        self._state: dict[tuple[str, int], dict[str, int]] = {}

    def track_sequence(
        self,
        exporter_ip: str,
        observation_domain_id: int,
        received_sequence: int,
        records_in_packet: int = 1,
        boot_epoch: int = 0,
    ) -> SequenceStatus:
        """
        Evaluate and update sequence state.
        Returns SequenceStatus detailing if a gap, duplicate, or reset occurred.
        """
        key = (exporter_ip, observation_domain_id)
        with self._lock:
            state = self._state.get(key)
            if state is None:
                # First observation of this exporter domain
                self._state[key] = {
                    "last_seq": received_sequence,
                    "boot_epoch": boot_epoch,
                    "total_gaps": 0,
                    "packet_count": 1,
                }
                return SequenceStatus(
                    is_valid=True,
                    is_gap=False,
                    is_duplicate_or_reorder=False,
                    is_reset=False,
                    gap_size=0,
                    expected_sequence=received_sequence,
                    received_sequence=received_sequence,
                )

            last_seq = state["last_seq"]
            last_epoch = state["boot_epoch"]

            # Exporter reboot check (explicit boot_epoch increment or massive backward sequence drop)
            if boot_epoch > last_epoch or (received_sequence < (last_seq // 2) and last_seq > 1000):
                state["last_seq"] = received_sequence
                state["boot_epoch"] = boot_epoch
                state["packet_count"] += 1
                return SequenceStatus(
                    is_valid=True,
                    is_gap=False,
                    is_duplicate_or_reorder=False,
                    is_reset=True,
                    gap_size=0,
                    expected_sequence=received_sequence,
                    received_sequence=received_sequence,
                )

            expected_seq = (last_seq + records_in_packet) & self.MAX_32BIT_INT

            if received_sequence == expected_seq or received_sequence == last_seq + 1:
                # Normal in-order sequence
                state["last_seq"] = received_sequence
                state["packet_count"] += 1
                return SequenceStatus(
                    is_valid=True,
                    is_gap=False,
                    is_duplicate_or_reorder=False,
                    is_reset=False,
                    gap_size=0,
                    expected_sequence=expected_seq,
                    received_sequence=received_sequence,
                )

            elif received_sequence > expected_seq:
                # Observable sequence gap (packets lost in transit)
                gap_size = received_sequence - expected_seq
                state["total_gaps"] += gap_size
                state["last_seq"] = received_sequence
                state["packet_count"] += 1
                return SequenceStatus(
                    is_valid=True,
                    is_gap=True,
                    is_duplicate_or_reorder=False,
                    is_reset=False,
                    gap_size=gap_size,
                    expected_sequence=expected_seq,
                    received_sequence=received_sequence,
                )

            else:
                # Duplicate packet or out-of-order arrival
                return SequenceStatus(
                    is_valid=False,
                    is_gap=False,
                    is_duplicate_or_reorder=True,
                    is_reset=False,
                    gap_size=0,
                    expected_sequence=expected_seq,
                    received_sequence=received_sequence,
                )

    def get_gap_count(self, exporter_ip: str, observation_domain_id: int) -> int:
        """Return total observed sequence gaps for domain."""
        key = (exporter_ip, observation_domain_id)
        with self._lock:
            state = self._state.get(key)
            return state["total_gaps"] if state else 0
