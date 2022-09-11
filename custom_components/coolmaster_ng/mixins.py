from __future__ import annotations

from homeassistant.helpers.entity import DeviceInfo

from .const import DOMAIN


class UtilityEntityMixin:
    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, str(self.device.uid))},
            manufacturer=self.device.brand_name,
            via_device=(DOMAIN, self.device.gateway.serial_number),
        )

    @property
    def unique_id(self) -> str:
        return str(self.device.uid) + "-" + self.title.lower().replace(" ", "_")

    @property
    def name(self) -> str:
        device_name = self.device.friendly_name or str(self.device.uid)

        return f"{device_name} {self.title}"
