st-uhubm
========

A Python library, command-line tool, and web GUI for managing
**StarTech Managed Industrial USB Hubs** on Linux.

   **Unofficial.** This project is not affiliated with, endorsed by, or supported
   by StarTech.com. "StarTech" is a trademark of its respective owner. This
   package is a wrapper around StarTech's own ``cusbi`` / ``cusba`` binary,
   which you must obtain separately (see `Prerequisites <#prerequisites>`__).
   The binary is proprietary and is **not** redistributed here.

--------------

What is it
------------

StarTech's USB hubs expose a serial control channel (it enumerates as
``/dev/ttyUSB<n>``) that lets user switches individual downstream ports on and off,
reboot the hub, and persist a default port state. StarTech ships a control
binary (``cusbi`` on x86/AMD64, ``cusba`` on ARM) to drive that channel.

``st-uhubm`` wraps that binary with:

- a **Python API** for scripting and integration;
- a **``stuhubm`` CLI** with subcommands and optional JSON output;
- an optional **``stuhubm-gui``** NiceGUI web GUI with port toggles.

Supported hardware
------------------

======================= ===== =============================
Model                   Ports Notes
======================= ===== =============================
``5G7AINDRM-USB-A-HUB`` 7     7-port managed industrial hub
``5G4AINDRM-USB-A-HUB`` 4     4-port managed industrial hub
======================= ===== =============================

Multiple hubs (including daisy-chained units) on one host are supported; each
gets its own control port. Firmware **v04 or newer** is required.

   This package controls hubs via StarTech's serial protocol. It is **not**
   ``uhubctl`` and does not use USB per-port power switching (PPPS). The two are
   different projects.

Prerequisites
-------------

1. **Python 3.10 or newer.**
2. **The StarTech binary**, obtained from StarTech (see below). The
   correct binary for user's CPU:

   - ``cusbi`` — Intel/AMD (x86-64) Linux hosts
   - ``cusba`` — ARM Linux hosts (e.g. Raspberry Pi, most SBCs)

3. **Root access.** The binary opens the control tty directly and requires root.
   Run as root, use ``sudo``, or grant access to the device via a udev rule /
   group membership (see `Running without root <#running-without-root>`__).

Obtaining the vendor binary
~~~~~~~~~~~~~~~~~~~~~~~~~~~

This package does not redistribute StarTech's proprietary binary. To obtain it:

1. Go to the product page for your model
   (``startech.com/5G7AINDRM-USB-A-HUB`` or ``startech.com/5G4AINDRM-USB-A-HUB``)
   and open the **Drivers & Downloads** tab.

2. Download the Linux package (a tarball such as ``cusbi-r1.02.tar.gz``).

3. Extract it and place the binary somewhere on your ``PATH``, e.g.:

   .. code:: bash

      tar xzf cusbi-r1.02.tar.gz
      sudo install -m 0755 cusbi /usr/local/bin/cusbi

   On ARM, do the same with ``cusba``.

Verify the package can see it:

.. code:: bash

   stuhubm health

Installation
------------

Core library and CLI:

.. code:: bash

   pip install st-uhubm

With the web GUI:

.. code:: bash

   pip install "st-uhubm[gui]"

As an isolated tool (recommended for CLI-only use):

.. code:: bash

   pipx install st-uhubm
   # or
   uv tool install st-uhubm

Installing the package does **not** install the StarTech binary, that is a
separate manual step (see `Prerequisites <#prerequisites>`__).

Quick start
-----------

.. code:: bash

   # 1. Confirm the binary is working and list hubs
   stuhubm health

   # 2. Discover connected hubs
   stuhubm list

   # 3. Show the port states of a hub
   stuhubm status /dev/ttyUSB0

   # 4. Turn port 3 off, then back on
   stuhubm off /dev/ttyUSB0 3
   stuhubm on  /dev/ttyUSB0 3

   # 5. Turn several ports off at once
   stuhubm off /dev/ttyUSB0 3,4,5

   # 6. Persist the current state so it survives a power cycle
   stuhubm save /dev/ttyUSB0

If ``sudo`` prompts for a password on each call, see
`Running without root <#running-without-root>`__.

Core concepts
-------------

