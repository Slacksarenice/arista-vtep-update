# Utility for updating VTEP endpoints on Arista switches.
#
# The script can configure VXLAN VTEP endpoints either by connecting via
# SSH or, optionally, using eAPI. Historically only eAPI was supported
# but the default behaviour is now to use SSH which works on devices
# where eAPI is not enabled.

import argparse
import json
import sys
import socket
from getpass import getpass
from typing import List
from concurrent.futures import ThreadPoolExecutor, as_completed

import paramiko
import time

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


def send_ssh_commands(
    host: str,
    username: str,
    password: str,
    commands: List[str],
) -> str:
    """Send a list of commands to the Arista switch over SSH."""

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname=host, username=username, password=password, look_for_keys=False)

    cli_cmds = " ; ".join(["configure terminal"] + commands)
    full_cmd = f"Cli -p 15 -c '{cli_cmds}'"
    stdin, stdout, stderr = client.exec_command(full_cmd)
    stdout.channel.recv_exit_status()
    out = stdout.read().decode()
    err = stderr.read().decode()
    client.close()
    if err:
        raise RuntimeError(err)
    return out


def build_flood_commands(remote_vtep_ips: List[str]) -> List[str]:
    """Build CLI commands to update the Vxlan1 flood list.

    Parameters
    ----------
    remote_vtep_ips : List[str]
        IP addresses of remote VTEP endpoints to add to the flood list.

    Returns
    -------
    List[str]
        Commands ready to be sent to the switch.
    """

    commands = ["interface Vxlan1"]
    # Clear any existing flood list entries so only the desired VTEPs remain.
    # 'no vxlan flood vtep' removes all currently configured remote VTEP
    # addresses from the list.
    commands.append("no vxlan flood vtep")
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
        nargs="*",
        help="Hostnames or IP addresses of the switches (minimum two)",
    )
    parser.add_argument(
        "-u",
        "--username",
        required=True,
        help="Login username",
    )
    parser.add_argument(
        "-f",
        "--hosts-file",
        help="File containing hostnames or IP addresses, one per line",
    )
    parser.add_argument(
        "--verify-ssl",
        action="store_true",
        help="Verify SSL certificates when connecting to the switches",
    )
    parser.add_argument(
        "--use-eapi",
        action="store_true",
        help="Use eAPI instead of SSH",
    )
    return parser.parse_args(argv)


def read_hosts_from_file(path: str) -> List[str]:
    """Read hostnames or IP addresses from a file."""

    try:
        with open(path) as f:
            return [line.strip() for line in f if line.strip()]
    except OSError as exc:
        print(f"Failed to read hosts file {path}: {exc}", file=sys.stderr)
        sys.exit(1)


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

    hosts = list(args.hosts)
    if args.hosts_file:
        hosts.extend(read_hosts_from_file(args.hosts_file))

    if len(hosts) < 2:
        print("At least two hosts must be specified", file=sys.stderr)
        return 1

    password = getpass()
    ips = resolve_hosts(hosts)

    def worker(host: str, ip: str):
        remote_vteps = [other for other in ips if other != ip]
        commands = build_flood_commands(remote_vteps)
        if args.use_eapi:
            result = send_eapi_commands(
                host=host,
                username=args.username,
                password=password,
                commands=commands,
                verify_ssl=args.verify_ssl,
            )
            return host, json.dumps(result)
        else:
            output = send_ssh_commands(
                host=host,
                username=args.username,
                password=password,
                commands=commands,
            )
            return host, output

    with ThreadPoolExecutor(max_workers=len(hosts)) as executor:
        future_to_host = {
            executor.submit(worker, host, ip): host
            for host, ip in zip(hosts, ips)
        }

        for future in as_completed(future_to_host):
            host = future_to_host[future]
            try:
                h, result = future.result()
                print(f"{h}: {result}")
            except (requests.RequestException, RuntimeError, paramiko.SSHException) as exc:
                print(f"{host}: failed to send commands: {exc}", file=sys.stderr)
    return 0
