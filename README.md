# st-uhubm

An unofficial toolset for controlling StarTech Managed Industrial USB Hubs on
Linux.

Includes a Python library, command-line tool, and web GUI.

Supported hubs:

- `5G7AINDRM-USB-A-HUB` (7 ports)
- `5G4AINDRM-USB-A-HUB` (4 ports)
- Firmware v04 or newer

Supported device identification:

- SEGGER J-Link
- Nordic Power Profiler Kit II (PPK2)

Full documentation: https://st-uhubm.readthedocs.io/

> This project is not affiliated with, endorsed by, or supported by
> StarTech.com.
>
> StarTech's proprietary `cusbi` and `cusba` programs are not included.

## Install

```bash
python3 -m pip install st-uhubm
```

Install with the optional web GUI:

```bash
python3 -m pip install "st-uhubm[gui]"
```

Download the StarTech Linux control program from the product's
**Drivers & Downloads** page and place it on `PATH`:

- `cusbi` on x86 and x86-64
- `cusba` on ARM and AArch64

## Command line

```bash
stuhubm health
stuhubm list
stuhubm status /dev/ttyUSB0

stuhubm off /dev/ttyUSB0 3
stuhubm on /dev/ttyUSB0 3

stuhubm off /dev/ttyUSB0 2,3,4
stuhubm on /dev/ttyUSB0 all
```

JSON output:

```bash
stuhubm --json status /dev/ttyUSB0
```

Custom control-program path:

```bash
stuhubm --binary /opt/startech/cusbi health
```

## Web GUI

```bash
stuhubm-gui
```

Open <http://127.0.0.1:8080>.

Use another address or port:

```bash
stuhubm-gui --host 0.0.0.0 --port 9000
```

## Python API

```python
from st_uhubm import discover

hub = discover()[0]

hub.set_port(4, on=False)
hub.set_port(4, on=True)

for port in range(1, hub.n_ports + 1):
    for device in hub.identified_devices(port):
        print(port, device.product, device.serial)
```

## Device identification

Device identification uses Linux sysfs and requires no additional Python
package.

Currently recognized:

- SEGGER devices with USB vendor ID `1366`
- Nordic PPK2 devices with USB ID `1915:c00a`

The application accounts for the internal cascaded USB topology of supported
seven-port hubs and associates identified devices with managed ports.

## Permissions

The StarTech control program normally requires permission to access the hub's
control device, such as `/dev/ttyUSB0`. By default, `st-uhubm` runs the program
through `sudo`. To run without `sudo`, grant the user access to the device.

## License

This project is licensed under the GNU General Public License, version 2 or
later (`GPL-2.0-or-later`).

StarTech's `cusbi` and `cusba` programs are not included and remain subject to
StarTech's own license terms.
