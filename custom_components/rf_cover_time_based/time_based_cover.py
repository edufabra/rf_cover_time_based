"""The cover entity for the RF Cover Time Based integration."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.components.cover import (
    ATTR_POSITION,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_DEVICE_CLASS,
    STATE_UNAVAILABLE,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_interval,
)
from homeassistant.helpers.restore_state import RestoreEntity

from .const import (
    CONF_CLOSE_COMMAND,
    CONF_OPEN_COMMAND,
    CONF_REMOTE_ENTITY,
    CONF_STOP_COMMAND,
    CONF_TRAVELLING_TIME_DOWN,
    CONF_TRAVELLING_TIME_UP,
    DOMAIN,
)
from .travelcalculator import TravelCalculator, TravelStatus

_LOGGER = logging.getLogger(__name__)

UPDATE_INTERVAL = timedelta(seconds=0.1)


class TimeBasedCover(CoverEntity, RestoreEntity):
    """A time-based cover that is controlled by an RF or IR remote."""

    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the cover."""
        self.hass = hass
        self.config_entry = config_entry

        self._attr_name = config_entry.title
        self._attr_unique_id = config_entry.entry_id
        self._attr_supported_features = (
            CoverEntityFeature.OPEN
            | CoverEntityFeature.CLOSE
            | CoverEntityFeature.STOP
            | CoverEntityFeature.SET_POSITION
        )

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self.config_entry.entry_id)},
            name=self.config_entry.title,
            manufacturer="RF Cover Time Based",
            model="Time Based RF Cover",
        )

        self._load_config()

        self.travel_calculator = TravelCalculator(
            self._travel_time_down, self._travel_time_up
        )

        # Initialize internal state attributes
        self._attr_current_cover_position: int | None = None
        self._attr_is_closed: bool | None = None
        self._updater_cancel_callback: callback | None = None

    def _load_config(self) -> None:
        """Load and apply the latest configuration from the config entry."""
        config = {**self.config_entry.data, **self.config_entry.options}

        self._attr_device_class = config.get(CONF_DEVICE_CLASS)
        self._remote_entity_id = config[CONF_REMOTE_ENTITY]
        self._open_command = config[CONF_OPEN_COMMAND]
        self._close_command = config[CONF_CLOSE_COMMAND]
        self._stop_command = config[CONF_STOP_COMMAND]
        self._travel_time_down = config[CONF_TRAVELLING_TIME_DOWN]
        self._travel_time_up = config[CONF_TRAVELLING_TIME_UP]

    @property
    def available(self) -> bool:
        """Return True if the remote entity is available."""
        remote_state = self.hass.states.get(self._remote_entity_id)
        return remote_state is not None and remote_state.state != STATE_UNAVAILABLE

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()
        await self._async_restore_state()

        self.async_on_remove(
            async_track_state_change_event(
                self.hass,
                [self._remote_entity_id],
                self._handle_remote_availability_change,
            )
        )
        self.config_entry.add_update_listener(self._handle_options_update)
        self.async_on_remove(self._cancel_updater)

    async def _async_restore_state(self) -> None:
        """Restore the last known state of the cover."""
        last_state = await self.async_get_last_state()
        restored_position = None

        if last_state and (
            last_position := last_state.attributes.get(ATTR_POSITION)
        ) is not None:
            _LOGGER.debug("Restoring cover position to %s", last_position)
            restored_position = int(last_position)
        else:
            _LOGGER.debug("No previous state found. Defaulting to open position.")
            restored_position = 100

        self.travel_calculator.set_known_position(restored_position)
        self._update_position_attributes()

    @callback
    def _update_position_attributes(self) -> None:
        """Update the position and is_closed attributes from the calculator."""
        self._attr_current_cover_position = self.travel_calculator.current_position()
        self._attr_is_closed = self._attr_current_cover_position == 0

    @callback
    def _handle_remote_availability_change(self, *args: Any) -> None:
        """Handle availability changes of the remote entity."""
        self.async_write_ha_state()

    @callback
    def _handle_options_update(
        self, hass: HomeAssistant, entry: ConfigEntry
    ) -> None:
        """Handle an options update."""
        _LOGGER.debug("Reloading configuration from options flow")
        self._load_config()
        self.travel_calculator = TravelCalculator(
            self._travel_time_down, self._travel_time_up
        )
        self.async_write_ha_state()

    def _get_command_for_direction(self, direction: TravelStatus) -> str:
        """Get the appropriate command based on the direction of travel."""
        is_awning = self.device_class == "awning"
        if direction == TravelStatus.OPENING:
            return self._close_command if is_awning else self._open_command
        return self._open_command if is_awning else self._close_command

    async def _async_trigger_travel(self, target_position: int) -> None:
        """Start a cover movement to a specific target position."""
        travel_direction = self.travel_calculator.start_travel(target_position)
        if not travel_direction:
            return

        command = self._get_command_for_direction(travel_direction)
        await self._async_handle_command(command)
        self._schedule_updater()
        self.async_write_ha_state()

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Service call to close the cover."""
        await self._async_trigger_travel(0)

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Service call to open the cover."""
        await self._async_trigger_travel(100)

    async def async_stop_cover(self, **kwargs: Any) -> None:
        """Service call to stop the cover."""
        if self.travel_calculator.stop_travel():
            self._cancel_updater()
            self._update_position_attributes()
            await self._async_handle_command(self._stop_command)
            self.async_write_ha_state()

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        """Service call to set the cover to a specific position."""
        await self._async_trigger_travel(kwargs[ATTR_POSITION])

    @callback
    def _schedule_updater(self) -> None:
        """Schedule the periodic position updater task."""
        self._cancel_updater()
        self._updater_cancel_callback = async_track_time_interval(
            self.hass, self._async_update_position, UPDATE_INTERVAL
        )

    @callback
    def _cancel_updater(self) -> None:
        """Cancel the periodic position updater task."""
        if self._updater_cancel_callback:
            self._updater_cancel_callback()
            self._updater_cancel_callback = None

    @callback
    def _async_update_position(self, *args: Any) -> None:
        """Periodically update the cover's position during travel."""
        if not self.travel_calculator.update_position():
            self._cancel_updater()

        self._update_position_attributes()
        self.async_write_ha_state()

    async def _async_handle_command(self, command: str) -> None:
        """Send a command to the remote entity."""
        if not command:
            _LOGGER.warning("No command specified for this action.")
            return

        _LOGGER.debug("Sending command '%s' to %s", command, self._remote_entity_id)
        await self.hass.services.async_call(
            "remote",
            "send_command",
            {"entity_id": self._remote_entity_id, "command": [command]},
            blocking=False,
        )

    @property
    def is_opening(self) -> bool | None:
        """Return if the cover is opening or not."""
        if self.current_cover_position is None:
            return None
        return self.travel_calculator.is_opening()

    @property
    def is_closing(self) -> bool | None:
        """Return if the cover is closing or not."""
        if self.current_cover_position is None:
            return None
        return self.travel_calculator.is_closing()

    # The `state` and `is_closed` properties are now inherited from the base
    # CoverEntity class. They automatically use `is_opening`, `is_closing`,
    # and `current_cover_position` to determine the correct state,
    # which avoids redundant code.
