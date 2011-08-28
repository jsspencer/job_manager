'''Calculation manager.

This module provides classes for managing collections of calculations.
For persistant information it is best to interact via a JobCache instance.
'''

import os
import os.path
import pickle
import re
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
    held = 'held'
    queueing = 'queueing'
    running = 'running'
    finished = 'finished'
    analysed = 'analysed'


class Job:
    '''Store of information regarding a calculation job.

Paramters
---------

job_id: job id (e.g. pid or from queueing system)
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

    def __repr__(self):
        return (self.job_id, self.path, self.input_fname, self.output_fname, self.status, self.submit, self.comment).__repr__()

    def auto_update(self):
        '''Update status of job automatically.

This inspects the output from ps and any queueing system to discover if the
status of the job has changed (e.g. if the job has started or has finished).
Note that this assumes the job is running on the local computer.  Warning: if
this condition is not met, then the job status will be incorrectly updated to
finished.

Currently only aware of the PBS queueing system.

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
        ]

        if self.status in (JobStatus.held, JobStatus.queueing, JobStatus.running):

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
                                break
                        if not found_job:
                            # Couldn't find job, assume it has finished.
                            self.status = JobStatus.finished
                except OSError:
                    # command doesn't exists on this server---skip.
                    pass

    def match(self, pattern):
        '''Test to see if the job description matches the supplied pattern.

Parameters
----------

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
                     input_fname=self.input_fname,
                     output_fname=self.output_fname,
                     status=self.status,
                     submit=self.submit,
                     comment=self.comment,
                   )


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
        else:
            print 'Not auto-updating jobs on host %s' % (self.hostname)

    def select(self, pattern):
        '''Select a subset of jobs from the server which match the supplied pattern.

Parameters
----------

pattern: regular expression.  All jobs are tested (using re.search)
against the pattern and the list of matching jobs is returned.  If pattern is
None then all jobs are returned.
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

Parameters
----------

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

    def pretty_print(self, hosts=None, pattern=None):
        '''Print out list of jobs.

Parameters
----------

hosts: list of hostnames.  If specified, print out only jobs on the specified servers.
pattern: regular expression.  Only jobs which match the supplied
pattern are printed.  If pattern is None then all jobs are printed.
'''
        selected_jobs = {}
        for (host, job_server) in self.job_servers.iteritems():
            if not hosts or job_server.hostname in hosts:
                selected_jobs[host] = job_server.select(pattern)
                # store only servers with jobs matching the pattern
                if not selected_jobs[host]:
                    selected_jobs.pop(host)

        attrs = ['hostname', 'index', 'job_id', 'path', 'input_fname', 'output_fname', 'submit', 'status', 'comment']
        lengths = dict((attr, len(attr)) for attr in attrs)
        for (host, jobs) in selected_jobs.iteritems():
            lengths['hostname'] = max(lengths['hostname'], len(host))
            for job in jobs:
                for (attr, val) in job.job_spec().iteritems():
                    lengths[attr] = max(lengths[attr], len(str(val)))

        if selected_jobs:
            # if not an empty dict, then we have jobs to print.
            # want output in a specific order.
            fmt = ''
            for attr in attrs:
                fmt = '%s%%(%s)-%is  ' % (fmt, attr, lengths[attr])
            header = dict((attr, attr) for attr in attrs)
            print fmt % header
            for attr in header.itervalues():
                header[attr] = '-'*lengths[attr]
            print fmt % header
            for (host, jobs) in selected_jobs.iteritems():
                for job in jobs:
                    output_dict = job.job_spec()
                    output_dict.update((
                        ('hostname', host),
                        ('index', self.job_servers[host].jobs.index(job))
                    ))
                    print fmt % output_dict
