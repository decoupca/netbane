from netbane import api
from scrapli import Scrapli
from ciscoconfparse import CiscoConfParse
import copy
import re

SCRAPLI_PLATFORM_MAP = {
    "eos": "arista_eos",
    "ios": "cisco_iosxe",
    "iosxr": "cisco_iosxr",
    "nxos": "cisco_nxos",
    "junos": "juniper_junos",
}

class BaseDevice(object):
    def __init__(self, host, username, password, port=22, platform, optional_args):
        
        ssh_config_file = optional_args.get('ssh_config_file', None)
        auth_strict_key = optional-args.get('auth_strict_key', False)
        default_timeout = optional_args.get('default_timeout', 30)
        timeout_ops = optional_args.get('timeout_ops', default_timeout)
        timeout_socket = optional_args.get('timeout_socket', default_timeout)
        timeout_transport = optional_args.get('timeout_transport', default_timeout)

        scrapli_args = {
            'host': host,
            'auth_username': username,
            'auth_password': password,
            'auth_strict_key': auth_strict_key,
            'platform': SCRAPLI_PLATFORM_MAP[platform],
            'port': port,
            'ssh_config_file': ssh_config_file,
            'timeout_ops': timeout_ops,
            'timeout_socket': timeout_socket,
            'timeout_transport': timeout_transport,
        }
        self.conn = Scrapli(**scrapli_args)

        # completely unformatted facts discovered from device
        # untouched response strings from command output
        self.raw = {
            "running_config": None,
        }

        # facts parsed into a data structure or object, but not yet normalized
        # to conform with API standard
        self.parsed = {
            # running config as parsed by a library like CiscoConfParse
            "running_config": None,
            # textfsm-parsed interface facts derived from
            # a command like `show interfaces`
            "live_interface_facts": None,
            # interface facts derived from config parsing
            "config_interface_facts": None,
            # textfsm-parsed vlan facts derived from a command like `show vlan`
            "vlan_facts": None,
            # textfsm-parsed system facts derived from a command like `show version`
            "system_facts": None,
        }

        # facts normalized to conform with API standard
        self.normalized = {
            "live_interface_facts": None,
            "config_interface_facts": None,
            "all_interface_facts": None,
            "system_facts": None,
        }

        # facts ready for use, normalized and collated
        self.interface_facts = None
        self.vlans = None
        self.system_facts = None
        self.LIVE_INTERFACE_NAME_KEY = ""
        self.LIVE_INTERFACE_FACTS_CMD = ""
        self.GET_RUNNING_CONFIG_CMD = ""
        self.GET_SYSTEM_FACTS_CMD = ""

    def open(self):
        self.conn.open()

    def close(self):
        self.conn.close()

    def cli(self, command):
        return self.conn.send_command(command)

    def parse_cli(self, command):
        return self.conn.send_command(command).textfsm_parse_output()

    def _interface_config_regex(self, interface_config, pattern):
        for line in interface_config:
            match = re.match(pattern, line.strip())
            if match:
                return match

    def _fetch_all_live_interface_facts(self):
        """Fetch textfsm-parsed interface facts"""
        self.parsed["live_interface_facts"] = self.parse_cli(
            self.LIVE_INTERFACE_FACTS_CMD
        )

    def _get_live_interface_facts(self, interface_name):
        """Get live facts for a given interface_name"""
        for live_facts in self.parsed["live_interface_facts"]:
            if live_facts[self.LIVE_INTERFACE_NAME_KEY] == interface_name:
                return live_facts

    def _fetch_running_config(self):
        """Fetch raw running config from device"""
        self.raw["running_config"] = self.cli(self.GET_RUNNING_CONFIG_CMD).result

    def _fetch_system_facts(self):
        """Fetch textfsm-parsed system facts"""
        self.parsed["system_facts"] = self.parse_cli(self.GET_SYSTEM_FACTS_CMD)[0]

    def _fetch_vlans(self):
        """Fetch textfsm-parsed vlan facts"""
        self.vlans = self.parse_cli(self.GET_VLANS_CMD)

    def _collate_all_interface_facts(self):
        """Collates interface facts from live and config into single data structure"""
        all_facts = []
        for interface in self.parsed["live_interface_facts"]:
            interface_name = interface[self.LIVE_INTERFACE_NAME_KEY]
            facts = copy.deepcopy(api.INTERFACE_FACTS)
            facts.update(self._normalize_config_interface_facts(interface_name))
            facts.update(self._normalize_live_interface_facts(interface_name))
            all_facts.append(facts)
        self.normalized["all_interface_facts"] = all_facts

    def _collate_system_facts(self):
        system_facts = copy.deepcopy(api.SYSTEM_FACTS)
        system_facts.update(self._normalize_system_facts())
        self.normalized["system_facts"] = system_facts

    def _normalize_all_interface_facts(self):
        """Normalizes interface facts from config and live system"""
        live_facts = []
        config_facts = []
        for interface in self.parsed["live_interface_facts"]:
            interface_name = interface[self.LIVE_INTERFACE_NAME_KEY]
            live_facts.append(self._normalize_live_interface_facts(interface_name))
            config_facts.append(self._normalize_config_interface_facts(interface_name))
        self.normalized["live_interface_facts"] = live_facts
        self.normalized["config_interface_facts"] = config_facts

    def get_system_facts(self):
        if self.system_facts is None:
            self._fetch_system_facts()
            self._normalize_system_facts()
            self._collate_system_facts()
            self.system_facts = self.normalized["system_facts"]
        return self.system_facts

    def get_interface_facts(self):
        if self.interface_facts is None:
            self._fetch_running_config()
            self._fetch_all_live_interface_facts()
            self._normalize_all_interface_facts()
            self._collate_all_interface_facts()
            self.interface_facts = self.normalized["all_interface_facts"]
        return self.interface_facts
