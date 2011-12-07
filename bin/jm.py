#!/usr/bin/env python
'''
Synopsis
--------

.. code-block:: bash

    jm.py add [-c | --cache] [-s | --server] <job_description>

    jm.py modify [-c | --cache] [-s | --server] [-i | --index] [-p | --pattern] <job_description>

    jm.py delete [-c | --cache] [-s | --server] [-i | --index] [-p | --pattern]

    jm.py list [-c | --cache] [-s | --server] [-p | --pattern] [-t | --terse]

    jm.py merge [-c | --cache] <[[user@]remote_host:]remote_cache> [remote_hostname]

    jm.py update [-c | --cache]  

    jm.py daemon [-c | --cache]  

Description
-----------

jm.py provides a command-line interface to the job_manager python module, which
enables a collection of jobs (principally long-running high-performance
computing calculations) to be easily monitored and managed.

Jobs can be added, modified, deleted and subsets of the jobs can be viewed.
Jobs are categorised according to the computer on which they are run.  The
local computer on which jm.py is run is treated specially and is called
*localhost*.

Data is saved to a cache file between runs and different cache files can be
merged together, including caches on remote servers directly over ssh.

Commands
--------

add
    Add a job running on the specified server with job details given by job
    description.
modify
    Modify the selected job(s) according to the job description fields
    supplied.  Note that if neither a pattern nor an index is provided then no
    job is selected to be modified.
delete
    Delete the specified jobs.  Note that if neither a pattern nor an index is
    provided then no job is selected to be modified.
list
    List jobs which match the supplied search criteria.  The complete list of
    jobs is printed out if no options are specified.  Only fields of the job
    description which are not null are printed out.
merge
    Merge jobs from the remote_cache file into the current cache.  The remote
    hostname nickname must be specified if the remote cache is actually a local
    file.  If remote_hostname is not given and the remote_cache is on a remote
    machine, then the hostname in the address is used as the remote_hostname
    parameter.
update
    Check all jobs on the *localhost* server and update the status of queueing
    or running jobs if they have started running or finished.  The job status
    is checked by searching for the *job_id* using ps, qstat (for PBS-based
    queueing systems) and llq (for LoadLeveler queueing systems).
daemon
    Run the update command once a minute.  Designed to be run in the background
    as a daemon-type process.

Job description
---------------

The job_description consists of a list of key-value pairs.  A new pair is
started by a new key, so each value can contain spaces.  The keys must
terminate with a colon (':') and have a space between the end of the key and
the first word in the value.  See :ref:`below <examples>` for examples.

Available elements of the job description are:

job_id
    ID of the job.  This ought to be unique and in order to work with the
    update and daemon commands should identiy the job by either being the pid
    of the job (for jobs running interactively) or the ID of the job in the
    queueing system.  This value is most conveniently obtained from the
    environment or a queueing system environment variable.
path
    Path to the directory in which the job is running.
program
    Name of the program being executed.
input_fname
    Filename of the input file.
output_fname
    Filename of the output file.
status
    status of job.  Available values are: unknown, held, queueing, running,
    finished and analysed.  Default: unknown.
submit
    File name of the submit script used.  Only relevant for jobs run on
    clusters with queueing systems.
comment
    Comment and notes on the job.

Unless specified above, all elements default to being a null value.

A job must have a *job_id*, *path* and *program* specified.  Other attributes are optional.  Only the attributes to be set or modified need to specified with the add and modify commands.

Options
-------

-c, --cache
    Specify the location of the cache file containing data from previous runs.
    The default is $HOME/.cache/jm/jm.cache.  The directory structure for the
    cache file will be created if necessary.
-s, --server
    Specify the server of the job.  The default is the *localhost* server
    except for the **list** command, where the default is all servers.  Can be
    specified multiple times, in which case the command is applied to each
    server in turn.  However, this rarely makes sense for the **add** command.
-i, --index
    Select a job by its index on the specified server(s).  Can be specified
    multiple times in order to select multiple jobs.
-p, --pattern
    Select a job by a given regular expression on the specified server(s).  The
    regular expression is tested against all fields in the job description for
    each job and a job is selected if any of the fields match the regular
    expression.
-t, --terse
    Print only the hostname, index, job id and status of each job.

.. _examples:

Examples
--------

Create a job from inside a script.  $$ is the current process id in bash.

.. code-block:: bash

    $ jm.py add job_id: $$ path: $PWD status: running 

List all jobs.

.. code-block:: bash

    $ jm.py list

Modify part of the job description.

.. code-block:: bash

    $ jm.py modify --index 0 comment: a test calculation

Automatically update the status of running jobs

.. code-block:: bash

    $ jm.py update

Run a daemon process to automatically update the status of running jobs once
a minute using a non-default cache file.

.. code-block:: bash

    $ jm.py daemon --cache /path/to/cache

Merge jobs from a remote server into the local job cache:

.. code-block:: bash

    $ jm.py merge user@remote_server_fqdn:/path/to/remote_cache remote_server_name

.. note::

    The remote file is transferred by scp and requires password-free access to
    the remote server (e.g. by using ssh keys and ssh-agent).  If this is not
    possible, copy the remote cache to the local machine and then merge using
    the local copy.

List a subset of jobs.

.. code-block:: bash

    $ jm.py list --server remote_server
    $ jm.py list --server localhost

Delete a job on the remote server.

.. code-block:: bash

    $ jm.py delete --server remote --index 0

License
-------

The jm.py script and the job_manager python module are distributed under the
Modified BSD License.  Please see the source files for more information.

Bugs
----

Contact James Spencer (j.spencer@imperial.ac.uk) regarding bug reports,
suggestions for improvements or code contributions.
'''

