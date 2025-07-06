"""An abstract base class for a time-based RF cover entity."""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import timedelta
from typing import Any

from homeassistant.components.cover import (
    ATTR_POSITION,
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import Event, callback
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_interval,
)
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN
from .travelcalculator import TravelCalculator

_LOGGER = logging.getLogger(__name__)
UPDATE_INTERVAL = timedelta(seconds=0.1)


class TimeBasedCover(CoverEntity, RestoreEntity, ABC):
    """Abstract representation of a time-based RF cover."""

    _attr_has_entity_name = True
    _attr_name = None  # Use the name from the config entry
    _attr_should_poll = False
    _attr_assumed_state = True
    _attr_supported_features = (
        CoverEntityFeature.OPEN
        | CoverEntityFeature.CLOSE
        | CoverEntityFeature.STOP
        | CoverEntityFeature.SET_POSITION
    )

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize the cover."""
        self.config_entry = config_entry
        self._attr_unique_id = config_entry.entry_id

        # This property ensures we always use the latest options
        config = self._merged_config

        self._attr_device_class = config.get("device_class", CoverDeviceClass.SHUTTER)
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": config["name"],
            "manufacturer": "RF Time Based",
        }

        self._remote_entity_id: str = config["remote_entity"]
        self._open_command: str = config["open_command"]
        self._close_command: str = config["close_command"]
        self._stop_command: str = config["stop_command"]

        self.travel_calculator = TravelCalculator(
            config["travelling_time_down"], config["travelling_time_up"]
        )
        self._attr_current_cover_position: int | None = None
        self._attr_available = False
        self._updater_unsub = None

    @property
    def _merged_config(self) -> dict[str, Any]:
        """Return the combined configuration from data and options."""
        # Options override the initial data
        return {**self.config_entry.data, **self.config_entry.options}

    @property
    def current_cover_position(self) -> int | None:
        """Return current position of cover."""
        if self.travel_calculator.is_moving():
            return self.travel_calculator.current_position()
        return self._attr_current_cover_position

    @property
    def is_opening(self) -> bool:
        """Return if the cover is opening or not."""
        return self.travel_calculator.is_opening()

    @property
    def is_closing(self) -> bool:
        """Return if the cover is closing or not."""
        return self.travel_calculator.is_closing()

    @property
    def is_closed(self) -> bool | None:
        """Return if the cover is closed or not."""
        pos = self.current_cover_position
        if pos is None:
            return None
        return pos == 0

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()

        last_state = await self.async_get_last_state()
        if last_state and (
            restored_pos := last_state.attributes.get(ATTR_POSITION)
        ) is not None:
            _LOGGER.debug("Restoring cover position to %s", restored_pos)
            self._attr_current_cover_position = int(restored_pos)
            self.travel_calculator.set_known_position(int(restored_pos))
        else:
            self._attr_current_cover_position = 100
            self.travel_calculator.set_known_position(100)

        @callback
        def _update_availability(event: Event | None = None) -> None:
            """Update availability based on the remote's state."""
            remote_state = self.hass.states.get(self._remote_entity_id)
            new_availability = (
                remote_state is not None and remote_state.state != STATE_UNAVAILABLE
            )
            if self._attr_available != new_availability:
                _LOGGER.debug(
                    "Availability of %s changed to %s",
                    self.entity_id,
                    new_availability,
                )
                self._attr_available = new_availability
                self.async_write_ha_state()

        self.async_on_remove(
            async_track_state_change_event(
                self.hass, [self._remote_entity_id], _update_availability
            )
        )
        _update_availability()

    @abstractmethod
    async def _async_handle_command(self, command: str) -> None:
        """Abstract method for sending a command to the physical device."""
        raise NotImplementedError

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open the cover by setting the position to 100."""
        await self.async_set_cover_position(position=100)

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close the cover by setting the position to 0."""
        await self.async_set_cover_position(position=0)

    async def async_stop_cover(self, **kwargs: Any) -> None:
        """Stop the cover."""
        if self.travel_calculator.is_moving():
            self.travel_calculator.stop_travel()
            self._cancel_updater()
            self._attr_current_cover_position = self.travel_calculator.current_position()
            await self._async_handle_command(self._stop_command)
            self.async_write_ha_state()

    def _get_command_for_travel(self) -> str:
        """Determine the correct command based on travel direction and device class."""
        is_awning = self._attr_device_class == CoverDeviceClass.AWNING
        if self.travel_calculator.is_opening():
            return self._close_command if is_awning else self._open_command
        return self._open_command if is_awning else self._close_command

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        """Move the cover to a specific position."""
        position = kwargs[ATTR_POSITION]
        if self.travel_calculator.start_travel(position):
            command = self._get_command_for_travel()
            await self._async_handle_command(command)
            self._start_updater()
            self.async_write_ha_state()

    def _start_updater(self) -> None:
        """Start the periodic updater to update the position."""
        self._cancel_updater()
        self._updater_unsub = async_track_time_interval(
            self.hass, self._async_update_position, UPDATE_INTERVAL
        )

    def _cancel_updater(self) -> None:
        """Cancel the periodic updater."""
        if self._updater_unsub:
            self._updater_unsub()
            self._updater_unsub = None

    @callback
    def _async_update_position(self, now: Any) -> None:
        """Periodically update the position and check if travel is complete."""
        is_still_moving = self.travel_calculator.update_position()

        if not is_still_moving:
            self._cancel_updater()
            self._attr_current_cover_position = self.travel_calculator.current_position()

        self.async_write_ha_state()
