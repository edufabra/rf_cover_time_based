"""Test the cover platform for RF Cover Time Based."""
from datetime import timedelta
from unittest.mock import patch

from freezegun.api import FrozenDateTimeFactory
import pytest
from homeassistant.components.cover import (
    ATTR_POSITION,
    DOMAIN as COVER_DOMAIN,
    SERVICE_CLOSE_COVER,
    SERVICE_OPEN_COVER,
    SERVICE_SET_COVER_POSITION,
    SERVICE_STOP_COVER,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    EVENT_CALL_SERVICE,
    STATE_UNAVAILABLE,
)
from homeassistant.core import Event, HomeAssistant, State
from homeassistant.helpers.entity_registry import EntityRegistry, async_get
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_capture_events,
    async_fire_time_changed,
)

from custom_components.rf_cover_time_based.const import DOMAIN
from tests.const import MOCK_CONFIG, MOCK_CONFIG_AWNING


def _get_entity_id(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> str | None:
    """Get the entity ID for the cover associated with a config entry."""
    entity_registry: EntityRegistry = async_get(hass)
    return entity_registry.async_get_entity_id(
        COVER_DOMAIN, DOMAIN, config_entry.entry_id
    )


async def test_shutter_commands(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test the service calls for a standard shutter."""
    # Dynamically get the entity ID to make the test robust
    entity_id = _get_entity_id(hass, init_integration)
    assert entity_id is not None

    # Make the remote available
    hass.states.async_set(MOCK_CONFIG["remote_entity"], "on")
    await hass.async_block_till_done()

    events: list[Event] = async_capture_events(hass, EVENT_CALL_SERVICE)

    # Test closing from the default open state
    await hass.services.async_call(
        COVER_DOMAIN, SERVICE_CLOSE_COVER, {ATTR_ENTITY_ID: entity_id}, blocking=True
    )
    await hass.async_block_till_done()
    assert any(
        event.data["domain"] == "remote"
        and event.data["service"] == "send_command"
        and event.data["service_data"]["command"] == [MOCK_CONFIG["close_command"]]
        for event in events
    )

    # Let the cover "travel" to the closed state
    freezer.tick(timedelta(seconds=MOCK_CONFIG["travelling_time_down"]))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    events.clear()

    # Now, test the open command from the known closed state
    await hass.services.async_call(
        COVER_DOMAIN, SERVICE_OPEN_COVER, {ATTR_ENTITY_ID: entity_id}, blocking=True
    )
    await hass.async_block_till_done()
    assert any(
        event.data["domain"] == "remote"
        and event.data["service"] == "send_command"
        and event.data["service_data"]["command"] == [MOCK_CONFIG["open_command"]]
        for event in events
    )


async def test_awning_commands_inverted(
    hass: HomeAssistant,
    init_awning_integration: MockConfigEntry,
) -> None:
    """Test that the service calls for an awning are inverted."""
    entity_id = _get_entity_id(hass, init_awning_integration)
    assert entity_id is not None

    hass.states.async_set(MOCK_CONFIG_AWNING["remote_entity"], "on")
    await hass.async_block_till_done()

    events: list[Event] = async_capture_events(hass, EVENT_CALL_SERVICE)

    # Test closing (which should send the 'open' command for an awning)
    await hass.services.async_call(
        COVER_DOMAIN,
        SERVICE_CLOSE_COVER,
        {ATTR_ENTITY_ID: entity_id},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert any(
        event.data["domain"] == "remote"
        and event.data["service"] == "send_command"
        and event.data["service_data"]["command"]
        == [MOCK_CONFIG_AWNING["open_command"]]
        for event in events
    )


async def test_initial_state_and_device_class(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Test the initial state and device class of the cover."""
    entity_registry = async_get(hass)
    entity_id = _get_entity_id(hass, init_integration)
    assert entity_id is not None

    entry = entity_registry.async_get(entity_id)
    assert entry
    assert entry.original_device_class == "shutter"

    state = hass.states.get(entity_id)
    assert state
    assert state.attributes.get("device_class") == "shutter"


async def test_availability(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Test the availability of the cover based on the remote entity."""
    entity_id = _get_entity_id(hass, init_integration)
    assert entity_id is not None

    # Test when remote becomes available
    hass.states.async_set(MOCK_CONFIG["remote_entity"], "on")
    await hass.async_block_till_done()
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state != STATE_UNAVAILABLE

    # Test when remote becomes unavailable
    hass.states.async_set(MOCK_CONFIG["remote_entity"], STATE_UNAVAILABLE)
    await hass.async_block_till_done()
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == STATE_UNAVAILABLE

    # Test when remote becomes available again
    hass.states.async_set(MOCK_CONFIG["remote_entity"], "on")
    await hass.async_block_till_done()
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state != STATE_UNAVAILABLE


@pytest.mark.parametrize(
    ("start_pos", "duration", "expected_pos", "direction"),
    [
        (0, 5, 50, "open"),  # Start at 0, open for 5s, expect 50%
        (100, 2, 80, "close"),  # Start at 100, close for 2s, expect 80%
    ],
)
async def test_travel_and_manual_stop(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
    start_pos: int,
    duration: int,
    expected_pos: int,
    direction: str,
) -> None:
    """Test starting a full travel and stopping it manually."""
    entity_id = _get_entity_id(hass, init_integration)
    assert entity_id is not None

    # Patch state restoration to start at a known position
    mock_restored_state = State(entity_id, "unknown", {ATTR_POSITION: start_pos})
    with patch(
        "homeassistant.helpers.restore_state.RestoreEntity.async_get_last_state",
        return_value=mock_restored_state,
    ):
        # Reload the entry to apply the restored state
        await hass.config_entries.async_reload(init_integration.entry_id)
        await hass.async_block_till_done()

    # Make remote available and check initial position
    hass.states.async_set(MOCK_CONFIG["remote_entity"], "on")
    await hass.async_block_till_done()
    state = hass.states.get(entity_id)
    assert state.attributes["current_position"] == start_pos

    # Start the cover moving
    service_to_call = SERVICE_OPEN_COVER if direction == "open" else SERVICE_CLOSE_COVER
    await hass.services.async_call(
        COVER_DOMAIN, service_to_call, {ATTR_ENTITY_ID: entity_id}, blocking=True
    )
    await hass.async_block_till_done()

    # Advance time partway through the travel
    freezer.tick(timedelta(seconds=duration))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    # Stop the cover manually
    await hass.services.async_call(
        COVER_DOMAIN, SERVICE_STOP_COVER, {ATTR_ENTITY_ID: entity_id}, blocking=True
    )
    await hass.async_block_till_done()

    # Check that the position is correct after stopping
    state = hass.states.get(entity_id)
    assert state.attributes["current_position"] == expected_pos


@pytest.mark.parametrize(
    ("start_pos", "target_pos"),
    [
        (0, 50),  # Open to 50%
        (100, 25),  # Close to 25%
        (20, 80),  # Open from 20% to 80%
    ],
)
async def test_set_position_and_auto_stop(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
    start_pos: int,
    target_pos: int,
) -> None:
    """Test that the cover travels to a set position and stops automatically."""
    entity_id = _get_entity_id(hass, init_integration)
    assert entity_id is not None

    # Patch state restoration to start at a known position
    mock_restored_state = State(entity_id, "unknown", {ATTR_POSITION: start_pos})
    with patch(
        "homeassistant.helpers.restore_state.RestoreEntity.async_get_last_state",
        return_value=mock_restored_state,
    ):
        await hass.config_entries.async_reload(init_integration.entry_id)
        await hass.async_block_till_done()

    hass.states.async_set(MOCK_CONFIG["remote_entity"], "on")
    await hass.async_block_till_done()

    # Call the set_cover_position service
    await hass.services.async_call(
        COVER_DOMAIN,
        SERVICE_SET_COVER_POSITION,
        {ATTR_ENTITY_ID: entity_id, ATTR_POSITION: target_pos},
        blocking=True,
    )
    await hass.async_block_till_done()

    # Advance time enough for the travel to complete
    travel_duration = (
        abs(target_pos - start_pos) / 100 * MOCK_CONFIG["travelling_time_up"]
    )
    freezer.tick(timedelta(seconds=travel_duration + 1))  # Add a 1s buffer
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    # Check that the position is the target position
    state = hass.states.get(entity_id)
    assert state.attributes["current_position"] == target_pos
