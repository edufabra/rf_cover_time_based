"""Test the RF Cover Time Based diagnostics."""
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from syrupy import SnapshotAssertion

from custom_components.rf_cover_time_based.diagnostics import (
    async_get_config_entry_diagnostics,
)


async def test_entry_diagnostics(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test config entry diagnostics."""
    # The init_integration fixture is already setting up the entry.
    # We can directly call the diagnostics function.
    diagnostics_data = await async_get_config_entry_diagnostics(
        hass, init_integration
    )

    # Use syrupy snapshot testing to verify the output.
    # This creates a snapshot file on the first run, and compares against it
    # on subsequent runs. It's a powerful way to test complex data structures.
    assert diagnostics_data == snapshot
