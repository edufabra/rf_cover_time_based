"""Diagnostics support for RF Cover Time Based."""
from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers.device_registry import (
    DeviceEntry,
)
from homeassistant.helpers.device_registry import (
    # FIX 1: Import the modern helper function for getting the device registry.
    async_get as async_get_device_registry,
)
from homeassistant.helpers.entity_registry import (
    # FIX 2: Import the modern helper function for getting the entity registry.
    async_get as async_get_entity_registry,
)

from .const import DOMAIN


def _get_entity_diagnostic_data(entity_state: State | None) -> dict[str, Any]:
    """
    Return a standardized diagnostic dictionary for a given entity state.

    This helper function encapsulates the logic for safely extracting state
    and attributes, preventing code duplication.
    """
    if not entity_state:
        return {"state": "not_found", "attributes": {}}

    return {
        "state": entity_state.state,
        "attributes": dict(entity_state.attributes),
    }


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    # REFACTOR: Use the imported helper function to get the device registry.
    device_registry = async_get_device_registry(hass)
    entity_registry = async_get_entity_registry(hass)

    device = device_registry.async_get_device(identifiers={(DOMAIN, entry.entry_id)})

    # Find the cover entity associated with this device
    cover_entity_id = _find_entity_for_device(entity_registry, device, "cover")
    cover_entity_state = hass.states.get(cover_entity_id) if cover_entity_id else None

    # Get the state of the remote gateway entity
    remote_entity_id = entry.data.get("remote_entity")
    remote_entity_state = (
        hass.states.get(remote_entity_id) if remote_entity_id else None
    )

    return {
        "config_entry": entry.as_dict(),
        "cover_entity": {
            "entity_id": cover_entity_id,
            **_get_entity_diagnostic_data(cover_entity_state),
        },
        "remote_gateway": {
            "entity_id": remote_entity_id,
            **_get_entity_diagnostic_data(remote_entity_state),
        },
    }


def _find_entity_for_device(
    entity_registry, device: DeviceEntry | None, platform: str
) -> str | None:
    """Find the first entity of a given platform for a device."""
    if not device:
        return None

    # REFACTOR: The entity_registry is now passed in, making this a pure function.
    for entity in entity_registry.entities.values():
        if entity.device_id == device.id and entity.platform == platform:
            return entity.entity_id
    return None