**Control port.** Each hub is addressed by the serial device it enumerates as.
Pass exactly what ``stuhubm list`` reports for the hub, e.g. ``/dev/ttyUSB0``.

**Ports.** Downstream USB-A ports are numbered from 1. User can act on a single
port (``3``), a comma-separated list (``3,4,5``), or all ports (``all``).

**Port state.** Each port is simply **on** or **off**. ``stuhubm status`` reports
the current state of every port.

**Volatile vs. persistent.** By default, changes are *volatile* — they apply
immediately but are lost when the hub loses power or is reset. To make a state
the power-on default, either:

- pass ``--persist`` (writes each change straight to the hub's flash), or
- make your changes volatile, then run ``stuhubm save`` once to commit the
  current state to flash.

Prefer the second pattern for test rigs: it avoids a flash write on every toggle.

**Password.** Hubs ship with the default password ``pass``. While the password is
unchanged from default, you do **not** need to supply it. Once you set a custom
password, every state-changing command must include it (via ``--password`` or the
``STUHUBM_PASSWORD`` environment variable). Passwords are at most 8 characters.

Command-line interface (``stuhubm``)
------------------------------------

General form:

::

   stuhubm [global options] <command> [arguments]

Commands
~~~~~~~~

+----------------------------+-----------------------------------------+
| Command                    | Description                             |
+============================+=========================================+
| ``health``                 | Check that the binary is present and    |
|                            | list detected hubs                      |
+----------------------------+-----------------------------------------+
| ``list``                   | Discover hubs and show control port,    |
|                            | model, serial, port count, firmware     |
+----------------------------+-----------------------------------------+
| ``status PORT``            | Show on/off state of every port on a    |
|                            | hub                                     |
+----------------------------+-----------------------------------------+
| ``on PORT PORTS``          | Turn the given port(s) on               |
+----------------------------+-----------------------------------------+
| ``off PORT PORTS``         | Turn the given port(s) off              |
+----------------------------+-----------------------------------------+
| ``toggle PORT PORTS``      | Invert the given port(s)                |
+----------------------------+-----------------------------------------+
| ``all PORT on\|off``       | Turn all ports on or off                |
+----------------------------+-----------------------------------------+
| ``save PORT``              | Save current port states to flash       |
|                            | (power-on default)                      |
+----------------------------+-----------------------------------------+
| ``reset PORT``             | Hardware-reset the hub                  |
+----------------------------+-----------------------------------------+
| ``restore PORT``           | Restore factory defaults (all ports on, |
|                            | password ``pass``)                      |
+----------------------------+-----------------------------------------+
| ``passwd PORT``            | Change the hub password (prompts        |
|                            | interactively)                          |
+----------------------------+-----------------------------------------+

``PORTS`` is a single port (``3``), a comma-separated list (``3,4,5``), or
``all``.

Global options
~~~~~~~~~~~~~~

+-------------------+----------------------+-----------------+------------------+
| Option            | Env var              | Default         | Meaning          |
+===================+======================+=================+==================+
| ``--binary PATH`` | ``STUHUBM_BINARY``   | ``cusbi``       | Control binary   |
|                   |                      |                 | name or full     |
|                   |                      |                 | path             |
+-------------------+----------------------+-----------------+------------------+
| ``--sudo`` /      | ``STUHUBM_SUDO``     | ``--sudo``      | Run the binary   |
| ``--no-sudo``     |                      |                 | via ``sudo``     |
+-------------------+----------------------+-----------------+------------------+
| ``--password PW`` | ``STUHUBM_PASSWORD`` | *(none)*        | Hub password, if |
|                   |                      |                 | changed from     |
|                   |                      |                 | default          |
+-------------------+----------------------+-----------------+------------------+
| ``--persist``     | ``STUHUBM_PERSIST``  | off             | Write changes to |
|                   |                      |                 | flash            |
|                   |                      |                 | immediately      |
+-------------------+----------------------+-----------------+------------------+
| ``--json``        | —                    | off             | Emit             |
|                   |                      |                 | machine-readable |
|                   |                      |                 | JSON instead of  |
|                   |                      |                 | text             |
+-------------------+----------------------+-----------------+------------------+
| ``--timeout N``   | —                    | ``10``          | Per-command      |
|                   |                      |                 | timeout in       |
|                   |                      |                 | seconds          |
+-------------------+----------------------+-----------------+------------------+
| ``--verbose``     | —                    | off             | Print the exact  |
|                   |                      |                 | binary           |
|                   |                      |                 | invocation       |
+-------------------+----------------------+-----------------+------------------+

Examples
~~~~~~~~

.. code:: bash

   # Use the ARM binary at a specific path, no sudo (already root)
   stuhubm --binary /opt/startech/cusba --no-sudo list

   # JSON output for scripting
   stuhubm --json status /dev/ttyUSB0
   # -> {"port": "/dev/ttyUSB0", "model": "7-port Managed USB Hub",
   #     "serial": "00020000149E", "firmware": "v04", "n_ports": 7,
   #     "states": {"1": true, "2": true, "3": false, ...}}

   # Make port 1 the only powered port and persist it
   stuhubm all /dev/ttyUSB0 off
   stuhubm on  /dev/ttyUSB0 1
   stuhubm save /dev/ttyUSB0

   # Power-cycle a device on port 4 (off, wait, on)
   stuhubm off /dev/ttyUSB0 4 && sleep 3 && stuhubm on /dev/ttyUSB0 4

Run any ``stuhubm`` command with ``--verbose`` to print the exact invocation.

Exit codes
~~~~~~~~~~

===== ======================================================
Code  Meaning
===== ======================================================
``0`` Success
``1`` Command failed (non-zero from the binary, parse error)
``2`` Usage error (bad arguments)
``3`` Binary not found
``4`` Timeout
===== ======================================================

Web GUI (``stuhubm-gui``)
-------------------------

Requires the ``[gui]`` extra.

.. code:: bash

   stuhubm-gui                       # serves on http://localhost:8080
   stuhubm-gui --port 9000           # custom port
   stuhubm-gui --native              # desktop window (requires pywebview)

The GUI provides hub discovery, a switch per port reflecting live state,
all-on/all-off, save-to-flash, reset, restore, and a password-change dialog —
plus a console pane showing the exact binary invocation and its output for every
action. Settings (binary path, sudo, password, persist) are editable in-page.
Each browser tab is independent, and a process-wide lock serialize the actual
hardware calls so two tabs never issue overlapping commands.

The GUI is just a convenience layer; everything it does is also available through the
CLI and the Python API.

Python API
----------

The library mirrors the CLI. A short example:

.. code:: python

   from st_uhubm import HubManager, discover

   # Convenience: discover with default settings (cusbi, sudo on)
   for hub in discover():
       print(hub.port, hub.model, hub.firmware, hub.states)

   # Explicit configuration
   mgr = HubManager(binary="cusba", use_sudo=False, password="s3cret")
   hub = mgr.hub("/dev/ttyUSB0")            # read one known hub

   hub.set_port(3, on=False)                # volatile by default
   hub.set_port(3, on=True, persist=True)   # write straight to flash
   hub.set_all(on=False)
   hub.toggle(2)
   hub.save()                               # commit current states to flash
   hub.refresh()                            # re-read live state
   print(hub.is_on(3))

The parsers are also importable for custom integrations or for testing the
tricky logic without hardware:

.. code:: python

   from st_uhubm.cli_backend import parse_query_all, parse_hub_info

   parse_query_all("0002,/dev/ttyUSB0,/dev/ttyUSB1")
   parse_hub_info("FBFFFFFF,7,v04,00020000149E,7-port Managed USB Hub")

The port-state bitmap is 32 bits, little-endian by byte; bit *n*\ −1 corresponds
to port *n* (``1`` = on).

Further details: every class, method, parser, and exception are in the
:doc:`API reference <api>`, generated directly from the source.

Configuration
-------------

Settings resolve in this order (later overrides earlier):

1. Built-in defaults
2. Environment variables (``STUHUBM_BINARY``, ``STUHUBM_SUDO``,
   ``STUHUBM_PASSWORD``, ``STUHUBM_PERSIST``)
3. Command-line flags (CLI) or ``HubManager`` arguments (API)

This makes CI configuration straightforward: set the environment once, then call
plain commands.

Use in CI automation
----------------------

Typical pattern: power-cycle a DUT between stages:

.. code:: yaml

   # Example CI step (any runner with the hub attached)
   env:
     STUHUBM_BINARY: /opt/startech/cusbi
     STUHUBM_SUDO: "1"
   steps:
     - run: stuhubm health
     - run: stuhubm off /dev/ttyUSB0 4         # cut power to the DUT
     - run: sleep 3
     - run: stuhubm on  /dev/ttyUSB0 4         # power back on
     - run: stuhubm --json status /dev/ttyUSB0 # record final state

For unattended use, configure passwordless ``sudo`` scoped to the binary so calls
never block on a prompt (see below), or run the job as root.

Because the parsing functions are pure text processing, user can cover the tricky logic in 
their own unit tests without any hardware attached:

.. code:: python

   from st_uhubm.cli_backend import parse_hub_info

   def test_port3_off():
       n, states, fw, serial, model = parse_hub_info(
           "FBFFFFFF,7,v04,00020000149E,7-port Managed USB Hub")
       assert states[3] is False
       assert n == 7

Troubleshooting
---------------

Binary not found
~~~~~~~~~~~~~~~~

``stuhubm health`` reports the binary cannot be located. Confirm the file is on
``PATH`` or pass ``--binary /full/path/to/cusbi``. On ARM hosts, ensure you are
using ``cusba``, not ``cusbi``.

No hubs detected
~~~~~~~~~~~~~~~~

- Check the cable :)
- Confirm the device node exists: ``ls /dev/ttyUSB*``.
- Make sure the hub is externally powered if your model/setup requires it.
- Try ``stuhubm --verbose list`` to see the raw discovery output.

