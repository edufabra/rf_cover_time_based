"""Diagnostics support for RF Cover Time Based."""
from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

# Dades que volem amagar als diagnòstics per seguretat
TO_REDACT = {
    "open_command",
    "close_command",
    "stop_command",
}

async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    config_data = {**entry.data, **entry.options}

    entity_registry = er.async_get(hass)
    entities = er.async_entries_for_config_entry(entity_registry, entry.entry_id)

    cover_entity_id = None
    cover_entity_state = None
    if entities:
        cover_entity_id = entities[0].entity_id
        cover_entity_state = hass.states.get(cover_entity_id)

    remote_entity_id = config_data.get("remote_entity")
    remote_state = hass.states.get(remote_entity_id) if remote_entity_id else None

    diagnostics_data = {
        "config_entry_id": entry.entry_id,
        "config_data": config_data,
        "cover_entity": {
            "entity_id": cover_entity_id,
            "state": cover_entity_state.state if cover_entity_state else "not_found",
            "attributes": dict(cover_entity_state.attributes) if cover_entity_state else {},
        },
        "remote_gateway": {
            "entity_id": remote_entity_id,
            "state": remote_state.state if remote_state else "not_configured",
            "attributes": dict(remote_state.attributes) if remote_state else {},
        },
    }

    for key in TO_REDACT:
        if key in diagnostics_data["config_data"]:
            diagnostics_data["config_data"][key] = "**REDACTED**"

    return diagnostics_data
