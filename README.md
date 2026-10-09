# Energy Sum Group

A Home Assistant helper that adds up energy meters **without the spikes** a regular sensor group creates in the Energy dashboard and long-term statistics.

## The problem it solves

A sum group adds up the members' raw counters. When one member's counter restarts (a Shelly rebooting during a network or firmware upgrade, a meter briefly reporting 0 on reconnect), the group's total drops. Long-term statistics treat any drop of more than 10% in a `total_increasing` sensor as a reset, and count the next value from zero: the group's whole total is booked as consumption in one hour. Each meter on its own is fine; only the group spikes.

## How it works

The Energy Sum Group sensor adds up each member's *increase* instead of its raw value:

- it remembers every member's last value;
- a member going `unavailable` or `unknown` is skipped, and when it comes back only the difference since its last value is added;
- a member dropping by more than 10% is treated as a restarted counter and counted from 0, the same rule statistics apply to the meter itself;
- smaller dips are ignored as noise;
- members in Wh, MWh, etc. are converted to kWh.

The total never goes down, so statistics never see a reset. It starts at 0 when created and counts up from there (statistics only use differences). The running total and each member's last value survive restarts, and anything a member counted while Home Assistant was down is caught up at startup.

## Installation

**HACS:** click the button below to open this repository in HACS on your Home Assistant, then install *Energy Sum Group* and restart Home Assistant.

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=spirann&repository=ha-energy-sum-group&category=integration)

Or add it by hand: HACS > ⋮ > Custom repositories > `https://github.com/spirann/ha-energy-sum-group`, category *Integration*.

**Manual:** copy `custom_components/energy_sum_group` into your `config/custom_components/` folder and restart Home Assistant.

## Usage

Settings > Devices & services > Helpers > Create helper > **Energy Sum Group**. Give it a name and pick the energy meters. To change the meters later, open the helper and choose *Energy Sum Group options*.

- Meters you add later start from their current value (nothing is added at once).
- Meters you remove keep what they already contributed.

Tip: replace each existing sum group with one of these helpers, switch your dashboards and automations to the new sensor, then delete the old group. For the Energy dashboard itself you can also add the individual meters directly; it sums them on its own.

## Repairing spikes already recorded

Developer tools > Statistics > search the old group entity > click the ramp icon ("Adjust sum") at the end of its row > pick the hour of the spike > set the correct value for that hour.