# Copyright (c) 2011, James Spencer. All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 
# #. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# #. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
# #. The name of the author may not be used to endorse or promote products
#    derived from this software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR ''AS IS'' AND ANY EXPRESS OR IMPLIED
# WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO
# EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
# OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
# OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
# ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import job_manager
import optparse
import os
import re
import subprocess
import sys
import tempfile
import time

### parsers ###

def subcommand_parser(subcommands, args):
    '''Obtain the subcommand specified in the arguments.

subcommands: list of available subcommnds.
args: list of command-line arguments.

Return the specified subcommand and the list of arguments with the subcommand
removed.

For full usage see top-level __doc__.
'''

    subcommand = None

    for arg in args:
        if arg in subcommands:
            if subcommand:
                raise job_manager.UserError('Cannot use multiple subcommands: %s and %s' % (subcommand, arg))
            else:
                subcommand = arg

    if subcommand:
        args.remove(subcommand)

    return (subcommand, args)

def job_desc_parser(job_desc_list):
    '''Parse job_desc_list.
    
job_desc_list: list of job descriptors.

Return a corresponding job_desc dictionary, which describes a Job instance.

Each element of job_desc_list is of the format attribute=value, where
allowed attributes are:

job_id: job id (e.g. pid or from queueing system)
path: path to job directory
input_fname: input file name
output_fname: output file name
status: current status of job.  See JobStatus for defined statuses.
submit: submit script file name.
comment: further information regarding the job.

Values not set default to None.
'''

    job_desc = dict(
                     job_id=None,
                     program=None,
                     path=None,
                     input_fname=None,
                     output_fname=None,
                     status=job_manager.JobStatus.unknown,
                     submit=None,
                     comment=None,
                   )

    option = job_desc_list[0][:-1]
    value = ''
    if option not in job_desc:
        raise job_manager.UserError('Invalid job descriptor: %s' % (option))
    for word in job_desc_list[1:]:
        if word[:-1] in job_desc and word[-1] == ':':
            job_desc[option] = value.strip() # remove trailing space
            option = word[:-1]
            value = ''
        else:
            value = '%s%s ' % (value, word)
    # add last option
    if option in job_desc:
        job_desc[option] = value.strip()
    else:
        raise job_manager.UserError('Invalid job descriptor: %s' % (option))

    return job_desc

def option_parser(subcommands, args):
    '''Pass options for an subcommand to select a job from .

subcommands: list of available subcommands.
args: list of arguments.  Not all options are valid for all subcommands.

Returns:

subcommand: selected subcommand.
options: an optparse.Values instance containing the set options.

For full usage, see top-level __doc__.
'''

    usage = '''
%prog add [-c | --cache] [-s | --server] <job_description>
%prog modify [-c | --cache] [-s | --server] [-i | --index] [-p | --pattern] <job_description>
%prog delete [-c | --cache] [-s | --server] [-i | --index] [-p | --pattern]
%prog list [-c | --cache] [-s | --server] [-p | --pattern] [-s | --terse]
%prog merge [-c | --cache] <[[user@]remote_host:]remote_cache> [remote_hostname]
%prog update [-c | --cache]
%prog daemon [-c | --cache]'''
    description = '''Manage and manipulate a set of jobs.
Options that are not relevant to a command are ignored.  See the man page for
more details.'''
    epilog='''A job_description consists of
a series of key: value pairs.  Available keys are job_id, program, path,
input_fname, output_fname, status, submit and comment.  Allowed status values
are unknown, held, queueing, running, finished and analysed.  Only job_id,
program and path are required to add a job and only the attributes to be
changed are required when modify a job.  Unused attributes are set to null
values.'''
    if sys.version_info[:2] >= (2, 5):
        # have epilog
        parser = optparse.OptionParser(
                                       usage=usage,
                                       description=description,
                                       epilog=epilog,
                                      )
    else:
        parser = optparse.OptionParser(
                                       usage=usage,
                                       description=description,
                                      )
    parser.add_option('-c', '--cache', default='~/.cache/jm/jm.cache', help='file containing stored job data.  Default: %default.')
    parser.add_option('-i', '--index', default=[], action='append', type='int', help='index of desired calculation on the server.  Can be specified multiple times to select multiple jobs.')
    parser.add_option('-s', '--server', default=[], action='append', help='servers of the job.  Can be specified multiple times to select more than one server.  Default: all servers (list command) or localhost (otherwise).')
    parser.add_option('-p', '--pattern', help='Select a job by a given regular expression on the specified server(s).')
    parser.add_option('-t', '--terse', action="store_true", default=False, help="Print only minimal information.")

    (options, args) = parser.parse_args(args)

    # obtain subcommand
    (subcommand, args) = subcommand_parser(subcommands, args)

    if subcommand != 'list' and len(options.server) == 0:
        options.server = ['localhost']

    # get additional arguments
    if subcommand in ['add', 'modify']:
        if len(args) == 0:
            raise job_manager.UserError('%s requires a job_desc.' % (subcommand))
        else:
            options.job_desc = job_desc_parser(args)
    elif subcommand in ['merge']:
        if len(args) == 0:
            raise job_manager.UserError('%s requires a second cache file.' % (subcommand))
        elif len(args) == 1:
            options.remote_cache = args[0]
            options.remote_server = None
        else:
            options.remote_cache = args[0]
            options.remote_server = args[1]

    return (subcommand, options)

