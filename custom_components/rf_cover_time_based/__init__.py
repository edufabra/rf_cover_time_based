# custom_components/rf_cover_time_based/__init__.py

"""The RF Cover Time Based integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

# Define the platforms that this integration will create.
PLATFORMS: list[Platform] = [Platform.COVER]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up from a config entry."""
    # This is the central point to forward the setup to the platforms.
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Add an update listener to the config entry for options flow.
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # This is the central point to forward the unload to the platforms.
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle an options update by reloading the entry."""
    await hass.config_entries.async_reload(entry.entry_id)