Permission denied / sudo prompts
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The binary needs root to open the control tty.

Running without root
^^^^^^^^^^^^^^^^^^^^

To avoid ``sudo`` entirely, grant your user access to the control device with a
udev rule. Identify the device's vendor/product, then add (example):

::

   # /etc/udev/rules.d/99-startech-hub.rules
   SUBSYSTEM=="tty", ATTRS{idVendor}=="XXXX", ATTRS{idProduct}=="YYYY", MODE="0660", GROUP="dialout"

Reload rules (``sudo udevadm control --reload && sudo udevadm trigger``), add your
user to the ``dialout`` group, re-login, and run with ``--no-sudo``.

Alternatively, allow passwordless ``sudo`` for just the binary in
``/etc/sudoers.d/``::

   youruser ALL=(root) NOPASSWD: /usr/local/bin/cusbi

A port powers back on by itself
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Some kernel drivers re-initialize a device shortly after a state change. If a
port you turned off comes back, persist the desired state (``--persist`` or
``stuhubm save``) so the hub re-applies it, and verify with ``stuhubm status``.

Forgotten password
~~~~~~~~~~~~~~~~~~

If you set a password and lost it, use the physical recovery procedure in the
StarTech hardware manual (power off, hold the button, power on) to restore
factory defaults, which resets the password to ``pass``.

