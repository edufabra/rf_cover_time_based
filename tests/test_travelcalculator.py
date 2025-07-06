"""Test the TravelCalculator helper class."""

import pytest
from freezegun import freeze_time

from custom_components.rf_cover_time_based.travelcalculator import (
    TravelCalculator,
    TravelStatus,
)
from tests.const import MOCK_CONFIG


@pytest.fixture
def calculator() -> TravelCalculator:
    """Return a TravelCalculator instance for testing."""
    return TravelCalculator(
        travel_time_down=MOCK_CONFIG["travelling_time_down"],
        travel_time_up=MOCK_CONFIG["travelling_time_up"],
    )


class TestTravelCalculatorState:
    """Test the state management of the TravelCalculator."""

    def test_initial_state(self, calculator: TravelCalculator):
        """Test the initial state of the calculator."""
        assert calculator.current_position() == 100
        assert not calculator.is_moving()
        assert not calculator.is_opening()
        assert not calculator.is_closing()

    def test_set_known_position(self, calculator: TravelCalculator):
        """Test setting a known position."""
        calculator.set_known_position(50)
        assert calculator.current_position() == 50
        assert not calculator.is_moving()

        calculator.set_known_position(0)
        assert calculator.current_position() == 0


class TestTravelCalculatorMovement:
    """Test the movement logic of the TravelCalculator."""

    def test_start_travel_down(self, calculator: TravelCalculator):
        """Test starting to travel down (closing)."""
        result = calculator.start_travel(0)
        assert result == TravelStatus.CLOSING
        assert calculator.is_moving()
        assert calculator.is_closing()
        assert not calculator.is_opening()

    def test_start_travel_up_from_closed(self, calculator: TravelCalculator):
        """Test starting to travel up (opening) from a closed state."""
        calculator.set_known_position(0)
        result = calculator.start_travel(100)
        assert result == TravelStatus.OPENING
        assert calculator.is_moving()
        assert calculator.is_opening()
        assert not calculator.is_closing()

    def test_start_travel_already_at_position(self, calculator: TravelCalculator):
        """Test that travel does not start if already at the target position."""
        calculator.set_known_position(50)
        result = calculator.start_travel(50)
        assert result is None
        assert not calculator.is_moving()

    def test_stop_travel(self, calculator: TravelCalculator):
        """Test stopping the travel."""
        calculator.start_travel(0)
        assert calculator.is_moving()

        was_moving = calculator.stop_travel()
        assert was_moving
        assert not calculator.is_moving()

        # Test stopping when not moving
        was_moving_again = calculator.stop_travel()
        assert not was_moving_again


class TestTravelCalculatorCalculations:
    """Test the position calculation logic."""

    @freeze_time("2023-01-01 12:00:00")
    def test_position_calculation_while_closing(self, calculator: TravelCalculator):
        """Test position calculation while the cover is closing."""
        calculator.start_travel(0)  # Start closing from 100%

        with freeze_time("2023-01-01 12:00:05"):  # 5 seconds later
            calculator.update_position()
            # Travel time down is 10s, so 5s should be 50% of the way.
            assert calculator.current_position() == 50

    @freeze_time("2023-01-01 12:00:00")
    def test_position_calculation_while_opening(self, calculator: TravelCalculator):
        """Test position calculation while the cover is opening."""
        calculator.set_known_position(0)
        calculator.start_travel(100)  # Start opening from 0%

        with freeze_time("2023-01-01 12:00:03"):  # 3 seconds later
            calculator.update_position()
            # Travel time up is 10s, so 3s should be 30% of the way.
            assert calculator.current_position() == 30

    @freeze_time("2023-01-01 12:00:00")
    def test_position_reached_on_arrival(self, calculator: TravelCalculator):
        """Test that the cover stops exactly at the target position."""
        calculator.start_travel(0)

        with freeze_time("2023-01-01 12:00:10"):  # Exactly 10 seconds later
            is_moving = calculator.update_position()
            assert calculator.current_position() == 0
            assert not is_moving
            assert not calculator.is_moving()

            assert not calculator.is_opening()

        # In /Users/eduardfabra/code/rf_cover_time_based/tests/test_travelcalculator.py

        # ... inside class TestTravelCalculatorCalculations:

    def test_position_with_zero_travel_time(self):
        """Test that the position is set instantly if travel time is zero."""
        # Create a calculator with zero travel time for the 'down' direction
        zero_time_calculator = TravelCalculator(travel_time_down=0, travel_time_up=10)

        # Start at 100 and command a move to 0.
        # Since travel_time_down is 0, it should move instantly.
        zero_time_calculator.start_travel(0)
        is_moving = zero_time_calculator.update_position()

        assert zero_time_calculator.current_position() == 0
        assert not is_moving, "Cover should not be moving after an instant travel"
