"""A helper class to calculate the position of a time-based cover."""
from __future__ import annotations

import time
from enum import Enum


class TravelStatus(Enum):
    """The state of the cover's movement."""

    STOPPED = "stopped"
    OPENING = "opening"
    CLOSING = "closing"


class TravelCalculator:
    """
    A class to calculate the position of a cover based on travel time.

    This class is a pure Python implementation, making it easy to unit test
    independently of the Home Assistant event loop. It uses time.monotonic()
    for reliable elapsed time measurement.
    """

    def __init__(self, travel_time_down: float, travel_time_up: float):
        """Initialize the travel calculator."""
        # Add validation to ensure travel times are not negative.
        # This makes the class more robust against invalid configuration by
        # failing early and clearly if provided with nonsensical data.
        if travel_time_down < 0 or travel_time_up < 0:
            raise ValueError("Travel time cannot be negative.")

        self._travel_time_down = travel_time_down
        self._travel_time_up = travel_time_up
        self._position: float = 100.0
        self._target_position: int = 100
        self._travel_status = TravelStatus.STOPPED
        self._last_update_time = time.monotonic()

    @property
    def _current_travel_time(self) -> float:
        """Get the total travel time for the current direction of travel."""
        if self.is_opening():
            return self._travel_time_up
        return self._travel_time_down

    def set_known_position(self, position: int) -> None:
        """Set the current position of the cover without initiating travel."""
        self._position = float(position)
        self._target_position = position
        self._travel_status = TravelStatus.STOPPED

    def start_travel(self, target_position: int) -> TravelStatus | None:
        """
        Start traveling to a new position.

        Returns the direction of travel or None if no travel is needed.
        """
        self.update_position()
        if target_position == self.current_position():
            return None

        self._target_position = target_position
        self._travel_status = (
            TravelStatus.OPENING
            if target_position > self._position
            else TravelStatus.CLOSING
        )
        self._last_update_time = time.monotonic()
        return self._travel_status

    def stop_travel(self) -> bool:
        """
        Stop the cover's movement.

        Returns True if the cover was moving, False otherwise.
        """
        was_moving = self.is_moving()
        self.update_position()
        self._travel_status = TravelStatus.STOPPED
        self._target_position = self.current_position()
        return was_moving

    def update_position(self) -> bool:
        """
        Update the cover's position based on elapsed time.

        Returns True if the cover is still moving, False if it has stopped.
        """
        if not self.is_moving():
            return False

        now = time.monotonic()
        elapsed_time = now - self._last_update_time
        self._last_update_time = now

        travel_time = self._current_travel_time
        if travel_time == 0:
            # Avoid division by zero if travel time is not set
            self._position = float(self._target_position)
        else:
            position_change = (elapsed_time / travel_time) * 100
            if self.is_opening():
                new_position = self._position + position_change
                self._position = min(new_position, self._target_position)
            else:  # Closing
                new_position = self._position - position_change
                self._position = max(new_position, self._target_position)

        if self.current_position() == self._target_position:
            self._travel_status = TravelStatus.STOPPED
            return False

        return True

    def current_position(self) -> int:
        """Return the current calculated position."""
        return round(self._position)

    def is_moving(self) -> bool:
        """Return if the cover is currently moving."""
        return self._travel_status != TravelStatus.STOPPED

    def is_opening(self) -> bool:
        """Return if the cover is opening."""
        return self._travel_status == TravelStatus.OPENING

    def is_closing(self) -> bool:
        """Return if the cover is closing."""
        return self._travel_status == TravelStatus.CLOSING
