"""Global fixtures for rf_cover_time_based integration tests."""
import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

# This is the magic that loads the pytest-homeassistant-custom-component fixtures.
pytest_plugins = "pytest_homeassistant_custom_component"

# Import test constants from the same directory.
from .const import MOCK_CONFIG, MOCK_CONFIG_AWNING


# This fixture is used to automatically enable custom integrations for all tests.
# It's a best practice for custom component testing.
@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations defined in the test environment."""
    yield


@pytest.fixture
async def init_integration(hass: HomeAssistant) -> MockConfigEntry:
    """Set up the standard shutter integration for testing."""
    # Create a mock for the remote entity.
    hass.states.async_set(MOCK_CONFIG["remote_entity"], "on")

    # Create and set up the mock config entry.
    config_entry = MockConfigEntry(
        domain="rf_cover_time_based",
        title=MOCK_CONFIG["name"],
        data=MOCK_CONFIG,
        entry_id="test_entry_id_1",
    )
    config_entry.add_to_hass(hass)

    # The dependency on "remote" is now handled by manifest.json, so
    # we just need to set up our entry and HASS will load it and its deps.
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    return config_entry


@pytest.fixture
async def init_awning_integration(hass: HomeAssistant) -> MockConfigEntry:
    """Set up the awning integration for testing."""
    # Create a mock for the remote entity.
    hass.states.async_set(MOCK_CONFIG_AWNING["remote_entity"], "on")

    # Create and set up the mock config entry.
    config_entry = MockConfigEntry(
        domain="rf_cover_time_based",
        title=MOCK_CONFIG_AWNING["name"],
        data=MOCK_CONFIG_AWNING,
        entry_id="test_entry_id_awning",
    )
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    return config_entry
