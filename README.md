# st-uhubm

Manage **StarTech Managed Industrial USB Hubs** on Linux from Python, a CLI, or
an optional web GUI.

> **Unofficial.** Not affiliated with, endorsed by, or supported by StarTech.com.
> "StarTech" is a trademark of its respective owner. This package wraps StarTech's
> proprietary `cusbi` / `cusba` control binary, which user must obtain separately
> and which is **not** redistributed here.

Supported hardware: `5G7AINDRM-USB-A-HUB` (7-port) and `5G4AINDRM-USB-A-HUB`
(4-port), firmware v04+. These hubs expose a serial control channel (enumerating
as `/dev/ttyUSBn`); this is **not** _uhubctl_ or _PPPS_.

## Install

```bash
pip install st-uhubm            # library + CLI
pip install "st-uhubm[gui]"     # also the web GUI
```

Then install StarTech's binary separately (from the product's 'Drivers & Downloads'
page) and put `cusbi` (x86) or `cusba` (ARM) on `PATH`. See the
[user manual](https://st-uhubm.readthedocs.io/) for details.

## Quick start

```bash
stuhubm health                 # check the binary is found, list hubs
stuhubm list                   # discover hubs
stuhubm status /dev/ttyUSB0    # show port states
stuhubm off /dev/ttyUSB0 3,4   # turn ports 3 and 4 off
stuhubm on  /dev/ttyUSB0 3     # turn port 3 on
stuhubm save /dev/ttyUSB0      # persist current states to flash
```

Python:

```python
from st_uhubm import discover

hub = discover()[0]
hub.set_port(4, on=False)    # power-cycle a device under test
hub.set_port(4, on=True)
```

GUI:

```bash
stuhubm-gui                    # http://localhost:8080
```

## Why

Built for embedded testing / CI use: power-cycling DUT from a pipeline.
The parsing (hub discovery output, the little-endian port bitmap) lives in
pure text processing functions, so behavior is predictable and the logic is
easy to test without hardware.

## Project layout

```
src/st_uhubm/
    __init__.py      # public API
    errors.py        # exception hierarchy
    cli_backend.py   # parsers + HubManager/Hub + subprocess wrapper
    cli.py           # `stuhubm` Click CLI
    gui.py           # `stuhubm-gui` NiceGUI app (optional [gui] extra)
docs/                # Sphinx docs
```

## Development

```bash
pip install -e ".[gui,docs]"
python -m sphinx -b html docs docs/_build/html   # build the docs locally
```

## Documentation

Full manual and auto-generated API reference:
[Read the Docs](https://st-uhubm.readthedocs.io/)
(source: [docs/USER_MANUAL.rst](docs/USER_MANUAL.rst)).

## License

This code is licensed under the GNU General Public License, version 2 or later
(GPL-2.0-or-later). StarTech's `cusbi`/`cusba` binary is not included and
remains the property of StarTech.com under its own terms.
