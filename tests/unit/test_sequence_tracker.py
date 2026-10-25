"""Unit tests for sequence tracking and packet loss gap detection."""

import pytest

from services.telemetry_collector.sequence import SequenceTracker


@pytest.mark.unit
class TestSequenceTracker:
    """Test suite verifying sequence tracking, gap detection, and reboot handling."""

    def test_normal_in_order_sequence(self) -> None:
        """Verify normal sequential packets update without reporting gaps."""
        tracker = SequenceTracker()
        s1 = tracker.track_sequence("10.100.1.1", 101, received_sequence=1, records_in_packet=1)
        assert s1.is_valid is True
        assert s1.is_gap is False

        s2 = tracker.track_sequence("10.100.1.1", 101, received_sequence=2, records_in_packet=1)
        assert s2.is_valid is True
        assert s2.is_gap is False

    def test_observable_sequence_gap_detected(self) -> None:
        """Verify sequence gap is detected and gap size computed accurately."""
        tracker = SequenceTracker()
        tracker.track_sequence("10.100.1.1", 101, received_sequence=10, records_in_packet=1)

        # Expected was 11, but received 16 -> Gap of 5 packets lost in transit
        status = tracker.track_sequence("10.100.1.1", 101, received_sequence=16, records_in_packet=1)
        assert status.is_valid is True
        assert status.is_gap is True
        assert status.gap_size == 5
        assert tracker.get_gap_count("10.100.1.1", 101) == 5

    def test_duplicate_or_reorder_detected(self) -> None:
        """Verify duplicate sequence is flagged."""
        tracker = SequenceTracker()
        tracker.track_sequence("10.100.1.1", 101, received_sequence=20, records_in_packet=1)

        # Duplicate arrives with sequence 20
        status = tracker.track_sequence("10.100.1.1", 101, received_sequence=20, records_in_packet=1)
        assert status.is_duplicate_or_reorder is True

    def test_exporter_reboot_detected(self) -> None:
        """Verify exporter reboot resets sequence expectation without counting massive gap."""
        tracker = SequenceTracker()
        tracker.track_sequence("10.100.1.1", 101, received_sequence=50000, boot_epoch=1)

        # Exporter reboots: boot_epoch increments to 2 and sequence resets to 1
        status = tracker.track_sequence("10.100.1.1", 101, received_sequence=1, boot_epoch=2)
        assert status.is_reset is True
        assert status.is_gap is False
        assert status.received_sequence == 1
