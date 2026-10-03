st-uhubm User Manual
====================

Overview
--------

``st-uhubm`` is an unofficial toolset for controlling StarTech Managed
Industrial USB Hubs on Linux.

It includes a Python library, command-line tool, and web GUI.

It provides hub discovery, individual USB port control, status reporting, and
identification of supported devices connected to managed ports.

Supported identified devices include:

* SEGGER J-Link devices;
* Nordic Power Profiler Kit II (PPK2) devices.

.. note::

   This project is not affiliated with, endorsed by, or supported by
   StarTech.com.

   StarTech's proprietary ``cusbi`` and ``cusba`` programs are not included
   and must be obtained separately.

Supported hubs
--------------

The following hubs are supported:

======================= ===== ======================
Model                   Ports Minimum firmware
======================= ===== ======================
``5G7AINDRM-USB-A-HUB`` 7     v04
``5G4AINDRM-USB-A-HUB`` 4     v04
======================= ===== ======================

Each hub exposes a serial control interface, normally named
``/dev/ttyUSB0`` or another ``/dev/ttyUSB<n>`` device.

Requirements
------------

``st-uhubm`` requires:

* Linux;
* Python 3.10 or newer;
* a supported StarTech managed USB hub;
* StarTech's ``cusbi`` or ``cusba`` control program;
* permission to access the hub's serial control interface.

Control program
~~~~~~~~~~~~~~~

Download the Linux control program from the **Drivers & Downloads** section
of the StarTech product page.

Use:

* ``cusbi`` on x86 and x86-64 systems;
* ``cusba`` on ARM and AArch64 systems.

Install the program somewhere on ``PATH``:

.. code-block:: bash

   sudo install -m 0755 cusbi /usr/local/bin/cusbi

On ARM:

.. code-block:: bash

   sudo install -m 0755 cusba /usr/local/bin/cusba

The appropriate program is selected automatically. It can be overridden with
``--binary`` or the ``STUHUBM_BINARY`` environment variable.

Installation
------------

Install the library and command-line tool:

.. code-block:: bash

   python3 -m pip install st-uhubm

Install with the optional web GUI:

.. code-block:: bash

   python3 -m pip install "st-uhubm[gui]"

Verify the installation:

.. code-block:: bash

   stuhubm health

Command-line interface
----------------------

Discovery
~~~~~~~~~

Discover connected hubs:

.. code-block:: bash

   stuhubm list

Check the installation and detected hubs:

.. code-block:: bash

   stuhubm health

Status
~~~~~~

Show the state of every port:

.. code-block:: bash

   stuhubm status /dev/ttyUSB0

The output includes identified J-Link and PPK2 devices when available.

Port control
~~~~~~~~~~~~

Turn one port off and on:

.. code-block:: bash

   stuhubm off /dev/ttyUSB0 3
   stuhubm on /dev/ttyUSB0 3

Control several ports:

.. code-block:: bash

   stuhubm off /dev/ttyUSB0 2,3,4
   stuhubm on /dev/ttyUSB0 2,3,4

Control every port:

.. code-block:: bash

   stuhubm off /dev/ttyUSB0 all
   stuhubm on /dev/ttyUSB0 all

Toggle ports:

.. code-block:: bash

   stuhubm toggle /dev/ttyUSB0 2,3

JSON output
~~~~~~~~~~~

Use ``--json`` for machine-readable output:

.. code-block:: bash

   stuhubm --json status /dev/ttyUSB0

Example:

.. code-block:: json

   {
     "port": "/dev/ttyUSB0",
     "model": "7-port Managed USB Hub",
     "serial": "00020000149E",
     "firmware": "v04",
     "n_ports": 7,
     "states": {
       "1": true,
       "2": true,
       "3": true,
       "4": true,
       "5": true,
       "6": true,
       "7": true
     },
     "identified_devices": {
       "2": [
         {
           "serial": "1051129184",
           "product": "J-Link",
           "manufacturer": "SEGGER",
           "sysfs_name": "1-13.2",
           "vendor_id": "1366",
           "product_id": "1069",
           "device_type": "SEGGER J-Link"
         }
       ]
     }
   }

