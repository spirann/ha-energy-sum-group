"""Config flow for Energy Sum Group."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN, SensorDeviceClass
from homeassistant.const import CONF_NAME
from homeassistant.helpers import selector
from homeassistant.helpers.schema_config_entry_flow import (
    SchemaCommonFlowHandler,
    SchemaConfigFlowHandler,
    SchemaFlowError,
    SchemaFlowFormStep,
)

from .const import CONF_MEMBERS, DOMAIN

OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_MEMBERS): selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain=SENSOR_DOMAIN,
                device_class=SensorDeviceClass.ENERGY,
                multiple=True,
            )
        ),
    }
)

CONFIG_SCHEMA = vol.Schema(
    {vol.Required(CONF_NAME): selector.TextSelector()}
).extend(OPTIONS_SCHEMA.schema)


async def _validate(
    handler: SchemaCommonFlowHandler, user_input: dict[str, Any]
) -> dict[str, Any]:
    if not user_input.get(CONF_MEMBERS):
        raise SchemaFlowError("need_one_member")
    return user_input


CONFIG_FLOW = {"user": SchemaFlowFormStep(CONFIG_SCHEMA, validate_user_input=_validate)}
OPTIONS_FLOW = {"init": SchemaFlowFormStep(OPTIONS_SCHEMA, validate_user_input=_validate)}


class EnergySumGroupConfigFlow(SchemaConfigFlowHandler, domain=DOMAIN):
    """Handle a config flow for Energy Sum Group."""

    config_flow = CONFIG_FLOW
    options_flow = OPTIONS_FLOW

    def async_config_entry_title(self, options: Mapping[str, Any]) -> str:
        """Return the config entry title."""
        return str(options[CONF_NAME])
