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
    STATE_CLOSED,
    STATE_CLOSING,
    STATE_OPEN,
    STATE_OPENING,
    STATE_UNAVAILABLE,
)
from homeassistant.core import HomeAssistant, callback
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
)
from .travelcalculator import TravelCalculator, TravelStatus

_LOGGER = logging.getLogger(__name__)

# The frequency at which the cover's position is updated.
UPDATE_INTERVAL = timedelta(seconds=0.1)


class TimeBasedCover(CoverEntity, RestoreEntity):
    """A time-based cover that is controlled by an RF or IR remote."""

    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the cover."""
        self.hass = hass
        self.config_entry = config_entry

        # Set immutable attributes from the config entry
        self._attr_name = config_entry.title
        self._attr_unique_id = config_entry.entry_id
        self._attr_supported_features = (
            CoverEntityFeature.OPEN
            | CoverEntityFeature.CLOSE
            | CoverEntityFeature.STOP
            | CoverEntityFeature.SET_POSITION
        )

        # Load all configuration values. This method will be reused for options updates.
        self._load_config()

        # Initialize the travel calculator. It will be re-initialized if options change.
        self.travel_calculator = TravelCalculator(
            self._travel_time_down, self._travel_time_up
        )

        # Initialize position to None. It will be set during state restoration.
        self._attr_current_cover_position = None
        self._attr_is_closed = None

        # A callback to cancel the periodic position updater
        self._updater_cancel_callback = None

    def _load_config(self) -> None:
        """Load and apply the latest configuration from the config entry."""
        # Options flow values take precedence over initial data
        config = {**self.config_entry.data, **self.config_entry.options}

        # --- THIS IS THE FIX ---
        # The device_class is now correctly loaded from the merged config
        self._attr_device_class = config.get(CONF_DEVICE_CLASS)
        # --- END OF THE FIX ---

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

        # Restore the last known state of the cover.
        await self._async_restore_state()

        # Set up listeners for remote availability and options updates.
        self.async_on_remove(
            async_track_state_change_event(
                self.hass,
                [self._remote_entity_id],
                self._handle_remote_availability_change,
            )
        )
        self.config_entry.add_update_listener(self._handle_options_update)

        # Register the updater cancellation as a cleanup callback.
        # This ensures that any running timer is stopped when the entity is
        # unloaded, preventing the "Lingering timer" error in tests.
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

        # If no state was restored, default to the fully open position.
        if restored_position is None:
            _LOGGER.debug("No previous state found. Defaulting to open position.")
            restored_position = 100

        self.travel_calculator.set_known_position(restored_position)
        self._attr_current_cover_position = self.travel_calculator.current_position()
        self._attr_is_closed = self.current_cover_position == 0

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
        # Reload all config values and re-initialize the travel calculator
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
        # Assumes direction is TravelStatus.CLOSING
        return self._open_command if is_awning else self._close_command

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close the cover."""
        if self.travel_calculator.start_travel(0):
            command = self._get_command_for_direction(TravelStatus.CLOSING)
            await self._async_handle_command(command)
            self._schedule_updater()
            self.async_write_ha_state()

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open the cover."""
        if self.travel_calculator.start_travel(100):
            command = self._get_command_for_direction(TravelStatus.OPENING)
            await self._async_handle_command(command)
            self._schedule_updater()
            self.async_write_ha_state()

    async def async_stop_cover(self, **kwargs: Any) -> None:
        """Stop the cover."""
        if self.travel_calculator.stop_travel():
            self._cancel_updater()
            position = self.travel_calculator.current_position()
            self._attr_current_cover_position = position
            await self._async_handle_command(self._stop_command)
            self.async_write_ha_state()

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        """Set the cover to a specific position."""
        target_position = kwargs[ATTR_POSITION]
        travel_direction = self.travel_calculator.start_travel(target_position)

        if travel_direction:
            command = self._get_command_for_direction(travel_direction)
            await self._async_handle_command(command)
            self._schedule_updater()
            self.async_write_ha_state()

    @callback
    def _schedule_updater(self) -> None:
        """Schedule the periodic position updater."""
        self._cancel_updater()
        self._updater_cancel_callback = async_track_time_interval(
            self.hass, self._async_update_position, UPDATE_INTERVAL
        )

    @callback
    def _cancel_updater(self) -> None:
        """Cancel the periodic position updater."""
        if self._updater_cancel_callback:
            self._updater_cancel_callback()
            self._updater_cancel_callback = None

    @callback
    def _async_update_position(self, *args: Any) -> None:
        """Periodically update the cover's position during travel."""
        is_still_moving = self.travel_calculator.update_position()
        position = self.travel_calculator.current_position()
        self._attr_current_cover_position = position

        if not is_still_moving:
            self._cancel_updater()

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
        if self._attr_current_cover_position is None:
            return None
        return self.travel_calculator.is_opening()

    @property
    def is_closing(self) -> bool | None:
        """Return if the cover is closing or not."""
        if self._attr_current_cover_position is None:
            return None
        return self.travel_calculator.is_closing()

    @property
    def is_closed(self) -> bool | None:
        """Return if the cover is closed or not."""
        if self._attr_current_cover_position is None:
            return None
        return self._attr_current_cover_position == 0

    @property
    def state(self) -> str:
        """Return the state of the cover."""
        if self.is_opening:
            return STATE_OPENING
        if self.is_closing:
            return STATE_CLOSING
        return STATE_OPEN if not self.is_closed else STATE_CLOSED