Control-program selection
~~~~~~~~~~~~~~~~~~~~~~~~~

Use a custom executable path:

.. code-block:: bash

   stuhubm --binary /opt/startech/cusbi health

Or set the path through the environment:

.. code-block:: bash

   export STUHUBM_BINARY=/opt/startech/cusbi
   stuhubm health

The default program is:

* ``cusbi`` on x86 and x86-64;
* ``cusba`` on ARM and AArch64.

Permissions
~~~~~~~~~~~

The control program normally needs permission to access the hub's serial
interface.

By default, ``st-uhubm`` runs the program through ``sudo``.

To run without ``sudo``:

.. code-block:: bash

   stuhubm --no-sudo status /dev/ttyUSB0

Running without ``sudo`` requires suitable device permissions.

Passwords
~~~~~~~~~

Supply a custom hub password:

.. code-block:: bash

   stuhubm --password secret status /dev/ttyUSB0

The password can also be supplied through the environment:

.. code-block:: bash

   export STUHUBM_PASSWORD=secret

Change the password interactively:

.. code-block:: bash

   stuhubm passwd /dev/ttyUSB0

Other hub operations
~~~~~~~~~~~~~~~~~~~~

Reset the hub:

.. code-block:: bash

   stuhubm reset /dev/ttyUSB0

Restore factory defaults:

.. code-block:: bash

   stuhubm restore /dev/ttyUSB0

Save the current port states to hub flash:

.. code-block:: bash

   stuhubm save /dev/ttyUSB0

Use ``--persist`` to remember each port change after the hub loses power:

.. code-block:: bash

   stuhubm --persist off /dev/ttyUSB0 3

Environment variables
~~~~~~~~~~~~~~~~~~~~~

====================== ===============================================
Variable               Purpose
====================== ===============================================
``STUHUBM_BINARY``      Control-program name or path
``STUHUBM_SUDO``        Enable or disable execution through ``sudo``
``STUHUBM_PASSWORD``    Custom hub password
``STUHUBM_PERSIST``     Remember each change after hub power-off
====================== ===============================================

Boolean environment variables accept values such as ``1``, ``true``, ``yes``,
and ``on``.

Exit codes
~~~~~~~~~~

===== =======================================
Code  Meaning
===== =======================================
0     Success
1     Hub command or parsing failure
2     Invalid command-line usage
3     StarTech control program not found
4     Command timeout
===== =======================================

Web GUI
-------

Install the GUI extra:

.. code-block:: bash

   python3 -m pip install "st-uhubm[gui]"

Start the GUI:

.. code-block:: bash

   stuhubm-gui

Open the following address in a web browser:

.. code-block:: text

   http://127.0.0.1:8080

Use another address or port:

.. code-block:: bash

   stuhubm-gui --host 0.0.0.0 --port 9000

GUI settings
~~~~~~~~~~~~

Binary
   The StarTech control-program name or full path.

Use sudo
   Run the control program through ``sudo``.

Hub password
   The custom hub password. Leave this blank when the default password is in
   use.

Remember port changes after hub power-off
   Write each port change to hub flash.

Auto-refresh
   Rediscover hubs and identified devices every five seconds.

Remote GUI access through SSH
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The recommended way to access the GUI remotely is to keep it bound to
localhost and forward the port through SSH.

On the remote Linux host connected to the hub, start the GUI:

.. code-block:: bash

   stuhubm-gui --host 127.0.0.1 --port 8080

Keep that command running.

On the local computer, open an SSH tunnel to the remote host:

.. code-block:: bash

   ssh -N -L 8080:127.0.0.1:8080 user@remote-host

Replace ``user`` and ``remote-host`` with the SSH username and hostname or IP
address of the remote system.

Open this address in a browser on the local computer:

.. code-block:: text

   http://127.0.0.1:8080

The browser connection is forwarded securely through SSH to the GUI running
on the remote host.

If local port ``8080`` is already in use, select another local port:

.. code-block:: bash

   ssh -N -L 9000:127.0.0.1:8080 user@remote-host

Then open:

.. code-block:: text

   http://127.0.0.1:9000

Python API
----------

