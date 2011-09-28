'''Calculation manager.

This module provides classes for managing collections of calculations.
For persistant information it is best to interact via a JobCache instance.
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

import copy
import os
import os.path
import pickle
import re
import time
import subprocess

### Custom exceptions ###

class UserError(Exception):
    '''Raised due to an error from user-input.'''
    pass


class LockException(Exception):
    '''Raised if a lock cannot be acquired.'''
    pass

### Cache classes ###

class JobStatus(object):
    '''enum-esque class for specifying the status of a job.

Defined statuses: held, queueing, running, finished, analysed.'''
    unknown = 'unknown'
    held = 'held'
    queueing = 'queueing'
    running = 'running'
    finished = 'finished'
    analysed = 'analysed'


class Job:
    '''Store of information regarding a calculation job.

job_id: job id (e.g. pid or from queueing system)
program: program being executed
path: path to job directory
input_fname: input file name
output_fname: output file name
status: current status of job.  See JobStatus for defined statuses.  This must
be an attribute of JobStatus.
submit: submit script file name.
comment: further information regarding the job.

Only job_id, program and path are required.  All other attributes are optional.
Not all attributes are always applicable.
'''
    def __init__(self, job_id, program, path, input_fname=None, output_fname=None, status=None, submit=None, comment=None):
        self.job_id = job_id
        self.program = program
        self.path = path
        self.input_fname = input_fname
        self.output_fname = output_fname
        self.status = status
        self.submit = submit
        self.comment = comment
        # time since epoch job entry was modified.  useful for merging job caches.
        self._timestamp = time.gmtime()

        if not self.status:
            self.status = JobStatus.unknown

    def __repr__(self):
        return (self.job_id, self.path, self.input_fname, self.output_fname, self.status, self.submit, self.comment).__repr__()

    def mtime(self):
        '''Return the last time (in seconds since the epoch) that the job was modified.'''
        return self._timestamp

    def auto_update(self):
        '''Update status of job automatically.

This inspects the output from ps and any queueing system to discover if the
status of the job has changed (e.g. if the job has started or has finished).
Note that this assumes the job is running on the local computer.  Warning: if
this condition is not met, then the job status will be incorrectly updated to
finished.

Currently only aware of the PBS and LoadLeveler queueing systems.

Only jobs which are currently held, queueing or running are updated.
'''
        # Check the queueing systems.
        # To add a queueing system, add a dictionary to the list.
        queues = [
            dict(
                command=["ps", "aux"],  # command to list all jobs
                job_column=1,  # column of output which contains the job id field (0-indexed).
                status_column=7,  # column of output which contains the status field.
                held=None,  # string which indicates a held status (not used if None).
                queueing=None,  # string which indicates a queueing status (not used if None).
                running=None,  # string which indicates a running status (not used if None).
            ),
            dict(
                command=["qstat"],
                job_column=0,
                status_column=4,
                held='H',
                queueing='Q',
                running='R',
            ),
            dict(
                command=["llq"],
                job_column=0,
                status_column=3,
                held='H|NQ|S',
                queueing='I',
                running='R',
            ),
        ]

        if self.status in (JobStatus.unknown, JobStatus.held, JobStatus.queueing, JobStatus.running):

            for queue in queues:
                try:
                    queue_popen = subprocess.Popen(queue['command'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    output = queue_popen.communicate()[0]
                    if queue_popen.returncode == 0:
                        found_job = False
                        for line in output.splitlines():
                            job_id = line.split()[queue['job_column']]
                            stat = line.split()[queue['status_column']]
                            if re.match(str(self.job_id), job_id):
                                # found job, update status
                                found_job = True
                                if not (queue['held'] and queue['queueing'] and queue['running']):
                                    # don't know about status.  assume running.
                                    self.status = JobStatus.running
                                elif queue['held'] and re.match(queue['held'], stat):
                                    self.status = JobStatus.held
                                elif queue['queueing'] and re.match(queue['queueing'], stat):
                                    self.status = JobStatus.queueing
                                elif queue['running'] and re.match(queue['running'], stat):
                                    self.status = JobStatus.running
                                self._timestamp = time.gmtime()
                                break
                        if not found_job:
                            # Couldn't find job, assume it has finished.
                            self.status = JobStatus.finished
                            self._timestamp = time.gmtime()
                except OSError:
                    # command doesn't exists on this server---skip.
                    pass

    def modify(self, job_spec):
        '''Modify the job description.

