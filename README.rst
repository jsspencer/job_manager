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

Documentation
-------------

Full documentation can be found in the ``docs/`` subdirectory and in the
appropriate docstrings.  Documentation can be compiled using :ref:`sphinx
<http://sphinx.pocoo.org/>`_.  The html and man builds are included in the
``docs/build/`` subdirectory.

Author
------

James Spencer, Imperial College London.

LICENSE
-------

Modified BSD license; see LICENSE for more details.
