"""Test the cover platform for RF Cover Time Based."""
from datetime import timedelta
from unittest.mock import patch

from freezegun.api import FrozenDateTimeFactory
from homeassistant.components.cover import (
    ATTR_POSITION,
)
from homeassistant.components.cover import (
    DOMAIN as COVER_DOMAIN,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    EVENT_CALL_SERVICE,
    SERVICE_CLOSE_COVER,
    SERVICE_OPEN_COVER,
    SERVICE_STOP_COVER,
    STATE_UNAVAILABLE,
)
from homeassistant.core import Event, HomeAssistant, State
from homeassistant.helpers.entity_registry import async_get
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_capture_events,
    async_fire_time_changed,
)

from custom_components.rf_cover_time_based.const import DOMAIN
from tests.const import MOCK_CONFIG, MOCK_CONFIG_AWNING

ENTITY_ID = f"{COVER_DOMAIN}.test_shutter"
ENTITY_ID_AWNING = f"{COVER_DOMAIN}.test_awning"


async def test_shutter_commands(
    hass: HomeAssistant, init_integration: MockConfigEntry, freezer: FrozenDateTimeFactory
) -> None:
    """Test the service calls for a standard shutter."""
    hass.states.async_set(MOCK_CONFIG["remote_entity"], "on")
    await hass.async_block_till_done()

    events: list[Event] = async_capture_events(hass, EVENT_CALL_SERVICE)

    # Test closing from the default open state
    await hass.services.async_call(
        COVER_DOMAIN, SERVICE_CLOSE_COVER, {ATTR_ENTITY_ID: ENTITY_ID}, blocking=True
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
        COVER_DOMAIN, SERVICE_OPEN_COVER, {ATTR_ENTITY_ID: ENTITY_ID}, blocking=True
    )
    await hass.async_block_till_done()
    assert any(
        event.data["domain"] == "remote"
        and event.data["service"] == "send_command"
        and event.data["service_data"]["command"] == [MOCK_CONFIG["open_command"]]
        for event in events
    )


async def test_awning_commands_inverted(
    hass: HomeAssistant, init_awning_integration: MockConfigEntry, freezer: FrozenDateTimeFactory
) -> None:
    """Test that the service calls for an awning are inverted."""
    hass.states.async_set(MOCK_CONFIG_AWNING["remote_entity"], "on")
    await hass.async_block_till_done()

    events: list[Event] = async_capture_events(hass, EVENT_CALL_SERVICE)

    # Test closing (which should send the 'open' command for an awning)
    await hass.services.async_call(
        COVER_DOMAIN,
        SERVICE_CLOSE_COVER,
        {ATTR_ENTITY_ID: ENTITY_ID_AWNING},
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

    # Let the cover "travel" to the closed state
    freezer.tick(timedelta(seconds=MOCK_CONFIG_AWNING["travelling_time_down"]))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    events.clear()

    # Test opening (which should send the 'close' command for an awning)
    await hass.services.async_call(
        COVER_DOMAIN,
        SERVICE_OPEN_COVER,
        {ATTR_ENTITY_ID: ENTITY_ID_AWNING},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert any(
        event.data["domain"] == "remote"
        and event.data["service"] == "send_command"
        and event.data["service_data"]["command"]
        == [MOCK_CONFIG_AWNING["close_command"]]
        for event in events
    )


async def test_initial_state_and_device_class(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Test the initial state and device class of the cover."""
    entity_registry = async_get(hass)
    entry = entity_registry.async_get(ENTITY_ID)

    assert entry
    assert entry.original_device_class == "shutter"

    state = hass.states.get(ENTITY_ID)
    assert state
    assert state.attributes.get("device_class") == "shutter"


async def test_availability(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Test the availability of the cover based on the remote entity."""
    hass.states.async_set(MOCK_CONFIG["remote_entity"], "on")
    await hass.async_block_till_done()
    state = hass.states.get(ENTITY_ID)
    assert state is not None
    assert state.state != STATE_UNAVAILABLE

    hass.states.async_set(MOCK_CONFIG["remote_entity"], STATE_UNAVAILABLE)
    await hass.async_block_till_done()

    state = hass.states.get(ENTITY_ID)
    assert state is not None
    assert state.state == STATE_UNAVAILABLE

    hass.states.async_set(MOCK_CONFIG["remote_entity"], "on")
    await hass.async_block_till_done()

    state = hass.states.get(ENTITY_ID)
    assert state is not None
    assert state.state != STATE_UNAVAILABLE


async def test_updater_loop_and_stop(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test that the updater loop correctly updates position and stops."""
    mock_restored_state = State(
        ENTITY_ID,
        "closed",
        {ATTR_POSITION: 0},
    )

    with patch(
        "homeassistant.helpers.restore_state.RestoreEntity.async_get_last_state",
        return_value=mock_restored_state,
    ):
        entry = MockConfigEntry(
            domain=DOMAIN,
            data=MOCK_CONFIG,
            entry_id="test_entry_id_1",
            unique_id="test_unique_id",
        )
        entry.add_to_hass(hass)
        assert await async_setup_component(hass, DOMAIN, {})
        await hass.async_block_till_done()

    hass.states.async_set(MOCK_CONFIG["remote_entity"], "on")
    await hass.async_block_till_done()

    state = hass.states.get(ENTITY_ID)
    assert state.attributes["current_position"] == 0

    # 1. TEST THE UPDATER LOOP
    await hass.services.async_call(
        COVER_DOMAIN, SERVICE_OPEN_COVER, {ATTR_ENTITY_ID: ENTITY_ID}, blocking=True
    )
    await hass.async_block_till_done()

    # Advance time by 5 seconds (halfway through the 10s travel)
    freezer.tick(timedelta(seconds=5))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    state = hass.states.get(ENTITY_ID)
    assert state.attributes["current_position"] == 50

    # Advance time by another 5 seconds (should reach the end)
    freezer.tick(timedelta(seconds=5))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    state = hass.states.get(ENTITY_ID)
    assert state.attributes["current_position"] == 100

    # 2. TEST THE STOP FUNCTION
    await hass.services.async_call(
        COVER_DOMAIN, SERVICE_CLOSE_COVER, {ATTR_ENTITY_ID: ENTITY_ID}, blocking=True
    )
    await hass.async_block_till_done()

    freezer.tick(timedelta(seconds=2))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    state = hass.states.get(ENTITY_ID)
    assert state.attributes["current_position"] == 80

    await hass.services.async_call(
        COVER_DOMAIN, SERVICE_STOP_COVER, {ATTR_ENTITY_ID: ENTITY_ID}, blocking=True
    )
    await hass.async_block_till_done()
    position_after_stop = hass.states.get(ENTITY_ID).attributes["current_position"]
    assert position_after_stop == 80

    freezer.tick(timedelta(seconds=5))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    state = hass.states.get(ENTITY_ID)
    assert state.attributes["current_position"] == position_after_stop