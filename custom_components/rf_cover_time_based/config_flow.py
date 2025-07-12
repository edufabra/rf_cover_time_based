# custom_components/rf_cover_time_based/config_flow.py
"""Config flow for RF Cover Time Based integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components.cover import CoverDeviceClass
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    CONF_CLOSE_COMMAND,
    CONF_DEVICE_CLASS,
    CONF_NAME,
    CONF_OPEN_COMMAND,
    CONF_REMOTE_ENTITY,
    CONF_STOP_COMMAND,
    CONF_TRAVELLING_TIME_DOWN,
    CONF_TRAVELLING_TIME_UP,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


def _build_options_schema(options: dict[str, Any]) -> vol.Schema:
    """Build the schema for the options form, pre-populating with existing values."""
    return vol.Schema(
        {
            vol.Required(
                CONF_REMOTE_ENTITY,
                default=options.get(CONF_REMOTE_ENTITY),
            ): EntitySelector(EntitySelectorConfig(domain="remote")),
            vol.Required(
                CONF_OPEN_COMMAND, default=options.get(CONF_OPEN_COMMAND)
            ): str,
            vol.Required(
                CONF_CLOSE_COMMAND,
                default=options.get(CONF_CLOSE_COMMAND),
            ): str,
            vol.Required(
                CONF_STOP_COMMAND, default=options.get(CONF_STOP_COMMAND)
            ): str,
            vol.Required(
                CONF_TRAVELLING_TIME_DOWN,
                default=options.get(CONF_TRAVELLING_TIME_DOWN, 10),
            ): int,
            vol.Required(
                CONF_TRAVELLING_TIME_UP,
                default=options.get(CONF_TRAVELLING_TIME_UP, 10),
            ): int,
            vol.Required(
                CONF_DEVICE_CLASS,
                default=options.get(CONF_DEVICE_CLASS, "shutter"),
            ): SelectSelector(
                SelectSelectorConfig(
                    options=[cls.value for cls in CoverDeviceClass],
                    mode=SelectSelectorMode.DROPDOWN,
                )
            ),
        }
    )


class RfCoverTimeBasedConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for RF Cover Time Based."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if not self.hass.states.async_all("remote"):
            return self.async_abort(reason="no_remotes_found")

        if user_input is not None:
            # Set the unique_id based on the name to prevent duplicates.
            await self.async_set_unique_id(user_input[CONF_NAME])
            self._abort_if_unique_id_configured()

            # Separate the configuration into data (immutable) and options (mutable).
            name = user_input.pop(CONF_NAME)

            # The 'data' dictionary should be minimal.
            config_data = {}

            # The rest of the user input becomes the initial options.
            config_options = user_input

            return self.async_create_entry(
                title=name, data=config_data, options=config_options
            )

        # Build the initial user schema, which includes the name field
        user_schema = vol.Schema({vol.Required(CONF_NAME): str}).extend(
            _build_options_schema({}).schema
        )

        return self.async_show_form(step_id="user", data_schema=user_schema)

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return RfCoverTimeBasedOptionsFlow(config_entry)


class RfCoverTimeBasedOptionsFlow(config_entries.OptionsFlowWithConfigEntry):
    """Handle an options flow for RF Cover Time Based."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            # This creates an entry in the `options` dictionary of the ConfigEntry
            return self.async_create_entry(title="", data=user_input)

        # Reuse the schema builder, passing the existing options
        options_schema = _build_options_schema(self.options)

        return self.async_show_form(step_id="init", data_schema=options_schema)