Caveats
------------------

- **Flash wear.** ``--persist`` (the ``/F`` path) writes flash on every change.
  For frequently-toggled test rigs, make changes volatile and ``save`` once.
- **Power-cycling live devices.** Cutting a port drops the device immediately.
  Ensure nothing is mid-write (e.g. mass storage) before switching a port off.
- **Root.** The binary runs with elevated privileges; review the ``--verbose``
  output if you need to audit exactly what is executed.
- **Compatibility.** This package targets firmware v04+ output of the StarTech
  binary. If StarTech changes the binary's output format in a future revision,
  parsing may need updating; ``stuhubm --verbose`` and the exposed parser
  functions make this easy to diagnose.

Support
----------------------

The public API is everything exported from the top-level ``st_uhubm`` package;
internal module layout may change between minor versions.

This is community software provided as-is. For issues with the **hub hardware or
the StarTech binary itself**, contact StarTech support. Those are outside the
scope of this package.

License
-------

This package is released under the **GNU General Public License, version 2 or
later** (GPL-2.0-or-later). See the ``LICENSE`` file for the version 2 text.
 
It does not include or redistribute any StarTech software; the ``cusbi`` /
``cusba`` binary is the property of StarTech.com and is governed by StarTech's
own license terms. The GPL applies only to this project's own code.
