# arista-vtep-update

Utility for statically configuring VXLAN VTEP flood lists on Arista switches.
By default the script connects via SSH but eAPI can be used as an optional
transport. `Vxlan1` on each switch is updated so that all provided devices are
configured as remote VTEP endpoints.

## Requirements

- Python 3.8+
- `requests` library (only needed when using eAPI)
- `paramiko` library
- Arista switch reachable over SSH. eAPI must be enabled only when the
  `--use-eapi` option is used.

## Installation

Install the required Python packages and optionally install the project
itself to get the ``arista-vtep-update`` command:

```bash
pip install -r requirements.txt
pip install .
```


## Usage

```
arista-vtep-update -u <username> [--use-eapi] [--verify-ssl] [--hosts-file FILE] <host1> <host2> [host3 ...]
```

The script prompts for the password. At least two hosts must be supplied.
Each switch will have all other hosts added to its flood list.

Hosts can also be read from a file using `--hosts-file`. The file may contain a
simple list of hosts, one per line, or it may define multiple independent host
groups using an INI style format:

```
[group-a]
10.0.0.1 10.0.0.2
[group-b]
192.0.2.1 192.0.2.2
```

When groups are used each section is processed separately. In the above
example the first pair is configured only with each other, and likewise for the
second pair. Any hosts provided on the command line form an additional group.

Example:

```
arista-vtep-update -u admin leaf1 leaf2 leaf3
```

SSL verification is disabled by default. Use `--verify-ssl` if your eAPI
endpoints use valid certificates. When `--use-eapi` is omitted the script will
connect to the switches using SSH.
