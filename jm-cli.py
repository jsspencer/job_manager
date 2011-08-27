#!/usr/bin/python

import jm

### command-line interface ###

def job_desc_parser(args):

    job_desc = dict(
                     host='localhost',
                     id=None,
                     path=None,
                     input=None,
                     output=None,
                     status=None,
                     submit=None,
                     comment=None,
                   )

    for arg in args:
        if '=' not in arg:
            raise UserException('Do not understand argument: %s' % (arg,))
        (option, value) = arg.split('=')
        if option in job_desc:
            job_desc[option] = value
        else:
            raise UserException('Invalid job descriptor: %s' % (option))

    return job_desc

def add(args):
    
    jc = JobCache('~/.cache/jm/job.cache', load=True)
    jc.dump()

def delete(args):

    jc = JobCache('~/.cache/jm/job.cache', load=True)
    jc.dump()

def modify(args):

    jc = JobCache('~/.cache/jm/job.cache', load=True)
    jc.dump()

def list(args):

    jc = JobCache('~/.cache/jm/job.cache', load=True)
    jc.dump()

def daemon():

    jc = JobCache('~/.cache/jm/job.cache')

    while True:
        time.sleep(60)
        jc.load()
        jc.auto_update()
        jc.dump()
