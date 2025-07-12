"""Test the RF Cover Time Based config flow."""
from unittest.mock import patch

import pytest
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.rf_cover_time_based.const import DOMAIN
from tests.const import MOCK_CONFIG


@pytest.fixture(autouse=True)
def mock_setup_entry() -> patch:
    """Override async_setup_entry to prevent actual setup in tests."""
    with patch(
        "custom_components.rf_cover_time_based.async_setup_entry", return_value=True
    ) as mock_setup:
        yield mock_setup


async def test_full_flow_implementation(hass: HomeAssistant) -> None:
    """Test the full config flow from user initiation to completion."""
    # Pre-create a remote entity for the flow to find
    hass.states.async_set("remote.test_gateway", "on")

    # Step 1: Start the flow, simulating a user clicking "Add Integration"
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    # We should get a form back
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    # Step 2: Simulate the user filling out the form and submitting
    # Use .copy() to prevent mutating the original MOCK_CONFIG
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=MOCK_CONFIG.copy(),
    )
    await hass.async_block_till_done()

    # Assert the flow finished and created an entry with the correct data
    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["title"] == MOCK_CONFIG["name"]
    assert result2["data"] == {}  # Data should be empty now

    # Create a copy of the mock config without the name to compare options
    expected_options = MOCK_CONFIG.copy()
    del expected_options["name"]
    assert result2["options"] == expected_options


async def test_config_flow_aborts_if_no_remotes(hass: HomeAssistant) -> None:
    """Test that the config flow aborts if no remote entities are found."""
    # Ensure no remote entities exist
    assert not hass.states.async_all("remote")

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "no_remotes_found"


async def test_config_flow_aborts_if_already_configured(hass: HomeAssistant) -> None:
    """Test that the config flow aborts if a device with the same name exists."""
    # Pre-create a remote entity
    hass.states.async_set("remote.test_gateway", "on")

    # Set up an initial entry. Use .copy() to prevent data mutation.
    init_result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}, data=MOCK_CONFIG.copy()
    )
    assert init_result["type"] == FlowResultType.CREATE_ENTRY

    # Try to configure a second time with the same data. Use .copy() again.
    second_result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}, data=MOCK_CONFIG.copy()
    )

    assert second_result["type"] == FlowResultType.ABORT
    assert second_result["reason"] == "already_configured"


async def test_options_flow(hass: HomeAssistant) -> None:
    """Test that the options flow can successfully update the configuration."""
    # Pre-create a remote entity
    hass.states.async_set("remote.test_gateway", "on")

    # 1. Set up the initial config entry. Use .copy().
    init_result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}, data=MOCK_CONFIG.copy()
    )
    await hass.async_block_till_done()

    assert init_result["type"] == FlowResultType.CREATE_ENTRY
    config_entry = init_result["result"]
    assert config_entry is not None

    # 2. Start the options flow
    options_result = await hass.config_entries.options.async_init(
        config_entry.entry_id
    )
    assert options_result["type"] == FlowResultType.FORM
    assert options_result["step_id"] == "init"

    # 3. Submit new data to the options flow
    new_travel_time = 25
    # Get the current options and modify them
    options_data = config_entry.options.copy()
    options_data["travelling_time_down"] = new_travel_time

    updated_options_result = await hass.config_entries.options.async_configure(
        options_result["flow_id"],
        user_input=options_data,
    )
    await hass.async_block_till_done()

    # 4. Assert that the flow finished and the config entry's options were updated
    assert updated_options_result["type"] == FlowResultType.CREATE_ENTRY
    assert config_entry.options["travelling_time_down"] == new_travel_time
    # Verify that the original data is still empty and unchanged
    assert config_entry.data == {}
