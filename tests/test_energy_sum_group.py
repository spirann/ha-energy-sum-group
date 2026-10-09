"""Tests for Energy Sum Group."""
from homeassistant import config_entries
from homeassistant.core import HomeAssistant, State
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    mock_restore_cache_with_extra_data,
)

from custom_components.energy_sum_group.const import DOMAIN

KWH = {"unit_of_measurement": "kWh", "device_class": "energy"}
WH = {"unit_of_measurement": "Wh", "device_class": "energy"}
SUM = "sensor.house_energy"


async def _setup(hass: HomeAssistant, members=("sensor.a", "sensor.b")):
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="House energy",
        options={"name": "House energy", "members": list(members)},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def _set(hass, entity_id, value, attrs=KWH):
    hass.states.async_set(entity_id, value, attrs)
    await hass.async_block_till_done()


def _total(hass) -> float:
    return float(hass.states.get(SUM).state)


async def test_config_flow(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"name": "House energy", "members": []}
    )
    assert result["errors"] == {"base": "need_one_member"}
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"name": "House energy", "members": ["sensor.a"]}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "House energy"
    await hass.async_block_till_done()
    state = hass.states.get(SUM)
    assert state.state == "0.0"
    assert state.attributes["state_class"] == "total_increasing"
    assert state.attributes["unit_of_measurement"] == "kWh"


async def test_options_flow_changes_members(hass: HomeAssistant) -> None:
    entry = await _setup(hass, ["sensor.a"])
    await _set(hass, "sensor.a", "10")
    await _set(hass, "sensor.a", "11")
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"members": ["sensor.a", "sensor.b"]}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert hass.states.get(SUM).attributes["entity_id"] == ["sensor.a", "sensor.b"]
    assert _total(hass) == 1.0  # kept across the reload
    await _set(hass, "sensor.b", "500")  # new member only seeds
    await _set(hass, "sensor.b", "502")
    assert _total(hass) == 3.0


async def test_outage_and_counter_restart(hass: HomeAssistant) -> None:
    await _set(hass, "sensor.a", "1000")
    await _set(hass, "sensor.b", "500")
    await _setup(hass)
    assert _total(hass) == 0.0

    await _set(hass, "sensor.a", "1001")
    await _set(hass, "sensor.b", "502")
    assert _total(hass) == 3.0

    # Wi-Fi outage: member unavailable, nothing changes, nothing drops.
    await _set(hass, "sensor.a", "unavailable")
    assert _total(hass) == 3.0
    await _set(hass, "sensor.a", "1003")
    assert _total(hass) == 5.0

    # Counter restart: counts from 0, no spike, no drop.
    await _set(hass, "sensor.b", "1")
    assert _total(hass) == 6.0
    await _set(hass, "sensor.b", "3")
    assert _total(hass) == 8.0

    # Small dip is noise and is ignored; baseline stays at the higher value.
    await _set(hass, "sensor.a", "1002.9")
    assert _total(hass) == 8.0
    await _set(hass, "sensor.a", "1004")
    assert _total(hass) == 9.0

    # Non-numeric and non-energy values are ignored.
    await _set(hass, "sensor.a", "garbage")
    await _set(hass, "sensor.a", "5000", {"unit_of_measurement": "W"})
    assert _total(hass) == 9.0


async def test_unit_conversion(hass: HomeAssistant) -> None:
    await _setup(hass, ["sensor.wh"])
    await _set(hass, "sensor.wh", "1000", WH)
    await _set(hass, "sensor.wh", "2500", WH)
    assert _total(hass) == 1.5


async def test_restore_catches_up(hass: HomeAssistant) -> None:
    mock_restore_cache_with_extra_data(
        hass,
        [
            (
                State(SUM, "42.0"),
                {"total": 42.0, "last_values": {"sensor.a": 100.0, "sensor.gone": 7.0}},
            )
        ],
    )
    # sensor.a counted 5 kWh while Home Assistant was down.
    await _set(hass, "sensor.a", "105")
    await _setup(hass, ["sensor.a"])
    assert _total(hass) == 47.0