### command-line interface ###

def add(options):
    '''Add a job.

options: optparse.Values instance as returned by option_parser.

For full usage, see top-level __doc__.
'''
    
    job_cache = job_manager.JobCache(options.cache, load=True)
    for server in options.server:
        if server not in job_cache.job_servers:
            job_cache.add_server(options.server)
        job_cache.job_servers[server].add(options.job_desc)
    job_cache.dump()

def delete(options):
    '''Delete a job.

options: optparse.Values instance as returned by option_parser.

For full usage, see top-level __doc__.
'''

    job_cache = job_manager.JobCache(options.cache, load=True)
    for server in options.server:
        job_cache.job_servers[server].delete(options.index, options.pattern)
    job_cache.dump()

def modify(options):
    '''Modify a job.

options: optparse.Values instance as returned by option_parser.

For full usage, see top-level __doc__.
'''

    job_cache = job_manager.JobCache(options.cache, load=True)
    for server in options.server:
        job_cache.job_servers[server].modify(options.job_desc, options.index, options.pattern)
    job_cache.dump()

def list_jobs(options):
    '''List jobs.

options: optparse.Values instance as returned by option_parser.

For full usage, see top-level __doc__.
'''

    job_cache = job_manager.JobCache(options.cache, load=True)
    job_cache.pretty_print(options.server, options.pattern, options.terse)
    job_cache.dump()

def merge(options):
    '''Merge jobs from two cache files.

options: optparse.Values instance as returned by option_parser.

For full usage, see top-level __doc__.
'''

    tmp_cache = None
    if re.match('.*?(.*?):', options.remote_cache):
        # a cache on a remote server has been provided
        tmp_cache = tempfile.NamedTemporaryFile(delete=False)
        tmp_cache.close()
        scp_proc = subprocess.Popen(['scp',options.remote_cache,tmp_cache.name], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (out,err) = scp_proc.communicate()
        if scp_proc.returncode != 0:
            raise job_manager.UserError('scp returned: %i.  Error: %s' % (scp_proc.returncode, err))
        if not options.remote_server:
            options.remote_server = options.remote_cache.split('@')[-1].split(':')[0]
        options.remote_cache = tmp_cache.name
    else:
        remote_cache = options.remote_cache

    if not options.remote_server:
        raise job_manager.UserError('No remote_server specified.')

    job_cache = job_manager.JobCache(options.cache, load=True)
    job_cache_remote = job_manager.JobCache(options.remote_cache, load=True)

    job_cache.merge(job_cache_remote, options.remote_server)

    job_cache.dump()
    if tmp_cache:
        os.remove(tmp_cache.name)

def daemon(options):
    '''Auto-update status of any queueing or running jobs once a minute.
    
Designed to run in the background.  Only jobs on the localhost JobServer are updated.

options: optparse.Values instance as returned by option_parser.

For full usage, see top-level __doc__.
'''

    job_cache = job_manager.JobCache(options.cache)

    while True:
        time.sleep(60)
        try:
            job_cache.load()
            job_cache.auto_update()
            job_cache.dump()
        except job_manager.LockException:
            # quietly skip this update if the cache is in use.
            pass

def update(options):
    '''Auto-update status of any queueing or running jobs.

options: optparse.Values instance as returned by option_parser.

For full usage, see top-level __doc__.
'''
    job_cache = job_manager.JobCache(options.cache)
    job_cache.load()
    job_cache.auto_update()
    job_cache.dump()

### main ###

def main(args):
    '''Wrapper around a JobCache instance providing a command-line interface.

args: list of arguments.

For full usage, see top-level __doc__.
'''

    subcommands = dict(
                       add=add,
                       modify=modify,
                       delete=delete,
                       list=list_jobs,
                       merge=merge,
                       daemon=daemon,
                       update=update,
                      )

    (subcommand, options) = option_parser(subcommands.keys(), args)

    if subcommand:
        if subcommand in subcommands:
            subcommands[subcommand](options)
        else:
            raise job_manager.UserError('subcommand not recognised: %s' % (subcommand))
    else:
        raise job_manager.UserError('No subcommand supplied')

if __name__ == '__main__':

    main(sys.argv[1:])