job_spec: dictionary with Job attributes as keys associated with new values.
All attributes set at initialisation can be changed.  Keys with null values are
ignored.
'''
        for (attr, val) in job_spec.iteritems():
            if val:
                setattr(self, attr, val)
        self._timestamp = time.gmtime()

    def match(self, pattern):
        '''Test to see if the job description matches the supplied pattern.

pattern: regular expression.  All attributes are tested (using re.search)
against the pattern and if any match then True is returned.
'''
        matched = False
        if pattern:
            for attr in ['job_id', 'program', 'path', 'input_fname', 'output_fname', 'status', 'submit', 'comment']:
                if re.search(pattern, str(getattr(self, attr))):
                    matched = True
        else:
            matched = True
        return matched

    def job_spec(self):
        '''Return a dictionary (a 'job spec') of the job attributes.'''
        return dict(
                     job_id=self.job_id,
                     path=self.path,
                     program=self.program,
                     input_fname=self.input_fname,
                     output_fname=self.output_fname,
                     status=self.status,
                     submit=self.submit,
                     comment=self.comment,
                   )


class JobServer:
    '''Store jobs running on a server/computer.

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
        else:
            print 'Not auto-updating jobs on host %s' % (self.hostname)

    def select(self, pattern):
        '''Select a subset of jobs from the server which match the supplied pattern.

pattern: regular expression.  All jobs are tested (using re.search)
against the pattern and the list of matching jobs is returned.  If pattern is
None then all jobs are returned.
'''
        selected_jobs = []
        for job in self.jobs:
            if job.match(pattern):
                selected_jobs.append(job)
        return selected_jobs

    def delete(self, indices=None, pattern=None):
        '''Delete a selected subset of jobs.

indices: iterable containing indices of Job instances in the jobs
list to delete.
pattern: regular expression.  All jobs are tested (using re.search)
against the pattern and matching jobs are deleted.  Not used if None.
'''
        if indices:
            deleted = 0
            for index in indices:
                self.jobs.pop(index-deleted)
                deleted += 1
        if pattern:
            for job in self.select(pattern):
                self.jobs.remove(job)

    def modify(self, job_spec, indices=None, pattern=None):
        '''Modify a selected subset of jobs.

indices: iterable containing indices of Job instances in the jobs
list to delete.
pattern: regular expression.  All jobs are tested (using re.search)
against the pattern and matching jobs are modified.   Not used if None.
'''
        if indices:
            for index in indices:
                self.jobs[index].modify(job_spec)
        if pattern:
            for (index, job) in enumerate(self.jobs):
                if job.match(pattern):
                    self.jobs[index].modify(job_spec)

    def merge(self, other):
        '''Merge data from another JobServer.

If a job in the other JobServer has the same job_id as a job in the current
instance and has a later modification time, then it is copied across.
If a job in the other JobServer does not have the same job_id as any job in the
current instance, then it is copied across.

Note that the hostname of the other JobServer is not checked.

The job_id of the Job instance is treated as a unique identifier.  This is
usually true on a given queueing system but is not guaranteed with running
local jobs (where the job_id is taken from ps).  Care should thus be taken when
merging jobs from localhost JobServers and from merging jobs from two different
servers (which should instead be grouped together using a JobCache instance).

other: another instance of JobServer.
'''
        # I don't pretend to be efficient here, but we should not be handling MB of data here!
        for other_job in other.jobs:
            found = False
            for job in self.jobs:
                if other_job.job_id == job.job_id:
                    found = True
                    if other_job.mtime() > job.mtime():
                        job.modify(other_job.job_spec())
                    break
            if not found:
                # new job.  add.
                self.jobs.append(copy.deepcopy(other_job))

class JobCache:
    '''Store, manipulate, load and save multiple JobServer instances.

By default a new (empty) JobServer instance is created on localhost.

cache: path to a file in which the job data can be stored and retrieved.  Only
one instance can manipulate job data stored in a cache at a time, so a lock is
acquired when a cache is read and released only when the cache dumped out to
the cache.  The directory for the cache file is created if it doesn't already
exist.
load: if true, load data from an existing cache file.
'''
    def __init__(self, cache, load=False):
        self.job_servers = dict(localhost=JobServer())
        cache = os.path.expanduser(cache)
        cache = os.path.expandvars(cache)
        cache = os.path.abspath(cache)
        self.cache = os.path.normpath(cache)
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
        '''Acquire a lock on the cache file.

This writes the pid of the current instance to the lock_file, which is only
possible if the lock_file doesn't already exist.  Manipulating the job cache
must be atomic in order to avoid race conditions, so one should always acquire
the lock when loading data from the cache file.
'''
        if os.path.exists(self.lock):
            lock_file = open(self.lock)
            pid = lock_file.read().strip()
            lock_file.close()
            raise LockException('Cannot obtain lock file: %s; lock held by process: %s.' % (self.lock, pid))
        else:
            lock_file = open(self.lock, 'w')
            lock_file.write('%i' % os.getpid())
            lock_file.close()
            self._has_lock = True

    def _release_lock(self):
        '''Release the lock on the cache file.

This simply deletes the lock file if the current instance holds the lock.  This
should only be done once the cache has been dumped to file and the current
instance is no longer manipulating the cache.
'''
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

