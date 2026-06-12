"""Config flow for MAGPK Schedule integration."""
from __future__ import annotations

import re
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN, CONF_GROUP, LOGGER


class MagpkScheduleConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for MAGPK Schedule."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            group = user_input[CONF_GROUP].strip()
            
            # Simple validation: alphanumeric, dashes, and Cyrillic characters
            if not re.match(r"^[А-Яа-яA-Za-z0-9\-]+$", group):
                errors["base"] = "invalid_group_format"
            else:
                # Create the entry
                return self.async_create_entry(
                    title=f"Группа {group}",
                    data={CONF_GROUP: group},
                )

        # Show input form
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_GROUP): str,
                }
            ),
            errors=errors,
        )
