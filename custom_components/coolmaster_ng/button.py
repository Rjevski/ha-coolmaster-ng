from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from pycoolmasternet_ng import models

from .const import DATA_COORDINATOR, DOMAIN
from .mixins import UtilityEntityMixin


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add buttons for passed config_entry in HA."""
    entry_data = hass.data[DOMAIN][config_entry.entry_id]
    coordinator = entry_data[DATA_COORDINATOR]

    gateway: models.Gateway = coordinator.data

    new_devices: list[ButtonEntity] = []

    for device in gateway.devices.values():
        new_devices.append(
            FilterResetButton(
                device=device,
            )
        )

    if new_devices:
        async_add_entities(new_devices)


class FilterResetButton(UtilityEntityMixin, ButtonEntity):
    title = "Filter reset"
    _attr_icon = "mdi:air-filter"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, device: models.Device) -> None:
        self.device = device

    async def async_press(self) -> None:
        await self.device.reset_filter_sign(refresh=False)
