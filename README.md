# arista-vtep-update

Utility for statically configuring VXLAN VTEP flood lists on Arista switches
using eAPI. The script updates `Vxlan1` on each switch so that all provided
devices are configured as remote VTEP endpoints.

## Requirements

- Python 3.8+
- `requests` library
- Arista switch with eAPI enabled

## Usage

```
python update_vtep.py -u <username> [--verify-ssl] <host1> <host2> [host3 ...]
```

The script prompts for the password. At least two hosts must be supplied.
Each switch will have all other hosts added to its flood list.

Example:

```
python update_vtep.py -u admin leaf1 leaf2 leaf3
```

SSL verification is disabled by default. Use `--verify-ssl` if your eAPI
endpoints use valid certificates.
