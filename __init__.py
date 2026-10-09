"""Energy Sum Group: a spike-free sum of energy meters.

A plain sensor group sums the members' raw counters, so when one member's
counter restarts (device reboot, firmware update) the group's total drops,
long-term statistics read that as a reset of the whole group, and the full
total is booked as consumption in one hour.

This helper sums each member's *increase* instead: it remembers every
member's last value, skips members while they are unavailable, and counts a
restarted counter from zero, exactly as statistics treat each meter on its
own. The resulting total never goes down.
"""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import PLATFORMS


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up an energy sum group from a config entry."""
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload an energy sum group config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry when its options change (e.g. members edited)."""
    await hass.config_entries.async_reload(entry.entry_id)
