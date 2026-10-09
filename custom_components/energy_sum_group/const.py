"""Constants for the Energy Sum Group integration."""

from homeassistant.const import Platform

DOMAIN = "energy_sum_group"

CONF_MEMBERS = "members"

# A member dropping below this fraction of its previous value is treated as
# a counter restart, the same threshold Home Assistant's long-term statistics
# use for total_increasing sensors. Smaller dips are ignored as noise.
RESET_RATIO = 0.9

PLATFORMS = [Platform.SENSOR]
