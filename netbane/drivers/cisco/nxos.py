from netbane.drivers.cisco.generic import CiscoDriver


class NXOSDriver(CiscoDriver):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.LIVE_INTERFACE_FACTS_CMD = "show interface"

    def _normalize_system_facts(self):
        facts = self.parsed["system_facts"]
        return {
            "uptime": facts["uptime"],
            "uptime_sec": ios.parse_uptime(facts["uptime"]),
            "image": facts["boot_image"],
        }

    def _normalize_live_interface_facts(self, interface_name):
        interface = self._get_live_interface_facts(interface_name)
        return {
            "description": interface["description"],
            "interface": interface["interface"],
            "is_enabled": interface["admin_state"].lower() == "up",
            "is_up": interface["link_status"].lower() == "up",
            "mac": interface["address"],
            # "mode": interface["mode"], # get this from config facts
            "mtu": int(interface["mtu"]),
        }