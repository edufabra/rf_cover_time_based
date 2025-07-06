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

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class RfCoverTimeBasedConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for RF Cover Time Based."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if not self.hass.states.async_all("remote"):
            return self.async_abort(reason="no_remotes_found")

        if user_input is None:
            # Show the form for the first time
            data_schema = vol.Schema(
                {
                    vol.Required("name"): str,
                    vol.Required("remote_entity"): EntitySelector(
                        EntitySelectorConfig(domain="remote")
                    ),
                    vol.Required("open_command"): str,
                    vol.Required("close_command"): str,
                    vol.Required("stop_command"): str,
                    vol.Required("travelling_time_down", default=10): int,
                    vol.Required("travelling_time_up", default=10): int,
                    vol.Required("device_class", default="shutter"): SelectSelector(
                        SelectSelectorConfig(
                            options=[cls.value for cls in CoverDeviceClass],
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    ),
                }
            )
            return self.async_show_form(step_id="user", data_schema=data_schema)

        # Use the name as the unique_id to prevent duplicates.
        await self.async_set_unique_id(user_input["name"])
        self._abort_if_unique_id_configured()

        title = user_input["name"]
        return self.async_create_entry(title=title, data=user_input)

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

        # Define the schema for the options form. Note that 'name' is not included.
        options_schema = vol.Schema(
            {
                vol.Required(
                    "remote_entity",
                    default=self.options.get("remote_entity"),
                ): EntitySelector(EntitySelectorConfig(domain="remote")),
                vol.Required(
                    "open_command", default=self.options.get("open_command")
                ): str,
                vol.Required(
                    "close_command",
                    default=self.options.get("close_command"),
                ): str,
                vol.Required(
                    "stop_command", default=self.options.get("stop_command")
                ): str,
                vol.Required(
                    "travelling_time_down",
                    default=self.options.get("travelling_time_down"),
                ): int,
                vol.Required(
                    "travelling_time_up",
                    default=self.options.get("travelling_time_up"),
                ): int,
                vol.Required(
                    "device_class",
                    default=self.options.get("device_class", "shutter"),
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=[cls.value for cls in CoverDeviceClass],
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
            }
        )

        return self.async_show_form(step_id="init", data_schema=options_schema)
