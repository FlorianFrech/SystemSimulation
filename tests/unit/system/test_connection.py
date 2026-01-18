"""
Unit tests for syssimx.system.connection

Tests the Connection and EventConnection dataclasses.
"""

import pytest

from syssimx.system.connection import Connection, EventConnection


# ============================================================================
# Test Connection Dataclass
# ============================================================================
class TestConnection:
    """Test Connection dataclass properties and methods."""

    def test_construction_minimal(self):
        """Test basic connection construction with required fields."""
        conn = Connection(
            src_comp="CompA",
            src_port="out",
            dst_comp="CompB",
            dst_port="in",
        )

        assert conn.src_comp == "CompA"
        assert conn.src_port == "out"
        assert conn.dst_comp == "CompB"
        assert conn.dst_port == "in"

    def test_key_method(self):
        """Test that key() returns unique tuple identifier."""
        conn = Connection(
            src_comp="CompA",
            src_port="out",
            dst_comp="CompB",
            dst_port="in",
        )

        key = conn.key()

        assert key == ("CompA", "out", "CompB", "in")
        assert isinstance(key, tuple)

    def test_connection_is_frozen(self):
        """Test that Connection is immutable (frozen dataclass)."""
        conn = Connection(
            src_comp="CompA",
            src_port="out",
            dst_comp="CompB",
            dst_port="in",
        )

        with pytest.raises(AttributeError):
            conn.src_comp = "CompC"

    def test_connection_equality(self):
        """Test connection equality comparison."""
        conn1 = Connection(
            src_comp="CompA",
            src_port="out",
            dst_comp="CompB",
            dst_port="in",
        )
        conn2 = Connection(
            src_comp="CompA",
            src_port="out",
            dst_comp="CompB",
            dst_port="in",
        )
        conn3 = Connection(
            src_comp="CompA",
            src_port="out",
            dst_comp="CompC",
            dst_port="in",
        )

        assert conn1 == conn2
        assert conn1 != conn3

    def test_connection_hashable(self):
        """Test that Connection can be used in sets and as dict keys."""
        conn1 = Connection(
            src_comp="CompA",
            src_port="out",
            dst_comp="CompB",
            dst_port="in",
        )
        conn2 = Connection(
            src_comp="CompA",
            src_port="out",
            dst_comp="CompB",
            dst_port="in",
        )

        # Should be usable in a set
        conn_set = {conn1, conn2}
        assert len(conn_set) == 1

        # Should be usable as dict key
        conn_dict = {conn1: "value"}
        assert conn_dict[conn2] == "value"


# ============================================================================
# Test EventConnection Dataclass
# ============================================================================
class TestEventConnection:
    """Test EventConnection dataclass properties."""

    def test_construction(self):
        """Test basic event connection construction."""
        event_conn = EventConnection(
            src_comp="SourceComp",
            src_port="trigger_event",
            dst_comp="TargetComp",
            dst_port="event_handler",
        )

        assert event_conn.src_comp == "SourceComp"
        assert event_conn.src_port == "trigger_event"
        assert event_conn.dst_comp == "TargetComp"
        assert event_conn.dst_port == "event_handler"

    def test_event_name_property(self):
        """Test that event_name property returns src_port."""
        event_conn = EventConnection(
            src_comp="SourceComp",
            src_port="my_event",
            dst_comp="TargetComp",
            dst_port="handler",
        )

        assert event_conn.event_name == "my_event"

    def test_target_comp_property(self):
        """Test that target_comp property returns dst_comp."""
        event_conn = EventConnection(
            src_comp="SourceComp",
            src_port="event",
            dst_comp="MyTarget",
            dst_port="handler",
        )

        assert event_conn.target_comp == "MyTarget"

    def test_event_connection_is_frozen(self):
        """Test that EventConnection is immutable (frozen dataclass)."""
        event_conn = EventConnection(
            src_comp="SourceComp",
            src_port="event",
            dst_comp="TargetComp",
            dst_port="handler",
        )

        with pytest.raises(AttributeError):
            event_conn.src_comp = "OtherComp"

    def test_event_connection_equality(self):
        """Test event connection equality comparison."""
        ec1 = EventConnection(
            src_comp="SourceComp",
            src_port="event",
            dst_comp="TargetComp",
            dst_port="handler",
        )
        ec2 = EventConnection(
            src_comp="SourceComp",
            src_port="event",
            dst_comp="TargetComp",
            dst_port="handler",
        )
        ec3 = EventConnection(
            src_comp="SourceComp",
            src_port="other_event",
            dst_comp="TargetComp",
            dst_port="handler",
        )

        assert ec1 == ec2
        assert ec1 != ec3

    def test_event_connection_hashable(self):
        """Test that EventConnection can be used in sets and as dict keys."""
        ec1 = EventConnection(
            src_comp="SourceComp",
            src_port="event",
            dst_comp="TargetComp",
            dst_port="handler",
        )
        ec2 = EventConnection(
            src_comp="SourceComp",
            src_port="event",
            dst_comp="TargetComp",
            dst_port="handler",
        )

        # Should be usable in a set
        ec_set = {ec1, ec2}
        assert len(ec_set) == 1
