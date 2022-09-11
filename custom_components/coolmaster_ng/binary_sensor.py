from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator
from pycoolmasternet_ng import models

from .const import DATA_COORDINATOR, DOMAIN
from .mixins import UtilityEntityMixin


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add sensors for passed config_entry in HA."""
    entry_data = hass.data[DOMAIN][config_entry.entry_id]
    coordinator = entry_data[DATA_COORDINATOR]

    gateway: models.Gateway = coordinator.data

    new_devices: list[BaseDeviceBinarySensor] = []

    for device in gateway.devices.values():
        new_devices.append(
            FilterSensor(
                coordinator=coordinator,
                device=device,
            )
        )

        new_devices.append(
            DemandSensor(
                coordinator=coordinator,
                device=device,
            )
        )

        new_devices.append(ErrorSensor(coordinator=coordinator, device=device))

    if new_devices:
        async_add_entities(new_devices)


class BaseDeviceBinarySensor(UtilityEntityMixin, CoordinatorEntity, BinarySensorEntity):
    title = "Base Device Binary Sensor"

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        device: models.Device,
    ) -> None:
        self.device = device

        super().__init__(coordinator=coordinator)


class FilterSensor(BaseDeviceBinarySensor):
    title = "Filter"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:air-filter"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    @property
    def is_on(self) -> bool:
        return self.device.filter_sign


class DemandSensor(BaseDeviceBinarySensor):
    title = "Demand"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_device_class = BinarySensorDeviceClass.RUNNING

    @property
    def is_on(self) -> bool:
        return self.device.demand


class ErrorSensor(BaseDeviceBinarySensor):
    title = "Error"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    @property
    def is_on(self) -> bool:
        return self.device.error_code is not None

    @property
    def extra_state_attributes(self) -> dict[str, str | None]:
        return {"error_code": self.device.error_code}
