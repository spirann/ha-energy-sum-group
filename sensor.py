"""Sensor platform for Energy Sum Group."""
from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_UNIT_OF_MEASUREMENT,
    CONF_NAME,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    UnitOfEnergy,
)
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, State, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.restore_state import ExtraStoredData, RestoreEntity
from homeassistant.util.unit_conversion import EnergyConverter

from .const import CONF_MEMBERS, RESET_RATIO

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the energy sum sensor from a config entry."""
    async_add_entities(
        [
            EnergySumSensor(
                entry.entry_id,
                entry.options[CONF_NAME],
                list(entry.options[CONF_MEMBERS]),
            )
        ]
    )


@dataclass
class EnergySumStoredData(ExtraStoredData):
    """Running total and each member's last seen value (kWh)."""

    total: float
    last_values: dict[str, float]

    def as_dict(self) -> dict[str, Any]:
        """Return a dict representation of the stored data."""
        return {"total": self.total, "last_values": self.last_values}

    @classmethod
    def from_dict(cls, restored: dict[str, Any]) -> EnergySumStoredData | None:
        """Initialize stored data from a dict."""
        try:
            return cls(
                float(restored["total"]),
                {k: float(v) for k, v in restored.get("last_values", {}).items()},
            )
        except (KeyError, TypeError, ValueError, AttributeError):
            return None


class EnergySumSensor(RestoreEntity, SensorEntity):
    """Sum of the members' increases, never decreasing."""

    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_suggested_display_precision = 3
    _attr_should_poll = False
    _attr_icon = "mdi:sigma"

    def __init__(self, unique_id: str, name: str, members: list[str]) -> None:
        """Initialize the sensor."""
        self._attr_unique_id = unique_id
        self._attr_name = name
        self._members = members
        self._total = 0.0
        self._last_values: dict[str, float] = {}
        self._warned: set[str] = set()

    @property
    def native_value(self) -> float:
        """Return the running total in kWh."""
        return round(self._total, 6)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the member entity ids."""
        return {"entity_id": self._members}

    @property
    def extra_restore_state_data(self) -> EnergySumStoredData:
        """Return the data to persist across restarts."""
        return EnergySumStoredData(self._total, dict(self._last_values))

    async def async_added_to_hass(self) -> None:
        """Restore the running total and start following the members."""
        await super().async_added_to_hass()

        if (extra := await self.async_get_last_extra_data()) is not None and (
            data := EnergySumStoredData.from_dict(extra.as_dict())
        ) is not None:
            self._total = data.total
            # Forget members that were removed from the group.
            self._last_values = {
                k: v for k, v in data.last_values.items() if k in self._members
            }

        # Catch up on whatever the members did while we weren't running.
        for entity_id in self._members:
            self._process(entity_id, self.hass.states.get(entity_id))

        self.async_on_remove(
            async_track_state_change_event(
                self.hass, self._members, self._async_member_changed
            )
        )

    @callback
    def _async_member_changed(self, event: Event[EventStateChangedData]) -> None:
        """Handle a member state change."""
        if self._process(event.data["entity_id"], event.data["new_state"]):
            self.async_write_ha_state()

    def _process(self, entity_id: str, state: State | None) -> bool:
        """Fold a member's new state into the total. Return True if it changed."""
        if entity_id == self.entity_id or state is None:
            return False
        if state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return False
        try:
            value = float(state.state)
        except ValueError:
            return False

        unit = state.attributes.get(ATTR_UNIT_OF_MEASUREMENT)
        if unit not in EnergyConverter.VALID_UNITS:
            if entity_id not in self._warned:
                self._warned.add(entity_id)
                _LOGGER.warning(
                    "%s: member %s has unit %s, which is not an energy unit; ignored",
                    self.entity_id,
                    entity_id,
                    unit,
                )
            return False
        value = EnergyConverter.convert(value, unit, UnitOfEnergy.KILO_WATT_HOUR)

        previous = self._last_values.get(entity_id)
        if previous is None:
            # First value seen for this member: it only sets the baseline.
            self._last_values[entity_id] = value
            return False
        if value >= previous:
            self._total += value - previous
        elif value < RESET_RATIO * previous:
            # Counter restarted: everything it counted since then is new.
            _LOGGER.debug(
                "%s: %s restarted from %s to %s kWh",
                self.entity_id,
                entity_id,
                previous,
                value,
            )
            self._total += value
        else:
            # Small dip: noise, keep the higher baseline.
            return False
        self._last_values[entity_id] = value
        return value != previous
