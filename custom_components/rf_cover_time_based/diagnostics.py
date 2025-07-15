"""Diagnostics support for RF Cover Time Based."""
from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers.device_registry import (
    async_get as async_get_device_registry,
)
from homeassistant.helpers.entity_registry import (
    EntityRegistry,
)
from homeassistant.helpers.entity_registry import (
    async_get as async_get_entity_registry,
)

from .const import CONF_REMOTE_ENTITY, DOMAIN


def _get_entity_diagnostic_data(entity_state: State | None) -> dict[str, Any]:
    """Return a standardized diagnostic dictionary for a given entity state."""
    if not entity_state:
        return {"state": "not_found", "attributes": {}}

    return {
        "state": entity_state.state,
        "attributes": dict(entity_state.attributes),
    }


def _get_redacted_config_entry(entry: ConfigEntry) -> dict[str, Any]:
    """
    Return a redacted config entry dictionary for diagnostics.

    This removes sensitive "command" keys for privacy.
    """
    entry_dict = entry.as_dict()
    if "data" in entry_dict:
        entry_dict["data"] = {
            key: value
            for key, value in entry_dict["data"].items()
            if "command" not in key
        }
    if "options" in entry_dict:
        entry_dict["options"] = {
            key: value
            for key, value in entry_dict["options"].items()
            if "command" not in key
        }
    return entry_dict


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    device_registry = async_get_device_registry(hass)
    entity_registry = async_get_entity_registry(hass)

    config = {**entry.data, **entry.options}

    device = device_registry.async_get_device(identifiers={(DOMAIN, entry.entry_id)})

    cover_entity_id = _find_entity_for_device(
        entity_registry, device.id if device else None, "cover"
    )
    cover_entity_state = (
        hass.states.get(cover_entity_id) if cover_entity_id else None
    )

    remote_entity_id = config.get(CONF_REMOTE_ENTITY)
    remote_entity_state = (
        hass.states.get(remote_entity_id) if remote_entity_id else None
    )

    return {
        "config_entry": _get_redacted_config_entry(entry),
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
    entity_registry: EntityRegistry, device_id: str | None, platform: str
) -> str | None:
    """Find the first entity of a given platform for a specific device."""
    if not device_id:
        return None

    for entity in entity_registry.entities.values():
        if entity.device_id == device_id and entity.platform == platform:
            return entity.entity_id

    return None
