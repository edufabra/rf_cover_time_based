"""The cover platform for the RF Cover Time Based integration.

This file is the entry point for the cover platform. It sets up the
cover entity and forwards the configuration to the underlying
TimeBasedCover class.
"""
from __future__ import annotations

from homeassistant.components.remote import DOMAIN as REMOTE_DOMAIN
from homeassistant.components.remote import SERVICE_SEND_COMMAND
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .time_based_cover import TimeBasedCover


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the cover platform for the RF Cover Time Based integration."""
    async_add_entities([RfTimeBasedCover(config_entry)])


class RfTimeBasedCover(TimeBasedCover):
    """A concrete implementation of a time-based RF cover."""

    async def _async_handle_command(self, command: str) -> None:
        """Handle sending a command to the remote entity."""
        await self.hass.services.async_call(
            REMOTE_DOMAIN,
            SERVICE_SEND_COMMAND,
            {
                ATTR_ENTITY_ID: self._remote_entity_id,
                "command": [command],
            },
            blocking=False,
        )
