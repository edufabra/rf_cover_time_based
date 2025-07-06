"""Global fixtures for rf_cover_time_based tests."""
from unittest.mock import patch

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

# Import test constants from the same directory.
# All imports should be at the top of the file to resolve the E402 error.
from .const import MOCK_CONFIG, MOCK_CONFIG_AWNING


# This fixture is used to prevent Home Assistant from attempting to create
# real network connections during tests. It's a standard practice.
@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations defined in the test environment."""
    yield


# This fixture patches the async_setup_entry to prevent the component from
# actually being set up. This is useful for more isolated unit tests.
@pytest.fixture
def mock_setup_entry():
    """Override async_setup_entry."""
    with patch(
        "custom_components.rf_cover_time_based.async_setup_entry", return_value=True
    ) as mock_setup:
        yield mock_setup


# Fixture to provide the standard mock configuration for tests.
@pytest.fixture(name="mock_config")
def mock_config_fixture():
    """Return a default mock config for a shutter."""
    return MOCK_CONFIG


# Fixture to provide the mock configuration for an awning.
@pytest.fixture(name="mock_config_awning")
def mock_config_awning_fixture():
    """Return a default mock config for an awning."""
    return MOCK_CONFIG_AWNING


# --- New Fixtures to Fix the Errors ---


@pytest.fixture
async def init_integration(hass: HomeAssistant, mock_config: dict) -> MockConfigEntry:
    """Set up the integration for testing with a standard shutter config."""
    # Create a mock config entry using the standard shutter configuration
    entry = MockConfigEntry(
        domain="rf_cover_time_based",
        data=mock_config,
        entry_id="test-shutter",
    )
    # Add the entry to the test instance of Home Assistant
    entry.add_to_hass(hass)

    # Set up the integration from the config entry
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Return the mock entry for use in tests
    return entry


@pytest.fixture
async def init_awning_integration(
    hass: HomeAssistant, mock_config_awning: dict
) -> MockConfigEntry:
    """Set up the integration for testing with an awning config."""
    # Create a mock config entry using the awning configuration
    entry = MockConfigEntry(
        domain="rf_cover_time_based",
        data=mock_config_awning,
        entry_id="test-awning",
    )
    # Add the entry to the test instance of Home Assistant
    entry.add_to_hass(hass)

    # Set up the integration from the config entry
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Return the mock entry for use in tests
    return entry
