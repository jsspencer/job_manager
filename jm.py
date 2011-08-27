#!/usr/bin/env python

import os
import os.path
import pickle
import time

### Custom exceptions ###

class UserException(Exception):
    pass

class LockException(Exception):
    pass

### Cache classes ###

class JobStatus:
    '''enum-esque class for specifying the status of a job.

Defined statuses: held, queueing, running, finished, analysed.'''
    held = 'held'
    queueing = 'queueing'
    running = 'running'
    finished = 'finished'
    analysed = 'analysed'


class Job:
    '''Store of information regarding a calculation job.  Not all attributes are always applicable.

Paramters
---------

id: job id (e.g. pid or from queueing system)
path: path to job directory
input: input file name
output: output file name
status: current status of job.  See JobStatus for defined statuses.  This must be an attribute of JobStatus.
submit: submit script file name.
comment: further information regarding the job.

Only id and path are required; all other attributes are optional.
'''
    def __init__(self, id, path, input=None, output=None, status=None, submit=None, comment=None):
        self.id = id
        self.path = path
        self.input = input
        self.output = output
        self.status = status
        self.submit = submit
        self.comment = comment

    def __repr__(self):
        return (self.id, self.path, self.input, self.output, self.status, self.submit, self.comment).__repr__()

    def auto_update(self):
        '''Update status of job automatically.

This inspects the output from ps and any queueing system to discover if the
status of the job has changed (e.g. if the job has started or has finished).
Note that this assumes the job is running on the local computer.  Warning: if
this condition is not met, then the job status will be incorrectly updated to
finished.

Only jobs which are currently held, queueing or running are updated.
'''
        if self.status == JobStatus.held or self.status == JobStatus.queueing or self.status == JobStatus.running:
            # TODO
            # queueing?
            # running?
            # finished?
            pass

    def match(self, pattern):
        '''Test to see if the job description matches the supplied pattern.

Parameters
----------

# TODO: doc
'''
        if pattern:
            # TODO: pattern matching
            matched = True
        else:
            matched = True
        return matched


class JobServer:
    '''Store jobs running on a server/computer.

Parameters
----------

hostname: name of computer running the jobs.  Default: localhost.  localhost is
treated as a special case and is assumed to be the computer on which this
instance of jm is running.
'''
    def __init__(self, hostname='localhost'):
        self.hostname = hostname
        self.jobs = []

    def __repr__(self):
        return (self.hostname, self.jobs).__repr__()

    def add(self, job_desc):
        '''Add a job to the list of jobs running on the server.

Parameters
----------

job_desc: dictionary describing the job to be added.  See Job class for possible fields.
'''
        self.jobs.append(Job(**job_desc))

    def auto_update(self):
        '''Automatically update the job status of all jobs.
        
Only performed on the localhost JobServer.  See also Job.auto_update.
'''
        if self.hostname == 'localhost':
            for job in self.jobs:
                job.auto_update()
            # TODO: discover if queueing system has jobs JobServer doesn't know
            # about.
        else:
            print 'Not auto-updating jobs on host %s' % (self.hostname)

    def select(self, pattern):
        '''Select a subset of jobs from the server which match the supplied pattern.

Parameters
----------

# TODO: doc
'''
        selected_jobs = []
        for job in self.jobs:
            if job.match(pattern):
                selected_jobs.append(job)
        return selected_jobs


class JobCache:
    '''Store, manipulate, load and save multiple JobServer instances.

By default a new (empty) JobServer instance is created on localhost.

Parameters
----------

cache: path to a file in which the job data can be stored and retrieved.  Only
one instance can manipulate job data stored in a cache at a time, so a lock is
acquired when a cache is read and released only when the cache dumped out to
the cache.  The directory for the cache file is created if it doesn't already
exist.
load: if true, load data from an existing cache file.
'''
    def __init__(self, cache, load=False):
        self.job_servers = dict(localhost=JobServer())
        self.cache = os.path.expanduser(cache)
        if not os.path.isdir(os.path.dirname(self.cache)):
            os.makedirs(os.path.dirname(self.cache))
        self.lock = '%s.lock' % (self.cache)
        self._has_lock = False
        if load:
            self.load()

    def __del__(self):
        self._release_lock()

    def __repr__(self):
        return (self.cache, self.lock, self._has_lock, self.job_servers).__repr__()

    def _acquire_lock(self):
        if os.path.exists(self.lock):
            f = open(self.lock)
            pid = f.read().strip()
            f.close()
            raise LockException('Cannot obtain lock file: %s; lock held by process: %s.' % (self.lock, pid))
        else:
            f = open(self.lock, 'w')
            f.write('%i' % os.getpid())
            f.close()
            self._has_lock = True

    def _release_lock(self):
        if self._has_lock:
            os.remove(self.lock)
            self._has_lock = False

    def dump(self):
        '''Dump job_servers data to the cache file.

This also releases the lock and resets the job_servers to be an empty JobServer
instance on the localhost.
'''
        if not self._has_lock:
            self._acquire_lock()
        pickle.dump(self.job_servers, open(self.cache, 'wb'))
        self.job_servers = dict(localhost=JobServer())
        self._release_lock()

    def load(self):
        '''Read in the job_servers data from the cache file.

This action acquires the lock.'''
        self._acquire_lock()
        if os.path.exists(self.cache):
            self.job_servers = pickle.load(open(self.cache))

    def add_server(self, hostname):
        '''Add a new JobServer instance.

Parameters
----------

hostname: name of server.

'''
        if hostname in self.job_servers:
            raise UserException('Cannot add new server.  Hostname already exists: %s.' % (hostname))
        self.job_servers[hostname] = JobServer(hostname)

    def auto_update(self):
        '''Auto-update the status of the jobs on the localhost job server.
        
See also JobServer.auto_update.
'''
        self.job_servers['localhost'].auto_update()

    def pretty_print(self, hosts=None, pattern=None):
        '''Print out list of jobs.

Parameters
----------

hosts: list of hostnames.  If specified, print out only jobs on the specified servers.
pattern: TODO.
'''
        jobs = []
        for (host, job_server) in self.job_servers.iteritems():
            # Move to JobServer.pretty_print
            if not hosts or job_server.hostname in hosts:
                jobs.extend(job_server.select(pattern))
        for job in jobs:
            # TODO: formatting
            # TODO: header
            print job
