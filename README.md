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

## Usage

```
python update_vtep.py -u <username> [--use-eapi] [--verify-ssl] <host1> <host2> [host3 ...]
```

The script prompts for the password. At least two hosts must be supplied.
Each switch will have all other hosts added to its flood list.

Example:

```
python update_vtep.py -u admin leaf1 leaf2 leaf3
```

SSL verification is disabled by default. Use `--verify-ssl` if your eAPI
endpoints use valid certificates. When `--use-eapi` is omitted the script will
connect to the switches using SSH.
