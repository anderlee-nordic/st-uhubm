API reference
=============

The public API lives in :mod:`st_uhubm`; the implementation is in
:mod:`st_uhubm.cli_backend`.

Hubs and the manager
--------------------

.. autoclass:: st_uhubm.cli_backend.HubManager
   :members:

.. autoclass:: st_uhubm.cli_backend.Hub
   :members:

Parsers
-------

.. autofunction:: st_uhubm.cli_backend.parse_query_all
.. autofunction:: st_uhubm.cli_backend.parse_hub_info
.. autofunction:: st_uhubm.cli_backend.discover

Errors
------

.. automodule:: st_uhubm.errors
   :members:

.. autoclass:: st_uhubm.cli_backend.ManagedHubAttachmentError
   :members:
