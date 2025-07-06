# tests/test_diagnostics.py

"""Test the RF Cover Time Based diagnostics."""
from __future__ import annotations

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from syrupy import SnapshotAssertion

# Import the 'props' filter from syrupy
from syrupy.filters import props

from custom_components.rf_cover_time_based.diagnostics import (
    async_get_config_entry_diagnostics,
)


async def test_entry_diagnostics(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test config entry diagnostics."""
    diagnostics_data = await async_get_config_entry_diagnostics(
        hass, init_integration
    )

    # Assert against the snapshot, excluding dynamic fields like timestamps.
    # This makes the test robust and independent of when it is run.
    assert diagnostics_data == snapshot(exclude=props("created_at", "modified_at"))
    