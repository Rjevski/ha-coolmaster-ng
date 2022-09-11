"""The Coolmaster integration."""
import logging

from homeassistant.components.climate import SCAN_INTERVAL
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_PROTOCOL, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from pycoolmasternet_ng import exceptions, models, transports

from .const import CONF_SERIAL_BAUD, CONF_SERIAL_URL, DATA_COORDINATOR, DOMAIN, PROTOCOL_SERIAL, PROTOCOL_SOCKET

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.CLIMATE, Platform.BINARY_SENSOR, Platform.BUTTON]


def _get_transport_from_config_data(data: dict) -> transports.BaseTransport:
    protocol = data.get(CONF_PROTOCOL, PROTOCOL_SOCKET)

    if protocol == PROTOCOL_SOCKET:
        return transports.TCPTransport(data[CONF_HOST], port=data.get(CONF_PORT))

    if protocol == PROTOCOL_SERIAL:
        return transports.SerialTransport(data[CONF_SERIAL_URL], baudrate=data.get(CONF_SERIAL_BAUD))

    raise ValueError(f"Unsupported protocol {protocol}")


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Coolmaster from a config entry."""
    transport = _get_transport_from_config_data(entry.data)

    try:
        gateway = await models.Gateway.from_transport(transport)
    except exceptions.CoolMasterNetRemoteError as exc:
        raise ConfigEntryNotReady from exc

    connections = set()

    if isinstance(transport, transports.NetworkTransportMixin):
        ifconfig = await gateway.get_ifconfig()
        connections = {(dr.CONNECTION_NETWORK_MAC, ifconfig["MAC"])}

    # according to CoolAutomation, CoolMasterNet S/Ns begin with 283B960,
    # CoolLinkHub's begin with 283B96C
    if gateway.serial_number.startswith("283B960"):
        model = "CoolMasterNet"
    elif gateway.serial_number.startswith("283B96C"):
        model = "CoolLinkHub"
    else:
        # my CoolLinkHub unit doesn't begin with either one of them,
        # use fallback method of checking for CoolMasterNet-only commands
        try:
            await gateway.transport.command("simul")
        except exceptions.CoolMasterNetUnknownCommandError:
            # CoolLinkHub does not support this command
            model = "CoolLinkHub"
        else:
            model = "CoolMasterNet"

    device_registry = dr.async_get(hass)

    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        connections=connections,
        identifiers={(DOMAIN, gateway.serial_number)},
        manufacturer="CoolAutomation",
        model=model,
        name=gateway.serial_number,
        sw_version=gateway.version,
    )

    coordinator = CoolmasterDataUpdateCoordinator(hass, gateway)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        DATA_COORDINATOR: coordinator,
    }

    await coordinator.async_config_entry_first_refresh()

    hass.config_entries.async_setup_platforms(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Coolmaster config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


class CoolmasterDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Coolmaster data."""

    def __init__(self, hass: HomeAssistant, gateway: models.Gateway) -> None:
        """Initialize global Coolmaster data updater."""
        self.gateway = gateway

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )

    async def _async_update_data(self) -> models.Gateway:
        """Fetch data from Coolmaster."""

        try:
            for device in self.gateway.devices.values():
                # refresh devices in-place so entities' references to these objects remain valid
                await device.refresh()
        except (OSError, exceptions.CoolMasterNetRemoteError) as exc:
            raise UpdateFailed from exc
        else:
            return self.gateway
