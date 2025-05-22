#!/usr/bin/env python3
"""Utility for updating VTEP endpoints on Arista switches.

This script uses Arista eAPI to manually configure VXLAN VTEP
endpoints. It does not rely on EVPN and is intended for static
configuration of remote VTEPs.
"""

import argparse
import json
import sys
import socket
from getpass import getpass
from typing import List

import requests


def send_eapi_commands(
    host: str,
    username: str,
    password: str,
    commands: List[str],
    verify_ssl: bool = False,
) -> dict:
    """Send a list of commands to the Arista switch using eAPI.

    Parameters
    ----------
    host : str
        IP or hostname of the Arista switch with eAPI enabled.
    username : str
        Login username.
    password : str
        Login password.
    commands : List[str]
        CLI commands to send.
    verify_ssl : bool
        Whether to verify SSL certificates. Defaults to False
        as most lab environments use self-signed certificates.

    Returns
    -------
    dict
        Parsed JSON response from the switch.
    """

    url = f"https://{host}/command-api"
    payload = {
        "jsonrpc": "2.0",
        "method": "runCmds",
        "params": {
            "version": 1,
            "cmds": commands,
        },
        "id": 1,
    }

    response = requests.post(
        url,
        auth=(username, password),
        json=payload,
        verify=verify_ssl,
    )
    response.raise_for_status()
    return response.json()


def build_flood_commands(remote_vtep_ips: List[str]) -> List[str]:
    """Build CLI commands to update the Vxlan1 flood list.

    Parameters
    ----------
    remote_vtep_ips : List[str]
        IP addresses of remote VTEP endpoints to add to the flood list.

    Returns
    -------
    List[str]
        Commands ready to be sent to the switch via eAPI.
    """

    commands = ["interface Vxlan1"]
    for ip in remote_vtep_ips:
        commands.append(f"vxlan flood vtep {ip}")
    commands.append("exit")
    return commands


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Update Vxlan1 flood list on multiple Arista switches"
    )
    parser.add_argument(
        "hosts",
        nargs="+",
        help="Hostnames or IP addresses of the switches (minimum two)",
    )
    parser.add_argument(
        "-u",
        "--username",
        required=True,
        help="Login username",
    )
    parser.add_argument(
        "--verify-ssl",
        action="store_true",
        help="Verify SSL certificates when connecting to the switches",
    )
    return parser.parse_args(argv)


def resolve_hosts(hosts: List[str]) -> List[str]:
    """Resolve hostnames to IP addresses."""

    resolved = []
    for host in hosts:
        try:
            ip = socket.gethostbyname(host)
        except socket.gaierror as exc:
            print(f"Unable to resolve {host}: {exc}", file=sys.stderr)
            sys.exit(1)
        resolved.append(ip)
    return resolved


def main(argv: List[str]) -> int:
    args = parse_args(argv)

    if len(args.hosts) < 2:
        print("At least two hosts must be specified", file=sys.stderr)
        return 1

    password = getpass()
    ips = resolve_hosts(args.hosts)

    for host, ip in zip(args.hosts, ips):
        remote_vteps = [other for other in ips if other != ip]
        commands = build_flood_commands(remote_vteps)
        try:
            result = send_eapi_commands(
                host=host,
                username=args.username,
                password=password,
                commands=commands,
                verify_ssl=args.verify_ssl,
            )
        except requests.RequestException as exc:
            print(f"{host}: failed to send commands: {exc}", file=sys.stderr)
            continue

        print(f"{host}: {json.dumps(result)}")

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
