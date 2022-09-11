# Improved CoolMasterNet integration for Home Assistant

This is an alternative Home Assistant integration for CoolMasterNet devices.

Compared to the built-in integration, this one adds a few extra features:

* other transports - in addition to telnet, serial is now supported and the code is structured in such a way that other transports can be added down the line (REST and maybe even CoolAutomation's official cloud)

* reporting of AC heating/cooling demand if supported (otherwise faked locally based on temperature differences)

* AC unit capability (heat, cool, dry, etc) as well as display name is now configured at the CoolMasterNet gateway level using `props` commands - this means that the configuration persists with the gateway and is independent of HA. I also believe that's how CoolAutomation's cloud-based app does it, so it would make switching to Home Assistant easier for users of the official app (and in fact they would be able to coexist)

* reporting of AC unit error status

* reporting of filter status and a "button" integration to reset it

* support for the "feed" command to provide ambient temperature in the form of a service

* support for the "fan swing" functionality, if the device supports it


# How to use

* telnet into your CoolMasterNet and set unit properties using the `props` commands (see [documentation](https://support.coolautomation.com/hc/en-us/article_attachments/4417614885905/CM5-PRM-1.pdf) for details) - you want the name, modes and fan speeds set accordingly
* install the custom component using your favorite method
* add the integration using the UI - it should auto-detect all the units configured in the CoolMasterNet gateway

# Credits / thanks

* [OnFreund](https://github.com/OnFreund)'s [pycoolmasternet-async](https://github.com/OnFreund/pycoolmasternet-async)
* [koreth](https://github.com/koreth)'s [pycoolmasternet](https://github.com/koreth/pycoolmasternet)
