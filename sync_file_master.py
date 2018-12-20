#!/usr/bin/env python
# -*- coding:utf-8 -*-
# Description: distribute rsync master
# Author     : quke
# Date       : 2018-12-07


import logging
import subprocess

import redis

minions_count = 195
# first rsync the file to one of the minions
minion_ip = '192.168.254.236'
redis_host = '192.168.254.11'
redis_port = 6379
# the next 4 variables store to redis
# condition race queue
synchronize_queue = 'synchronize_queue'
# indicate the finished minion
finished_queue = 'finished_queue'
running_queue = 'running_queue'
# store the absolute file path
task = 'task'
# lookup=1 then new task create
lookup = 'lookup'

rsync_passwd = 'abc123456def'

_connection = None
logging.basicConfig(filename="/var/log/sync_file_master.log", level=logging.INFO, format='%(asctime)s - %(message)s',
                    datefmt='%d-%b-%y %H:%M:%S')


def connection():
    """
    redis connection singleton
    """
    global _connection
    if _connection is None:
        _connection = redis.StrictRedis(host=redis_host, port=redis_port, db=10)
    return _connection


def get_task():
    """
    get file absolute path from redis key['task']
    """
    file_name = redis_conn.get(task)

    if file_name:
        redis_conn.incr(lookup)
        return file_name
    else:
        logging.info('no task, exit')
        raise SystemExit


def rsync_file_to_minion(file_name):
    print 'start rsync to minion: %s' % file_name
    source = file_name
    destination = 'sre@%s::repo/' % minion_ip
    p = subprocess.Popen(
        'export RSYNC_PASSWORD="%s";rsync -avz %s %s' % (rsync_passwd, source, destination),
        shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    logging.info('rsync complete: \n%s\n%s', p.stdout.read(), p.stderr.read())


def deploy_task():
    logging.info('try to find a task')
    file_name = get_task()
    finished_minions_count = redis_conn.scard(finished_queue)
    logging.info('file_name: %s, finished_minion_count: %s', file_name, finished_minions_count)

    # mission complete then clean model_task and finished_minions
    if minions_count == finished_minions_count:
        logging.info('mission complete, clean task and queue')
        redis_conn.delete(task, lookup, synchronize_queue, finished_queue, running_queue)

    elif "1" == redis_conn.get(lookup):
        logging.info('found new task, start rsync and set redis queue')
        redis_conn.delete(synchronize_queue, finished_queue, running_queue)
        rsync_file_to_minion(file_name)
        redis_conn.sadd(finished_queue, minion_ip)
        redis_conn.sadd(synchronize_queue, minion_ip)
    else:
        logging.info('nothing to do')


if __name__ == '__main__':
    redis_conn = connection()
    deploy_task()

