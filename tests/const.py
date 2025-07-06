"""Constants for rf_cover_time_based tests."""

MOCK_CONFIG = {
    "name": "Test Shutter",
    "remote_entity": "remote.test_gateway",
    "travelling_time_down": 10,
    "travelling_time_up": 10,
    "open_command": "b64:open_code",
    "close_command": "b64:close_code",
    "stop_command": "b64:stop_code",
    "device_class": "shutter",
}

MOCK_CONFIG_AWNING = {
    **MOCK_CONFIG,
    "name": "Test Awning",
    "device_class": "awning",
}
