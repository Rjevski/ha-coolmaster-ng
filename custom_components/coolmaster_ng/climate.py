"""CoolMasterNet platform to control of CoolMasterNet Climate Devices."""
from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    FAN_AUTO,
    FAN_DIFFUSE,
    FAN_HIGH,
    FAN_LOW,
    FAN_MEDIUM,
    FAN_TOP,
    SWING_HORIZONTAL,
    SWING_OFF,
    SWING_ON,
    SWING_VERTICAL,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, TEMP_CELSIUS, TEMP_FAHRENHEIT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback, async_get_current_platform
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from pycoolmasternet_ng import constants, models

from .const import DATA_COORDINATOR, DOMAIN, SERVICE_SET_AMBIENT_TEMPERATURE

CM_TO_HA_STATE = {
    constants.Mode.HEAT: HVACMode.HEAT,
    constants.Mode.COOL: HVACMode.COOL,
    constants.Mode.AUTO: HVACMode.HEAT_COOL,
    constants.Mode.DRY: HVACMode.DRY,
    constants.Mode.FAN: HVACMode.FAN_ONLY,
}

HA_STATE_TO_CM = {value: key for key, value in CM_TO_HA_STATE.items()}


CM_TO_HA_FAN_MODE = {
    constants.FanMode.VERY_LOW: FAN_DIFFUSE,
    constants.FanMode.LOW: FAN_LOW,
    constants.FanMode.MEDIUM: FAN_MEDIUM,
    constants.FanMode.HIGH: FAN_HIGH,
    constants.FanMode.VERY_HIGH: FAN_TOP,
    constants.FanMode.AUTO: FAN_AUTO,
}

HA_FAN_MODE_TO_CM = {value: key for key, value in CM_TO_HA_FAN_MODE.items()}

SWING_30_DEGREES = "30-degrees"
SWING_45_DEGREES = "45-degrees"
SWING_60_DEGREES = "60-degrees"

CM_TO_HA_SWING_STATE = {
    constants.LouverPositionState.SWING: SWING_ON,
    constants.LouverPositionState.STOP_SWING: SWING_OFF,
    constants.LouverPositionState.HORIZONTAL: SWING_HORIZONTAL,
    constants.LouverPositionState.VERTICAL: SWING_VERTICAL,
    constants.LouverPositionState.THIRTY_DEGREES: SWING_30_DEGREES,
    constants.LouverPositionState.FORTY_FIVE_DEGREES: SWING_45_DEGREES,
    constants.LouverPositionState.SIXTY_DEGREES: SWING_60_DEGREES,
}

HA_SWING_MODE_TO_CM = {
    SWING_ON: constants.LouverPosition.SWING,
    SWING_OFF: constants.LouverPosition.STOP_SWING,
    SWING_HORIZONTAL: constants.LouverPosition.HORIZONTAL,
    SWING_VERTICAL: constants.LouverPosition.VERTICAL,
    SWING_30_DEGREES: constants.LouverPosition.THIRTY_DEGREES,
    SWING_45_DEGREES: constants.LouverPosition.FORTY_FIVE_DEGREES,
    SWING_60_DEGREES: constants.LouverPosition.SIXTY_DEGREES,
}

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_devices: AddEntitiesCallback,
) -> None:
    """Set up the CoolMasterNet climate platform."""
    entry_data = hass.data[DOMAIN][config_entry.entry_id]
    coordinator = entry_data[DATA_COORDINATOR]

    gateway: models.Gateway = coordinator.data

    all_devices = [CoolmasterClimate(coordinator=coordinator, device=device) for device in gateway.devices.values()]

    async_add_devices(all_devices)

    platform = async_get_current_platform()

    platform.async_register_entity_service(
        SERVICE_SET_AMBIENT_TEMPERATURE,
        {
            vol.Required("temperature"): vol.Coerce(float),
        },
        "set_ambient_temperature",
    )