Discover hubs
~~~~~~~~~~~~~

.. code-block:: python

   from st_uhubm import discover

   hubs = discover()

   for hub in hubs:
       print(hub.port)
       print(hub.model)
       print(hub.serial)
       print(hub.states)

Control ports
~~~~~~~~~~~~~

.. code-block:: python

   from st_uhubm import discover

   hub = discover()[0]

   hub.set_port(3, on=False)
   hub.set_port(3, on=True)

Control multiple ports:

.. code-block:: python

   hub.set_ports([2, 3, 4], on=False)
   hub.set_ports([2, 3, 4], on=True)

Control every port:

.. code-block:: python

   hub.set_all(on=False)
   hub.set_all(on=True)

Read state
~~~~~~~~~~

.. code-block:: python

   hub.refresh()

   for port in range(1, hub.n_ports + 1):
       print(port, hub.is_on(port))

Identify attached devices
~~~~~~~~~~~~~~~~~~~~~~~~~

Use ``identified_devices(port)`` to retrieve supported devices connected to a
managed port:

.. code-block:: python

   from st_uhubm import discover

   hub = discover()[0]

   for port in range(1, hub.n_ports + 1):
       for device in hub.identified_devices(port):
           print(
               port,
               device.device_type,
               device.product,
               device.serial,
           )

Refresh device information:

.. code-block:: python

   hub.refresh_device_identification()

Direct identification
~~~~~~~~~~~~~~~~~~~~~

Run device identification without creating a ``Hub`` object:

.. code-block:: python

   from st_uhubm import identify_devices

   devices_by_port = identify_devices(
       "/dev/ttyUSB0",
       n_ports=7,
   )

   for port, devices in devices_by_port.items():
       for device in devices:
           print(port, device.display_name)

Manager configuration
~~~~~~~~~~~~~~~~~~~~~

Use ``HubManager`` for explicit configuration:

.. code-block:: python

   from st_uhubm import HubManager

   manager = HubManager(
       binary="cusbi",
       use_sudo=True,
       password="",
       persist=False,
       timeout=10,
   )

   hub = manager.hub("/dev/ttyUSB0")
   print(hub.states)

Device identification
---------------------

Implementation
~~~~~~~~~~~~~~

Device identification is implemented in ``st_uhubm.device``.

The public types and functions are:

* ``IdentifiedDevice``;
* ``identify_devices()``;
* ``Hub.identified_devices(port)``;
* ``Hub.refresh_device_identification()``.

Identification uses Linux sysfs:

.. code-block:: text

   /sys/bus/usb/devices
   /sys/class/tty

No J-Link library, ``nrfutil``, or additional Python package is required.

Supported devices
~~~~~~~~~~~~~~~~~

The following devices are currently recognized:

===================== ============ =================
Device                Vendor ID    Product ID
===================== ============ =================
SEGGER J-Link         ``1366``     Any
Nordic PPK2           ``1915``     ``c00a``
===================== ============ =================

An ``IdentifiedDevice`` contains:

``serial``
   The normalized J-Link serial number or PPK2 CDC ID.

``product``
   The USB product name.

``manufacturer``
   The USB manufacturer name.

``sysfs_name``
   The Linux USB topology identifier.

``vendor_id``
   The USB vendor ID.

``product_id``
   The USB product ID.

``device_type``
   A normalized category such as ``SEGGER J-Link`` or ``Nordic PPK2``.

Seven-port topology
~~~~~~~~~~~~~~~~~~~

The supported seven-port hub contains an internal cascaded hub controller.

The confirmed mapping is:

======================= ====================
Linux route             Managed port
======================= ====================
Outer port ``1``        1
Outer port ``2``        2
Outer port ``3``        3
Inner route ``4.1``     4
Inner route ``4.2``     5
Inner route ``4.3``     6
Inner route ``4.4``     Control interface
======================= ====================

The control interface is not returned as an identified attached device.

License
-------

``st-uhubm`` is licensed under the GNU General Public License, version 2 or
later (GPL-2.0-or-later).

StarTech's ``cusbi`` and ``cusba`` programs are not included and remain
subject to StarTech's own license terms.
