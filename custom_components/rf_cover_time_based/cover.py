"""The cover platform for the RF Cover Time Based integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

# Import the actual entity class from your main implementation file.
from .time_based_cover import TimeBasedCover


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """
    Set up the cover entity from a config entry.

    This function is called by Home Assistant to set up the cover platform.
    It's responsible for creating and adding the cover entity.
    """
    # The fix is here: Pass both `hass` and `config_entry` to the constructor,
    # which resolves the TypeError seen in the test logs.
    async_add_entities([TimeBasedCover(hass, config_entry)])