class CoolmasterClimate(CoordinatorEntity, ClimateEntity):
    """Representation of a Coolmaster climate device."""

    _attr_icon = "mdi:hvac"

    def __init__(self, coordinator, device: models.Device):
        """Initialize the climate device."""
        super().__init__(coordinator)

        self.device: models.Device = device

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info for this device."""

        return DeviceInfo(
            identifiers={(DOMAIN, str(self.device.uid))},
            manufacturer=self.device.brand_name,
            name=self.name,
            via_device=(DOMAIN, self.device.gateway.serial_number),
        )

    @property
    def unique_id(self) -> str:
        return str(self.device.uid) + "-climate"

    @property
    def supported_features(self) -> int:
        flags: int = ClimateEntityFeature.TARGET_TEMPERATURE

        # only set this if supported by the device
        if self.device.louver_position != constants.LouverPositionState.NOT_SUPPORTED:
            flags |= ClimateEntityFeature.SWING_MODE

        # only set this if the device has defined fan speeds (in CoolMasterNet properties)
        if self.fan_modes:
            flags |= ClimateEntityFeature.FAN_MODE

        return flags

    @property
    def swing_modes(self) -> list[str] | None:
        # only return a value if the device supports it
        if self.device.louver_position != constants.LouverPositionState.NOT_SUPPORTED:
            return list(CM_TO_HA_SWING_STATE.values())

        return None

    @property
    def swing_mode(self) -> str | None:
        # this is intended to return None if it gets LouverPositionState.NOT_SUPPORTED
        # as we assume that in this case self.swing_modes will return None to begin with

        return CM_TO_HA_SWING_STATE.get(self.device.louver_position)

    @property
    def max_temp(self) -> float:
        """
        Return the maximum temperature allowed by the device if available, falling back to defaults.
        """
        temp_range = self.device.target_temperature_range

        if temp_range:
            return float(temp_range.stop)

        return super().max_temp

    @property
    def min_temp(self) -> float:
        """
        Return the minimum temperature allowed by the device if available, falling back to defaults.
        """
        temp_range = self.device.target_temperature_range

        if temp_range:
            return float(temp_range.start)

        return super().min_temp

    @property
    def name(self) -> str | None:
        """
        Return the friendly name set via CoolMasterNet properties, if any.
        """
        return self.device.friendly_name

    @property
    def temperature_unit(self) -> str:
        """
        Return the unit of measurement - this is a CoolMasterNet gateway-wide setting.
        """

        return TEMP_CELSIUS if self.device.temperature_unit == "C" else TEMP_FAHRENHEIT

    @property
    def current_temperature(self) -> float:
        return float(self.device.current_temperature)

    @property
    def target_temperature(self) -> float:
        return float(self.device.target_temperature)

    @property
    def hvac_mode(self) -> HVACMode:
        if not self.device.power_state:
            return HVACMode.OFF

        return CM_TO_HA_STATE[self.device.mode]

    @property
    def hvac_action(self) -> HVACAction:
        """
        Return the current "action" (whether the unit is currently heating/cooling/etc).

        We use a combination of the "demand" flag as well as comparing current & target temperatures
        to account for cases where the demand flag is always set to False.
        """

        if self.hvac_mode == HVACMode.FAN_ONLY:
            return HVACAction.FAN

        if self.hvac_mode == HVACMode.DRY:
            return HVACAction.DRYING

        if self.hvac_mode in (HVACMode.HEAT, HVACMode.COOL, HVACMode.HEAT_COOL):
            unit_no_demand = not self.device.demand

            # note that not all units set the "demand" flag, thus we also fall back to checking
            # whether the current temperature is around the target temperature

            if self.hvac_mode == HVACMode.HEAT:
                return (
                    HVACAction.IDLE
                    if unit_no_demand and self.current_temperature >= self.target_temperature
                    else HVACAction.HEATING
                )

            if self.hvac_mode == HVACMode.COOL:
                return (
                    HVACAction.IDLE
                    if unit_no_demand and self.current_temperature <= self.target_temperature
                    else HVACAction.COOLING
                )

            if self.hvac_mode == HVACMode.HEAT_COOL:
                if self.current_temperature == self.target_temperature:
                    return HVACAction.IDLE

                if self.current_temperature > self.target_temperature:
                    return HVACAction.COOLING

                return HVACAction.HEATING

        return HVACAction.OFF

    @property
    def hvac_modes(self) -> list[HVACMode]:
        return [CM_TO_HA_STATE[mode] for mode in self.device.supported_modes if mode in CM_TO_HA_STATE] + [
            HVACMode.OFF
        ]

    @property
    def fan_mode(self) -> str | None:
        if self.fan_modes:
            return CM_TO_HA_FAN_MODE[self.device.fan_mode]

        return None

    @property
    def fan_modes(self) -> list[str]:
        """
        Return the list of available fan modes based on CoolMasterNet device properties.

        This allows the user to control which fan speeds are available (and hide unsupported ones)
        using CoolMasterNet configuration commands.
        """

        return [CM_TO_HA_FAN_MODE[mode] for mode in self.device.supported_fan_speeds if mode in CM_TO_HA_FAN_MODE]

    async def async_set_temperature(self, **kwargs):
        """Set new target temperatures."""
        if (temp := kwargs.get(ATTR_TEMPERATURE)) is not None:
            _LOGGER.debug("Setting temp of %s to %s", self.unique_id, str(temp))
            await self.device.set_temperature(temp, refresh=False)

    async def async_set_fan_mode(self, fan_mode: str):
        """Set new fan mode."""
        _LOGGER.debug("Setting fan mode of %s to %s", self.unique_id, fan_mode)
        await self.device.set_fan_mode(HA_FAN_MODE_TO_CM[fan_mode], refresh=False)

    async def async_set_swing_mode(self, swing_mode: str):
        """Set new target swing operation."""
        await self.device.set_louver_position(HA_SWING_MODE_TO_CM[swing_mode], refresh=False)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode):
        """Set new operation mode."""
        _LOGGER.debug("Setting operation mode of %s to %s", self.unique_id, hvac_mode)

        if hvac_mode == HVACMode.OFF:
            await self.async_turn_off()
        else:
            await self.device.set_mode(HA_STATE_TO_CM[hvac_mode], refresh=False)
            await self.async_turn_on()

    async def async_turn_on(self):
        """Turn on."""
        _LOGGER.debug("Turning %s on", self.unique_id)
        await self.device.set_power_state(True, refresh=False)

    async def async_turn_off(self):
        """Turn off."""
        _LOGGER.debug("Turning %s off", self.unique_id)
        await self.device.set_power_state(False, refresh=False)

    async def set_ambient_temperature(self, temperature: float):
        """
        Provide ambient temperature suggestion to the unit.

        Note that this is not supported by all units and even if supported will depend
        on the unit's configuration, thus it is not guaranteed that this will have any effect.
        """
        _LOGGER.debug("Sending %d as ambient temperature", temperature)

        await self.device.set_current_temperature(temperature, refresh=False)