hostname: name of server.

'''
        if hostname in self.job_servers:
            raise UserError('Cannot add new server.  Hostname already exists: %s.' % (hostname))
        self.job_servers[hostname] = JobServer(hostname)

    def auto_update(self):
        '''Auto-update the status of the jobs on the localhost job server.

See also JobServer.auto_update.
'''
        self.job_servers['localhost'].auto_update()

    def merge(self, other, other_hostname):
        '''Merge data from another JobCache.

Each JobServer in other JobCache is merged with the corresponding JobServer in
the current instance.  JobServers are matched by the hostname. If a JobServer
exists in the other JobCache and in the current instance, then they are merged
using JobServer.merge, otherwise it is simply copied to the current instance.
(Note that the localhost hostname of the other JobCache is replaced with
other_hostname to avoid unintended nameclashes.)

other: another instance of JobCache.
other_hostname: hostname of the other JobCache.  Used instead of localhost when
transferring the localhost JobServer from the other JobCache to the current
instance.
'''
        # treat localhost separately---want to save it to a different name.
        other.job_servers['localhost'].hostname = other_hostname
        for job_server in other.job_servers.itervalues():
            if job_server.hostname in self.job_servers:
                # have already got a job_server of the same name. 
                self.job_servers[job_server.hostname].merge(job_server)
            else:
                # simple---host doesn't exist.  just copy the job server directly...
                self.job_servers[job_server.hostname] = copy.deepcopy(job_server)
        # undo local modification to localhost on the other cache.
        other.job_servers['localhost'].hostname = 'localhost'

    def pretty_print(self, hosts=None, pattern=None, short=False):
        '''Print out list of jobs.

hosts: list of hostnames.  If specified, print out only jobs on the specified servers.
pattern: regular expression.  Only jobs which match the supplied
pattern are printed.  If pattern is None then all jobs are printed.
short: print just the hostname, index, job_id and status.
'''
        selected_jobs = {}
        for (host, job_server) in self.job_servers.iteritems():
            if not hosts or job_server.hostname in hosts:
                selected_jobs[host] = job_server.select(pattern)
                # store only servers with jobs matching the pattern
                if not selected_jobs[host]:
                    selected_jobs.pop(host)

        # want output to be ordered: use list.
        attrs = ['hostname', 'index', 'job_id', 'program', 'path', 'input_fname', 'output_fname', 'submit', 'status', 'comment']
        lengths = dict((attr, len(attr)) for attr in attrs)
        used = dict((attr, None) for attr in attrs)
        for (host, jobs) in selected_jobs.iteritems():
            lengths['hostname'] = max(lengths['hostname'], len(host))
            for job in jobs:
                for (attr, val) in job.job_spec().iteritems():
                    lengths[attr] = max(lengths[attr], len(str(val)))
                    used[attr] = used[attr] or val

        # don't output unused fields
        # remove 'long' fields if requested
        for (attr, val) in used.iteritems():
            if (attr not in ['hostname', 'index'] and not val) or \
               (short and attr not in ['hostname', 'index', 'job_id', 'status']):
                attrs.remove(attr)
                lengths.pop(attr)

        if selected_jobs:
            # if not an empty dict, then we have jobs to print.
            # want output in a specific order.
            fmt = ''
            for attr in attrs:
                fmt = '%s%%(%s)-%is  ' % (fmt, attr, lengths[attr])
            print fmt % dict((attr, attr) for attr in attrs)
            print fmt % dict((attr, '-'*lengths[attr]) for attr in attrs)
            for (host, jobs) in selected_jobs.iteritems():
                for job in jobs:
                    output_dict = job.job_spec()
                    output_dict.update((
                        ('hostname', host),
                        ('index', self.job_servers[host].jobs.index(job))
                    ))
                    print fmt % output_dict
