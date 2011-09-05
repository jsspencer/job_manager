#!/usr/bin/python
'''
Synopsis
--------

jm.py add [-c | --cache] [-s | --server] <job_description>

jm.py modify [-c | --cache] [-s | --server] [-i | --index] [-p | --pattern] <job_description>

jm.py delete [-c | --cache] [-s | --server] [-i | --index] [-p | --pattern]

jm.py list [-c | --cache] [-s | --server] [-p | --pattern]

jm.py update [-c | --cache]  

jm.py daemon [-c | --cache]  

jm.py merge [-c | --cache] <[[user@]remote_host:]remote_cache> [remote_hostname]

Description
-----------

Commands
--------

Options
-------

Examples
--------
'''

import job_manager
import optparse
import os
import re
import sys
import tempfile
import time

# optional paramiko functionality
try:
    import paramiko
    HAVE_PARAMIKO = True
except ImportError:
    HAVE_PARAMIKO = False

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
                     status=None,
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

    parser = optparse.OptionParser()
    parser.add_option('-c', '--cache', default='~/.cache/jm/jm.cache', help='file containing stored job data.  Default: %default.')
    parser.add_option('-i', '--index', default=[], action='append', type='int', help='index of desired calculation on the server specified by --server.  All jobs are selected if not provided.  Can be specified multiple times to select multiple jobs.')
    parser.add_option('-s', '--server', default=[], action='append', help='hostname of servers running the calculations.  All servers are selected if not provided.  Can be specified multiple times multiple times to select multiple servers.  Default: localhost.')
    parser.add_option('-p', '--pattern', help='')

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
    job_cache.pretty_print(options.server, options.pattern)
    job_cache.dump()

def merge(options):
    '''Merge jobs from two cache files.

options: optparse.Values instance as returned by option_parser.

For full usage, see top-level __doc__.
'''

    tmp_cache = None
    if re.match('.*?(.*?):', options.remote_cache):
        # a cache on a remote server has been provided
        if HAVE_PARAMIKO:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            remotem = re.match('(.*?)@(.*?):(.*)', options.remote_cache) 
            if remotem:
                user = remotem.group(1)
                host = remotem.group(2)
                remote_file = remotem.group(3)
                ssh.connect(host, username=user)
            else:
                remotem = re.match('(.*?):(.*)', options.remote_cache) 
                host = remotem.group(1)
                remote_file = remotem.group(2)
                ssh.connect(host)
            if not options.remote_server:
                options.remote_server = host
            sftp = ssh.open_sftp()
            tmp_cache = tempfile.NamedTemporaryFile(delete=False)
            tmp_cache.close()
            options.remote_cache = tmp_cache.name
            sftp.get(remote_file, options.remote_cache)
            sftp.close()
            ssh.close()
        else:
            raise job_manager.UserError('Cannot obtain remote cache files without paramiko installed.')

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
        job_cache.load()
        job_cache.auto_update()
        job_cache.dump()

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
