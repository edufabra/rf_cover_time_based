"""Constants for the RF Cover Time Based integration."""
from __future__ import annotations

from typing import Final

# This is the domain of your integration. It must be unique.
DOMAIN: Final = "rf_cover_time_based"

# The version of the integration.
VERSION: Final = "0.1.0"

#Configuration keys used throughout the integration
CONF_NAME = "name"
CONF_REMOTE_ENTITY = "remote_entity"
CONF_TRAVELLING_TIME_DOWN = "travelling_time_down"
CONF_TRAVELLING_TIME_UP = "travelling_time_up"
CONF_OPEN_COMMAND = "open_command"
CONF_CLOSE_COMMAND = "close_command"
CONF_STOP_COMMAND = "stop_command"
CONF_DEVICE_CLASS = "device_class"
