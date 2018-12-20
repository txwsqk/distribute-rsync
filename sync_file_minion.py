#!/usr/bin/env python
# -*- coding:utf-8 -*-
# Description: distribute rsync minion
# Author     : quke
# Date       : 2018-12-07


import logging
import random
import subprocess
import time

import redis
from redis import WatchError

redis_host = '192.168.254.11'
redis_port = 6379
task = 'task'
synchronize_queue = 'synchronize_queue'
finished_queue = 'finished_queue'
running_queue = 'running_queue'
rsync_passwd = 'abc123456def'

_connection = None

logging.basicConfig(filename="/var/log/sync_file_minion.log", level=logging.INFO, format='%(asctime)s - %(message)s',
                    datefmt='%d-%b-%y %H:%M:%S')


def connection():
    global _connection
    if _connection is None:
        _connection = redis.StrictRedis(host=redis_host, port=redis_port, db=10)
    return _connection


def get_ip():
    p = subprocess.Popen('hostname -i', shell=True, stdout=subprocess.PIPE)
    return p.stdout.read().strip()


def start_rsync(minion):
    logging.info('add lock to running_queue')
    logging.info('start rsync from %s' % minion)
    source = 'sre@%s::repo/' % minion
    destination = '/data1/repo/'
    logging.info('START rsync:\n  syn_queue:%d\n  fin_queue:%d\n', redis_conn.scard(synchronize_queue),
                 redis_conn.scard(finished_queue))

    p = subprocess.Popen(
        'export RSYNC_PASSWORD="%s";rsync -av %s %s' % (rsync_passwd, source, destination),
        shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    logging.info('rsync complete: \n%s\n%s', p.stdout.read(), p.stderr.read())
    redis_conn.sadd(synchronize_queue, minion, local_ip)
    redis_conn.sadd(finished_queue, minion, local_ip)
    redis_conn.srem(running_queue, local_ip)

    logging.info('END rsync:\n  syn_queue:%d\n  fin_queue:%d\n', redis_conn.scard(synchronize_queue),
                 redis_conn.scard(finished_queue))


def rsync_file():
    redis_conn.sadd(running_queue, local_ip)

    with redis_conn.pipeline() as pipe:
        while True:
            try:
                logging.info('try to get a avaiable rsync source')
                pipe.watch(synchronize_queue)
                available_minion_total = pipe.scard(synchronize_queue)
                if available_minion_total:
                    pipe.multi()
                    pipe.spop(synchronize_queue)
                    available_minion = pipe.execute()[0]
                    break
                else:
                    time.sleep(random.choice(range(10)))
                    continue
            except WatchError:
                time.sleep(random.choice(range(10)))
                continue
            finally:
                pipe.unwatch()

        start_rsync(available_minion)


if __name__ == '__main__':
    redis_conn = connection()
    local_ip = get_ip()
    finished_minions = redis_conn.smembers(finished_queue)
    running_minions = redis_conn.smembers(running_queue)

    if redis_conn.get(task):
        if local_ip not in finished_minions:
            if local_ip not in running_minions:
                rsync_file()
            else:
                logging.info('task is already running, exit')


