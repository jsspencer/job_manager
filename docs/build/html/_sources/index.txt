job_manager
===========

``job_manager`` is a lightweight python module for managing a large number of
long-running jobs (particularly calcuations on high-performance computing
resources).  Jobs added previously are stored in a cache file.  Job information
can be added, updated, manipulated and deleted.  Jobs from different servers
can also be collated in one place, via a builtin merge capability.

``job_manager`` can be imported and used in python scripts.  A command-line
interface, ``jm.py`` is provided which exposes most functionaility of
``job_manager`` for everyday use.

.. toctree::
   :maxdepth: 1

   install
   jm
   job_manager
   license

Indices and tables
==================

* :ref:`genindex`
* :ref:`search`
