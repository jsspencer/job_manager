Installation
------------

``job_manager`` can be used directly.  However the PYTHONPATH environment
variable must include the path to the directory containing the job_manager
directory.  This is the lib directory in the source distribution.  It is also
convenient to set ``jm.py`` and its manpage to be available via the PATH and
MANPATH environment variables respectively.

Under bash this can be accomplished by the commands

.. code-block:: bash

    $ export PYTHONPATH=$PYTHONPATH:/path/to/lib
    $ export PATH=$PATH:/path/to/bin/jm.py
    $ export MANPATH=$MANPATH:/path/to/share/man

A bash completion script for ``jm.py`` is provided for convenience and can be used by
executing:

.. code-block:: bash

    $ source etc/bash_completion.d/jm
